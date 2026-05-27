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

import logging
from os.path import expanduser

from mxcubeqt.base_components import BaseWidget
from mxcubeqt.utils import colors, icons, qt_import

from mxcubecore import HardwareRepository as HWR


__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class SampleControlBrick(BaseWidget):
    """
    Sample control is used to perform sample centring
    """

    def __init__(self, *args):
        BaseWidget.__init__(self, *args)

        # Internal values -----------------------------------------------------
        self.inside_data_collection = None
        self.prefix = "snapshot"
        self.file_index = 1

        # Properties ----------------------------------------------------------
        self.add_property("enableAutoFocus", "boolean", True)
        self.add_property("enableRefreshCamera", "boolean", False)
        self.add_property("enableVisualAlign", "boolean", True)
        self.add_property("enableAutoCenter", "boolean", True)
        self.add_property("enableRealignBeam", "boolean", False)

        # Signals -------------------------------------------------------------

        # Slots ---------------------------------------------------------------

        # Graphic elements ----------------------------------------------------
        self.centre_button = DuoStateButton(self, "Centre")
        self.centre_button.set_icons("VCRPlay2", "Delete")
        self.accept_button = MonoStateButton(self, "Save", "ThumbUp")
        self.standard_color = self.accept_button.palette().color(
            qt_import.QPalette.Window
        )
        self.reject_button = MonoStateButton(self, "Reject", "ThumbDown")
        self.reject_button.hide()
        self.create_line_button = MonoStateButton(self, "Line", "Line")
        self.draw_grid_button = MonoStateButton(self, "Grid", "Grid")
        self.auto_focus_button = MonoStateButton(self, "Focus", "Eyeball")
        self.snapshot_button = MonoStateButton(self, "Snapshot", "Camera")
        self.refresh_camera_button = MonoStateButton(
            self, "Refresh", "Refresh")
        self.visual_align_button = MonoStateButton(self, "Align", "Align")
        self.select_all_button = MonoStateButton(self, "Select all", "Check")
        self.clear_all_button = MonoStateButton(self, "Clear all", "Delete")
        self.auto_center_button = MonoStateButton(self, "Auto", "VCRPlay2")
        self.auto_center_button.setText("Auto")
        self.realign_button = MonoStateButton(
            self, "Realign beam", "QuickRealign")

        # Layout --------------------------------------------------------------
        _main_vlayout = qt_import.QVBoxLayout(self)
        _main_vlayout.addWidget(self.centre_button)
        _main_vlayout.addWidget(self.accept_button)
        _main_vlayout.addWidget(self.reject_button)
        _main_vlayout.addWidget(self.create_line_button)
        _main_vlayout.addWidget(self.draw_grid_button)
        _main_vlayout.addWidget(self.auto_focus_button)
        _main_vlayout.addWidget(self.snapshot_button)
        _main_vlayout.addWidget(self.refresh_camera_button)
        _main_vlayout.addWidget(self.visual_align_button)
        _main_vlayout.addWidget(self.select_all_button)
        _main_vlayout.addWidget(self.clear_all_button)
        _main_vlayout.addWidget(self.auto_center_button)
        _main_vlayout.addWidget(self.realign_button)
        _main_vlayout.addStretch(0)
        _main_vlayout.setSpacing(0)
        _main_vlayout.setContentsMargins(0, 0, 0, 0)

        # Qt signal/slot connections ------------------------------------------
        self.centre_button.commandExecuteSignal.connect(
            self.centre_button_clicked)
        self.accept_button.clicked.connect(self.accept_clicked)
        self.reject_button.clicked.connect(self.reject_clicked)
        self.create_line_button.clicked.connect(create_line_clicked)
        self.draw_grid_button.clicked.connect(draw_grid_clicked)
        self.auto_focus_button.clicked.connect(auto_focus_clicked)
        self.snapshot_button.clicked.connect(self.save_snapshot_clicked)
        self.refresh_camera_button.clicked.connect(refresh_camera_clicked)
        self.visual_align_button.clicked.connect(visual_align_clicked)
        self.select_all_button.clicked.connect(select_all_clicked)
        self.clear_all_button.clicked.connect(clear_all_clicked)
        self.auto_center_button.clicked.connect(auto_center_clicked)

        # Other ---------------------------------------------------------------
        self.centre_button.setToolTip("3 click centring")
        self.accept_button.setToolTip(
            "Accept 3 click centring or "
            "create a point\nbased on current position"
        )
        self.reject_button.setToolTip("Reject centring")
        self.create_line_button.setToolTip(
            "Create helical line between two points"
        )
        self.draw_grid_button.setToolTip("Create grid with drag and drop")
        self.select_all_button.setToolTip("Select all centring points")
        self.clear_all_button.setToolTip("Clear all items")
        # self.instanceSynchronize("")

        self.connect(HWR.beamline.sample_view,
                     "centringStarted", self.centring_started)
        self.connect(HWR.beamline.sample_view,
                     "centringFailed", self.centring_failed)
        self.connect(
            HWR.beamline.sample_view, "centringSuccessful", self.centring_successful
        )
        self.connect(
            HWR.beamline.sample_view,
            "diffractometerPhaseChanged",
            self.diffractometer_phase_changed,
        )

    def property_changed(self, property_name, old_value, new_value):
        if property_name == "enableAutoFocus":
            self.auto_focus_button.setVisible(new_value)
        elif property_name == "enableRefreshCamera":
            self.refresh_camera_button.setVisible(new_value)
        elif property_name == "enableVisualAlign":
            self.visual_align_button.setVisible(new_value)
        elif property_name == "enableAutoCenter":
            self.auto_center_button.setVisible(new_value)
        elif property_name == "enableRealignBeam":
            self.realign_button.setVisible(new_value)
        else:
            BaseWidget.property_changed(
                self, property_name, old_value, new_value)

    def centre_button_clicked(self, state):
        if state:
            HWR.beamline.sample_view.start_centring(tree_click=True)
        else:
            HWR.beamline.sample_view.cancel_centring(reject=False)
            self.accept_button.setEnabled(True)

    def save_snapshot_clicked(self):
        logging.getLogger().info("Saving snapshot...")

        # Add safety check to prevent multiple simultaneous operations
        if hasattr(self, '_snapshot_in_progress') and self._snapshot_in_progress:
            logging.getLogger().warning("Snapshot already in progress, ignoring request")
            return

        self._snapshot_in_progress = True

        try:
            # Check for writable directories in order of preference
            import os
            possible_dirs = [
                "/gpfs/current/processed",
                "/gpfs/local/shared",
                expanduser("~"),
                "/tmp"
            ]

            save_dir = None
            for directory in possible_dirs:
                if os.path.exists(directory) and os.access(directory, os.W_OK):
                    save_dir = directory
                    logging.getLogger().info("Using writable directory: %s", save_dir)
                    break
                else:
                    logging.getLogger().info("Directory not writable or doesn't exist: %s", directory)

            if save_dir is None:
                logging.getLogger().error("No writable directory found!")
                return

            # Create manual_snapshots subdirectory
            manual_snapshots_dir = os.path.join(save_dir, "manual_snapshots")
            try:
                if not os.path.exists(manual_snapshots_dir):
                    os.makedirs(manual_snapshots_dir, exist_ok=True)
                    logging.getLogger().info("Created manual_snapshots directory: %s", manual_snapshots_dir)
                else:
                    logging.getLogger().info(
                        "Using existing manual_snapshots directory: %s", manual_snapshots_dir)
            except Exception as e:
                logging.getLogger().error("Failed to create manual_snapshots directory: %s", str(e))
                # Fallback to parent directory
                manual_snapshots_dir = save_dir
                logging.getLogger().info("Falling back to parent directory: %s", manual_snapshots_dir)

            # Generate filename with timestamp to avoid conflicts
            import time
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            current_file_name = "%s/%s_%s.png" % (
                manual_snapshots_dir,
                self.prefix,
                timestamp
            )

            logging.getLogger().info("Saving snapshot to: %s", current_file_name)

            # Try to save the snapshot directly
            try:
                HWR.beamline.sample_view.save_scene_snapshot(current_file_name)
                logging.getLogger().info("Snapshot saved successfully to: %s", current_file_name)

                # Also save raw camera frames from overview (zoom0) and zoom (zoom1)
                try:
                    camera = HWR.beamline.sample_view.camera
                    if hasattr(camera, 'save_raw_snapshot'):
                        overview_file = "%s/%s_%s_zoom0.png" % (
                            manual_snapshots_dir, self.prefix, timestamp)
                        zoom_file = "%s/%s_%s_zoom1.png" % (
                            manual_snapshots_dir, self.prefix, timestamp)
                        camera.save_raw_snapshot(overview_file, use_overview=True)
                        camera.save_raw_snapshot(zoom_file, use_overview=False)
                except Exception as cam_err:
                    logging.getLogger().warning(
                        "Could not save raw camera frames: %s", str(cam_err))

                # Show a simple success message (with safety measures)
                try:
                    # Create message box as instance variable to prevent double deletion
                    if not hasattr(self, '_msg_box'):
                        self._msg_box = None

                    if self._msg_box is not None:
                        self._msg_box.close()
                        self._msg_box = None

                    self._msg_box = qt_import.QMessageBox(self)
                    self._msg_box.setWindowTitle("Snapshot Saved")
                    self._msg_box.setText(
                        f"Snapshot saved to:\n{current_file_name}")
                    self._msg_box.setIcon(qt_import.QMessageBox.Information)
                    self._msg_box.setStandardButtons(qt_import.QMessageBox.Ok)
                    self._msg_box.show()

                    # Auto-close after 3 seconds to prevent memory issues
                    qt_import.QTimer.singleShot(
                        3000, lambda: self._msg_box.close() if self._msg_box else None)

                except Exception as msg_error:
                    logging.getLogger().warning("Could not show success message: %s", str(msg_error))

            except BaseException as e:
                logging.getLogger().exception("Error saving snapshot: %s", str(e))
                # Show error message
                try:
                    qt_import.QMessageBox.critical(
                        self,
                        "Save Error",
                        f"Failed to save snapshot:\n{str(e)}"
                    )
                except Exception as msg_error:
                    logging.getLogger().warning("Could not show error message: %s", str(msg_error))

        except BaseException as e:
            logging.getLogger().exception("Error in snapshot operation: %s", str(e))
        finally:
            # Always reset the flag
            self._snapshot_in_progress = False
            logging.getLogger().info("Snapshot operation completed, flag reset")

    def accept_clicked(self):
        colors.set_widget_color(self.accept_button, self.standard_color)
        self.reject_button.setEnabled(False)
        HWR.beamline.sample_view.accept_centring()

        if (
            HWR.beamline.queue_manager.is_executing()
            and HWR.beamline.queue_manager.is_paused()
        ):
            HWR.beamline.queue_manager.set_pause(False)

    def reject_clicked(self):
        colors.set_widget_color(self.accept_button, self.standard_color)
        self.reject_button.setEnabled(False)
        self.centre_button.setEnabled(True)
        self.accept_button.setEnabled(True)
        HWR.beamline.sample_view.reject_centring()

    def centring_snapshots(self, state):
        if state is None:
            self.setEnabled(False)
        else:
            self.setEnabled(True)

    def centring_started(self):
        self.setEnabled(True)
        self.centre_button.command_started()
        self.accept_button.setEnabled(False)
        self.reject_button.setEnabled(True)

    def centring_successful(self, method, centring_status):
        self.centre_button.command_done()
        self.accept_button.setEnabled(True)
        self.reject_button.setEnabled(True)
        if self.inside_data_collection:
            colors.set_widget_color(self.accept_button, colors.LIGHT_GREEN)
            colors.set_widget_color(self.reject_button, colors.LIGHT_RED)

        self.setEnabled(True)

    def centring_failed(self, method, centring_status):
        self.centre_button.command_failed()
        self.accept_button.setEnabled(True)
        if self.inside_data_collection:
            colors.set_widget_color(self.accept_button, self.standard_color)
            self.reject_button.setEnabled(True)
            colors.set_widget_color(self.reject_button, qt_import.Qt.red)
        else:
            self.reject_button.setEnabled(False)

    def diffractometer_ready_changed(self, is_ready):
        self.setEnabled(is_ready)

    def diffractometer_phase_changed(self, phase):
        # TODO connect this to minidiff
        status = phase != "BeamLocation"
        self.centre_button.setEnabled(status)
        self.accept_button.setEnabled(status)
        self.reject_button.setEnabled(status)
        self.create_line_button.setEnabled(status)
        self.draw_grid_button.setEnabled(status)
        self.auto_focus_button.setEnabled(status)
        self.refresh_camera_button.setEnabled(status)
        self.visual_align_button.setEnabled(status)
        self.select_all_button.setEnabled(status)
        self.clear_all_button.setEnabled(status)
        self.auto_center_button.setEnabled(status)


