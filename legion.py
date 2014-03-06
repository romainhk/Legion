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
        super().__init__(address, handler)
        self.nb_import = 0
        self.root = os.getcwd()
        os.chdir(self.root + os.sep + 'web') # la partie html est dans le dossier web
        # Fichier de config
        config = configparser.ConfigParser()
        config.read(self.root + os.sep + 'config.cfg')
        self.nom_etablissement=config.get('General', 'nom de l\'etablissement')
        self.situations=sorted([x.strip(' ') for x in config.get('General', 'situations').split(',')])
        self.niveaux=sorted([x.strip(' ') for x in config.get('General', 'niveaux').split(',')])
        self.filières=sorted([x.strip(' ') for x in config.get('General', 'filières').split(',')])
        self.sections=sorted([x.strip(' ') for x in config.get('General', 'sections').split(',')])
        # Les colonnes qui seront affichées, dans l'ordre et avec leur contenu par défaut
        self.header = [ ['Nom', 'A-z'], \
                        [u'Prénom', 'A-z'], \
                        [u'Âge', ''], \
                        ['Mail', ''], \
                        ['Genre', 'H/F'], \
                        ['Année', 'Toutes'], \
                        ['Classe', ''], \
                        ['Établissement', ''], \
                        ['Doublement', 'Oui/Non'], \
                        [u'Entrée', 'Date'], \
                        [u'Diplômé', 'A-z'], \
                        [u'Situation', 'A-z'], \
                        [u'Lieu', 'A-z'] \
                        ]

        ajd = datetime.date.today()
        if ajd.month < 9:
            self.date = debut_AS(ajd.year-1)
        else:
            self.date = debut_AS(ajd.year)
        # DB
        self.db = database.Database(self.root)

    def maj_date(self, date):
        self.date = date

if __name__ == "__main__":
    """
    logging.basicConfig(
        filename='legion.log',
        level=logging.DEBUG,
        format='%(asctime)s;%(levelname)s;%(message)s')
    """
    PORT = 5432
    address = ("", PORT)
    server = Legion(address, httphandler.HttpHandler)
    #open_browser(PORT)
    thread = threading.Thread(target = server.serve_forever)
    thread.deamon = True
    logging.info(u'Démarrage du serveur sur le port {0}'.format(PORT))
    time.sleep(0.2)
    thread.start()
