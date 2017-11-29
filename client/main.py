#!/usr/bin/env python3.6
# -*- coding:Utf-8 -*-
import os

import time

from api import Api

import os
import shlex
import struct
import platform
import subprocess


def get_terminal_size():
    """ getTerminalSize()
     - get width and height of console
     - works on linux,os x,windows,cygwin(windows)
     originally retrieved from:
     http://stackoverflow.com/questions/566746/how-to-get-console-window-width-in-python
    """
    current_os = platform.system()
    tuple_xy = None
    if current_os == 'Windows':
        tuple_xy = _get_terminal_size_windows()
        if tuple_xy is None:
            tuple_xy = _get_terminal_size_tput()
            # needed for window's python in cygwin's xterm!
    if current_os in ['Linux', 'Darwin'] or current_os.startswith('CYGWIN'):
        tuple_xy = _get_terminal_size_linux()
    if tuple_xy is None:
        tuple_xy = (80, 25)      # default value
    return tuple_xy


def _get_terminal_size_windows():
    try:
        from ctypes import windll, create_string_buffer
        # stdin handle is -10
        # stdout handle is -11
        # stderr handle is -12
        h = windll.kernel32.GetStdHandle(-12)
        csbi = create_string_buffer(22)
        res = windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)
        if res:
            (bufx, bufy, curx, cury, wattr,
             left, top, right, bottom,
             maxx, maxy) = struct.unpack("hhhhHhhhhhh", csbi.raw)
            sizex = right - left + 1
            sizey = bottom - top + 1
            return sizex, sizey
    except:
        pass


def _get_terminal_size_tput():
    # get terminal width
    # src: http://stackoverflow.com/questions/263890/how-do-i-find-the-width-height-of-a-terminal-window
    try:
        cols = int(subprocess.check_call(shlex.split('tput cols')))
        rows = int(subprocess.check_call(shlex.split('tput lines')))
        return (cols, rows)
    except:
        pass


