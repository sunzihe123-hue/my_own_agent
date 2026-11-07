"""阶段 2 重写：配置 + 模型客户端。

照 studymate 的 config.py（69 行）+ llm.py（120 行）的最小版写，目标是把
"读配置 → 拿客户端 → 发一次请求" 这条链路彻底搞明白。

参考版砍掉了什么（这次不写）：
  - 其他 3 家厂商（qwen / glm / kimi）：只留 deepseek + fake
  - tasks_file / notes_dir 两个路径字段：阶段 3、4 才用
  - FakeClient 的"按关键词路由到工具"：那是给 agent 用的，阶段 3 再写

写作顺序（每完成一步就 Run 一次测试）：
  第 1 步  load_dotenv       → TestLoadDotenv 5 个全绿
  第 2 步  Config + load_config → TestLoadConfig 6 个全绿
  第 3 步  FakeClient（__init__ / _next / _Completions.create）→ TestFakeClient 8 个全绿
  第 4 步  create_client     → TestCreateClient 2 个全绿
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

# ============================================================================
# 一、厂商预设表（已给你，这是数据不是逻辑）
# ============================================================================

# 国内厂商大多提供"OpenAI 兼容接口"，所以只换 base_url + 模型名。
PROVIDERS: dict[str, dict[str, str]] = {
    "deepseek": {"base_url": "https://api.deepseek.com", "model": "deepseek-chat"},
    "fake": {"base_url": "", "model": "fake"},  # 离线模式，不联网、不花钱
}


# ============================================================================
# 二、解析 .env（第 1 步）
# ============================================================================


def load_dotenv(path: Path) -> None:
    """把 .env 文件里的 KEY=VALUE 塞进 os.environ。

    要求：
      - 文件不存在 → 直接返回，不报错
      - 跳过空行、# 开头的注释、没有 = 的行
      - KEY 和 VALUE 两头的空格要去掉
      - VALUE 两头的 " 或 ' 要去掉（写 .env 的人可能会加引号）
      - **已经存在的环境变量不能被覆盖**（真实部署时是用环境变量覆盖 .env 的）
    提示：os.environ.setdefault(key, value) 就是"不存在才设置"。
    """
    if not path.exists():
        return
    with path.open("r",encoding = "utf-8") as f:
        text = f.read()
    lines = text.splitlines()
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or '=' not in line:
            continue
        key,value = raw.split("=",1)
        key,value = key.strip() , value.strip().strip("'").strip('"')

        os.environ.setdefault(key,value)



# ============================================================================
# 三、配置对象（第 2 步）
# ============================================================================


@dataclass
class Config:
    """一次请求需要的全部配置。字段已给，实现 load_config 。"""

    provider: str
    api_key: str
    base_url: str
    model: str


def load_config(env_file: Path | None = None) -> Config:
    """读环境变量（以及 .env 文件），拼出一个 Config。

    要求：
      - 先 load_dotenv(env_file or Path(".env"))
      - provider 读 STUDYMATE_PROVIDER，默认 "fake"，并转小写
      - provider 不在 PROVIDERS 里 → 抛 ValueError，消息里要列出可选值
      - api_key 读 STUDYMATE_API_KEY，默认空串 ""
      - base_url / model 先取厂商预设，允许被 STUDYMATE_BASE_URL / STUDYMATE_MODEL 覆盖
    """
    load_dotenv(env_file or Path(".env"))
    provider = os.getenv("STUDYMATE_PROVIDER", "fake").lower()

    if provider not in PROVIDERS:
        raise ValueError(f"未知的 provider：{provider}，可选：{', '.join(PROVIDERS)}")
    api_key = os.getenv("STUDYMATE_API_KEY", "")

    preset = PROVIDERS[provider]

    base_url = os.getenv("STUDYMATE_BASE_URL", preset["base_url"])
    model = os.getenv("STUDYMATE_MODEL", preset["model"])
    return Config(
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )





# ============================================================================
# 四、创建客户端（第 4 步）
# ============================================================================


def create_client(cfg: Config):
    """按 provider 返回可用的客户端。

    要求：
      - provider == "fake" → 返回 FakeClient()
      - 否则若没有 api_key → 抛 RuntimeError，消息里要告诉用户 .env 怎么写
        （参考版那句 4 行提示照抄过来：没有 Key 是新手必踩的第一个坑）
      - 否则延迟导入 openai（fake 模式不需要装 openai），返回 OpenAI(...)
      - 导入失败 → 抛 RuntimeError 提示 pip install openai
    """
    raise NotImplementedError("TODO 第 4 步")


# ============================================================================
# 五、离线假客户端（第 3 步）
# ============================================================================


def _response(content: str):
    """把一段文字包装成"和真实 SDK 长得一样"的返回值（已给你）。

    真实返回值长这样：resp.choices[0].message.content
    我们不用真 SDK 的类型，用 SimpleNamespace 临时捏一个，形状对得上就行。
    """
    message = SimpleNamespace(role="assistant", content=content)
    return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason="stop")])


class _Completions:
    """挂在 client.chat.completions 上，提供 .create(...)（和真 SDK 同形）。"""

    def __init__(self, owner: "FakeClient") -> None:
        self._owner = owner

    def create(self, model: str, messages: list[dict], **kwargs):
        """记录这次请求，然后返回剧本里的下一句。

        要求：
          - 把 {"model": ..., "messages": [...]} 追加到 self._owner.calls
          - messages 要**拷贝**一份再存（见文档 3.10），别存原对象
          - 返回 self._owner._next()
        """
        raise NotImplementedError("TODO 第 3 步")


class FakeClient:
    """离线假模型：形状模拟 OpenAI 客户端，但只会照着剧本说话。"""

    def __init__(self, script: list[str] | None = None) -> None:
        """要求：
          - self.script 存剧本，但要用 list(...) 拷一份（别把调用方的列表吃掉）
          - script 为 None 时保持 None（表示"没给剧本"，调用时应当报错）
          - self.calls 存每次请求的记录，初始为空列表
          - self.chat 是一个 SimpleNamespace(completions=_Completions(self))
        """
        self.script: list[str] | None =list(script) if script is not None else None
        self.calls: list[] = []
        self.chat: SimpleNamespace = SimpleNamespace(completions=_Completions(self))

    def _next(self):
        """弹出剧本里的下一句。剧本为空（或没给）→ 抛 RuntimeError，说明原因。"""
        if not self.script:
            raise RuntimeError("剧本为空")
        return _response(self.script.pop(0))



# ============================================================================
# 六、自测：写完之后在 PyCharm 里右键 Run 'phase2'
# ============================================================================

if __name__ == "__main__":
    cfg = load_config()
    print(f"当前配置：provider={cfg.provider}  model={cfg.model}  base_url={cfg.base_url or '(离线)'}")
    print(f"API Key：{'已配置' if cfg.api_key else '未配置'}")

    print("\n--- 1. 用离线假客户端跑一次（不联网、不花钱）---")
    client = FakeClient(script=["（假模型）你好，我是阶段 2 的 FakeClient。"])
    resp = client.chat.completions.create(
        model=cfg.model,
        messages=[{"role": "user", "content": "你好"}],
    )
    print("回复：", resp.choices[0].message.content)
    print("这次请求被记录在 client.calls[0]：")
    print("  model    =", client.calls[0]["model"])
    print("  messages =", client.calls[0]["messages"])

    print("\n--- 2. 剧本演完了会怎样 ---")
    try:
        client.chat.completions.create(model=cfg.model, messages=[])
    except RuntimeError as e:
        print("  按预期报错：", e)

    print("\n--- 3. 没配 Key 就选真实厂商会怎样 ---")
    try:
        create_client(Config("deepseek", "", "https://api.deepseek.com", "deepseek-chat"))
    except RuntimeError as e:
        print("  按预期报错：")
        for line in str(e).splitlines():
            print("   ", line)
