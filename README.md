# PythonProject —— 跟着 StudyMate 手册学 Python

学习方式：**参考实现驱动 + 红绿循环**（见 [学习方法.md](学习方法.md)）。
参照项目：`C:\Users\sunzi\Desktop\studymate`（《Python × Agent 项目式学习手册》配套代码，不在本仓库内）。

每个阶段都遵守同一条流程：**划最小范围 → 给骨架 → 写验收测试（先在参考实现上跑绿）→ 一次填一个函数 → 全绿后审查 → 回答 3 个原理问题**。

## 现在到哪了

| 阶段 | 内容 | 状态 | 验收 |
|---|---|---|---|
| 1 | 任务数据层：dataclass、自定义异常、JSON 持久化、排序/筛选 | ✅ **结业** | 29/29 测试绿，`__main__` 自测跑通 |
| 2 | 配置 + 模型客户端：`.env` 解析、Config、FakeClient、create_client | ✅ **结业** | 21/21 测试绿；`main.py` 真机调用 DeepSeek 通过 |
| 3 | 工具注册表 + agent 循环 | ⬜ 未开始 | — |
| 4 | 单元测试与工程化 | ⬜ 未开始 | — |
| 5 | 笔记检索（简易 RAG） | ⬜ 未开始 | — |
| 6 | MCP 服务器 | ⬜ 未开始 | — |

## 目录地图

```
PythonProject/
├── main.py                 ← 成品入口：真实模型调用（阶段 2 验收要改它）
├── README.md               ← 本文件：项目地图
├── 学习方法.md              ← 固定学习流程，每次开工前看一眼
├── 交接文档.md              ← 换新对话/换 AI 时，先给它看这个（进度、下一步、偏好）
├── learning-skill/          ← 学习法的可移植成品（给 Claude/ChatGPT 等用的 skill）
├── 速查/                    ← 实验脚本、速查表、笔记（**不进阶段目录**）
│   ├── 基础语法卡点.md        self / dataclass / 装饰器 / 魔法方法 等 14 条
│   ├── 英文命名对照.md        英文变量名/缩写的中文意思（看不懂名字先查这里）
│   ├── 字符串与路径速查表.md   不懂某个方法先看这张表
│   └── 实验_方法速查.py       想确认某个行为时才跑它
│
├── 阶段1_重写/              ← ✅ 结业
│   ├── task.py             你的实现（Task / TaskStore / parse_due）
│   ├── test_task.py        29 个验收测试
│   ├── 说明_为什么.md       15 节"为什么" + C 对照表
│   └── 结构总览.md          类/方法/import/装饰器/调用关系全景图
│
├── 阶段2_重写/              ← 🚧 进行中
│   ├── llm_config.py       你的实现（.env / Config / FakeClient / create_client 合在一个文件）
│   ├── test_llm_config.py  21 个验收测试
│   ├── 说明_为什么.md       12 节"为什么" + 4 个坑
│   └── 结构总览.md          类/方法/import/装饰器/调用关系全景图
│
└── 草稿/                    ← 归档区：练过的、练废的，只挪不删
    ├── tasks.py            474 行的手册 v2 版（无持久化，已被阶段 1 超越）
    ├── 参考task.py         最早的 JSON 持久化尝试（有 6 处语法错误，PyCharm 标红属正常）
    ├── register.py         阶段 3 的早期练习（工具注册表）
    └── tools.py            阶段 3 的早期练习（add / multiply）
```

## 四条规矩

1. **根目录只放"成品"和"索引"**：`main.py`、`README.md`、`学习方法.md`、`learning-skill/`。学习代码一律进 `阶段N_` 目录。
2. **每个 `阶段N_` 目录自包含**：自己的实现 + 自己的测试 + 自己的说明，**不跨目录 import**。这样任何一阶段都能单独跑、单独删。
3. **草稿区只进不出**：不确定的先挪进 `草稿/`，确认没用了再删（有 `.git`，挪动留痕，比直接删安全）。
4. **阶段目录里只放四件套**：`你的实现` + `test_xxx.py` + `说明_为什么.md` + `结构总览.md`。实验脚本、方法速查、临时笔记一律放根目录的 `速查/`——否则下次打开阶段目录会分不清哪个文件该填、哪个是辅助资料。

## 怎么跑（PyCharm）

1. 解释器：`Settings → Project: PythonProject → Python Interpreter` → `.venv\Scripts\python.exe`
2. 跑某阶段测试：右键该阶段的 `test_xxx.py` → `Run 'Unittests in test_xxx'`
3. 看自测输出：右键 `task.py` / `llm_config.py` → `Run 'task'` / `Run 'llm_config'`

> ⚠️ **别点基类**：`阶段1_重写` 里的 `StoreTest`、`阶段2_重写` 里的 `Base` 都只有 0 个测试，点了会显示"没有发现测试"。要跑就点具体子类，或者点整个文件。

## 两个环境坑（都踩过）

| 现象 | 原因 | 解法 |
|---|---|---|
| `UnicodeEncodeError: 'gbk' codec can't encode '\u2713'` | cmd/PowerShell 默认 GBK，编不了 `✓`/`✔` | PyCharm 的 Run 窗口是 UTF-8，直接用；命令行加 `$env:PYTHONIOENCODING='utf-8'` |
| `ModuleNotFoundError: No module named 'llm_config'` | 中文目录名不能当 Python 包 import | 在调用方加 `sys.path.insert(0, str(Path(__file__).parent / "阶段2_重写"))` |

## 参考代码映射（studymate → 本仓库）

| 阶段 | studymate 里的文件 | 本仓库 |
|---|---|---|
| 1 | `studymate/tasks.py`（159 行） | `阶段1_重写/task.py` |
| 2 | `studymate/config.py` + `llm.py`（189 行） | `阶段2_重写/llm_config.py`（合并成一个文件） |
| 3 | `studymate/tools.py` + `study_tools.py` + `agent.py` | 待建 |
| 4 | `tests/test_studymate.py` | 待建 |
| 5 | `studymate/notes.py` + `notes/` | 待建 |
| 6 | `studymate/mcp_server.py` | 待建 |
