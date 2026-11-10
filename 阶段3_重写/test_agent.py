"""阶段 3 · agent.py 的验收测试。标准库就够，不联网、不花钱、不装包。

PyCharm：右键本文件 → Run 'Unittests in test_agent'
命令行： cd 阶段3_重写 ; python -m unittest test_agent -v

这里的假客户端是"能假装要工具"的：剧本里可以写纯文本，也可以写 tool_calls。
"""

import sys
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent))

from agent import Agent
from tools import ToolRegistry


# ---------------------------------------------------------------------------
# 测试替身：一个只会照剧本说话的假客户端（形状和真 SDK 一致）
# ---------------------------------------------------------------------------


def _tool_call(call_id: str, name: str, arguments: str):
    """捏一个 tool_call：真 SDK 里是 .id / .function.name / .function.arguments。"""
    return SimpleNamespace(id=call_id, function=SimpleNamespace(name=name, arguments=arguments))


def _msg(content=None, tool_calls=None):
    """捏一条模型回复：.content 是文本，.tool_calls 是工具调用列表（可能为 None）。"""
    return SimpleNamespace(content=content, tool_calls=tool_calls)


class FakeToolClient:
    def __init__(self, script):
        self.script = list(script)
        self.calls = []  # 记录每次请求，供断言
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, model, messages, tools=None, **kwargs):
        self.calls.append(
            {
                "model": model,
                "messages": [dict(m) for m in messages],
                "tools": tools,
            }
        )
        return SimpleNamespace(choices=[SimpleNamespace(message=self.script.pop(0))])


def make_registry():
    """注册一个 add 工具，并返回一个列表用于记录它被执行了几次。"""
    reg = ToolRegistry()
    executed = []

    @reg.tool("把两个数相加。", params={"a": "加数", "b": "加数"})
    def add(a: int, b: int) -> int:
        executed.append((a, b))
        return a + b

    return reg, executed


class TestAgentSetup(unittest.TestCase):
    def test_system_prompt_is_first_message(self):
        agent = Agent(FakeToolClient([]), "fake-model", make_registry()[0])
        self.assertEqual(agent.messages[0]["role"], "system")
        self.assertIn("StudyMate", agent.messages[0]["content"])

    def test_system_prompt_contains_today(self):
        agent = Agent(FakeToolClient([]), "fake-model", make_registry()[0])
        self.assertIn(date.today().isoformat(), agent.messages[0]["content"])

    def test_call_model_returns_message(self):
        client = FakeToolClient([_msg(content="第一句")])
        agent = Agent(client, "fake-model", make_registry()[0])
        self.assertEqual(agent._call_model().content, "第一句")

    def test_tool_schemas_are_sent_to_model(self):
        reg, _ = make_registry()
        client = FakeToolClient([_msg(content="好")])
        Agent(client, "fake-model", reg)._call_model()
        self.assertEqual(client.calls[0]["tools"], reg.schemas())

    def test_empty_registry_sends_none(self):
        client = FakeToolClient([_msg(content="好")])
        Agent(client, "fake-model", ToolRegistry())._call_model()
        self.assertIsNone(client.calls[0]["tools"])


class TestAgentLoop(unittest.TestCase):
    def test_direct_answer_needs_no_tool(self):
        client = FakeToolClient([_msg(content="你好")])
        agent = Agent(client, "fake-model", make_registry()[0])
        self.assertEqual(agent.chat("hi"), "你好")
        self.assertEqual(len(client.calls), 1)

    def test_answer_is_recorded_in_history(self):
        client = FakeToolClient([_msg(content="你好")])
        agent = Agent(client, "fake-model", make_registry()[0])
        agent.chat("hi")
        self.assertEqual(agent.messages[-1], {"role": "assistant", "content": "你好"})

    def test_tool_call_is_executed(self):
        reg, executed = make_registry()
        client = FakeToolClient(
            [
                _msg(tool_calls=[_tool_call("call_1", "add", '{"a": 2, "b": 3}')]),
                _msg(content="2+3=5"),
            ]
        )
        agent = Agent(client, "fake-model", reg)
        self.assertEqual(agent.chat("2+3 等于几"), "2+3=5")
        self.assertEqual(executed, [(2, 3)])

    def test_tool_result_is_fed_back_as_tool_message(self):
        reg, _ = make_registry()
        client = FakeToolClient(
            [
                _msg(tool_calls=[_tool_call("call_1", "add", '{"a": 2, "b": 3}')]),
                _msg(content="2+3=5"),
            ]
        )
        Agent(client, "fake-model", reg).chat("算一下")
        second_round = client.calls[1]["messages"]
        tool_messages = [m for m in second_round if m.get("role") == "tool"]
        self.assertEqual(
            tool_messages, [{"role": "tool", "tool_call_id": "call_1", "content": "5"}]
        )

    def test_assistant_tool_calls_are_recorded(self):
        reg, _ = make_registry()
        client = FakeToolClient(
            [
                _msg(tool_calls=[_tool_call("call_1", "add", '{"a": 2, "b": 3}')]),
                _msg(content="2+3=5"),
            ]
        )
        Agent(client, "fake-model", reg).chat("算一下")
        second_round = client.calls[1]["messages"]
        assistant = [m for m in second_round if m.get("role") == "assistant"][-1]
        self.assertEqual(
            assistant["tool_calls"],
            [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "add", "arguments": '{"a": 2, "b": 3}'},
                }
            ],
        )

    def test_two_tool_calls_in_one_round(self):
        reg, executed = make_registry()
        client = FakeToolClient(
            [
                _msg(
                    tool_calls=[
                        _tool_call("c1", "add", '{"a": 1, "b": 2}'),
                        _tool_call("c2", "add", '{"a": 3, "b": 4}'),
                    ]
                ),
                _msg(content="都算完了"),
            ]
        )
        Agent(client, "fake-model", reg).chat("两个加法")
        self.assertEqual(executed, [(1, 2), (3, 4)])
        tool_messages = [m for m in client.calls[1]["messages"] if m.get("role") == "tool"]
        self.assertEqual([m["tool_call_id"] for m in tool_messages], ["c1", "c2"])

    def test_tool_error_is_fed_back_instead_of_crashing(self):
        reg, _ = make_registry()
        client = FakeToolClient(
            [
                _msg(tool_calls=[_tool_call("c1", "不存在的工具", "{}")]),
                _msg(content="抱歉，我刚才用错工具了"),
            ]
        )
        agent = Agent(client, "fake-model", reg)
        self.assertEqual(agent.chat("试试"), "抱歉，我刚才用错工具了")
        tool_messages = [m for m in client.calls[1]["messages"] if m.get("role") == "tool"]
        self.assertTrue(tool_messages[0]["content"].startswith("错误"))

    def test_max_steps_stops_endless_tool_calls(self):
        reg, _ = make_registry()
        script = [
            _msg(tool_calls=[_tool_call(f"c{i}", "add", '{"a": 1, "b": 1}')]) for i in range(4)
        ]
        client = FakeToolClient(script)
        agent = Agent(client, "fake-model", reg, max_steps=3)
        answer = agent.chat("一直调工具")
        self.assertEqual(len(client.calls), 3, msg="最多只应该请求模型 max_steps 次")
        self.assertTrue(isinstance(answer, str) and answer, msg="用完步数要给一句人能读懂的提示")


if __name__ == "__main__":
    unittest.main(verbosity=2)
