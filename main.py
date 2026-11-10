import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "阶段2_重写"))
from llm_config import load_config, create_client, FakeClient

cfg = load_config()
print(f"provider={cfg.provider}  model={cfg.model}  base_url={cfg.base_url or '(离线)'}")

if cfg.provider == "fake":
    client = FakeClient(script=["（离线演示）你好，我是假模型。"])
else:
    client = create_client(cfg)

response = client.chat.completions.create(
    #chat.completions.create(...)：调用客户端提供的方法，向模型发送一次对话请求
    model=cfg.model,
    messages=[
        {"role": "user", "content": "钛价格与优势"}    #role：这条消息是谁说的，"user" 表示用户。
    ]
)

print(response.choices[0].message.content)