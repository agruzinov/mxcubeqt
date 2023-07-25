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


"""PyQt GUI for runtime queries - port of paramsgui - rhfogh Jan 2018, May 2023
"""
from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

import os.path
import logging
import gevent
import gevent.event

from collections import OrderedDict

from mxcubeqt.utils import qt_import, colors
from mxcubecore.dispatcher import dispatcher


__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"

ColourMap = {
    "OK": colors.WHITE,
    "WARNING": colors.LIGHT_ORANGE,
    "ERROR": colors.LINE_EDIT_ERROR,
    "CHANGED": colors.LINE_EDIT_CHANGED,
}

class ValueWidget:
    """Mixin class for widgets containg actual values (i..e not containers)"""
    def __init__(self, gui_root_widget, options):
        self.is_hidden = options.get("hidden")
        self.gui_root_widget = gui_root_widget
        self.__name = options["variable_name"]
        if "default" in options:
            self.set_value(options["default"])
        self.update_on_change = bool(options.get("update_on_change"))
        self.highlight = options.get("highlight")

        if self.is_hidden or options.get("readOnly"):
            self.setReadOnly(True)
            self.setEnabled(False)

    def get_name(self):
        return self.__name

    def is_valid(self):
        """Override in subclasses where there is validity checking"""
        return True

    def input_field_changed(self):
        """UI update function triggered by field value changes"""
        root_widget = self.gui_root_widge
        valid = self.is_valid()
        if valid:
            update_on_change = self.gui_root_widget.update_on_change
            if (update_on_change
                and (self.update_on_change or update_on_change == "always")
            ):
                self._wait_event.clear()
                responses = dispatcher.send(
                    root_widget.return_signal,
                    self,
                    self.get_name(),
                    root_widget.get_values_map(),
                )
                if not responses:
                    self._return_parameters.set_exception(
                        RuntimeError("Signal 'gphlJsonParametersNeeded' is not connected")
                    )
                self._wait_event.wait()
        root_widget.validate_fields()
        colors.set_widget_color(
            self, colors.LINE_EDIT_CHANGED, qt_import.QPalette.Base
        )

    def colour_widget(self, colour):
        """

        Args:
            colour (str): One of WIDGET_COLOURS

        Returns: None

        """
        colors.set_widget_color(self, getattr(colors, colour), qt_import.QPalette.Base)

class LineEdit(qt_import.QLineEdit, ValueWidget):
    """Standard LineEdit widget"""

    def __init__(self, parent, options):
        qt_import.QLineEdit.__init__(self, parent)
        self.setAlignment(qt_import.Qt.AlignRight)

    def set_value(self, value):
        self.setText(value)

    def get_value(self):
        return str(self.text())

class FloatString(LineEdit):
    """LineEdit widget with validators and formatting for floating point numbers"""

    def __init__(self, parent, options):
        decimals = options.get("decimals")
        # NB We do NOT enforce a maximum number of decimals in edited text,
        # Only in set values.
        if decimals is None:
            self.formatstr = "%s"
        else:
            self.formatstr = "%%.%sf" % decimals
        LineEdit.__init__(self, parent, options)
        self.validator = qt_import.QDoubleValidator(self)
        val = options.get("minimum")
        if val is not None:
            self.validator.setBottom(val)
        val = options.get("maximum")
        if val is not None:
            self.validator.setTop(val)
        import_module = self.import_module = options.get("import_module")
        fname = options.get("update_function")
        if fname:
            if import_module:
                self.update_function = getattr(import_module, fname)
            else:
                raise ValueError(
                    "Widget %s has update_function %s but lacks import_module"
                    % (self, fname)
                )
        else:
            self.update_function = None

        self.textEdited.connect(self.input_field_changed)

    def set_value(self, value):
        self.setText(self.formatstr % value)

    def get_value(self):
        val = self.text().strip()
        if val:
            return float(val)
        else:
            return None

    def is_valid(self):

        if (
            self.validator.validate(self.text(), 0)[0]
            != qt_import.QValidator.Acceptable
        ):
            return False
        return True


