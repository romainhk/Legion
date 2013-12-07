#!/usr/bin/python
# -*- coding: utf-8  -*-
import sqlite3, datetime, os, shutil
import http.server, socketserver, threading, webbrowser
import logging, urllib, json
from urllib.parse import urlparse, parse_qs
import xml.etree.ElementTree as ET

class Legion(http.server.SimpleHTTPRequestHandler):
    """ Classe Legion
    Serveur web et interface pour base sqlite

    TODO :
    * logging des activités en txt
    * L'INE peut manquer !?
    * si aucuns changements à l'extinction -> supprimer la copie de la base
    """
    def __init__(self, request, client, server):
        global root
        # Les colonnes qui seront affichées, dans l'ordre et avec leur tri
        self.header = [ ['Nom', 'string'], \
                        [u'Prénom', 'string'], \
                        ['Naissance', 'int'], \
                        ['Genre', 'int'], \
                        ['Classe', 'string'], \
                        ['Doublement', 'string'], \
                        [u'Entrée', None] ]
        # La liste des classes connues
        self.classes = []

        self.annee = datetime.date.today().year
        self.root = root
        self.nb_import = 0
        # DB
        bdd = self.root+os.sep+'base.sqlite'
        # Sauvegarde de la base
        shutil.copy(bdd, bdd+'.'+datetime.date.today().isoformat())
        try:
            self.conn = sqlite3.connect(bdd)
        except:
            pywikibot.output("Impossible d'ouvrir la base sqlite {0}".format(bdd))
            exit(2)
        self.conn.row_factory = sqlite3.Row
        self.curs = self.conn.cursor()

        super().__init__(request, client, server)

    def dict_from_row(self, row):
        return dict(zip(row.keys(), row))

    def do_GET(self):
        # Analyse de l'url
        params = urlparse(self.path)
        query = parse_qs(params.query)
        logging.warning("REQUEST : {0} ? {1}".format(params, query))
        if params.path == '/liste':
            data = self.readfromdb()
            a = json.dumps(data)
            self.repondre(a)
        elif params.path == '/init':
            a = json.dumps(self.header)
            self.repondre(a)
        elif params.path == '/liste-classes':
            self.liste_classes()
            a = json.dumps(self.classes)
            self.repondre(a)
        elif params.path == '/recherche':
            res = self.rechercher(query['val'].pop(), query['type'].pop())
            a = json.dumps(res)
            self.repondre(a)
        else:
            # Par défaut, on sert l'index 
            http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        length = self.headers['content-length']
        data = self.rfile.read(int(length))
        parse = parse_qs(data.decode('UTF-8')) # { data: , name: }
        # le fichier xml est en ISO-8859-15
        data = parse['data'].pop()
        logging.warning(self.path)
        if self.path == '/importation':
            logging.warning('Importation du fichier...')
            self.importer_xml(data)
            self.liste_classes() # on met à jour la liste des classes
            a = json.dumps(u'Importation de {nb} élèves terminée'.format(nb=self.nb_import))
            self.repondre(a)

    def repondre(self, reponse):
        """ Envoie une réponse http [sic]
        """
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(bytes(reponse, 'UTF-8'))
        self.wfile.flush()

    def log_request(self, code=None, size=None):
        pass

    def log_message(self, format, *args):
        print('Message')

    def rechercher(self, id, type):
        """ Fait une recherche dans la base
        """
        # TODO : type=Tout
        data = []
        req = u'SELECT * FROM Élèves WHERE "{type}" COLLATE UTF8_GENERAL_CI LIKE "%{id}%" ORDER BY Nom,Prénom ASC'.format(id=id, type=type)
        # COLLATE UTF8_GENERAL_CI = sans casse
        try:
            for row in self.curs.execute(req):
                data.append(self.dict_from_row(row))
        except:
            logging.warning(u'La recherche de {0} comme {1} a échoué.\n{2}'.format(id, type, req))
        return data

    def importer_xml(self, data):
        """ Parse le xml à importer
        """
        #logging.warning('Parsing du fichier xml')
        self.nb_import = 0
        # Écriture de l'xml dans un fichier
        fichier_tmp = 'importation.xml'
        f = open(fichier_tmp, 'w', encoding='ISO-8859-15')
        f.write(data)
        f.close()
        # Parsing
        tree = ET.parse(fichier_tmp)
        root = tree.getroot()
        self.annee = int(root.findtext('.//PARAMETRES/ANNEE_SCOLAIRE'))
        date = root.findtext('.//PARAMETRES/DATE_EXPORT')
        for eleve in root.iter('ELEVE'):
            eid = eleve.get('ELEVE_ID')
            ine = eleve.findtext('ID_NATIONAL')
            nom = eleve.findtext('NOM')
            prenom = eleve.findtext('PRENOM')
            j, m, naissance = eleve.findtext('DATE_NAISS').split('/')
            genre = eleve.findtext('CODE_SEXE')
            doublement = eleve.findtext('DOUBLEMENT')
            entree = eleve.findtext('DATE_ENTREE')
            sortie = eleve.findtext('DATE_SORTIE')
            classe = root.findtext(".//*[@ELEVE_ID='{0}']/STRUCTURE/CODE_STRUCTURE".format(eid))
            if sortie is None:
                enr = { 'eid': eid, 'ine': ine, 'nom': nom, u'prénom': prenom, \
                        'naissance': int(naissance), 'genre': int(genre), \
                        'doublement': doublement, 'classe': classe, 'entree': entree }
                self.writetodb(enr)
            else:
                # élève sortie de l'établissement
                logging.error(u'{0} {1} (id:{2}) est sortie de l\'établissement'.format(prenom, nom, eid))

    def writetodb(self, enr):
        """ Ajoute un élève dans la bdd
        """
        # On vérifie si l'élève est déjà présent dans la bdd pour cette année
        req = u'SELECT COUNT(*) FROM Élèves WHERE ' \
            + u'INE="{ine}" AND Année={annee}'.format(ine=enr['ine'], annee=self.annee)
        try:
            self.curs.execute(req)
        except sqlite3.Error as e:
            logging.error(u"Impossible de savoir si l'élève est déjà dans la base :\n%s" % (e.args[0]))
        r = self.curs.fetchone()
        if r[0] == 0:
            req = u'INSERT INTO Élèves ' \
                + u'(INE, Nom, Prénom, Naissance, Genre, Classe, Doublement, Année, Entrée) VALUES ("%s", "%s", "%s", %i, %i, "%s", "%s", %i, "%s")' \
                % (enr['ine'], enr['nom'], enr[u'prénom'], enr['naissance'], enr['genre'], enr['classe'], enr['doublement'], self.annee, enr['entree'])
            try:
                self.curs.execute(req)
                self.nb_import = self.nb_import + 1
            except sqlite3.Error as e:
                logging.error(u"Erreur lors de l'insertion :\n%s" % (e.args[0]))
            self.conn.commit()

    def readfromdb(self):
        """ Lit le contenu de la base
        """
        data = []
        req = u'SELECT {0} FROM Élèves ORDER BY Nom,Prénom ASC'.format(', '.join([c[0] for c in self.header]))
        for row in self.curs.execute(req):
            data.append(self.dict_from_row(row))
        return data
        
    def liste_classes(self):
        """ Met à jour la liste des classes connues
        """
        req = u'SELECT DISTINCT Classe FROM Élèves ORDER BY Classe ASC'
        try:
            self.curs.execute(req)
        except sqlite3.Error as e:
            logging.error(u"Erreur lors de la mise à jour de la liste des classes :\n%s" % (e.args[0]))
        self.classes = [item[0] for item in self.curs.fetchall()]

# DEFINES
PORT = 5432

def open_browser():
    """ Ouvre un navigateur web sur la bonne page """
    def _open_browser():
        webbrowser.open(u'http://localhost:{port}'.format(port=PORT))
    thread = threading.Timer(0.5, _open_browser)
    thread.start()

if __name__ == "__main__":
    try:
        #open_browser()
        address = ("", PORT)
        root = os.getcwd()
        os.chdir(root + os.sep + 'web') # la partie html est dans le dossier web
        server = http.server.HTTPServer(address, Legion)
        logging.warning(u'Démarrage du serveur sur le port {0}'.format(PORT))
        server.serve_forever()
    except KeyboardInterrupt:
        logging.warning(u'^C reçu, extinction du serveur')
        server.socket.close()
