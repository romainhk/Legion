#!/usr/bin/python
# -*- coding: utf-8  -*-
import os
import datetime
import logging
import configparser
#web
import http.server, socketserver
import json
import urllib
from urllib.parse import urlparse, parse_qs
import xml.etree.ElementTree as ET
#lib spécifique
import database
from liblegion import *

class Legion(http.server.SimpleHTTPRequestHandler):
    """ Classe Legion
    Serveur web et interface pour base sqlite
    """
    def __init__(self, request, client, server):
        global root
        # Fichier de config
        config = configparser.ConfigParser()
        config.read(root + os.sep + 'config.cfg')
        self.situations=[x.strip(' ') for x in config.get('General', 'situations').split(',')]
        self.niveaux=[x.strip(' ') for x in config.get('General', 'niveaux').split(',')]
        self.sections=[x.strip(' ') for x in config.get('General', 'sections').split(',')]
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
        self.root = root
        self.nb_import = 0
        # DB
        self.db = database.Database(root)

        super().__init__(request, client, server)

    def do_GET(self):
        """ Traitement des GET """
        # Analyse de l'url
        params = urlparse(self.path)
        query = parse_qs(params.query)
        logging.debug("GET {0} ? {1}".format(params, query))
        rep = "";
        if params.path == '/liste':
            rep = { 'annee': self.date.year, 'data': self.db.lire() }
        elif params.path == '/stats':
            annee = query['annee'].pop()
            if annee == 'null': annee = self.date.year
            rep = self.generer_stats(annee)
        elif params.path == '/maj':
            ine = query['ine'].pop()
            champ = query['champ'].pop()
            donnee = query['d'].pop()
            rep = self.db.maj_champ('Élèves', ine, champ, donnee)
        elif params.path == '/maj_classe':
            classe = query['classe'].pop()
            champ = query['champ'].pop()
            if 'val' in query: # val peut être vide
                val = query['val'].pop()
            else:
                val = ''
            rep = self.db.maj_champ('Classes', classe, champ, val)
        elif params.path == '/pending':
            rep = self.db.lire_pending()
        elif params.path == '/liste-annees':
            rep = self.db.lister('Année')
        elif params.path == '/options':
            rep = {'affectations': self.db.lire_classes(), 'niveaux': self.niveaux, 'sections': self.sections }
        elif params.path == '/init':
            rep = {'header': self.header, 'situations': self.situations }
        else:
            # Par défaut, on sert l'index 
            http.server.SimpleHTTPRequestHandler.do_GET(self)
            return True
        self.repondre(rep)

    def do_POST(self):
        """ Traitement des POST """
        length = self.headers['content-length']
        data = self.rfile.read(int(length))
        parse = parse_qs(data.decode('UTF-8')) # { data: , name: }
        # le fichier xml est en ISO-8859-15
        data = parse['data'].pop()
        rep = "";
        if self.path == '/importation':
            logging.info('Importation du fichier...')
            self.importer_xml(data)
            rep = u"L'importation de {nb} élèves s'est bien terminée.".format(nb=self.nb_import)
        else:
            return True
        self.repondre(rep)

    def repondre(self, reponse):
        """ Envoie une réponse http [sic] """
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(bytes(json.dumps(reponse), 'UTF-8'))
        self.wfile.flush()

    def generer_stats(self, annee):
        """ Génère des statistiques sur la base """
        # Récupération des infos : classes, effectif...
        data = self.db.get_stats(annee)

        # On génère maintenant le tableau de statistiques
        rep = []
        eff_total = sum([sum(x[:2]) for x in data.values()]) # Effectif total
        for cla, val in sorted(data.items()):
            g, f, doub = val
            eff = g + f
            r = ( "{classe}".format(classe=cla), \
                  "{effectif}".format(effectif=eff), \
                  "{0} %".format(round(100*eff/eff_total,1)), \
                  "{0} ({1} %)".format(doub, round(100*doub/eff, 1)), \
                  "{0} %".format( round(100*g/eff, 1) ) )
            rep.append(r)
        return rep

    def importer_xml(self, data):
        """ Parse le xml à importer """
        self.nb_import = 0
        les_classes = list(self.db_lire_classes().keys())
        classes_a_ajouter = []
        # Écriture de l'xml dans un fichier
        fichier_tmp = 'importation.xml'
        f = open(fichier_tmp, 'w', encoding='ISO-8859-15')
        f.write(data)
        f.close()
        # Parsing
        tree = ET.parse(fichier_tmp)
        root = tree.getroot()
        self.date = debut_AS( int(root.findtext('.//PARAMETRES/ANNEE_SCOLAIRE')) )
        date = root.findtext('.//PARAMETRES/DATE_EXPORT')
        for eleve in root.iter('ELEVE'):
            eid = eleve.get('ELEVE_ID')
            ine = eleve.findtext('ID_NATIONAL')
            if ine is None:
                #logging.error(u"Impossible d'importer l'élève muni de l'ID {0}, données insuffisantes".format(eid))
                continue
            nom = eleve.findtext('NOM')
            prenom = eleve.findtext('PRENOM')
            naissance = eleve.findtext('DATE_NAISS')
            genre = eleve.findtext('CODE_SEXE')
            mail = xstr(eleve.findtext('MEL'))
            doublement = eleve.findtext('DOUBLEMENT')
            j, m, entrée = eleve.findtext('DATE_ENTREE').split('/')
            sortie = eleve.findtext('DATE_SORTIE')
            classe = root.findtext(".//*[@ELEVE_ID='{0}']/STRUCTURE[TYPE_STRUCTURE='D']/CODE_STRUCTURE".format(eid))
            sad_etab = xstr(eleve.findtext('SCOLARITE_AN_DERNIER/DENOM_COMPL')).title()
            sad_classe = xstr(eleve.findtext('SCOLARITE_AN_DERNIER/CODE_STRUCTURE')).strip(' ')
            enr = { 'eid': eid, 'ine': ine, 'nom': nom, u'prénom': prenom, \
                    'naissance': naissance, 'genre': int(genre), 'mail': mail, \
                    'doublement': int(doublement), 'classe': classe, 'entrée': int(entrée), \
                    'sad_établissement': sad_etab,   'sad_classe': sad_classe }
            self.db.ecrire(enr)
            if not (classe in les_classes or classe in classes_a_ajouter or classe is None) :
                classes_a_ajouter.append(classe)
        # Ici, les données élèves ont été importé ; il ne reste qu'à ajouter les classes inconnues
        for cla in classes_a_ajouter:
            req = u'INSERT INTO Classes VALUES ("{0}", "", "")'.format(cla)
            try:
                self.curs.execute(req)
            except sqlite3.Error as e:
                #logging.warning(u"Erreur lors de l'ajout de la classe {0}:\n{1}".format(cla, e.args[0]))
                pass
        self.conn.commit()

if __name__ == "__main__":
    # DEFINES
    PORT = 5432
    """
    logging.basicConfig(
        filename='legion.log',
        level=logging.DEBUG,
        format='%(asctime)s;%(levelname)s;%(message)s')
    """
    address = ("", PORT)
    root = os.getcwd()
    try:
        #open_browser(PORT)
        os.chdir(root + os.sep + 'web') # la partie html est dans le dossier web
        server = http.server.HTTPServer(address, Legion)
        logging.info(u'Démarrage du serveur sur le port {0}'.format(PORT))
        server.serve_forever()
    except KeyboardInterrupt:
        logging.warning(u'^C reçu, extinction du serveur')
        server.socket.close()