class TextEdit(qt_import.QTextEdit, ValueWidget):
    """Standard text edit widget (multiline text)"""

    def __init__(self, parent, options):
        qt_import.QTextEdit.__init__(self, parent)
        self.is_hidden = options.get("hidden")
        self.setAlignment(qt_import.Qt.AlignLeft)
        self.setSizePolicy(
            qt_import.QSizePolicy.Expanding, qt_import.QSizePolicy.Expanding
        )
        self.setSizeAdjustPolicy(qt_import.QAbstractScrollArea.AdjustToContents)
        self.setFont(qt_import.QFont("Courier"))
        self.__name = options["variable_name"]
        if "default" in options:
            self.set_value(options["default"])
        if self.is_hidden or options.get("readOnly"):
            self.setReadOnly(True)

    def set_value(self, value):
        self.setText(value)

    def get_value(self):
        return str(self.toPlainText())


class Combo(qt_import.QComboBox, ValueWidget):
    """Standard ComboBox (pulldown) widget"""

    def __init__(self, parent, options):
        qt_import.QComboBox.__init__(self, parent)
        self.__name = options["variable_name"]
        self.setup_pulldown(**options)
        import_module = self.import_module = options.get("import_module")
        fname = options.get("update_function")
        if fname:
            if import_module:
                self.update_function = getattr(import_module, fname)
            else:
                raise ValueError(
                    "Widget %s has update_function %s but lacks import_module"
                    % (self, fname)
                )
        else:
            self.update_function = None
        self.currentIndexChanged.connect(self.input_field_changed)
        self.setSizeAdjustPolicy(qt_import.QComboBox.AdjustToContents)

    def setup_pulldown(self, **options):
        self.is_hidden = options.get("hidden")
        self.value_dict = options["value_dict"]
        for val in self.value_dict:
            self.addItem(str(val))
        if "default" in options:
            self.set_value(options["default"])

    def set_value(self, value):
        self.setCurrentIndex(self.findText(value))

    def get_value(self):
        return self.value_dict.get(str(self.currentText()))

    def reset_options(self, options):
        # Supported options are: value_dict, hidden, and default
        supported = frozenset(("hidden", "value_dict", "default"))
        disallowed = frozenset(options).difference(supported)
        if disallowed:
            raise ValueError(
                "Disallowed reset options for widget %s: %s"
                % (self.get_name(), sorted(disallowed))
            )
        self.clear()
        self.setup_pulldown(**options)


class File(qt_import.QWidget, ValueWidget):
    """Standard file selection widget"""

    def __init__(self, parent, options):
        qt_import.QWidget.__init__(self, parent)

        # do not allow qt to stretch us vertically
        policy = self.sizePolicy()
        policy.setVerticalPolicy(qt_import.QSizePolicy.Fixed)
        self.setSizePolicy(policy)

        qt_import.QHBoxLayout(self)
        self.__name = options["variable_name"]
        self.filepath = qt_import.QLineEdit(self)
        self.filepath.setAlignment(qt_import.Qt.AlignLeft)
        if "default" in options:
            self.filepath.setText(options["default"])
        self.open_dialog_btn = qt_import.QPushButton("...", self)
        self.open_dialog_btn.clicked.connect(self.open_file_dialog)

        self.layout().addWidget(self.filepath)
        self.layout().addWidget(self.open_dialog_btn)

    def set_value(self, value):
        self.filepath.setText(value)

    def get_value(self):
        return str(self.filepath.text())

    def open_file_dialog(self):
        start_path = os.path.dirname(str(self.filepath.text()))
        if not os.path.exists(start_path):
            start_path = ""
        path = qt_import.QFileDialog(self).getOpenFileName(directory=start_path)
        if not path.isNull():
            self.filepath.setText(path)


class IntSpinBox(qt_import.QSpinBox, ValueWidget):
    """Standard integer (spinbox) widget"""

    CHANGED_COLOR = qt_import.QColor(255, 165, 0)

    def __init__(self, parent, options):
        qt_import.QSpinBox.__init__(self, parent)
        self.lineEdit().setAlignment(qt_import.Qt.AlignLeft)
        self.__name = options["variable_name"]
        if "unit" in options:
            self.setSuffix(" " + options["unit"])
        if "default" in options:
            val = int(options["default"])
            self.setValue(val)
        if "maximum" in options:
            self.setMaximum(int(options["maximum"]))
        if "minimum" in options:
            self.setMinimum(int(options["minimum"]))
        if "tooltip" in options:
            self.setToolTip(options["tooltip"])
        self.is_hidden = options.get("hidden")

    def set_value(self, value):
        self.setValue(int(value))

    def get_value(self):
        val = self.value()
        if val:
            return int(val)
        else:
            return None


