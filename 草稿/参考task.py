"""阶段 1 v2：dataclass + TaskStore + 自定义异常。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from textwrap import indent


# ---------------------------------------------------------------- 异常


class StudyMateError(Exception):
    """本项目所有自定义异常的基类。"""


class InvalidTaskError(StudyMateError):
    """任务数据不合法：标题为空、日期格式错误。"""


class TaskNotFoundError(StudyMateError):
    """按编号找不到任务。"""

    def __init__(self, task_id: int) -> None:
        super().__init__(f"找不到编号为 {task_id} 的任务")
        self.task_id = task_id


# ---------------------------------------------------------------- 日期工具


def _normalize_due(due: str | None) -> str | None:
    """把用户给的日期字符串统一成 YYYY-MM-DD。"""
    if due is None:
        return None
    text = due.strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        raise InvalidTaskError(
            f"日期格式不对：「{text}」。请用 YYYY-MM-DD，例如 2026-10-14"
        ) from None #隐藏掉底层原始报错的踪迹，只向用户展示你自定义的那一句报错信息


# ---------------------------------------------------------------- 任务对象


@dataclass
class Task:
    id: int
    title: str
    due: str | None = None
    course: str | None = None
    done: bool = False
    priority: int = 2          # 1 高 / 2 中 / 3 低

    def days_left(self, today: date | None = None) -> int | None:
        if not self.due:
            return None
        return (date.fromisoformat(self.due) - (today or date.today())).days

    def describe(self) -> str:
        box = "☑" if self.done else "□"
        parts = [f"{box} #{self.id} {self.title}"]
        if self.course:
            parts.append(f"[{self.course}]")
        if not self.due:
            parts.append("无截止日期")
        elif self.done:
            parts.append(f"原定 {self.due}，已完成")
        else:
            left = self.days_left()
            if left is None:
                parts.append(f"截止 {self.due}")
            elif left < 0:
                parts.append(f"截止 {self.due}（已逾期 {-left} 天）")
            elif left == 0:
                parts.append(f"截止 {self.due}（今天到期）")
            else:
                parts.append(f"截止 {self.due}（还剩 {left} 天）")
        if self.priority != 2:
            parts.append("高优先级" if self.priority == 1 else "低优先级")
        return " ".join(parts)


# ---------------------------------------------------------------- 仓库


class TaskStore:
    def __init__(self, tasks: list[Task] | None = None) -> None:
        self.tasks: list[Task] = list(tasks or [])

    # ---------- 内部工具 ----------

    def _next_id(self) -> int:
        return max((t.id for t in self.tasks), default=0) + 1

    def _locate(self, task_id: int) -> int:
        for i, t in enumerate(self.tasks):
            if t.id == task_id:
                return i
        raise TaskNotFoundError(task_id)

    # ---------- 增 ----------

    def add(self, title: str, due: str | None = None,
            course: str | None = None, priority: int = 2) -> Task:
        title = (title or "").strip()
        if not title:
            raise InvalidTaskError("任务标题不能为空")
        if priority not in (1, 2, 3):
            raise InvalidTaskError("priority 只能是 1（高）、2（中）、3（低）")
        task = Task(
            id=self._next_id(),
            title=title,
            due=_normalize_due(due),
            course=(course or "").strip() or None,
            priority=priority,
        )
        self.tasks.append(task)
        return task

    # ---------- 查 ----------

    def get(self, task_id: int) -> Task:
        return self.tasks[self._locate(task_id)]

    def list(self, include_done: bool = True) -> list[Task]:
        items = [t for t in self.tasks if include_done or not t.done]
        return sorted(items, key=lambda t: (t.due is None, t.due or "", t.id))

    def upcoming(self, days: int = 7, today: date | None = None) -> list[Task]:
        today = today or date.today()
        result = []
        for t in self.tasks:
            if t.done:
                continue
            left = t.days_left(today)
            if left is not None and left <= days:
                result.append(t)
        return sorted(result, key=lambda t: (t.due or "", t.id))

    # ---------- 改 ----------

    def complete(self, task_id: int) -> Task:
        task = self.get(task_id)
        task.done = True
        return task

    def edit(self, task_id: int, title: str | None = None, due: str | None = None,
             course: str | None = None, priority: int | None = None) -> Task:
        task = self.get(task_id)
        if title is not None:
            title = title.strip()
            if not title:
                raise InvalidTaskError("任务标题不能为空")
            task.title = title
        if due is not None:
            task.due = _normalize_due(due)
        if course is not None:
            task.course = course.strip() or None
        if priority is not None:
            if priority not in (1, 2, 3):
                raise InvalidTaskError("priority 只能是 1（高）、2（中）、3（低）")
            task.priority = priority
        return task

    # ---------- 删 ----------

    def delete(self, task_id: int) -> Task:
        return self.tasks.pop(self._locate(task_id))

    def __len__(self) -> int:
        return len(self.tasks)

    def __iter__(self):
        return iter(self.tasks)


def load_task(task:list[Task]) -> TaskStore:
    if not task.json.exists():
        return []

    try :
        with open("task.json","r",encoding="utf-8") as f:
            data = json.load(f)
        return [task.dict(items) for items in data]

        except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError) as error::
            print("文件未找到")
            return []


def save_tasks(task:list[Task]): -> None:
    data = [ task.dict() for task in task ]
    try
        with open("task.json", "w",encoding="utf-8") as f:
            json.dumps(data,f,ensure_ascii=False,indent(4))
    except OSError as e:
