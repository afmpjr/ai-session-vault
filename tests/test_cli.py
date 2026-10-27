"""Unit tests for the CLI dispatcher (subcommand wiring only)."""

import json
import os
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from ai_session_vault import cli


class CliDispatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_no_args_returns_usage_error_code(self) -> None:
        with patch("sys.argv", ["asv"]):
            result = cli.main()
        self.assertEqual(result, 2)

    def test_init_subcommand_creates_vault(self) -> None:
        vault_dir = self.tmp / "vault"
        with patch("sys.argv", ["asv", "init", str(vault_dir)]):
            result = cli.main()
        self.assertEqual(result, 0)
        self.assertTrue((vault_dir / ".git").exists())

    def test_version_flag_succeeds(self) -> None:
        with patch("sys.argv", ["asv", "--version"]):
            result = cli.main()
        self.assertEqual(result, 0)

    def test_resolve_vault_prefers_cwd_when_it_is_a_vault(self) -> None:
        from pathlib import Path as _Path

        vault_dir = self.tmp / "vault"
        cli.Vault.init(vault_dir)
        with patch("ai_session_vault.cli.Path.cwd", return_value=vault_dir):
            vault = cli._resolve_vault(None)
        self.assertEqual(vault.root, vault_dir.resolve())

    def test_resolve_vault_falls_back_to_default_when_cwd_is_not_vault(self) -> None:
        with patch("ai_session_vault.cli.Path.cwd", return_value=self.tmp):
            vault = cli._resolve_vault(None)
        self.assertEqual(vault.root, cli.DEFAULT_VAULT.resolve())

    def test_config_set_path_persists_in_vault_json(self) -> None:
        from io import StringIO

        vault_dir = self.tmp / "vault"
        cli.Vault.init(vault_dir)
        with patch("sys.argv", ["asv", "config", "set", "paths.claude", "*.jsonl", "--vault", str(vault_dir)]):
            result = cli.main()
        self.assertEqual(result, 0)
        config = cli.VaultConfig.load(vault_dir / "vault.json")
        self.assertEqual(config.get_path("claude"), "*.jsonl")

    def test_config_get_prints_the_stored_pattern(self) -> None:
        from io import StringIO

        vault_dir = self.tmp / "vault"
        cli.Vault.init(vault_dir)
        with patch("sys.argv", ["asv", "config", "set", "paths.claude", "custom/*.jsonl", "--vault", str(vault_dir)]):
            cli.main()
        with patch("sys.argv", ["asv", "config", "get", "paths.claude", "--vault", str(vault_dir)]):
            out = StringIO()
            with patch("sys.stdout", out):
                result = cli.main()
        self.assertEqual(result, 0)
        self.assertIn("custom/*.jsonl", out.getvalue())

    def test_config_get_missing_key_returns_error(self) -> None:
        vault_dir = self.tmp / "vault"
        cli.Vault.init(vault_dir)
        with patch("sys.argv", ["asv", "config", "get", "paths.doesnotexist", "--vault", str(vault_dir)]):
            result = cli.main()
        self.assertEqual(result, 2)

    def test_discover_lists_matching_session_files(self) -> None:
        from io import StringIO

        vault_dir = self.tmp / "vault"
        cli.Vault.init(vault_dir)
        session_dir = self.tmp / "sessions"
        session_dir.mkdir()
        (session_dir / "aaa.jsonl").write_text('{"type": "user", "message": {"role": "user", "content": "hi"}}\n', encoding="utf-8")
        with patch("sys.argv", ["asv", "config", "set", "paths.codex", str(session_dir / "*.jsonl"), "--vault", str(vault_dir)]):
            cli.main()
        with patch("sys.argv", ["asv", "discover", "--runtime", "codex", "--vault", str(vault_dir)]):
            out = StringIO()
            with patch("sys.stdout", out):
                result = cli.main()
        self.assertEqual(result, 0)
        self.assertIn("codex", out.getvalue())
        self.assertIn(str(session_dir / "aaa.jsonl"), out.getvalue())

    def test_sync_subcommand_adds_and_commits(self) -> None:
        from io import StringIO

        vault_dir = self.tmp / "vault"
        cli.Vault.init(vault_dir)
        session_dir = self.tmp / "sessions"
        session_dir.mkdir()
        (session_dir / "sync_sample.jsonl").write_text('{"type": "user", "message": {"role": "user", "content": "hi"}}\n', encoding="utf-8")
        with patch("sys.argv", ["asv", "config", "set", "paths.claude", str(session_dir / "*.jsonl"), "--vault", str(vault_dir)]):
            cli.main()

        out = StringIO()
        with patch("sys.stdout", out), patch("sys.argv", ["asv", "sync", "--runtime", "claude", "--vault", str(vault_dir), "--json"]):
            result = cli.main()
        self.assertEqual(result, 0)
        self.assertIn('"discovered": 1', out.getvalue())
        self.assertIn('"added": 1', out.getvalue())

    def test_config_set_storage_repack_persists(self) -> None:
        from io import StringIO

        vault_dir = self.tmp / "vault"
        cli.Vault.init(vault_dir)
        with patch("sys.argv", ["asv", "config", "set", "storage.repack.enabled", "false", "--vault", str(vault_dir)]):
            result = cli.main()
        self.assertEqual(result, 0)

        out = StringIO()
        with patch("sys.stdout", out), patch("sys.argv", ["asv", "config", "get", "storage.repack.enabled", "--vault", str(vault_dir)]):
            result = cli.main()
        self.assertEqual(result, 0)
        self.assertIn("False", out.getvalue())

    def test_status_reports_storage_health(self) -> None:
        from io import StringIO

        vault_dir = self.tmp / "vault"
        cli.Vault.init(vault_dir)
        out = StringIO()
        with patch("sys.stdout", out), patch("sys.argv", ["asv", "status", "--vault", str(vault_dir)]):
            result = cli.main()
        self.assertEqual(result, 0)
        self.assertIn("storage:", out.getvalue())

    def test_export_session_text_format(self) -> None:
        from io import StringIO

        vault_dir = self.tmp / "vault"
        cli.Vault.init(vault_dir)
        session_dir = vault_dir / "sessions" / "claude"
        session_dir.mkdir(parents=True)
        sample = session_dir / "ses_test.jsonl"
        sample.write_text('{"type": "user", "message": {"role": "user", "content": "hello"}}\n', encoding="utf-8")
        cli.Vault.open(vault_dir).add_session(sample, "claude")

        out = StringIO()
        with patch("sys.stdout", out), patch("sys.argv", ["asv", "export", "ses_test", "--vault", str(vault_dir)]):
            result = cli.main()
        self.assertEqual(result, 0)
        self.assertIn("user: hello", out.getvalue())

    def test_export_session_json_format(self) -> None:
        from io import StringIO

        vault_dir = self.tmp / "vault"
        cli.Vault.init(vault_dir)
        session_dir = vault_dir / "sessions" / "claude"
        session_dir.mkdir(parents=True)
        sample = session_dir / "ses_test.jsonl"
        sample.write_text('{"type": "user", "message": {"role": "user", "content": "hello"}}\n', encoding="utf-8")
        cli.Vault.open(vault_dir).add_session(sample, "claude")

        out = StringIO()
        with patch("sys.stdout", out), patch("sys.argv", ["asv", "export", "ses_test", "--vault", str(vault_dir), "--format", "json"]):
            result = cli.main()
        self.assertEqual(result, 0)
        import json as _json
        data = _json.loads(out.getvalue())
        self.assertEqual(data["session_id"], "ses_test")
        self.assertEqual(data["runtime"], "claude")

    def test_export_missing_session_returns_error(self) -> None:
        vault_dir = self.tmp / "vault"
        cli.Vault.init(vault_dir)
        with patch("sys.argv", ["asv", "export", "nonexistent", "--vault", str(vault_dir)]):
            result = cli.main()
        self.assertEqual(result, 1)

    def test_repack_command_runs(self) -> None:
        from io import StringIO

        vault_dir = self.tmp / "vault"
        cli.Vault.init(vault_dir)
        out = StringIO()
        with patch("sys.stdout", out), patch("sys.argv", ["asv", "repack", "--vault", str(vault_dir)]):
            result = cli.main()
        self.assertEqual(result, 0)
        self.assertIn("repacked", out.getvalue())


