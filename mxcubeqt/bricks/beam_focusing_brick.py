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

from mxcubeqt.utils import colors, qt_import
from mxcubeqt.base_components import BaseWidget
import logging
import gevent


__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "DESY"


class BeamFocusingBrick(BaseWidget):
    def __init__(self, *args):
        BaseWidget.__init__(self, *args)

        # Hardware objects ----------------------------------------------------
        self.beam_focusing_hwobj = None

        # Internal values -----------------------------------------------------

        # Properties ----------------------------------------------------------
        self.add_property("mnemonic", "string", "")

        # Signals ------------------------------------------------------------

        # Slots ---------------------------------------------------------------

        # Graphic elements ----------------------------------------------------
        _main_groupbox = qt_import.QGroupBox("Beam focus", self)
        self.beam_focusing_combo = qt_import.QComboBox(_main_groupbox)
        self.beam_focusing_combo.setMinimumWidth(100)

        # Layout --------------------------------------------------------------
        _main_groupbox_vlayout = qt_import.QVBoxLayout(_main_groupbox)
        _main_groupbox_vlayout.addWidget(self.beam_focusing_combo)
        _main_groupbox_vlayout.addStretch()
        _main_groupbox_vlayout.setSpacing(2)
        _main_groupbox_vlayout.setContentsMargins(2, 2, 2, 2)

        _main_vlayout = qt_import.QVBoxLayout(self)
        _main_vlayout.addWidget(_main_groupbox)
        _main_vlayout.setSpacing(0)
        _main_vlayout.setContentsMargins(2, 2, 2, 2)

        # Qt signal/slot connections ------------------------------------------
        self.beam_focusing_combo.activated.connect(self.change_focus_mode)

        # SizePolicies --------------------------------------------------------

        # Other ---------------------------------------------------------------
        colors.set_widget_color(
            self.beam_focusing_combo, colors.LIGHT_GREEN, qt_import.QPalette.Button
        )
    
    def property_changed(self, property_name, old_value, new_value):
        if property_name == "mnemonic":
            if self.beam_focusing_hwobj is not None:
                self.disconnect(
                    self.beam_focusing_hwobj,
                    "focusingModeChanged",
                    self.focus_mode_changed,
                )
                self.disconnect(
                    self.beam_focusing_hwobj,
                    "stateChanged",
                    self.beam_state_changed,
                )

            self.beam_focusing_hwobj = self.get_hardware_object(new_value)

            if self.beam_focusing_hwobj is not None:
                self.connect(
                    self.beam_focusing_hwobj,
                    "focusingModeChanged",
                    self.focus_mode_changed,
                )
                self.connect(
                    self.beam_focusing_hwobj,
                    "stateChanged",
                    self.beam_state_changed,
                )

                # First, fill the combo box
                self.init_focus_mode_combo()

                # Now get the current focus mode and update it
                mode, beam_size = self.beam_focusing_hwobj.get_active_focus_mode()
                self.focus_mode_changed(mode, beam_size)
        else:
            BaseWidget.property_changed(self, property_name, old_value, new_value)
    
    def init_focus_mode_combo(self):
        self.beam_focusing_combo.blockSignals(True)
        self.beam_focusing_combo.clear()
        modes = self.beam_focusing_hwobj.get_focus_mode_names()
        for mode in modes:
            self.beam_focusing_combo.addItem(mode)
        self.beam_focusing_combo.blockSignals(False)

    def change_focus_mode(self):
        focus_mode_name = str(self.beam_focusing_combo.currentText())
        txt = self.beam_focusing_hwobj.get_focus_mode_message(focus_mode_name)

        if len(txt) > 0:
            confDialog = qt_import.QMessageBox(
                self
            )  # Assign parent to avoid closing issues
            confDialog.setIcon(qt_import.QMessageBox.Warning)
            confDialog.setWindowTitle("Focus mode")
            confDialog.setText(txt)
            confDialog.setStandardButtons(
                qt_import.QMessageBox.Ok | qt_import.QMessageBox.Cancel
            )

            result = confDialog.exec_()  # Use exec_() safely

            if result == qt_import.QMessageBox.Ok:
                self.beam_focusing_combo.setCurrentIndex(-1)
                gevent.spawn(self.beam_focusing_hwobj.set_focus_mode, focus_mode_name)
            else:
                self.beam_focusing_combo.setCurrentIndex(
                    self.beam_focusing_combo.findText(self.active_focus_mode)
                )
        else:
            self.beam_focusing_combo.setCurrentIndex(-1)
            gevent.spawn(self.beam_focusing_hwobj.set_focus_mode, focus_mode_name)

    def beam_state_changed(self, state):
        """Turn the combo yellow while benders are moving, green when ready."""
        if isinstance(state, (list, tuple)):
            state = state[0]
        colors.set_widget_color_by_state(
            self.beam_focusing_combo, state, qt_import.QPalette.Button
        )

    def focus_mode_changed(self, new_focus_mode, beam_size):
        """Updates the focus mode dropdown when the beam size changes."""
        self.active_focus_mode = new_focus_mode
        self.beam_focusing_combo.blockSignals(True)
    
        if self.active_focus_mode is None:
            self.beam_focusing_combo.clear()
            self.setEnabled(False)
            self.beam_focusing_combo.setCurrentIndex(-1)
        else:
            self.init_focus_mode_combo()
            self.setEnabled(True)
            index = self.beam_focusing_combo.findText(self.active_focus_mode)
            self.beam_focusing_combo.setCurrentIndex(index)
    
        self.beam_focusing_combo.blockSignals(False)
    
        logging.debug(f"Focus mode changed: {new_focus_mode}, Beam size: {beam_size}")
    
