"""Live constraint tracker (bpy-free).

With the constraint toggled on, Blender's *own* transforms (G / R / S keys in
any keymap, the Move / Rotate / Scale / Transform gizmos, the Mesh menu,
F3, Python) run untouched and write their free result into the mesh. A
depsgraph handler then snaps that result back onto the mesh. This class
decides, per update, *which original positions* the snap is relative to:

* ``idle``    - the selection as it was the last time nothing was running.
* ``session`` - the idle snapshot frozen when an interactive transform
  starts; every frame of the drag is projected from it.
* ``redo``    - the base of the last finished transform, kept so Adjust Last
  Operation (F9) or a re-exec can be projected again from the right state.

Undo is noted separately: a plain Ctrl+Z restores positions that must NOT
be re-projected, while F9 is "undo, then exec", which must be.

All positions are {vert index: (x, y, z)} dicts of the *selected* vertices;
``key`` identifies topology + selection, so a snapshot never gets applied to
a different mesh state (extrude, duplicate, selection change ...).
"""

TOL = 1e-6


def same_positions(a, b, tol=TOL):
    if a is None or b is None or a.keys() != b.keys():
        return False
    for k, p in a.items():
        q = b[k]
        if abs(p[0] - q[0]) > tol or abs(p[1] - q[1]) > tol or abs(p[2] - q[2]) > tol:
            return False
    return True


class Snapshot:
    __slots__ = ("key", "positions", "op_id", "cache")

    def __init__(self, key, positions, op_id):
        self.key = key
        self.positions = dict(positions)
        self.op_id = op_id
        self.cache = {}     # solver data, built lazily by the Blender layer


class LiveTracker:
    """Per-object state machine. Call decide() then settle() on every update."""

    def __init__(self):
        self.idle = None
        self.session = None
        self.session_op = None
        self.in_session = False
        self.redo_op = None
        self.redo_base = None
        self.written = None
        self.undo_positions = None

    # -- events --------------------------------------------------------------

    def note_undo(self, positions):
        """Positions right after an undo/redo step was applied."""
        self.undo_positions = dict(positions)

    def reset(self):
        self.__init__()

    # -- per update ----------------------------------------------------------

    def _running_heuristic(self, positions, last_op):
        """No Window.modal_operators: a drag is in progress when selected verts
        moved but no new operator was registered yet."""
        if self.undo_positions is not None:
            return False
        if self.in_session:
            # Running until an operator is registered (confirm) or the
            # selection is back where it started (cancel).
            base = self.session
            if last_op != self.session_op:
                return False
            return base is None or not same_positions(positions, base.positions)
        idle = self.idle
        return (idle is not None and last_op == idle.op_id
                and not same_positions(positions, self.written))

    def decide(self, key, positions, *, last_op, last_is_transform, transform_running):
        """Return the Snapshot to project from, or None to leave the mesh alone.

        transform_running: True / False when known (Window.modal_operators),
        None to fall back on the heuristic.
        """
        if transform_running is None:
            transform_running = self._running_heuristic(positions, last_op)

        base = None
        if transform_running:
            if not self.in_session:
                self.in_session = True
                self.session_op = last_op
                self.session = self.idle if (self.idle is not None and self.idle.key == key) else None
            base = self.session

        elif self.in_session:
            # The drag just ended: confirmed (a new transform op got
            # registered) or cancelled (positions restored, no new op).
            self.in_session = False
            start = self.session
            self.session = None
            if start is not None and last_is_transform and last_op != start.op_id:
                self.redo_op, self.redo_base = last_op, start
                if not same_positions(positions, self.written):
                    base = start       # a final recalc landed after our last snap

        elif self.undo_positions is not None:
            after_undo = self.undo_positions
            self.undo_positions = None
            if same_positions(positions, after_undo):
                self.redo_op = self.redo_base = None        # plain undo / redo
            elif last_is_transform and last_op == self.redo_op:
                base = self.redo_base                       # F9: undo + exec

        elif last_is_transform and not same_positions(positions, self.written):
            if last_op == self.redo_op:
                base = self.redo_base                       # repeat / re-exec
            elif self.idle is not None and last_op != self.idle.op_id:
                base = self.idle                            # scripted / exec transform
                self.redo_op, self.redo_base = last_op, self.idle

        if base is not None and base.key != key:
            return None
        return base

    def settle(self, key, positions, last_op):
        """Record the state after this update (including our own writes)."""
        self.written = dict(positions)
        if not self.in_session:
            self.idle = Snapshot(key, positions, last_op)
        elif self.idle is None or self.idle.key != key:
            self.idle = Snapshot(key, positions, last_op)
