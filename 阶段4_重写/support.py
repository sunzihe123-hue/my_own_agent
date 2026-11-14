"""阶段 4 · 测试支撑（support = 支撑材料，测试用的"脚手架部件"）。

阶段 4 换了个视角：不再写业务代码，而是给已经写好的代码**装上自动化验证**。

  - 测试（test）= 自动的验收：不用人眼看输出，点一下 Run 就知道对没对
  - 日志（log）  = 自动的记录：不用 print，事后还能查"当时到底发生了什么"

测试层（test layer）天然是横切的（cross-cutting）：它不生产业务代码，只检查别人写的代码。
所以本文件破一次例：用 sys.path 把 `阶段3_重写` 加进模块搜索路径。
（中文目录名不能当 Python 包 import，只能这么绕——见 交接文档 §6。）

本文件三件东西：
  1. TmpDirTest     测试基类：每个测试一个干净的临时目录，跑完自动删
  2. FakeToolClient 假的大模型客户端：形状和真 SDK 一样，离线、不花钱
  3. capture_logs   日志重定向（capture = 捕获）：把日志引到文件里，测试才能"读日志"

写作顺序（每完成一步就 Run 一次测试，先拿"最小绿"）：
  第 1 步  build_registry（fixture = 测试用的固定数据）
  第 2 步  test_tools.py 的四条断言        → 4/6 绿
  第 3 步  TmpDirTest + FakeToolClient（给日志测试备料）
  第 4 步  capture_logs + agent.py 三处日志
  第 5 步  test_agent_log.py 的两条断言      → 6/6 绿
"""

from __future__ import annotations

import logging
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

# 把 阶段3_重写 目录加进 sys.path：之后 `import tools` / `import agent` 才能找到它们。
# 注意：必须在 import tools / agent **之前**执行（所以这段代码写在这里，不在函数里）。
PHASE3_DIR = Path(__file__).resolve().parent.parent / "阶段3_重写"
if str(PHASE3_DIR) not in sys.path:
    sys.path.insert(0, str(PHASE3_DIR))

from tools import ToolRegistry  # noqa: E402 —— 必须在 sys.path 插入之后 import


# ---------------------------------------------------------------------------
# 1. 测试基类：临时目录
# ---------------------------------------------------------------------------


class TmpDirTest(unittest.TestCase):
    """带临时目录的测试基类（base = 基类 / 父类）。

    子类只要继承它，就自动拥有 `self.dir` —— 一个空目录，跑完自动删。
    为什么必须用临时目录：测试产生的文件绝不能写进项目里（会留垃圾、会互相污染、
    甚至可能把真实数据写坏）。测试要"可重复、互不影响、不留痕迹"，靠的就是这个。

    参考写法：阶段1_重写/test_task.py 的 StoreTest、阶段2_重写/test_llm_config.py 的 Base。
    """

    def setUp(self) -> None:
        """TODO 第 3 步（2 行）：建临时目录。

        要用的东西：tempfile.TemporaryDirectory()，它的 .name 是目录路径字符串。
        要存两样：
          - 把 **TemporaryDirectory 对象**存进 self（例如 self._tmp）——对象活着，目录才存在
          - 把 Path(那个 .name) 存成 self.dir —— 后面拼文件路径用
        为什么两样都存：对象被回收时目录会被自动删掉，所以 tearDown 也要靠它来清理。
        """
        raise NotImplementedError("TODO 第 3 步：TmpDirTest.setUp")

    def tearDown(self) -> None:
        """TODO 第 3 步（1 行）：清理临时目录（调用 TemporaryDirectory 的 cleanup()）。"""
        raise NotImplementedError("TODO 第 3 步：TmpDirTest.tearDown")


# ---------------------------------------------------------------------------
# 2. 测试数据：两个示例工具
# ---------------------------------------------------------------------------


def build_registry() -> ToolRegistry:
    """TODO 第 1 步：造一个注册了 add / hello 的注册表（fixture = 夹具 = 测试用的固定数据）。

    要求（测试里的断言依赖这些字符串，别自己改）：
      - add(a: int, b: int) -> int，返回 a + b
        工具描述 "把两个整数相加。"，参数说明 {"a": "第一个加数", "b": "第二个加数"}
      - hello(name: str = "同学") -> str，返回 f"你好，{name}"
        工具描述 "打个招呼。"，参数说明 {"name": "对方的名字"}

    提示：阶段3_重写/test_tools.py 里有个一模一样的 make_registry()，照它写。
          —— 这是"复习"，不是新知识。
    """
    raise NotImplementedError("TODO 第 1 步：build_registry")


# ---------------------------------------------------------------------------
# 3. 两个小工具：捏"模型回复"的形状（真 SDK 里就长这样）
# ---------------------------------------------------------------------------


