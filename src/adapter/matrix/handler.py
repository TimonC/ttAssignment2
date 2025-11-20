import logging
import time
import http.client
import subprocess
from datetime import datetime
from generic.api import label_pb2
from generic.api.configuration import ConfigurationItem, Configuration
from generic.api.label import Label, Sort
from generic.api.parameter import Type, Parameter
from generic.handler import Handler as AbstractHandler

from ttAssignment1 import login_user, logout_user, register_user

PORT = 8008

class Handler(AbstractHandler):

    def __init__(self):
        super().__init__()
        self.adapter_core = None

    def send_message_to_amp(self, raw_message: str, parameters=None):
        logging.debug(f'response received: {raw_message}')

        if raw_message == 'RESET_PERFORMED':
            self._wait_for_synapse(PORT)
            status, _ = register_user(PORT, "Alice", "alice123")
            assert status==200
            self.adapter_core.send_ready()
        else:
            label = self._message2label(raw_message, parameters)
            self.adapter_core.send_response(label)

    def _wait_for_synapse(self, port, timeout=15):
        start = time.time()
        while True:
            try:
                conn = http.client.HTTPConnection("localhost", port, timeout=2)
                conn.request("GET", "/_matrix/client/versions")
                res = conn.getresponse()
                if res.status == 200:
                    return
                if time.time() - start > timeout:
                    raise RuntimeError(f"Synapse timeout")
            except Exception:
                if time.time() - start > timeout:
                    raise RuntimeError(f"Synapse timeout")
            time.sleep(0.5)

    def start(self):
        logging.info("Starting Handler")
        self._rebuild_synapse()
        self.send_message_to_amp("RESET_PERFORMED")

    def reset(self):
        logging.info('Resetting SUT')
        self._rebuild_synapse()
        self.send_message_to_amp("RESET_PERFORMED")

    def _rebuild_synapse(self):
        logging.info("Rebuilding Synapse")
        subprocess.run(["src/ttAssignment1/setup_homeserver.sh"], check=True)

    def stop(self):
        logging.info('Stopping Handler - FORCE')

    def stimulate(self, pb_label: label_pb2.Label):
        label = Label.decode(pb_label)
        sut_msg, response_parameters= self._label2message(label)

        pb_label.timestamp = time.time_ns()
        pb_label.physical_label = bytes(sut_msg, 'UTF-8')
        self.adapter_core.send_stimulus_confirmation(pb_label)

        logging.info(f'Injecting stimulus @SUT: {label.name}')
        self.send_message_to_amp(sut_msg, parameters=response_parameters)

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
            Label(Sort.RESPONSE, 'shut_off', 'synapse')
        ]

    def default_configuration(self) -> Configuration:
        return Configuration([ConfigurationItem(
            name='endpoint',
            tipe=Type.STRING,
            description='Base URL for Matrix API',
            value='http://localhost:8008'
        )])

    def _label2message(self, label: Label) -> tuple:
        """Returns (message_string, parameters_list)"""

        if label.name == 'login':
            username = label.parameters[0].value
            password = label.parameters[1].value
            status, response = login_user(PORT, username, password)

            if status == 200 and "access_token" in response:
                token = response["access_token"]
                # Return both message and parameters for logged_in response
                return "logged_in", [Parameter('session_token', Type.STRING, token)]
            elif status == 403:
                return "incorrect_login", None
            else:
                return "invalid_login", None

        elif label.name == 'logout':
            token = label.parameters[0].value
            status, _ = logout_user(PORT, token)
            if status == 200:
                return "logged_out", None
            else:
                return "invalid_logout", None

        elif label.name == 'register':
            username = label.parameters[0].value
            password = label.parameters[1].value
            status, _ = register_user(PORT, username, password)
            if status == 200:
                return "user_registered", None
            else:
                return "invalid_register", None

        return "shut_off", None

    def _message2label(self, message: str, parameters=None):
        return Label(
            sort=Sort.RESPONSE,
            name=message.lower(),
            parameters=parameters or [],
            channel='synapse',
            physical_label=bytes(message, 'UTF-8'),
            timestamp=datetime.now()
        )
