# 与本地工作台协作

本 Skill 可以独立运行。只有使用者已经选择本地工作台，并且宿主 Agent 具有相应工具时，才调用它。所有路径和资料由使用者的环境决定；Skill 不内置账号、云端地址或模型接口。

## 发现工具

在工作台产品根目录运行：

```sh
python3 workbench/cli.py tools-list
```

查看该工作台实际返回的名称、参数和说明；后续操作按返回的契约组织 JSON。CLI 使用 `--workspace` 指定独立数据目录，通过 `--payload-file` 传入操作参数文件，避免复杂文本的命令行转义。可以直接使用 `case_create --payload '{"title":"区域经营变化"}'` 创建空白案例。

具备 MCP 的宿主可以以 stdio 方式启动 `workbench/mcp_server.py`，向它传入同一个工作区。连接参数由宿主配置决定；不要把配置成功描述为模型推理或材料解析成功。

```text
程序：python3
参数：workbench/mcp_server.py --workspace <数据工作区绝对路径>
工作目录：本地工作台产品根目录
```

路径示例是占位说明，实际执行时使用用户环境里的真实目录。案例、附件和导入知识放在产品代码目录之外，便于独立备份和迁移。

## 工具与目的

| 目的 | 工具 |
| --- | --- |
| 初始化独立工作区、读取分类 | `workbench_init`、`taxonomy_get` |
| 导入、检索与读取方法 | `knowledge_import`、`knowledge_search`、`knowledge_get`、`knowledge_list` |
| 建立或续接案例 | `case_create`、`case_list`、`case_get` |
| 追加真实消息与材料 | `message_append`、`source_add`、`source_get` |
| 读取当前分析上下文 | `context_assemble` |
| 保存判断变化与行动 | `state_update` |
| 导出案例 | `case_export` |
| 将选定来源纳入长期复用、检索长期资料 | `source_promote`、`library_search` |

首次保存当前用户消息后，保留返回的消息 ID。事实引用只使用真实用户消息或已解析来源的逐字片段，不把自行生成的总结当作用户原话追加。材料未解析时保留原件登记，不称已读。

## 一次持续分析

1. 用 `case_get` 读取案例、消息、来源及当前版本。新问题确需独立分析时再创建案例。
2. 追加本轮用户提供的消息或材料；同源提取和原件保持家族关系。补充的方法由知识检索获取。
3. 使用 `context_assemble` 获取本轮上下文，检查截断或缺失提示。未读完整的方法不得宣称已核对。
4. 宿主 Agent 生成分析。将事实、假设、反证、缺口和行动组织为 [state.schema.json](state.schema.json)。
5. 按工具契约携带预期版本调用 `state_update`。旧项的 ID、`text` 和已有引用不可删除或改写；修订主张时新增 ID，并将旧项标记为 `superseded`。这也适用于旧的缺口、行动和决定。发生版本冲突就重新读取合并；保存失败时明确告知，不能声称已记住。
6. 记录回答与判断变化；按需调用 `case_export`。只有用户选择复用的资料才纳入长期库，复用权限不等于内容经过验证。

工具负责结构、检索与保存，Agent 负责解释与判断。工作台输出不能替代来源核对，安装 Skill 也不会自动提供持久服务、后台通知或跨平台记忆。
