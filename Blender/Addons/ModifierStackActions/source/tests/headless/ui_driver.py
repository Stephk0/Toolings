"""Shared helpers for driving the real Blender UI with simulated input.

Run Blender WITH its UI and --enable-event-simulate (real OS input is then
ignored by that window), step a generator from a timer, grab the window with
screen.screenshot. Windows: the GPU framebuffer reads fine (no Xvfb trap).
"""

import os
import sys

import bpy

SOURCE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def load_addon():
    sys.path.insert(0, os.path.dirname(SOURCE))
    addon = __import__(os.path.basename(SOURCE))
    addon.register()
    return addon


def win():
    return bpy.context.window_manager.windows[0]


def area(kind):
    return next(a for a in win().screen.areas if a.type == kind)


def region(a, kind='WINDOW'):
    return next(r for r in a.regions if r.type == kind)


def ui_unit():
    """UI_UNIT_X/Y in pixels (20 at 100 % scale)."""
    return 20.0 * bpy.context.preferences.system.ui_scale


_cursor = [10, 10]


def ev(type, value='NOTHING', **kw):
    win().event_simulate(type=type, value=value, **kw)


def mouse(x, y):
    _cursor[:] = [int(x), int(y)]
    ev('MOUSEMOVE', x=int(x), y=int(y))


def click(button='LEFTMOUSE'):
    x, y = _cursor
    ev(button, 'PRESS', x=x, y=y)
    ev(button, 'RELEASE', x=x, y=y)


def key(k, ctrl=False, shift=False):
    x, y = _cursor
    mods = [m for m, on in (('LEFT_CTRL', ctrl), ('LEFT_SHIFT', shift)) if on]
    for m in mods:
        ev(m, 'PRESS', x=x, y=y, ctrl=ctrl, shift=shift)
    ev(k, 'PRESS', x=x, y=y, ctrl=ctrl, shift=shift)
    ev(k, 'RELEASE', x=x, y=y, ctrl=ctrl, shift=shift)
    for m in reversed(mods):
        ev(m, 'RELEASE', x=x, y=y)


def type_text(text):
    x, y = _cursor
    for ch in text:
        ev('TEXTINPUT', 'NOTHING', x=x, y=y, unicode=ch)


def screenshot(path):
    w = win()
    with bpy.context.temp_override(window=w, screen=w.screen, area=w.screen.areas[0]):
        bpy.ops.screen.screenshot(filepath=path, check_existing=False)


def cursor():
    return tuple(_cursor)


def run(gen_fn, first=2.0):
    """Step ``gen_fn()`` from a timer; each yield is the delay to the next step."""
    gen = gen_fn()

    def tick():
        try:
            return next(gen)
        except StopIteration:
            pass
        except Exception:
            import traceback
            traceback.print_exc()
        sys.stdout.flush()
        os._exit(0)

    bpy.app.timers.register(tick, first_interval=first)
