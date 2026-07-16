"""Tests for core.relink — must run without bpy."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import relink

OLD = os.path.normpath("D:/Old/Geonodes")
NEW = os.path.normpath("D:/New/Geonodes")


def lib(name, folder=OLD):
    return (name, os.path.join(folder, name + ".blend"))


class TestIsUnder:
    def test_inside(self):
        assert relink.is_under(os.path.join(OLD, "GN_Wave.blend"), OLD)

    def test_outside(self):
        assert not relink.is_under("C:/Elsewhere/GN_Wave.blend", OLD)

    def test_trailing_separator_on_filter(self):
        assert relink.is_under(os.path.join(OLD, "GN_Wave.blend"), OLD + os.sep)

    def test_prefix_of_sibling_folder_does_not_match(self):
        assert not relink.is_under(OLD + "_backup" + os.sep + "GN_Wave.blend", OLD)

    def test_empty_filter_matches_everything(self):
        assert relink.is_under("C:/Anywhere/file.blend", "")


class TestPlanRelink:
    def test_relink_when_file_available(self):
        plan = relink.plan_relink([lib("GN_Wave")], NEW, ["GN_Wave.blend"])
        assert plan[0]["status"] == relink.STATUS_RELINK
        assert plan[0]["target"] == os.path.join(NEW, "GN_Wave.blend")

    def test_missing_when_file_not_available(self):
        plan = relink.plan_relink([lib("GN_Wave")], NEW, ["GN_Other.blend"])
        assert plan[0]["status"] == relink.STATUS_MISSING

    def test_same_when_already_in_new_dir(self):
        plan = relink.plan_relink([lib("GN_Wave", NEW)], NEW, ["GN_Wave.blend"])
        assert plan[0]["status"] == relink.STATUS_SAME

    def test_same_beats_filter(self):
        # a freshly relinked library sits outside the old-dir filter but must
        # still read as SAME (done), not FILTERED
        plan = relink.plan_relink([lib("GN_Wave", NEW)], NEW, ["GN_Wave.blend"],
                                  old_dir_filter=OLD)
        assert plan[0]["status"] == relink.STATUS_SAME

    def test_filtered_when_outside_filter(self):
        essentials = ("essentials", "C:/Blender/assets/essentials.blend")
        plan = relink.plan_relink([essentials], NEW, ["essentials.blend"],
                                  old_dir_filter=OLD)
        assert plan[0]["status"] == relink.STATUS_FILTERED

    def test_empty_filter_considers_all(self):
        essentials = ("essentials", "C:/Blender/assets/essentials.blend")
        plan = relink.plan_relink([essentials], NEW, ["essentials.blend"])
        assert plan[0]["status"] == relink.STATUS_RELINK

    def test_filename_match_is_case_insensitive(self):
        plan = relink.plan_relink([lib("GN_Wave")], NEW, ["gn_wave.BLEND"])
        assert plan[0]["status"] == relink.STATUS_RELINK

    def test_target_uses_on_disk_spelling(self):
        plan = relink.plan_relink([lib("GN_Wave")], NEW, ["gn_wave.blend"])
        assert plan[0]["target"] == os.path.join(NEW, "gn_wave.blend")

    def test_preserves_library_name_and_current_path(self):
        name, path = lib("GN_Wave")
        plan = relink.plan_relink([(name, path)], NEW, [])
        assert plan[0]["name"] == name
        assert plan[0]["current"] == path

    def test_mixed_plan_order_preserved(self):
        libs = [lib("GN_Wave"), lib("GN_Gone"), lib("GN_Here", NEW)]
        plan = relink.plan_relink(libs, NEW, ["GN_Wave.blend", "GN_Here.blend"])
        assert [item["status"] for item in plan] == [
            relink.STATUS_RELINK, relink.STATUS_MISSING, relink.STATUS_SAME]


class TestSummarize:
    def test_counts_every_status(self):
        libs = [lib("GN_Wave"), lib("GN_Gone"), lib("GN_Here", NEW),
                ("ess", "C:/Blender/essentials.blend")]
        plan = relink.plan_relink(libs, NEW, ["GN_Wave.blend", "GN_Here.blend"],
                                  old_dir_filter="")
        plan_filtered = relink.plan_relink(
            libs, NEW, ["GN_Wave.blend", "GN_Here.blend", "ess.blend"],
            old_dir_filter=OLD)
        counts = relink.summarize(plan_filtered)
        assert counts[relink.STATUS_RELINK] == 1
        assert counts[relink.STATUS_MISSING] == 1
        assert counts[relink.STATUS_FILTERED] == 1  # ess (C:) sits outside OLD
        assert counts[relink.STATUS_SAME] == 1      # GN_Here already in NEW beats the filter
        assert relink.summarize(plan)[relink.STATUS_SAME] == 1

    def test_empty_plan(self):
        counts = relink.summarize([])
        assert all(value == 0 for value in counts.values())