class DoubleSpinBox(qt_import.QDoubleSpinBox, ValueWidget):
    """Standard float (spinbox) widget"""

    # CHANGED_COLOR = qt_import.QColor(255, 165, 0)

    def __init__(self, parent, options):
        qt_import.QDoubleSpinBox.__init__(self, parent)
        self.lineEdit().setAlignment(qt_import.Qt.AlignLeft)
        self.__name = options["variable_name"]
        if "unit" in options:
            self.setSuffix(" " + options["unit"])
        if "default" in options:
            val = float(options["default"])
            self.setValue(val)
        if "maximum" in options:
            self.setMaximum(float(options["maximum"]))
        if "minimum" in options:
            self.setMinimum(float(options["minimum"]))
        if "tooltip" in options:
            self.setToolTip(options["tooltip"])
        self.is_hidden = options.get("hidden")

    def set_value(self, value):
        self.setValue(float(value))

    def get_value(self):
        val = self.value()
        if val:
            return float(val)
        else:
            return None


class CheckBox(qt_import.QCheckBox, ValueWidget):
    """Standard Boolean (CheckBox) widget"""

    def __init__(self, parent, options):
        qt_import.QCheckBox.__init__(self, options.get("uiLabel"), parent)
        # self.setAlignment(qt_import.Qt.AlignLeft)
        self.is_hidden = options.get("hidden")
        self.__name = options["variable_name"]
        state = (
            qt_import.Qt.Checked if options.get("default") else qt_import.Qt.Unchecked
        )
        self.setCheckState(state)
        self.setSizePolicy(
            qt_import.QSizePolicy.Expanding, qt_import.QSizePolicy.Expanding
        )

    def set_value(self, value):
        self.setChecked(value)

    def get_value(self):
        return self.isChecked()


class LocalQGroupBox(qt_import.QGroupBox):
    is_hidden = False


def create_widgets(
    schema, ui_schema, field_name=None, parent_widget=None, gui_root_widget=None
):
    """Recursive widget creation function

    Args:
        schema (dict):  jsonschema
        ui_schema (dict): ui:schema dictionary for widget being created
        field_name (str): Unique name of field (or container) being created.
                          Equal to tag in ui_schema, and used as variable_name
        parent_widget(qt_import.QWidget): parent widget
        gui_root_widget (dict): root (layoutWidget) widget

    Returns (qt_import.QWidget):

    NB the input data structures differ from standard ui:schema usage
    fields and layout are taken from the ui:schema, so the schema order is mandatory
    there are grouping constructs corresponding to columns and boxes in the ui:schema
    that do not match any object in the jsonschema.
    """

    is_top_object = gui_root_widget is None

    default_container_name = "vertical_box"

    fields = schema["properties"]
    # definitions = schema["definitions"]

    field_data = fields.get(field_name)
    if field_data:
        # This is an actual data field
        widget_name = ui_schema.get("ui:widget")
        if not widget_name:
            widget_name = field_data.get("type")
        options = field_data.copy()
        options["variable_name"] = field_name

        pathstr = field_data.get("$ref")
        if "value_dict" in options and not ui_schema.get("ui:widget"):
            widget_name = "select"
        elif pathstr:
            if not ui_schema.get("ui:widget"):
                widget_name = "select"
            tags = pathstr.split("/")[1:]
            dd0 = schema
            for tag in tags:
                dd0 = dd0[tag]
            enums = dd0
            options["value_dict"] = OrderedDict(
                (dd1["title"], dd1["enum"][0]) for dd1 in enums
            )

        options.update(ui_schema.get("ui:options", {}))
        if ui_schema.get("ui:readonly"):
            options["readOnly"] = True
        widget = WIDGET_CLASSES[widget_name](parent_widget, options)
        if widget.is_hidden:
            if hasattr(widget, "setReadOnly"):
                widget.setReadOnly(True)
            widget.setEnabled(False)
            widget.hide()
        gui_root_widget.parameter_widgets[field_name] = widget
    else:
        # This is a container field
        title = ui_schema.get("ui:title")
        widget_name = ui_schema.get("ui:widget") or default_container_name
        if is_top_object:
            # Top of schema
            options = ui_schema["ui:options"]
            widget = gui_root_widget = LayoutWidget(options)
        elif title:
            widget = LocalQGroupBox(title, parent=parent_widget)
        else:
            widget = LocalQGroupBox(parent=parent_widget)
        layout_class = WIDGET_CLASSES[widget_name]
        layout = layout_class(widget)
        layout.setSpacing(6)
        widget.setSizePolicy(
            qt_import.QSizePolicy.Expanding, qt_import.QSizePolicy.Expanding
        )
        layout.populate_widget(schema, ui_schema, field_name, gui_root_widget)
    if is_top_object:
        # This is the root widget
        # Now everything is populated, put the hidden widgets in as data holders
        for fname, field in fields.items():
            if fname not in gui_root_widget.parameter_widgets:
                if field.get("hidden"):
                    # NB should not happen much,
                    # but might be used to temporarily hide fields
                    create_widgets(
                        schema,
                        field,
                        fname,
                        parent_widget=gui_root_widget,
                        gui_root_widget=gui_root_widget,
                    )
                else:
                    raise RuntimeError(
                        "Coding error: UI fields %s is neither hidden nor displayed"
                        % fname
                    )

    #
    return widget


