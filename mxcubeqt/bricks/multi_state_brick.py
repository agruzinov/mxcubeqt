"""
[Name] MultiStateBrick

[Description]
The MultiStateBrick displays checkbox with available states on a MotorsNState object.

[Properties]
-----------------------------------------------------------------------
| name         | type   | description
-----------------------------------------------------------------------
| mnenmonic  | string | name of the BeamAperture Hardware Object
-----------------------------------------------------------------------

[Signals] -

[Slots] -

[Comments] -

[Hardware Objects]
-----------------------------------------------------------------------
| name            | signals         | functions
-----------------------------------------------------------------------
| mnemonic        | valueChanged, stateChanged |
-----------------------------------------------------------------------
"""

try:
    unichr
except NameError:
    unichr = chr

import logging
from typing import Optional, List

from mxcubeqt.utils import colors, qt_import
from mxcubeqt.base_components import BaseWidget
from mxcubecore.BaseHardwareObjects import HardwareObjectState

__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class MultiStateBrick(BaseWidget):
    units = {"micron": "\u03BC"}

    def __init__(self, *args):
        BaseWidget.__init__(self, *args)
        self.log = logging.getLogger("HWR.MultiStateBrick")
        # Hardware objects ----------------------------------------------------
        self.multi_hwobj: Optional[object] = None

        # Internal values -----------------------------------------------------
        self.positions: List[str] = []
        self.multibutton: bool = False
        self.multibuttons: List[qt_import.QPushButton] = []

        # Properties ----------------------------------------------------------
        self.add_property("label", "string", "")
        self.add_property("title", "string", "")
        self.add_property("mnemonic", "string", "")
        self.add_property("multibutton", "boolean", False)

        # Graphic elements ----------------------------------------------------
        self.main_gbox = qt_import.QGroupBox("", self)
        _main_vlayout = qt_import.QVBoxLayout(self)
        _main_vlayout.addWidget(self.main_gbox)
        _main_vlayout.addStretch()
        _main_vlayout.setSpacing(0)
        _main_vlayout.setContentsMargins(0, 0, 0, 0)

        self.label = qt_import.QLabel(self.main_gbox)
        self.multi_position_combo = qt_import.QComboBox(self.main_gbox)
        self.multi_position_combo.setMinimumWidth(100)
        self.multi_button_box = qt_import.QWidget(self.main_gbox)
        self._multi_button_hlayout = qt_import.QHBoxLayout(self.multi_button_box)

        # Layout --------------------------------------------------------------
        _main_gbox_hlayout = qt_import.QHBoxLayout(self.main_gbox)
        _main_gbox_hlayout.addWidget(self.label)
        _main_gbox_hlayout.addWidget(self.multi_position_combo)
        _main_gbox_hlayout.addWidget(self.multi_button_box)
        _main_gbox_hlayout.setSpacing(2)
        _main_gbox_hlayout.setContentsMargins(0, 0, 0, 0)

        # Qt signal/slot connections ------------------------------------------
        self.multi_position_combo.activated.connect(self.change_value)
        self.switch_multibutton_mode(False)

    def property_changed(self, property_name: str, old_value: str, new_value: str) -> None:
        if property_name == "label":
            self.label.setText(new_value) if new_value else self.label.show()
        elif property_name == "title":
            if new_value:
                self.main_gbox.setTitle(new_value)
        elif property_name == "multibutton":
            self.multibutton = bool(new_value)
            if self.positions and self.multi_hwobj:
                self.switch_multibutton_mode(self.multibutton)
        elif property_name == "mnemonic":
            # Disconnect previous hardware object signals
            if self.multi_hwobj is not None:
                try:
                    self.multi_hwobj.disconnect("stateChanged", self.state_changed)
                    self.multi_hwobj.disconnect("valueChanged", self.value_changed)
                except Exception as e:
                    logging.warning(f"Failed to disconnect signals: {e}")

            # Connect new hardware object
            self.multi_hwobj = self.get_hardware_object(new_value)
            if self.multi_hwobj is not None:
                if not hasattr(self.multi_hwobj, "get_position_list"):
                    logging.error("Hardware object lacks get_position_list method")
                    return
                # Connect signals
                try:
                    self.multi_hwobj.connect("stateChanged", self.state_changed)
                    self.multi_hwobj.connect("valueChanged", self.value_changed)
                except Exception as e:
                    logging.error(f"Failed to connect signals: {e}")
                # Initialize UI
                self.fill_positions()
                if self.multibutton:
                    self.switch_multibutton_mode(True)
                self.state_changed(self.multi_hwobj.get_state())
                self.value_changed(self.multi_hwobj.get_value())

                # Start periodic polling to catch state changes from other
                # instances (e.g. NanoDiff's sub-objects are separate from
                # the GUI-facing top-level hardware objects).
                if not hasattr(self, "_poll_timer"):
                    self._poll_timer = qt_import.QTimer(self)
                    self._poll_timer.timeout.connect(self._poll_state)
                self._poll_timer.start(500)
            else:
                logging.error(f"Failed to initialize hardware object: {new_value}")
        else:
            BaseWidget.property_changed(self, property_name, old_value, new_value)

    def switch_multibutton_mode(self, mode: bool) -> None:
        self.multi_position_combo.setVisible(not mode)
        self.multi_button_box.setVisible(mode)

    def get_position_label(self, posidx: int) -> str:
        """Return the label for a position. Simplified for P11Collimator."""
        return str(self.positions[posidx])

    def fill_positions(self) -> None:
        """Populate combo box and buttons with positions from the hardware object."""
        if not self.multi_hwobj or not hasattr(self.multi_hwobj, "get_position_list"):
            logging.error("No valid hardware object for filling positions")
            return

        self.positions = self.multi_hwobj.get_position_list()
        self.multi_position_combo.clear()
        self.multibuttons = []

        # Clear existing buttons
        while self._multi_button_hlayout.count():
            item = self._multi_button_hlayout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for posidx, pos in enumerate(self.positions):
            poslabel = self.get_position_label(posidx)
            self.multi_position_combo.addItem(poslabel)
            but = qt_import.QPushButton(poslabel)
            but.clicked.connect(lambda _, idx=posidx: self.change_value(idx))
            self._multi_button_hlayout.addWidget(but)
            self.multibuttons.append(but)

        self.value_changed()

    def change_value(self, index: int) -> None:
        """Set the hardware object to the selected position."""
        if not self.positions or not isinstance(self.positions, list):
            logging.error(f"Invalid positions: {self.positions}")
            return
        if 0 <= index < len(self.positions):
            position_name = self.positions[index]
            try:
                self.multi_hwobj.set_value(position_name)
            except Exception as e:
                logging.error(f"Failed to set position {position_name}: {e}")
        else:
            logging.error(f"Invalid index: {index}")

    def set_ui_color(self, color: qt_import.QColor) -> None:
        """Set the color of the combo box and buttons."""
        colors.set_widget_color(self.multi_position_combo, color, qt_import.QPalette.Button)
        for button in self.multibuttons:
            colors.set_widget_color(button, color, qt_import.QPalette.Button)

    def _poll_state(self) -> None:
        """Periodic poll to detect state changes from external sources."""
        if not self.multi_hwobj:
            return
        is_moving = hasattr(self.multi_hwobj, "is_moving") and self.multi_hwobj.is_moving()
        state = self.multi_hwobj.get_state()
        is_busy = is_moving or state == HardwareObjectState.BUSY
        # Determine what the UI currently shows
        currently_busy = not self.isEnabled()
        if is_busy != currently_busy:
            self.state_changed(state)
        # Always refresh the displayed value so dropdown tracks position
        self.value_changed()

    def state_changed(self, state: Optional[HardwareObjectState] = None) -> None:
        self.log.debug(f"Received stateChanged: {state}")
        if not self.multi_hwobj:
            self.log.warning("No hardware object for state update")
            return
        if state is None:
            state = self.multi_hwobj.get_state()
            self.log.debug(f"Queried state: {state}")
        is_moving = hasattr(self.multi_hwobj, "is_moving") and self.multi_hwobj.is_moving()
        is_busy = is_moving or state == HardwareObjectState.BUSY
        self.log.debug(f"State update: is_moving={is_moving}, is_busy={is_busy}")
        color = colors.LIGHT_YELLOW if is_busy else colors.LIGHT_GREEN
        self.setEnabled(not is_busy)
        self.set_ui_color(color)
        if is_busy:
            self.log.debug("Scheduling next state check")
            qt_import.QTimer.singleShot(200, lambda: self.state_changed())
            
    def value_changed(self, value: Optional[str] = None) -> None:
        """Update the combo box and buttons when the hardware value changes."""
        if not self.multi_hwobj or not self.positions:
            return

        if value is None:
            try:
                value = self.multi_hwobj.get_value()
            except Exception as e:
                logging.error(f"Failed to get value: {e}")
                value = None

        # If value is None or not a known position, keep the current display
        if not isinstance(value, str) or value not in self.positions:
            return

        self.multi_position_combo.blockSignals(True)
        index = self.positions.index(value)
        self.multi_position_combo.setCurrentIndex(index)
        for i, button in enumerate(self.multibuttons):
            button.setEnabled(i != index)
        self.multi_position_combo.blockSignals(False)
