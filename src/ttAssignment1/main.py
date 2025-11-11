from mock_client import *
import sys

port1 = 8008
port2 = 8009
password = "0000"

    ### wrappers for mock client functions for easier use
def ep_registration(x):
    return register_user(port1, x, password)
def ep_login(x):
    return login_user(port1, x, password)
def main_send_message(sender_token, receiver_token, room_id, msg):
    return send_message(port1, sender_token, room_id, msg), get_room_messages(port1, receiver_token, room_id, limit=5)

if __name__ == "__main__":
    try:
        sys.stdout = open("test_result_log.txt", "w")
        
        # ------------------------------------------------------------
        # 6 EP tests for registration
        # ------------------------------------------------------------

        # (2,5,7): not string
        x = 1234
        status, res = ep_registration(x)
        assert status == 400
        assert res["error"] == 'Invalid username'
        print("   > registration test 1 passed (non-string input)")

        # (1,3,5,7): valid unique username
        x = unique_username(port1)
        status, res = ep_registration(x)
        assert status == 200
        print("   > registration test 2 passed (valid username)")

        # (1,4,5,7): invalid char
        x = x + "$"
        status, res = ep_registration(x)
        assert status == 400
        assert res["error"] == "User ID can only contain characters a-z, 0-9, or '=_-./+'"
        print("   > registration test 3 passed (invalid character)")

        # (1,5,8): empty string
        x = ""
        status, res = ep_registration(x)
        assert status == 400
        assert res["error"] == 'User ID cannot be empty'
        print("   > registration test 4 passed (empty username)")
    
         # (6): None
        x = None
        status, res = ep_registration(x)
        assert status == 400
        assert "Invalid username" in res["error"]
        print("   > registration test 5 passed (None as username)")

        # (1,3,5,9): >255 chars
        x = "a" * 256
        status, res = ep_registration(x)
        assert status == 400
        assert res["error"] == 'User ID may not be longer than 255 characters'
        print("   > registration test 6 passed (too long username)")

        print("All 6 registration API tests passed!\n")

        # ------------------------------------------------------------
        # 4 EP tests for login
        # ------------------------------------------------------------   
             
        username = "alice"
        if not check_user_exists(port1, username):
            register_user(port1, username, password)

        # (2,5): not string
        x = 1234
        status, res= ep_login(x)
        assert status == 500
        assert res["error"] == 'Internal server error'
        print("   > login test 1 passed (non-string input)")

        # (1,3,5): valid username
        x = "alice"
        status, res = ep_login(x)
        assert status == 200
        print("   > login test 2 passed (valid user)")

        # (1,4,5): valid format, unregistered
        x = unique_username(port1)
        status, res = ep_login(x)
        assert status == 403
        assert res["error"] == 'Invalid username or password'
        print("   > login test 3 passed (unregistered user)")

        # (6): None
        x = None
        status, res = ep_login(x)
        assert status == 400
        assert res["error"] == "User identifier is missing 'user' key"
        print("   > login test 4 passed (None as username)")

        print("All 4 login API tests passed!\n")

        # ------------------------------------------------------------
        # 2 tests for messaging
        # ------------------------------------------------------------

        # create two valid users
        status, user1 = register_user(port1, unique_username(port1), password)
        assert status == 200
        status, user2 = register_user(port1, unique_username(port1), password)
        assert status == 200

        # user1 creates room and invites user2
        status, room = create_room(port1, user1["access_token"], name="ep_test_room")
        room_id = room["room_id"]
        invite_user(port1, user1["access_token"], room_id, user2["user_id"])
        join_room(port1, user2["access_token"], room_id)

        # case 1: user1 sends message -> user2 receives
        msg1 = "Hello from user1!"
        send_res, recv_res = main_send_message(user1["access_token"], user2["access_token"], room_id, msg1)
        assert 200 in send_res
        assert 200 in recv_res
        print("  > messaging test 1 passed (user1→user2)")

        # case 2: user2 sends message -> user1 receives
        msg2 = "Hello back from user2!"
        send_res, recv_res = main_send_message(user2["access_token"], user1["access_token"], room_id, msg2)
        assert 200 in send_res
        assert 200 in recv_res
        print("  > messaging test 2 passed (user2→user1)")

        print("All messaging tests passed!")

    ###Print results from log file
    finally:
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        print(open("test_result_log.txt").read())
