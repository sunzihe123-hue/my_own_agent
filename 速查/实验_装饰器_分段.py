"""阶段 3 卡点拆解：装饰器 / 函数反射 / 拼参数表。

用法：右键 Run 本文件，从上往下看 5 段输出。
每一段都是最小可运行版，不需要 tools.py，也不联网。

看完再回去填 阶段3_重写/tools.py 的 ToolRegistry.tool()。
"""

from __future__ import annotations


print("=== 第 1 段：装饰器 = 把函数包一层，再原样还回去 ===")


def wrap(func):
    print("  wrap 收到函数:", func.__name__)
    return func          # 关键：还回去，函数才还在


@wrap
def hello(name):
    return "你好，" + name


print("  hello('小明') =", hello("小明"))


print()
print("=== 第 2 段：带参数的装饰器 = 多一层，第一层专门接描述文字 ===")


def tool_like(description):
    print("  第一层收到描述:", description)

    def decorator(func):
        print("  第二层收到函数:", func.__name__)
        return func

    return decorator


@tool_like("打个招呼")
def greet():
    return "hi"


print("  greet() =", greet())


print()
print("=== 第 3 段：inspect.signature 看参数名和默认值 ===")

import inspect


def add(a: int, b: int = 10) -> int:
    return a + b


sig = inspect.signature(add)
print("  完整签名:", sig)
for name, p in sig.parameters.items():
    kind = "必填" if p.default is inspect.Parameter.empty else f"有默认值 {p.default!r}"
    print(f"  参数 {name} → {kind}")


print()
print("=== 第 4 段：类型标注取出来是'类型'还是'字符串'？ ===")

import typing

print("  typing.get_type_hints(add) :", typing.get_type_hints(add), "← 这里是真类型")
print("  add.__annotations__        :", add.__annotations__, "← 这里是字符串！")


print()
print("=== 第 5 段：把参数表拼出来（就是 tool() 里第 2 步） ===")


def build_parameters(func):
    sig = inspect.signature(func)
    hints = typing.get_type_hints(func)
    properties = {}
    required = []
    for name, p in sig.parameters.items():
        json_type = {int: "integer", str: "string"}.get(hints.get(name), "string")
        properties[name] = {"type": json_type}
        if p.default is inspect.Parameter.empty:
            required.append(name)
    return {"type": "object", "properties": properties, "required": required}


print("  add 的参数表:", build_parameters(add))
print()
print("完事。现在回 tools.py：把第 3、4、5 段的逻辑搬进 decorator，")
print("再加两行 —— self.tools[func.__name__] = Tool(...) 和 return func。")
