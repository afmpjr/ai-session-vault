"""Unit tests for searching stored sessions."""

import tempfile
import unittest
from pathlib import Path

from ai_session_vault.search import parse_since, search_file, search_text


def _match_indices(text: str, query: str, case_sensitive: bool = False) -> list[int]:
    return [offset for offset, _ in search_text(text, query, case_sensitive)]


class SearchTextTests(unittest.TestCase):
    def test_finds_case_insensitive_substring(self) -> None:
        # "world" begins at offset 6 in "Hello World".
        self.assertEqual(_match_indices("Hello World", "world"), [6])

    def test_case_sensitive_respects_flag(self) -> None:
        self.assertEqual(_match_indices("Hello World", "world", case_sensitive=True), [])

    def test_multiple_occurrences(self) -> None:
        indices = _match_indices("abc abc abc", "abc")
        self.assertEqual(indices, [0, 4, 8])

    def test_no_match_returns_empty(self) -> None:
        self.assertEqual(_match_indices("abc", "zzz"), [])


class SearchSessionFileTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _make(self, name: str, text: str) -> Path:
        path = self.tmp / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_search_file_returns_line_numbers_and_snippets(self) -> None:
        path = self._make(
            "s.jsonl",
            '{"x": 1}\n{"message": {"role": "user", "content": "deploy the api"}}\n',
        )
        results = list(search_text(path.read_text(encoding="utf-8"), "deploy"))
        self.assertEqual(len(results), 1)

    def test_search_file_streaming_finds_matches_and_snippets(self) -> None:
        path = self._make(
            "stream.jsonl",
            '{"line": 1, "text": "alpha beta gamma"}\n'
            '{"line": 2, "text": "delta beta epsilon"}\n'
            '{"line": 3, "text": "zeta eta theta"}\n',
        )
        count, snippets = search_file(path, "beta")
        self.assertEqual(count, 2)
        self.assertEqual(len(snippets), 2)
        self.assertTrue(any("alpha beta gamma" in s for s in snippets))
        self.assertTrue(any("delta beta epsilon" in s for s in snippets))

    def test_search_file_empty_query_returns_zero(self) -> None:
        path = self._make("empty.jsonl", '{"a": 1}\n')
        count, snippets = search_file(path, "")
        self.assertEqual(count, 0)
        self.assertEqual(snippets, [])

    def test_search_file_respects_max_snippets(self) -> None:
        path = self._make("multi.jsonl", "match\nmatch\nmatch\nmatch\n")
        count, snippets = search_file(path, "match", max_snippets=2)
        self.assertEqual(count, 4)
        self.assertEqual(len(snippets), 2)


class ParseSinceTests(unittest.TestCase):
    NOW = 1_000_000.0

    def test_relative_units(self) -> None:
        self.assertEqual(parse_since("30m", now=self.NOW), self.NOW - 1800)
        self.assertEqual(parse_since("12h", now=self.NOW), self.NOW - 43200)
        self.assertEqual(parse_since("7d", now=self.NOW), self.NOW - 604800)
        self.assertEqual(parse_since("2w", now=self.NOW), self.NOW - 1209600)

    def test_iso_date_is_midnight_local(self) -> None:
        from datetime import datetime

        self.assertEqual(parse_since("2026-10-01"), datetime(2026, 10, 1).timestamp())

    def test_invalid_values_raise_value_error(self) -> None:
        for bad in ("", "abc", "7", "d7", "-3d", "7 days"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    parse_since(bad)


if __name__ == "__main__":
    unittest.main()