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
        self.filières=[x.strip(' ') for x in config.get('General', 'filières').split(',')]
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
            rep = {'affectations': self.db.lire_classes(), 'niveaux': self.niveaux, 'filières': self.filières, 'sections': self.sections }
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
        """
            Génère des statistiques sur la base

        :param annee: Statistiques pour cette année
        :type annee: str

        :return: un dictionnaire des valeurs triées par catégories
        - ordre : l'ordre d'affichage
        - pour l'établissement
            - effectif total
            - proportion de garçon
            - De même, hors BTS
        - par section
            - effectif total => rep['section'][SECTION]['effectif'] = TOTAL
            - poids / étab
            - proportion de redoublants
            - proportion de garçon
            - taux de passage
        - par niveau
            - _idem_
        - provenance
            - établissement : total d'élèves, total d'élèves actuellement en seconde
        """
        # Récupération des infos : classes, effectif...
        data = self.db.stats_par_classe(annee)
        classes = self.db.lire_classes()

        # On génère maintenant le tableau de statistiques
        rep = { 'ordre': {},
                'établissement': {},
                'section': {}, 
                'niveau': {},
                'provenance': {} }
        # Ordre d'affichage des colonnes
        rep['ordre']['section']    = ['effectif', 'poids', 'garçon', 'doublant']
        rep['ordre']['niveau']     = ['effectif', 'poids', 'garçon', 'doublant']
        rep['ordre']['provenance'] = ['total', 'en seconde']
        # Calculs
        eff_total = sum([sum(x[:2]) for x in data.values()]) # Effectif total
        eff_total_bts = 0
        total_garcon = 0
        total_garcon_bts = 0
        total_doublant = 0
        for cla, val in sorted(data.items()):
            g, f, doub = val
            eff = g + f
            section_classe = classes[cla]['Section']
            niveau_classe = classes[cla]['Niveau']
            total_garcon = total_garcon + g
            total_doublant = total_doublant + doub
            #tp = self.db.taux_de_passage(cla)

            # Par Section
            if section_classe:
                if not section_classe in rep['section']:
                    rep['section'][section_classe] = {}
                dict_add(rep['section'][section_classe], 'effectif', eff)
                dict_add(rep['section'][section_classe], 'garçon', g)
                dict_add(rep['section'][section_classe], 'doublant', doub)
                #dict_add(rep['section'][section_classe], 'taux de passage', tp)
            # Par Niveau
            if niveau_classe:
                if not niveau_classe in rep['niveau']:
                    rep['niveau'][niveau_classe] = {}
                if niveau_classe == "BTS":
                    total_garcon_bts = total_garcon_bts + g
                    eff_total_bts = eff_total_bts + eff
                dict_add(rep['niveau'][niveau_classe], 'effectif', eff)
                dict_add(rep['niveau'][niveau_classe], 'garçon', g)
                dict_add(rep['niveau'][niveau_classe], 'doublant', doub)

        # Calcul des proportions : Poids, Garçon, Doublant
        for key, val in rep['section'].items():
            rep['section'][key]['poids'] = en_pourcentage(val['effectif']/eff_total)
            rep['section'][key]['garçon'] = en_pourcentage(val['garçon']/val['effectif'])
            rep['section'][key]['doublant'] = en_pourcentage(val['doublant']/val['effectif'])
        for key, val in rep['niveau'].items():
            rep['niveau'][key]['poids'] = en_pourcentage(val['effectif']/eff_total)
            rep['niveau'][key]['garçon'] = en_pourcentage(val['garçon']/val['effectif'])
            rep['niveau'][key]['doublant'] = en_pourcentage(val['doublant']/val['effectif'])
        # Pour l'établissement
        rep['établissement']['Effectif total'] = eff_total
        rep['établissement']['Proportion garçon'] = en_pourcentage(total_garcon / eff_total)
        a = (total_garcon - total_garcon_bts)/(eff_total - eff_total_bts)
        rep['établissement']['Proportion garçon (hors BTS)'] = en_pourcentage(a)
        rep['établissement']['Proportion doublant'] = en_pourcentage(total_doublant / eff_total)
        # Provenance
        aff = self.db.lire_affectations()
        annee_pre = int(annee)-1
        for k,v in aff.items():
            annee_aff = v['Année']
            etab = v['Établissement']
            if not etab in rep['provenance']:
                rep['provenance'][etab] = {'en seconde':0, 'total':0}
            if annee_aff == annee_pre: # On ne compte que les affectations de l'année précédente
                dict_add(rep['provenance'][etab], 'total', 1)
            elif annee_aff == int(annee):
                if v['Niveau'] == "Seconde": # Pour les élèves de seconde...
                    a = v['INE']+'__'+str(annee_pre)
                    if a in aff:
                        #... on recherche l'établissement de l'année précédent (si possible)
                        etab_pre = aff[a]['Établissement']
                        if not etab_pre in rep['provenance']:
                            rep['provenance'][etab_pre] = {'en seconde':0, 'total':0}
                        dict_add(rep['provenance'][etab_pre], 'en seconde', 1)
                    # Requête équivalente en SQL :
                    # SELECT Établissement,count(*) FROM Affectations WHERE INE IN (SELECT INE FROM Affectations A LEFT JOIN Classes C ON A.Classe = C.Classe WHERE Niveau="Seconde" AND Année=2013) AND Année=2012 GROUP BY Établissement
        return rep

    def importer_xml(self, data):
        """
            Parse le xml à importer
        :param data: le fichier à importer (passé en POST)
        :type data: flux de fichier xml
        """
        self.nb_import = 0
        les_classes = list(self.db.lire_classes().keys())
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
                    'naissance': naissance, 'genre': genre, 'mail': mail, \
                    'doublement': doublement, 'classe': classe, 'entrée': entrée, \
                    'sad_établissement': sad_etab,   'sad_classe': sad_classe }
            if self.db.ecrire(enr, self.date):
                self.nb_import = self.nb_import + 1
            if not (classe in les_classes or classe in classes_a_ajouter or classe is None) :
                classes_a_ajouter.append(classe)
        # Ici, les données élèves ont été importé ; il ne reste qu'à ajouter les classes inconnues
        self.db.ecrire_classes(classes_a_ajouter)

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
