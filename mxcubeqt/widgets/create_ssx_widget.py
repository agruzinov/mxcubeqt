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

"""CreateSsxWidget allows to create a ssx acquisition method"""

import copy

from mxcubeqt.utils import queue_item, qt_import
from mxcubeqt.widgets.create_task_base import CreateTaskBase
from mxcubeqt.widgets.acquisition_ssx_widget import AcquisitionSsxWidget
from mxcubeqt.widgets.data_path_widget import DataPathWidget
from mxcubeqt.widgets.ssx_sequence_widget import SSXSequenceWidget
from mxcubeqt.widgets.processing_widget import ProcessingWidget


from mxcubecore.model import (
    queue_model_objects,
    queue_model_enumerables,
)

from mxcubecore import HardwareRepository as HWR


__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"


class CreateSsxWidget(CreateTaskBase):
    def __init__(self, parent=None, name=None, flags=0):

        CreateTaskBase.__init__(
            self, parent, name, qt_import.Qt.WindowFlags(flags), "SSX"
        )

        if not name:
            self.setObjectName("create_ssx_widget")

        # Hardware objects ----------------------------------------------------

        # Internal variables --------------------------------------------------
        self.init_models()

        # Graphic elements ----------------------------------------------------
        self._acq_widget = AcquisitionSsxWidget(
            self,
            "acquisition_widget",
            layout="vertical",
            acq_params=self._acquisition_parameters,
            path_template=self._path_template,
        )

        self._data_path_widget = DataPathWidget(
            self,
            "create_dc_path_widget",
            data_model=self._path_template,
            layout="vertical",
        )

        self._col_seq_widget = SSXSequenceWidget(self)

        self._processing_widget = ProcessingWidget(
            self, data_model=self._processing_parameters
        )

        #self._comment_widget = CommentWidget(self)

        # Layout --------------------------------------------------------------
        _main_vlayout = qt_import.QVBoxLayout(self)
        _main_vlayout.addWidget(self._acq_widget)
        _main_vlayout.addWidget(self._data_path_widget)
        _main_vlayout.addWidget(self._col_seq_widget)
        _main_vlayout.addWidget(self._processing_widget)
        #_main_vlayout.addWidget(self._comment_widget)
        _main_vlayout.addStretch(0)
        _main_vlayout.setSpacing(6)
        _main_vlayout.setContentsMargins(2, 2, 2, 2)

        # SizePolicies --------------------------------------------------------

        # Qt signal/slot connections ------------------------------------------
        self._acq_widget.acqParametersChangedSignal.connect(
            self.acq_parameters_changed
        )
        self._data_path_widget.pathTemplateChangedSignal.connect(
            self.path_template_changed
        )
        self._processing_widget.enableProcessingSignal.connect(
            self._run_processing_toggled
        )

        # Other ---------------------------------------------------------------
        self._processing_widget.processing_widget.run_online_processing_cbox.setChecked(
            HWR.beamline.run_online_processing
        )

        #Rename to self._processing_widget.layout
        self._processing_widget.processing_widget.resolution_cutoff_label.setHidden(False)
        self._processing_widget.processing_widget.resolution_cutoff_ledit.setHidden(False)
        self._processing_widget.processing_widget.pdb_file_label.setHidden(False)
        self._processing_widget.processing_widget.pdb_file_ledit.setHidden(False)
        self._processing_widget.processing_widget.pdb_file_browse_button.setHidden(False)

    def use_osc_start(self, status):
        """
        Enables osc start QLineEdit
        :param status: boolean
        :return:
        """
        return

    def update_exp_time_limits(self):
        """
        Updates exposure time limits
        :return:
        """
        return

    def init_models(self):
        """
        Inits data model
        :return: None
        """
        CreateTaskBase.init_models(self)
        self._processing_parameters = queue_model_objects.ProcessingParameters()

        has_shutter_less = HWR.beamline.detector.has_shutterless()
        self._acquisition_parameters.shutterless = has_shutter_less

        self._acquisition_parameters = (
            HWR.beamline.get_default_acquisition_parameters()
        )
        self._acquisition_parameters.num_triggers = 1
        self._acquisition_parameters.num_images_per_trigger = 1

    def set_tunable_energy(self, state):
        """
        Sets tunable energy
        :param state: boolean
        :return: None
        """
        self._acq_widget.set_tunable_energy(state)

    def single_item_selection(self, tree_item):
        """
        Method called when a queue item in the tree is selected
        :param tree_item: queue_item
        :return: None
        """
        CreateTaskBase.single_item_selection(self, tree_item)

        if isinstance(tree_item, queue_item.SampleQueueItem):
            sample_model = tree_item.get_model()
            # self._processing_parameters = copy.deepcopy(self._processing_parameters)
            self._processing_parameters = sample_model.processing_parameters
            self._processing_widget.update_data_model(self._processing_parameters)
        elif isinstance(tree_item, queue_item.BasketQueueItem):
            self.setDisabled(False)
        elif isinstance(tree_item, queue_item.DataCollectionQueueItem):
            dc_model = tree_item.get_model()
            self._acq_widget.use_kappa(False)

            if not dc_model.is_helical():
                if dc_model.is_executed():
                    self.setDisabled(True)
                else:
                    self.setDisabled(False)

                sample_data_model = self.get_sample_item(tree_item).get_model()
                energy_scan_result = sample_data_model.crystals[0].energy_scan_result
                self._acq_widget.set_energies(energy_scan_result)

                # self._acq_widget.disable_inverse_beam(True)

                self._path_template = dc_model.get_path_template()
                self._data_path_widget.update_data_model(self._path_template)

                self._acquisition_parameters = dc_model.acquisitions[0].acquisition_parameters
                self._acq_widget.update_data_model(
                    self._acquisition_parameters, self._path_template
                )
                # self.get_acquisition_widget().use_osc_start(True)
                if len(dc_model.acquisitions) == 1:
                    HWR.beamline.sample_view.select_shape_with_cpos(
                        self._acquisition_parameters.centred_position
                    )

                self._processing_parameters = dc_model.processing_parameters
                self._processing_widget.update_data_model(self._processing_parameters)
            else:
                self.setDisabled(True)
        else:
            self.setDisabled(True)

    def _create_task(self, sample, shape, comments=None):
        """
        Creates a new SSX scan task
        :param sample: sample node
        :param shape: centering point
        :return: Acquisition item
        """
        tasks = []

        cpos = queue_model_objects.CentredPosition()
        cpos.snapshot_image = HWR.beamline.sample_view.get_snapshot()

        tasks.extend(self.create_dc(sample, cpos=cpos, comments=comments))
        self._path_template.run_number += 1

        return tasks

    def create_dc(
        self,
        sample,
        run_number=None,
        start_image=None,
        num_images=None,
        osc_start=None,
        sc=None,
        cpos=None,
        inverse_beam=False,
        comments=None
    ):
        """
        Creates a new data collection item
        :param sample: Sample
        :param run_number: int
        :param start_image: int
        :param num_images: int
        :param osc_start: float
        :param sc:
        :param cpos: centered position
        :param inverse_beam: boolean
        :return:
        """
        tasks = []

        # Acquisition for start position
        acq = self._create_acq(sample)

        if run_number:
            acq.path_template.run_number = run_number

        if start_image:
            acq.acquisition_parameters.first_image = start_image
            acq.path_template.start_num = start_image

        if num_images:
            acq.acquisition_parameters.num_images = num_images
            acq.path_template.num_files = num_images

        if osc_start:
            acq.acquisition_parameters.osc_start = osc_start

        if inverse_beam:
            acq.acquisition_parameters.inverse_beam = False

        acq.acquisition_parameters.centred_position = cpos
        if comments:
            acq.acquisition_parameters.comments = comments

        processing_parameters = copy.deepcopy(self._processing_parameters)
        data_collection = queue_model_objects.DataCollection(
            [acq], sample.crystals[0], processing_parameters
        )
        data_collection.set_name(acq.path_template.get_prefix())
        data_collection.set_number(acq.path_template.run_number)
        data_collection.experiment_type = queue_model_enumerables.EXPERIMENT_TYPE.STILL
        run_processing_after, run_online_processing = \
            self._processing_widget.get_processing_state()

        data_collection.run_processing_after = run_processing_after
        if run_online_processing:
            data_collection.run_online_processing = "Still"
        data_collection.set_requires_centring(False)

        tasks.append(data_collection)

        return tasks
