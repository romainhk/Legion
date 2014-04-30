#!/usr/bin/python
# -*- coding: utf-8  -*-
import os
import threading
import time
import datetime
import logging
import configparser
#web
import http.server
#lib spécifique
import database
import httphandler
from liblegion import *

class Legion(http.server.HTTPServer):
    """
        Legion est la classe principale.
        C'est le serveur web qui lance le traitement des requêtes HTTP et instancie la base sqlite
    """
    def __init__(self, address, handler):
        # Création du server
        super().__init__(address, handler)

        global root, config
        os.chdir(root + os.sep + 'web') # la partie html est dans le dossier web
        # Lecture de la configuration
        self.nom_etablissement=config.get('Établissement', 'nom de l\'etablissement')
        self.situations=sorted([x.strip(' ') for x in config.get('Établissement', 'situations').split(',')])
        #self.niveaux=sorted([x.strip(' ') for x in config.get('Établissement', 'niveaux').split(',')])
        self.niveaux=['Seconde', 'Première', 'Terminale', 'BTS', 'Formation']
        self.sections = []
        self.filières = []
        for a in sorted([x.strip(' ') for x in config.get('Établissement', 'sections').split('\n')]):
            b = a.split(',')
            if len(b) == 2:
                self.sections.append(b[0].strip(' '))
                self.filières.append(b[1].strip(' '))
        # Les colonnes qui seront affichées, dans l'ordre et avec leur contenu par défaut
        self.header = [ ['Nom', 'A-z'], \
                        ['Prénom', 'A-z'], \
                        ['Âge', ''], \
                        ['Mail', ''], \
                        ['Genre', 'H/F'], \
                        ['Année', 'Toutes'], \
                        ['Classe', ''], \
                        ['Établissement', ''], \
                        ['Doublement', 'Oui/Non'], \
                        ['Entrée', 'Date'], \
                        ['Diplômé', 'A-z'], \
                        ['Situation', 'A-z'], \
                        ['Lieu', 'A-z'] \
                        ]

        ajd = datetime.date.today()
        if ajd.month < 9:
            self.date = debut_AS(ajd.year-1)
        else:
            self.date = debut_AS(ajd.year)
        # DB
        self.db = database.Database(root)

    def maj_date(self, date):
        """ Seter sur la date """
        self.date = date

if __name__ == "__main__":
    # Logging
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    # Logging fichier
    file_handler = logging.FileHandler('legion.log', 'a')
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s;%(levelname)s;%(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    # Logging console
    steam_handler = logging.StreamHandler()
    steam_handler.setLevel(logging.DEBUG)
    logger.addHandler(steam_handler)

    # Fichier de config
    root = os.getcwd()
    config = configparser.ConfigParser()
    config.read(root + os.sep + 'config.cfg')

    port=int(config.get('General', 'port'))
    address = ("", port)
    server = Legion(address, httphandler.HttpHandler)
    #open_browser(port)
    thread = threading.Thread(target = server.serve_forever)
    thread.deamon = True
    logging.info('Démarrage du serveur sur le port {0}'.format(port))
    time.sleep(0.2)
    thread.start()
