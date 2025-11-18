import logging
import time

from datetime import datetime

from generic.api import label_pb2
from generic.api.configuration import ConfigurationItem, Configuration
from generic.api.label import Label, Sort
from generic.api.parameter import Type, Parameter
from generic.handler import Handler as AbstractHandler
from matrix.matrix_connection import MatrixConnection

from src.ttAssignment1 import login_user, logout_user, send_message

def _response(name, channel='synapse', parameters=None):
    """ Helper method to create a response Label. """
    return Label(Sort.RESPONSE, name, channel, parameters=parameters)

def _stimulus(name, channel='synapse', parameters=None):
    """ Helper method to create a stimulus Label. """
    return Label(Sort.STIMULUS, name, channel, parameters=parameters)

class Handler(AbstractHandler):
    """
    This class handles the interaction between AMP and the Matrix SUT.
    """

    def __init__(self):
        super().__init__()
        self.sut = None
        self.adapter_core = None

    def send_message_to_amp(self, raw_message: str):
        """
        Send a message back to AMP. The message from the SUT needs to be converted to a Label.

        Args:
            raw_message (str): The message to send to AMP.
        """
        logging.debug('response received: {label}'.format(label=raw_message))

        if raw_message == 'RESET_PERFORMED':
            # After 'RESET_PERFORMED', the SUT is ready for a new test case.
            self.adapter_core.send_ready()
        else:
            label = self._message2label(raw_message)
            self.adapter_core.send_response(label)

    def start(self):
        """
        Start a test.
        """
        end_point = self.configuration.items[0].value
        self.sut = MatrixConnection(self, end_point)
        self.sut.connect()

    def reset(self):
        """
        Prepare the SUT for the next test case.
        """
        logging.info('Resetting the SUT for a new test case')
        # Just send RESET to MatrixConnection - it handles the actual reset
        self.sut.send('RESET')

    def stop(self):
        """
        Stop the SUT from testing.
        """
        logging.info('Stopping the plugin handler')
        self.sut.stop()
        self.sut = None

        logging.debug('Finished stopping the plugin handler')

    def stimulate(self, pb_label: label_pb2.Label):
        """
        Processes a stimulus of a given label at the SUT.

        Args:
            pb_label (label_pb2.Label): stimulus that the Axini Modeling Platform has sent
        """

        label = Label.decode(pb_label)
        sut_msg = self._label2message(label)

        # send confirmation of stimulus back to AMP
        pb_label.timestamp = time.time_ns()
        pb_label.physical_label = bytes(sut_msg, 'UTF-8')
        self.adapter_core.send_stimulus_confirmation(pb_label)

        # leading spaces are needed to justify the stimuli and responses
        logging.info('      Injecting stimulus @SUT: ?{name}'.format(name=label.name))
        self.sut.send(sut_msg)

    def supported_labels(self):
        """
        The labels supported by the adapter.
        """
        return [
            # Stimuli
            _stimulus('login', parameters=[
                Parameter('username', Type.STRING),
                Parameter('password', Type.STRING)
            ]),
            _stimulus('logout', parameters=[
                Parameter('session_token', Type.STRING)
            ]),
            _stimulus('send_message', parameters=[
                Parameter('session_token', Type.STRING),
                Parameter('room_id', Type.STRING),
                Parameter('message', Type.STRING)
            ]),

            # Responses
            _response('logged_in'),
            _response('logged_out'),
            _response('message_sent'),
            _response('invalid_command'),
            _response('invalid_token'),
            _response('invalid_username'),
            _response('invalid_password'),
            _response('incorrect_password'),
        ]

    def default_configuration(self) -> Configuration:
        return Configuration([
            ConfigurationItem(
                name='endpoint',
                tipe=Type.STRING,
                description='Base URL for the Matrix API',
                value='http://localhost:8008'
            ),
        ])

    # Label to Message Translation
    def _label2message(self, label: Label) -> str:
        """
        Converts a Label into an action on the Matrix client.
        Returns the SUT's response message string (to be converted into a Label).
        """
        # we expect that input URL is a string that ends in the 4 digits
        #   of the local host domain of the synapse homeserver
        host = self.configuration.items[0].value
        port = int(str(host)[-4:])

        if label.name == 'login':
            username = label.parameters[0].value
            password = label.parameters[1].value
            status, response = login_user(port, username, password)

            if status == 200 and "access_token" in response:
                self.access_token = response["access_token"]
                return "LOGGED_IN"
            elif status == 403:
                return "INCORRECT_PASSWORD"
            else:
                return "INVALID_PASSWORD"

        elif label.name == 'logout':
            token = label.parameters[0].value
            if not token:
                return "INVALID_TOKEN"

            status, _ = logout_user(port, token)
            if status == 200:
                self.access_token = None
                return "LOGGED_OUT"
            else:
                return "INVALID_TOKEN"

        elif label.name == 'send_message':
            token = label.parameters[0].value
            room_id = label.parameters[1].value
            message = label.parameters[2].value

            if not token:
                return "INVALID_TOKEN"

            status, _ = send_message(port, token, room_id, message)
            return "MESSAGE_SENT" if status == 200 else "INVALID_TOKEN"

        else:
            return "INVALID_COMMAND"


    def _message2label(self, message: str):
        """
        Converts a SUT message to a Protobuf Label.

        Args:
            message (str)
        Returns:
            Label: The converted message as a Label.
        """

        label_name = message.lower()
        label = Label(
            sort=Sort.RESPONSE,
            name=label_name,
            channel='synapse',
            physical_label=bytes(message, 'UTF-8'),
            timestamp=datetime.now())

        return label