def tool_call(call_id: str, name: str, arguments: str) -> SimpleNamespace:
    """捏一个工具调用（已给，不用改）：.id / .function.name / .function.arguments。"""
    return SimpleNamespace(id=call_id, function=SimpleNamespace(name=name, arguments=arguments))


def model_msg(content: str | None = None, calls: list | None = None) -> SimpleNamespace:
    """捏一条模型回复（已给）：.content 是文本，.tool_calls 是工具调用列表（可能为 None）。"""
    return SimpleNamespace(content=content, tool_calls=calls)


# ---------------------------------------------------------------------------
# 4. 假客户端
# ---------------------------------------------------------------------------


class FakeToolClient:
    """假的大模型客户端（fake = 假的）：照剧本说话，不发网络请求。

    它必须长得和真 SDK 一样：
        client.chat.completions.create(model=..., messages=..., tools=...)
        → 返回值 .choices[0].message，message 上有 .content 和 .tool_calls
    Agent 的代码是照着真 SDK 写的，替身也得照这个"插头形状"做 ——
    插头不匹配，就不是"离线验证真代码"，而是"验证一个假的代码"。

    剧本（script）= 每次请求依次返回的模型回复；calls = 每次请求的记录，供断言。
    """

    def __init__(self, script: list):
        """TODO 第 3 步（3 行）：存剧本、存 calls、把 create 指向自己的 _create。

        要做的事：
          1. self.script = list(script)   ← 复制一份，_create 里会用 pop 消耗
          2. self.calls = []              ← 每次请求都记一笔
          3. 造 self.chat，使 self.chat.completions.create 等价于 self._create
             提示：用 SimpleNamespace 层层套（chat → completions → create）。
        """
        raise NotImplementedError("TODO 第 3 步：FakeToolClient.__init__")

    def _create(self, model, messages, tools=None, **kwargs):
        """TODO 第 3 步（3 行）：记一笔请求，从剧本弹出一条回复，包成真 SDK 的形状。

        1. self.calls.append({...})：记 model / messages / tools
           messages 要**复制**成普通 dict 列表（[dict(m) for m in messages]）——
           不然之后 agent 改历史，你记录下来的那份也跟着变，断言就没意义了。
        2. message = self.script.pop(0)      ← 按顺序取剧本
        3. 返回 SimpleNamespace(choices=[SimpleNamespace(message=message)])
        """
        raise NotImplementedError("TODO 第 3 步：FakeToolClient._create")


# ---------------------------------------------------------------------------
# 5. 日志重定向
# ---------------------------------------------------------------------------


class capture_logs:
    """日志重定向（capture = 捕获）：with 块里产生的日志，全部写进指定文件。

    用法：
        with capture_logs(self.dir / "agent.log") as log_path:
            agent.chat("算一下")
        text = log_path.read_text(encoding="utf-8")    # 日志全文，随便断言

    为什么要它：日志默认写向屏幕（stderr = 标准错误流）；测试要能"读"日志，
    就得临时换个出口。logging 里"往哪里写"由 Handler（处理器）决定 ——
    换 Handler 就是换出口，业务代码里所有 log.info 一行都不用改。这就是日志比 print 强的地方。

    C 类比：这是 RAII —— __init__ 准备资源，__exit__ 释放；
    即使 with 块里抛异常，__exit__ 也一定会执行（print 调试做不到）。
    """

    def __init__(self, path: Path, level: int = logging.DEBUG):
        """TODO 第 4 步（4 行）：准备文件处理器 + 根日志器 + 记住旧级别。

        要做的事：
          1. self.path = Path(path)
          2. self.handler = logging.FileHandler(self.path, encoding="utf-8")
             ← encoding 必须显式写 utf-8：日志内容是中文，用 Windows 默认编码写会乱码。
             再给 handler 设个格式（可选但推荐）：logging.Formatter("%(levelname)s %(name)s %(message)s")
          3. self.root = logging.getLogger()   ← 根日志器（root logger）：所有 log 默认向上冒泡到这里
          4. self.old_level = self.root.level  ← 记下旧级别，__exit__ 要还回去
        """
        raise NotImplementedError("TODO 第 4 步：capture_logs.__init__")

    def __enter__(self) -> Path:
        """TODO 第 4 步（2 行）：把 handler 挂到根日志器上、把根日志器级别调到 level。

        然后 return self.path（with ... as log_path 拿到的就是它）。
        """
        raise NotImplementedError("TODO 第 4 步：capture_logs.__enter__")

    def __exit__(self, *exc_info) -> None:
        """TODO 第 4 步（2~3 行）：摘掉 handler + 关闭它 + 恢复根日志器级别。

        为什么必须 close()：FileHandler 带缓冲区，不关的话最后几行日志可能还没落盘，
        你读文件就会读到空内容（本阶段最容易踩的坑）。
        为什么必须恢复 level：否则会污染后面所有测试 —— 测试之间绝不能有顺序依赖。
        """
        raise NotImplementedError("TODO 第 4 步：capture_logs.__exit__")
