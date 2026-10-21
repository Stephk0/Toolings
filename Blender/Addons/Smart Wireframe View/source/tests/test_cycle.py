from core.cycle import OFF, OVERLAYS, WIREFRAME, flags_of, next_state, state_of


def test_state_round_trip():
    for s in (OFF, OVERLAYS, WIREFRAME):
        assert state_of(*flags_of(s)) == s


def test_wireframe_flag_ignored_while_overlays_off():
    assert state_of(False, True) == OFF


def test_full_cycle_forward():
    seq, s = [], OFF
    for _ in range(4):
        s = next_state(s)
        seq.append(s)
    assert seq == [OVERLAYS, WIREFRAME, OFF, OVERLAYS]


def test_full_cycle_reverse():
    assert next_state(OFF, reverse=True) == WIREFRAME
    assert next_state(WIREFRAME, reverse=True) == OVERLAYS


def test_skip_disabled_state():
    enabled = (OVERLAYS, WIREFRAME)
    assert next_state(OVERLAYS, enabled) == WIREFRAME
    assert next_state(WIREFRAME, enabled) == OVERLAYS
    # starting from a disabled state lands on the next enabled one
    assert next_state(OFF, enabled) == OVERLAYS


def test_nothing_enabled_keeps_state():
    assert next_state(OVERLAYS, ()) == OVERLAYS
