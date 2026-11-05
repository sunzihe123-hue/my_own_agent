import os
from openai import OpenAI

api_key = os.getenv("DEEPSEEK_API_KEY")

if not api_key:
    raise RuntimeError("没有读取到 API Key")

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"
)    #创建好的客户端client

response = client.chat.completions.create(
                 #chat.completions.create(...)：调用客户端提供的方法，向模型发送一次对话请求
    model="deepseek-flash",
    messages=[
        {"role": "user", "content": "我好困"}    #role：这条消息是谁说的，"user" 表示用户。
    ]
)

print(response.choices[0].message.content)