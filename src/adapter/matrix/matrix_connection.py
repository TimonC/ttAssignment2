import logging
import threading
import websocket
import http.client
import time
import subprocess

HOST = "localhost"

class MatrixConnection:
    """
    This class handles the connection, sending and receiving of messages to the SmartDoor SUT
    """

    def __init__(self, handler, endpoint):
        self.handler = handler
        self.endpoint = endpoint
        self.websocket = None
        self.wst = None

    def connect(self):
        """
        Connect to the SmartDoor SUT.
        """
        logging.info('Connecting to Matrix')
        self.websocket = websocket.WebSocketApp(
            self.endpoint,
            on_open=lambda _: self.on_open(),
            on_close=lambda _, close_status_code, close_msg: self.on_close(),
            on_message=lambda _, msg: self.on_message(msg),
            on_error=lambda _, msg: self.on_error(msg)
        )
        self.wst = threading.Thread(target=self.websocket.run_forever)
        self.wst.daemon = True
        self.wst.start()

    def _wait_for_synapse_ready(self, ports=(8008, 8009), timeout=30):
        """
        Wait for Synapse to be responsive by checking health endpoint.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                conn = http.client.HTTPConnection(HOST, ports[0], timeout=5)
                conn.request("GET", "/health")
                resp1 = conn.getresponse().status
                conn.close()

                conn = http.client.HTTPConnection(HOST, ports[1], timeout=5)
                conn.request("GET", "/health")
                resp2 = conn.getresponse().status
                conn.close()

                if resp1 == 200 and resp2 == 200:
                    logging.info('Synapse is ready')
                    return
            except (ConnectionRefusedError, TimeoutError, OSError):
                pass
            time.sleep(1)
        raise Exception(f"Synapse failed to start within {timeout} seconds")

    def _rebuild_synapse_homeservers(self):
        """
        Rebuild Synapse homeserver using the setup script.
        """
        logging.info('Rebuilding Synapse')
        subprocess.run(["../ttAssignment1/setup_homeserver.sh"], check=True)
        self._wait_for_synapse_ready()

    def send(self, message):
        """
        Send a message to the SUT.
        """
        if message == 'RESET':
            logging.debug('RESET received, rebuilding Synapse')
            reset_thread = threading.Thread(target=self._handle_reset)
            reset_thread.daemon = True
            reset_thread.start()
        else:
            logging.debug(f'Sending message to SUT: {message}')
            self.websocket.send(message)

    def _handle_reset(self):
        """
        Handle RESET through a mock script.
        """
        try:
            self._rebuild_synapse_homeservers()
            self.handler.send_message_to_amp('RESET_PERFORMED')
            logging.info('Reset completed successfully')
        except Exception as e:
            logging.error(f"Reset failed: {e}")
            self.handler.send_message_to_amp('RESET_FAILED')

    def on_open(self):
        """
        Callback that is called when the socket to the SUT is opened.
        """
        logging.info('Connected to SUT')
        self.send('RESET')

    def on_close(self):
        """
        Callback that is called when the socket is closed.
        """
        logging.debug('Closed connection to SUT')

    def on_message(self, msg):
        """
        Callback that is called when the SUT sends a message.
        """
        logging.debug(f'Received message from SUT: {msg}')
        self.handler.send_message_to_amp(msg)

    def on_error(self, msg):
        """
        Callback that is called when something is wrong with the websocket connection
        """
        logging.error(f"Error with connection to SUT: {msg}")

    def stop(self):
        """
        Perform any cleanup if the SUT is closed.
        """
        if self.websocket:
            self.websocket.close()
            self.websocket.keep_running = False
            self.wst.join()
            self.wst = None
