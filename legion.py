#!/usr/bin/python
# -*- coding: utf-8  -*-
import os
import sqlite3
import datetime
import logging
import shutil
#web
import http.server, socketserver
import json
import urllib
from urllib.parse import urlparse, parse_qs
import xml.etree.ElementTree as ET
#lib spécifique
from liblegion import *

class Legion(http.server.SimpleHTTPRequestHandler):
    """ Classe Legion
    Serveur web et interface pour base sqlite
    """
    def __init__(self, request, client, server):
        global root
        # Les colonnes qui seront affichées, dans l'ordre et avec leur contenu par défaut
        self.header = [ ['Nom', 'A-z'], \
                        [u'Prénom', 'A-z'], \
                        [u'Âge', '0-9'], \
                        ['Mail', ''], \
                        ['Genre', 'H/F'], \
                        ['Parcours', 'Classes'], \
                        [u'Entrée', 'Date'], \
                        [u'Durée', '0-9'], \
                        [u'SAD_établissement', 'A-z'], \
                        [u'SAD_classe', 'A-z'], \
                        [u'Diplômé', 'A-z'], \
                        [u'Après', 'A-z'] \
                        ]
        self.date = datetime.date.today()
        self.root = root
        self.nb_import = 0
        # DB
        bdd = self.root+os.sep+'base.sqlite'
        if os.path.isfile(bdd):
            self.old_db = bdd+'.'+datetime.date.today().isoformat()
            # Sauvegarde de la base
            shutil.copy(bdd, self.old_db)
        else:
            logging.error("La base sqlite ({0}) n'est pas accessible. Impossible de continuer.".format(bdd))
            exit(2)

        try:
            self.conn = sqlite3.connect(bdd)
        except:
            logging.error("Impossible de se connecter à la base de données ({0})".format(bdd))
            exit(3)
        self.conn.row_factory = sqlite3.Row
        self.curs = self.conn.cursor()

        super().__init__(request, client, server)

    def do_GET(self):
        """ Traitement des GET """
        # Analyse de l'url
        params = urlparse(self.path)
        query = parse_qs(params.query)
        logging.debug("GET {0} ? {1}".format(params, query))
        if params.path == '/liste':
            data = self.readfromdb()
            self.repondre(data)
        elif params.path == '/stats':
            annee = query['annee'].pop()
            if annee == 'null': annee = self.date.year
            data = self.generer_stats(annee)
            self.repondre(data)
        elif params.path == '/maj':
            ine = query['ine'].pop()
            champ = query['champ'].pop()
            donnee = query['d'].pop()
            data = self.maj_champ(ine, champ, donnee)
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
        """ Traitement des POST """
        length = self.headers['content-length']
        data = self.rfile.read(int(length))
        parse = parse_qs(data.decode('UTF-8')) # { data: , name: }
        # le fichier xml est en ISO-8859-15
        data = parse['data'].pop()
        if self.path == '/importation':
            logging.info('Importation du fichier...')
            self.importer_xml(data)
            self.repondre(u"L'importation de {nb} élèves s'est bien terminée.".format(nb=self.nb_import))

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
        data = {}
        req = u'SELECT * FROM Élèves NATURAL JOIN Affectations WHERE Année={0}'.format(annee)
        for row in self.curs.execute(req).fetchall():
            d = dict_from_row(row)
            if d['Genre'] == 2:
                h = (0,1)
            else: # = 1
                h = (1,0)
            t = [ h[0], h[1], int(d['Doublement']) ] # Nb : garçon, fille, doublant
            classe = d['Classe']
            if classe in data:
                data[classe] = [sum(x) for x in zip(data[classe], t)] # data[classe] += t
            else:
                data[classe] = t

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

    def maj_champ(self, ine, champ, donnee):
        """ Mets à jour un champ de la base """
        req = u'UPDATE Élèves SET {champ}="{d}" WHERE INE="{ine}"'.format(ine=ine, champ=champ, d=donnee)
        try:
            self.curs.execute(req)
        except sqlite3.Error as e:
            logging.error(u"Erreur lors de l'insertion de '{0}' :\n{1}".format(ine, e.args[0]))
            return 'Non'
        self.conn.commit()
        return 'Oui'

    def lister(self, info):
        """ Génère une liste des INE, des classes ou des années connues """
        req = u'SELECT DISTINCT {0} FROM Affectations ORDER BY {0} ASC'.format(info)
        try:
            self.curs.execute(req)
        except sqlite3.Error as e:
            logging.error(u"Erreur lors du listage '{0}' :\n{1}".format(info, e.args[0]))
        return [item[0] for item in self.curs.fetchall()]

    def importer_xml(self, data):
        """ Parse le xml à importer """
        self.nb_import = 0
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
                logging.error(u"Impossible d'importer l'élève muni de l'ID {0}, données insuffisantes".format(eid))
                continue
            nom = eleve.findtext('NOM')
            prenom = eleve.findtext('PRENOM')
            naissance = eleve.findtext('DATE_NAISS')
            genre = eleve.findtext('CODE_SEXE')
            mail = xstr(eleve.findtext('MEL'))
            doublement = eleve.findtext('DOUBLEMENT')
            j, m, entree = eleve.findtext('DATE_ENTREE').split('/')
            sortie = eleve.findtext('DATE_SORTIE')
            classe = root.findtext(".//*[@ELEVE_ID='{0}']/STRUCTURE/CODE_STRUCTURE".format(eid))
            sad_etab = xstr(eleve.findtext('SCOLARITE_AN_DERNIER/DENOM_COMPL')).title()
            sad_classe = xstr(eleve.findtext('SCOLARITE_AN_DERNIER/CODE_STRUCTURE')).strip(' ')
            if sortie is None:
                enr = { 'eid': eid, 'ine': ine, 'nom': nom, u'prénom': prenom, \
                        'naissance': naissance, 'genre': int(genre), 'mail': mail, \
                        'doublement': int(doublement), 'classe': classe, 'entree': int(entree), \
                        'sad_etablissement': sad_etab,   'sad_classe': sad_classe \
                        }
                self.writetodb(enr)
            else:
                #logging.warning(u'{0} {1} (id:{2}) est sortie de l\'établissement'.format(prenom, nom, eid))
                pass

    def writetodb(self, enr):
        """ Ajoute les informations d'un élève à la bdd """
        classe = enr['classe']
        ine = enr['ine']
        enr[u'Diplômé'] = enr[u'Après'] = '?'
        # On vérifie si l'élève est déjà présent dans la bdd pour cette année
        req = u'SELECT COUNT(*) FROM Affectations WHERE ' \
            + u'INE="{ine}" AND Année={annee}'.format(ine=ine, annee=self.date.year)
        try:
            self.curs.execute(req)
        except sqlite3.Error as e:
            logging.error(u"Impossible de savoir si l'élève est déjà dans la base :\n%s" % (e.args[0]))
        r = self.curs.fetchone()
        if r[0] == 0:
            # Ajout de l'élève
            req = u'INSERT INTO Élèves ' \
                + u'(INE, Nom, Prénom, Naissance, Genre, Entrée, Mail, SAD_établissement, SAD_classe, Diplômé, Après) ' \
                + 'VALUES ("{0}", "{1}", "{2}", "{3}", {4}, {5}, "{6}", "{7}", "{8}", "{9}", "{10}")'.format(
                        ine,                enr['nom'],         enr[u'prénom'],
                        enr['naissance'],   enr['genre'],       enr['entree'],
                        enr['mail'],        enr['sad_etablissement'],    enr['sad_classe'],
                        enr[u'Diplômé'],    enr[u'Après'])
            try:
                self.curs.execute(req)
            except sqlite3.Error as e:
                logging.error(u"Erreur lors de l'insertion :\n%s" % (e.args[0]))
                return False

        else:
            #logging.warning(u"L'élève {0} est déjà présent dans la base {1}".format(ine, self.date.year))
            pass

        # Affectation à une classe
        req = u'INSERT INTO Affectations ' \
              +  u'(INE, Classe, Année, Doublement) ' \
              + 'VALUES ("{0}", "{1}", {2}, {3})'.format(
                      ine, classe, self.date.year, enr['doublement'])
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
        """ Lit le contenu de la base """
        data = []
        req = u'SELECT * FROM Élèves NATURAL JOIN Affectations ORDER BY Nom,Prénom ASC'
        for row in self.curs.execute(req).fetchall():
            d = dict_from_row(row)
            ine = d['INE']
            if [el['INE'] for el in data].count(ine) == 0: # => L'INE est inconnu pour le moment
                # Génération de la colonne 'Parcours'
                parcours = []
                # Année de sortie
                sortie = self.date
                req = u'SELECT Classe,Année,Doublement FROM Affectations WHERE INE="{0}" ORDER BY Année ASC'.format(ine)
                try:
                    for r in self.curs.execute(req):
                        classe = r['Classe']
                        if r['Doublement'] == 1: classe = classe+'*'
                        parcours.append(classe)
                        a = debut_AS( int(r['Année']) )
                        if a > sortie : sortie = a
                except sqlite3.Error as e:
                    logging.error(u"Erreur lors de la génération du parcours de {0}:\n{1}".format(ine, e.args[0]))
                    continue
                d['Parcours'] = ', '.join(parcours)
                # Calcul de la durée de scolarisation
                entree = debut_AS( d['Entrée'] )
                d[u'Durée'] = nb_annees(entree, sortie) + 1
                # Calcul de l'âge actuel
                d[u'Âge'] = nb_annees(datefr(d['Naissance']))

                data.append(d)
        return data
        
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
