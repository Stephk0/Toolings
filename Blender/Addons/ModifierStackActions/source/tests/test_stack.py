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


def test_apply_plan_skips_switched_off_modifiers():
    assert S.apply_plan([True, False, True, True], 3) == ([0, 2], [1])


def test_apply_plan_on_first_modifier_is_empty():
    assert S.apply_plan([True, True], 0) == ([], [])


def test_apply_plan_out_of_range():
    with pytest.raises(IndexError):
        S.apply_plan([True], 1)


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


def test_move_plan_without_pins():
    free = [False] * 4
    assert S.move_plan(free, 2, 'FIRST') == (0, None)
    assert S.move_plan(free, 1, 'LAST') == (3, None)
    assert S.move_plan(free, 2, 'UP') == (1, None)
    assert S.move_plan(free, 2, 'DOWN') == (3, None)
    assert S.move_plan(free, 0, 'UP') == (0, None)      # already first: stays
    assert S.move_plan(free, 3, 'DOWN') == (3, None)    # already last: stays
    with pytest.raises(ValueError):
        S.move_plan(free, 0, 'MIDDLE')
    with pytest.raises(IndexError):
        S.move_plan(free, 4, 'UP')


PINNED = [False, False, False, True, True]  # pinned block = slots 3, 4


def test_move_plan_unpinned_stays_above_pinned_block():
    assert S.move_plan(PINNED, 0, 'LAST') == (2, None)
    assert S.move_plan(PINNED, 2, 'DOWN') == (2, None)
    assert S.move_plan(PINNED, 0, 'BEFORE_PINNED') == (2, None)
    assert not S.move_changes(PINNED, 2, 'LAST')


def test_move_plan_unpinned_after_pinned_pins_it():
    assert S.move_plan(PINNED, 1, 'AFTER_PINNED') == (4, True)
    assert S.move_changes(PINNED, 2, 'AFTER_PINNED')


def test_move_plan_pinned_stays_in_pinned_block():
    assert S.move_plan(PINNED, 4, 'UP') == (3, None)
    assert S.move_plan(PINNED, 3, 'UP') == (3, None)
    assert S.move_plan(PINNED, 3, 'LAST') == (4, None)
    assert S.move_plan(PINNED, 3, 'AFTER_PINNED') == (4, None)
    assert not S.move_changes(PINNED, 4, 'LAST')


def test_move_plan_pinned_leaving_block_unpins_it():
    assert S.move_plan(PINNED, 4, 'FIRST') == (0, False)
    assert S.move_plan(PINNED, 4, 'BEFORE_PINNED') == (3, False)
    assert S.move_plan(PINNED, 3, 'BEFORE_PINNED') == (3, False)
    assert S.move_changes(PINNED, 3, 'BEFORE_PINNED')    # same slot, but unpinned


def test_move_plan_all_pinned():
    assert S.move_plan([True, True], 1, 'FIRST') == (0, False)
    assert S.move_plan([True, True], 1, 'BEFORE_PINNED') == (0, False)


@pytest.mark.parametrize("names,new,anchor,position,expected", [
    (["A", "B", "C", "N"], "N", "B", 'BEFORE', 1),
    (["A", "B", "C", "N"], "N", "B", 'AFTER', 2),
    (["A", "N", "B", "C"], "N", "C", 'AFTER', 3),
    (["A", "N", "B", "C"], "N", "A", 'BEFORE', 0),
])
def test_insert_target(names, new, anchor, position, expected):
    assert S.insert_target(names, new, anchor, position) == expected
