"""阶段 4 · test_agent_log.py：验证 agent.py 的日志。

日志最容易被当成"顺手 print 一下"，所以这里把它当**输出**来测：
把日志重定向到临时文件，再像断言返回值一样断言日志内容。

剧本（script = 剧本，FakeToolClient 用的固定台词）：
  第 1 次请求 → 模型要求调用 add({"a": 2, "b": 3})
  第 2 次请求 → 模型给出最终回答

PyCharm：右键本文件 → Run 'Unittests in test_agent_log'
命令行： cd 阶段4_重写 ; python -m unittest test_agent_log -v
"""

import unittest

# 先 import support：它会先把 阶段3_重写 加进 sys.path，之后才能 import agent。
from support import FakeToolClient, TmpDirTest, build_registry, capture_logs, model_msg, tool_call
from agent import Agent


class TestAgentLogs(TmpDirTest):
    """继承 TmpDirTest：每个测试一个临时目录，日志文件写在里面，跑完自动删。"""

    def test_agent_logs_tool_call(self):
        """要验证什么：模型要求调工具时，日志里能读到 **工具名** 和 **参数**。

        步骤：
          1. 造剧本（两条，都是"模型回复"）：
             第 1 条 = 要求调工具 → model_msg(calls=[tool_call("call_1", "add", '{"a": 2, "b": 3}')])
             第 2 条 = 纯文本回答 → model_msg(content="都算完了")
             （注意：tool_call 要**放进** model_msg 的 calls 里，它不是一条消息）
          2. client = FakeToolClient(剧本)
          3. agent = Agent(client, "fake-model", build_registry())
          4. with capture_logs(self.dir / "agent.log") as log_path:
                 agent.chat("算一下")
          5. text = log_path.read_text(encoding="utf-8")     ← 日志全文

        断言：日志全文里同时出现 "add" 和参数原文 '{"a": 2, "b": 3}'。
        为什么两个都要断：只断 "add" 的话，"参数忘了记"这个 bug 逃得掉。
        """
        raise NotImplementedError("TODO 第 5 条：test_agent_logs_tool_call")

    def test_agent_logs_tool_result(self):
        """要验证什么：工具执行完，日志里能读到**工具返回的结果**（add(2, 3) → 5）。

        剧本同上；断言：日志全文里有 "5"。
        为什么这里只断 "5"：参数的原文是 '{"a": 2, "b": 3}'，里面没有 5 ——
        所以"5"只可能来自工具结果。好测试的标准：断言的东西只可能出现在"该出现"的那一处。
        （反过来：别拿 "2"/"3" 当断言，它们在参数里也出现，分不清是参数还是结果。）
        """
        raise NotImplementedError("TODO 第 6 条：test_agent_logs_tool_result")


if __name__ == "__main__":
    unittest.main(verbosity=2)
