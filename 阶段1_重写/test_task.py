"""task.py 的验收测试。标准库就够，不联网、不用装包。

PyCharm：右键本文件 → Run 'Unittests in test_task'
命令行： cd 阶段1_重写 ; python -m unittest test_task -v

红 → 绿就是你的进度条。测试不要改。
"""

import sys
import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

# 让 PyCharm 的测试运行器不管工作目录设成哪，都能找到同目录的 task.py
sys.path.insert(0, str(Path(__file__).parent))

from task import Task, TaskError, TaskNotFoundError, TaskStore, parse_due


# ============================================================================
# 日期校验
# ============================================================================


class TestParseDue(unittest.TestCase):
    def test_none_and_blank_are_none(self):
        for value in (None, "", "   "):
            self.assertIsNone(parse_due(value), msg=f"parse_due({value!r}) 应该返回 None")

    def test_normalize_to_iso(self):
        self.assertEqual(parse_due("20261020"), "2026-10-20", msg="紧凑格式要归一成带横线的")
        self.assertEqual(parse_due(" 2026-10-20 "), "2026-10-20", msg="两头空格要去掉")

    def test_bad_format_raises_task_error(self):
        with self.assertRaises(TaskError):
            parse_due("10月20日")

    def test_unpadded_month_is_rejected(self):
        # 坑：date.fromisoformat 不接受 "2026-1-4"（ISO 要求月和日补零），
        # 所以这里必须抛 TaskError，不能指望它帮你"规范成 2026-01-04"。
        with self.assertRaises(TaskError):
            parse_due("2026-1-4")


# ============================================================================
# Task 自身的行为
# ============================================================================


class TestTask(unittest.TestCase):
    def test_created_at_is_filled(self):
        task = Task(id=1, title="a")
        self.assertIsInstance(task.created_at, str)
        self.assertTrue(task.created_at, msg="created_at 不能是空串")
        datetime.fromisoformat(task.created_at)  # 解析不了就抛 ValueError → 测试失败

    def test_defaults(self):
        task = Task(id=1, title="a")
        self.assertIsNone(task.due)
        self.assertIsNone(task.course)
        self.assertFalse(task.done)

    def test_days_left(self):
        task = Task(id=1, title="a", due="2026-10-12")
        self.assertEqual(task.days_left(date(2026, 10, 10)), 2)
        self.assertEqual(task.days_left(date(2026, 10, 12)), 0)
        self.assertEqual(task.days_left(date(2026, 10, 15)), -3)
        self.assertIsNone(Task(id=2, title="b").days_left(date(2026, 10, 10)))

    def test_describe(self):
        today = date(2026, 10, 10)
        self.assertIn("还剩 2 天", Task(id=1, title="作业", due="2026-10-12").describe(today))
        self.assertIn("已逾期 5 天", Task(id=2, title="作业", due="2026-10-05").describe(today))
        self.assertIn("今天", Task(id=3, title="作业", due="2026-10-10").describe(today))

    def test_describe_without_due_and_when_done(self):
        today = date(2026, 10, 10)
        no_due = Task(id=1, title="读书笔记").describe(today)
        self.assertIn("#1 读书笔记", no_due)
        self.assertNotIn("截止", no_due)

        done = Task(id=2, title="作业", due="2026-10-12", done=True).describe(today)
        self.assertIn("截止 2026-10-12", done)
        self.assertNotIn("还剩", done)

    def test_describe_shows_course(self):
        text = Task(id=1, title="作业", course="C语言").describe(date(2026, 10, 10))
        self.assertIn("[C语言]", text)


# ============================================================================
# TaskStore：需要临时目录，每个测试一个干净的起点
# ============================================================================


class StoreTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.path = self.dir / "tasks.json"

    def tearDown(self):
        self._tmp.cleanup()

    def new_store(self) -> TaskStore:
        """同一个文件新建一个 store —— 验证"存盘"的标准做法。"""
        return TaskStore(self.path)


