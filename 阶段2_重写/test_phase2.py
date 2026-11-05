"""阶段 2 的验收测试。标准库就够，不联网、不花钱、不装包。

PyCharm：右键本文件 → Run 'Unittests in test_phase2'
命令行： cd 阶段2_重写 ; python -m unittest test_phase2 -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))

from phase2 import Config, FakeClient, PROVIDERS, create_client, load_config, load_dotenv

# 测试前后要清理的环境变量：不清理的话，测试之间会互相污染
ENV_KEYS = [
    "STUDYMATE_PROVIDER",
    "STUDYMATE_API_KEY",
    "STUDYMATE_BASE_URL",
    "STUDYMATE_MODEL",
]


class Base(unittest.TestCase):
    def setUp(self):
        # 暂存并清空真实环境里的 STUDYMATE_*，给每个测试一个干净的起点
        self._saved = {k: os.environ.pop(k, None) for k in ENV_KEYS}
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.env_file = self.dir / ".env"

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self._tmp.cleanup()


# ============================================================================
# .env 解析
# ============================================================================


class TestLoadDotenv(Base):
    def test_parses_simple_pairs(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            self.env_file.write_text("T_A=1\nT_B = 2\n", encoding="utf-8")
            load_dotenv(self.env_file)
            self.assertEqual(os.environ.get("T_A"), "1")
            self.assertEqual(os.environ.get("T_B"), "2")

    def test_skips_comments_and_blank_lines(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            self.env_file.write_text("# 这是注释\n\nT_C=3\n没有等号的行\n", encoding="utf-8")
            load_dotenv(self.env_file)
            self.assertEqual(os.environ.get("T_C"), "3")

    def test_strips_quotes(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            self.env_file.write_text('T_D="带双引号"\nT_E=\'单引号\'\n', encoding="utf-8")
            load_dotenv(self.env_file)
            self.assertEqual(os.environ.get("T_D"), "带双引号")
            self.assertEqual(os.environ.get("T_E"), "单引号")

    def test_does_not_override_existing_env(self):
        with mock.patch.dict(os.environ, {"T_F": "旧值"}):
            self.env_file.write_text("T_F=新值\n", encoding="utf-8")
            load_dotenv(self.env_file)
            self.assertEqual(os.environ["T_F"], "旧值", msg="已存在的环境变量优先，不能被 .env 覆盖")

    def test_missing_file_is_noop(self):
        load_dotenv(self.dir / "根本不存在.env")  # 不抛异常就算过


# ============================================================================
# 配置
# ============================================================================


class TestLoadConfig(Base):
    def test_defaults_to_fake(self):
        cfg = load_config(env_file=self.dir / "missing.env")
        self.assertEqual(cfg.provider, "fake")
        self.assertEqual(cfg.api_key, "")
        self.assertEqual(cfg.model, "fake")

    def test_reads_provider_preset(self):
        with mock.patch.dict(os.environ, {"STUDYMATE_PROVIDER": "deepseek"}, clear=False):
            cfg = load_config(env_file=self.dir / "missing.env")
            self.assertEqual(cfg.provider, "deepseek")
            self.assertEqual(cfg.base_url, PROVIDERS["deepseek"]["base_url"])
            self.assertEqual(cfg.model, PROVIDERS["deepseek"]["model"])

    def test_unknown_provider_raises(self):
        with mock.patch.dict(os.environ, {"STUDYMATE_PROVIDER": "openai"}, clear=False):
            with self.assertRaises(ValueError) as ctx:
                load_config(env_file=self.dir / "missing.env")
            self.assertIn("可选", str(ctx.exception), msg="报错要告诉用户有哪些合法值")

    def test_env_overrides_preset(self):
        with mock.patch.dict(
            os.environ,
            {
                "STUDYMATE_PROVIDER": "deepseek",
                "STUDYMATE_BASE_URL": "https://example.com/v1",
                "STUDYMATE_MODEL": "my-model",
            },
            clear=False,
        ):
            cfg = load_config(env_file=self.dir / "missing.env")
            self.assertEqual(cfg.base_url, "https://example.com/v1")
            self.assertEqual(cfg.model, "my-model")

    def test_reads_dotenv_file(self):
        self.env_file.write_text(
            "STUDYMATE_PROVIDER=deepseek\nSTUDYMATE_API_KEY=sk-test\n", encoding="utf-8"
        )
        cfg = load_config(env_file=self.env_file)
        self.assertEqual(cfg.provider, "deepseek")
        self.assertEqual(cfg.api_key, "sk-test")

    def test_config_equality(self):
        self.assertEqual(Config("fake", "", "", "fake"), Config("fake", "", "", "fake"))


# ============================================================================
# 创建客户端
# ============================================================================


class TestCreateClient(Base):
    def test_fake_provider_returns_fake_client(self):
        client = create_client(Config("fake", "", "", "fake"))
        self.assertIsInstance(client, FakeClient)

    def test_missing_api_key_raises_readable_error(self):
        with self.assertRaises(RuntimeError) as ctx:
            create_client(Config("deepseek", "", "https://api.deepseek.com", "deepseek-chat"))
        msg = str(ctx.exception)
        self.assertIn("API Key", msg)
        self.assertIn(".env", msg, msg="报错要直接告诉用户 .env 怎么写")


# ============================================================================
# 离线假客户端
# ============================================================================


class TestFakeClient(Base):
    def test_returns_scripted_text(self):
        client = FakeClient(script=["第一句"])
        resp = client.chat.completions.create(
            model="fake", messages=[{"role": "user", "content": "hi"}]
        )
        self.assertEqual(resp.choices[0].message.content, "第一句")

    def test_shape_matches_real_sdk(self):
        client = FakeClient(script=["x"])
        resp = client.chat.completions.create(model="fake", messages=[])
        self.assertEqual(resp.choices[0].message.role, "assistant")
        self.assertEqual(resp.choices[0].finish_reason, "stop")

    def test_records_calls(self):
        client = FakeClient(script=["a"])
        client.chat.completions.create(model="m1", messages=[{"role": "user", "content": "1"}])
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0]["model"], "m1")
        self.assertEqual(client.calls[0]["messages"][0]["content"], "1")

    def test_script_plays_in_order(self):
        client = FakeClient(script=["a", "b"])
        got = [
            client.chat.completions.create(model="fake", messages=[]).choices[0].message.content
            for _ in range(2)
        ]
        self.assertEqual(got, ["a", "b"])

    def test_exhausted_script_raises(self):
        client = FakeClient(script=["a"])
        client.chat.completions.create(model="fake", messages=[])
        with self.assertRaises(RuntimeError):
            client.chat.completions.create(model="fake", messages=[])

    def test_no_script_raises(self):
        client = FakeClient()
        with self.assertRaises(RuntimeError):
            client.chat.completions.create(model="fake", messages=[])

    def test_messages_are_copied(self):
        client = FakeClient(script=["ok"])
        messages = [{"role": "user", "content": "原始"}]
        client.chat.completions.create(model="fake", messages=messages)
        messages[0]["content"] = "被改了"
        self.assertEqual(client.calls[0]["messages"][0]["content"], "原始", msg="记录要留副本")

    def test_script_list_is_copied(self):
        script = ["a"]
        client = FakeClient(script=script)
        client.chat.completions.create(model="fake", messages=[])
        self.assertEqual(script, ["a"], msg="不能把调用方的列表吃掉")


if __name__ == "__main__":
    unittest.main(verbosity=2)
