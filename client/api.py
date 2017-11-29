import time




API_URL = "http://werewolves.api-d.com:8000/"
API_VERSION = "v1"
COMPLETE_API_URL = API_URL + API_VERSION + "/"
AUTH = None

import requests
from requests.auth import HTTPBasicAuth


import logging
import platform


## LOGGER ##


class _AnsiColorStreamHandler(logging.StreamHandler):
    DEFAULT = '\x1b[0m'
    RED = '\x1b[31m'
    GREEN = '\x1b[32m'
    YELLOW = '\x1b[33m'
    CYAN = '\x1b[36m'

    CRITICAL = RED
    ERROR = RED
    WARNING = YELLOW
    INFO = GREEN
    DEBUG = CYAN

    @classmethod
    def _get_color(cls, level):
        if level >= logging.CRITICAL:
            return cls.CRITICAL
        elif level >= logging.ERROR:
            return cls.ERROR
        elif level >= logging.WARNING:
            return cls.WARNING
        elif level >= logging.INFO:
            return cls.INFO
        elif level >= logging.DEBUG:
            return cls.DEBUG
        else:
            return cls.DEFAULT

    def __init__(self, stream=None):
        logging.StreamHandler.__init__(self, stream)

    def format(self, record):
        text = logging.StreamHandler.format(self, record)
        color = self._get_color(record.levelno)
        return color + text + self.DEFAULT


class _WinColorStreamHandler(logging.StreamHandler):
    # wincon.h
    FOREGROUND_BLACK = 0x0000
    FOREGROUND_BLUE = 0x0001
    FOREGROUND_GREEN = 0x0002
    FOREGROUND_CYAN = 0x0003
    FOREGROUND_RED = 0x0004
    FOREGROUND_MAGENTA = 0x0005
    FOREGROUND_YELLOW = 0x0006
    FOREGROUND_GREY = 0x0007
    FOREGROUND_INTENSITY = 0x0008  # foreground color is intensified.
    FOREGROUND_WHITE = FOREGROUND_BLUE | FOREGROUND_GREEN | FOREGROUND_RED

    BACKGROUND_BLACK = 0x0000
    BACKGROUND_BLUE = 0x0010
    BACKGROUND_GREEN = 0x0020
    BACKGROUND_CYAN = 0x0030
    BACKGROUND_RED = 0x0040
    BACKGROUND_MAGENTA = 0x0050
    BACKGROUND_YELLOW = 0x0060
    BACKGROUND_GREY = 0x0070
    BACKGROUND_INTENSITY = 0x0080  # background color is intensified.

    DEFAULT = FOREGROUND_WHITE
    CRITICAL = BACKGROUND_YELLOW | FOREGROUND_RED | FOREGROUND_INTENSITY | BACKGROUND_INTENSITY
    ERROR = FOREGROUND_RED | FOREGROUND_INTENSITY
    WARNING = FOREGROUND_YELLOW | FOREGROUND_INTENSITY
    INFO = FOREGROUND_GREEN
    DEBUG = FOREGROUND_CYAN

    @classmethod
    def _get_color(cls, level):
        if level >= logging.CRITICAL:
            return cls.CRITICAL
        elif level >= logging.ERROR:
            return cls.ERROR
        elif level >= logging.WARNING:
            return cls.WARNING
        elif level >= logging.INFO:
            return cls.INFO
        elif level >= logging.DEBUG:
            return cls.DEBUG
        else:
            return cls.DEFAULT

    def _set_color(self, code):
        import ctypes
        ctypes.windll.kernel32.SetConsoleTextAttribute(self._outhdl, code)

    def __init__(self, stream=None):
        logging.StreamHandler.__init__(self, stream)
        # get file handle for the stream
        import ctypes, ctypes.util
        # for some reason find_msvcrt() sometimes doesn't find msvcrt.dll on my system?
        crtname = ctypes.util.find_msvcrt()
        if not crtname:
            crtname = ctypes.util.find_library("msvcrt")
        crtlib = ctypes.cdll.LoadLibrary(crtname)
        self._outhdl = crtlib._get_osfhandle(self.stream.fileno())

    def emit(self, record):
        color = self._get_color(record.levelno)
        self._set_color(color)
        logging.StreamHandler.emit(self, record)
        self._set_color(self.FOREGROUND_WHITE)


# select ColorStreamHandler based on platform

if platform.system() == 'Windows':
    ColorStreamHandler = _WinColorStreamHandler
else:
    ColorStreamHandler = _AnsiColorStreamHandler


