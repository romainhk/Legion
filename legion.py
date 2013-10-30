#!/usr/bin/python
# -*- coding: utf-8  -*-
import csv, sqlite3
import http.server, socketserver, threading, webbrowser
import logging, urllib, json
from urllib.parse import urlparse, parse_qs

class Legion(http.server.SimpleHTTPRequestHandler):
    """ Classe Legion
    """
    def __init__(self, request, client, server):
        self.fichier = 'export.csv'
        self.enreg = {}
        self.header = []
        self.annee = 2013
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

    def do_GET(self):
        # Analyse de l'url
        params = urlparse(self.path)
        query = parse_qs(params.query)
        #logging.warning(params)
        if params.path == "/test":
            self.processMyRequest(query)
        else:
            # Par défaut, on sert l'index 
            http.server.SimpleHTTPRequestHandler.do_GET(self)

        """
    def do_POST(self):
        #logging.warning(self.headers)
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD':'POST',
                     'CONTENT_TYPE':self.headers['Content-Type'],
                     })
        logging.warning("======= POST VALUES =======")
        for item in form.list:
            logging.warning(item)
        http.server.SimpleHTTPRequestHandler.do_GET(self)
        """

    def processMyRequest(self, query):
        logging.warning(query)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        a = json.dumps(self.fichier)
        logging.warning(a)
        self.wfile.write(bytes(a, 'UTF-8'))
        self.wfile.flush()

    def log_request(self, code=None, size=None):
        #print('Request')
        pass

    def log_message(self, format, *args):
        print('Message')

    def open_csv(self):
        """ Importe le csv
        """
        iINE = 0 # position de l'INE
        with open(self.fichier, 'r') as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='"')
            for row in reader:
                if reader.line_num == 1: # première ligne = entêtes
                    self.header = row
                    try:
                        iINE = row.index('INE')
                    except:
                        print('Impossible de trouver la colonne INE')
                        return False
                    #for h in row:
                    #    self.enreg[h] = []
                    continue
                #self.enreg[row.pop(iINE)] = row
                if row[iINE] not in self.enreg:
                    self.enreg[row[iINE]] = row
                else:
                    print('Enregistrement en double : {0}').format(row)
                #for h, v in zip(self.header, row):
                #    self.enreg[h].append(v)

    def writetodb(self):
        """ Ecrit un enregistrement dans la base
        """
        try:
            iINE = self.header.index(u'INE')
            iNom = self.header.index(u'Nom')
            iPre = self.header.index(u'Prénom')
            iClasse = self.header.index(u'Classe')
        except:
            print(u"Le fichier csv n'est pas au bon format.")
            return False
        for k,v in self.enreg.items():
            req = u'INSERT INTO Élèves ' \
                + u'(INE, Nom, Prénom, Classe, Année) VALUES ("%s", "%s", "%s", "%s", %i)' \
                % (v[iINE], v[iNom], v[iPre], v[iClasse], self.annee)
            try:
                self.curs.execute(req)
            except sqlite3.Error as e:
                print(req)
                print(u"Erreur lors de l'insertion :\n%s" % (e.args[0]))
            self.conn.commit()

    def readfromdb(self):
        """ Lit le contenu de la base
        """
        for row in self.curs.execute(u'SELECT * FROM Élèves ORDER BY INE'):
            print(row['INE'])
        
    def run(self):
        self.open_csv()
        print(self.header)
        print(self.enreg)
        #self.writetodb()
        self.readfromdb()

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
