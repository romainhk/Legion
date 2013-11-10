#!/usr/bin/python
# -*- coding: utf-8  -*-
import sqlite3, datetime
import http.server, socketserver, threading, webbrowser
import logging, urllib, json
from urllib.parse import urlparse, parse_qs
import xml.etree.ElementTree as ET

class Legion(http.server.SimpleHTTPRequestHandler):
    """ Classe Legion

    Nécessite : jquery

    TODO :
    * vrai format de données
    * logging des activités
    """
    def __init__(self, request, client, server):
        self.enreg = {}
        self.header = [ 'INE', 'Nom', u'Prénom', 'Classe' ]
        self.annee = datetime.date.today().year
        # DB
        bdd = 'base.sqlite'
        try:
            self.conn = sqlite3.connect(bdd)
        except:
            pywikibot.output("Impossible d'ouvrir la base sqlite {0}".format(bdd))
            exit(2)
        self.conn.row_factory = sqlite3.Row
        self.curs = self.conn.cursor()
        # TODO : faire une sauvegarde de la base
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
            logging.warning(data)
            a = json.dumps(data)
            self.repondre(a)
        elif params.path == '/init':
            a = json.dumps(self.header)
            self.repondre(a)
        elif params.path == '/recherche':
            logging.warning('Recherche')
            res = self.rechercher(query['val'].pop(), query['type'].pop())
            a = json.dumps(res)
            self.repondre(a)
        else:
            # Par défaut, on sert l'index 
            http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        logging.warning('POST')
        length = self.headers['content-length']
        data = self.rfile.read(int(length))
        parse = parse_qs(data) # { data: , name: }
        data = parse[b'data'].pop()
        if self.path == '/importation':
            logging.warning('Importation du fichier...')
            self.importer_xml(data)
            #self.writetodb()
            a = json.dumps(u'Importation réussie')
            self.repondre(a)

    def repondre(self, reponse):
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
        # TODO : type=Tout
        data = []
        req = u'SELECT * FROM Élèves WHERE "{type}"="{id}" ORDER BY Nom,Prénom ASC'.format(id=id, type=type)
        logging.warning(req)
        # TODO TRY
        for row in self.curs.execute(req):
            data.append(self.dict_from_row(row))
        logging.warning(data)
        return data

    def importer_xml(self, data):
        """ Parse le xml
        """
        logging.warning('Parsing du fichier xml')
        # Écriture de l'xml dans un fichier
        fichier_tmp = 'importation.xml'
        f = open(fichier_tmp, 'wb')
        f.write(data)
        f.close()
        # Parsing
        tree = ET.parse(fichier_tmp)
        root = tree.getroot()
        self.annee = root.findtext('.//PARAMETRES/ANNEE_SCOLAIRE')
        date = root.findtext('.//PARAMETRES/DATE_EXPORT')
        for eleve in root.iter('ELEVE'):
            eid = eleve.get('ELEVE_ID')
            ine = eleve.findtext('ID_NATIONAL')
            nom = eleve.findtext('NOM')
            prenom = eleve.findtext('PRENOM')
            classe = root.findtext(".//*[@ELEVE_ID='{0}']/STRUCTURE/CODE_STRUCTURE".format(eid))
            if classe is None:
                logging.warning('Impossible de trouver la classe pour {0} {1} (id:{2})'.format(prenom, nom, eid))
            enr = { 'eid': eid, 'ine': ine, 'nom': nom, 'prenom': prenom, 'classe': classe }
            #self.writetodb(enr)

    def open_csv(self):
        """ Importe le csv
        iINE = 0 # position de l'INE
        fichier = 'export.csv'
        with open(fichier, 'r') as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='"')
            for row in reader:
                if reader.line_num == 1: # première ligne = entêtes
                    self.header = row
                    try:
                        iINE = row.index('INE')
                    except:
                        print('Impossible de trouver la colonne INE')
                        return False
                    continue
                if row[iINE] not in self.enreg:
                    self.enreg[row[iINE]] = row
                else:
                    print('Enregistrement en double : {0}').format(row)
        """

    def writetodb(self, enr):
        """ Écrit un enregistrement dans la base
        """
        # TODO : gestion des duplicatas
        req = u'INSERT INTO Élèves ' \
            + u'(INE, Nom, Prénom, Classe, Année) VALUES ("%s", "%s", "%s", "%s", %i)' \
            % (enr['INE'], enr['Nom'], enr[u'Prénom'], enr['Classe'], self.annee)
        logging.error(req)
        try:
            #self.curs.execute(req)
            pass
        except sqlite3.Error as e:
            logging.error(u"Erreur lors de l'insertion :\n%s" % (e.args[0]))
        self.conn.commit()

    def readfromdb(self):
        """ Lit le contenu de la base
        """
        data = []
        for row in self.curs.execute(u'SELECT * FROM Élèves ORDER BY Nom,Prénom ASC'):
            data.append(self.dict_from_row(row))
        return data
        

# defines
PORT = 5432
FILE = ''

def open_browser():
    """ Ouvre un navigateur web sur la bonne page """
    def _open_browser():
        webbrowser.open(u'http://localhost:%s/%s' % (PORT, FILE))
    thread = threading.Timer(0.5, _open_browser)
    thread.start()

if __name__ == "__main__":
    try:
        #open_browser()
        address = ("", PORT)
        server = http.server.HTTPServer(address, Legion)
        print(u'Démarrage du serveur sur le port', PORT)
        server.serve_forever()
    except KeyboardInterrupt:
        print(u'^C reçu, extinction du serveur')
        server.socket.close()
