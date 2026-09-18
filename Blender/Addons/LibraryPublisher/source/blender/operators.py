"""Operators: run a publish from inside Blender without freezing the UI.

`core/` imports no bpy, which makes it safe to run on a worker thread - the very
thing the architecture split buys us here. A modal timer polls the thread and
does all the bpy work (reporting, refreshing asset libraries) back on the main
thread, where it belongs.
"""

import os
import threading
import traceback

import bpy
from bpy.types import Operator

from ..core import config, publish
from . import properties


class _PublishJob:
    """A publish running on a worker thread. Touches no bpy."""

    def __init__(self, cfg, tool_root, force, dry_run):
        self.cfg = cfg
        self.tool_root = tool_root
        self.force = force
        self.dry_run = dry_run
        self.result = None
        self.error = ""
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.thread.start()

    @property
    def done(self) -> bool:
        return not self.thread.is_alive()

    def _run(self):
        try:
            cfg = dict(self.cfg)
            if self.dry_run:
                cfg["delivery"] = dict(cfg["delivery"])
                cfg["delivery"]["dry_run"] = True
            self.result = publish.publish(
                cfg, self.tool_root, force=self.force, reason="blender-button"
            )
        except Exception:
            self.error = traceback.format_exc(limit=6)


def _load_cfg(context):
    """(cfg, tool_root, error_message)"""
    tool_root = properties.resolved_tool_root(context)
    if not tool_root:
        return None, "", (
            "LibraryPublisher folder is not set - open Preferences > Add-ons > "
            "Library Publisher and point it at the repo folder"
        )
    path = config.config_path(tool_root)
    if not os.path.isfile(path):
        return None, tool_root, "No publish_config.json at %s" % path
    try:
        cfg = config.load(path)
    except config.ConfigError as exc:
        return None, tool_root, str(exc)
    if not cfg["source"].get("repo_root"):
        return None, tool_root, "source.repo_root is empty - run /publish-library-config"
    return cfg, tool_root, ""


def _store(context, result, ok: bool, headline: str):
    state = context.window_manager.st3e_library_publish
    state.report_text = "\n".join(result.lines) if result else headline
    state.report_ok = ok
    state.headline = headline


def _refresh_asset_libraries(context) -> str:
    """Reload asset libraries so the published change is visible immediately.

    `asset.library_refresh` needs an Asset Browser context, so it is run through
    a temp_override on the first one found. No browser open is not an error -
    there is simply nothing to refresh yet.
    """
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != "FILE_BROWSER":
                continue
            space = area.spaces.active
            if getattr(space, "browse_mode", "") != "ASSETS":
                continue
            try:
                with context.temp_override(window=window, area=area, region=area.regions[-1]):
                    bpy.ops.asset.library_refresh()
                return "asset library refreshed"
            except Exception as exc:
                return "could not refresh asset library: %s" % exc
    return "no Asset Browser open - refresh manually to see the change"


class ST3E_OT_library_status(Operator):
    """Report what would be published, without writing anything"""

    bl_idname = "st3e.library_publish_status"
    bl_label = "Preview Publish"
    bl_options = {"REGISTER"}

    def execute(self, context):
        cfg, tool_root, error = _load_cfg(context)
        if error:
            self.report({"ERROR"}, error)
            _store(context, None, False, error)
            return {"CANCELLED"}

        problems = config.validate(cfg)
        if problems:
            message = "config not usable: %s" % problems[0]
            self.report({"ERROR"}, message)
            _store(context, None, False, message)
            return {"CANCELLED"}

        cfg["delivery"] = dict(cfg["delivery"])
        cfg["delivery"]["dry_run"] = True
        try:
            result = publish.publish(cfg, tool_root, reason="blender-preview")
        except Exception as exc:
            self.report({"ERROR"}, "preview failed: %s" % exc)
            _store(context, None, False, str(exc))
            return {"CANCELLED"}

        headline = "%s | %s" % (
            "%d file(s) selected" % len(result.selection.files),
            result.diff.summary(),
        )
        _store(context, result, result.ok, headline)
        self.report({"INFO"} if result.ok else {"WARNING"}, headline)
        print("\n".join(result.lines))
        return {"FINISHED"}


