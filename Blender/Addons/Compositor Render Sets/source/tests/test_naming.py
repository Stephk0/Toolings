"""Tests for core.naming — must run without bpy."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import naming


class TestEnsureTrailingSlash:
    def test_adds_default_separator(self):
        assert naming.ensure_trailing_slash("C:/renders") == "C:/renders/"

    def test_adds_custom_separator(self):
        assert naming.ensure_trailing_slash("C:\\renders", sep="\\") == "C:\\renders\\"

    def test_keeps_existing_forward_slash(self):
        assert naming.ensure_trailing_slash("//renders/") == "//renders/"

    def test_keeps_existing_backslash(self):
        assert naming.ensure_trailing_slash("C:\\renders\\") == "C:\\renders\\"

    def test_empty_path_untouched(self):
        assert naming.ensure_trailing_slash("") == ""


class TestResolvePrefix:
    def test_override_wins(self):
        assert naming.resolve_prefix("GLB", True, "OVR") == "OVR"

    def test_override_disabled_uses_global(self):
        assert naming.resolve_prefix("GLB", False, "OVR") == "GLB"

    def test_empty_override_falls_back_to_global(self):
        assert naming.resolve_prefix("GLB", True, "") == "GLB"

    def test_everything_empty_uses_fallback(self):
        assert naming.resolve_prefix("", False, "") == naming.FALLBACK_PREFIX


class TestReplacePrefix:
    def test_prefix_replaced(self):
        assert naming.replace_prefix("XXX_Beauty", "XXX", "CharA") == "CharA_Beauty"

    def test_no_match_returns_none(self):
        assert naming.replace_prefix("Beauty", "XXX", "CharA") is None

    def test_prefix_only_slot(self):
        assert naming.replace_prefix("XXX", "XXX", "CharA") == "CharA"

    def test_empty_prefix_never_matches(self):
        assert naming.replace_prefix("XXX_Beauty", "", "CharA") is None

    def test_empty_slot_never_matches(self):
        assert naming.replace_prefix("", "XXX", "CharA") is None


class TestComputeSlotRenames:
    def test_mixed_slots(self):
        renames = naming.compute_slot_renames(
            ["XXX_Beauty", "Depth", "XXX_Mask"], "XXX", "Prop")
        assert renames == [
            ("XXX_Beauty", "Prop_Beauty"),
            ("Depth", None),
            ("XXX_Mask", "Prop_Mask"),
        ]

    def test_empty_list(self):
        assert naming.compute_slot_renames([], "XXX", "Prop") == []


class TestComputeOutputNames:
    def test_slots_joined_with_set_name(self):
        assert naming.compute_output_names(["Beauty", "Mask"], "CharA") == [
            "CharA_Beauty", "CharA_Mask"]

    def test_empty_slot_path_uses_set_name(self):
        assert naming.compute_output_names([""], "CharA") == ["CharA"]
