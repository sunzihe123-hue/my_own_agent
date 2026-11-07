"""实验文件：把 load_dotenv 里用到的每个方法，一行一个地跑给你看。

用法：在 PyCharm 里右键 → Run '实验_方法速查'，然后对照 说明_为什么.md 看输出。
看懂了可以删掉这个文件（不影响测试）。
"""

import os
from pathlib import Path

# 造一个假的 .env 文件，用来观察"文件 → 字符串 → 行"的变化
demo = Path(__file__).with_name("_demo_实验用.env")
demo.write_text(
    "# 这是注释行\n"
    "\n"
    "KEY=value\n"
    "  SPACED = 带空格  \n"
    'QUOTED="带双引号"\n'
    "SINGLE='单引号'\n"
    "NOEQUALS\n"
    "A=B=C\n",
    encoding="utf-8",
)
print(f"实验用的假 .env 已写在：{demo}\n")

print("=" * 70)
print("1) Path 是什么")
print("=" * 70)
p = Path("some/dir/file.env")
print("  Path('some/dir/file.env') =", p, "| 类型：", type(p).__name__)
print("  Path 是'路径对象'，不是字符串：它自带 .exists() / .read_text() / .name / .parent 等方法")
print("  拼路径：Path('a') / 'b' ->", Path("a") / "b", "（用 / 号，不用 + 号）")

print()
print("=" * 70)
print("2) path.exists() -> bool   文件在不在")
print("=" * 70)
print("  刚写的 demo 存在吗：", demo.exists())
print("  一个不存在的文件：", Path("绝对不存在_xyz.env").exists())

print()
print("=" * 70)
print("3) path.read_text(encoding='utf-8') -> str   一次读成整段字符串")
print("=" * 70)
text = demo.read_text(encoding="utf-8")
print("  返回值类型：", type(text).__name__)
print("  长度：", len(text), "个字符")
print("  前 20 个字符是：", repr(text[:20]))
print("  （注意：换行符 \\n 也是字符串的一部分，所以读到的是'一整段'）")

print()
print("=" * 70)
print("4) text.splitlines() -> list[str]   按行切开，换行符不保留")
print("=" * 70)
lines = text.splitlines()
print(f"  一共切出 {len(lines)} 行：")
for i, line in enumerate(lines, 1):
    print(f"    第{i}行: {line!r}")
print("  对比 split('\\n')：", repr("a\nb\n".split("\n")), " ← 多出一个空串，所以用 splitlines() 更省心")

print()
print("=" * 70)
print("5) str.strip() / strip(字符)   去掉两端的东西")
print("=" * 70)
print("  '  带空格  '.strip()      =", repr("  带空格  ".strip()))
print("  '\"带双引号\"'.strip('\"')  =", repr('"带双引号"'.strip('"')))
print("  \"'单引号'\".strip(\"'\")    =", repr("'单引号'".strip("'")))
print("  注意 strip 只去【两端】，不去中间：' a b '.strip() =", repr(" a b ".strip()))
print("  注意 strip('\"') 去掉的是'任意多个双引号'，不是配对：", repr('""x""'.strip('"')))

print()
print("=" * 70)
print("6) str.startswith('#') 和 '=' in line   两种判断")
print("=" * 70)
print("  '#注释'.startswith('#') =", "#注释".startswith("#"))
print("  'KEY=x'.startswith('#') =", "KEY=x".startswith("#"))
print("  '=' in 'KEY=value'      =", "=" in "KEY=value")
print("  '=' in 'NOEQUALS'       =", "=" in "NOEQUALS")

print()
print("=" * 70)
print("7) str.split('=', 1)  -> list[str]   只拆第一个 = 号")
print("=" * 70)
print("  'A=B=C'.split('=')     =", "A=B=C".split("="), " ← 拆成 3 段，后面 code 会炸")
print("  'A=B=C'.split('=', 1)  =", "A=B=C".split("=", 1), " ← 只拆 1 次，值里保留 =")
print("  为什么必须写 1：API Key / URL 里经常带 = 号")

print()
print("=" * 70)
print("8) 元组解包：key, value = 两元素列表")
print("=" * 70)
key, value = "A=B=C".split("=", 1)
print("  key =", repr(key), "| value =", repr(value))
print("  等价于：pair = [...]; key = pair[0]; value = pair[1]")

print()
print("=" * 70)
print("9) os.environ 是一个'字典'，setdefault 是字典方法")
print("=" * 70)
os.environ["DEMO_KEY"] = "第一次设置"
print("  直接赋值后 os.environ['DEMO_KEY'] =", os.environ["DEMO_KEY"])
os.environ.setdefault("DEMO_KEY", "第二次想覆盖，但应该无效")
print("  setdefault 遇到'已存在'时 =", os.environ["DEMO_KEY"], " ← 没被覆盖")
os.environ.setdefault("DEMO_BRAND_NEW", "全新写入")
print("  setdefault 遇到'不存在'时 =", os.environ.get("DEMO_BRAND_NEW"))
print("  真实环境变量长什么样：", os.environ.get("USERPROFILE") or os.environ.get("USERNAME"))

print()
print("=" * 70)
print("10) os.getenv 和 os.environ[...] 的区别")
print("=" * 70)
print("  os.getenv('根本不存在_XYZ', '默认值') =", os.getenv("根本不存在_XYZ", "默认值"), " ← 不报错")
try:
    os.environ["根本不存在_XYZ"]
except KeyError:
    print("  os.environ['根本不存在_XYZ'] → KeyError  ← 键不存在会炸")

print()
print("=" * 70)
print("11) continue：跳过本轮循环，继续下一轮")
print("=" * 70)
for x in [1, 2, 3]:
    if x == 2:
        continue
    print("    处理了", x)
print("  （2 被 continue 跳过了，循环本身没结束）")

print()
print("=" * 70)
print("12) 把上面所有东西串起来：手写一遍解析逻辑（只是演示，不是答案）")
print("=" * 70)
for raw_line in lines:
    line = raw_line.strip()
    if not line:
        print(f"  跳过空行：{raw_line!r}")
        continue
    if line.startswith("#"):
        print(f"  跳过注释：{line!r}")
        continue
    if "=" not in line:
        print(f"  跳过没有等号的行：{line!r}")
        continue
    k, v = line.split("=", 1)
    k = k.strip()
    v = v.strip().strip('"').strip("'")
    print(f"  解析出：key={k!r}  value={v!r}")