class ST3E_OT_library_publish(Operator):
    """Publish the asset library to the shared drive"""

    bl_idname = "st3e.library_publish"
    bl_label = "Publish Library"
    bl_options = {"REGISTER"}

    force: bpy.props.BoolProperty(
        name="Force",
        description="Publish even when no file has changed",
        default=False,
    )
    dry_run: bpy.props.BoolProperty(
        name="Dry Run",
        description="Run everything but write nothing to the destination",
        default=False,
    )

    _job = None
    _timer = None

    @classmethod
    def poll(cls, context):
        return not context.window_manager.st3e_library_publish.busy

    def invoke(self, context, event):
        prefs = properties.get_prefs(context)
        if prefs and prefs.confirm_before_publish and not self.dry_run:
            return context.window_manager.invoke_confirm(self, event)
        return self.execute(context)

    def execute(self, context):
        cfg, tool_root, error = _load_cfg(context)
        if error:
            self.report({"ERROR"}, error)
            _store(context, None, False, error)
            return {"CANCELLED"}

        problems = config.validate(cfg)
        if problems:
            message = "config not usable: %s" % problems[0]
            self.report({"ERROR"}, message)
            _store(context, None, False, message)
            return {"CANCELLED"}

        state = context.window_manager.st3e_library_publish
        state.busy = True
        state.headline = "publishing…"

        self._job = _PublishJob(cfg, tool_root, self.force, self.dry_run)
        self._job.start()
        self._timer = context.window_manager.event_timer_add(0.3, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type != "TIMER":
            return {"PASS_THROUGH"}
        if not self._job.done:
            return {"RUNNING_MODAL"}
        return self._finish(context)

    def _finish(self, context):
        self._cleanup(context)
        job, self._job = self._job, None

        if job.error:
            self.report({"ERROR"}, "publish crashed - see the system console")
            print(job.error)
            _store(context, None, False, "publish crashed")
            return {"CANCELLED"}

        result = job.result
        if not result.ok:
            self.report({"ERROR"}, result.reason.splitlines()[0] if result.reason else "failed")
            print("\n".join(result.lines))
            _store(context, result, False, result.reason.splitlines()[0] if result.reason else "failed")
            return {"CANCELLED"}

        if result.delivered:
            headline = "published %d file(s)" % result.manifest.get("counts", {}).get("files", 0)
        else:
            headline = "already up to date (%s)" % result.diff.summary()

        cfg = job.cfg
        if result.delivered and cfg["triggers"]["blender_button"].get("refresh_after"):
            headline += " - " + _refresh_asset_libraries(context)

        if result.skipped_files:
            headline += " | %d withheld by a blocking check" % len(result.skipped_files)
            self.report({"WARNING"}, headline)
        else:
            self.report({"INFO"}, headline)

        _store(context, result, True, headline)
        print("\n".join(result.lines))
        return {"FINISHED"}

    def _cleanup(self, context):
        if self._timer is not None:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None
        context.window_manager.st3e_library_publish.busy = False

    def cancel(self, context):
        # The worker is a daemon thread doing file I/O; it finishes on its own.
        # What must not leak is the timer or the busy flag, which would leave the
        # publish button permanently greyed out.
        self._cleanup(context)
        self._job = None


class ST3E_OT_library_show_report(Operator):
    """Show the full report from the last run"""

    bl_idname = "st3e.library_publish_report"
    bl_label = "Last Publish Report"
    bl_options = {"REGISTER"}

    def execute(self, context):
        state = context.window_manager.st3e_library_publish
        text = state.report_text or "nothing has run yet"
        print(text)

        block = bpy.data.texts.get("ST3E Publish Report") or bpy.data.texts.new(
            "ST3E Publish Report"
        )
        block.clear()
        block.write(text)
        self.report({"INFO"}, "report written to the text block 'ST3E Publish Report'")
        return {"FINISHED"}


classes = (
    ST3E_OT_library_status,
    ST3E_OT_library_publish,
    ST3E_OT_library_show_report,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
