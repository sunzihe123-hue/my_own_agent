"""阶段 4 · test_tools.py：给阶段 3 的 tools.py 写一套**独立验收**。

阶段 3 的 15 条测试是教练给的（你读它、把实现填绿）；
这一套 4 条由**你**写：从"读测试"升级成"写测试"。

写测试的三条规矩（阶段 1~3 一直靠它们）：
  1. 一条测试验证一个行为；测试名说人话，能当一句需求读
  2. 断言要"能区分对错"：实现被改坏时，它必须变红（不会红的测试 = 没有测试）
  3. 只断言**必须**成立的事；别断言实现细节，否则以后改实现就得改测试

PyCharm：右键本文件 → Run 'Unittests in test_tools'
命令行： cd 阶段4_重写 ; python -m unittest test_tools -v
"""

import unittest

# 注意 import 顺序：先 import support，它会把 阶段3_重写 加进 sys.path。
from support import build_registry


class TestToolSchema(unittest.TestCase):
    """工具的"说明书"（schema = 结构描述）。模型只靠它判断"这工具叫什么、怎么传参"。"""

    def test_add_tool_schema_required(self):
        """要验证什么：add 的 schema 里，a / b 必填、类型是整数、说明都在。

        从哪拿：build_registry().tools["add"].schema()  ← schema() 返回的是 {"type": "function", "function": {...}}
        断言（3 件事）：
          1. parameters["required"] 排序后 == ["a", "b"]      （required = 必填项清单）
          2. properties["a"]["type"] 和 properties["b"]["type"] == "integer"
          3. properties["a"]["description"] 和 ["b"]["description"] 非空（内容 = build_registry 里写的）
         """
        raise NotImplementedError("TODO 第 1 条：test_add_tool_schema_required")

    def test_hello_schema_has_description(self):
        """要验证什么：hello 的 schema 里，工具描述和参数描述都不能丢。

        断言：function["description"] == "打个招呼。"
              properties["name"]["description"] == "对方的名字"
        为什么单独测它：描述是模型判断"该不该调这个工具"的唯一依据。
        丢一个字段，模型就变成瞎猜 —— 这种错不会报错、也不会崩，最难发现。
        """
        raise NotImplementedError("TODO 第 3 条：test_hello_schema_has_description")


class TestExecute(unittest.TestCase):
    """执行工具：模型送来的是 JSON 字符串，拿回去的**必须是字符串**。"""

    def test_execute_add_returns_string(self):
        """要验证什么：execute("add", '{"a": 2, "b": 3}') 返回字符串 "5"，不是数字 5。

        断言（2 件事，都要）：
          1. 返回值 == "5"
          2. 返回值是 str（用 assertIsInstance 单独断一条）
        为什么第 2 条不能省：== "5" 已经能挡住数字 5，但单独断类型能让报错一眼看出病因；
        更重要的原因：模型只能读文本，返回 int 会让下一次请求组装失败（阶段 3 §4.6 讲过）。
        """
        raise NotImplementedError("TODO 第 2 条：test_execute_add_returns_string")

    def test_hello_uses_default_arg(self):
        """要验证什么：hello 不传 name 时，用默认值"同学"。

        两个角度都要断：
          1. 行为：execute("hello", "{}") == "你好，同学"
          2. 说明书：hello 的 schema 里 parameters["required"] == []（有默认值 → 不必填）
        为什么两个都要：只测行为的话，把 name 错写进 required，模型每次都会硬塞一个名字，
        默认值永远用不上 —— 行为测试还是绿的。必须"实现 + 说明书"两处一致才算对。
        """
        raise NotImplementedError("TODO 第 4 条：test_hello_uses_default_arg")


if __name__ == "__main__":
    unittest.main(verbosity=2)
