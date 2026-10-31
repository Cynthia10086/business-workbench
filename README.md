# 经营工作台与经营 Skill

把经营现象、方法知识、现场证据和验证行动连接起来。产品使用本地 Agent 的推理能力，不内置模型接口，不需要云端账号。

仓库只有两份产品及必要说明：

| 产品 | 入口 | 用途 |
| --- | --- | --- |
| 本地 Agent 工作台 | `workbench/` | CLI、MCP 和本地页面共用知识、案例、来源与版本记录 |
| 通用经营 Skill | `skills/business-reasoning/` | 按业务场景选择方法、比较解释与反证、持续修订判断 |

## 快速使用

需要 Python 3.10 或以上，无运行时第三方依赖。在仓库目录执行：

```sh
python3 workbench/cli.py --workspace ../business-data workbench_init
python3 workbench/cli.py --workspace ../business-data knowledge_import \
  --payload '{"path":"skills/business-reasoning/examples/knowledge.json"}'
python3 workbench/serve.py --workspace ../business-data --port 8770
```

打开终端给出的回环地址。页面支持案例记录、来源查看、方法分类和导出；分析由正在使用的 Agent 完成。示例知识是通用方法说明，不是实际业务证据。

工作目录必须在产品目录之外。迁移时分别带走代码与工作目录；导出单个案例可使用 JSON 或 Markdown。公开代码不包含使用者自己的知识资料或案例数据。

## 让 Agent 操作

直接在 Agent 中打开此项目，让它读取 `AGENTS.md`；也可以调用：

```sh
python3 workbench/cli.py tools-list
python3 workbench/cli.py --workspace ../business-data knowledge_search \
  --payload '{"query":"销售下降"}'
```

支持 MCP 的宿主可配置 stdio 启动命令：

```json
{
  "command": "python3",
  "args": ["/path/to/product/workbench/mcp_server.py", "--workspace", "/path/to/business-data"]
}
```

这里的 `/path/to/` 是示意占位，需替换为实际路径。MCP、CLI 与页面使用相同运行时和校验规则。工具清单、文件与案例操作见 [工作台说明](workbench/README.md)。

## 通用 Skill

将 `skills/business-reasoning/` 整个目录复制到宿主支持的 Skill 目录。没有 Skill 加载器时，也可以直接让 Agent 读取其中的 `SKILL.md`。

> 使用 business-reasoning，基于我提供的资料分析这个经营现象。比较可能解释与反证，提出下一步验证，并保留前后判断的变化。

Skill 可以独立使用。文件检索、持久化和工具调用取决于宿主实际能力；没有工具时输出可保存的结构，不假装已经写入本地。

分类支持三条路径：

- **业务场景**：策略定位、增长漏斗、商品库存、渠道网络、门店执行、客户会员、组织协同、区域诊断、损益资源配置、指标复盘。
- **分析方法**：指标拆解、分群对照、流程触点、组合优先级、竞争假设、单位经济等。
- **管理层级**：门店、区域、总部与中台。

同一条知识可以多选。分类用于导航，不证明方法适用于每个业务问题；需要结合数据口径、适用条件与来源限制。

## 数据原则

原始消息和材料保留；状态更新带版本；方法不能替代业务证据；助手历史回答不能自动变成事实；撤回反证需要说明理由。上下文采用预算控制并列出遗漏，不默默截断正文或图形关系。

知识检索是本地词项检索，不是向量检索或自动因果发现。PDF、PPT 与图片可以登记原件，但解析和原图核验需要宿主工具；未解析资料不能声称已经阅读。

## 验证

```sh
python3 -m unittest discover -s workbench/tests -v
```

MIT 许可适用于产品代码和自行编写的示例。使用者导入的材料保留各自的权利与使用范围。
