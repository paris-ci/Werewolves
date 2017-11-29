#!/usr/bin/env python3.6
# -*- coding:Utf-8 -*-
import logging

import time

from common import objects

logger = logging.getLogger("werewolves")
MIN = 60
HOUR = 60 * MIN


class Cache():
    def __init__(self):
        self.players = set()
        self.games = set()

    def get_player_by_uuid(self, uuid) -> objects.Player:
        return next((x for x in self.players if x.uuid == uuid), None)

    def get_game_by_uuid(self, uuid) -> objects.Game:
        return next((x for x in self.games if x.uuid == uuid), None)

    def get_user_from_auth(self, uuid, token):
        #self.purge()
        player = self.get_player_by_uuid(uuid)

        try:
            if player.token == token:
                return player
            else:
                return False
        except:
            return False

    def purge(self):
        #logger.debug("Purge starting")
        time_start = time.time()
        players_deleted = 0
        games_deleted = 0
        expiry_time = int(time.time()) - 2 * HOUR
        for player in list(self.players):
            if player.last_activity <= expiry_time:
                afk_minutes = int(time.time() - player.last_activity)/60
                # logger.debug(f"Purge of player {player.display_name} (AFK for {afk_minutes}):")
                for game_played in player.games:
                    game_played.players.remove(player)
                    # logger.debug(f"\t1)\tRemoved player {player.display_name} from game {game_played.display_name}.")

                self.players.remove(player)
                players_deleted += 1
                # logger.debug(f"\t2)\tDeleted player {player.display_name} from cache")

        for game in list(self.games):
            if len(game.players) == 0:
                self.games.remove(game)
                games_deleted += 1
                # logger.debug(f"Removed game {game.display_name}.")


        time_stop = time.time()

        time_taken = round(time_stop-time_start, 3)

        logger.debug(f"Purge finished. Removed {players_deleted} players and {games_deleted} games, in {time_taken} seconds.")


