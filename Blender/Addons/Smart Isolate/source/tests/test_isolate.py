from core.isolate import (
    BACK, DEEPER, ENTER, EXIT, EXIT_ALL, NONE, REPLACE, STEP_BACK,
    Settings, apply, decide, prune,
)

ABC = frozenset("abc")
AB = frozenset("ab")
A = frozenset("a")


def run(presses, settings=Settings()):
    """Feed a sequence of selections, return (actions, final stack)."""
    stack, actions = [], []
    for sel in presses:
        action = decide(sel, stack, settings)
        actions.append(action)
        stack = apply(action, sel, stack)
    return actions, stack


def test_nothing_selected_outside_isolation_does_nothing():
    assert decide(set(), []) == NONE


def test_enter_then_same_selection_exits():
    actions, stack = run([ABC, ABC])
    assert actions == [ENTER, EXIT]
    assert stack == []


def test_subset_goes_deeper():
    actions, stack = run([ABC, AB, A])
    assert actions == [ENTER, DEEPER, DEEPER]
    assert stack == [ABC, AB, A]


def test_same_selection_steps_back_one_level():
    actions, stack = run([ABC, AB, AB, ABC])
    assert actions == [ENTER, DEEPER, BACK, EXIT]
    assert stack == []


def test_empty_selection_exits_all_by_default():
    actions, stack = run([ABC, AB, A, set()])
    assert actions[-1] == EXIT
    assert stack == []


def test_empty_selection_can_step_back():
    s = Settings(empty_selection=STEP_BACK)
    actions, stack = run([ABC, AB, set(), set()], s)
    assert actions == [ENTER, DEEPER, BACK, EXIT]


def test_same_selection_can_exit_all():
    s = Settings(same_selection=EXIT_ALL)
    actions, _ = run([ABC, AB, AB], s)
    assert actions[-1] == EXIT


def test_not_nested_replaces_like_3ds_max():
    s = Settings(nested=False)
    actions, stack = run([ABC, AB, AB], s)
    assert actions == [ENTER, REPLACE, EXIT]
    assert stack == []


def test_selection_outside_current_level_replaces_it():
    actions, stack = run([ABC, AB, frozenset("ax")])
    assert actions[-1] == REPLACE
    assert stack == [ABC, frozenset("ax")]


def test_prune_drops_deleted_objects_and_empty_levels():
    assert prune([ABC, AB, A], "bc") == [frozenset("bc"), frozenset("b")]
