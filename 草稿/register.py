from tools import add, multiply

TOOL_REGISTRY = {
    "add": add,
    "multiply": multiply,
}
def run_tool(tool_name, arguments):
    if tool_name not in TOOL_REGISTRY:
        raise ValueError(f"不允许调用该工具：{tool_name}")

    if not isinstance(arguments, dict):
        raise ValueError("工具参数必须是字典")
    # 仅允许工具声明需要的参数，避免意外参数传入
    expected_args = {
        "add": {"a", "b"},
        "multiply": {"a", "b"},
    }
    if set(arguments.keys()) != expected_args[tool_name]:
        raise ValueError("工具参数不正确")
    a = arguments["a"]
    b = arguments["b"]
    # bool 是 int 的子类，因此这里需要排除布尔值
    if (
        isinstance(a, bool) or not isinstance(a, (int, float))
        or isinstance(b, bool) or not isinstance(b, (int, float))
    ):
        raise ValueError("a 和 b 必须是数字")

    return TOOL_REGISTRY[tool_name](**arguments)