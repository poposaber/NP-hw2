from message_format import MessageFormat

class Protocols:
    class LobbyToDB:
        COMMAND = MessageFormat({
            "collection": str,
            "action": str,
            "data": dict
        })
    class ClientToLobby:
        COMMAND = MessageFormat({
            "command": str,
            "params": dict
        })
    class LobbyToClient:
        RESPONSE = MessageFormat({
            "response_to": str,
            "result": str,
            "data": dict
        })

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
    class Command:
        LOGIN = "login"
        LOGOUT = "logout"
        CREATE_ROOM = "create_room"
        JOIN_ROOM = "join_room"
        LEAVE_ROOM = "leave_room"
        START_GAME = "start_game"
    class Result:
        SUCCESS = "success"
        FAILURE = "failure"
        NOT_FOUND = "not_found"
        ERROR = "error"
        INVALID = "invalid"
    class DataKey:
        USERNAME = "username"
        PASSWORD = "password"
        ROOM_ID = "room_id"
        ROOM_NAME = "room_name"
        PLAYERS = "players"
        GAME_STATE = "game_state"
        SCORE = "score"
        MESSAGE = "message"
        TIMESTAMP = "timestamp"
        DETAILS = "details"
        REASON = "reason"
    class Reason:
        INVALID_CREDENTIALS = "invalid_credentials"
        ROOM_FULL = "room_full"
        GAME_ALREADY_STARTED = "game_already_started"
        ACCOUNT_USING = "account_using"