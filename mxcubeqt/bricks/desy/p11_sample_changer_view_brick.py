#
#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""P11 Sample Changer View Brick

Displays two live MJPEG camera feeds during sample mounting:
  - Left:  gonio/sample camera  (e.g. haspp11ethcam4, id=8405)
  - Right: robot camera          (e.g. haspp11ethcam7, id=8002)

The brick connects to HWR.beamline.sample_changer STATUS_CHANGED_EVENT and
auto-starts/stops streaming when the SC state is "Loading" or "Unloading".
Streaming can also be toggled manually with the "Live" checkbox.

URLs are configured via brick properties:
  mjpeg_url_left  - MJPEG stream URL for the left (gonio) camera
  mjpeg_url_right - MJPEG stream URL for the right (robot) camera
  frame_width     - display width per camera in pixels (default 640)
  frame_height    - display height per camera in pixels (default 480)
"""

import logging
import http.client
import urllib.parse

from mxcubeqt.base_components import BaseWidget
from mxcubeqt.utils import colors, qt_import
from mxcubeqt.utils.sample_changer_helper import SampleChanger

from mxcubecore import HardwareRepository as HWR


__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "DESY"

log = logging.getLogger("GUI")

# ---------------------------------------------------------------------------
# MJPEG reader thread
# ---------------------------------------------------------------------------

class _MjpegThread(qt_import.QThread):
    """Fetches JPEG frames from an MJPEG stream in a background thread.

    Emits frameReady(QPixmap) for each decoded frame.
    URL format expected: http://<host>/mjpg/video.mjpg[?id=NNNN]
    """

    frameReady = qt_import.pyqtSignal(qt_import.QPixmap)

    def __init__(self, url, width, height, parent=None):
        super().__init__(parent)
        self._url = url
        self._width = width
        self._height = height
        self._running = False

    def run(self):
        self._running = True
        parsed = urllib.parse.urlparse(self._url)
        host = parsed.hostname
        port = parsed.port or 80
        path = parsed.path
        if parsed.query:
            path = path + "?" + parsed.query

        while self._running:
            try:
                conn = http.client.HTTPConnection(host, port, timeout=5)
                conn.request("GET", path)
                resp = conn.getresponse()

                buf = b""
                while self._running:
                    chunk = resp.read(4096)
                    if not chunk:
                        break
                    buf += chunk
                    # Look for a complete JPEG: starts with FF D8, ends with FF D9
                    start = buf.find(b"\xff\xd8")
                    end = buf.find(b"\xff\xd9")
                    if start != -1 and end != -1 and end > start:
                        jpeg_data = buf[start:end + 2]
                        buf = buf[end + 2:]
                        self._emit_frame(jpeg_data)

                conn.close()
            except Exception as exc:
                if self._running:
                    log.debug("MjpegThread(%s): %s", self._url, exc)
                    self.msleep(1000)

    def _emit_frame(self, jpeg_data):
        pixmap = qt_import.QPixmap()
        if pixmap.loadFromData(jpeg_data):
            if self._width and self._height:
                pixmap = pixmap.scaled(
                    self._width,
                    self._height,
                    qt_import.Qt.KeepAspectRatio,
                    qt_import.Qt.SmoothTransformation,
                )
            self.frameReady.emit(pixmap)

    def stop(self):
        self._running = False
        self.wait(2000)


# ---------------------------------------------------------------------------
# Brick
# ---------------------------------------------------------------------------

class P11SampleChangerViewBrick(BaseWidget):
    """Two-camera MJPEG viewer for P11 robot / gonio cameras."""

    def __init__(self, *args):
        BaseWidget.__init__(self, *args)

        # Properties
        # If cameras_hwobj_role is set, URLs + frame size are read from the
        # named beamline role (see P11SampleChangerCameras). Otherwise the
        # mjpeg_url_* / frame_* properties below are used directly.
        self.add_property("cameras_hwobj_role", "string", "sample_changer_cameras")
        self.add_property(
            "mjpeg_url_left", "string",
            "",
        )
        self.add_property(
            "mjpeg_url_right", "string",
            "",
        )
        self.add_property("frame_width", "integer", 640)
        self.add_property("frame_height", "integer", 480)
        # When True the camera view is not embedded; instead, a non-modal
        # popup window is opened automatically while the SC is Loading or
        # Unloading, and closed when it returns to idle.
        self.add_property("popup_on_mount", "boolean", True)

        # Internal
        self._thread_left = None
        self._thread_right = None
        self._streaming = False
        self._popup = None
        # Reference-count mount operations so simultaneous signal sources
        # (TreeBrick manual path + sample-changer progress_message queue path)
        # don't leave the popup visible after only one of them finishes.
        self._mount_depth = 0
        # Cached TreeBrick reference so the progress_message handler can
        # honour the "During mount show sample changer" checkbox.
        self._tree_brick = None
        # True while a queue-driven mount (detected from progress_message)
        # is active; ensures we emit exactly one finished for it.
        self._queue_mount_active = False

        # --- GUI elements ---
        title_label = qt_import.QLabel("<b>Sample Changer Cameras</b>", self)
        title_label.setAlignment(qt_import.Qt.AlignCenter)

        status_widget = qt_import.QWidget(self)
        status_label = qt_import.QLabel("SC status:", status_widget)
        self.status_ledit = qt_import.QLineEdit(status_widget)
        self.status_ledit.setReadOnly(True)

        self.live_cbx = qt_import.QCheckBox("Live", self)
        self.live_cbx.setChecked(False)

        self.progress_bar = qt_import.QProgressBar(self)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)

        camera_widget = qt_import.QWidget(self)

        # Left camera (gonio/sample)
        left_panel = qt_import.QWidget(camera_widget)
        left_title = qt_import.QLabel("Gonio camera", left_panel)
        left_title.setAlignment(qt_import.Qt.AlignCenter)
        self.left_view = qt_import.QLabel(left_panel)
        self.left_view.setAlignment(qt_import.Qt.AlignCenter)
        self.left_view.setText("(stream stopped)")
        left_layout = qt_import.QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)
        left_layout.addWidget(left_title)
        left_layout.addWidget(self.left_view)

        # Right camera (robot)
        right_panel = qt_import.QWidget(camera_widget)
        right_title = qt_import.QLabel("Robot camera", right_panel)
        right_title.setAlignment(qt_import.Qt.AlignCenter)
        self.right_view = qt_import.QLabel(right_panel)
        self.right_view.setAlignment(qt_import.Qt.AlignCenter)
        self.right_view.setText("(stream stopped)")
        right_layout = qt_import.QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(2)
        right_layout.addWidget(right_title)
        right_layout.addWidget(self.right_view)

        # --- Layouts ---
        _status_hl = qt_import.QHBoxLayout(status_widget)
        _status_hl.addWidget(status_label)
        _status_hl.addWidget(self.status_ledit)

        _cam_hl = qt_import.QHBoxLayout(camera_widget)
        _cam_hl.setContentsMargins(0, 0, 0, 0)
        _cam_hl.setSpacing(4)
        _cam_hl.addWidget(left_panel)
        _cam_hl.addWidget(right_panel)

        _main_vl = qt_import.QVBoxLayout(self)
        _main_vl.setContentsMargins(2, 2, 2, 2)
        _main_vl.setSpacing(2)
        _main_vl.addWidget(title_label)
        _main_vl.addWidget(status_widget)
        _main_vl.addWidget(self.live_cbx)
        _main_vl.addWidget(camera_widget)
        _main_vl.addWidget(self.progress_bar)

        # --- Connections ---
        self.live_cbx.stateChanged.connect(self._on_live_toggled)

        if HWR.beamline.sample_changer is not None:
            self.connect(
                HWR.beamline.sample_changer,
                SampleChanger.STATUS_CHANGED_EVENT,
                self._on_sc_status_changed,
            )
            self.connect(
                HWR.beamline.sample_changer,
                "progressInit",
                self._on_progress_init,
            )
            self.connect(
                HWR.beamline.sample_changer,
                "progressStep",
                self._on_progress_step,
            )
            self.connect(
                HWR.beamline.sample_changer,
                "progressStop",
                self._on_progress_stop,
            )
            # Queue-driven mounts bypass TreeBrick's mount_sample_task and
            # therefore never emit sample_mount_started/_finished. The
            # base_queue_entry.mount_sample() helper DOES call
            # sample_changer.trigger_progress_message("Loading sample" /
            # "Sample loaded" / "Sample not loaded"), so we hook that to
            # cover the queue path.
            self.connect(
                HWR.beamline.sample_changer,
                SampleChanger.PROGRESS_MESSAGE,
                self._on_progress_message,
            )

        # TreeBrick signal subscription is done lazily in run() once all
        # bricks have been instantiated.
        self._tree_brick_connected = False

    def property_changed(self, property_name, old_value, new_value):
        if property_name in ("cameras_hwobj_role", "mjpeg_url_left",
                             "mjpeg_url_right", "frame_width", "frame_height"):
            pass  # applied on next stream start
        else:
            BaseWidget.property_changed(self, property_name, old_value, new_value)

    # ------------------------------------------------------------------
    # Stream control
    # ------------------------------------------------------------------

    def _resolve_config(self):
        """Return (left_url, right_url, width, height).

        Prefers the beamline hardware object (role configurable via
        cameras_hwobj_role). Falls back to direct brick properties.
        """
        left = self["mjpeg_url_left"]
        right = self["mjpeg_url_right"]
        width = self["frame_width"]
        height = self["frame_height"]

        role = self["cameras_hwobj_role"]
        if role:
            try:
                hwobj = HWR.beamline.get_object_by_role(role)
            except Exception:
                hwobj = None
            if hwobj is not None:
                try:
                    left = hwobj.get_gonio_url() or left
                    right = hwobj.get_robot_url() or right
                    w, h = hwobj.get_frame_size()
                    width = w or width
                    height = h or height
                except Exception as exc:
                    log.warning("SC cameras hwobj %r lookup failed: %s", role, exc)

        return left, right, width, height

    def _start_streaming(self):
        if self._streaming:
            return

        left_url, right_url, w, h = self._resolve_config()
        if not left_url and not right_url:
            log.warning("SC cameras: no MJPEG URLs configured, not starting stream")
            return

        self._streaming = True

        if left_url:
            self._thread_left = _MjpegThread(left_url, w, h)
            self._thread_left.frameReady.connect(self._on_left_frame)
            self._thread_left.start()
        if right_url:
            self._thread_right = _MjpegThread(right_url, w, h)
            self._thread_right.frameReady.connect(self._on_right_frame)
            self._thread_right.start()

    def _stop_streaming(self):
        if not self._streaming:
            return
        self._streaming = False
        for thread in (self._thread_left, self._thread_right):
            if thread is not None:
                thread.stop()
        self._thread_left = None
        self._thread_right = None
        self.left_view.setText("(stream stopped)")
        self.right_view.setText("(stream stopped)")

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_live_toggled(self, state):
        if state:
            self._start_streaming()
        else:
            if not self._streaming:
                return
            # Keep streaming while a mount/unmount is in progress.
            if not self._mount_in_progress:
                self._stop_streaming()

    # ------------------------------------------------------------------
    # TreeBrick mount signals (only emitted on Mount / Unmount / Wash)
    # ------------------------------------------------------------------

    def run(self):
        """Called after all bricks have been instantiated."""
        if self._tree_brick_connected:
            return
        tree_brick = self._find_tree_brick()
        if tree_brick is None:
            log.warning("SC view brick: TreeBrick not found; popup will not"
                        " trigger on mount/unmount.")
            return
        try:
            tree_brick.sample_mount_started.connect(self._on_mount_started)
            tree_brick.sample_mount_finished.connect(self._on_mount_finished)
            self._tree_brick = tree_brick
            self._tree_brick_connected = True
            log.info("SC view brick: connected to TreeBrick mount signals")
        except Exception as exc:
            log.warning("SC view brick: failed connecting to TreeBrick: %s", exc)

    @staticmethod
    def _find_tree_brick():
        app = qt_import.QApplication.instance()
        if app is None:
            return None
        for top in app.topLevelWidgets():
            for child in top.findChildren(qt_import.QWidget):
                if type(child).__name__ == "TreeBrick":
                    return child
        return None

    @property
    def _mount_in_progress(self):
        return self._mount_depth > 0

    def _on_mount_started(self):
        """Common entry point for TreeBrick and queue-driven mount starts."""
        self._mount_depth += 1
        log.info("SC view brick: mount started (depth=%d)", self._mount_depth)
        if self._mount_depth > 1:
            return
        self._start_streaming()
        if self["popup_on_mount"]:
            self._show_popup()

    def _on_mount_finished(self):
        """Common exit point. Pops the depth counter and hides when idle."""
        if self._mount_depth == 0:
            # Stray finished without a matching started - ignore.
            return
        self._mount_depth -= 1
        log.info("SC view brick: mount finished (depth=%d)", self._mount_depth)
        if self._mount_depth > 0:
            return
        if not self.live_cbx.isChecked():
            self._stop_streaming()
        if self["popup_on_mount"]:
            self._hide_popup()

    def _on_progress_message(self, message):
        """Queue-driven mounts do not fire TreeBrick.sample_mount_started
        because SampleQueueEntry.execute() calls
        base_queue_entry.mount_sample() directly. That helper does call
        sample_changer.trigger_progress_message() with well-known strings,
        which we use here to open/close the popup for every queued sample.
        """
        if not message:
            return
        msg = str(message).strip().lower()

        # Gate by the "During mount show sample changer" checkbox in the tree.
        show = True
        if self._tree_brick is not None:
            try:
                show = bool(
                    self._tree_brick.dc_tree_widget.show_sc_during_mount
                )
            except AttributeError:
                show = True

        if msg.startswith("loading sample"):
            if self._queue_mount_active:
                return
            if not show:
                return
            self._queue_mount_active = True
            self._on_mount_started()
        elif msg.startswith("sample loaded") or \
                msg.startswith("sample not loaded"):
            if not self._queue_mount_active:
                return
            self._queue_mount_active = False
            self._on_mount_finished()

    # ------------------------------------------------------------------
    # Sample changer status (purely informational — no popup trigger)
    # ------------------------------------------------------------------

    def _on_sc_status_changed(self, status):
        self.status_ledit.setText(status)
        if self._popup is not None:
            self._popup_status_ledit.setText(status)
        if status == "Moving":
            colors.set_widget_color(
                self.status_ledit, colors.LIGHT_GREEN, qt_import.QPalette.Base
            )
        else:
            colors.set_widget_color(
                self.status_ledit, colors.WHITE, qt_import.QPalette.Base
            )

    # ------------------------------------------------------------------
    # Non-modal popup mode
    # ------------------------------------------------------------------

    def _ensure_popup(self):
        if self._popup is not None:
            return
        popup = qt_import.QDialog(self, qt_import.Qt.Window)
        popup.setWindowTitle("Sample Changer Cameras")
        popup.setModal(False)
        popup.setWindowFlags(
            popup.windowFlags() | qt_import.Qt.WindowStaysOnTopHint
        )

        left_title = qt_import.QLabel("Gonio camera", popup)
        left_title.setAlignment(qt_import.Qt.AlignCenter)
        self._popup_left_view = qt_import.QLabel(popup)
        self._popup_left_view.setAlignment(qt_import.Qt.AlignCenter)
        self._popup_left_view.setText("(waiting for frames...)")

        right_title = qt_import.QLabel("Robot camera", popup)
        right_title.setAlignment(qt_import.Qt.AlignCenter)
        self._popup_right_view = qt_import.QLabel(popup)
        self._popup_right_view.setAlignment(qt_import.Qt.AlignCenter)
        self._popup_right_view.setText("(waiting for frames...)")

        left_panel = qt_import.QWidget(popup)
        ll = qt_import.QVBoxLayout(left_panel)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(left_title)
        ll.addWidget(self._popup_left_view)

        right_panel = qt_import.QWidget(popup)
        rl = qt_import.QVBoxLayout(right_panel)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(right_title)
        rl.addWidget(self._popup_right_view)

        cam_row = qt_import.QHBoxLayout()
        cam_row.addWidget(left_panel)
        cam_row.addWidget(right_panel)

        status_row = qt_import.QHBoxLayout()
        status_row.addWidget(qt_import.QLabel("SC status:", popup))
        self._popup_status_ledit = qt_import.QLineEdit(popup)
        self._popup_status_ledit.setReadOnly(True)
        self._popup_status_ledit.setText(self.status_ledit.text())
        status_row.addWidget(self._popup_status_ledit)

        self._popup_progress = qt_import.QProgressBar(popup)
        self._popup_progress.setMinimum(0)
        self._popup_progress.setMaximum(100)

        main = qt_import.QVBoxLayout(popup)
        main.addLayout(status_row)
        main.addLayout(cam_row)
        main.addWidget(self._popup_progress)

        self._popup = popup

    def _show_popup(self):
        self._ensure_popup()
        self._popup.show()
        self._popup.raise_()
        self._popup.activateWindow()

    def _hide_popup(self):
        if self._popup is not None:
            self._popup.hide()

    def _on_left_frame(self, pixmap):
        self.left_view.setPixmap(pixmap)
        if self._popup is not None:
            self._popup_left_view.setPixmap(pixmap)

    def _on_right_frame(self, pixmap):
        self.right_view.setPixmap(pixmap)
        if self._popup is not None:
            self._popup_right_view.setPixmap(pixmap)

    def _on_progress_init(self, progress_type, number_of_steps, use_dialog=False):
        self.progress_bar.reset()
        self.progress_bar.setMaximum(number_of_steps)
        if self._popup is not None:
            self._popup_progress.reset()
            self._popup_progress.setMaximum(number_of_steps)

    def _on_progress_step(self, step, msg=None):
        self.progress_bar.setValue(step)
        if self._popup is not None:
            self._popup_progress.setValue(step)

    def _on_progress_stop(self, *args):
        self.progress_bar.reset()
        if self._popup is not None:
            self._popup_progress.reset()
