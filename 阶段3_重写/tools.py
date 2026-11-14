"""阶段 3 · 工具注册表（对应 studymate/tools.py，108 行砍成最小版）。

大模型只会说话，不会做事。"工具调用"（tool call）是三件事配合：
  1. 我们把工具清单（名字 + 描述 + 参数）用 JSON Schema 告诉模型   ← schemas()
  2. 模型如果觉得需要，就回一句"请帮我调用 xxx，参数是 {...}"      ← tool_calls
  3. 我们真的执行那个 Python 函数，把结果发回给模型                ← execute()

有了注册表，加一个工具 = 写一个函数 + 加一个装饰器，不用改任何 if/elif。

写作顺序（每完成一步就 Run 一次 test_tools.py）：
  第 1 步  ToolRegistry.tool()     → 2 个变绿
  第 2 步  Tool.schema()           → 6 个变绿（累计）
  第 3 步  ToolRegistry.schemas()  → 8 个变绿
  第 4 步  ToolRegistry.execute()  → 15 个全绿
"""

from __future__ import annotations

import inspect
import json
import types
import typing
from dataclasses import dataclass, field
from typing import Any, Callable

# Python 类型 → JSON Schema 里的类型名
_JSON_TYPES = {str: "string", int: "integer", float: "number", bool: "boolean"}


def _json_type(annotation: Any) -> str:
    """把类型标注转成 JSON Schema 的类型名（已给你）。

    str → "string"、int → "integer"、float → "number"、bool → "boolean"；
    str | None 这种"可空"取里面那个非 None 的；list[...] → "array"。
    """
    origin = typing.get_origin(annotation)
    if origin in (typing.Union, types.UnionType):
        args = [a for a in typing.get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return _json_type(args[0])
    if origin in (list, typing.List):
        return "array"
    return _JSON_TYPES.get(annotation, "string")


@dataclass
class Tool:
    """一个工具的全部信息（字段已给）。"""

    name: str
    description: str
    func: Callable[..., Any]
    parameters: dict

    def schema(self) -> dict:
        """TODO 第 2 步：拼出 OpenAI 要的工具描述（3 行左右）。

        （test_schema_shape 会逐项检查）："""
        return{
            "type":"function",
            "function":{
                "name": self.name,
                "description":self.description,
                "parameters": self.parameters,
            }
        }

@dataclass
class ToolRegistry:
    """工具注册表：工具名 → Tool。"""

    tools: dict[str, Tool] = field(default_factory=dict)

    def tool(self, description: str, params: dict[str, str] | None = None):
        """TODO 第 1 步：装饰器，把被装饰的函数登记进 self.tools。

        用法：
            @reg.tool("把两个数相加。", params={"a": "加数", "b": "加数"})
            def add(a: int, b: int) -> int:
                return a + b

        要做的事：
          1. 用 inspect.signature(func) 拿参数列表（参数名 + 有没有默认值）
          2. 用 typing.get_type_hints(func) 拿类型标注
          3. 每个参数生成 {"type": _json_type(类型)}，params 里给了说明就再加 "description"
          4. 没有默认值（default 是 inspect.Parameter.empty）的参数 → 放进 required
          5. parameters = {"type": "object", "properties": {...}, "required": [...]}
          6. self.tools[func.__name__] = Tool(...)，然后 **return func**（原函数还能直接调）
        """
        if params is None:
            params = {}

        def decorator(func):
            sig = inspect.signature(func)
            hints = typing.get_type_hints(func)
            properties = {}
            required = []
            for name,param in sig.parameters.items():

                properties[name] = {"type":_json_type(hints.get(name, str))}
                if name in params:
                    properties[name]["description"] = params[name]
                if param.default is inspect.Parameter.empty:
                    required.append(name)
            parameters = {"type": "object", "properties": properties, "required": required}
            self.tools[func.__name__] =(
                Tool(
                     name = func.__name__,
                     description=description,
                     func = func,
                     parameters=parameters,)
                                                 )
            return func

        return decorator

    def schemas(self) -> list[dict]:
        """TODO 第 3 步：所有工具的 schema 列表（发给模型的就是它）。

        一个列表推导式就够。
        """
        return [t.schema() for t in self.tools.values()]

    def execute(self, name: str, arguments: str | dict) -> str:
        """TODO 第 4 步：执行工具，结果**一律转成字符串**（模型只能读文本）。

        本阶段最难的一步。要求（test_tools.py 后半段逐条检查）：

          - 找不到工具 → 返回 "错误：没有名为 xxx 的工具"
          - arguments 是 str → json.loads 成 dict；是 dict → 复制一份再用
          - 解析出来不是 dict → "错误：参数必须是 JSON 对象"
          - JSON 语法错 → "错误：参数不是合法 JSON（...）"
          - 调 tool.func(**args) 时参数名/个数不对（TypeError）→ "错误：参数不匹配（...）"
          - 工具内部抛别的异常 → "错误：<异常信息>"
          - **注意：绝不要把异常抛出去**——模型给错参数很常见，把错误当结果告诉它，
            它通常会自己改正后重试；抛出去整个对话就断了
          - 结果是 str 原样返回；其他类型 → json.dumps(result, ensure_ascii=False, default=str)
        """
        if name not in self.tools:
            return f"错误：没有名为 {name} 的工具"
        try:
            if isinstance(arguments,str):
                args = json.loads(arguments)
            if isinstance(arguments,dict):
                args = dict(arguments)
            if not isinstance(args,dict):
                return "错误：参数必须是 JSON 对象"
        except json.decoder.JSONDecodeError:
            return "错误：参数不是合法 JSON 对象"
        try:
            tool = self.tools[name]
            result = tool.func(**args)
        except TypeError:
            return "错误：参数不匹配"
        except Exception as e:
            return f"错误：{e}"
        if isinstance(result,str):
            return result
        return json.dumps(result, ensure_ascii=False, default = str)


