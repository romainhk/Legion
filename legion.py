#!/usr/bin/python
# -*- coding: utf-8  -*-
import os
import sqlite3
import datetime
import logging
import shutil
import configparser
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
        # Fichier de config
        config = configparser.ConfigParser()
        config.read(root + os.sep + 'config.cfg')
        self.liste_situations=config.get('General', 'situations').split(',')
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
        rep = "";
        if params.path == '/liste':
            rep = { 'annee': self.date.year, 'data': self.db_lire() }
        elif params.path == '/stats':
            annee = query['annee'].pop()
            if annee == 'null': annee = self.date.year
            rep = self.generer_stats(annee)
        elif params.path == '/maj':
            ine = query['ine'].pop()
            champ = query['champ'].pop()
            donnee = query['d'].pop()
            rep = self.maj_champ(ine, champ, donnee)
        elif params.path == '/pending':
            rep = self.db_lire_pending()
        elif params.path == '/liste-annees':
            rep = self.lister('Année')
        elif params.path == '/init':
            rep = {'header': self.header, 'situations': self.liste_situations }
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
        data = {}
        req = u'SELECT * FROM Élèves NATURAL JOIN Affectations WHERE Année={0}'.format(annee)
        for row in self.curs.execute(req).fetchall():
            d = dict_from_row(row)
            if d['Genre'] == 2: # une femme
                h = (0,1)
            else: # == 1
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
            self.db_ecrire(enr)

    def db_inserer_affectation(self, ine, annee, classe, etab, doublement):
        """ Ajoute une affectations (un élève, dans une classe, dans un établissement) """
        if classe == "" or etab == "":
            logging.info("Erreur lors de l'affectation : classe ou établissement en défaut")
            return False
        req = u'INSERT INTO Affectations ' \
              +  u'(INE, Année, Classe, Établissement, Doublement) ' \
              + 'VALUES ("{0}", {1}, "{2}", "{3}", {4})'.format( ine, annee, classe, etab, doublement )
        try:
            self.curs.execute(req)
        except sqlite3.Error as e:
            logging.warning(u"Erreur lors de l'affectation de la classe pour {0}:\n{1}".format(ine, e.args[0]))
            # En cas de redoublement, une erreur d'insertion sur l'année précédente (code 9)
            # indique que l'élève est déjà connu -> on l'ignore
            if doublement != 9:
                return False
        return True

    def db_in_pending(self, enr, annee):
        """ Mise en attente de donnes incomplètes pour validation """
        req = u'INSERT INTO Pending ' \
            + u'(INE, Nom, Prénom, Naissance, Genre, Mail, Entrée, Diplômé, Situation, Lieu, Année, CLasse, Établissement, Doublement) ' \
            + 'VALUES ("{0}", "{1}", "{2}", "{3}", {4}, "{5}", {6}, "{7}", "{8}", "{9}", {10}, "{11}", "{12}", {13})'.format(
                    enr['ine'],         enr['nom'],         enr[u'prénom'],
                    enr['naissance'],   enr['genre'],       enr['mail'],
                    enr['entrée'],      enr[u'Diplômé'],    enr['Situation'],
                    enr['Lieu'],        annee,              enr['classe'],
                    enr['sad_établissement'],   enr['doublement'] )
        try:
            self.curs.execute(req)
        except sqlite3.Error as e:
            logging.error(u"Erreur lors de la mise en pending :\n%s" % (e.args[0]))

    def db_ecrire(self, enr):
        """ Ajoute les informations d'un élève à la bdd """
        ine = enr['ine']
        classe = enr['classe']
        enr[u'Diplômé'] = enr[u'Situation'] = enr['Lieu'] = '?'
        if ine is None or classe is None:
            self.db_in_pending(enr, self.date.year)
            return True
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
                + u'(INE, Nom, Prénom, Naissance, Genre, Mail, Entrée, Diplômé, Situation, Lieu) ' \
                + 'VALUES ("{0}", "{1}", "{2}", "{3}", {4}, "{5}", {6}, "{7}", "{8}", "{9}")'.format(
                        ine,                enr['nom'],         enr[u'prénom'],
                        enr['naissance'],   enr['genre'],       enr['mail'],
                        enr['entrée'],        enr[u'Diplômé'],    enr['Situation'],
                        enr['Lieu'])
            try:
                self.curs.execute(req)
            except sqlite3.Error as e:
                logging.error(u"Erreur lors de l'insertion :\n%s" % (e.args[0]))
                return False

            annee = self.date.year
            x = self.db_inserer_affectation(
                    ine,    annee,     classe,  'Jean Moulin',  enr['doublement'])
            etab = enr['sad_établissement']
            classe_pre = enr['sad_classe']
            if enr['doublement']: # Parfois, ces informations ne sont pas redonnées dans SIECLE
                classe_pre = classe
                etab = 'Jean Moulin'
            y = self.db_inserer_affectation(
                    ine,    annee-1,   classe_pre,  etab,   9)
            # En cas de problème, annulation des modifications précédentes
            if not x or not y:
                self.conn.rollback()
                #logging.warning(u"Rollback suite à un problème d'affectation\n{0}".format(enr))
                self.db_in_pending(enr, annee)

        else:
            #logging.warning(u"L'élève {0} est déjà présent dans la base {1}".format(ine, self.date.year))
            pass

        # Validation de l'affectation à une classe
        self.conn.commit()
        self.nb_import = self.nb_import + 1

    def db_lire(self):
        """ Lit le contenu de la base """
        data = {}
        req = u'SELECT * FROM Élèves NATURAL JOIN Affectations ORDER BY Nom,Prénom ASC, Année DESC'
        for row in self.curs.execute(req).fetchall():
            d = dict_from_row(row)
            ine = d['INE']
            # Génération du parcours
            annee = d.pop('Année')
            classe = d.pop('Classe')
            etab = d.pop('Établissement')
            doub = d.pop('Doublement')
            if ine in data.keys():
                # Déjà présent : on ajoute juste une année scolaire
                data[ine]['Parcours'][annee] = [ classe, etab, doub ]
            else:
                d['Parcours'] = {annee: [ classe, etab, doub ]}
                # Calcul de l'âge actuel
                d[u'Âge'] = nb_annees(datefr(d['Naissance']))
                data[ine] = d
        return data

    def db_lire_pending(self):
        """ Lit le contenu de la base """
        data = {}
        req = u'SELECT * FROM Pending ORDER BY Nom,Prénom ASC, Année DESC'
        for row in self.curs.execute(req).fetchall():
            d = dict_from_row(row)
            ine = d['INE']
            data[ine] = d
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
