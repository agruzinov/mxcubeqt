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

import os
import time

from mxcubeqt.utils import icons, qt_import
from mxcubeqt.base_components import BaseWidget

from mxcubecore.HardwareObjects import QtInstanceServer


__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class ChatBrick(BaseWidget):

    PRIORITY_COLORS = ("darkblue", "black", "red")
    MY_COLOR = "darkgrey"

    incoming_unread_messages = qt_import.pyqtSignal(int, bool)
    reset_unread_messages = qt_import.pyqtSignal(bool)

    def __init__(self, *args):

        BaseWidget.__init__(self, *args)

        # Properties ----------------------------------------------------------
        self.add_property("mnemonic", "string", "")
        self.add_property("icons", "string", "")
        self.add_property("myTabLabel", "string", "")

        # Signals ------------------------------------------------------------
        self.define_signal("incoming_unread_messages", ())
        self.define_signal("reset_unread_message", ())

        # Slots ---------------------------------------------------------------
        self.define_slot("tabSelected", ())
        self.define_slot("sessionSelected", ())

        # Hardware objects ----------------------------------------------------
        self.instance_server_hwobj = None

        # Internal values -----------------------------------------------------
        self.session_id = None
        self.nickname = ""
        self.role = BaseWidget.INSTANCE_ROLE_UNKNOWN

        # Graphic elements ----------------------------------------------------
        self.conversation_textedit = qt_import.QTextEdit(self)
        self.conversation_textedit.setReadOnly(True)
        _controls_widget = qt_import.QWidget(self)
        _say_label = qt_import.QLabel("Say:", _controls_widget)
        self.message_ledit = qt_import.QLineEdit(_controls_widget)
        self.send_button = qt_import.QPushButton("Send", _controls_widget)
        self.send_button.setEnabled(False)

        # Layout --------------------------------------------------------------
        _controls_widget_hlayout = qt_import.QHBoxLayout(_controls_widget)
        _controls_widget_hlayout.addWidget(_say_label)
        _controls_widget_hlayout.addWidget(self.message_ledit)
        _controls_widget_hlayout.addWidget(self.send_button)
        _controls_widget_hlayout.setSpacing(2)
        _controls_widget_hlayout.setContentsMargins(0, 0, 0, 0)

        _main_vlayout = qt_import.QVBoxLayout(self)
        _main_vlayout.addWidget(self.conversation_textedit)
        _main_vlayout.addWidget(_controls_widget)
        _main_vlayout.setSpacing(2)
        _main_vlayout.setContentsMargins(2, 2, 2, 2)

        # Qt signal/slot connections ------------------------------------------
        self.send_button.clicked.connect(self.send_current_message)
        self.message_ledit.returnPressed.connect(self.send_current_message)
        self.message_ledit.textChanged.connect(self.message_changed)

        # self.setFixedHeight(120)
        # self.setFixedWidth(790)

    def run(self):
        self.set_role(self.role)

    def session_selected(self, *args):
        session_id = args[0]
        is_inhouse = args[-1]
        self.conversation_textedit.clear()
        if is_inhouse:
            self.session_id = None
        else:
            self.session_id = session_id
            self.load_chat_history()

    def load_chat_history(self):
        if self.instance_server_hwobj is not None:
            chat_history_filename = "/tmp/mxCuBE_chat_%s.%s" % (
                self.session_id,
                self.instance_server_hwobj.isClient() and "client" or "server",
            )
        else:
            return
        try:
            chat_history = open(chat_history_filename, "r")
        except BaseException:
            return

        if self.isEnabled():
            for msg in chat_history.readlines():
                self.conversation_textedit.append(msg)

    def instance_role_changed(self, role):
        self.set_role(role)

    def set_role(self, role):
        self.role = role
        if role != BaseWidget.INSTANCE_ROLE_UNKNOWN and not self.isEnabled():
            self.setEnabled(True)
            self.load_chat_history()

    def message_changed(self, text):
        self.send_button.setEnabled(len(str(text)) > 0)

    def message_arrived(self, priority, user_id, message):
        color = ChatBrick.PRIORITY_COLORS[priority]
        msg_prefix = ""
        msg_suffix = ""
        if priority == QtInstanceServer.ChatInstanceMessage.PRIORITY_NORMAL:
            if user_id is None:
                header = ""
            else:
                header = " %s:" % self.instance_server_hwobj.idPrettyPrint(user_id)
                if user_id[0] == self.nickname:
                    color = ChatBrick.MY_COLOR
        else:
            header = ""
            msg_prefix = "<i>"
            msg_suffix = "</i>"

        now = time.strftime("%T")
        new_line = "<font color=%s><b>(%s)%s</b> %s%s%s</font>" % (
            color,
            now,
            header,
            msg_prefix,
            message,
            msg_suffix,
        )
        self.conversation_textedit.append(new_line)

        if self.session_id is not None and self.instance_server_hwobj is not None:
            chat_history_filename = "/tmp/mxCuBE_chat_%s.%s" % (
                self.session_id,
                self.instance_server_hwobj.isClient() and "client" or "server",
            )
            try:
                if time.time() - os.stat(chat_history_filename).st_mtime > 24 * 3600:
                    os.unlink(chat_history_filename)
            except OSError:
                pass
            chat_history_file = open(chat_history_filename, "a")
            chat_history_file.write(new_line)
            chat_history_file.write("\n")
            chat_history_file.close()

        # self.emit(QtCore.SIGNAL("incUnreadMessages"),1, True)
        self.incoming_unread_messages.emit(1, True)

    def new_client(self, client_id):
        msg = (
            "%s has joined the conversation."
            % self.instance_server_hwobj.idPrettyPrint(client_id)
        )
        self.message_arrived(QtInstanceServer.ChatInstanceMessage.PRIORITY_LOW, None, msg)

    def wants_control(self, client_id):
        msg = "%s wants to have control!" % self.instance_server_hwobj.idPrettyPrint(
            client_id
        )
        self.message_arrived(
            QtInstanceServer.ChatInstanceMessage.PRIORITY_HIGH, None, msg
        )

    def server_initialized(self, started, server_id=None):
        if started:
            # sg="I'm moderating the chat as %s." % server_id[0]
            # self.message_arrived(InstanceServer.ChatInstanceMessage.PRIORITY_LOW,None,msg)
            self.nickname = server_id[0]

    def client_closed(self, client_id):
        msg = (
            "%s has left the conversation..."
            % self.instance_server_hwobj.idPrettyPrint(client_id)
        )
        self.message_arrived(QtInstanceServer.ChatInstanceMessage.PRIORITY_LOW, None, msg)

    def client_initialized(
        self, connected, server_id=None, my_nickname=None, quiet=False
    ):
        if connected:
            server_print = self.instance_server_hwobj.idPrettyPrint(server_id)
            msg = "I've joined the conversation as %s (moderator is %s)." % (
                my_nickname,
                server_print,
            )
            self.message_arrived(
                QtInstanceServer.ChatInstanceMessage.PRIORITY_LOW, None, msg
            )
            self.nickname = my_nickname

    def client_changed(self, old_client_id, new_client_id):
        # print "CHAT CLIENT CHANGED",old_client_id,new_client_id
        if old_client_id[0] == self.nickname:
            self.nickname = new_client_id[0]
        else:
            old_client_print = self.instance_server_hwobj.idPrettyPrint(old_client_id)
            new_client_print = self.instance_server_hwobj.idPrettyPrint(new_client_id)
            msg = "%s has changed to %s." % (old_client_print, new_client_print)
            self.message_arrived(
                QtInstanceServer.ChatInstanceMessage.PRIORITY_LOW, None, msg
            )

    def send_current_message(self):
        txt = str(self.message_ledit.text())
        if len(txt):
            self.instance_server_hwobj.sendChatMessage(
                QtInstanceServer.ChatInstanceMessage.PRIORITY_NORMAL, txt
            )
            self.message_ledit.setText("")

    def property_changed(self, property_name, old_value, new_value):
        if property_name == "mnemonic":
            if self.instance_server_hwobj is not None:
                self.disconnect(
                    self.instance_server_hwobj,
                    "chatMessageReceived",
                    self.message_arrived,
                )
                self.disconnect(
                    self.instance_server_hwobj, "newClient", self.new_client
                )
                self.disconnect(
                    self.instance_server_hwobj,
                    "serverInitialized",
                    self.server_initialized,
                )
                self.disconnect(
                    self.instance_server_hwobj,
                    "clientInitialized",
                    self.client_initialized,
                )
                self.disconnect(
                    self.instance_server_hwobj, "serverClosed", self.client_closed
                )
                self.disconnect(
                    self.instance_server_hwobj, "wantsControl", self.wants_control
                )
                self.disconnect(
                    self.instance_server_hwobj, "haveControl", self.have_control
                )
                self.disconnect(
                    self.instance_server_hwobj, "passControl", self.pass_control
                )
                self.disconnect(
                    self.instance_server_hwobj, "clientClosed", self.client_closed
                )
                self.disconnect(
                    self.instance_server_hwobj, "clientChanged", self.client_changed
                )

            self.instance_server_hwobj = self.get_hardware_object(new_value)

            if self.instance_server_hwobj is not None:
                self.connect(
                    self.instance_server_hwobj,
                    "chatMessageReceived",
                    self.message_arrived,
                )
                self.connect(self.instance_server_hwobj, "newClient", self.new_client)
                self.connect(
                    self.instance_server_hwobj,
                    "serverInitialized",
                    self.server_initialized,
                )
                self.connect(
                    self.instance_server_hwobj,
                    "clientInitialized",
                    self.client_initialized,
                )
                self.connect(
                    self.instance_server_hwobj, "serverClosed", self.client_closed
                )
                self.connect(
                    self.instance_server_hwobj, "wantsControl", self.wants_control
                )
                self.connect(
                    self.instance_server_hwobj, "haveControl", self.have_control
                )
                self.connect(
                    self.instance_server_hwobj, "passControl", self.pass_control
                )
                self.connect(
                    self.instance_server_hwobj, "clientClosed", self.client_closed
                )
                self.connect(
                    self.instance_server_hwobj, "clientChanged", self.client_changed
                )

        elif property_name == "icons":
            icons_list = new_value.split()
            try:
                self.send_button.setIcon(icons.load_icon(icons_list[0]))
            except IndexError:
                pass
        else:
            BaseWidget.property_changed(self, property_name, old_value, new_value)

    def have_control(self, have_control, gui_only=False):
        if not gui_only:
            if have_control:
                p = QtInstanceServer.ChatInstanceMessage.PRIORITY_HIGH
                msg = "I've gained control!"
            else:
                p = QtInstanceServer.ChatInstanceMessage.PRIORITY_HIGH
                msg = "I've lost control..."
            self.message_arrived(p, None, msg)

    def pass_control(self, has_control_id):
        has_control_print = self.instance_server_hwobj.idPrettyPrint(has_control_id)
        msg = "%s has control." % has_control_print
        self.message_arrived(QtInstanceServer.ChatInstanceMessage.PRIORITY_LOW, None, msg)

    def tabSelected(self, tab_name):
        if tab_name == self["myTabLabel"]:
            # self.emit(QtCore.SIGNAL("resetUnreadMessages"), True)
            self.reset_unread_messages.emit(True)
