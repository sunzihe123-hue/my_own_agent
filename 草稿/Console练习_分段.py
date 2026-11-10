"""Console 练习：一段一段跑，不用复制粘贴。

====== PyCharm 社区版（你的版本）======

方式 A（最省事）：右键本文件 → Run 'Console练习_分段'
    → 从头到尾跑一遍，输出按"第 N 段"标题分段打印。适合先看整体。

方式 B（逐段跑，变量保留）：选中某一段的几行 → 右键
    → Execute Selection in Python Console（快捷键 Alt+Shift+E）
    → 底部 Python Console 里执行，变量留着，下一段能直接用。
    这就是"单元格"的平替，社区版有。

====== 如果你以后装了专业版 ======

`#%%` 会变成"单元格分隔符"，左边出现绿色 ▶，点一下跑一格（Ctrl+Enter）。
社区版没有这个箭头，正常的。

（`#%%` 本身只是注释，删掉不影响运行。）
"""

#%% 第 1 段：准备
import os
from pathlib import Path

print("=== 第 1 段：准备 ===")
print("import 完成")


#%% 第 2 段：字典套字典（厂商预设）
print("\n=== 第 2 段：字典套字典 ===")
PROVIDERS = {
    "deepseek": {"base_url": "https://api.deepseek.com", "model": "deepseek-chat"},
    "fake": {"base_url": "", "model": "fake"},
}
print("整张表:", PROVIDERS)
print("取一家:", PROVIDERS["deepseek"])
print("再取一层:", PROVIDERS["deepseek"]["model"])


#%% 第 3 段：preset 是中间结果
print("\n=== 第 3 段：preset ===")
provider = "deepseek"
preset = PROVIDERS[provider]
print("preset =", preset)
print("preset 的类型 =", type(preset))
print("preset['base_url'] =", preset["base_url"])


#%% 第 4 段：[] 对字典和列表不是一回事
print("\n=== 第 4 段：[] 的两种含义 ===")
xs = ["a", "b", "c"]
d = {"a": 1, "b": 2}
print("list 的 xs[0]  =", xs[0], "  ← 第 0 个位置")
print("dict 的 d['a'] =", d["a"], "  ← 键 'a' 的值")
print("dict 写 d[0] 会怎样：")
try:
    print(d[0])
except KeyError as e:
    print("    KeyError:", e, "← 键是数字 0，不存在")


#%% 第 5 段：三种"不存在时才用默认值"
print("\n=== 第 5 段：默认值 ===")
print("os.getenv(键, 默认) =", os.getenv("完全不存在的键_XYZ", "默认值"))
print("dict.get(键, 默认)  =", {"a": 1}.get("不存在", "默认值"))
print("in 判断键存在       =", "deepseek" in PROVIDERS)
print("in 判断值不存在     =", "https://api.deepseek.com" in PROVIDERS, "  ← in 只查键")


#%% 第 6 段：字符串方法
print("\n=== 第 6 段：字符串方法 ===")
line = "   KEY = value  "
print("strip()         =", repr(line.strip()))
print("split('=')      =", "A=B=C".split("="))
print("split('=', 1)   =", "A=B=C".split("=", 1))
print("splitlines()    =", "a\r\nb\n".splitlines())
print("startswith('#') =", "#注释".startswith("#"))
print("strip('\"')      =", repr('"带引号"'.strip('"')))


#%% 第 7 段：Path 方法
print("\n=== 第 7 段：Path 方法 ===")
p = Path("dir") / "tasks.json"
print("拼接        =", p)
print("name        =", p.name)
print("parent      =", p.parent)
print("exists()    =", p.exists())
print("with_suffix =", p.with_suffix(".tmp"), "  ← 替换后缀")
print("with_name   =", p.with_name(p.name + ".tmp"), "  ← 追加后缀")


#%% 第 8 段：手写一遍 .env 的解析逻辑（假数据，不读文件）
print("\n=== 第 8 段：手写 .env 解析 ===")
text = "# 这是注释\n\nKEY=value\n  SPACED = 带空格  \nQUOTED=\"带引号\"\nNOEQUALS\nA=B=C\n"
for raw in text.splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        print("  跳过:", repr(raw))
        continue
    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip().strip('"').strip("'")
    print(f"  解析出 key={key!r}  value={value!r}")


#%% 第 9 段：setdefault 是"不存在才写"
print("\n=== 第 9 段：setdefault ===")
os.environ["DEMO_KEY"] = "第一次"
print("直接赋值后        =", os.environ["DEMO_KEY"])
os.environ.setdefault("DEMO_KEY", "想覆盖但无效")
print("setdefault 已存在 =", os.environ["DEMO_KEY"])
os.environ.setdefault("DEMO_BRAND_NEW", "全新写入")
print("setdefault 不存在 =", os.environ["DEMO_BRAND_NEW"])
