"""LiveTracker: which originals does a native transform get projected from?"""

import pytest

from core.live import LiveTracker

KEY = ("cube", (8, 9, 10, 11))
P0 = {8: (1.0, 1.0, 0.0)}
P_FREE = {8: (1.0, 1.0 - 0.1, 0.5)}       # what Blender's rotate wrote
P_SNAP = {8: (1.0, 1.0, 0.5)}             # what we wrote back


def step(tr, positions, *, op, is_t, running, key=KEY, write=None):
    base = tr.decide(key, positions, last_op=op, last_is_transform=is_t,
                     transform_running=running)
    final = write if (base is not None and write is not None) else positions
    tr.settle(key, final, op)
    return base


@pytest.mark.parametrize("running_known", [True, False])
def test_interactive_drag_projects_from_pre_drag_state(running_known):
    tr = LiveTracker()
    r = (lambda v: v) if running_known else (lambda v: None)
    assert step(tr, P0, op=1, is_t=False, running=r(False)) is None        # idle
    b = step(tr, P_FREE, op=1, is_t=False, running=r(True), write=P_SNAP)   # drag frame 1
    assert b is not None and b.positions == P0
    # a frame where Blender wrote a new free position
    P_FREE2 = {8: (1.0, 0.8, 0.7)}
    b2 = step(tr, P_FREE2, op=1, is_t=False, running=r(True), write={8: (1, 1, 0.7)})
    assert b2.positions == P0                                               # same base, not the last frame
    # confirm: transform op 2 registered, positions are what we wrote
    assert step(tr, {8: (1, 1, 0.7)}, op=2, is_t=True, running=r(False)) is None
    # next idle update keeps things quiet
    assert step(tr, {8: (1, 1, 0.7)}, op=2, is_t=True, running=r(False)) is None


def test_cancelled_drag_does_nothing():
    tr = LiveTracker()
    step(tr, P0, op=1, is_t=False, running=False)
    step(tr, P_FREE, op=1, is_t=False, running=True, write=P_SNAP)
    assert step(tr, P0, op=1, is_t=False, running=False) is None           # RMB restored


def test_exec_transform_is_projected_once():
    """Scripted bpy.ops.transform.*, menu Move with typed value, F3 exec."""
    tr = LiveTracker()
    step(tr, P0, op=1, is_t=False, running=False)
    b = step(tr, P_FREE, op=2, is_t=True, running=False, write=P_SNAP)
    assert b is not None and b.positions == P0
    assert step(tr, P_SNAP, op=2, is_t=True, running=False) is None        # our own write echo


def test_f9_redo_projects_from_the_original_base_again():
    tr = LiveTracker()
    step(tr, P0, op=1, is_t=False, running=False)
    step(tr, P_FREE, op=1, is_t=False, running=True, write=P_SNAP)
    step(tr, P_SNAP, op=2, is_t=True, running=False)                       # confirmed
    # F9: Blender undoes (back to P0) then re-executes with new values
    tr.note_undo(P0)
    P_REDO = {8: (1.0, 0.7, 0.9)}
    b = step(tr, P_REDO, op=2, is_t=True, running=False, write={8: (1, 1, 0.9)})
    assert b is not None and b.positions == P0


def test_plain_undo_is_left_alone():
    tr = LiveTracker()
    step(tr, P0, op=1, is_t=False, running=False)
    step(tr, P_FREE, op=2, is_t=True, running=False, write=P_SNAP)
    tr.note_undo(P0)
    assert step(tr, P0, op=2, is_t=True, running=False) is None
    # ...and an undo further back with the same op still last is ignored too
    older = {8: (1.0, 1.0, -0.4)}
    tr.note_undo(older)
    assert step(tr, older, op=2, is_t=True, running=False) is None


def test_non_transform_ops_are_ignored():
    tr = LiveTracker()
    step(tr, P0, op=1, is_t=False, running=False)
    # e.g. Smooth Vertices moved the selection; not a transform
    assert step(tr, {8: (0.9, 0.9, 0.0)}, op=5, is_t=False, running=False) is None


def test_topology_change_blocks_projection():
    """Extrude / duplicate macro: the pre-drag snapshot is for another mesh."""
    tr = LiveTracker()
    step(tr, P0, op=1, is_t=False, running=False)
    new_key = ("cube", (12, 13, 14, 15))
    assert step(tr, {12: (1, 1, 0.3)}, op=1, is_t=False, running=True, key=new_key) is None


def test_second_drag_uses_post_first_drag_state():
    tr = LiveTracker()
    step(tr, P0, op=1, is_t=False, running=False)
    step(tr, P_FREE, op=1, is_t=False, running=True, write=P_SNAP)
    step(tr, P_SNAP, op=2, is_t=True, running=False)
    step(tr, P_SNAP, op=2, is_t=True, running=False)                       # idle
    b = step(tr, {8: (1.2, 1.0, 0.6)}, op=2, is_t=True, running=True, write={8: (1, 1, 0.6)})
    assert b.positions == P_SNAP


def test_second_drag_without_an_update_after_confirm():
    """Confirm fired no depsgraph update: the next drag's first update is
    already running, with a newer registered op. Project from our last write,
    not from the first drag's start."""
    tr = LiveTracker()
    step(tr, P0, op=1, is_t=False, running=False)
    step(tr, P_FREE, op=1, is_t=False, running=True, write=P_SNAP)
    b = step(tr, {8: (1.2, 1.0, 0.6)}, op=2, is_t=True, running=True, write={8: (1, 1, 0.6)})
    assert b.positions == P_SNAP
    # ...and F9 on the first drag still projects from its start
    assert tr.redo_op == 2 and tr.redo_base.positions == P0
