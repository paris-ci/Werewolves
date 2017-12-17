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


def print_centered(string, char="*", full=False):
    cols, lign = get_terminal_size()

    if full:
        cstring = string.center(len(string) + 2, " ")
    else:
        cstring = string.center(cols - 2, " ")

    print(cstring.center(cols, char))

def choix(message:str, liste_de_choix:list):
    while True:
        val = input(message + " > ")
        if val in liste_de_choix:
            return val
        else:
            print(f"Je n'ai pas compris... Choix possibles : {liste_de_choix}")

def main_menu():
    print_centered("Menu Principal", full=True)
    print_centered("1) Créer une partie")
    print_centered("2) Rejoindre une partie")
    print_centered("3) Quitter le jeu :(")
    print_centered("", full=True)
    next_action = choix("Que voulez-vous faire ?", ["1", "2", "3"])
    if next_action == "1":
        game = create_game()
    elif next_action == "2":
        game = game_join_menu()
    elif next_action == "3":
        exit(0)

def create_game():
    api.create_game(input("Nom de la partie > "))

def game_join_menu():
    print_centered("Rejoindre une partie", full=True)
    games = api.list_games()
    for game in games:
        print_centered(game.name)





clear_screen()
print("Bienvenue sur WERWOLVES !")
api = Api(str(input("Quel est le pseudo que vous voulez utiliser ?>")))

while True:
    clear_screen()
    main_menu()