class ColumnGridWidget(qt_import.QGridLayout):
    """Gridded layout, content specified by column"""

    col_spacing = " " * 7

    def __init__(self, parent):
        """
        Args:
            parent (qtimport.QtWidget:
        """
        super().__init__(parent)
        self.is_hidden = False

    def populate_widget(self, schema, ui_schema, field_name, gui_root_widget):
        fields = schema["properties"]
        maxrownum = 0
        for colnum, colname in enumerate(
            (ui_schema["ui:order"])
            or list(x for x in ui_schema if not x.startswith("ui:"))
        ):
            column = ui_schema[colname]
            col1 = 2 * colnum
            col2 = col1 + 1
            for rownum, rowname in enumerate(
                (column["ui:order"])
                or list(x for x in column if not x.startswith("ui:"))
            ):
                field = fields.get(rowname)
                ui_field = column.get(rowname) or field
                new_widget = create_widgets(
                    schema,
                    ui_field,
                    rowname,
                    self.parent(),
                    gui_root_widget,
                )
                if field:
                    widget_type = ui_field.get("ui:widget") or field.get(type, "string")
                    if widget_type in ("textarea", "selection_table"):
                        self.setRowStretch(rownum, 8)
                        self.setColumnStretch(colnum, 8)
                    title = field.get("title") or ui_field.get("ui:title")
                    if title:
                        if widget_type in ("textarea", "selection_table"):
                            # Special case - title goes above
                            outer_box = LocalQGroupBox(
                                title,
                                parent=self.parent(),
                            )
                            self.addWidget(
                                outer_box,
                                rownum,
                                col1,
                                1,
                                2,
                            )
                            outer_layout = qt_import.QVBoxLayout()
                            outer_box.setLayout(outer_layout)
                            outer_layout.addWidget(new_widget)
                            outer_layout.setStretch(8, 8)
                        elif not new_widget.is_hidden:
                            new_widget.setSizePolicy(
                                qt_import.QSizePolicy.Fixed, qt_import.QSizePolicy.Fixed
                            )
                            if col1:
                                # Add spacing to columns after the first
                                title = self.col_spacing + title
                            label = qt_import.QLabel(title, self.parent())
                            self.addWidget(
                                label,
                                rownum,
                                col1,
                                qt_import.Qt.AlignRight | qt_import.Qt.AlignTop,
                            )
                            self.addWidget(
                                new_widget,
                                rownum,
                                col2,
                                qt_import.Qt.AlignLeft | qt_import.Qt.AlignTop,
                            )
                    else:
                        self.addWidget(
                            new_widget,
                            rownum,
                            col1,
                            1,
                            2,
                        )
                else:
                    title = ui_schema.get("ui:title")
                    if title:
                        outer_box = LocalQGroupBox(title, parent=self.parent())
                        self.addWidget(
                            outer_box,
                            rownum,
                            col1,
                            1,
                            2,
                        )
                        outer_layout = qt_import.QVBoxLayout()
                        outer_box.setLayout(outer_layout)
                        outer_layout.addWidget(
                            new_widget,
                            0,
                        )
                        # outer_layout.setStretch(0, 8)
                    else:
                        self.addWidget(
                            new_widget,
                            rownum,
                            col1,
                            1,
                            2,
                        )
            else:
                maxrownum = max(maxrownum, rownum)
        # Add spacer to compress layout
        spacerItem = qt_import.QSpacerItem(
            6,
            6,
            qt_import.QSizePolicy.Expanding,
            qt_import.QSizePolicy.Expanding,
        )
        self.addItem(spacerItem, maxrownum + 1, col2 + 1)


