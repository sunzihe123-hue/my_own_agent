"""阶段 1 v2：StudyMate 的任务数据层。

在 PyCharm 里怎么跑
==================
1. PyCharm 打开的是项目根目录（也就是同时包含 studymate/ 和 .venv/ 的那一层，
   即 /Users/calvin/Documents/deepseek-harness-agent/studymate）
2. PyCharm → Settings（macOS 是 PyCharm → Preferences）
   → Project: studymate → Python Interpreter
   → 齿轮 / Add Interpreter → Add Local Interpreter → Existing
   → 选 项目根/.venv/bin/python
3. 打开本文件，在编辑区右键 → Run 'tasks'
   下方 Run 窗口应该看到 7 段输出

为什么本文件直接右键就能跑：
   本文件没有用相对导入（没有 from .xxx import），所以不需要按"模块"方式运行。
   阶段 1 v4 的 cli.py 会用到相对导入，那时候才必须用 python -m studymate.cli。

本文件的三个设计原则
==================
1. 数据层只管数据，不 print。打印交给 cli.py / 网页 / MCP。
   因为同一份数据要被三个不同界面的程序复用，谁 print 谁就被绑死在一个界面上。
2. 出错抛异常，不用返回值表示失败。
   C 的 return -1 调用方经常忘了检查；异常会一路往上抛，不处理就崩，逼你面对。
3. 校验只在一个地方做（add 和 edit）。
   校验散落在各处，改规则时必然漏改一处，然后就出现"cli 能加空标题、网页不能加"这种鬼事。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# ============================================================================
# 一、异常
# ============================================================================


class StudyMateError(Exception):
    """本项目所有业务异常的基类。

    作用：给所有"可预期的错误"一个共同祖先。
    为什么需要：调用方可以只写一句 except StudyMateError 就接住全部业务错误，
               而不用把每个子类都列一遍；同时还能把"业务错误"和"程序 bug"
               （比如 AttributeError）区分开——后者不该被吞掉。
    为什么里面是空的：它只负责"分类"，不带任何行为。
    """


class InvalidTaskError(StudyMateError):
    """数据不合法：标题为空、日期格式错、priority 越界。

    为什么单独一个类：调用方想"让用户重新输入"时，抓这个类就够了，
                     不用去分辨 TaskNotFoundError。
    """


class TaskNotFoundError(StudyMateError):
    """按编号找不到任务。

    为什么要把 task_id 存成属性：调用方 catch 之后可能想提示
    "没有 #7 这条，你要不要看看 #1-#5"，需要拿到原始编号重新组织语言。
    如果只把编号拼进消息字符串，调用方就只能对着字符串做正则，很难看。
    """

    def __init__(self, task_id: int) -> None:
        super().__init__(f"找不到编号为 {task_id} 的任务")
        self.task_id = task_id


# ============================================================================
# 二、日期工具
# ============================================================================


def _normalize_due(due: str | None) -> str | None:
    """把用户给的日期字符串统一成 YYYY-MM-DD。

    作用：收口所有"日期字符串"的校验和规范化。
    为什么需要一个单独的私有函数：
      - add() 和 edit() 都要校验日期，写两遍必然有一天改了一处忘了另一处；
      - 开头的下划线是 Python 的约定：内部函数，外部别调，不是给使用者用的。

    为什么存字符串而不存 date 对象：
      v3 要把任务写进 JSON，而 JSON 只认字符串/数字/布尔/null。
      存 date 对象的话，每次存和读都要手动转换；存字符串则原样进出，
      需要计算时再 date.fromisoformat() 转一下。少一层转换就少一类 bug。

    为什么错误信息写得这么长：
      阶段 3 里，这句话会原样发给大模型。模型看到"请用 YYYY-MM-DD"
      就会自己改正后重新调用；只写 "invalid date" 它只能瞎猜。
    """
    if due is None:
        return None
    text = due.strip()
    if not text:
        return None
    try:
        # fromisoformat 同时干两件事：校验格式 + 把 "2026-1-4" 规范成 "2026-01-04"
        return date.fromisoformat(text).isoformat()
    except ValueError:
        # from None 的作用：不让报错里出现 "During handling of the above exception..."
        # 我们要给用户的是一句清楚的话，不是 Python 的内部调用链。
        raise InvalidTaskError(
            f"日期格式不对：「{text}」。请用 YYYY-MM-DD，例如 2026-10-14"
        ) from None


# ============================================================================
# 三、任务对象
# ============================================================================


@dataclass
class Task:
    """一条任务。

    作用：把"一条任务"的所有字段打包成一个类型，替代你 v1 里的 dict。
    为什么用 dataclass 而不是 dict：
      - dict 的键是字符串，写错键名（"titel"）只有运行时才报，而且报在很远的地方；
      - dataclass 写错属性名，PyCharm 当场标红；
      - 字段有默认值，不用每次写全；
      - PyCharm 能补全 task.title / task.due，dict 不行。
    为什么字段顺序是这样：
      id 和 title 没有默认值，必须排前面；有默认值的排后面。
      这是 Python 语法强制要求的，否则报 "non-default argument follows default argument"。
    """

    id: int
    title: str
    due: str | None = None        # 没有截止日期就是 None
    course: str | None = None     # 没分类就是 None
    done: bool = False
    priority: int = 2             # 1 高 / 2 中 / 3 低

    # ---------------------------------------------------------------- 方法

    def days_left(self, today: date | None = None) -> int | None:
        """距截止日期还有几天。没有 due 返回 None，负数表示已逾期。

        作用：把"日期差计算"收在一处。
        为什么需要：describe() 要用它、upcoming() 要用它、阶段 3 的工具也要用它。
                   如果每处都自己写一遍 date.fromisoformat(...) - date.today()，
                   某天发现"已逾期"该按自然日算，就要改三处。
        为什么有个 today 参数：测试的时候需要固定"今天"，否则写出来的测试
                   过一天就失败（比如断言"还剩 6 天"，明天就变 5 天了）。
                   这是"依赖注入"的最小形态——不在函数里写死 date.today()。
        """
        if not self.due:
            return None
        return (date.fromisoformat(self.due) - (today or date.today())).days

    def describe(self) -> str:
        """返回一行人类可读的描述。

        作用：规定"一条任务长什么样"的唯一格式。
        为什么放在 Task 里而不是 cli 里：
          命令行、网页、MCP、给模型看的工具结果，四个地方都要展示任务。
          格式写在数据上，四处共用；写在 cli 里，网页就得再抄一遍。
        为什么返回字符串而不 print：数据层不打印，见文件开头原则 1。

        输出的几种形态：
          □ #1 C语言实验三 [C语言] 截止 2026-11-04（还剩 6 天） 高优先级
          □ #2 高数习题 [高数] 截止 2026-10-20（已逾期 3 天）
          □ #3 英语听力 [英语] 截止 2026-10-29（今天到期）
          ☑ #4 线代作业 原定 2026-10-25，已完成
          □ #5 读书笔记 无截止日期
        """
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
                # 负数取反再显示，避免出现"还剩 -3 天"这种别扭的话
                parts.append(f"截止 {self.due}（已逾期 {-left} 天）")
            elif left == 0:
                parts.append(f"截止 {self.due}（今天到期）")
            else:
                parts.append(f"截止 {self.due}（还剩 {left} 天）")

        if self.priority == 1:
            parts.append("高优先级")
        elif self.priority == 3:
            parts.append("低优先级")
        # priority == 2（中）是默认值，不显示，减少噪音

        return " ".join(parts)


# ============================================================================
# 四、仓库
# ============================================================================


class TaskStore:
    """所有任务的容器。

    作用：管理一批任务——加、查、改、删、排序、算到期。
    为什么用类而不是你 v1 的模块级全局列表：
      1. 全局列表一个程序只能有一份。阶段 4 写测试时，每个测试都要干净的起点，
         全局列表做不到，测试之间会互相污染，而且顺序一换就挂。
      2. 类可以实例化多份：TaskStore() 给测试用，TaskStore(从 JSON 读出来的) 给真用。
      3. v3 加持久化时，只需要改这个类，外部代码一行不用动。
    """

    def __init__(self, tasks: list[Task] | None = None) -> None:
        """初始化。

        作用：把任务列表存成实例属性。
        为什么用 list(tasks or []) 而不是 self.tasks = tasks or []：
          直接赋值的话，传进来的列表和 self.tasks 是同一个对象，
          外面改动那个列表，store 也会跟着变（就是前面热身实验里的那条分界线）。
          用 list(...) 复制一份，两者互不影响。
        为什么默认值是 None 而不是 []：
          Python 的默认参数只在函数定义时求值一次。如果写 tasks=[]，
          所有 TaskStore 实例会共享同一个列表——这是 Python 最经典的坑之一。
        """
        self.tasks: list[Task] = list(tasks or [])

    # ------------------------------------------------------------------ 内部

    def _next_id(self) -> int:
        """下一个可用编号。

        作用：生成永不复用的任务编号。
        为什么不用 len(self.tasks) + 1：
          删掉 #2 之后列表长度退回 2，下一条又会拿到 2，和历史编号撞车。
          用"当前最大值 +1"，编号只增不减，永远不会重复。
        为什么要 default=0：
          max() 对空列表会抛 ValueError；default=0 让它返回 0，空列表时 id 从 1 开始。
        为什么用生成器表达式而不是列表推导：
          max((t.id for t in ...)) 不会先在内存里造一个新列表，任务多时更省。
        """
        return max((t.id for t in self.tasks), default=0) + 1

    def _locate(self, task_id: int) -> int:
        """返回任务在 self.tasks 里的下标，找不到抛 TaskNotFoundError。

        作用：把"按 id 找位置"收口。
        为什么返回下标而不是对象：
          删除需要下标（list.pop(下标)），修改需要对象（改属性）。
          返回下标，get 用它取对象，delete 用它 pop，两种需求都满足。
        为什么用 enumerate 而不是 range(len(...))：
          C 里写 for (i = 0; i < n; i++) tasks[i] 很自然，但 Python 里
          enumerate 同时给下标和元素，少一次按下标取值（也少一次越界机会）。
        """
        for i, t in enumerate(self.tasks):
            if t.id == task_id:
                return i
        raise TaskNotFoundError(task_id)

    # -------------------------------------------------------------------- 增

    def add(
        self,
        title: str,
        due: str | None = None,
        course: str | None = None,
        priority: int = 2,
    ) -> Task:
        """加一条任务，返回新建的 Task。

        作用：唯一的新增入口，负责分配编号 + 校验 + 归一化。
        为什么把所有校验都堆在这一个方法里：
          校验散落是 bug 之源。只要 add 收口了，cli / 网页 / agent 三条路径
          都不可能绕过它，规则改了也只改这里。
        为什么返回 Task 而不是 None：
          调用方刚加完，通常要回显"已添加 #7"或拿到编号继续操作。
          返回对象比让调用方再去 get 一次方便得多。
        """
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

    # -------------------------------------------------------------------- 查

    def get(self, task_id: int) -> Task:
        """按编号取一条，找不到抛 TaskNotFoundError。

        作用：带校验的单条读取。
        为什么抛异常而不是返回 None：
          返回 None 的话，调用方接下来 t.title 会报 AttributeError，
          报错的地方离真正的原因（编号不存在）很远，很难查。
          抛异常则错误在出事的瞬间暴露，而且消息直接说明原因。
        """
        return self.tasks[self._locate(task_id)]

    def list(self, include_done: bool = True) -> list[Task]:
        """返回排好序的列表。

        作用：把"任务该怎么排"固化成规则，所有界面用同一个顺序。
        排序规则：有截止日期的在前 → 按日期由近到远 → 同一天按编号。

        为什么 key 返回元组：Python 会比较元组的第一项，相同再比第二项，依此类推。
          t.due is None 得到 False/True，False(0) 排前面 → 有日期的在前；
          t.due or "" 把 None 变成空串，避免 None 和 str 比较报错；
          t.id 兜底，保证排序结果稳定（同样的输入永远同样的顺序）。
        为什么返回新列表而不是就地排序：
          就地 sort 会改动 self.tasks 的顺序，
          调用方只是"看一下"却把内部状态改了，后面出问题很难追。

        参数 include_done=False 时只返回未完成的，给"待办清单"用。
        """
        items = [t for t in self.tasks if include_done or not t.done]
        return sorted(items, key=lambda t: (t.due is None, t.due or "", t.id))

    def upcoming(self, days: int = 7, today: date | None = None) -> list[Task]:
        """days 天内到期（含已逾期）的未完成任务，按截止日期排序。

        作用：回答"我最近有什么快到期的"——这是 StudyMate 最高频的问题之一。
        为什么已逾期的也算进来：
          逾期任务比未来任务更紧急，把它排除掉正好漏掉最该处理的。
        为什么跳过 done：已经做完的不需要再提醒。
        为什么要 today 参数：同 days_left，测试需要固定"今天"。
        """
        today = today or date.today()
        result = []
        for t in self.tasks:
            if t.done:
                continue
            left = t.days_left(today)
            if left is not None and left <= days:
                result.append(t)
        return sorted(result, key=lambda t: (t.due or "", t.id))

    # -------------------------------------------------------------------- 改

    def complete(self, task_id: int) -> Task:
        """标记完成，返回那条任务。

        作用：唯一的"完成"入口。
        为什么改的是对象属性而不是替换一条新 Task：
          Task 是可变对象，直接改 task.done 就是改仓库里的那一条；
          替换成新对象会让其他人持有的引用指向旧的那条。
        """
        task = self.get(task_id)
        task.done = True
        return task

    def edit(
        self,
        task_id: int,
        title: str | None = None,
        due: str | None = None,
        course: str | None = None,
        priority: int | None = None,
    ) -> Task:
        """只改传进来的字段。

        作用：1.3 练习 3。
        为什么默认值是 None 而不是空串：
          None 表示"这个字段别动"，空串表示"把它改成空"。
          只有用 None 才能区分这两种意图。
        为什么每个字段都要重新校验：
          edit 也是写入口，绕过校验就等于给 add 的校验开了个后门。
        """
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

    # -------------------------------------------------------------------- 删

    def delete(self, task_id: int) -> Task:
        """删掉并返回被删的那条。

        作用：删除。
        为什么返回被删对象：
          界面可以回显"已删除 #3 英语听力"，比只说"删除成功"友好得多；
          阶段 3 里，工具函数的返回值会原样发给大模型，
          带上标题它才知道自己删对了没有。
        """
        return self.tasks.pop(self._locate(task_id))

    # ------------------------------------------------------------------ 杂项

    def __len__(self) -> int:
        """让 len(store) 直接可用。

        作用：提供"有多少条"的读法。
        为什么要有：否则调用方得写 len(store.tasks)，等于把内部实现暴露出去。
                   以后如果改成"从数据库分页读"，只要 __len__ 还能算对，
                   调用方一行都不用改。
        """
        return len(self.tasks)

    def __iter__(self):
        """让 for t in store 直接可用。"""
        return iter(self.tasks)


# ============================================================================
# 五、自测：右键 Run 看这里
# ============================================================================

if __name__ == "__main__":
    store = TaskStore()
    store.add("C语言实验三", due="2026-11-04", course="C语言", priority=1)
    store.add("高数习题 2.3", due="2026-11-06", course="高数")
    store.add("英语听力", course="英语", priority=3)
    store.add("线代作业", due="2026-10-25", course="线代")

    print("=== 1. 全部任务（已排序）===")
    for t in store.list():
        print("  ", t.describe())

    print("\n=== 2. 只看未完成 ===")
    for t in store.list(include_done=False):
        print("  ", t.describe())

    print("\n=== 3. 完成 #2 ===")
    print("  ", store.complete(2).describe())

    print("\n=== 4. 一周内到期（含逾期）===")
    for t in store.upcoming(7):
        print("  ", t.describe())

    print("\n=== 5. 修改 #3 ===")
    print("  ", store.edit(3, title="英语听力 Unit 4", due="2026-11-10").describe())

    print("\n=== 6. 删除 #1 ===")
    print("   已删除：", store.delete(1).title)
    print("   剩余编号：", [t.id for t in store.tasks], "  共", len(store), "条")

    print("\n=== 7. 四种错误都应该被抓住 ===")
    for name, fn in (
        ("空标题", lambda: store.add("   ")),
        ("日期格式错", lambda: store.add("实验四", due="10月20日")),
        ("priority 越界", lambda: store.add("实验五", priority=9)),
        ("编号不存在", lambda: store.complete(99)),
    ):
        try:
            fn()
            print(f"   {name}: !!! 这里应该抛异常，却没有")
        except StudyMateError as e:
            print(f"   {name}: [{type(e).__name__}] {e}")