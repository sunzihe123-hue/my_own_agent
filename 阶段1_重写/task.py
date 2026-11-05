"""阶段 1 重写：任务数据层（照着 studymate/studymate/tasks.py 写）。

规则
====
1. 只实现 TODO 的地方。不要复制参考文件的正文，靠 test_task.py 的报错推。
2. 按 说明_为什么.md 第三节的顺序写，每完成一步就 Run 一次测试。
3. 测试全部变绿 = 功能对齐参考版；然后再回答文档最后那 3 个问题。

依赖顺序：异常 → Task → 日期校验 → TaskStore 存取 → 增 → 查 → 改 → 删
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path


# ============================================================================
# 一、异常
# ============================================================================


class TaskError(Exception):
    """任务相关错误的基类。演示：这个类体是空的，它只负责"分类"。"""


class TaskNotFoundError(TaskError):
    """按编号找不到任务。

    要求：
      - 消息是 f"找不到编号为 {task_id} 的任务"
      - 把 task_id 存成 self.task_id（调用方要拿它重组提示语）
    """

    def __init__(self, task_id: int) -> None:
        super().__init__(f"找不到编号为 {task_id} 的任务")
        self.task_id = task_id

# ============================================================================
# 二、时间工具
# ============================================================================


def _now() -> str:
    """当前时间，ISO 格式，精确到秒。例如 2026-11-02T21:30:00。

    提示：datetime.now().isoformat(timespec="seconds")
    """
    return datetime.now().isoformat(timespec="seconds")



# ============================================================================
# 三、日期校验
# ============================================================================


def parse_due(due: str | None) -> str | None:
    """校验并归一化截止日期。

    要求：
      - None 或 空白字符串 → 返回 None
      - "20261020" → 返回 "2026-10-20"（归一化）
      - "2026-1-4" → 抛 TaskError（ISO 要求月日补零，fromisoformat 不认这个）
      - 格式不合法 → 抛 TaskError（不是 ValueError）
    提示：date.fromisoformat() 同时干"校验"和"归一化"两件事，它抛的 ValueError 要接住。
    """
    # 1. 拦截 None
    if due is None:
        return None

    # 2. 清理空格，并拦截空字符串
    text = due.strip()
    if not text:
        return None

    # 3. 处理特殊的 8 位纯数字
    if len(text) == 8 and text.isdigit():
        try:
            dt = datetime.strptime(text, "%Y%m%d")
            return dt.date().isoformat()
        except ValueError:
            raise TaskError(f"日期不合法：{text}。请使用 YYYY-MM-DD 格式，例如 2026-10-20") from None

    # 4. 【重点修复】处理带横杠的标准 ISO 格式，别忘了 try: 和冒号！
    try:
        d = date.fromisoformat(text)
        return d.isoformat()
    except ValueError:
        raise TaskError(f"格式不合法：{text}。请使用 YYYY-MM-DD 格式，例如 2026-10-20") from None
# ============================================================================
# 四、任务对象
# ============================================================================


@dataclass
class Task:
    """一条作业/待办。@dataclass 会自动生成 __init__ / __repr__ / __eq__。"""

    id: int
    title: str
    due: str | None = None        # "YYYY-MM-DD"
    course: str | None = None
    done: bool = False
    # 这行已经给你了。坑在 说明_为什么.md 的 4.3：为什么不能写 created_at: str = _now()
    created_at: str = field(default_factory=_now)

    def days_left(self, today: date | None = None) -> int | None:
        """距截止日期还有几天。没有 due 返回 None，负数表示已逾期。

        要求：不传 today 时用 date.today()（依赖注入，为了测试能固定"今天"）。
        """
        if self.due is None:
            return None
        if today is None:
            today = date.today()

        return (date.fromisoformat(self.due) - today).days

    def describe(self, today: date | None = None) -> str:
        """返回一行人类可读的描述。格式必须是：

        ✔/□ #1 标题 [课程] 截止 2026-10-12（还剩 2 天）
                                 （已逾期 5 天） / （今天！）
        已完成的任务显示"截止 X"，不带剩余天数。
        没有 due 的超期——没有 due 就不显示这一段。
        """
        # 1. 组装基础前缀 (图标、ID、标题、课程)
        icon = "✓" if self.done else "□"
        prefix = f"{icon} #{self.id} {self.title} [{self.course}]"

        # 2. 前置拦截：如果没日期，或者已经完成了，直接秒回，不往下算
        if self.due is None:
            return prefix
        if self.done:
            return f"{prefix} 截止 {self.due}"

        # 3. 核心一行流：在 f-string 里面做判断！
        days = self.days_left(today)
        time_str = f"（已逾期 {abs(days)} 天）" if days < 0 else ("（今天！）" if days == 0 else f"（还剩 {days} 天）")

        return f"{prefix} 截止 {self.due} {time_str}"
# ============================================================================
# 五、仓库
# ============================================================================


class TaskStore:
    """一批任务的容器，数据存在一个 JSON 文件里。"""

    def __init__(self, path: str | Path) -> None:
        """要求：存下 path（转成 Path），并把文件读成 self.tasks: list[Task]。"""
        self.path = Path(path)
        self.tasks: list[Task] = self._load()
    # ------------------------------------------------------------ 持久化

    def _load(self) -> list[Task]:
        """把 JSON 文件读成 list[Task]。

        三个必须处理的情况：
          1. 文件不存在（第一次运行）→ []
          2. 文件存在但是空的/只有空白 → []（否则 json.loads("") 会炸）
          3. 正常 → [Task(**d) for d in data]
        """
        if not self.path.exists():
        #self.tasks 是 __init__ 里 self.tasks = self._load()
        #返回之后才赋值的——_load 执行时它压根还没生出来
        #所以用不用self.tasks
            return []
        with open(self.path,"r",encoding = "utf-8") as f:
            text = f.read()
            if not text.strip():
                return []
            try:
                data = json.loads(text)
                return [Task(**d) for d in data]

            except json.decoder.JSONDecodeError:
                raise TaskError(f"文件损坏{self.path}")

    def _save(self) -> None:
        """把 self.tasks 写进 path。要求（见文档 4.10）：

          - 父目录不存在时自动创建（mkdir(parents=True, exist_ok=True)）
          - 先写 path + ".tmp"，再 replace 到正式文件（防止写一半崩了毁掉原文件）
          - ensure_ascii=False 保证中文可读；indent=2 保证 human-readable
          - 用 asdict(t) 把 Task 转成 dict
        """
        self.path.parent.mkdir(parents = True,exist_ok = True)
        #详见deepen_python
        data = [asdict(t) for t in self.tasks]
        json_str = json.dumps(data, ensure_ascii=False,indent = 2)
        tmp_path = self.path.with_name(self.path.name + ".tmp")
        #错误理解（加上.tmp后缀）
        #正确理解（替换后缀即tasks.json  ->  tasks.tmp），即临时文件
        tmp_path.write_text(json_str,encoding = "utf-8")
        #写进替身
        tmp_path.replace(self.path)

        """ tmp_path = 刚买来的新空水桶（临时文件）。
            json_str = 干净的水（新数据）。
            self.path = 家里那个装了半桶脏水的旧水桶（旧文件）"""

    # ------------------------------------------------------------ 查询

    def get(self, task_id: int) -> Task:
        """按编号取一条，找不到抛 TaskNotFoundError。"""
        result = next((a for a in self.tasks if a.id == task_id),None)
        if  result is None:
            #这是Python界规矩
            #判断 None 一律用 is None，不要用 if not x
            raise TaskNotFoundError(task_id)
        return result


    def list(self, include_done: bool = False, course: str | None = None) -> list[Task]:
        """返回排好序的列表（返回新列表，不要就地 sort）。
        .sort就地排序，覆盖了
        sorted（）生成新列表
        sorted(要排序的列表, key=排序规则, reverse=是否倒序)
        lambda 参数: 返回值表达式
        过滤：
          - include_done=False 时排除已完成
          - course 不为 None 时只留该课程，比较时不区分大小写
        排序：有截止日期的在前 → 按日期由近到远 → 同一天按编号
        """
        result = [
            t for t in self.tasks
            if (include_done or not t.done)  #只要一个true即过
            and(course is None or (t.course is not None and t.course.lower() == course.lower()))
        ]#有点绕哈哈哈哈
        return sorted(
            result,
            key = lambda t :(t.due is None ,t.due or "",t.id),
            reverse = False
        )

    def upcoming(self, days: int = 7, today: date | None = None) -> list[Task]:
        """days 天内到期（含已逾期）的未完成任务，按截止日期排序。

        提示：limit = today + timedelta(days=days)，拿 due <= limit 过滤；直接复用 self.list()。
        """
        if today is None:
            today = date.today()
        limit = today + timedelta(days=days)
        str_limit = limit.isoformat()
        pending_list = self.list()
        return [
            _t for _t in pending_list
            if _t.due is not None and _t.due <= str_limit
        ]

    # ------------------------------------------------------------ 增

    def add(self, title: str, due: str | None = None, course: str | None = None) -> Task:
        """加一条任务并保存，返回新建的 Task。

        要求：
          - 标题 strip 后为空 → 抛 TaskError
          - 编号 = 当前最大 id + 1（不是 len + 1，编号永不复用）
          - due 要过 parse_due 校验
          - 改完 self.tasks 必须 _save()
        """
        title = title.strip()
        if not title:
            raise TaskError("任务标题不能为空")
        new_id = max([_t.id for _t in self.tasks], default=0) + 1
        new_task = Task(title = title,
                        id = new_id,
                        due = parse_due(due),
                        course = course,
                 )
        self.tasks.append(new_task)
        self._save()
        return new_task
    # ------------------------------------------------------------ 改 / 删

    def complete(self, task_id: int) -> Task:
        """标记完成并保存。"""
        goal = self.get(task_id)
        goal.done = True
        self._save()
        return goal

    def delete(self, task_id: int) -> Task:
        """删除并返回被删的那条，保存。"""
        goal = self.get(task_id)
        self.tasks.remove(goal)
        self._save()
        return goal

# ============================================================================
# 六、自测：写完之后在 PyCharm 里右键 Run 'task'，看输出
# ============================================================================

if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "tasks.json"
        store = TaskStore(path)

        store.add("C语言实验三", "2026-11-04", "C语言")
        store.add("高数习题 2.3", "2026-11-06", "高数")
        store.add("英语听力", course="英语")

        print("=== 1. 全部任务（默认只看未完成）===")
        for t in store.list():
            print("  ", t.describe())

        print("\n=== 2. 完成 #2 ===")
        print("  ", store.complete(2).describe())

        print("\n=== 3. 重新打开同一个文件（验证真的存下来了）===")
        reloaded = TaskStore(path)
        for t in reloaded.list(include_done=True):
            print("  ", t.describe())

        print("\n=== 4. 一周内到期 ===")
        for t in reloaded.upcoming(7):
            print("  ", t.describe())

        print("\n=== 5. 删除 #1 ===")
        print("   已删除：", reloaded.delete(1).title)
        print("   剩余：", [t.id for t in reloaded.list(include_done=True)])

        print("\n=== 6. 四种错误应该都被抓住 ===")
        for name, fn in (
            ("空标题", lambda: reloaded.add("   ")),
            ("日期格式错", lambda: reloaded.add("实验四", "10月20日")),
            ("编号不存在", lambda: reloaded.complete(99)),
        ):
            try:
                fn()
                print(f"   {name}: !!! 这里应该抛异常，却没有")
            except TaskError as e:
                print(f"   {name}: [{type(e).__name__}] {e}")

        print("\n=== 7. JSON 文件长这样 ===")
        print(path.read_text(encoding="utf-8"))