class VerticalBox(ColumnGridWidget):
    """Treated as a single column gridded box, with input not grouped in columns"""

    def populate_widget(self, schema, ui_schema, field_name, gui_root_widget):
        wrap_schema = {}
        col_schema = wrap_schema["column"] = {}
        self.is_hidden = False
        for tag, val in ui_schema.items():
            if tag.startswith("ui:"):
                wrap_schema[tag] = val
            else:
                col_schema[tag] = val
        col_schema["ui:order"] = wrap_schema["ui:order"]
        wrap_schema["ui:order"] = ("column",)
        #
        super().populate_widget(schema, wrap_schema, field_name, gui_root_widget)


class HorizontalBox(ColumnGridWidget):
    def populate_widget(self, schema, ui_schema, field_name, gui_root_widget):
        wrap_schema = {}
        self.is_hidden = False
        title = ui_schema.get("ui:title")
        if title:
            wrap_schema["ui:title"] = title
        wrap_schema["ui:order"] = new_order = []
        for tag in ui_schema["ui:order"]:
            colname = tag + "_col"
            new_order.append((colname))
            dd0 = {"ui:order": [tag]}
            if tag in ui_schema:
                dd0[tag] = ui_schema[tag]
            wrap_schema[colname] = dd0
        #
        super().populate_widget(schema, wrap_schema, field_name, gui_root_widget)


class LayoutWidget(qt_import.QWidget):
    """Collection-of-widgets widget for parameter query"""

    parametersValidSignal = qt_import.pyqtSignal(bool)

    def __init__(self, options):



        self.parameter_widgets = {}
        self.return_signal = options.get("return_signal")
        self.update_signal = options.get("update_signal")
        self.update_on_change = options.get("update_on_change")
        qt_import.QWidget.__init__(self)
        dispatcher.connect(self.update_values, self.update_signal, dispatcher.Any)

        # event to handle waiting for parameter input
        self._wait_event = gevent.event.Event()

    def close(self):
        super().close()
        dispatcher.disconnect(self.update_values, self.update_signal, dispatcher.Any)

    def set_values(self, **values):
        """Set values for all fields from values dictionary"""
        for tag, val in values.items():
            self.parameter_widgets[tag].set_value(val)

    def get_values_map(self):
        """Get parameter values dictionary for all fields"""
        return dict(
            (tag, val.get_value()) for tag, val in self.parameter_widgets.items()
        )

    def update_values(self, changes_dict):

        for tag, ddict in changes_dict.items():
            widget = self.parameter_widgets[tag]
            if "value" in ddict:
                widget.set_value(ddict["value"])
            options = ddict.get("options")
            if options is not None:
                if hasattr(widget, "reset_options"):
                    widget.reset_options(options)
                else:
                    raise ValueError(
                        " reset_options not supported for widget %s of type %s"
                        % (tag, widget.__class__.__name__)
                    )
            highlight = ddict.get("highlight")
            widget.highlight = highlight
        self._wait_event.set()

    def validate_fields(self, editing=None):
        all_valid = True
        for field_name, widget in self.parameter_widgets.items():
            if widget.is_valid():
                colour = widget.highlight
                if not colour:
                    if field_name == editing:
                        colour = "CHANGED"
                    else:
                        colour = "OK"
            else:
                all_valid = False
                print(
                    "WARNING, invalid value %s for %s"
                    % (widget.get_value(), field_name)
                )
                colour = "ERROR"
            self.colour_widget(field_name, colour)
        self.parametersValidSignal.emit(all_valid)

