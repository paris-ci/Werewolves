#!/usr/bin/env python3.6
# -*- coding:Utf-8 -*-


import logging

from logging.handlers import RotatingFileHandler

import hug
import time
import common.objects as obj
import common.cache as cache

cache_store = cache.Cache()


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
import platform

if platform.system() == 'Windows':
    ColorStreamHandler = _WinColorStreamHandler
else:
    ColorStreamHandler = _AnsiColorStreamHandler

logger = logging.getLogger("werewolves")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s :: %(levelname)s :: [%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s')
file_handler = RotatingFileHandler('werewolves.log', 'a', 10000, 1)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

steam_handler = ColorStreamHandler()
steam_handler.setLevel(logging.DEBUG)
# steam_handler.setLevel(logging.INFO)

steam_handler.setFormatter(formatter)
logger.addHandler(steam_handler)
logger.debug("Starting... :)")


## WEREWOLVES ##

def gen_error(name, message):
    return {"errors": {name: message}}


def check_auth(uuid, token):
    player = cache_store.get_user_from_auth(uuid, token)
    if player:
        player.last_activity = int(time.time())
        logger.debug(f"Auth for user {uuid} with {token} returned {player.display_name}")
    else:
        logger.warning(f"Auth for user {uuid} with {token} failed with {player}")
    return player


uuid_token_authentication = hug.authentication.basic(check_auth)


@hug.request_middleware()
def process_data(request, response):
    logger.debug(f"-> {request.url} || {request.params}")

@hug.response_middleware()
def process_data(request, response, resource):
    logger.debug(f"<- {request.url} || ({response.status}) {response.body} ")
    logger.info(f"<-> {request.url}")

@hug.post('/login', versions=1)
def login(name: hug.types.text):
    """
    Create a new player, named with a nickname. Nicknames don't have to be unique.

    Returns a public player profile, with a non-public token, that will only be sent once.
    """
    player = obj.Player(name)
    cache_store.players.add(player)
    res = player.public_dict()
    res["token"] = player.token
    logger.info(f"User {player.display_name} logged in.")

    return res


@hug.post('/create_game', versions=1, requires=uuid_token_authentication)
def create_game(player: hug.directives.user, name: hug.types.text):
    """
    Create a new game, named. Does NOT start the game but open it for new players

    Returns a Game dict
    """
    game = obj.Game(name, player)
    cache_store.games.add(game)

    game.players.add(player)
    player.games.add(game)
    player.current_game = game

    logger.info(f"User {player.display_name} created game {game.display_name}")

    res = game.uuid

    return res


@hug.post('/join_game', versions=1, requires=uuid_token_authentication)
def join_game(player: hug.directives.user, uuid: hug.types.text):
    """
    Create a new game, named. Does NOT start the game but open it for new players

    Returns a Game dict

    Possible errors are :
        - GameNotJoinable : You can't join the game because it started
        - GameNotFound : The game specified couldn't be found

    """
    game = cache_store.get_game_by_uuid(uuid)
    if game:
        if game.phase == 0:
            game.players.add(player)
            player.games.add(game)
            player.current_game = game
            logger.info(f"User {player.display_name} joined game {game.display_name}")
        else:
            return gen_error("GameNotJoinable", "The selected game started and couldn't be joined.")
    else:
        return gen_error("GameNotFound", "The selected game couldn't be found.")


@hug.post('/leave_game', versions=1, requires=uuid_token_authentication)
def leave_game(player: hug.directives.user, uuid: hug.types.text):
    """
    Leave a game you are in.

    Returns a Game dict

    Possible errors are :
        - GameNotFound : The game specified couldn't be found
        - NotInGame : You are not in this game

    """
    game = cache_store.get_game_by_uuid(uuid)
    if game:
        if player in game.players:
            game.players.remove(player)
            player.current_game = None
            logger.info(f"User {player.display_name} left game {game.display_name}")
        else:
            return gen_error("NotInGame", "You can't leave a game you didn't joined.")

    else:
        return gen_error("GameNotFound", "The selected game couldn't be found.")


@hug.post('/game_status', versions=1, requires=uuid_token_authentication)
def game_status(player: hug.directives.user, uuid: hug.types.text):
    """
    Get the latest information about a game. Must be called frequently by clients to update users lists, phases...

    Returns a Game dict

    Possible errors are :
        - GameNotFound : The game specified couldn't be found
    """
    game = cache_store.get_game_by_uuid(uuid)
    if game:
        game.tick()
        res = game.public_dict()
        return res
    else:
        return gen_error("GameNotFound", "The selected game couldn't be found.")


@hug.post('/player_status', versions=1, requires=uuid_token_authentication)
def player_status(player: hug.directives.user, uuid: hug.types.text):
    """
    Get the latest information about a player.
    Must be called by clients to update cards, current_games, status and more...

    Returns a Game dict

    Possible errors are :
        - PlayerNotFound : The game specified couldn't be found
    """
    player_selected = cache_store.get_player_by_uuid(uuid)

    if player == player_selected:
        res = player_selected.private_dict()
        logger.debug(str(res))
        return res
    elif player:
        res = player_selected.public_dict()
        return res
    else:
        return gen_error("PlayerNotFound", "The selected player couldn't be found.")


@hug.post('/start_game', versions=1, requires=uuid_token_authentication)
def start_game(player: hug.directives.user, uuid: hug.types.text):
    """
    Called by the game owner to start the game.

    Possible errors are :
        - GameNotFound : The game specified couldn't be found
        - GameCantStart : The game couldn't be started. Maybe there isn't enough players.
        - NotAllowed : You are'nt the game owner, and you can't start it.
    """
    game = cache_store.get_game_by_uuid(uuid)
    if game:

        if game.owner == player:
            started = game.start()
            if not started:
                return gen_error("GameCantStart", "Game couldn't be started")
        else:
            return gen_error("NotAllowed", "You are not allowed to start the game")
        logger.info(f"User {player.display_name} started game {game.display_name}")
    else:
        return gen_error("GameNotFound", "The selected game couldn't be found.")


@hug.post('/select_player', versions=1, requires=uuid_token_authentication)
def select_player(player: hug.directives.user, game_uuid: hug.types.text, players_uuid: hug.types.comma_separated_list):
    """
    Select a player/some players. This function is used to vote on people, select lovers, people to swap card with...
    """
    game = cache_store.get_game_by_uuid(game_uuid)

    players_uuid = set(players_uuid)

    for uuid in players_uuid:
        if uuid not in [p.uuid for p in game.players_alive]:
            return gen_error("PlayerNotAlive", f"Player {uuid} is not alive.")

    game.votes[player] = players_uuid


@hug.post('/sorceress_select', versions=1, requires=uuid_token_authentication)
def sorceress_select(player: hug.directives.user, game_uuid: hug.types.text, player_uuid: hug.types.text,
                     save_or_kill: hug.types.boolean):
    """
    Select a player/some players. This function is used to vote on people, select lovers, people to swap card with...

    save_or_kill -> True to save; False to kill.
    """
    game = cache_store.get_game_by_uuid(game_uuid)
    target_player = cache_store.get_player_by_uuid(player_uuid)

    kill = not save_or_kill
    save = save_or_kill

    if target_player not in game.players_alive and kill:
        return gen_error("PlayerNotAlive", f"Player {target_player.display_name} is not alive.")

    if target_player not in game.players_killed_last_night and save:
        return gen_error("PlayerAlive",
                         f"Player {target_player.display_name} is alive and can't be saved, or was killed for too long.")

    else:
        if save:
            if player.cards[game].heal_portion:
                player.cards[game].heal_portion = False
            else:
                gen_error("NoHealPotion", "You don't have a heal potion")
            game.players_killed_last_night.remove(target_player)
            game.players_alive.add(target_player)


        else:
            if player.cards[game].kill_potion:
                player.cards[game].kill_potion = False
            else:
                gen_error("NoKillPotion", "You don't have a kill potion")

            game.players_killed_last_night.add(target_player)
            game.players_alive.remove(target_player)


@hug.post('/list_games', versions=1, requires=uuid_token_authentication)
def list_games():
    """
    Return the list of games on the server
    """

    return [g.uuid for g in cache_store.games]


@hug.get('/status', versions=1)
@hug.post('/status', versions=1)
def status():
    """
    Return a status report of the server
    """
    return {
        "players_count": len(cache_store.players),
        "games_count": len(cache_store.games)
    }
