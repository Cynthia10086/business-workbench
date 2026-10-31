import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime import Workbench, WorkbenchError, dispatch
from mcp_server import Server


def record(id='GENERIC:example', body='参考步骤完整内容'):
    return dict(id=id, title='转化归因', body=body, source=dict(document='原创测试说明', page_numbers=[]), family_ids=['generic'], limitations=['测试用虚构内容'], scenario_ids=['growth-funnel'], method_type_ids=['metric-decomposition'], management_levels=['store'])


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=str(Path(tempfile.gettempdir()).resolve()))
        self.base = Path(self.temp.name)
        self.wb = Workbench(self.base / 'workspace')
        self.case_id = self.wb.case_create('Synthetic case')['case_id']
        self.msg = self.wb.message_append(self.case_id, 'user', '本月销售额下降12%，客流持平。缺货还没确认。')

    def tearDown(self):
        self.wb.close()
        self.temp.cleanup()

    def expect_error(self, code, fn, *args, **kwargs):
        with self.assertRaises(WorkbenchError) as ctx:
            fn(*args, **kwargs)
        self.assertEqual(ctx.exception.code, code)

    def state(self):
        return self.wb.case_get(self.case_id)['state']

    def ref(self, quote='销售额下降12%', id=None, kind='message'):
        return dict(kind=kind, id=id or self.msg['id'], quote=quote)

    def test_fact_verbatim_ref_and_revision(self):
        state = self.state()
        state['facts'] = [dict(id='F1', text='销售额下降', evidence_refs=[self.ref()])]
        self.assertEqual(self.wb.state_update(self.case_id, 0, state)['revision'], 1)
        self.expect_error('REVISION_CONFLICT', self.wb.state_update, self.case_id, 0, state)
        self.assertEqual(len(self.wb.case_get(self.case_id)['revisions']), 2)

    def test_fabricated_quote_rejected(self):
        state = self.state()
        state['facts'] = [dict(id='F1', text='任意归因', evidence_refs=[self.ref('促销导致增长')])]
        self.expect_error('QUOTE_MISMATCH', self.wb.state_update, self.case_id, 0, state)
        self.assertEqual(self.wb.case_get(self.case_id)['revision'], 0)

    def test_assistant_cannot_be_evidence(self):
        msg = self.wb.message_append(self.case_id, 'assistant', '库存不足。')
        state = self.state()
        state['facts'] = [dict(id='F1', text='缺货', evidence_refs=[self.ref('库存不足', msg['id'])])]
        self.expect_error('INVALID_REFERENCE', self.wb.state_update, self.case_id, 0, state)

    def test_method_cannot_prove_business_fact(self):
        state = self.state()
        state['facts'] = [dict(id='F1', text='缺货', evidence_refs=[dict(kind='method', id='GENERIC:example', quote='库存')])]
        self.expect_error('INVALID_REFERENCE', self.wb.state_update, self.case_id, 0, state)

    def test_cross_case_ref_rejected(self):
        other = self.wb.case_create('Other')['case_id']
        msg = self.wb.message_append(other, 'user', '库存不足。')
        state = self.state()
        state['facts'] = [dict(id='F1', text='缺货', evidence_refs=[self.ref('库存不足', msg['id'])])]
        self.expect_error('INVALID_REFERENCE', self.wb.state_update, self.case_id, 0, state)

    def test_preserve_counterevidence_and_claim_text(self):
        state = self.state()
        state['hypotheses'] = [dict(id='H1', text='客流下降导致销售下降', supporting_refs=[], counter_refs=[self.ref('客流持平')])]
        self.wb.state_update(self.case_id, 0, state)
        state['hypotheses'][0]['counter_refs'] = []
        self.expect_error('HISTORY_LOSS', self.wb.state_update, self.case_id, 1, state)
        state = self.state()
        state['hypotheses'][0]['text'] = '替换原话'
        self.expect_error('HISTORY_LOSS', self.wb.state_update, self.case_id, 1, state)
        state = self.state()
        state['hypotheses'][0]['status'] = 'rejected'
        self.wb.state_update(self.case_id, 1, state)

    def test_original_messages_append_only(self):
        self.wb.message_append(self.case_id, 'assistant', '待验证')
        export = self.wb.case_export(self.case_id)['content']
        self.assertEqual(export['messages'][0]['text'], self.msg['text'])
        self.assertEqual(len(export['messages']), 2)
        self.expect_error('UNKNOWN_TOOL', dispatch, self.wb, 'message_update', {})

    def test_text_source_actual_read_binary_pending(self):
        p = self.base / 'metrics.txt'
        p.write_text('毛利率20%，口径待核对', encoding='utf-8')
        source = self.wb.source_add(self.case_id, path=str(p))['source']
        self.assertEqual(source['content_text'], '毛利率20%，口径待核对')
        state = self.state()
        state['facts'] = [dict(id='F1', text='毛利率', evidence_refs=[self.ref('毛利率20%', source['id'], 'source')])]
        self.wb.state_update(self.case_id, 0, state)
        binary = self.base / 'diagram.pdf'
        binary.write_bytes(b'%PDF-fake')
        pending = self.wb.source_add(self.case_id, path=str(binary))['source']
        self.assertEqual(pending['extraction_status'], 'pending_extraction')
        self.expect_error('INVALID_REFERENCE', self.wb.verify_ref, self.case_id, self.ref('%PDF', pending['id'], 'source'))

    def test_lineage_duplicate_and_explicit_promotion(self):
        original = self.wb.source_add(self.case_id, text='经营记录')
        same = self.wb.source_add(self.case_id, text='经营记录')
        self.assertTrue(same['duplicate'])
        derived = self.wb.source_add(self.case_id, text='经营记录二次摘录', derived_from=original['source']['id'])['source']
        self.assertEqual(derived['evidence_family_id'], original['source']['evidence_family_id'])
        self.assertEqual(self.wb.library_search('经营')['matched_count'], 0)
        self.wb.source_promote(self.case_id, original['source']['id'])
        self.assertEqual(self.wb.library_search('经营')['matched_count'], 1)

    def test_budget_omits_full_item_and_get_preserves_text(self):
        long = '完整原文' * 5000
        source = self.wb.source_add(self.case_id, text=long)['source']
        result = self.wb.context_assemble(self.case_id, budget_chars=1000)
        self.assertTrue(any(x['id'] == source['id'] and x['reason'] == 'budget_exceeded' for x in result['omitted']))
        self.assertLessEqual(result['budget']['used'], 1000)
        self.assertEqual(self.wb.source_get(self.case_id, source['id'])['content_text'], long)

    def test_knowledge_import_idempotence_conflict_no_partial(self):
        p = self.base / 'knowledge.json'
        p.write_text(json.dumps({'records': [record()]}), encoding='utf-8')
        self.assertEqual(self.wb.knowledge_import(str(p))['added'], 1)
        self.assertEqual(self.wb.knowledge_import(str(p))['already_present'], 1)
        self.assertEqual(self.wb.knowledge_search('转化')['results'][0]['id'], 'GENERIC:example')
        changed = record(body='changed')
        p.write_text(json.dumps({'records': [record(id='GENERIC:new'), changed]}), encoding='utf-8')
        self.expect_error('KNOWLEDGE_CONFLICT', self.wb.knowledge_import, str(p))
        self.expect_error('NOT_FOUND', self.wb.knowledge_get, 'GENERIC:new')

    def test_legacy_manifest_hash_and_path_validation(self):
        package = self.base / 'legacy'
        (package / 'records').mkdir(parents=True)
        r = record(id='MODEL:sample')
        raw = json.dumps(r).encode()
        sha = hashlib.sha256(raw).hexdigest()
        (package / 'records' / 'one.json').write_bytes(raw)
        index = json.dumps([dict(id=r['id'], sha256=sha)]).encode()
        (package / 'index.json').write_bytes(index)
        manifest = dict(index_sha256=hashlib.sha256(index).hexdigest(), records=[dict(id=r['id'], sha256=sha, file='records/one.json')])
        (package / 'manifest.json').write_text(json.dumps(manifest))
        self.assertEqual(self.wb.knowledge_import(str(package))['added'], 1)
        manifest['records'][0]['file'] = '../outside.json'
        (package / 'manifest.json').write_text(json.dumps(manifest))
        self.expect_error('UNSAFE_PATH', self.wb.knowledge_import, str(package))
        manifest['records'][0]['file'] = 'records/one.json'
        (package / 'manifest.json').write_text(json.dumps(manifest))
        (package / 'records' / 'one.json').write_text('{}')
        self.expect_error('HASH_MISMATCH', self.wb.knowledge_import, str(package))

    def test_workspace_symlink_and_product_directory_rejected(self):
        link = self.base / 'linked'
        link.symlink_to(self.base / 'workspace', target_is_directory=True)
        self.expect_error('UNSAFE_PATH', Workbench, link)
        self.expect_error('UNSAFE_WORKSPACE', Workbench, ROOT / 'runtime-data')
        malicious = self.base / 'malicious'
        malicious.mkdir()
        (malicious / 'workbench.sqlite3').symlink_to(self.base / 'workspace' / 'workbench.sqlite3')
        self.expect_error('UNSAFE_PATH', Workbench, malicious)

    def test_unsupported_database_schema_not_mutated(self):
        folder = self.base / 'future'
        folder.mkdir()
        db = folder / 'workbench.sqlite3'
        conn = sqlite3.connect(db)
        conn.execute('CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
        conn.execute("INSERT INTO meta VALUES('schema_version','999')")
        conn.commit()
        before = db.read_bytes()
        self.expect_error('SCHEMA_MISMATCH', Workbench, folder)
        self.assertEqual(db.read_bytes(), before)
        self.assertEqual([r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")], ['meta'])
        conn.close()

    def test_dispatch_schema_unknown_and_invalid(self):
        self.expect_error('UNKNOWN_TOOL', dispatch, self.wb, 'execute_shell', {})
        self.expect_error('INVALID_ARGUMENT', dispatch, self.wb, 'case_create', {'title': 3})
        self.expect_error('INVALID_ARGUMENT', dispatch, self.wb, 'case_create', {'title': 'ok', 'extra': 1})
        self.expect_error('INVALID_ARGUMENT', dispatch, self.wb, 'knowledge_search', {'query': 'x', 'limit': -1})

    def test_two_connections_revision_conflict(self):
        second = Workbench(self.base / 'workspace')
        try:
            state = self.state()
            self.wb.state_update(self.case_id, 0, state)
            self.expect_error('REVISION_CONFLICT', second.state_update, self.case_id, 0, state)
        finally:
            second.close()

    def test_mcp_protocol_errors_and_shared_validation(self):
        server = Server(self.wb)
        self.assertEqual(server.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'})['error']['code'], -32000)
        init = server.handle({'jsonrpc': '2.0', 'id': 2, 'method': 'initialize', 'params': {'protocolVersion': '2025-06-18', 'capabilities': {}, 'clientInfo': {'name': 'test', 'version': '1'}}})
        self.assertEqual(init['result']['protocolVersion'], '2025-06-18')
        self.assertIsNone(server.handle({'jsonrpc': '2.0', 'method': 'notifications/initialized'}))
        unknown = server.handle({'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'execute_shell', 'arguments': {}}})
        self.assertEqual(unknown['error']['code'], -32602)
        self.assertIn('UNKNOWN_TOOL', unknown['error']['message'])

    def test_unknown_methods_and_invalid_status_rejected(self):
        state = self.state()
        state['hypotheses'] = [dict(id='H1', text='假设', supporting_refs=[], counter_refs=[], method_ids=['GENERIC:missing'])]
        self.expect_error('NOT_FOUND', self.wb.state_update, self.case_id, 0, state)
        state['hypotheses'][0]['method_ids'] = []
        state['hypotheses'][0]['status'] = 'causal_proof'
        self.expect_error('INVALID_STATE', self.wb.state_update, self.case_id, 0, state)
        del state['hypotheses'][0]['status']
        state['hypotheses'][0]['knowledge_refs'] = ['missing']
        self.expect_error('INVALID_REFERENCE', self.wb.state_update, self.case_id, 0, state)

    def test_stdio_and_cli_are_json(self):
        requests = [dict(jsonrpc='2.0', id=1, method='initialize', params=dict(protocolVersion='2025-06-18', capabilities={}, clientInfo=dict(name='test', version='1'))), dict(jsonrpc='2.0', method='notifications/initialized'), dict(jsonrpc='2.0', id=2, method='tools/list')]
        proc = subprocess.run([sys.executable, str(ROOT / 'mcp_server.py'), '--workspace', str(self.base / 'stdio')], input='\n'.join(json.dumps(r) for r in requests)+'\n', text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        lines = [json.loads(s) for s in proc.stdout.splitlines()]
        self.assertEqual(len(lines), 2)
        self.assertEqual(len(lines[1]['result']['tools']), 17)
        bad = subprocess.run([sys.executable, str(ROOT / 'cli.py'), '--workspace', str(self.base / 'cli'), 'case_create', '--payload', '{bad'], text=True, capture_output=True)
        self.assertEqual(bad.returncode, 2)
        self.assertEqual(json.loads(bad.stdout)['error']['code'], 'INVALID_JSON')


if __name__ == '__main__':
    unittest.main()
