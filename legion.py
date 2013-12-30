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
    """
    def __init__(self, request, client, server):
        global root
        # Les colonnes qui seront affichées, dans l'ordre et avec leur tri (Stupid-Table-Plugin)
        self.header = [ ['Nom', 'A-z'], \
                        [u'Prénom', 'A-z'], \
                        [U'Âge', '0-9'], \
                        ['Genre', 'H/F'], \
                        ['Parcours', 'Classes'], \
                        ['Doublement', 'Oui/Non'], \
                        [u'Entrée', 'Date'], \
                        [u'Durée', '0-9'], \
                        [u'Diplômé', 'A-z'], \
                        [u'Après', 'A-z'] \
                        ]
        self.annee = datetime.date.today().year
        self.root = root
        self.nb_import = 0
        # DB
        bdd = self.root+os.sep+'base.sqlite'
        if os.path.isfile(bdd):
            self.old_db = bdd+'.'+datetime.date.today().isoformat()
            # Sauvegarde de la base
            shutil.copy(bdd, self.old_db)

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
            self.repondre(data)
        elif params.path == '/stats':
            annee = query['annee'].pop()
            if annee == 'null': annee = self.annee
            data = self.generer_stats(annee)
            self.repondre(data)
        elif params.path == '/liste-annees':
            annees = self.lister('Année')
            self.repondre(annees)
        elif params.path == '/init':
            self.repondre(self.header)
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
            self.repondre(u'Importation de {nb} élèves terminée.'.format(nb=self.nb_import))

    def repondre(self, reponse):
        """ Envoie une réponse http [sic]
        """
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(bytes(json.dumps(reponse), 'UTF-8'))
        self.wfile.flush()

    def log_request(self, code=None, size=None):
        pass

    def log_message(self, format, *args):
        print('Message')

    def generer_stats(self, annee):
        """ Génère des statistiques sur la base
        """
        # Récupération des infos : classes, effectif...
        data = {}
        req = u'SELECT * FROM Élèves NATURAL JOIN Affectations WHERE Année={0}'.format(annee)
        for row in self.curs.execute(req).fetchall():
            d = self.dict_from_row(row)
            if d['Genre'] == 1:
                h = (0,1)
            else:
                h = (1,0)
            t = [ h[0], h[1], int(d['Doublement']) ] # Nb : garçon, fille, doublant
            classe = d['Classe']
            if classe in data:
                data[classe] = [sum(x) for x in zip(data[classe], t)] # data[classe] += t
            else:
                data[classe] = t

        # On génère maintenant le tableau de statistiques
        rep = []
        for cla, val in sorted(data.items()):
            g, f, doub = val
            r = ( "{classe}".format(classe=cla), \
                  "{effectif}".format(effectif=g+f), \
                  "{0} ({1} %)".format(doub, round(100*doub/(g+f), 1)), \
                  "{0} %".format( round(100*g/(g+f), 1) ) )
            rep.append(r)
        return rep

    def lister(self, info):
        """ Fait une liste des INE, des classes ou des années connues
        """
        req = u'SELECT DISTINCT {0} FROM Affectations ORDER BY {0} ASC'.format(info)
        try:
            self.curs.execute(req)
        except sqlite3.Error as e:
            logging.error(u"Erreur lors du listage '{0}' :\n{1}".format(info, e.args[0]))
        return [item[0] for item in self.curs.fetchall()]

    def importer_xml(self, data):
        """ Parse le xml à importer
        """
        ### TODO : pour tous les élèves non modifiés : mettre la date de sortie à l'année précédente ?
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
            if ine is None:
                logging.error(u"Impossible d'importer l'élève muni de l'ID {0}, données insuffisantes".format(eid))
                continue
            nom = eleve.findtext('NOM')
            prenom = eleve.findtext('PRENOM')
            j, m, naissance = eleve.findtext('DATE_NAISS').split('/')
            genre = eleve.findtext('CODE_SEXE')
            doublement = eleve.findtext('DOUBLEMENT')
            j, m, entree = eleve.findtext('DATE_ENTREE').split('/')
            sortie = eleve.findtext('DATE_SORTIE')
            classe = root.findtext(".//*[@ELEVE_ID='{0}']/STRUCTURE/CODE_STRUCTURE".format(eid))
            if sortie is None:
                enr = { 'eid': eid, 'ine': ine, 'nom': nom, u'prénom': prenom, \
                        'naissance': int(naissance), 'genre': int(genre), \
                        'doublement': doublement, 'classe': classe, 'entree': int(entree) \
                        }
                self.writetodb(enr)
            else:
                #logging.warning(u'{0} {1} (id:{2}) est sortie de l\'établissement'.format(prenom, nom, eid))
                pass

    def writetodb(self, enr):
        """ Ajoute un élève dans la bdd
        """
        classe = enr['classe']
        ine = enr['ine']
        enr[u'Diplômé'] = enr[u'Après'] = '?'
        # On vérifie si l'élève est déjà présent dans la bdd pour cette année
        req = u'SELECT COUNT(*) FROM Affectations WHERE ' \
            + u'INE="{ine}" AND Année={annee}'.format(ine=ine, annee=self.annee)
        try:
            self.curs.execute(req)
        except sqlite3.Error as e:
            logging.error(u"Impossible de savoir si l'élève est déjà dans la base :\n%s" % (e.args[0]))
        r = self.curs.fetchone()
        if r[0] == 0:
            # Ajout de l'élève
            req = u'INSERT INTO Élèves ' \
                + u'(INE, Nom, Prénom, Naissance, Genre, Doublement, Entrée, Diplômé, Après) VALUES ("%s", "%s", "%s", %i, %i, "%s", %i, "%s", "%s")' \
                % (ine, enr['nom'], enr[u'prénom'], enr['naissance'], enr['genre'], enr['doublement'], enr['entree'], enr[u'Diplômé'], enr[u'Après'])
            try:
                self.curs.execute(req)
            except sqlite3.Error as e:
                logging.error(u"Erreur lors de l'insertion :\n%s" % (e.args[0]))
                return False

        else:
            #logging.warning(u"L'élève {0} est déjà présent dans la base {1}".format(ine, self.annee))
            pass

        # Affectation à une classe cette année
        req = u'INSERT INTO Affectations ' \
              +  u'(INE, Classe, Année) VALUES ("{0}", "{1}", {2})'.format(ine, classe, self.annee)
        try:
            self.curs.execute(req)
        except sqlite3.Error as e:
            logging.warning(u"Erreur lors de l'affectation de la classe pour {0}:\n{1}".format(ine, e.args[0]))
            # au cas où, annulation de l'insert précédent
            self.conn.rollback()
            return False

        self.conn.commit()
        self.nb_import = self.nb_import + 1

    def readfromdb(self):
        """ Lit le contenu de la base
        """
        data = []
        req = u'SELECT * FROM Élèves NATURAL JOIN Affectations ORDER BY Nom,Prénom ASC'.format(self.annee)
        for row in self.curs.execute(req).fetchall():
            d = self.dict_from_row(row)
            ine = d['INE']
            if [el['INE'] for el in data].count(ine) == 0: # => L'INE est inconnu pour le moment
                # Génération de la colonne 'Parcours'
                parcours = []
                # Année de sortie
                sortie = self.annee
                req = u'SELECT Classe,Année FROM Affectations WHERE INE="{0}" ORDER BY Année ASC'.format(ine)
                try:
                    for r in self.curs.execute(req):
                        parcours.append(r['Classe'])
                        a = int(r['Année'])
                        if a > sortie : sortie = a
                except sqlite3.Error as e:
                    logging.error(u"Erreur lors de la génération du parcours de {0}:\n{1}".format(ine, e.args[0]))
                    continue
                d['Parcours'] = ', '.join(parcours)
                # Calcul de la durée de scolarisation
                d[u'Durée'] = sortie - d[u'Entrée'] + 1
                # Calcul de l'âge actuel
                d[u'Âge'] = self.annee - d['Naissance']

                data.append(d)
        return data
        
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
