#!/usr/bin/python
# -*- coding: utf-8  -*-
import os
import threading
import time
import datetime
import logging
import configparser, codecs
import database
import signal
#web
import http.server, http.cookies
import httphandler
#import ssl, socket
from liblegion import *
#import pkgutil

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
        self.cookie = http.cookies.SimpleCookie()
        self.auth_tries = {} # Timestamp des tentatives d'authentification récentes par IP
        # Lecture de la configuration
        self.nom_etablissement=config.get('Établissement', 'nom de l\'etablissement')
        self.mdp_admin=config.get('Général', 'mdp_admin')
        self.mdp_eps=config.get('Général', 'mdp_eps')
        self.situations=sorted([x.strip(' ') for x in config.get('Établissement', 'situations').split(',')])
        self.niveaux=['Seconde', 'Première', 'Terminale', '1BTS', '2BTS', 'Bac+1', 'Bac+3']
        self.filières = ['Générale', 'Technologique', 'Pro', 'Enseignement supérieur']
        self.sections = []
        self.section_filière = {}
        for f in self.filières:
            for a in sorted([x.strip(' ') for x in config.get('Établissement', 'sections_'+f).split('\n')]):
                for b in a.split(','):
                    c = b.strip(' ')
                    self.sections.append(c)
                    self.section_filière[c] = f
        # EPS
        self.eps_activites={}
        for i in range(1,5):
            for a in sorted([x.strip(' ').capitalize() for x in config.get('EPS', 'CP_{0}'.format(i)).split(',')]):
                self.eps_activites[a] = i
        # Les colonnes qui seront affichées, dans l'ordre
        self.header = [ 'Nom', 'Prénom', 'Âge', 'Mail', 'Genre', 'Année', 'Classe', 'Établissement', 'Doublement', 'Entrée', 'Diplômé', 'Situation', 'Lieu' ]

        ajd = datetime.date.today()
        if ajd.month < 9:
            self.date = debut_AS(ajd.year-1)
        else:
            self.date = debut_AS(ajd.year)
        # DB
        self.db = database.Database(root, self.nom_etablissement)
        self.lire = None
        # Suite de couleurs utilisés pour les graphiques
        self.colors=('#0080FF', '#FF0080', '#80FF00',
                     '#8000FF', '#FF8000', '#00FF80',
                     '#FF0000', '#00FF00', '#0000FF')
        #modules = []
        #for a,b,c in pkgutil.iter_modules():
        #    modules.append(b)

    #def maj_date(self, date):
    #    """
    #        Seter sur la date
    #    :param date: date d'importation
    #    :type date: datetime
    #    """
    #    self.date = date

    def quitter(self):
        """ Éteint le programme proprement """
        self.db.fermer()
        # Suppression des fichiers de cache
        for root, dirs, filenames in os.walk('cache'):
            for f in filenames:
                os.remove(os.path.join(root, f))
        # Coupure du serveur web
        time.sleep(0.5)
        logging.info('Extinction du serveur')
        eteindre_serveur(self)

def term(signal, frame):
    """ Lance l'extinction """
    server.quitter()

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
    
    port=int(config.get('Général', 'port'))
    address = ("", port)
    server = Legion(address, httphandler.HttpHandler)
    #server.socket = ssl.wrap_socket(server, certfile='cert.pem', server_side=True, cert_reqs=ssl.CERT_REQUIRED)
    thread = threading.Thread(target = server.serve_forever)
    thread.deamon = True
    logging.info('Démarrage du serveur sur le port {0}'.format(port))
    time.sleep(0.2)
    thread.start()
    # Interception des signaux d'extinction (2 et 15)
    signal.signal(signal.SIGINT, term)
    signal.signal(signal.SIGTERM, term)
