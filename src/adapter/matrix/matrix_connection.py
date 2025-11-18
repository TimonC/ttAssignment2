import logging
import threading
import subprocess

class MatrixConnection:
    """
    Handles the Matrix SUT via HTTP calls (Synapse homeservers) and exposes
    a clean interface to the Handler for sending stimuli and receiving responses.
    """

    def __init__(self, handler, endpoint):
        self.handler = handler
        self.endpoint = endpoint
        self.reset_lock = threading.Lock()

    def connect(self):
        """
        Prepare the SUT (rebuild homeservers) and signal ready.
        """
        logging.info("Connecting to Matrix SUT")
        try:
            self._rebuild_synapse_homeservers()
            self.handler.send_message_to_amp("RESET_PERFORMED")
            logging.info("Matrix SUT ready")
        except Exception as e:
            logging.error(f"Failed to connect to Matrix SUT: {e}")
            self.handler.send_message_to_amp("RESET_FAILED")

    def _rebuild_synapse_homeservers(self):
        """
        Rebuild the Synapse homeservers via the setup script.
        Thread-safe to allow concurrent RESET calls.
        """
        with self.reset_lock:
            logging.info("Rebuilding Synapse homeservers")
            try:
                subprocess.run(["src/ttAssignment1/setup_homeservers.sh"], check=True)
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Setup script failed: {e}")

    def send(self, message: str):
        """
        Send a message/stimulus to the SUT.
        If 'RESET', rebuild homeservers asynchronously.
        Otherwise, directly send it to the handler via HTTP.
        """
        if message.upper() == "RESET":
            logging.info("RESET received: rebuilding Synapse")
            reset_thread = threading.Thread(target=self._handle_reset)
            reset_thread.daemon = True
            reset_thread.start()
        else:
            # This triggers your Handler's logic: convert message → HTTP → Synapse
            try:
                logging.debug(f"Sending message to SUT: {message}")
                self.handler.send_message_to_amp(message)
            except Exception as e:
                logging.error(f"Failed to send message to SUT: {e}")

    def _handle_reset(self):
        """
        Thread-safe RESET handling.
        """
        try:
            self._rebuild_synapse_homeservers()
            self.handler.send_message_to_amp("RESET_PERFORMED")
            logging.info("RESET completed successfully")
        except Exception as e:
            logging.error(f"RESET failed: {e}")
            self.handler.send_message_to_amp("RESET_FAILED")

    def stop(self):
        """
        Clean-up if needed. Clears handler state to avoid test contamination.
        """
        logging.info("Stopping MatrixConnection")
        if hasattr(self.handler, 'access_token'):
            self.handler.access_token = None
        if hasattr(self.handler, 'room_id'):
            self.handler.room_id = None
        if hasattr(self.handler, 'handler_state'):
            self.handler.handler_state = None

        logging.info("MatrixConnection stopped cleanly")