class MultiSelectionTable(qt_import.QTableWidget, ValueWidget):
    """Read-only table for data display and selection;
    allows slection of multiple cells"""

    def __init__(self, parent, options):
        qt_import.QTableWidget.__init__(self, parent)
        raise NotImplementedError()


class SelectionTable(qt_import.QTableWidget, ValueWidget):
    """Read-only table for data display and selection"""

    def __init__(self, parent, options):
        qt_import.QTableWidget.__init__(self, parent)
        header = options["header"]

        self.is_hidden = options.get("hidden")

        # self.setObjectName(name)
        self.setFrameShape(qt_import.QFrame.StyledPanel)
        self.setFrameShadow(qt_import.QFrame.Sunken)
        self.setContentsMargins(0, 3, 0, 3)
        self.setColumnCount(len(header))
        self.setSelectionMode(qt_import.QTableWidget.SingleSelection)
        self.setHorizontalHeaderLabels(header)
        self.horizontalHeader().setDefaultAlignment(qt_import.Qt.AlignLeft)
        self.setSizePolicy(
            qt_import.QSizePolicy.Expanding, qt_import.QSizePolicy.Expanding
        )
        self.setSizeAdjustPolicy(qt_import.QAbstractScrollArea.AdjustToContents)
        self.setFont(qt_import.QFont("Courier"))

        hdr = self.horizontalHeader()
        hdr.setResizeMode(0, qt_import.QHeaderView.Stretch)
        for idx in range(1, len(header)):
            hdr.setResizeMode(idx, qt_import.QHeaderView.ResizeToContents)

        colouring = options.get("colouring")
        for idx, data in enumerate(options["content"]):
            self.populateColumn(idx, data, colouring)

        self.setCurrentCell(options.get("select_row", 0), 0)

        import_module = self.import_module = options.get("import_module")
        fname = options.get("update_function")
        if fname:
            if import_module:
                self.update_function = getattr(import_module, fname)
            else:
                raise ValueError(
                    "Widget %s has update_function %s but lacks import_module"
                    % (self, fname)
                )
        else:
            self.update_function = None
        self.currentCellChanged.connect(self.input_field_changed)

    def resizeData(self, ii):
        """Dummy method, recommended by docs when not using std cell widgets"""
        pass

    def populateColumn(self, colnum, values, colouring=None):
        """Fill values into column, extending if necessary"""
        if len(values) > self.rowCount():
            self.setRowCount(len(values))
        if colouring and any(colouring):
            colour = getattr(colors, "LIGHT_GREEN")
        else:
            colour = None
        for rownum, text in enumerate(values):
            wdg = qt_import.QLineEdit(self)
            wdg.setFont(qt_import.QFont("Courier"))
            wdg.setReadOnly(True)
            wdg.setText(str(text))
            if colour and colouring[rownum]:
                colors.set_widget_color(wdg, colour, qt_import.QPalette.Base)
            self.setCellWidget(rownum, colnum, wdg)

    def get_value(self):
        """Get value - list of cell contents for selected row"""
        row_id = self.currentRow()
        if not self.cellWidget(row_id, 0):
            logging.getLogger("user_log").warning(
                "Select a row of the table, and then press [Continue]"
            )
        return [self.cellWidget(row_id, ii).text() for ii in range(self.columnCount())]


# Class is selected from ui:widget or, failing that, from type
WIDGET_CLASSES = {
    "number": FloatString,
    "string": LineEdit,
    "boolean": CheckBox,
    "integer": FloatString,
    "textarea": TextEdit,
    "spinbox": IntSpinBox,
    "float": DoubleSpinBox,
    "select": Combo,
    "column_grid": ColumnGridWidget,
    "horizontal_box": HorizontalBox,
    "vertical_box": VerticalBox,
    "selection_table": SelectionTable,
    "multi_selection_table": MultiSelectionTable,
}