class FindFilterTests(unittest.TestCase):
    """`asv find` filters (--limit, --runtime, --since) and mtime ordering."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.vault_dir = Path(self._tmp.name) / "vault"
        cli.Vault.init(self.vault_dir)
        base = self.vault_dir / "sessions"
        # (runtime, session id, age in seconds)
        for runtime, session_id, age in [
            ("claude", "old", 10 * 86400),
            ("claude", "mid", 2 * 86400),
            ("opencode", "new", 60),
        ]:
            runtime_dir = base / runtime
            runtime_dir.mkdir(parents=True, exist_ok=True)
            path = runtime_dir / f"{session_id}.jsonl"
            path.write_text('{"text": "needle here"}\n', encoding="utf-8")
            stamp = time.time() - age
            os.utime(path, (stamp, stamp))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _find(self, *extra: str) -> tuple[int, list[dict]]:
        out = StringIO()
        argv = ["asv", "find", "needle", "--vault", str(self.vault_dir), "--json", *extra]
        with patch("sys.stdout", out), patch("sys.argv", argv):
            code = cli.main()
        return code, (json.loads(out.getvalue()) if code == 0 else [])

    def test_orders_most_recently_modified_first(self) -> None:
        code, results = self._find()
        self.assertEqual(code, 0)
        self.assertEqual([r["session_id"] for r in results], ["new", "mid", "old"])

    def test_limit_keeps_the_most_recent(self) -> None:
        _, results = self._find("--limit", "2")
        self.assertEqual([r["session_id"] for r in results], ["new", "mid"])

    def test_limit_below_one_is_a_usage_error(self) -> None:
        code, _ = self._find("--limit", "0")
        self.assertEqual(code, 2)

    def test_runtime_filter(self) -> None:
        _, results = self._find("--runtime", "claude")
        self.assertEqual([r["session_id"] for r in results], ["mid", "old"])

    def test_since_relative_excludes_older_sessions(self) -> None:
        _, results = self._find("--since", "3d")
        self.assertEqual([r["session_id"] for r in results], ["new", "mid"])

    def test_since_iso_date(self) -> None:
        tomorrow = (datetime.now() + timedelta(days=1)).date().isoformat()
        _, results = self._find("--since", tomorrow)
        self.assertEqual(results, [])

    def test_since_invalid_value_is_a_usage_error(self) -> None:
        code, _ = self._find("--since", "yesterday-ish")
        self.assertEqual(code, 2)

    def test_filters_combine(self) -> None:
        _, results = self._find("--runtime", "claude", "--since", "3d", "--limit", "1")
        self.assertEqual([r["session_id"] for r in results], ["mid"])


if __name__ == "__main__":
    unittest.main()