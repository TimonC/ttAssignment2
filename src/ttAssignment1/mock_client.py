import http.client
import json
import uuid
import random

HOST = "localhost"
BASE_PATH = "/_matrix/client/v3"


#-----------------------------------------------------------------------------#

def _send_request(port, method, path, body=None, headers=None):
    """ internal helper to send HTTP requests """
    conn = http.client.HTTPConnection(HOST, port)
    payload = json.dumps(body) if body else None
    headers = headers or {"Content-Type": "application/json"}
    conn.request(method, path, payload, headers)
    res = conn.getresponse()
    data = res.read()
    conn.close()

    return res.status, json.loads(data)

def random_string(length=20):
    """generate a random lowercase string for temporary usernames or passwords"""
    letters = "abcdefghijklmnopqrstuvwxyz"
    return "".join(random.choice(letters) for _ in range(length))


def unique_username(port):
    username = random_string()
    while (check_user_exists(port, username)):
        username = random_string()
    return username
#---------------------- authentication API -------------------------------------#

def register_user(port, username, password):
    """
    register a new Matrix user using dummy authentication
    """
    payload = {
        "auth": {"type": "m.login.dummy"},
        "username": username,
        "password": password,
        "refresh_token": True
    }
    return _send_request(port, "POST", f"{BASE_PATH}/register", payload)


def login_user(port, username, password):
    """
    log in with username/password.
    """
    payload = {
        "type": "m.login.password",
        "identifier": {
            "type": "m.id.user",
            "user": username
        },
        "password": password,
        "refresh_token": True
    }
    return _send_request(port, "POST", f"{BASE_PATH}/login", payload)


def refresh_token(port, refresh_token):
    """
    refresh an access token.
    """
    payload = {"refresh_token": refresh_token}
    return _send_request(port, "POST", f"{BASE_PATH}/refresh", payload)


def logout_user(port, access_token):
    """
    log out the current session.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    return _send_request(port, "POST", f"{BASE_PATH}/logout", headers=headers)


def check_user_exists(port: int, username: str):
    conn = http.client.HTTPConnection(host=HOST, port=port)
    path = f"{BASE_PATH}/register/available?username={username}"
    conn.request("GET", path)
    res = conn.getresponse()
    return res.status!= 200

#------------------------ sync API -----------------------------------------#

def get_sync(port, access_token, since=None, full_state=False):
    """
    perform a /sync call to fetch rooms and messages.
    """
    path = f"{BASE_PATH}/sync?timeout=0"
    if since:
        path += f"&since={since}"
    if full_state:
        path += "&full_state=true"

    headers = {"Authorization": f"Bearer {access_token}"}
    return _send_request(port, "GET", path, headers=headers)


#------------------------------- rooms -------------------------------------#

def create_room(port, access_token, name=None, topic=None, preset="public_chat", invite=None):
    """
    create a new room
    """
    payload = {
        "preset": preset
    }
    if name:
        payload["name"] = name
    if topic:
        payload["topic"] = topic
    if invite:
        payload["invite"] = invite if isinstance(invite, list) else [invite]

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    return _send_request(port, "POST", f"{BASE_PATH}/createRoom", payload, headers)


def join_room(port, access_token, room_id_or_alias):
    """
    join a room by ID or alias
    """
    path = f"{BASE_PATH}/join/{room_id_or_alias}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    return _send_request(port, "POST", path, headers=headers)


def leave_room(port, access_token, room_id):
    """
    leave a room
    """
    path = f"{BASE_PATH}/rooms/{room_id}/leave"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    return _send_request(port, "POST", path, headers=headers)


def invite_user(port, access_token, room_id, user_id):
    """
    invite another user to a room
    """
    payload = {"user_id": user_id}
    path = f"{BASE_PATH}/rooms/{room_id}/invite"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    return _send_request(port, "POST", path, payload, headers)


def list_rooms(port, access_token):
    """
    list rooms the user has joined.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    return _send_request(port, "GET", f"{BASE_PATH}/joined_rooms", headers=headers)


def get_room_messages(port, access_token, room_id, limit=10, dir="b"):
    """
    retrieve messages from a room’s timeline.
    dir = 'b' (backwards) or 'f' (forwards)
    """
    path = f"{BASE_PATH}/rooms/{room_id}/messages?limit={limit}&dir={dir}"
    headers = {"Authorization": f"Bearer {access_token}"}
    return _send_request(port, "GET", path, headers=headers)



#---------------------- messaging API -------------------------------------#

def send_message(port, access_token, room_id, message):
    """
    send a message event to a room.
    """
    txn_id = str(uuid.uuid4())
    path = f"{BASE_PATH}/rooms/{room_id}/send/m.room.message/{txn_id}"

    payload = {
        "msgtype": "m.text",
        "body": message
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    return _send_request(port, "PUT", path, payload, headers)
