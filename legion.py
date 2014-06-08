#!/usr/bin/python
# -*- coding: utf-8  -*-
import os
import threading
import time
import datetime
import logging
import configparser, codecs
#web
import http.server
#lib spécifique
import database
import httphandler
from liblegion import *

class Legion(http.server.HTTPServer):
    """
        Legion est la classe principale.
        C'est le serveur web ; il lance le traitement des requêtes HTTP et instancie la base sqlite.
    """
    def __init__(self, address, handler):
        # Création du server
        super().__init__(address, handler)

        global root, config
        os.chdir(root + os.sep + 'web') # la partie html est dans le dossier web
        if not os.path.isdir("cache"): os.makedirs('cache')
        # Lecture de la configuration
        self.nom_etablissement=config.get('Établissement', 'nom de l\'etablissement')
        self.situations=sorted([x.strip(' ') for x in config.get('Établissement', 'situations').split(',')])
        #self.niveaux=sorted([x.strip(' ') for x in config.get('Établissement', 'niveaux').split(',')])
        self.niveaux=['Seconde', 'Première', 'Terminale', '1BTS', '2BTS', 'Bac+1', 'Bac+3']
        self.filières = ['GT', 'Pro', 'Enseignement supérieur']
        self.sections = []
        self.section_filière = {}
        for f in self.filières:
            for a in sorted([x.strip(' ') for x in config.get('Établissement', 'sections_'+f).split('\n')]):
                for b in a.split(','):
                    c = b.strip(' ')
                    self.sections.append(c)
                    self.section_filière[c] = f
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
        self.db = database.Database(root, self.nom_etablissement)
        # Suite de couleurs utilisés pour les graphiques
        self.colors=('#0080FF', '#FF0080', '#80FF00',
                     '#8000FF', '#FF8000', '#00FF80',
                     '#FF0000', '#00FF00', '#0000FF')

    def maj_date(self, date):
        """ Seter sur la date (date d'importation) """
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
    config.read_file(codecs.open(root + os.sep + 'config.cfg', "r", "utf8"))
    
    port=int(config.get('General', 'port'))
    address = ("", port)
    server = Legion(address, httphandler.HttpHandler)
    #open_browser(port)
    thread = threading.Thread(target = server.serve_forever)
    thread.deamon = True
    logging.info('Démarrage du serveur sur le port {0}'.format(port))
    time.sleep(0.2)
    thread.start()
