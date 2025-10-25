from message_format import MessageFormat

class Protocols:
    class ConnectionToLobby:
        HANDSHAKE = MessageFormat({
            "connection_type": str
        })
        """
        connection_type: 'client', 'database_server', or 'game_server'
        """

    class LobbyToConnection:
        HANDSHAKE_RESPONSE = MessageFormat({
            "result": str,
            "message": str
        })
        """
        result: 'confirmed' or 'error' \n
        message: additional information
        """

    class LobbyToDB:
        REQUEST = MessageFormat({
            "request_id": str,
            "collection": str,
            "action": str,
            "data": dict
        })
        """
        request_id: unique identifier for the request \n
        collection: e.g., 'user', 'room', 'gamelog' \n
        action: e.g., 'create', 'read', 'update', 'delete', 'query'\n
        data: additional data as a dictionary
        """

    class DBToLobby:
        RESPONSE = MessageFormat({
            "responding_request_id": str,
            "result": str,
            "data": dict
        })
        """
        responding_request_id: the request_id this response is for \n
        result: 'success' or 'failure' \n
        data: additional data as a dictionary
        """

    class ClientToLobby:
        COMMAND = MessageFormat({
            "command": str,
            "params": dict
        })
        """
        command: e.g., 'login', 'register', 'create_room', etc. \n
        params: additional parameters as a dictionary
        """
    
    class LobbyToClient:
        MESSAGE = MessageFormat({
            "message_type": str,
            "responding_command": str,
            "event_type": str,
            "result": str,
            "data": dict
        })
        """
        message_type: 'response' or 'event' \n
        responding_command: the command this message is responding to (for responses) \n
        event_type: type of event (for events) \n
        result: 'success', 'failure', etc. (for responses) \n
        data: additional data as a dictionary
        """

class Words:
    class Collection:
        USER = "user"
        ROOM = "room"
        GAMELOG = "gamelog"
    class Action:
        CREATE = "create"
        READ = "read"
        UPDATE = "update"
        DELETE = "delete"
        QUERY = "query"
        ADD_USER = "add_user"
        REMOVE_USER = "remove_user"
    class Command:
        EXIT = "exit"
        CHECK_USERNAME = "check_username" # Check if a username is available to register
        REGISTER = "register"
        LOGIN = "login"
        LOGOUT = "logout"
        CREATE_ROOM = "create_room"
        JOIN_ROOM = "join_room"
        LEAVE_ROOM = "leave_room"
        DISBAND_ROOM = "disband_room"
        INVITE_PLAYER = "invite_player"
        ACCEPT_INVITE = "accept_invite"
        DECLINE_INVITE = "decline_invite"
        START_GAME = "start_game"
    class Result:
        SUCCESS = "success"
        FAILURE = "failure"
        FOUND = "found"
        NOT_FOUND = "not_found"
        ERROR = "error"
        VALID = "valid"
        INVALID = "invalid"
        CONFIRMED = "confirmed"
    class DataParamKey:
        USERNAME = "username"
        PASSWORD = "password"
        ROOM_ID = "room_id"
        PLAYERS = "players"
        GAME_STATE = "game_state"
        SCORE = "score"
        MESSAGE = "message"
        TIMESTAMP = "timestamp"
        DETAILS = "details"
        REASON = "reason"
        GAMES_PLAYED = "games_played"
        GAMES_WON = "games_won"
        ONLINE = "online"
        CURRENT_ROOM_ID = "current_room_id"
    class Reason:
        INVALID_CREDENTIALS = "invalid_credentials"
        ROOM_FULL = "room_full"
        GAME_ALREADY_STARTED = "game_already_started"
        ACCOUNT_USING = "account_using"
    class Message:
        WELCOME_USER = "welcome_user"
    class MessageType:
        RESPONSE = "response"
        EVENT = "event"
    class EventType:
        USER_JOINED = "user_joined"
        USER_LEFT = "user_left"
        ROOM_DISBANDED = "room_disbanded"
        INVITE_RECEIVED = "invite_received"
        GAME_STARTED = "game_started"
        SERVER_SHUTDOWN = "server_shutdown"
    class ConnectionType:
        CLIENT = "client"
        DATABASE_SERVER = "database_server"
        GAME_SERVER = "game_server"
