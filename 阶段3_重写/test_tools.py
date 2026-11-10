"""阶段 3 · tools.py 的验收测试。标准库就够，不联网、不花钱、不装包。

PyCharm：右键本文件 → Run 'Unittests in test_tools'
命令行： cd 阶段3_重写 ; python -m unittest test_tools -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tools import ToolRegistry


def make_registry() -> ToolRegistry:
    """造一个注册了两个工具的注册表，给各测试共用。"""
    reg = ToolRegistry()

    @reg.tool("把两个整数相加。", params={"a": "第一个加数", "b": "第二个加数"})
    def add(a: int, b: int) -> int:
        return a + b

    @reg.tool("打个招呼。", params={"name": "对方的名字"})
    def hello(name: str = "同学") -> str:
        return f"你好，{name}"

    return reg


class TestRegister(unittest.TestCase):
    def test_decorator_registers_function(self):
        reg = make_registry()
        self.assertIn("add", reg.tools)
        self.assertEqual(reg.tools["add"].description, "把两个整数相加。")
        self.assertEqual(reg.tools["hello"].description, "打个招呼。")

    def test_decorator_returns_original_function(self):
        """装饰器不能"吃掉"原函数，被装饰后还应该能直接调用。"""
        reg = ToolRegistry()

        @reg.tool("返回固定文字。")
        def ping() -> str:
            return "pong"

        self.assertEqual(ping(), "pong")

    def test_schema_shape(self):
        schema = make_registry().tools["add"].schema()
        self.assertEqual(schema["type"], "function")
        self.assertEqual(schema["function"]["name"], "add")
        self.assertEqual(schema["function"]["description"], "把两个整数相加。")
        params = schema["function"]["parameters"]
        self.assertEqual(params["type"], "object")

    def test_required_only_for_params_without_default(self):
        params = make_registry().tools["add"].schema()["function"]["parameters"]
        self.assertEqual(sorted(params["required"]), ["a", "b"])

    def test_param_with_default_is_not_required(self):
        params = make_registry().tools["hello"].schema()["function"]["parameters"]
        self.assertEqual(params["required"], [])

    def test_types_and_descriptions_are_mapped(self):
        props = make_registry().tools["add"].schema()["function"]["parameters"]["properties"]
        self.assertEqual(props["a"]["type"], "integer")
        self.assertEqual(props["b"]["type"], "integer")
        self.assertEqual(props["a"]["description"], "第一个加数")

    def test_schemas_lists_every_tool(self):
        names = [s["function"]["name"] for s in make_registry().schemas()]
        self.assertEqual(sorted(names), ["add", "hello"])

    def test_empty_registry_has_empty_schemas(self):
        self.assertEqual(ToolRegistry().schemas(), [])


class TestExecute(unittest.TestCase):
    def test_executes_with_json_string(self):
        self.assertEqual(make_registry().execute("add", '{"a": 2, "b": 3}'), "5")

    def test_executes_with_dict(self):
        self.assertEqual(make_registry().execute("add", {"a": 2, "b": 3}), "5")

    def test_string_result_is_returned_as_is(self):
        self.assertEqual(make_registry().execute("hello", '{"name": "小明"}'), "你好，小明")

    def test_unknown_tool_returns_error_string(self):
        result = make_registry().execute("nope", "{}")
        self.assertTrue(result.startswith("错误"), msg="错误要以字符串返回，不能抛异常")
        self.assertIn("nope", result)

    def test_bad_json_returns_error_string(self):
        result = make_registry().execute("add", "{这不是 JSON")
        self.assertTrue(result.startswith("错误"))
        self.assertIn("JSON", result)

    def test_wrong_arguments_return_error_string(self):
        result = make_registry().execute("add", '{"x": 1}')
        self.assertTrue(result.startswith("错误"))
        self.assertIn("参数", result)

    def test_exception_from_tool_becomes_error_string(self):
        reg = ToolRegistry()

        @reg.tool("总是失败。")
        def boom() -> str:
            raise ValueError("炸了")

        self.assertEqual(reg.execute("boom", "{}"), "错误：炸了")


if __name__ == "__main__":
    unittest.main(verbosity=2)
