import os
from openai import OpenAI

api_key = os.getenv("VIBERS_API_KEY")

if not api_key:
    raise RuntimeError("没有读取到 API Key")

client = OpenAI(
    api_key=api_key,
    base_url="https://vibers.cc/v1"
)

response = client.chat.completions.create(
    model="claude-opus-5-5",
    messages=[
        {"role": "user", "content": "请用一句话介绍 Python。"}
    ]
)

print(response.choices[0].message.content)