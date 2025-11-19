import logging
import time
import http.client
from datetime import datetime

from generic.api import label_pb2
from generic.api.configuration import ConfigurationItem, Configuration
from generic.api.label import Label, Sort
from generic.api.parameter import Type, Parameter
from generic.handler import Handler as AbstractHandler
from matrix.matrix_connection import MatrixConnection

from ttAssignment1 import login_user, logout_user, register_user

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
        """
        logging.debug('response received: {label}'.format(label=raw_message))

        if raw_message == 'RESET_PERFORMED':
            # After 'RESET_PERFORMED', initialize test environment and then signal ready
            try:
                self._wait_for_synapse(8008)
                self._wait_for_synapse(8009)
                self._initialize_test_environment()
                logging.info('Test environment initialized successfully')
            except Exception as e:
                logging.error(f"Test environment initialization failed: {e}")
                # You might want to send a different signal here for failure
            finally:
                # Signal AMP that we're ready for the next test case
                self.adapter_core.send_ready()
        else:
            label = self._message2label(raw_message)
            self.adapter_core.send_response(label)

    def _wait_for_synapse(self, port, timeout=15):
        """
        Wait until the Synapse server at localhost:port responds to HTTP requests.
        """
        start = time.time()
        while True:
            try:
                conn = http.client.HTTPConnection("localhost", port, timeout=2)
                conn.request("GET", "/_matrix/client/versions")
                res = conn.getresponse()
                if res.status == 200:
                    return True
            except Exception:
                pass
            if time.time() - start > timeout:
                raise RuntimeError(f"Synapse at port {port} did not become ready within {timeout}s")
            time.sleep(0.5)

    def _initialize_test_environment(self):
        """
        Initialize test users and room after reset.
        """
        try:
            # Register two test users
            status, user1 = register_user(8008, "Alice", "alice123")
            assert status == 200, f"User1 registration failed: {status}"
            # status, user2 = register_user(8009, "Bob", "bob123")
            # assert status == 200, f"User2 registration failed: {status}"

            # User2 creates room and invites user1
            # status, room = create_room(8009, user2["access_token"], name="group10_test_room")
            # room_id = room["room_id"]
            # invite_user(8009, user2["access_token"], room_id, user1["user_id"])
            # join_room(8008, user1["access_token"], room_id)
            # assert status == 200, f"Room creation failed: {status}"

            logging.info(f'Test environment initialized: registered user "Alice" with password "alice123"')
            # logging.info(f'Test environment initialized: users registered, room created: {room["room_id"]}')

        except Exception as e:
            logging.error(f"Failed to initialize test environment: {e}")
            raise

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
            _stimulus('register', parameters=[
                Parameter('username', Type.STRING),
                Parameter('password', Type.STRING)
            ]),
            _stimulus('login', parameters=[
                Parameter('username', Type.STRING),
                Parameter('password', Type.STRING)
            ]),
            _stimulus('logout', parameters=[
                Parameter('session_token', Type.STRING)
            ]),
            # _stimulus('send_message', parameters=[
            #     Parameter('session_token', Type.STRING),
            #     Parameter('room_id', Type.STRING),
            #     Parameter('message', Type.STRING)
            # ]),
            _stimulus('reset'),

            _response('user_registered'),
            _response('logged_in'),
            _response('logged_out'),
            # _response('message_sent'),
            _response('invalid_command'),
            _response('invalid_token'),
            _response('invalid_username'),
            _response('invalid_password'),
            _response('incorrect_password'),
            _response('shut_off'),
        ]

    def default_configuration(self) -> Configuration:
        """
        The default configuration of this adapter.

        Returns:
            Configuration: the default configuration required by this adapter.
        """
        return Configuration([ConfigurationItem(\
            name='endpoint',
            tipe=Type.STRING,
            description='Base websocket URL of the mock client for the Client-Server Matrix API',
                value = 'http://localhost:8008'
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

        elif label.name == 'register':
            username = label.parameters[0].value
            password = label.parameters[1].value
            status, _ = register_user(port, username, password)
            if status == 200:
                return "USER_REGISTERED"
            elif status == 403:
                return "INCORRECT_PASSWORD"
            else:
                return "INVALID_PASSWORD"



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
