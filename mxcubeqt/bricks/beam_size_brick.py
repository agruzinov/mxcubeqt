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
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""
[Name] BeamSizeBrick

[Description]
The Beam size brick displays beam horizontal and vertical sizes.
Sizes are estimated by related HO

[Properties]
-----------------------------------------------------------------------
| name         | type   | description
-----------------------------------------------------------------------
| beamSizeDev  | string | name of the BeamSize Hardware Object
| formatString | string | format string for size display (defaults to #.###)
-----------------------------------------------------------------------

[Signals] -

[Slots] -

[Comments] -

[Hardware Objects]
-----------------------------------------------------------------------
| name		| signals         | functions
-----------------------------------------------------------------------
| BeamSize      | beamSizeChanged |
-----------------------------------------------------------------------
"""



from mxcubeqt.utils import colors, qt_import
from mxcubeqt.base_components import BaseWidget

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObjectState

try:
    unichr
except NameError:
    unichr = chr

__credits__ = ["MXCuBE collaboration"]
__category__ = "Beam definition"

import logging
log = logging.getLogger("HWR")


class BeamSizeBrick(BaseWidget):
    def __init__(self, *args):
        BaseWidget.__init__(self, *args)

        # Hardware objects ----------------------------------------------------

        # Internal values -----------------------------------------------------

        # Properties ----------------------------------------------------------
        self.add_property("formatString", "formatString", "#.#")

        # Signals ------------------------------------------------------------

        # Slots ---------------------------------------------------------------

        # Graphic elements ----------------------------------------------------
        self.main_gbox = qt_import.QGroupBox("Beam size", self)
        hor_label = qt_import.QLabel("Horizontal:", self.main_gbox)
        self.hor_size_ledit = qt_import.QLineEdit(self.main_gbox)
        self.hor_size_ledit.setMaximumWidth(120)
        self.hor_size_ledit.setEnabled(False)
        self.hor_size_ledit.setAlignment(qt_import.Qt.AlignRight)

        ver_label = qt_import.QLabel("Vertical:", self.main_gbox)
        self.ver_size_ledit = qt_import.QLineEdit(self.main_gbox)
        self.ver_size_ledit.setMaximumWidth(120)
        self.ver_size_ledit.setEnabled(False)
        self.ver_size_ledit.setAlignment(qt_import.Qt.AlignRight)

        bold_font = self.hor_size_ledit.font()
        bold_font.setBold(True)
        self.hor_size_ledit.setFont(bold_font)
        self.ver_size_ledit.setFont(bold_font)

        # Layout --------------------------------------------------------------
        _main_gbox_gridlayout = qt_import.QGridLayout(self.main_gbox)
        _main_gbox_gridlayout.addWidget(hor_label, 0, 0)
        _main_gbox_gridlayout.addWidget(self.hor_size_ledit, 0, 1)
        _main_gbox_gridlayout.addWidget(ver_label, 1, 0)
        _main_gbox_gridlayout.addWidget(self.ver_size_ledit, 1, 1)
        _main_gbox_gridlayout.setRowStretch(2, 10)
        _main_gbox_gridlayout.setSpacing(2)
        _main_gbox_gridlayout.setContentsMargins(0, 0, 0, 0)

        _main_vlayout = qt_import.QVBoxLayout(self)
        _main_vlayout.addWidget(self.main_gbox)
        _main_vlayout.setSpacing(0)
        _main_vlayout.setContentsMargins(2, 2, 2, 2)

        # SizePolicies --------------------------------------------------------

        # Qt signal/slot connections ------------------------------------------

        # Other ---------------------------------------------------------------

        self.connect(HWR.beamline.beam, "beamInfoChanged", self.beam_info_changed)
        self.connect(HWR.beamline.beam, "stateChanged", self.beam_info_state_changed)

        log.debug(f"  BEAM INFO connected")
        log.debug(f"     current size is: {HWR.beamline.beam.get_beam_size()}")
        self.beam_info_changed()
        self.beam_info_state_changed()

    def beam_info_changed(self, beam_info=None):
       """Ensures beam size updates correctly after movement stops."""
       if beam_info is None:
           try:
               beam_info = HWR.beamline.beam.get_beam_info_dict()
           except AttributeError:
               log.error("Failed to get beam info from hardware object.")
               return
   
       log.debug(f"Current size: {HWR.beamline.beam.get_beam_size()}")
       log.debug(f"Updated BEAM INFO: {beam_info}")
   
       hor_size = beam_info.get("size_x")
       ver_size = beam_info.get("size_y")
   
       # Check if pinhole or beam is still moving before updating size
       pinhole_hwobj = self.get_hardware_object("pinhole")
       beam_hwobj = self.get_hardware_object("beam")
   
       is_pinhole_moving = pinhole_hwobj.is_moving() if pinhole_hwobj else False
       is_beam_moving = beam_hwobj.get_beam_info_state() == HardwareObjectState.BUSY if beam_hwobj else False
   
       # Only skip update if moving AND we don't have valid data yet
       # If we have valid data (hor_size or ver_size is not None), always update regardless of movement state
       # This ensures the display updates even when state transitions are delayed
       if (is_pinhole_moving or is_beam_moving) and (hor_size is None and ver_size is None):
           log.debug("Beam or pinhole is still moving and no valid data, delaying beam size update.")
           return  # Prevent premature UI updates
       
       # If we have valid data, log that we're updating despite movement state
       if (is_pinhole_moving or is_beam_moving) and (hor_size is not None or ver_size is not None):
           log.debug("Beam or pinhole reported as moving but have valid data, updating display anyway.")
   
       # Ensure formatString is set correctly
       format_str = self.property("formatString")
       if not format_str or not isinstance(format_str, str):
           format_str = "{:.3f}"  # Default to 3 decimal places
   
       try:
           if hor_size is not None:
               hor_size_microns = hor_size * 1000
               size_str = format_str.format(hor_size_microns)
               self.hor_size_ledit.setText(f"{size_str} μm")
               log.debug(f"Set horizontal beam size to: {size_str} μm")
           else:
               self.hor_size_ledit.setText("")
               log.debug("Horizontal beam size is None, cleared display")
   
           if ver_size is not None:
               ver_size_microns = ver_size * 1000
               size_str = format_str.format(ver_size_microns)
               self.ver_size_ledit.setText(f"{size_str} μm")
               log.debug(f"Set vertical beam size to: {size_str} μm")
           else:
               self.ver_size_ledit.setText("")
               log.debug("Vertical beam size is None, cleared display")
   
       except Exception as e:
           log.error(f"Error formatting beam size: {e}", exc_info=True)
   

#    def beam_info_changed(self, beam_info=None):
#        """Ensures beam size updates correctly after movement stops."""
#        if beam_info is None:
#            try:
#                beam_info = HWR.beamline.beam.get_beam_info_dict()
#            except AttributeError:
#                log.error("Failed to get beam info from hardware object.")
#                return
#    
#        log.debug(f"Current size: {HWR.beamline.beam.get_beam_size()}")
#        log.debug(f"Updated BEAM INFO: {beam_info}")
#    
#        hor_size = beam_info.get("size_x")
#        ver_size = beam_info.get("size_y")
#    
#        # Check if pinhole or beam is still moving before updating size
#        pinhole_hwobj = self.get_hardware_object("pinhole")
#        beam_hwobj = self.get_hardware_object("beam")
#    
#        is_pinhole_moving = pinhole_hwobj.is_moving() if pinhole_hwobj else False
#        is_beam_moving = beam_hwobj.get_beam_info_state() ==  HardwareObjectState.BUSY if beam_hwobj else False
#    
#        if is_pinhole_moving or is_beam_moving:
#            log.debug("Beam or pinhole is still moving, delaying beam size update.")
#            return  # Prevent premature UI updates
#    
#        # Ensure formatString is set
#        format_str = self.property("formatString") or "#.###"
#    
#        try:
#            if hor_size is not None:
#                hor_size_microns = hor_size * 1000
#                size_str = format_str % hor_size_microns
#                self.hor_size_ledit.setText(f"{size_str} μm")
#            else:
#                self.hor_size_ledit.setText("")
#    
#            if ver_size is not None:
#                ver_size_microns = ver_size * 1000
#                size_str = format_str % ver_size_microns
#                self.ver_size_ledit.setText(f"{size_str} μm")
#            else:
#                self.ver_size_ledit.setText("")
#    
#        except Exception as e:
#            log.error(f"Error formatting beam size: {e}")



    
    def beam_info_state_changed(self, state=None):
        """Ensure the UI updates when the beam and pinhole are fully ready."""
        if state is None:
            try:
                state = HWR.beamline.beam.get_beam_info_state()
            except AttributeError:
                log.error("Beam hardware object not found.")
                return
    
        # Get the pinhole and beam hardware objects
        pinhole_hwobj = self.get_hardware_object("pinhole")
        beam_hwobj = self.get_hardware_object("beam")
    
        is_pinhole_moving = pinhole_hwobj.is_moving() if pinhole_hwobj else False
        is_beam_moving = state == HardwareObjectState.BUSY
    
        # Update UI state
        if is_beam_moving or is_pinhole_moving:
            log.debug("Beam or Pinhole is moving, setting UI to YELLOW.")
            self._update_color(colors.LIGHT_YELLOW)  # Yellow when moving
        elif state == HardwareObjectState.READY and not is_pinhole_moving:
            log.debug("Beam and Pinhole are READY, setting UI to GREEN.")
            self._update_color(colors.LIGHT_GREEN)  # Green when ready
            self.beam_info_changed()  # Force UI refresh after movement stops
        else:
            # For UNKNOWN/FAULT states, check if we have valid beam data
            # If we have valid data, keep it green; only set gray if no data
            try:
                beam_info = HWR.beamline.beam.get_beam_info_dict()
                hor_size = beam_info.get("size_x")
                ver_size = beam_info.get("size_y")
                if hor_size is not None or ver_size is not None:
                    # We have valid data, so keep it green
                    log.debug("Unknown/FAULT state but have valid beam data, keeping UI GREEN.")
                    self._update_color(colors.LIGHT_GREEN)
                    self.beam_info_changed()
                else:
                    # No valid data, set to gray
                    log.debug("Unknown/FAULT state and no valid beam data, setting UI to GRAY.")
                    self._update_color(colors.LIGHT_GRAY)
                    self.beam_info_changed()
            except (AttributeError, Exception) as e:
                log.debug(f"Unknown/FAULT state and cannot get beam data: {e}, setting UI to GRAY.")
                self._update_color(colors.LIGHT_GRAY)
                self.beam_info_changed()
    














#def beam_info_state_changed(self, state=None):
#
#
#
#        """Ensure UI updates as soon as beam and pinhole are fully ready."""
#        if state is None:
#            try:
#                state = HWR.beamline.beam.get_beam_info_state()
#            except AttributeError:
#                return
#    
#        # Get the pinhole and beam hardware objects
#        pinhole_hwobj = self.get_hardware_object("pinhole")
#        beam_hwobj = self.get_hardware_object("beam")
#    
#        is_pinhole_moving = pinhole_hwobj.is_moving() if pinhole_hwobj else False
#        is_beam_moving = state == HardwareObjectState.BUSY
#    
#        # Update UI state
#        if is_beam_moving or is_pinhole_moving:
#            log.debug("Beam or Pinhole is moving, setting UI to YELLOW.")
#            self._update_color(colors.LIGHT_YELLOW)  # Yellow when moving
#        elif state == HardwareObjectState.READY and not is_pinhole_moving:
#            log.debug("Beam and Pinhole are READY, updating UI immediately.")
#            self._update_color(colors.LIGHT_GREEN)  # Green when ready
#            self.beam_info_changed()  # Force immediate UI refresh
#        else:
#            log.debug("Unknown state, delaying gray update.")
#            time.sleep(0.5)  # Small delay to prevent flickering
#            self._update_color(colors.LIGHT_GRAY)  # Default unknown state
#    

#    def beam_info_changed(self, beam_info=None):
#        """
#        beam size is in mm. It is displayed in microns
#        """
#        if beam_info is None:
#            beam_info = HWR.beamline.beam.get_beam_info_dict()
#
#        log.debug(f"     current size is: {HWR.beamline.beam.get_beam_size()}")
#        log.debug(f"  BEAM INFO updated on beam_info brick: {beam_info}")
#        hor_size = beam_info.get("size_x", None)
#        ver_size = beam_info.get("size_y", None)
#
#        if hor_size is None:
#            self.hor_size_ledit.setText("")
#        else:
#            size_str = self["formatString"] % (hor_size * 1000)
#            self.hor_size_ledit.setText("%s %sm" % (size_str, unichr(956)))
#        if ver_size is None:
#            self.ver_size_ledit.setText("")
#        else:
#            # ver_size *= 1000
#            size_str = self["formatString"] % (ver_size * 1000)
#            self.ver_size_ledit.setText("%s %sm" % (size_str, unichr(956)))
# 
#    def beam_info_state_changed(self, state=None):
#        if state is None:
#            try:
#                state = HWR.beamline.beam.get_beam_info_state()
#            except AttributeError:
#                return
#
#        self._update_color(colors.COLOR_STATES[state])

    def _update_color(self, color):
        colors.set_widget_color(self.ver_size_ledit, color, qt_import.QPalette.Base)
        colors.set_widget_color(self.hor_size_ledit, color, qt_import.QPalette.Base)
