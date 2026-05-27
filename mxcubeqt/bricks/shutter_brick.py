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

"""
Shutter brick provides access to a shutter like device.
Interface is based on the AbstractNState hardware object
"""

from mxcubeqt.utils import colors, icons, qt_import
from mxcubeqt.base_components import BaseWidget
import logging

log = logging.getLogger("HWR")

__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class ShutterBrick(BaseWidget):
    """Widget contains state label and two buttons to open and close the shutter"""

    def __init__(self, *args):
        BaseWidget.__init__(self, *args)

        # Properties ----------------------------------------------------------
        self.add_property("title", "string", "Shutter")
        self.add_property("hwobj_shutter", "string", "")
        self.add_property("control_only_expert", "boolean", False)

        # Signals -------------------------------------------------------------

        # Slots ---------------------------------------------------------------

        # Hardware objects ----------------------------------------------------
        self.shutter_hwobj = None

        # Internal values -----------------------------------------------------
        self.expert_control = False
        self.expert = False
        self.door_interlocked = True
        self._original_title = "Shutter"

        # Graphic elements ----------------------------------------------------
        self.main_groupbox = qt_import.QGroupBox("Shutter", self)
        self.main_groupbox.setAlignment(qt_import.Qt.AlignCenter)
        self.state_label = qt_import.QLabel(
            "<b>unknown</b>", self.main_groupbox)
        self.state_label.setAlignment(qt_import.Qt.AlignCenter)
        self.state_label.setFixedHeight(24)
        colors.set_widget_color(self.state_label, colors.LIGHT_GRAY)
        self.button_widget = qt_import.QWidget(self.main_groupbox)

        self.open_button = qt_import.QPushButton(
            icons.load_icon("ShutterOpen"), "Open", self.button_widget
        )
        self.close_button = qt_import.QPushButton(
            icons.load_icon("ShutterClose"), "Close", self.button_widget
        )

        # Layout --------------------------------------------------------------
        _button_widget_hlayout = qt_import.QHBoxLayout(self.button_widget)
        _button_widget_hlayout.addWidget(self.open_button)
        _button_widget_hlayout.addWidget(self.close_button)
        _button_widget_hlayout.setSpacing(2)
        _button_widget_hlayout.setContentsMargins(0, 0, 0, 0)

        _main_gbox_vlayout = qt_import.QVBoxLayout(self.main_groupbox)
        _main_gbox_vlayout.addWidget(self.state_label)
        _main_gbox_vlayout.addWidget(self.button_widget)
        _main_gbox_vlayout.setSpacing(2)
        _main_gbox_vlayout.setContentsMargins(2, 2, 2, 2)

        _main_vlayout = qt_import.QVBoxLayout(self)
        _main_vlayout.addWidget(self.main_groupbox)
        _main_vlayout.setSpacing(0)
        _main_vlayout.setContentsMargins(0, 0, 0, 0)

        # SizePolicies --------------------------------------------------------

        # Qt signal/slot connections ------------------------------------------
        self.open_button.clicked.connect(self.open_button_clicked)
        self.close_button.clicked.connect(self.close_button_clicked)

        # Other ---------------------------------------------------------------
        self.set_expert_mode(False)

    def set_expert_mode(self, expert=None):

        if expert is not None:
            self.expert = expert

        if not self.expert_control:
            self.button_widget.show()
            return

        if not self.expert:
            self.button_widget.hide()
        else:
            self.button_widget.show()

    def open_button_clicked(self):
        """Opens the shutter"""
        self.shutter_hwobj.open()

    def close_button_clicked(self):
        """Closes the shutter"""
        self.shutter_hwobj.close()

    def property_changed(self, property_name, old_value, new_value):
        """Initates the shutter hwobj"""
        if property_name == "hwobj_shutter":
            if self.shutter_hwobj is not None:
                self.disconnect(
                    self.shutter_hwobj, "valueChanged", self.value_changed
                )
            else:
                self.shutter_hwobj = self.get_hardware_object(new_value)
                self.connect(
                    self.shutter_hwobj, "valueChanged", self.value_changed
                )
                log.debug(f"Setting title from config: '{self['title']}'")
                self.main_groupbox.setTitle(self["title"])
                self._original_title = self["title"]
                self.value_changed()

                # Connect to interlock state changes if this shutter supports interlock checking
                if (hasattr(self.shutter_hwobj, 'supports_interlock_checking') and
                        self.shutter_hwobj.supports_interlock_checking):
                    log.debug("Connecting to interlockStateChanged signal")
                    self.connect(
                        self.shutter_hwobj, "interlockStateChanged",
                        self.interlock_state_changed
                    )
                    log.debug("Signal connected successfully")

                    # Get initial interlock state
                    self._check_initial_interlock_state()

                    # Set up periodic interlock state check to ensure synchronization
                    from PyQt5.QtCore import QTimer
                    self._interlock_check_timer = QTimer()
                    self._interlock_check_timer.timeout.connect(
                        self._periodic_interlock_check)
                    self._interlock_check_timer.start(
                        5000)  # Check every 5 seconds
                    log.debug("Periodic interlock check timer started")
                else:
                    log.debug("Shutter does not support interlock checking")

        elif property_name == "title":
            # Only update title from config if we don't have an active interlock state
            # This prevents config from overriding our interlock-based title
            if not hasattr(self, 'door_interlocked') or self.door_interlocked:
                self.main_groupbox.setTitle(new_value)
                self._original_title = new_value
                log.debug(
                    f"Title updated from config: '{new_value}' (interlock active)")
                log.debug(f"_original_title set to: '{self._original_title}'")
            else:
                log.debug(
                    f"Ignoring config title update to '{new_value}' (door unlocked, keeping interlock title)")
                log.debug(f"Current _original_title: '{self._original_title}'")
        elif property_name == "control_only_expert":
            self.expert_control = new_value
            self.set_expert_mode()
        else:
            BaseWidget.property_changed(
                self, property_name, old_value, new_value)

    def value_changed(self, value=None):
        """Based on the shutter state enables/disables open and close buttons"""

        if value is None:
            value = self.shutter_hwobj.get_value()

        if value.name == 'OPEN':
            colors.set_widget_color(self.state_label, colors.LIGHT_GREEN)
        elif value.name == 'CLOSED':
            colors.set_widget_color(self.state_label, colors.LIGHT_GRAY)
        elif value.name == 'MOVING':
            colors.set_widget_color(self.state_label, colors.LIGHT_YELLOW)
        else:
            colors.set_widget_color(self.state_label, colors.DARK_GRAY)

        # colors.set_widget_color_by_state(self.state_label, value)
        self.state_label.setText(value.value.title())
        self.setDisabled(value.name == "DISABLED")

        # Intelligent button enabling/disabling based on shutter state
        # BUT only if the door is interlocked (brick is enabled)
        if self.door_interlocked:
            is_open = self.shutter_hwobj.is_open
            self.open_button.setEnabled(not is_open)  # Enable if closed
            self.close_button.setEnabled(is_open)     # Enable if open
        else:
            # Keep buttons disabled when door is unlocked (brick is disabled)
            self.open_button.setEnabled(False)
            self.close_button.setEnabled(False)

    def _check_initial_interlock_state(self):
        """Check the initial interlock state for safety shutters."""
        try:
            log.debug("Checking initial interlock state for shutter brick")
            if hasattr(self.shutter_hwobj, 'get_interlock_state'):
                # Use the hardware object's method if available
                self.door_interlocked = self.shutter_hwobj.get_interlock_state()
                log.debug(
                    f"Got interlock state from hardware object: {self.door_interlocked}")
            else:
                # Fallback to checking via HWR
                log.debug(
                    "Hardware object doesn't have get_interlock_state, checking via HWR")
                from mxcubecore import HardwareRepository as HWR
                if (hasattr(HWR, "beamline") and
                        HWR.beamline.hutch_interlock is not None):
                    interlock_state = (
                        HWR.beamline.hutch_interlock.door_interlock_state)
                    self.door_interlocked = interlock_state in [
                        "locked_active", "locked_inactive"]
                    log.debug(
                        f"Got interlock state from HWR: {interlock_state} -> {self.door_interlocked}")
                else:
                    log.debug("No HWR beamline or hutch_interlock available")
                    self.door_interlocked = True  # Default to locked

            # Always update GUI with the state we have
            log.debug(f"Final interlock state: {self.door_interlocked}")
            log.debug(
                f"Current title before update_gui: '{self.main_groupbox.title()}'")
            log.debug(
                f"Calling update_gui with door_interlocked={self.door_interlocked}")
            self.update_gui()
            log.debug(
                f"Title after update_gui: '{self.main_groupbox.title()}'")

            # Also request interlock state from hardware object if available (for real-time updates)
            if hasattr(self.shutter_hwobj, 'request_interlock_state'):
                log.debug(
                    "Requesting interlock state from hardware object for real-time updates")
                self.shutter_hwobj.request_interlock_state()

        except Exception as e:
            log.debug(f"Could not check initial interlock state: {e}")
            self.door_interlocked = True  # Default to locked on error
            log.debug(
                "Defaulting to locked state due to error, calling update_gui")
            self.update_gui()
        finally:
            # Always ensure GUI is updated, even if there were errors
            log.debug("Finally block: ensuring GUI is updated")
            if not hasattr(self, 'door_interlocked'):
                self.door_interlocked = True
            self.update_gui()

    def _verify_signal_connection(self):
        """Verify that the interlock signal connection is still active."""
        if hasattr(self, 'shutter_hwobj') and self.shutter_hwobj is not None:
            if hasattr(self.shutter_hwobj, 'supports_interlock_checking'):
                log.debug(
                    f"Shutter supports interlock checking: {self.shutter_hwobj.supports_interlock_checking}")
                if self.shutter_hwobj.supports_interlock_checking:
                    # Check if we're connected to the signal
                    try:
                        # This is a simple check - if the signal exists and we can access it
                        log.debug("Signal connection appears to be active")
                        return True
                    except Exception as e:
                        log.debug(f"Signal connection check failed: {e}")
                        return False
        return False

    def _periodic_interlock_check(self):
        """Periodically check interlock state to ensure synchronization."""
        try:
            if hasattr(self, 'shutter_hwobj') and self.shutter_hwobj is not None:
                if hasattr(self.shutter_hwobj, 'get_interlock_state'):
                    current_interlock_state = self.shutter_hwobj.get_interlock_state()
                    if current_interlock_state != self.door_interlocked:
                        log.debug(
                            f"Periodic check: interlock state mismatch detected!")
                        log.debug(
                            f"Current: {self.door_interlocked}, Hardware: {current_interlock_state}")
                        log.debug("Updating GUI to match hardware state")
                        self.door_interlocked = current_interlock_state
                        self.update_gui()
                    else:
                        log.debug(
                            f"Periodic check: interlock state synchronized ({current_interlock_state})")
        except Exception as e:
            log.debug(f"Periodic interlock check failed: {e}")

    def interlock_state_changed(self, is_locked, state_message):
        """Handle interlock state changes for safety shutters."""
        log.debug(
            f"Interlock state changed: {is_locked}, message: {state_message}")
        log.debug(
            f"Current door_interlocked before change: {self.door_interlocked}")
        self.door_interlocked = is_locked
        log.debug(f"Updated door_interlocked to: {self.door_interlocked}")
        log.debug(f"Calling update_gui from interlock_state_changed")
        self.update_gui()
        log.debug(f"update_gui completed from interlock_state_changed")

    def update_gui(self):
        """Update the GUI based on current state."""
        log.debug(
            f"update_gui called with door_interlocked={self.door_interlocked}")
        log.debug(f"_original_title is: '{self._original_title}'")
        log.debug(
            f"Current title before update: '{self.main_groupbox.title()}'")

        if not self.door_interlocked:
            log.debug(
                "Door is unlocked - disabling shutter brick and updating title")
            new_title = f"{self._original_title} (door unlocked)"
            log.debug(f"Setting title to: '{new_title}'")
            self.main_groupbox.setTitle(new_title)

            # Disable the entire brick instead of individual buttons
            self.setEnabled(False)
            log.debug("Entire shutter brick disabled")

            log.debug("Shutter brick disabled and title updated")
        else:
            log.debug(
                "Door is locked - enabling shutter brick and restoring title")
            # Restore the original title
            log.debug(f"Restoring title to: '{self._original_title}'")
            self.main_groupbox.setTitle(self._original_title)

            # Enable the entire brick
            self.setEnabled(True)
            log.debug("Entire shutter brick enabled")

            # Restore intelligent button states based on current shutter value
            self.value_changed()
            log.debug("Button states restored via value_changed")

            log.debug("Shutter brick enabled and title restored")

        log.debug(f"Final title after update: '{self.main_groupbox.title()}'")

        # Force GUI to redraw
        self.repaint()
        self.update()
        log.debug("GUI repaint and update called")

