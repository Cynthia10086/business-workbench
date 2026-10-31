# 本地 Agent 工作台

Python 标准库运行时，支持命令行、MCP stdio 与可选的回环网页。三种入口调用同一份知识与案例结构，没有内置模型连接。

## 操作契约

```sh
python3 workbench/cli.py tools-list
```

返回所有工具的 `inputSchema`、用途和只读提示。调用方式：

```sh
python3 workbench/cli.py --workspace ../business-data case_create \
  --payload '{"title":"区域经营变化"}'
```

也可使用 `--payload-file arguments.json`，避免多行 JSON 的 shell 转义。成功返回 `{ok:true,result:...}`；失败返回 `{ok:false,error:{code,message,details}}`，同时使用非零退出码。

| 能力 | 工具 |
| --- | --- |
| 初始化与分类 | `workbench_init`、`taxonomy_get` |
| 知识 | `knowledge_import`、`knowledge_list`、`knowledge_search`、`knowledge_get` |
| 案例 | `case_create`、`case_list`、`case_get` |
| 消息与资料 | `message_append`、`source_add`、`source_get` |
| 归因状态与上下文 | `state_update`、`context_assemble` |
| 复用与导出 | `source_promote`、`library_search`、`case_export` |

状态字段以 [schemas/state.schema.json](schemas/state.schema.json) 为准。先取得当前版本和真实来源 ID，再提交更新。不能直接引用另一个案例的材料作为当前事实。

`source_add` 可接收明确指定的文件 `path`，或 `text` 与 `title`。二进制原件保留为待解析；宿主解析后，通过 `derived_from` 关联派生文本，保留同源关系。只有主动调用 `source_promote` 才允许跨案例资料检索。

## 知识格式

一个 JSON 数组，或含 `records` 数组的对象。每条记录包含：

```json
{
  "id": "METHOD:sample",
  "title": "示例方法",
  "body": "完整正文或结构化 JSON",
  "source": {"document": "来源名称", "page_numbers": []},
  "family_ids": ["source-family"],
  "limitations": ["适用边界"],
  "scenario_ids": ["regional-diagnosis"],
  "method_type_ids": ["segmentation-comparison"],
  "management_levels": ["region"]
}
```

导入使用 `knowledge_import` 的 `path`。同 ID、同内容可重复导入；不同内容冲突会被拒绝，应使用有版本的新 ID。兼容带 SHA-256 的 `manifest.json + index.json + records/` 导出目录，校验后才写入。

知识分类和场景说明来自 `skills/business-reasoning/references/taxonomy.json`。分类标签可交叉，未知适用性应保留待核状态。

## MCP

启动 `python3 workbench/mcp_server.py --workspace <外部工作目录>`，由宿主接管标准输入输出。支持 JSON-RPC 初始化、工具发现和工具调用；标准输出只写协议消息。不要把网页服务器配置成 MCP 启动命令。

## 本地页面

```sh
python3 workbench/serve.py --workspace ../business-data --port 8770
```

仅绑定 `127.0.0.1`。网页使用会话令牌与同源请求；不向互联网开放。页面不支持任意本地路径导入，文件访问由 Agent 的 CLI / MCP 按用户授权执行。

## 保存与迁移

工作目录包含 SQLite 数据库及 `originals/`。停止写入进程后复制整个工作目录，可保留知识、案例、来源和历史版本。单案例导出供查阅与归档；它不替代完整工作目录备份。仓库只保存程序和通用说明。
