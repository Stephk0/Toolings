import pytest

from core import stack as S


def test_hide_after_hides_only_visible_later_modifiers():
    visible = [True, True, False, True, True]
    assert S.hide_after_plan(visible, 1) == [3, 4]


def test_hide_after_last_modifier_is_noop():
    assert S.hide_after_plan([True, True], 1) == []


def test_hide_after_out_of_range():
    with pytest.raises(IndexError):
        S.hide_after_plan([True], 3)


def test_state_roundtrip():
    raw = S.encode_state("Mirror", ["Subdivision", "Bevel"])
    assert S.decode_state(raw) == {"target": "Mirror", "hidden": ["Subdivision", "Bevel"]}


@pytest.mark.parametrize("raw", ["", None, "not json", "[]", '{"target": "x"}'])
def test_decode_bad_state(raw):
    assert S.decode_state(raw) is None


def test_restore_skips_deleted_modifiers():
    assert S.restore_plan(["Mirror", "Bevel"], ["Subdivision", "Bevel"]) == [1]


def test_extract_forces_target_on_and_later_off():
    visible = [False, False, True, False]
    # earlier disabled modifier (0) keeps its state, target (1) goes on, 2 goes off
    assert S.extract_plan(visible, 1) == {1: True, 2: False}


def test_extract_on_visible_last_modifier_changes_nothing():
    assert S.extract_plan([True, True], 1) == {}


def test_extract_name():
    assert S.extract_name("Cube", "Mirror") == "Cube_Mirror"


@pytest.mark.parametrize("anchor,position,expected", [(0, 'BEFORE', 0), (0, 'AFTER', 1), (2, 'AFTER', 3)])
def test_insert_index(anchor, position, expected):
    assert S.insert_index(anchor, position) == expected


def test_insert_index_bad_position():
    with pytest.raises(ValueError):
        S.insert_index(0, 'SIDEWAYS')


def test_find_added_single_new_modifier():
    assert S.find_added(["Mirror", "Bevel"], ["Mirror", "Bevel", "Array"]) == "Array"


@pytest.mark.parametrize("after", [
    ["Mirror", "Bevel"],                     # nothing added
    ["Mirror", "Bevel", "Array", "Weld"],    # two added
    ["Mirror", "Array", "Weld"],             # one removed, two added
])
def test_find_added_rejects_other_edits(after):
    assert S.find_added(["Mirror", "Bevel"], after) is None


def test_move_index():
    assert S.move_index(4, 'FIRST') == 0
    assert S.move_index(4, 'LAST') == 3
    with pytest.raises(ValueError):
        S.move_index(4, 'MIDDLE')