def _get_terminal_size_linux():
    def ioctl_GWINSZ(fd):
        try:
            import fcntl
            import termios
            cr = struct.unpack('hh',
                               fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
            return cr
        except:
            pass
    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
    if not cr:
        try:
            cr = (os.environ['LINES'], os.environ['COLUMNS'])
        except:
            return None
    return int(cr[1]), int(cr[0])


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

clear_screen()

api = Api(str(input("Quel est le pseudo que vous voulez utiliser >")))

#api.logger.debug("Debbbbbugggggg")


def print_centered(string, char="*", full = False):
    cols, lign = get_terminal_size()

    if full:
        cstring = string.center(len(string)+2, " ")
    else:
        cstring = string.center(cols - 2, " ")

    print(cstring.center(cols, char))


def choix(message="Veuillez choisir une option >", liste_choix_possibles=None):
    if liste_choix_possibles is None:
        liste_choix_possibles = ["1", "2"]
    while True:
        choix_menu = str(input(message))
        if choix_menu in liste_choix_possibles:
            return choix_menu
        else:
            print(f"Le choix fait est incorrect, veuillez choisir une des options suivantes : {liste_choix_possibles}. ")


def main_menu():
    print_centered("Menu Principal", full=True)
    print_centered("1/ Rejoindre une partie")
    print_centered("2/ Créer une partie")
    print_centered("3/ Quitter")
    print_centered("", full=True)
    choix_possibles = [str(i) for i in range(1, 3+1)]
    option_choisie = choix(liste_choix_possibles=choix_possibles)
    clear_screen()
    if option_choisie == "1":
        games_list = api.list_games()
        if len(games_list) > 0:
            print_centered("Liste des parties", full=True)
            for i, game in enumerate(games_list):
                ip1 = i+1
                print_centered(f"{ip1}/ {game.name} ({game.player_count} joueur(s))")

            print_centered("")
            print_centered("a/ Retourner au menu principal")
            print_centered("", full=True)

            choix_possibles = [str(i) for i in range(1, len(games_list)+1)]
            choix_possibles.append("a")

            option_choisie = choix(message="Choisissez une partie >", liste_choix_possibles=choix_possibles)
            if option_choisie != "a":
                i = int(option_choisie) - 1
                partie_choisie = games_list[i]
                api.join_game(partie_choisie)
                in_game(partie_choisie)

        else:
            print("Aucune partie n'existe :(. Retour au menu")
    elif option_choisie == "2":
        game = api.create_game(input("Quel est le nom de votre partie ? >"))
        in_game(game)
    else:
        exit(0)


def print_game_status_screen(game, end_line = False):
    carte = game.api.get_player(api.uuid, force_update=True).cards[game.uuid]
    print_centered(f"Votre partie {game.name}", full = True)
    if game.mayor:
        print_centered("")
        print_centered("Maire :")
        print_centered(f"{game.mayor.name}")
    print_centered("")
    print_centered("Joueurs :")
    for player in game.players:
        if player in game.players_alive:
            print_centered(f"{player.name}")
        else:
            print_centered(f"(RIP) {player.name}")
    print_centered("")
    if end_line:
        print_centered(f"Votre carte : {carte}", full=True)

def vote_for(game, titre_menu, message_demande, optional = True, vote=True):
    print_centered(titre_menu, full=True)
    print_centered("Liste des joueurs :")

    for i, player in enumerate(game.players_alive):
        ip1 = i+1
        print_centered(f"{ip1}/ {player.name}")

    choix_possibles = [str(i) for i in range(1, len(game.players)+1)]

    if optional:
        print_centered("a/ Ne choisir personne")
        choix_possibles.append("a")

    carte = api.get_player(api.uuid, force_update=True).cards[game.uuid]

    print_centered(f"Votre carte : {carte}", full=True)

    option_choisie = choix(message=message_demande, liste_choix_possibles=choix_possibles)
    if option_choisie != "a":
        option_choisie = int(option_choisie)
        if vote:
            api.select_player(game, [game.players_alive[option_choisie-1]])
            return True
        else:
            return game.players_alive[option_choisie-1]

    else:
        return None

def in_game(game):
    phase_finished = 0

    while True:
        clear_screen()
        game = api.get_game(game.uuid, force_update=True)

        if game.phase != 0:
            print_game_status_screen(game, end_line=False)

        if game.phase == 0:

            print_centered(f"Votre partie {game.name}", full = True)
            print_centered("Joueurs présents :")
            for player in game.players:
                print_centered(player.name)

            if game.is_owned_by_me():
                print_centered("")
                print_centered("1/ Rafraîchir les joueurs")
                choix_possibles = ["1"]

                if len(game.players) >= 2:
                    print_centered("2/ Démarrer la partie")
                    choix_possibles.append("2")
                    pass

                print_centered("", full=True)
                option_choisie = choix(liste_choix_possibles=choix_possibles)

                if option_choisie == "2":
                    api.start_game(game)
            else:
                print_centered("", full=True)

        elif game.phase == 1:
            if phase_finished != 1:
                phase_finished = 1
                print_centered("")
                vote_for(game, "Selection du maire", "Quel joueur voulez-vous élir >")


            else:
                print_game_status_screen(game, end_line=True)
                print_centered(f"Votre choix est fait, nous attendons les autres pour encore {game.time_left} seconde(s).")

        elif game.phase == 10:
            if phase_finished != 10:
                phase_finished = 10
                carte = api.get_player(api.uuid).cards[game.uuid]
                if carte == "cupid":
                    vote_for(game, "Selection des amoureux", "Quel joueur voulez-vous selectionner comme mari >", optional=False)
                    vote_for(game, "Selection des amoureux", "Quel joueur voulez-vous selectionner comme femme >", optional=False)
            else:
                print(f"Nous attendons cupidon, qui choisis les deux amoureux pour encore {game.time_left} seconde(s)")

        elif game.phase == 12:
            if phase_finished != 12:
                phase_finished = 12
                carte = api.get_player(api.uuid).cards[game.uuid]
                if carte == "werewolve":
                    vote_for(game, "Selection de la victime des loups", "Quel joueur voulez-vous dévorer >")
            else:

                print(f"Nous attendons le(s) loup(s), qui choisissent leur proie pour encore {game.time_left} seconde(s)")

        elif game.phase == 13:
            if phase_finished != 13:
                phase_finished = 13
                carte = api.get_player(api.uuid).cards[game.uuid]
                if carte == "sorceress":
                    print_centered("Est mort cette nuit :", full=True)
                    print_centered(game.players_killed_last_night[0].name)
                    sauver = choix(message="Voulez vous le sauver ? [O/N >]", liste_choix_possibles=["o", "n", "O", "N"])
                    if sauver.lower() == "o":
                        api.sorceress_select(game, game.players_killed_last_night[0].name, save=True)
                    tuer = vote_for(game, "Selection de la personne à tuer", "Quel joueur tuer >", vote=False)
                    if tuer:
                        api.sorceress_select(game, tuer, save=False)
            else:
                print(f"Nous attendons le(s) loup(s), qui choisissent leur proie pour encore {game.time_left} seconde(s)")

        elif game.phase == 20:
            if not api.get_player(api.uuid) in game.players_alive:
                print_centered("RIP you :(")
                return
            vote_for(game, "Vote du jour", "Qui souhaitez-vous pointer du doigt afin de lui trancher le cou ? >", optional=True)

        elif game.phase == 99:
            return

        else:
            print_centered(f"Oops, le jeu est en phase {game.phase}, mais je ne sais pas comment la gérer... Je ne fais rien et je prie.")

        time.sleep(2)







while True:
    clear_screen()
    main_menu()