import logging
import time
import http.client
import threading
import subprocess
from datetime import datetime

from generic.api import label_pb2
from generic.api.configuration import ConfigurationItem, Configuration
from generic.api.label import Label, Sort
from generic.api.parameter import Type, Parameter
from generic.handler import Handler as AbstractHandler

from ttAssignment1 import login_user, logout_user, register_user


class Handler(AbstractHandler):

    def __init__(self):
        super().__init__()
        self.adapter_core = None

    async def send_message_to_amp(self, raw_message: str, parameters=None):
        logging.debug(f'response received: {raw_message}')

        if raw_message == 'RESET_PERFORMED':
            self._wait_for_synapse(8008)
            self._initialize_test_environment()
            self.adapter_core.send_ready()
        else:
            label = self._message2label(raw_message, parameters)
            self.adapter_core.send_response(label)

    def _wait_for_synapse(self, port, timeout=15):
        start = time.time()
        while True:
            conn = http.client.HTTPConnection("localhost", port, timeout=2)
            conn.request("GET", "/_matrix/client/versions")
            res = conn.getresponse()
            if res.status == 200:
                return
            if time.time() - start > timeout:
                raise RuntimeError(f"Synapse timeout")
            time.sleep(0.5)

    def _initialize_test_environment(self):
        status, user1 = register_user(8008, "Alice", "alice123")
        assert status == 200
        logging.info('Test environment initialized: Alice registered')

    def start(self):
        logging.info("Starting Handler")
        self._rebuild_synapse()
        self.send_message_to_amp("RESET_PERFORMED")

    def reset(self):
        logging.info('Resetting SUT')
        reset_thread = threading.Thread(target=self._handle_reset)
        reset_thread.daemon = True
        reset_thread.start()

    def _handle_reset(self):
        self._rebuild_synapse()
        self.send_message_to_amp("RESET_PERFORMED")

    def _rebuild_synapse(self):
        logging.info("Rebuilding Synapse")
        subprocess.run(["src/ttAssignment1/setup_homeservers.sh"], check=True)

    def stop(self):
        logging.info('Stopping Handler')

    async def stimulate(self, pb_label: label_pb2.Label):
        label = Label.decode(pb_label)
        sut_msg = self._label2message(label)

        pb_label.timestamp = time.time_ns()
        pb_label.physical_label = bytes(sut_msg, 'UTF-8')
        self.adapter_core.send_stimulus_confirmation(pb_label)

        logging.info(f'      Injecting stimulus @SUT: ?{label.name}')
        self.send_message_to_amp(sut_msg)

    def supported_labels(self):
        return [
            Label(Sort.STIMULUS, 'reset', 'synapse'),
            Label(Sort.STIMULUS, 'register', 'synapse', parameters=[
                Parameter('username', Type.STRING),
                Parameter('password', Type.STRING)
            ]),
            Label(Sort.STIMULUS, 'login', 'synapse', parameters=[
                Parameter('username', Type.STRING),
                Parameter('password', Type.STRING)
            ]),
            Label(Sort.STIMULUS, 'logout', 'synapse', parameters=[
                Parameter('session_token', Type.STRING)
            ]),
            Label(Sort.RESPONSE, 'logged_in', 'synapse', parameters=[
                Parameter('session_token', Type.STRING)
            ]),
            Label(Sort.RESPONSE, 'user_registered', 'synapse'),
            Label(Sort.RESPONSE, 'logged_out', 'synapse'),
            Label(Sort.RESPONSE, 'incorrect_login', 'synapse'),
            Label(Sort.RESPONSE, 'invalid_register', 'synapse'),
            Label(Sort.RESPONSE, 'invalid_login', 'synapse'),
            Label(Sort.RESPONSE, 'invalid_logout', 'synapse'),
            Label(Sort.RESPONSE, 'shut_off', 'synapse'),
        ]

    def default_configuration(self) -> Configuration:
        return Configuration([ConfigurationItem(
            name='endpoint',
            tipe=Type.STRING,
            description='Base websocket URL of the mock client for the Client-Server Matrix API',
            value='http://localhost:8008'
        )])

    def _label2message(self, label: Label) -> str:
        host = self.configuration.items[0].value
        port = int(str(host)[-4:])

        if label.name == 'login':
            username = label.parameters[0].value
            password = label.parameters[1].value
            status, response = login_user(port, username, password)

            if status == 200 and "access_token" in response:
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

        return "INVALID_COMMAND"

    def _message2label(self, message: str, parameters=None):
        label_name = message.lower()
        if parameters:
            return Label(
                sort=Sort.RESPONSE,
                name=label_name,
                parameters=parameters,
                channel='synapse',
                physical_label=bytes(message, 'UTF-8'),
                timestamp=datetime.now()
            )
        return Label(
            sort=Sort.RESPONSE,
            name=label_name,
            channel='synapse',
            physical_label=bytes(message, 'UTF-8'),
            timestamp=datetime.now()
        )
