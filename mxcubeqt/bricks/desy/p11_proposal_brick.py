import logging
import os

from mxcubeqt.utils import colors, icons, qt_import
from mxcubeqt.bricks.proposal_brick import ProposalBrick, ProposalGUIEvent
from mxcubecore import HardwareRepository as HWR
from mxcubeqt.base_components import BaseWidget


class P11ProposalBrick(ProposalBrick):
    def __init__(self, *args):
        super(P11ProposalBrick, self).__init__(*args)
        self.loggedIn.connect(self.update_login_ui)

    def update_login_ui(self, logged_in):
        """
        Updates the UI based on login state.
    
        Args:
            logged_in (bool): True if the user is logged in, False otherwise.
        """
        if logged_in:
            logging.getLogger("GUI").info("User successfully logged in.")
            self.login_button.hide()
        else:
            logging.getLogger("GUI").info("User not logged in or login failed.")

    def run(self):
        """
        Overrides the base class run method. Manages initialization and
        ensures the state of the UI is updated based on database and session availability.
        """
        if not HWR.beamline.lims:
            self._handle_no_db_connection()
            return

        if not HWR.beamline.session:
            logging.getLogger("HWR").error("Beamline session is not initialized.")
            self.message_widget.setText("Session not initialized.")
            self.message_widget.show()
            return

        self.setEnabled(True)
        self.login_as_user = HWR.beamline.lims.get_login_type() == "user"

        if self.login_as_user:
            self.login_as_user_widget.show()
            self.login_as_proposal_widget.hide()
        else:
            self.login_as_user_widget.hide()
            self.login_as_proposal_widget.show()

        proposal_code = HWR.beamline.session.get_current_proposal_code()

        if not proposal_code:
            self._handle_no_proposal()
        else:
            self._handle_proposal(proposal_code)

        # Trigger server initialization
        start_server_event = ProposalGUIEvent(self.start_servers, ())
        qt_import.QApplication.postEvent(self, start_server_event)

    def _handle_no_db_connection(self):
        """
        Handles the case where no database connection is available.
        """
        logging.getLogger("HWR").warning("Not connected to ISPyB database.")
        self.message_widget.setText("Not connected to ISPyB database.")
        self.message_widget.show()
        self.login_as_proposal_widget.hide()
        self.login_button.hide()
        self.user_group_widget.show()

        # Set fallback session only if session is available
        if HWR.beamline.session:
            HWR.beamline.session.proposal_code = ""
            HWR.beamline.session.session_id = 1
            HWR.beamline.session.proposal_id = ""
            HWR.beamline.session.proposal_number = ""

        self.setWindowTitle.emit(self["titlePrefix"])
        self.loggedIn.emit(True)
        self.sessionSelected.emit(
            HWR.beamline.session.session_id,
            os.getenv("USER", "unknown"),
            str(HWR.beamline.session.session_id),
            0,
            "",
            "",
            False,
        )

    def _handle_no_proposal(self):
        """
        Handles the case where no current proposal is set.
        """
        logging.getLogger("HWR").info("No proposal set for the current session.")
        self.message_widget.setText("No active proposal.")
        self.message_widget.show()
        self.login_as_proposal_widget.hide()
        self.proposal_number_ledit.setText("no proposal")

        self.loggedIn.emit(False)

    def _handle_proposal(self, proposal_code):
        """
        Handles the case where a proposal is available and performs login.
        """
        logging.getLogger("HWR").debug(f"Handling proposal with code: {proposal_code}")
        self.message_widget.hide()
        self.p11_login_as_proposal()

    def p11_login_as_proposal(self):
        if HWR.beamline.lims.simulated_proposal == 1:
            proposal_code = HWR.beamline.lims.simulated_prop_code
            proposal_number = HWR.beamline.lims.simulated_prop_number
        else:
            # Handle case where session is not available
            if not HWR.beamline.session:
                logging.getLogger("HWR").warning("Session not available, cannot login as proposal")
                self.loggedIn.emit(False)
                return
            proposal_code = HWR.beamline.session.get_current_proposal_code()
            proposal_number = HWR.beamline.session.get_current_proposal_number()

        logging.getLogger("HWR").debug(
            f"P11ProposalBrick: Login as proposal - Code: {proposal_code}, Number: {proposal_number}"
        )

        prop = HWR.beamline.lims.get_proposal(proposal_code, proposal_number)

        # Allow login even if ISPyB is unavailable - use fallback proposal data
        if not prop:
            logging.getLogger("HWR").error(
                "P11ProposalBrick: Login as proposal failed - no proposal data."
            )
            self.loggedIn.emit(False)
            return
        
        # Check status - if error, log warning but continue with fallback data
        status = prop.get("status", {})
        if status.get("code") != "ok":
            logging.getLogger("HWR").warning(
                f"P11ProposalBrick: ISPyB connection issue ({status.get('msg', 'unknown')}), "
                f"continuing with offline mode for proposal {proposal_code}{proposal_number}"
            )
            # Continue with the fallback proposal data

        self._do_login_as_proposal(
            proposal_code, proposal_number, None, HWR.beamline.lims.beamline_name
        )

    def select_proposal(self, selected_proposal):
        """
        Selects the provided proposal and handles its display.
    
        Args:
            selected_proposal (dict): The selected proposal data.
        """
        # Log full details of the selected proposal
        logging.getLogger("HWR").info(
            f"Complete selected proposal details: {selected_proposal}"
        )

        # Check if "Proposal" key exists
        if "Proposal" in selected_proposal:
            proposal_details = selected_proposal["Proposal"]
            logging.getLogger("HWR").debug(f"Proposal core details: {proposal_details}")
        else:
            logging.getLogger("HWR").error("Proposal key missing in selected proposal.")
            self.message_widget.setText("Invalid proposal data.")
            self.message_widget.show()
            return

        # Handle further processing of the proposal
        self.show_selected_proposal(selected_proposal["Proposal"])

    def show_selected_proposal(self, proposal):
        """
        Displays selected proposal information in the UI.
        Handles 'suds.sudsobject' by accessing its attributes directly.
        Falls back to session data when proposal object is missing or incomplete.
        """
        # Log entry point with proposal info
        logging.getLogger("HWR").info(
            f"show_selected_proposal called with proposal type: {type(proposal)}, value: {proposal}"
        )
        
        try:
            # Get beamtime ID from session
            if HWR.beamline.session:
                beamtime_id = HWR.beamline.session.get_current_beamtime_id()
            else:
                beamtime_id = "N/A"
            
            # Try to get proposal code and number from proposal object
            prop_number = None
            prop_code = None
            
            if proposal is not None:
                # First try dictionary-style access (most common case)
                if isinstance(proposal, dict):
                    prop_number = proposal.get("number", None)
                    prop_code = proposal.get("code", None)
                    # Also try alternative key names
                    if prop_number is None:
                        prop_number = proposal.get("proposalNumber", None)
                    if prop_code is None:
                        prop_code = proposal.get("proposalCode", None)
                    logging.getLogger("HWR").info(
                        f"Extracted from dict: code={prop_code}, number={prop_number}"
                    )
                else:
                    # Try attribute access for suds objects or other objects
                    try:
                        prop_number = getattr(proposal, "proposalNumber", None)
                        prop_code = getattr(proposal, "proposalCode", None)
                        # Also try alternative attribute names
                        if prop_number is None:
                            prop_number = getattr(proposal, "number", None)
                        if prop_code is None:
                            prop_code = getattr(proposal, "code", None)
                        logging.getLogger("HWR").info(
                            f"Extracted from attributes: code={prop_code}, number={prop_number}"
                        )
                    except (AttributeError, TypeError) as e:
                        logging.getLogger("HWR").warning(f"Attribute access failed: {e}")
                        pass
            else:
                logging.getLogger("HWR").warning("Proposal object is None")
            
            # Fall back to session data if proposal object doesn't have the info
            if prop_number is None or prop_code is None:
                logging.getLogger("HWR").info(
                    f"Proposal extraction incomplete: code={prop_code}, number={prop_number}, using session fallback"
                )
                if HWR.beamline.session:
                    if prop_code is None:
                        prop_code = HWR.beamline.session.get_current_proposal_code()
                        logging.getLogger("HWR").info(f"Got proposal code from session: {prop_code}")
                    if prop_number is None:
                        prop_number = HWR.beamline.session.get_current_proposal_number()
                        logging.getLogger("HWR").info(f"Got proposal number from session: {prop_number}")
                else:
                    logging.getLogger("HWR").warning("No session available for fallback")
                    prop_code = prop_code or "N/A"
                    prop_number = prop_number or "N/A"
            
            # Convert to string if needed, ensuring we have valid values
            # Note: session methods may return "N/A" as string, which is acceptable
            prop_code = str(prop_code) if prop_code is not None and prop_code != "" else "N/A"
            prop_number = str(prop_number) if prop_number is not None and prop_number != "" else "N/A"
            
            logging.getLogger("HWR").info(
                f"Final proposal values: code={prop_code}, number={prop_number}, beamtime_id={beamtime_id}"
            )

            # Format the information for display
            prop_info = f"ID: {prop_code}-{prop_number} - BT_ID: {beamtime_id}"
        except Exception as e:
            logging.getLogger("HWR").error(f"Error displaying proposal: {e}", exc_info=True)
            # Fallback: try to get from session
            try:
                if HWR.beamline.session:
                    prop_code = HWR.beamline.session.get_current_proposal_code()
                    prop_number = HWR.beamline.session.get_current_proposal_number()
                    beamtime_id = HWR.beamline.session.get_current_beamtime_id()
                    # Ensure we have valid values
                    prop_code = str(prop_code) if prop_code is not None and prop_code != "" else "N/A"
                    prop_number = str(prop_number) if prop_number is not None and prop_number != "" else "N/A"
                    prop_info = f"ID: {prop_code}-{prop_number} - BT_ID: {beamtime_id}"
                else:
                    prop_info = "Incomplete proposal information."
            except Exception as e2:
                logging.getLogger("HWR").error(f"Error in fallback: {e2}", exc_info=True)
                prop_info = "Incomplete proposal information."

        logging.getLogger("GUI").info(f"Displaying proposal info: {prop_info}")
        self.proposal_info.setText(prop_info)
        self.proposal_info.show()

        # Hide fields irrelevant after login
        self.code_label.hide()
        self.proposal_type_combox.hide()
        self.proposal_number_ledit.hide()
        self.password_label.hide()
        self.proposal_password_ledit.hide()

    def setup_connections(self):
        self.loggedIn.connect(self.update_login_ui)

    def _do_login_as_proposal(
        self,
        proposal_code,
        proposal_number,
        proposal_password,
        beamline_name,
        impersonate=False,
    ):
        try:
            logging.getLogger("HWR").debug("ProposalBrick: querying ISPyB database...")
            prop = HWR.beamline.lims.get_proposal(proposal_code, proposal_number)

            if not prop or prop.get("status", {}).get("code") != "ok":
                logging.getLogger("HWR").error(
                    f"ProposalBrick: Login failed for proposal {proposal_code}-{proposal_number}."
                )
                self.set_ispyb_down()
                self.loggedIn.emit(False)
                return

            logging.getLogger("HWR").debug(
                f"ProposalBrick: proposal {proposal_code} {proposal_number} is valid."
            )
            self.select_proposal(prop)
            BaseWidget.set_status_info(
                "user", f"{proposal_code}{proposal_number}@{beamline_name}"
            )
            BaseWidget.set_status_info("ispyb", "ready")
            self.loggedIn.emit(True)

        except Exception as e:
            logging.getLogger("HWR").exception(
                f"ProposalBrick: Exception during login: {e}"
            )
            self.loggedIn.emit(False)
