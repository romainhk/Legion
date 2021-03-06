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

        # Écriture du pid dans un fichier
        pid = str(os.getpid())
        self.pidfile = "legion.pid"
        open(self.pidfile, 'w').write(pid)

        global root, config
        os.chdir(root + os.sep + 'web') # la partie html est dans le dossier web
        if not os.path.isdir("cache"): os.makedirs('cache')
        self.cookie = http.cookies.SimpleCookie()
        self.auth_tries = {} # Timestamp des tentatives d'authentification récentes par IP
        self.importation_en_cours = False # mutex pour l'imporation
        # Lecture de la configuration
        self.nom_etablissement=config.get('Établissement', 'nom de l\'etablissement')
        self.mdp_admin=config.get('Général', 'mdp_admin')
        self.mdp_eps=config.get('Général', 'mdp_eps')
        self.situations=sorted([x.strip(' ') for x in config.get('Établissement', 'situations').split(',')])

        # DB
        self.db = database.Database(root, self.nom_etablissement)
        self.lire = None
        # EPS
        self.eps_activites=self.db.lire_eps_activites()
        # Lecture des options dans la BDD
        self.options=self.db.lire_options()
        self.date = datetime.date(year=1970, month=1, day=1)
        self.maj_date(self.options['date export'])
        # Suite de couleurs utilisés pour les graphiques
        self.colors = tuple([x.strip() for x in self.options['couleurs'].split(',')])
        # Les colonnes qui seront affichées, dans l'ordre
        self.header = [x.strip() for x in self.options['header'].split(',')]

        # Niveaux / Filières / Sections
        self.niveaux = [x.strip() for x in self.options['niveaux'].split(',')]
        self.filières = [x.strip() for x in self.options['filières'].split(',')]
        self.sections = []
        self.section_filière = {}
        for f in self.filières:
            for a in sorted([x.strip(' ') for x in config.get('Établissement', 'sections_'+f).split('\n')]):
                for b in a.split(','):
                    c = b.strip(' ')
                    if c not in self.sections:
                        self.sections.append(c)
                    self.section_filière[c] = f

        #modules = []
        #for a,b,c in pkgutil.iter_modules():
        #    modules.append(b)

    def maj_date(self, nvl_date):
        """ Mise à jour de la date de référence
        
        :param nvl_date: la nouvelle date (format ISO-8601)
        :type nvl_date: str
        """
        d = date(nvl_date)
        if d != self.date:
            self.date = d
            # MAJ de la base
            self.db.ecrire_option('date export', nvl_date)
        if d.month < 9:
            self.debut_AS = debut_AS(d.year-1)
        else:
            self.debut_AS = debut_AS(d.year)

    def quitter(self):
        """ Éteint le programme proprement """
        self.db.fermer()
        # Suppression des fichiers de cache
        for root, dirs, filenames in os.walk('cache'):
            for f in filenames:
                os.remove(os.path.join(root, f))

        os.remove('..'+os.sep+self.pidfile)
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
    logging.info('Démarrage du serveur (PID {1}) sur le port {0}'.format(port, os.getpid()))

    time.sleep(0.2)
    thread.start()
    # Interception des signaux d'extinction (2 et 15)
    signal.signal(signal.SIGINT, term)
    signal.signal(signal.SIGTERM, term)
