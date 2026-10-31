"""One discovery contract shared by CLI, MCP, and optional local UI."""
S = {"type": "string"}
I = {"type": "integer"}
STRINGS = {"type": "array", "items": S}


def tool(name, description, properties=None, required=(), read=False):
    return {"name": name, "description": description,
            "inputSchema": {"type": "object", "properties": properties or {},
                            "required": list(required), "additionalProperties": False},
            "annotations": {"readOnlyHint": read, "destructiveHint": False,
                            "openWorldHint": False}}


TOOLS = [
    tool("workbench_init", "初始化显式工作目录；运行数据保存在产品目录之外。"),
    tool("taxonomy_get", "读取经营场景、方法类别、管理层级的分类定义。", {"path": S}, read=True),
    tool("knowledge_import", "导入通用 JSON 知识包或带 SHA256 的旧私有导出目录；同 ID 冲突拒绝覆盖。", {"path": S}, ["path"]),
    tool("knowledge_list", "按场景、方法类别、管理层级列出本地知识元数据。", {"scenario_id": S, "method_type_id": S, "management_level": S}, read=True),
    tool("knowledge_search", "词项检索；返回分数和命中依据，非向量语义搜索。", {"query": S, "limit": {"type": "integer", "minimum": 1, "maximum": 100}, "scenario_id": S, "method_type_id": S, "management_level": S}, ["query"], True),
    tool("knowledge_get", "读取完整知识记录，不裁剪图形关系或正文。", {"id": S}, ["id"], True),
    tool("case_create", "创建一个归因案例。", {"title": S}, ["title"]),
    tool("case_list", "列出本地案例。", read=True),
    tool("case_get", "读取案例状态、全部消息、来源元数据及历次状态。", {"case_id": S}, ["case_id"], True),
    tool("message_append", "追加原始用户或 Agent 消息。消息不能被修改，Agent 消息不能作业务证据。", {"case_id": S, "role": {"enum": ["user", "assistant"]}, "text": S}, ["case_id", "role", "text"]),
    tool("source_add", "保存一个明确指定的本地文件或文本；二进制仅保存原件并标记待解析。", {"case_id": S, "path": S, "text": S, "title": S, "derived_from": S}, ["case_id"]),
    tool("source_get", "读取本案例来源的完整文本、原件位置和来源链。", {"case_id": S, "source_id": S}, ["case_id", "source_id"], True),
    tool("state_update", "乐观锁更新案例状态；旧对象ID、text及引用不可删除或改写。修订时新增ID并将旧项标为superseded，保留旧证据与反证。", {"case_id": S, "expected_revision": {"type": "integer", "minimum": 0}, "state": {"type": "object"}, "note": S}, ["case_id", "expected_revision", "state"]),
    tool("context_assemble", "按字符预算组合完整状态、方法、消息和来源；逐项列出遗漏，不静默裁剪。", {"case_id": S, "budget_chars": {"type": "integer", "minimum": 1000, "maximum": 200000}, "method_ids": STRINGS, "source_ids": STRINGS, "library_ids": STRINGS}, ["case_id"], True),
    tool("case_export", "导出完整 JSON 或 Markdown 内容；不自动写入任意路径。", {"case_id": S, "format": {"enum": ["json", "markdown"]}}, ["case_id"], True),
    tool("source_promote", "明确授权一个来源作为长期资料；不自动使其成为其他案例的事实。", {"case_id": S, "source_id": S}, ["case_id", "source_id"]),
    tool("library_search", "仅检索已主动加入长期资料的文本；跨案例引用需另行核验。", {"query": S, "limit": {"type": "integer", "minimum": 1, "maximum": 100}}, ["query"], True),
]

BY_NAME = {t["name"]: t for t in TOOLS}
