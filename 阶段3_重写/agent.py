"""阶段 3 · agent 主循环（对应 studymate/agent.py，142 行砍成最小版）。

agent 的本质是一个循环：

    用户提问
      ↓
    ┌→ 把完整对话 + 工具清单发给模型
    │    ↓
    │  模型回复里有 tool_calls 吗？
    │    ├─ 没有 → 这就是最终答案，返回给用户
    │    └─ 有   → 逐个执行工具，把结果作为 role="tool" 的消息追加到对话
    └────────────┘ （回到循环开头，让模型看着工具结果继续思考）

本阶段只保留最核心的部分，砍掉了：重试/退避、危险操作确认、历史裁剪、事件回调。

写作顺序（每完成一步就 Run 一次 test_agent.py）：
  第 5 步  Agent.__init__    → 2 个变绿
  第 6 步  Agent._call_model → 5 个变绿（累计）
  第 7 步  Agent.chat()      → 13 个全绿

阶段 4 追加：本文件要补 3 处日志（工程化的意义 = 测试证明"行为对"，日志证明"过程可查"）。
  TODO 日志①  chat() 每轮开头     ：第几轮 + 历史条数
  TODO 日志②  工具执行前/后两行    ：name / arguments、result
  TODO 日志③  _call_model() 异常分支：log.exception（记完必须原样 raise）
"""

from __future__ import annotations

import logging
from datetime import date

from tools import ToolRegistry

# 模块级日志器（logger = 日志器）：名字取 __name__，被 import 时就是模块名 "agent"。
# 阶段 4 已给好，不用改；下面三处 TODO 就往它上面写。
log = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = """你是 StudyMate，一名大学生的学习助手，用简洁友好的中文回答。
规则：
1. 需要事实信息时必须调用工具获取，不要编造。
2. 处理"明天""下周五"这类相对日期时，先调用工具换算成 YYYY-MM-DD。
3. 删除任务前要确认用户确实想删除。
今天大约是 {today}（精确时间请调用工具）。"""


class Agent:
    """把"模型 + 工具"串成一个能多轮思考和动手的对话器。"""

    def __init__(self, client, model: str, registry: ToolRegistry, max_steps: int = 5):
        """TODO 第 5 步（5 行左右）。

        要求：
          - 存好 self.client / self.model / self.registry / self.max_steps
          - self.messages 是对话历史，第一条是 system 消息：
                {"role": "system", "content": DEFAULT_SYSTEM_PROMPT 里把 {today} 替换成今天}
            提示：字符串的 .replace("{today}", date.today().isoformat())
        """
        self.client = client
        self.model = model
        self.registry = registry
        self.max_steps = max_steps
        prompt = DEFAULT_SYSTEM_PROMPT.replace("{today}", date.today().isoformat())
        self.messages :list[dict] = [{"role":"system","content":prompt}]

    def chat(self, user_text: str) -> str:
        """TODO 第 7 步：本阶段最核心的 ~25 行。

        流程：
          1. 把用户的这句话 append 进 self.messages
          2. for step in range(self.max_steps):
               a. msg = self._call_model()          ← 拿回模型这一轮的消息
               b. 如果 msg.tool_calls 为空 → 这就是最终答案：
                    把 {"role": "assistant", "content": msg.content or ""} 记进历史，
                    然后 return 这句话
               c. 否则（有工具调用）：
                  ① 先把"模型要工具"这条消息**原样**记进历史（role=assistant + tool_calls 列表），
                     每个 tool_call 只保留 {"id", "type": "function",
                                           "function": {"name", "arguments"}} 三个字段
                  ② 然后逐个执行：结果 = self.registry.execute(tc.function.name,
                                                             tc.function.arguments)
                     每条结果都 append 成 {"role": "tool", "tool_call_id": tc.id,
                                          "content": 结果}
                  ③ 回到循环开头（下一轮模型会看到工具结果）
          3. 循环跑满 max_steps 还没结束 → return 一句提示（例如
             "（思考步数太多，我先停下了。可以把问题说得更具体一点再试试。）"），
             并把这句话记进历史
        """
        self.messages.append({"role": "user", "content": user_text})
        for step in range(self.max_steps):
            # TODO 日志①（1 行）：每轮请求开头记一条 info
            #   内容：第几轮（step + 1）+ 当前历史条数（len(self.messages)）
            #   用途：事后能还原"模型当时看到的是多长的对话"（排查越聊越傻的经典手段）
            msg = self._call_model()
            if not msg.tool_calls:
                text = msg.content or ""
                self.messages.append({"role": "assistant", "content": text})
                return text
            calls = [{
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in msg.tool_calls]
            self.messages.append({
                "role": "assistant",
                "tool_calls": calls,
                "content": msg.content or ""
            })
            for tc in msg.tool_calls:
                # TODO 日志②-a（1 行）：执行**前**记一条 info：工具名 + 参数原文
                #   （参数原文 = tc.function.arguments；这是 test_agent_log.py 第 5 条的数据来源）
                result = self.registry.execute(tc.function.name, tc.function.arguments)
                # TODO 日志②-b（1 行）：执行**后**记一条 info：工具名 + result
                #   （这是 test_agent_log.py 第 6 条的数据来源）
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result)
                })   #工具返回结果必须是字符串
        final_text = "思考步数太多，我先停下了。可以把问题说得更具体一点再试试。"
        self.messages.append({"role": "assistant","content": final_text})
        return final_text

    def _call_model(self):
        """TODO 第 6 步（2 行）。

        发一次请求，返回 resp.choices[0].message。
        注意要把 tools=self.registry.schemas() or None 传上去：
        注册表为空时传 None（有的接口不接受空列表）。

        阶段 4 追加（TODO 日志③）：把下面这次调用包进 try / except Exception
          - except 分支里先 log.exception("...")，再 **原样 raise** 重新抛出
          - 为什么用 log.exception 而不是 log.error：它会把完整调用栈（traceback）写进日志，
            事后能直接看出是哪一行炸的；log.error 只有一句话
          - 为什么必须 raise：日志是"记录"，不是"处理"；吞掉异常会让上层误以为成功
          - 现有的两行代码要缩进进 try 里（这是阶段 4 唯一改结构的地方）
        """
        resp = self.client.chat.completions.create(
            model = self.model,
            messages = self.messages,
            tools = self.registry.schemas() or None,
        )
        return resp.choices[0].message
