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

from mxcubeqt.base_components import BaseWidget
from mxcubeqt.utils import colors, qt_import
from mxcubecore import HardwareRepository as HWR
import logging
from PyQt5.QtCore import QMetaObject, Qt

STATES = {
    "unknown": colors.GRAY,
    "ready": colors.LIGHT_BLUE,
    "error": colors.LIGHT_RED
}

__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "DESY"


class P11MachineInfoBrick(BaseWidget):
    """Brick to display information about synchrotron and beamline as simple text lines."""

    def __init__(self, *args):
        super().__init__(*args)

        self.current_label_text = qt_import.QLabel(self)
        self.current_label = qt_import.QLabel(self)

        self.message_label_text = qt_import.QLabel(self)
        self.message_label = qt_import.QLabel(self)

        self.lifetime_label_text = qt_import.QLabel(self)
        self.lifetime_label = qt_import.QLabel(self)

        self.energy_label_text = qt_import.QLabel(self)
        self.energy_label = qt_import.QLabel(self)

        # Cryostream labels
        self.cryo_set_temp_label_text = qt_import.QLabel(self)
        self.cryo_set_temp_label = qt_import.QLabel(self)

        self.cryo_sample_temp_label_text = qt_import.QLabel(self)
        self.cryo_sample_temp_label = qt_import.QLabel(self)

        self.cryo_status_label_text = qt_import.QLabel(self)
        self.cryo_status_label = qt_import.QLabel(self)

        # Set default values
        self.current_label_text.setText("Machine current")
        self.current_label.setText("N/A mA")
        self.current_label.setStyleSheet("background-color: #6cb2f8;")
        self.current_label.setAlignment(Qt.AlignCenter)

        self.message_label_text.setText("Machine state")
        self.message_label.setStyleSheet("background-color: #6cb2f8;")
        self.message_label.setText("N/A")
        self.message_label.setAlignment(Qt.AlignCenter)

        self.lifetime_label_text.setText("Lifetime")
        self.lifetime_label.setText("N/A hours")
        self.lifetime_label.setStyleSheet("background-color: #6cb2f8;")
        self.lifetime_label.setAlignment(Qt.AlignCenter)

        self.energy_label_text.setText("Energy")
        self.energy_label.setText("N/A GeV")
        self.energy_label.setStyleSheet("background-color: #6cb2f8;")
        self.energy_label.setAlignment(Qt.AlignCenter)

        # Set cryostream default values
        self.cryo_set_temp_label_text.setText("Cryostream Set Temp")
        self.cryo_set_temp_label.setText("N/A °K")
        self.cryo_set_temp_label.setStyleSheet("background-color: #6cb2f8;")
        self.cryo_set_temp_label.setAlignment(Qt.AlignCenter)

        self.cryo_sample_temp_label_text.setText("Cryostream Sample Temp")
        self.cryo_sample_temp_label.setText("N/A °K")
        self.cryo_sample_temp_label.setStyleSheet("background-color: #6cb2f8;")
        self.cryo_sample_temp_label.setAlignment(Qt.AlignCenter)

        self.cryo_status_label_text.setText("Cryostream Status")
        self.cryo_status_label.setText("N/A")
        self.cryo_status_label.setStyleSheet("background-color: #6cb2f8;")
        self.cryo_status_label.setAlignment(Qt.AlignCenter)

        # Add labels to layout
        self.main_layout = qt_import.QVBoxLayout(self)

        self.main_layout.addWidget(self.current_label_text)
        self.main_layout.addWidget(self.current_label)

        self.main_layout.addWidget(self.message_label_text)
        self.main_layout.addWidget(self.message_label)

        self.main_layout.addWidget(self.lifetime_label_text)
        self.main_layout.addWidget(self.lifetime_label)

        self.main_layout.addWidget(self.energy_label_text)
        self.main_layout.addWidget(self.energy_label)

        # Add cryostream labels to layout
        self.main_layout.addWidget(self.cryo_set_temp_label_text)
        self.main_layout.addWidget(self.cryo_set_temp_label)

        self.main_layout.addWidget(self.cryo_sample_temp_label_text)
        self.main_layout.addWidget(self.cryo_sample_temp_label)

        self.main_layout.addWidget(self.cryo_status_label_text)
        self.main_layout.addWidget(self.cryo_status_label)

    def update_labels_in_ui_thread(self, current_value):
        QMetaObject.invokeMethod(
            self.current_label, "setText", Qt.QueuedConnection, f"{current_value} mA"
        )

    def run(self):
        """Connect the signal from the hardware object."""
        if HWR.beamline.machine_info is not None:
            HWR.beamline.machine_info.valuesChanged.connect(self.set_value)
        else:
            logging.error("Machine info object not available")

    def set_value(self, values_dict):
        """Update the labels in the MachineInfoBrick with machine values."""

        current_value = values_dict.get("current", {}).get("value", "N/A")
        lifetime_value = values_dict.get("lifetime", {}).get("value", "N/A")
        energy_value = values_dict.get("energy", {}).get("value", "N/A")
        message_value = values_dict.get("message", {}).get("value", "N/A")

        # Update the UI labels
        self.current_label.setText(f"{current_value} mA")
        self.lifetime_label.setText(f"{lifetime_value} hours")
        self.energy_label.setText(f"{energy_value} GeV")
        self.message_label.setText(f"{message_value}")

        # Update cryostream labels
        if "cryostream" in values_dict:
            cryo = values_dict["cryostream"]

            set_temp_value = cryo.get(
                "set_temperature", {}).get("value", "N/A")
            sample_temp_value = cryo.get(
                "sample_temperature", {}).get("value", "N/A")
            status_value = cryo.get("status", {}).get("value", "N/A")

            self.cryo_set_temp_label.setText(f"{set_temp_value} °K")
            self.cryo_sample_temp_label.setText(f"{sample_temp_value} °K")
            self.cryo_status_label.setText(f"{status_value}")

        # Check if machine current is <= 99, change color for machine info labels only
        if current_value != "N/A" and float(current_value) <= 99:
            self.set_machine_labels_color("salmon")
        else:
            self.reset_machine_labels_color()

        # Set cryostream color based on its status (independent of beam current)
        self.update_cryostream_colors(values_dict)

    def set_all_labels_color(self, color):
        """Set all label backgrounds to the specified color."""
        self.current_label.setStyleSheet(f"background-color: {color};")
        self.message_label.setStyleSheet(f"background-color: {color};")
        self.lifetime_label.setStyleSheet(f"background-color: {color};")
        self.energy_label.setStyleSheet(f"background-color: {color};")
        self.cryo_set_temp_label.setStyleSheet(f"background-color: {color};")
        self.cryo_sample_temp_label.setStyleSheet(
            f"background-color: {color};")
        self.cryo_status_label.setStyleSheet(f"background-color: {color};")

    def reset_all_labels_color(self):
        """Reset all label backgrounds to their default color."""
        default_color = "#6cb2f8"
        self.current_label.setStyleSheet(f"background-color: {default_color};")
        self.message_label.setStyleSheet(f"background-color: {default_color};")
        self.lifetime_label.setStyleSheet(
            f"background-color: {default_color};")
        self.energy_label.setStyleSheet(f"background-color: {default_color};")
        self.cryo_set_temp_label.setStyleSheet(
            f"background-color: {default_color};")
        self.cryo_sample_temp_label.setStyleSheet(
            f"background-color: {default_color};")
        self.cryo_status_label.setStyleSheet(
            f"background-color: {default_color};")

    def set_machine_labels_color(self, color):
        """Set only machine info label backgrounds to the specified color."""
        self.current_label.setStyleSheet(f"background-color: {color};")
        self.message_label.setStyleSheet(f"background-color: {color};")
        self.lifetime_label.setStyleSheet(f"background-color: {color};")
        self.energy_label.setStyleSheet(f"background-color: {color};")

    def reset_machine_labels_color(self):
        """Reset only machine info label backgrounds to their default color."""
        default_color = "#6cb2f8"
        self.current_label.setStyleSheet(f"background-color: {default_color};")
        self.message_label.setStyleSheet(f"background-color: {default_color};")
        self.lifetime_label.setStyleSheet(
            f"background-color: {default_color};")
        self.energy_label.setStyleSheet(f"background-color: {default_color};")

    def update_cryostream_colors(self, values_dict):
        """Update cryostream label colors based on cryostream status (independent of beam current)."""
        if "cryostream" not in values_dict:
            # No cryostream data, reset to default
            self.reset_cryostream_labels_color()
            return

        cryo = values_dict["cryostream"]
        status_value = cryo.get("status", {}).get("value", "N/A")
        set_temp_value = cryo.get("set_temperature", {}).get("value", "N/A")
        sample_temp_value = cryo.get(
            "sample_temperature", {}).get("value", "N/A")

        # Determine color based on cryostream status and temperature
        cryo_color = self.get_cryostream_color(
            status_value, set_temp_value, sample_temp_value)

        # Apply color to cryostream labels only
        self.cryo_set_temp_label.setStyleSheet(
            f"background-color: {cryo_color};")
        self.cryo_sample_temp_label.setStyleSheet(
            f"background-color: {cryo_color};")
        self.cryo_status_label.setStyleSheet(
            f"background-color: {cryo_color};")

    def get_cryostream_color(self, status_value, set_temp_value, sample_temp_value):
        """Determine color for cryostream based on status and temperature."""
        if status_value == "N/A" or status_value is None:
            return "#868e96"  # Gray for unknown/N/A

        status_str = str(status_value).lower()

        # Check for specific good status first
        if status_str == "no errors or warnings":
            # This is a good status, check temperature stability
            temp_stable = self.check_temperature_stability(
                set_temp_value, sample_temp_value)
            if not temp_stable:
                return "#ff6b6b"  # Red for temperature instability
            else:
                return "#6cb2f8"  # Blue for good status with stable temp

        # Error conditions - red (check these first)
        # Use more specific patterns to avoid false positives
        error_patterns = [
            " error", " fail", " fault", " alarm", " not ready",
            " not in place", " unknown", " invalid", " no nitrogen", " no helium",
            " vacuum", " overheat", " timeout", " disconnect", " service required",
            "no alarm status available"
        ]

        # Check for error patterns (with space prefix to avoid "error" in "No errors")
        if any(pattern in status_str for pattern in error_patterns):
            return "#ff6b6b"  # Light red

        # Check temperature stability for good status only
        temp_stable = self.check_temperature_stability(
            set_temp_value, sample_temp_value)
        if not temp_stable:
            return "#ff6b6b"  # Red for temperature instability

        # Good conditions - blue (same as machine current)
        if any(keyword in status_str for keyword in [
            "no errors", "ready", "complete", "in place", "connected", "ok"
        ]):
            return "#6cb2f8"  # Same blue as machine current

        # Warning conditions - yellow
        elif any(keyword in status_str for keyword in [
            "warning", "temp warning", "pressure warning", "maintenance"
        ]):
            return "#ffd43b"  # Light yellow

        # Default - blue (same as machine current)
        else:
            return "#6cb2f8"  # Same blue as machine current

    def check_temperature_stability(self, set_temp_value, sample_temp_value):
        """Check if cryostream temperature is stable (within ±1K of set temperature)."""
        try:
            # Convert to float if possible
            if set_temp_value == "N/A" or set_temp_value is None:
                return True  # Can't check stability without set temp

            if sample_temp_value == "N/A" or sample_temp_value is None:
                return True  # Can't check stability without sample temp

            set_temp = float(set_temp_value)
            sample_temp = float(sample_temp_value)

            # Check if sample temperature is within ±1K of set temperature
            temp_diff = abs(sample_temp - set_temp)
            is_stable = temp_diff <= 1.0

            if not is_stable:
                logging.getLogger("HWR").debug(
                    f"Cryostream temperature instability: Set={set_temp}K, Sample={sample_temp}K, Diff={temp_diff:.1f}K"
                )

            return is_stable

        except (ValueError, TypeError) as e:
            logging.getLogger("HWR").debug(
                f"Error checking temperature stability: {e}")
            return True  # Assume stable if we can't parse temperatures

    def reset_cryostream_labels_color(self):
        """Reset cryostream label backgrounds to their default color."""
        default_color = "#6cb2f8"
        self.cryo_set_temp_label.setStyleSheet(
            f"background-color: {default_color};")
        self.cryo_sample_temp_label.setStyleSheet(
            f"background-color: {default_color};")
        self.cryo_status_label.setStyleSheet(
            f"background-color: {default_color};")

