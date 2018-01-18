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

     Toute cette partie sers à trouver la taille du terminal de l'utilisateur
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
        tuple_xy = (80, 25)  # default value
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
    """ Cette fonction vide le terminal de l'utilisateur """
    os.system('cls' if os.name == 'nt' else 'clear')


######################################################################################################################


def print_centered(string, char="*", full=False):
    """Cette fonction sert à afficher au centre du terminal"""
    cols, lign = get_terminal_size()

    if full:
        cstring = string.center(len(string) + 2, " ")
    else:
        cstring = string.center(cols - 2, " ")

    print(cstring.center(cols, char))


def choix(message: str, liste_de_choix: list) -> str:
    """
    Cette fonction prend en compte la valeur entrer par l'utilisateur et la compare à une liste de string pour savoir
    si elle est autorisé

    :param message: Le message affiché à l'utilisateur lors de la demande d'un choix
    :param liste_de_choix: Liste de strings de choix autorisés pour l'utilisateur
    :return: La valeur choisie et vérifiée par l'utilisateur
    """
    while True:
        val = input(message + " > ").lower()
        if val in liste_de_choix:
            return val
        else:
            print(f"Je n'ai pas compris... Choix possibles : {liste_de_choix}")


def main_menu():
    """
    Cette fonction affiche et gère le menu principal

    :return:
    """
    print_centered("Menu Principal", full=True)
    print_centered("1) Créer une partie")
    print_centered("2) Rejoindre une partie")
    print_centered("3) Quitter le jeu :(")
    print_centered("", full=True)
    next_action = choix("Que voulez-vous faire ?", ["1", "2", "3"])
    game = None
    if next_action == "1":
        game = create_game()
    elif next_action == "2":
        game = game_join_menu()
    elif next_action == "3":
        exit(0)

    if game is not None:
        in_game(game)


def create_game():
    """ Cette fonction crée une partie dans l'api """
    return api.create_game(input("Nom de la partie > "))


def game_join_menu():
    """ Cette fonction sert à rejoindre une partie en ligne """

    print_centered("Rejoindre une partie", full=True)
    games = api.list_games()
    for i, game in enumerate(games):
        i_plus_un = i + 1
        print_centered(f"{i_plus_un}) {game.name}")
    print_centered("")
    print_centered("a) Revenir au menu principal")
    print_centered("", full=True)
    liste_de_choix = list(map(str, list(range(1, len(games) + 1)))) + ["a"]

    """(list) va prendre l'élément et en faire une liste
       (map) prend les éléments applique la focntion str a chacun
     des éléments passé dans la fonction 'str' dans le cas présent"""

    next_action = choix("Quelle partie souhaitez-vous rejoindre ?", liste_de_choix)
    if next_action == 'a':
        return
    else:
        return api.join_game(games[int(next_action) - 1])


def vote(game, question, nombre_a_tuer=1):
    """ Cette fonction sert à faire voter l'utilisateur
    :param game qui
    :param question
    :param nombre a tuer
    :return la personne qui va etre tuer
    """
    personnes_a_tuer = []
    personnes_vivantes = game.players_alive

    for i in range(nombre_a_tuer):
        print_centered("Quel est votre vote ?", full=True)
        liste_de_noms = [p.name for p in personnes_vivantes]
        for j, nom in enumerate(liste_de_noms):
            j_plus_un = j + 1
            print_centered(f"{j_plus_un}) {nom}")

        print_centered("", full=True)

        c = choix(question, list(map(str, range(1, len(liste_de_noms) + 1))))

        personnes_a_tuer.append(personnes_vivantes.pop(int(c) - 1))

    return personnes_a_tuer


def in_game(game_obj):
    """ Cette fonction permet de gérer les différentes phases du jeu
    :param  game_obj qui
    """
    last_phase = 0

    while True:
        game_obj = api.get_game(game_obj.uuid, force_update=True)
        if game_obj.phase != 0:
            carte = api.get_player(api.uuid, force_update=True).cards[game_obj.uuid]
            print_centered(f"Jeu en cours : {game_obj.name}", full=True)
            print_centered(f"Votre carte : {carte}")

            maire = game_obj.mayor.name if game_obj.mayor else "Pas désigné"

            print_centered(f"Votre maire à tous : {maire}")

        if game_obj.phase == 0:

            if game_obj.owner == api.me:
                print_centered("1) Rafraichir les joueurs")
                print_centered("2) Lancer la partie !")
                action = choix("Que voulez-vous faire ?", ["1", "2"])

                if action == "2":
                    api.start_game(game_obj)
                else:
                    print("Liste des joueurs en ligne:")
                    print("\n".join([e.name for e in game_obj.players]))

            else:
                print("Le jeu n'a pas encore commencé les ami(e)s !")
                print("Liste des joueurs en ligne:")
                print("\n".join([e.name for e in game_obj.players]))

        elif game_obj.phase == 1:

            if last_phase != 1:
                print("Choisir un maire !")
                api.select_player(game_obj, vote(game_obj, "Choissez une personne à élire"))
                last_phase = 1

        elif game_obj.phase == 10:

            print("Nuit - Le voleur peut voler une carte")
            last_phase = 10

        elif game_obj.phase == 11:
            print("Nuit - La magie de Cupidon opère")
            last_phase = 11

        elif game_obj.phase == 12:
            print("Nuit - Les loups choississent leur proie et la Voyante choisi une carte a révéler")
            if carte == 'werewolve':
                if last_phase != 12:
                    api.select_player(game_obj, vote(game_obj, "Choissez une personne à dévorer"))
                    last_phase = 12
                else:
                    print_centered("Vos copains finissent de manger !")
            else:
                print(" Les loups dévorent leurs proies ! ")
        elif game_obj.phase == 13:
            print("Nuit - La sorcière peut tuer ou sauver un joueur")
            if carte == 'sorceress':
                print_centered("1/ Tuer")
                print_centered("2/ Sauver")
                action_sorc = choix("Voulez-vous tuer ou sauver?", ['1', '2'])
                if action_sorc == '1':
                    api.select_player(game_obj, vote(game_obj, "Choissez une personne à tuer"))
                elif action_sorc == '2':
                    api.select_player(game_obj, vote(game_obj, "Choissez une personne à sauver"))
        elif game_obj.phase == 20:
            print("Le jour se lève - Vote")
            api.select_player(game_obj, vote(game_obj, "Choissez une personne à tuer"))
        elif game_obj.phase == 99:
            print("Fin !")
        time.sleep(1)



clear_screen()

print("Bienvenue sur WERWOLVES !")
api = Api(str(input("Quel est le pseudo que vous voulez utiliser ?>")))

while True:
    clear_screen()
    main_menu()