class Api:
    def __init__(self, name):
        self.authed = False

        logger = logging.getLogger("werewolves")
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s :: %(levelname)s :: [%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s')

        steam_handler = ColorStreamHandler()
        #steam_handler.setLevel(logging.DEBUG)
        steam_handler.setLevel(logging.INFO)

        steam_handler.setFormatter(formatter)
        logger.addHandler(steam_handler)

        self.logger = logger

        login_resp = self.call_api("login", {"name" : name}).json()
        self.uuid = login_resp["uuid"]
        self.token = login_resp["token"]
        self.authed = True
        self.players_cache = {}
        self.games_cache = {}
        self.me = self.get_player(self.uuid, force_update=True)


    def call_api(self, path, data):
        """
        Appelle l'api comme définie.

        Exemple :
            call_api("login", {"name":name})

        """
        url = COMPLETE_API_URL + path
        self.logger.debug(f"-> {url} || {data}")

        time_start = time.time()

        if self.authed:
            res = requests.post(url, data, auth=HTTPBasicAuth(self.uuid, self.token))
        else:
            res = requests.post(url, data)

        time_stop = time.time()
        js = res.json()
        self.logger.debug(f"<- {url} || ({res.status_code}) {js}")
        total_time = time_stop-time_start

        self.logger.debug(f"Took {total_time} to get res from API")

        if type(js) == dict and "errors" in js.keys():
            raise Exception(str(js["errors"]))

        return res

    def get_player(self, uuid, force_update = False):
        if force_update or uuid not in self.players_cache.keys() or (uuid in self.players_cache.keys() and self.players_cache[uuid].last_update + 120 < time.time()):
            pl = self.call_api("player_status", {"uuid": uuid}).json()
            player = Player(pl, api=self)
            self.players_cache[uuid] = player
            return player
        else:
            return self.players_cache[uuid]

    def get_game(self, uuid, force_update = False):
        if force_update or uuid not in self.games_cache.keys() or (uuid in self.games_cache.keys() and self.games_cache[uuid].last_update + 120 < time.time()):
            gm = self.call_api("game_status", {"uuid": uuid}).json()
            game = Game(gm, api=self)
            self.players_cache[uuid] = game
            return game
        else:
            return self.games_cache[uuid]

    def create_game(self, name):
        resp = self.call_api("create_game", {"name": name}).json()
        return self.get_game(resp)

    def join_game(self, game):
        self.call_api("join_game", {"uuid": game.uuid}).json()
        return self.get_game(game.uuid)

    def leave_game(self, game):
        self.call_api("leave_game", {"uuid": game.uuid})

    def start_game(self, game):
        self.call_api("start_game", {"uuid": game.uuid})

    def select_player(self, game, players:list):
        csp = ""
        for uuid in [p.uuid for p in players]:
            csp += uuid + ","

        csp = csp[:-1]
        self.call_api("select_player", {"game_uuid": game.uuid, "players_uuid": csp})

    def sorceress_select(self, game, player, save):
        if save:
            save_or_kill = "y"
        else:
            save_or_kill = ""

        self.call_api("sorceress_select", {"game_uuid": game.uuid, "player_uuid": player.uuid, "save_or_kill": save_or_kill})

    def list_games(self):
        games_uuid = self.call_api("list_games", {}).json()
        games = []
        for game in games_uuid:
            games.append(self.get_game(game))
        return games


class Player:
    def __init__(self, player_dict, api):
        self.data = player_dict
        self.data["api"] = api
        self.data["last_update"] = time.time()

    def __getattr__(self, item):

        if item == "games" or "games_created":
            self.load_games()

        return self.data[item]

    def load_games(self):
        ng = []
        for game in self.data["games"][:]:
            if not isinstance(game, Game):
                ng.append(self.data["api"].get_game(game, force_update=False))
            else:
                ng.append(game)

        self.data["games"] = ng

        ng = []
        for game in self.data["games_created"][:]:
            if not isinstance(game, Game):
                ng.append(self.data["api"].get_game(game))
            else:
                ng.append(game)

        self.data["games_created"] = ng


class Game:
    def __init__(self, game_dict, api):
        self.data = game_dict
        self.data["api"] = api
        self.data["last_update"] = time.time()

    def __getattr__(self, item):
        if item == "players" or "players_killed_last_night" or "players_alive" or "owner" or "mayor":
            self.load_players()

        return self.data[item]

    def start(self):
        self.api.start_game(self)

    def leave(self):
        self.api.leave_game(self)

    def join(self):
        self.api.join_game(self)

    def is_owned_by_me(self):
        return self.owner.uuid == self.api.uuid

    def load_players(self):
        np = []
        for player in self.data["players"][:]:
            if not isinstance(player, Player):
                np.append(self.data["api"].get_player(player, force_update=False))
            else:
                np.append(player)

        self.data["players"] = np

        np = []
        for player in self.data["players_killed_last_night"][:]:
            if not isinstance(player, Player):
                np.append(self.data["api"].get_player(player))
            else:
                np.append(player)

        self.data["players_killed_last_night"] = np

        np = []
        for player in self.data["players_alive"][:]:
            if not isinstance(player, Player):
                np.append(self.data["api"].get_player(player))
            else:
                np.append(player)

        self.data["players_alive"] = np

        if not isinstance(self.data["owner"], Player):
            self.data["owner"] = self.data["api"].get_player(self.data["owner"])

        if self.data["mayor"] and not isinstance(self.data["mayor"], Player):
            self.data["mayor"] = self.data["api"].get_player(self.data["mayor"])




