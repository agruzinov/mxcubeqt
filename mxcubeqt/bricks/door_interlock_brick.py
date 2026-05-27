#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software (LGPLv3+).

from mxcubeqt.utils import colors, icons, qt_import
from mxcubeqt.base_components import BaseWidget
from mxcubecore import HardwareRepository as HWR


__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class DoorInterlockBrick(BaseWidget):
    STATES = {
        "unknown":         colors.LIGHT_GRAY,
        "disabled":        colors.LIGHT_GRAY,
        "error":           colors.LIGHT_RED,
        "unlocked":        colors.LIGHT_GRAY,
        "locked_active":   colors.LIGHT_GREEN,
        "locked_inactive": colors.LIGHT_GRAY,
    }

    def __init__(self, *args):
        super().__init__(*args)

        # UI -----------------------------------------------------------------
        self.main_groupbox = qt_import.QGroupBox("Door interlock", self)
        self.main_groupbox.setAlignment(qt_import.Qt.AlignCenter)

        self.state_label = qt_import.QLabel(
            "<b>Unknown</b>", self.main_groupbox)
        colors.set_widget_color(self.state_label, self.STATES["unknown"])
        self.state_label.setAlignment(qt_import.Qt.AlignCenter)
        self.state_label.setFixedHeight(24)

        self.unlock_door_button = qt_import.QPushButton(
            icons.load_icon("EnterHutch"), "Unlock", self.main_groupbox
        )

        g = qt_import.QVBoxLayout(self.main_groupbox)
        g.addWidget(self.state_label)
        g.addWidget(self.unlock_door_button)
        g.setSpacing(2)
        g.setContentsMargins(4, 4, 4, 4)

        root = qt_import.QVBoxLayout(self)
        root.addWidget(self.main_groupbox)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # Tooltips
        self.state_label.setToolTip("Shows the current door interlock state")
        self.unlock_door_button.setToolTip("Unlocks the doors (opens EH)")

        # Actions
        self.unlock_door_button.clicked.connect(self.unlock_doors)

        # Polling fallback (covers missed/late signals at startup)
        # Use QTimer from qt_import (flattened API)
        self._poll_timer = qt_import.QTimer(self)
        self._poll_timer.setInterval(500)  # ms
        self._poll_timer.timeout.connect(self._poll_once)
        self._last_state = None
        self._wired = False
        self._safety_shutter = None
        self._shutter_wired = False
        self._shutter_closed = None

    # ----------------------------------------------------------------------
    # MXCuBE lifecycle
    # ----------------------------------------------------------------------
    def run(self):
        """Connect signals after HWR is ready and paint the true state."""
        hi = getattr(HWR.beamline, "hutch_interlock", None)
        if hi is None:
            self._wire_safety_shutter(None)
            self._apply_state("unknown")
            self._poll_timer.stop()
            return

        # Avoid double-connecting if run() is called again
        if self._wired:
            try:
                self.disconnect(hi, "valueChanged", self.value_changed)
                self.disconnect(hi, "doorInterlockStateChanged",
                                self.state_changed)
            except Exception:
                pass

        self.connect(hi, "valueChanged", self.value_changed)
        self.connect(hi, "doorInterlockStateChanged", self.state_changed)
        self._wired = True

        self._wire_safety_shutter(self._get_safety_shutter_hwobj())

        # Fetch and apply current state once, then start polling as a safety net
        self._init_state()
        self._init_shutter_state()
        if not self._poll_timer.isActive():
            self._poll_timer.start()

    # ----------------------------------------------------------------------
    # UI actions
    # ----------------------------------------------------------------------
    def unlock_doors(self):
        if not self._confirm_unlock_action():
            self._update_unlock_button_state()
            return

        self.unlock_door_button.setEnabled(False)
        try:
            HWR.beamline.hutch_interlock.unlock()
        except Exception:
            # Button will be re-enabled appropriately on next state update
            pass

    def _confirm_unlock_action(self):
        hi = getattr(HWR.beamline, "hutch_interlock", None)
        if hi is None:
            return False

        conf_msg = (
            "Do you really want to unlock the hutch?\n\n"
            "This will enable hutch access and will :\n"
            "- break the interlock (on-site presence is needed to reset it)\n"
            "- set the transfer phase\n"
            "- retract cryo\n"
            "- move detector to safety position (1200 mm)"
        )

        conf_dialog = qt_import.QMessageBox(self)
        conf_dialog.setIcon(qt_import.QMessageBox.Warning)
        conf_dialog.setWindowTitle("Unlock hutch")
        conf_dialog.setText(conf_msg)
        conf_dialog.setStandardButtons(
            qt_import.QMessageBox.Ok | qt_import.QMessageBox.Cancel
        )

        return conf_dialog.exec_() == qt_import.QMessageBox.Ok

    def updateLabel(self, label):
        self.main_groupbox.setTitle(label)

    # ----------------------------------------------------------------------
    # Signal handlers
    # ----------------------------------------------------------------------
    def value_changed(self, value):
        """Handles legacy valueChanged where 'value' may be an object with .value."""
        state = getattr(value, "value", value)
        st = self._normalize_state_str(state)
        # Always use QTimer.singleShot to ensure UI updates happen in GUI thread
        # This prevents crashes from cross-thread UI updates
        qt_import.QTimer.singleShot(0, lambda s=st: self._apply_state(s))

    def state_changed(self, state, _msg):
        """Handles doorInterlockStateChanged(state, msg)."""
        st = self._normalize_state_str(state)
        # Always use QTimer.singleShot to ensure UI updates happen in GUI thread
        # This prevents crashes from cross-thread UI updates
        qt_import.QTimer.singleShot(0, lambda s=st: self._apply_state(s))

    # ----------------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------------
    def _init_state(self):
        """Read current state from the HW object once at startup."""
        self._apply_state(self._read_current_state())

    def _poll_once(self):
        """Periodic refresh to avoid stale UI if startup signals were missed."""
        st = self._read_current_state()
        if st != self._last_state:
            self._apply_state(st)

        shutter_closed = self._read_shutter_closed()
        if shutter_closed != self._shutter_closed:
            self._apply_shutter_state(shutter_closed)

        # Keep button state synchronized even when unlock command does not
        # trigger an interlock state transition.
        self._update_unlock_button_state()

    def _init_shutter_state(self):
        self._apply_shutter_state(self._read_shutter_closed())

    def _get_safety_shutter_hwobj(self):
        beamline = getattr(HWR, "beamline", None)
        if beamline is None:
            return None

        shutter = getattr(beamline, "safety_shutter", None)
        if shutter is not None:
            return shutter

        hi = getattr(beamline, "hutch_interlock", None)
        if hi is None:
            return None

        return getattr(hi, "safety_shutter", None)

    def _wire_safety_shutter(self, shutter):
        if self._shutter_wired and self._safety_shutter is not None:
            try:
                self.disconnect(
                    self._safety_shutter,
                    "valueChanged",
                    self.shutter_value_changed,
                )
            except Exception:
                pass

        self._safety_shutter = shutter
        self._shutter_wired = False

        if shutter is None:
            self._shutter_closed = None
            return

        try:
            self.connect(shutter, "valueChanged", self.shutter_value_changed)
            self._shutter_wired = True
        except Exception:
            self._shutter_wired = False

    def shutter_value_changed(self, value=None):
        shutter_closed = self._normalize_shutter_closed(value)
        qt_import.QTimer.singleShot(
            0,
            lambda is_closed=shutter_closed: self._apply_shutter_state(is_closed),
        )

    def _read_shutter_closed(self):
        if self._safety_shutter is None:
            return None

        try:
            return bool(self._safety_shutter.is_closed)
        except Exception:
            pass

        try:
            return self._normalize_shutter_closed(self._safety_shutter.get_value())
        except Exception:
            return False

    def _normalize_shutter_closed(self, value):
        state = value
        if isinstance(state, (tuple, list)) and state:
            state = state[0]

        if state is None:
            return False

        name = getattr(state, "name", None)
        if isinstance(name, str):
            return name.strip().upper() == "CLOSED"

        enum_value = getattr(state, "value", None)
        if isinstance(enum_value, str):
            return enum_value.strip().upper() == "CLOSED"

        state_str = str(state).strip().upper()
        return state_str == "CLOSED" or state_str.endswith(".CLOSED")

    def _apply_shutter_state(self, is_closed):
        self._shutter_closed = None if is_closed is None else bool(is_closed)
        self._update_unlock_button_state()

    def _read_current_state(self):
        hi = getattr(HWR.beamline, "hutch_interlock", None)
        if hi is None:
            return "unknown"

        # Prefer an explicit string accessor if available
        try:
            if hasattr(hi, "get_state_string"):
                s = hi.get_state_string()
                return self._normalize_state_str(s)
        except Exception:
            pass

        # Fall back to get_state()
        try:
            if hasattr(hi, "get_state"):
                s = hi.get_state()
                return self._normalize_state_str(s)
        except Exception:
            pass

        # Fall back to boolean lock status
        try:
            if hasattr(hi, "door_is_interlocked"):
                locked = bool(hi.door_is_interlocked())
                # If we only know "locked/unlocked" and not beam status, call it 'locked_inactive'
                return "locked_inactive" if locked else "unlocked"
        except Exception:
            pass

        # Last resort: direct attribute
        s = getattr(hi, "door_interlock_state", None)
        return self._normalize_state_str(s if s is not None else "unknown")

    def _normalize_state_str(self, s):
        """Map various inputs to one of our known state strings."""
        st = str(s).strip().lower() if s is not None else "unknown"
        if st in self.STATES:
            return st
        # Generic substrings
        if st.startswith("locked"):
            # Without beam context default to 'locked_inactive'
            return "locked_inactive"
        if "unlock" in st or st == "open":
            return "unlocked"
        if "error" in st or "fault" in st:
            return "error"
        if "disable" in st:
            return "disabled"
        return "unknown"

    def _apply_state(self, st: str):
        st = st if st in self.STATES else "unknown"
        self._last_state = st

        # Text & color
        txt = st.replace("_", " ").title()
        self.state_label.setText(f"<b>{txt}</b>")
        colors.set_widget_color(self.state_label, self.STATES[st])

        self._update_unlock_button_state()

        # Helpful tooltip
        hints = {
            "locked_active":   "Door is locked (beam ON).",
            "locked_inactive": "Door is locked (beam OFF).",
            "unlocked":        "Door is unlocked (EH open).",
            "disabled":        "Interlock disabled.",
            "error":           "Interlock error.",
            "unknown":         "Interlock state unknown.",
        }
        self.state_label.setToolTip(hints.get(st, ""))

    def _update_unlock_button_state(self):
        is_locked = self._last_state in ("locked_active", "locked_inactive")
        shutter_known = self._shutter_closed is not None
        shutter_closed = bool(self._shutter_closed)
        can_unlock = is_locked and (shutter_closed or not shutter_known)
        self.unlock_door_button.setEnabled(can_unlock)

        if can_unlock:
            if shutter_known:
                tooltip = "Unlocks the doors (opens EH)"
            else:
                tooltip = "Unlocks the doors (safety shutter state unavailable)."
        elif not is_locked:
            tooltip = "Unlock is available only when the door interlock is locked."
        else:
            tooltip = "Unlock is available only when the safety shutter is Closed."

        self.unlock_door_button.setToolTip(tooltip)