class TestStorePersistence(StoreTest):
    def test_missing_file_is_empty_store(self):
        self.assertEqual(self.new_store().list(include_done=True), [])

    def test_blank_file_is_empty_store(self):
        self.path.write_text("   \n", encoding="utf-8")
        self.assertEqual(self.new_store().list(include_done=True), [])

    def test_add_is_persisted(self):
        self.new_store().add("C语言实验三", "2026-10-20", "C语言")
        task = self.new_store().get(1)
        self.assertEqual(task.title, "C语言实验三")
        self.assertEqual(task.due, "2026-10-20")
        self.assertEqual(task.course, "C语言")

    def test_json_file_is_plain_dicts(self):
        self.new_store().add("x")
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertIsInstance(data, list)
        self.assertEqual(data[0]["title"], "x")
        self.assertIn("created_at", data[0], msg="Task 的所有字段都应该写进 JSON")

    def test_save_creates_missing_directories(self):
        deep = self.dir / "a" / "b" / "tasks.json"
        TaskStore(deep).add("x")
        self.assertTrue(deep.exists(), msg="父目录不存在时 _save 应该自己创建")

    def test_two_stores_append_to_same_file(self):
        self.new_store().add("x")
        self.new_store().add("y")
        titles = [t.title for t in self.new_store().list(include_done=True)]
        self.assertEqual(titles, ["x", "y"])


class TestStoreAdd(StoreTest):
    def test_add_returns_task_and_assigns_ids(self):
        store = self.new_store()
        first = store.add("第一")
        second = store.add("第二")
        self.assertEqual((first.id, second.id), (1, 2))
        self.assertEqual(len(store.list(include_done=True)), 2)

    def test_ids_are_not_reused_after_delete(self):
        store = self.new_store()
        store.add("a")
        store.add("b")
        store.delete(1)
        self.assertEqual(store.add("c").id, 3, msg="编号只增不减，删过也不复用")

    def test_empty_title_rejected(self):
        with self.assertRaises(TaskError):
            self.new_store().add("   ")

    def test_bad_date_rejected(self):
        with self.assertRaises(TaskError):
            self.new_store().add("x", "10月20日")

    def test_blank_due_becomes_none(self):
        task = self.new_store().add("x", "")
        self.assertIsNone(task.due)


class TestStoreQuery(StoreTest):
    def test_get_missing_raises_with_id(self):
        with self.assertRaises(TaskNotFoundError) as ctx:
            self.new_store().get(42)
        self.assertEqual(ctx.exception.task_id, 42)

    def test_list_hides_done_by_default(self):
        store = self.new_store()
        store.add("a")
        store.add("b")
        store.complete(1)
        self.assertEqual([t.title for t in store.list()], ["b"])
        self.assertEqual([t.title for t in store.list(include_done=True)], ["a", "b"])

    def test_list_sorts_dated_first(self):
        store = self.new_store()
        store.add("无日期")
        store.add("晚", "2026-12-01")
        store.add("早", "2026-10-11")
        self.assertEqual([t.title for t in store.list()], ["早", "晚", "无日期"])

    def test_list_filters_course_ignoring_case(self):
        store = self.new_store()
        store.add("a", course="C语言")
        store.add("b", course="高数")
        self.assertEqual([t.title for t in store.list(course="c语言")], ["a"])

    def test_upcoming_includes_overdue_skips_done_and_far(self):
        store = self.new_store()
        store.add("逾期", "2026-10-01")
        store.add("近", "2026-10-12")
        store.add("远", "2026-11-30")
        store.add("已完成", "2026-10-11")
        store.complete(4)
        got = [t.title for t in store.upcoming(7, today=date(2026, 10, 10))]
        self.assertEqual(got, ["逾期", "近"], msg="逾期要算进来，已完成的要排除")


class TestStoreChange(StoreTest):
    def test_complete_is_persisted(self):
        store = self.new_store()
        store.add("a")
        self.assertTrue(store.complete(1).done)
        self.assertTrue(self.new_store().get(1).done, msg="complete 之后要存盘")

    def test_delete_returns_task_and_persists(self):
        store = self.new_store()
        store.add("a")
        store.add("b")
        gone = store.delete(1)
        self.assertEqual(gone.title, "a")
        self.assertEqual([t.title for t in self.new_store().list(include_done=True)], ["b"])

    def test_change_missing_task(self):
        store = self.new_store()
        with self.assertRaises(TaskNotFoundError):
            store.complete(99)
        with self.assertRaises(TaskNotFoundError):
            store.delete(99)


if __name__ == "__main__":
    unittest.main(verbosity=2)
