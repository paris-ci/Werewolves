#!/usr/bin/env python3.6
# -*- coding:Utf-8 -*-
import collections
import logging
import random
from uuid import uuid4

import time

logger = logging.getLogger("werewolves")

SECOND = 1
MINUTE = SECOND * 60
HOUR = MINUTE * 60
DAY = HOUR * 24


class Game:
    """
    The phases are as follow :
        - 0 : Not started
        - 1 : Just started, need to have a Mayor.
        - 10: Night — The stealer can steal a card
        - 11: Night — Cupid select lovers
        - 12: Night - Werewolves select thier preys, and the Pristress select a card to reveal
        - 13: Night - The sorceress can save and/or kill someone
        - 20: Day — Vote
        - 21: Day - Post-vote : hunter
        - 99: Finished

        Other numbers are reserved for future use.
    """

    def __init__(self, name, owner):
        self.STATE_NOT_STARTED = 0
        self.STATE_STARTED = 1
        self.STATE_NIGHT_STEALER = 10
        self.STATE_NIGHT_CUPID = 11
        self.STATE_NIGHT_WEREWOLVES = 12
        self.STATE_NIGHT_SORCERESS = 13
        self.STATE_DAY_VOTE = 20
        self.STATE_DAY_HUNTER = 21
        self.STATE_FINISHED = 99
        self.first_night = True
        self.players = set()
        self.players_alive = set()
        self.name = name
        self.uuid = str(uuid4())
        self.display_name = f"{self.name} §({self.uuid})"
        self.phase = 0
        self.need_to_complete_phase_before = 0
        self.created_at = int(time.time())
        self.owner = owner
        self.cards = []
        self.votes = {}
        self.players_killed_last_night = set()
        self.mayor = None
        self.pristress_last_used = 0

    def public_dict(self):
        return {
            "phase": self.phase,
            "players": [p.uuid for p in self.players],
            "players_alive": [p.uuid for p in self.players_alive],
            "players_killed_last_night": [p.uuid for p in self.players_killed_last_night],
            "cards": [c.name for c in self.cards],
            "name": self.name,
            "uuid": self.uuid,
            "owner": self.owner.uuid,
            "created_at": self.created_at,
            "time_left": int(self.need_to_complete_phase_before - time.time()),
            "player_count": len(self.players),
            "mayor": self.mayor.uuid if self.mayor else None
        }

    def get_player_with_card(self, card):
        for player in self.players_alive:
            if str(player.cards[self]) == str(card):
                return player

        return None

    def get_player_with_uuid(self, uuid):
        for player in self.players_alive:
            if str(player.uuid) == uuid:
                return player
        return None

    def get_votes(self, count_only_werewolves=False, player=None, number_required=1):
        if player:
            player_votes = set(self.votes[player])

            if number_required >= len(self.players_alive):
                raise Exception("NotEnoughPlayers")

            while len(player_votes) < number_required:
                player_votes.add(random.choice(list(self.players_alive)))

            return list(player_votes)[:number_required]

        cnt = collections.Counter()

        keys = []

        if count_only_werewolves:
            for player in self.votes.keys():
                if player.cards[self].name == "werewolve":
                    keys.append(player)

        else:
            keys = self.votes.keys()

        most_common = random.choice(list(self.players_alive))
        voted = 0
        if keys:
            for player in keys:
                vote_uuid = list(self.votes[player])[0]
                vote = self.get_player_with_uuid(vote_uuid)
                if vote:
                    cnt[vote] += 1
                    most_common, voted = cnt.most_common(1)[0]

        logger.info(
            f"Votes ({self.votes}) for game {self.display_name} selected {most_common} with {voted} votes. Clearing them.")
        votes = self.votes
        self.votes = {}

        return most_common, votes

    def tick(self, force=False):
        current_time = int(time.time())
        if self.phase == 0:
            return

        if len(self.votes) == len(self.players_alive):
            force = True

        if self.phase == self.STATE_NIGHT_STEALER:
            stealer = self.get_player_with_card("stealer")
            if stealer in self.votes.keys():
                force = True

        if self.phase == self.STATE_NIGHT_CUPID:
            cupid = self.get_player_with_card("cupid")
            if cupid in self.votes.keys():
                force = True

        if self.phase == self.STATE_NIGHT_WEREWOLVES:
            for player in self.players_alive:
                if str(player.cards[self]) == str("werewolve"):
                    if player not in self.votes.keys():
                        break
            else:
                force = True

        if len(self.players_alive) <= 1:
            self.phase = 99
            return

        if self.need_to_complete_phase_before < current_time or force:
            # most_common, votes = self.get_votes()

            cards = [c.cards[self].name for c in self.players_alive]
            logger.info(f"Game {self.display_name} finished phase {self.phase}, ticking.")
            if self.phase <= self.STATE_STARTED and self.first_night:
                self.mayor, votes = self.get_votes()
                logger.debug(f"{self.display_name} now have {self.mayor.display_name} as a mayor")

                # self.mayor = self.get_player_with_uuid(most_common)

                if "stealer" in cards:
                    self.need_to_complete_phase_before = current_time + 1 * MINUTE
                    self.phase = self.STATE_NIGHT_STEALER
                    return

            if self.phase <= self.STATE_NIGHT_STEALER and self.first_night:
                if "stealer" in cards:
                    stealer = self.get_player_with_card("stealer")
                    player_stolen = self.get_votes(stealer, number_required=1)[0]
                    stealer.cards[self] = player_stolen.cards[self]
                    player_stolen.cards[self] = "stealer"

                if "cupid" in cards:
                    self.need_to_complete_phase_before = current_time + 1 * MINUTE
                    self.get_votes()  # Reset votes
                    self.phase = self.STATE_NIGHT_CUPID
                    return

            if self.phase <= self.STATE_NIGHT_CUPID:
                if "cupid" in cards:
                    cupid = self.get_player_with_card("cupid")
                    players = self.get_votes(cupid, number_required=2)

                    for lover in players:
                        lover.love = players

                self.need_to_complete_phase_before = current_time + 1 * MINUTE
                self.get_votes()  # Reset votes
                self.phase = self.STATE_NIGHT_WEREWOLVES
                return

            if self.phase <= self.STATE_NIGHT_WEREWOLVES:

                most_common, votes = self.get_votes(count_only_werewolves=True)

                self.players_alive.remove(most_common)
                self.players_killed_last_night.add(most_common)

                if "sorceress" in cards:
                    self.need_to_complete_phase_before = current_time + 30
                    self.phase = self.STATE_NIGHT_SORCERESS
                    return

            if self.phase <= self.STATE_NIGHT_SORCERESS:
                self.need_to_complete_phase_before = current_time + 5 * MINUTE
                self.first_night = False
                self.get_votes()  # Reset votes
                self.phase = self.STATE_DAY_VOTE
                return

            # Hunter state is set outside of TICK, in case the vote result kills the Hunter.
            if self.phase <= self.STATE_DAY_HUNTER:
                self.need_to_complete_phase_before = current_time + 1 * MINUTE
                self.phase = self.STATE_NIGHT_WEREWOLVES
                return

    def give_cards(self):
        player_count = len(self.players)

        if player_count < 3:
            cards = ["werewolve"]

        elif player_count < 5:
            cards = ["werewolve", "sorceress"]

        elif player_count <= 7:
            cards = ["werewolve", "werewolve", "sorceress"]

        elif player_count <= 9:
            cards = ["werewolve", "werewolve", "sorceress", "stealer", "cupid"]

        elif player_count <= 11:
            cards = ["werewolve", "werewolve", "werewolve", "sorceress", "stealer", "cupid"]

        else:
            cards = ["werewolve", "werewolve", "werewolve", "werewolve", "sorceress", "stealer", "cupid"]

        while len(cards) < player_count:
            cards.append("villager")

        random.shuffle(cards)

        logger.info(f"We are giving out cards for game {self.display_name} : {cards}")

        for player in self.players:
            carte = Card(player, cards.pop())
            player.cards[self] = carte
            self.cards.append(carte)

            self.players_alive.add(player)

    def start(self):
        logger.info(f"Starting game {self.display_name}, with players {self.players}")
        if len(self.players) >= 2:
            self.phase = self.STATE_STARTED
            self.give_cards()
            self.need_to_complete_phase_before = int(time.time() + 1 * MINUTE)
            self.players_alive = self.players
            return True
        else:
            return False


class Player:
    def __init__(self, name):
        self.name = name
        self.uuid = str(uuid4())
        self.display_name = f"{self.name} §({self.uuid})"
        self.token = str(uuid4())
        self.games_created = set()
        self.games = set()
        self.current_game = None
        self.last_activity = int(time.time())
        self.cards = {}
        self.love = {}

    def public_dict(self):
        return {
            "games": [g.uuid for g in self.games],
            "games_created": [g.uuid for g in self.games_created],
            "name": self.name,
            "uuid": self.uuid
        }

    def private_dict(self):
        res = self.public_dict()
        cards = {}
        for game in self.cards.keys():
            cards[game.uuid] = self.cards[game].name

        res["cards"] = cards
        res["current_game"] = self.current_game.uuid if self.current_game else None
        res["love"] = self.love
        return res


class Card:
    def __init__(self, owner, name):
        self.name = name
        self.owner = owner
        self.heal_potion = (name == "sorceress")
        self.kill_potion = (name == "sorceress")

    def __str__(self):
        return self.name
