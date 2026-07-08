"""Tests for core.logbuf — must run without bpy."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import logbuf


class TestFormatEntry:
    def test_format(self):
        assert logbuf.format_entry("hello", "2026-07-02 10:00:00") == \
            "[2026-07-02 10:00:00] hello\n"


class TestAppendCapped:
    def test_simple_append(self):
        assert logbuf.append_capped("a\n", "b\n") == "a\nb\n"

    def test_caps_to_max_lines(self):
        log = "".join(f"line{i}\n" for i in range(5))
        result = logbuf.append_capped(log, "new\n", max_lines=3)
        assert result == "line3\nline4\nnew\n"

    def test_under_cap_untouched(self):
        log = "one\ntwo\n"
        assert logbuf.append_capped(log, "three\n", max_lines=10) == "one\ntwo\nthree\n"

    def test_append_to_empty(self):
        assert logbuf.append_capped("", "first\n") == "first\n"


class TestTail:
    def test_last_n_lines(self):
        assert logbuf.tail("a\nb\nc\n", 2) == ["b", "c"]

    def test_fewer_lines_than_requested(self):
        assert logbuf.tail("a\n", 10) == ["a"]

    def test_empty_log(self):
        assert logbuf.tail("", 10) == []

    def test_whitespace_only_log(self):
        assert logbuf.tail("  \n ", 10) == []
