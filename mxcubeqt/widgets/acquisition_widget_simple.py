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
#  GNU Leeser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

from mxcubeqt.utils import qt_import
from mxcubeqt.utils.widget_utils import DataModelInputBinder
from mxcubecore.model import queue_model_objects

from mxcubecore import HardwareRepository as HWR


__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"


class AcquisitionWidgetSimple(qt_import.QWidget):

    acqParametersChangedSignal = qt_import.pyqtSignal(list)
    madEnergySelectedSignal = qt_import.pyqtSignal(str, float, bool)

    def __init__(
        self,
        parent=None,
        name=None,
        fl=0,
        acq_params=None,
        path_template=None,
        layout=None,
    ):

        qt_import.QWidget.__init__(self, parent, qt_import.Qt.WindowFlags(fl))
        if name is not None:
            self.setObjectName(name)

        # Internal variables --------------------------------------------------
        self.value_changed_list = []

        # Properties ----------------------------------------------------------

        # Signals -------------------------------------------------------------

        # Slots ---------------------------------------------------------------

        # Graphic elements ----------------------------------------------------
        if acq_params is None:
            self._acquisition_parameters = queue_model_objects.AcquisitionParameters()
        else:
            self._acquisition_parameters = acq_params
        if path_template is None:
            self._path_template = queue_model_objects.PathTemplate()
        else:
            self._path_template = path_template

        self._acquisition_mib = DataModelInputBinder(self._acquisition_parameters)
        self.acq_widget_layout = qt_import.load_ui_file(
            "acquisition_widget_vertical_simple_layout.ui"
        )

        # Layout --------------------------------------------------------------
        main_layout = qt_import.QVBoxLayout(self)
        main_layout.addWidget(self.acq_widget_layout)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # SizePolicies --------------------------------------------------------

        # Qt signal/slot connections ------------------------------------------
        self.acq_widget_layout.osc_start_cbox.stateChanged.connect(self.use_osc_start)
        self.acq_widget_layout.num_images_cbox.activated.connect(self.update_num_images)
        self.acq_widget_layout.detector_roi_mode_combo.activated.connect(
            self.detector_roi_mode_changed
        )

        # Other ---------------------------------------------------------------
        self.osc_start_validator = qt_import.QDoubleValidator(
            -10000, 10000, 4, self.acq_widget_layout.osc_start_ledit
        )
        self.osc_range_validator = qt_import.QDoubleValidator(
            -10000, 10000, 4, self.acq_widget_layout.osc_range_ledit
        )
        self.kappa_validator = qt_import.QDoubleValidator(
            0, 360, 4, self.acq_widget_layout.kappa_ledit
        )
        self.kappa_phi_validator = qt_import.QDoubleValidator(
            0, 360, 4, self.acq_widget_layout.kappa_phi_ledit
        )
        self.energy_validator = qt_import.QDoubleValidator(
            0, 25, 5, self.acq_widget_layout.energy_ledit
        )
        self.resolution_validator = qt_import.QDoubleValidator(
            0, 15, 3, self.acq_widget_layout.resolution_ledit
        )
        self.transmission_validator = qt_import.QDoubleValidator(
            0, 100, 3, self.acq_widget_layout.transmission_ledit
        )
        self.exp_time_validator = qt_import.QDoubleValidator(
            0, 10000, 6, self.acq_widget_layout.exp_time_ledit
        )
        self.acq_widget_layout.num_images_cbox.setCurrentIndex(1)

        self.acq_widget_layout.detector_roi_mode_label.setEnabled(False)
        self.acq_widget_layout.detector_roi_mode_combo.setEnabled(False)

        self.set_tunable_energy(HWR.beamline.tunable_wavelength)

        if HWR.beamline.diffractometer.in_plate_mode():
            self.acq_widget_layout.num_images_cbox.clear()
            self.acq_widget_layout.num_images_cbox.addItem("1")
            self.acq_widget_layout.num_images_cbox.setCurrentIndex(0)

        self.init_detector_roi_modes()
        self.init_limits()

    def update_osc_total_range(self):
        pass

    def set_osc_start_limits(self, limits):
        if not None in limits:
            self.osc_start_validator.setRange(limits[0], limits[1], 4)

    def update_osc_start(self, new_value):
        if not self.acq_widget_layout.osc_start_cbox.hasFocus():
            self.acq_widget_layout.osc_start_ledit.setText(str(new_value))

    def update_kappa(self, new_value):
        if not self.acq_widget_layout.kappa_ledit.hasFocus():
            self.acq_widget_layout.kappa_ledit.setText(str(new_value))

    def update_kappa_phi(self, new_value):
        if not self.acq_widget_layout.kappa_phi_ledit.hasFocus():
            self.acq_widget_layout.kappa_phi_ledit.setText(str(new_value))

    def use_kappa(self, state):
        if HWR.beamline.diffractometer.in_plate_mode():
            state = False
        self.acq_widget_layout.kappa_label.setEnabled(state)
        self.acq_widget_layout.kappa_ledit.setEnabled(state)
        self.acq_widget_layout.kappa_phi_label.setEnabled(state)
        self.acq_widget_layout.kappa_phi_ledit.setEnabled(state)

    def use_max_osc_range(self, state):
        pass

    def update_num_images(self, index=None, num_images=None):
        if index is not None:
            if index == 0:
                self._acquisition_parameters.num_images = 1
                self._path_template.num_files = 1
            elif index == 1:
                self._acquisition_parameters.num_images = 2
                self._path_template.num_files = 2
            elif index == 2:
                self._acquisition_parameters.num_images = 4
                self._path_template.num_files = 4

        if num_images:
            if self.acq_widget_layout.num_images_cbox.count() > 3:
                self.acq_widget_layout.num_images_cbox.removeItem(4)

            if num_images == 1:
                self.acq_widget_layout.num_images_cbox.setCurrentIndex(0)
            elif num_images == 2:
                self.acq_widget_layout.num_images_cbox.setCurrentIndex(1)
            elif num_images == 4:
                self.acq_widget_layout.num_images_cbox.setCurrentIndex(2)
            else:
                self.acq_widget_layout.num_images_cbox.addItem(str(num_images))
                self.acq_widget_layout.num_images_cbox.setCurrenIndex(3)

            self._path_template.num_files = num_images

    def use_mad(self, state):
        pass

    def get_mad_energy(self):
        pass

    def set_energies(self, energy_scan_result):
        pass

    def energy_selected(self, index):
        pass

    def init_limits(self):
        limits_dict = HWR.beamline.acquisition_limit_values

        tpl = limits_dict.get("osc_range")
        if tpl:
            self.osc_start_validator.setRange(tpl[0], tpl[1], 4)
            self.osc_range_validator.setRange(tpl[0], tpl[1], 4)

        self._acquisition_mib.bind_value_update(
            "osc_start",
            self.acq_widget_layout.osc_start_ledit,
            float,
            self.osc_start_validator,
        )

        self._acquisition_mib.bind_value_update(
            "osc_range",
            self.acq_widget_layout.osc_range_ledit,
            float,
            self.osc_range_validator,
        )

        tpl = limits_dict.get("kappa")
        if tpl:
            self.kappa_validator.setRange(tpl[0], tpl[1], 4)
        self._acquisition_mib.bind_value_update(
            "kappa", self.acq_widget_layout.kappa_ledit, float, self.kappa_validator
        )

        tpl = limits_dict.get("kappa_phi")
        if tpl:
            self.kappa_phi_validator.setRange(tpl[0], tpl[1], 4)
        self._acquisition_mib.bind_value_update(
            "kappa_phi",
            self.acq_widget_layout.kappa_phi_ledit,
            float,
            self.kappa_phi_validator,
        )

        tpl = limits_dict.get("exposure_time")
        if tpl:
            self.exp_time_validator.setRange(tpl[0], tpl[1], 6)
        self._acquisition_mib.bind_value_update(
            "exp_time",
            self.acq_widget_layout.exp_time_ledit,
            float,
            self.exp_time_validator,
        )

        self._acquisition_mib.bind_value_update(
            "energy", self.acq_widget_layout.energy_ledit, float, self.energy_validator
        )
        self.acq_widget_layout.energy_ledit.setToolTip(
            "Energy limits %0.3f : %0.3f"
            % (self.energy_validator.bottom(), self.energy_validator.top())
        )

        self._acquisition_mib.bind_value_update(
            "transmission",
            self.acq_widget_layout.transmission_ledit,
            float,
            self.transmission_validator,
        )

        self._acquisition_mib.bind_value_update(
            "resolution",
            self.acq_widget_layout.resolution_ledit,
            float,
            self.resolution_validator,
        )

        if HWR.beamline.diffractometer.in_plate_mode():
            self.acq_widget_layout.num_images_cbox.clear()
            self.acq_widget_layout.num_images_cbox.addItem("1")
            self.acq_widget_layout.num_images_cbox.setCurrentIndex(0)

    def set_energy(self, energy, wav):
        if not self.acq_widget_layout.energy_ledit.hasFocus():
            self.acq_widget_layout.energy_ledit.setText(str(energy))

    def update_transmission(self, transmission):
        if self.acq_widget_layout.transmission_ledit.hasFocus():
            self.acq_widget_layout.transmission_ledit.setText(str(transmission))

    def update_resolution(self, resolution):
        if not self.acq_widget_layout.resolution_ledit.hasFocus():
            self.acq_widget_layout.resolution_ledit.setText(str(resolution))

    def update_energy_limits(self, limits):
        if limits:
            self.energy_validator.setBottom(limits[0])
            self.energy_validator.setTop(limits[1])
            self.acq_widget_layout.energy_ledit.setToolTip(
                "Energy limits %0.3f : %0.3f" % (limits[0], limits[1])
            )
            self._acquisition_mib.validate_all()

    def update_transmission_limits(self, limits):
        if limits:
            self.transmission_validator.setBottom(limits[0])
            self.transmission_validator.setTop(limits[1])
            self.acq_widget_layout.transmission_ledit.setToolTip(
                "Transmission limits %0.3f : %0.3f" % (limits[0], limits[1])
            )
            self._acquisition_mib.validate_all()

    def update_resolution_limits(self, limits):
        if limits:
            self.resolution_validator.setBottom(limits[0])
            self.resolution_validator.setTop(limits[1])
            self.acq_widget_layout.resolution_ledit.setToolTip(
                "Resolution limits %0.3f : %0.3f" % (limits[0], limits[1])
            )
            self._acquisition_mib.validate_all()

    def update_detector_exp_time_limits(self, limits):
        if limits:
            self.exp_time_validator.setBottom(limits[0])
            self.exp_time_validator.setTop(limits[1])
            self.acq_widget_layout.exp_time_ledit.setToolTip(
                "Exposure time limits %0.3f : %0.3f" % (limits[0], limits[1])
            )
            self._acquisition_mib.validate_all()

    def update_energy(self, energy):
        if (
            "energy" not in self.value_changed_list
            and not self.acq_widget_layout.energy_ledit.hasFocus()
        ):
            self.acq_widget_layout.energy_ledit.setText("%.4f" % float(energy))

    def init_detector_roi_modes(self):
        roi_modes = HWR.beamline.detector.get_roi_modes()
        if (
            len(roi_modes) > 0
            and self.acq_widget_layout.detector_roi_mode_combo.count() == 0
        ):
            for roi_mode in roi_modes:
                self.acq_widget_layout.detector_roi_mode_combo.addItem(roi_mode)
            self.acq_widget_layout.detector_roi_mode_label.setEnabled(True)
            self.acq_widget_layout.detector_roi_mode_combo.setEnabled(True)

    def update_exp_time_limits(self):
        try:
            exp_time_limits = (
                HWR.beamline.detector.get_exposure_time_limits()
            )
            max_osc_speed = HWR.beamline.diffractometer.get_osc_max_speed()
            top_limit = (
                float(self.acq_widget_layout.osc_range_ledit.text()) / max_osc_speed
            )
            limits = (max(exp_time_limits[0], top_limit), exp_time_limits[1])
            self.update_detector_exp_time_limits(limits)
        except BaseException:
            pass

    def update_detector_roi_mode(self, roi_mode_index):
        if (
            roi_mode_index is not None
            and self.acq_widget_layout.detector_roi_mode_combo.count() > 0
        ):
            self.acq_widget_layout.detector_roi_mode_combo.setCurrentIndex(
                roi_mode_index
            )

    def update_osc_range_limits(self, limits=None):
        pass

    def detector_roi_mode_changed(self, roi_mode_index):
        HWR.beamline.detector.set_roi_mode(roi_mode_index)

    def update_data_model(self, acquisition_parameters, path_template):
        self._acquisition_parameters = acquisition_parameters
        self._acquisition_mib.set_model(acquisition_parameters)
        self._path_template = path_template
        self.update_num_images(None, acquisition_parameters.num_images)

    def set_tunable_energy(self, state):
        self.acq_widget_layout.energy_ledit.setEnabled(state)

    def use_osc_start(self, state):
        self.acq_widget_layout.osc_start_ledit.setEnabled(state)

    def check_parameter_conflict(self):
        return self._acquisition_mib.validate_all()