def refresh_camera_clicked():
    HWR.beamline.sample_view.refresh_camera()


def visual_align_clicked():
    HWR.beamline.sample_view.start_visual_align()


def select_all_clicked():
    HWR.beamline.sample_view.select_all_points()


def clear_all_clicked():
    """
    Clears all shapes (points, lines and meshes)
    """
    HWR.beamline.sample_view.clear_all_shapes()


def auto_focus_clicked():
    HWR.beamline.sample_view.auto_focus()


def auto_center_clicked():
    HWR.beamline.sample_view.start_auto_centring()


def create_line_clicked():
    HWR.beamline.sample_view.create_line()


def draw_grid_clicked():
    HWR.beamline.sample_view.create_grid()


class MonoStateButton(qt_import.QToolButton):
    def __init__(self, parent, caption=None, icon=None):

        qt_import.QToolButton.__init__(self, parent)
        self.setSizePolicy(qt_import.QSizePolicy.Expanding,
                           qt_import.QSizePolicy.Fixed)
        self.setToolButtonStyle(qt_import.Qt.ToolButtonTextUnderIcon)
        if caption:
            self.setText(caption)
            self.setWindowIconText(caption)
        if icon:
            self.setIcon(icons.load_icon(icon))


class DuoStateButton(qt_import.QToolButton):

    commandExecuteSignal = qt_import.pyqtSignal(bool)

    def __init__(self, parent, caption):
        qt_import.QToolButton.__init__(self, parent)

        self.setToolButtonStyle(qt_import.Qt.ToolButtonTextUnderIcon)
        self.executing = False
        self.run_icon = None
        self.stop_icon = None
        self.standard_color = self.palette().color(qt_import.QPalette.Window)
        self.setText(caption)
        self.setSizePolicy(qt_import.QSizePolicy.Expanding,
                           qt_import.QSizePolicy.Fixed)
        self.clicked.connect(self.button_clicked)

    def set_icons(self, icon_run, icon_stop):
        self.run_icon = icons.load_icon(icon_run)
        self.stop_icon = icons.load_icon(icon_stop)
        if self.executing:
            self.setIcon(self.stop_icon)
        else:
            self.setIcon(self.run_icon)

    def button_clicked(self):
        self.commandExecuteSignal.emit(not self.executing)
        # if not self.executing:
        #    self.setEnabled(False)

    def command_started(self):
        colors.set_widget_color(self, colors.LIGHT_YELLOW,
                                qt_import.QPalette.Button)
        if self.stop_icon is not None:
            self.setIcon(self.stop_icon)
        self.executing = True
        self.setEnabled(True)

    def is_executing(self):
        return self.executing

    def command_done(self):
        self.executing = False
        colors.set_widget_color(self, self.standard_color,
                                qt_import.QPalette.Button)
        if self.run_icon is not None:
            self.setIcon(self.run_icon)
        self.setEnabled(True)

    def command_failed(self):
        self.command_done()

