#!/usr/bin/python
# -*- coding: utf-8  -*-
import time
import logging
#web
import http.server
import json
import urllib
from urllib.parse import urlparse, parse_qs
import xml.etree.ElementTree as ET
#lib spécifique
from liblegion import *

class HttpHandler(http.server.SimpleHTTPRequestHandler):
    """ Classe HttpHandler
    Traite les requêtes HTTP issues du serveur web

    self.server est une référence vers le serveur d'origine
    """
    def do_GET(self):
        """ Traitement des GET """
        # Analyse de l'url
        params = urlparse(self.path)
        query = parse_qs(params.query)
        logging.debug("GET {0} ? {1}".format(params, query))
        rep = "";
        if params.path == '/liste':
            rep = { 'annee': self.server.date.year, 'data': self.server.db.lire() }
        elif params.path == '/stats':
            annee = query['annee'].pop()
            if annee == 'null': annee = self.server.date.year
            rep = self.generer_stats(int(annee))
        elif params.path == '/maj':
            ine = query['ine'].pop()
            champ = query['champ'].pop()
            donnee = query['d'].pop()
            rep = self.server.db.maj_champ('Élèves', ine, champ, donnee)
        elif params.path == '/maj_classe':
            classe = query['classe'].pop()
            champ = query['champ'].pop()
            if 'val' in query: # val peut être vide
                val = query['val'].pop()
            else:
                val = ''
            rep = self.server.db.maj_champ('Classes', classe, champ, val)
        elif params.path == '/pending':
            rep = self.server.db.lire_pending()
        elif params.path == '/liste-annees':
            rep = self.server.db.lister('Année')
        elif params.path == '/options':
            rep = { 'affectations': self.server.db.lire_classes(), 
                'niveaux': self.server.niveaux,
                'filières': self.server.filières,
                'sections': self.server.sections }
        elif params.path == '/init':
            rep = {'header': self.server.header, 'situations': self.server.situations }
        elif params.path == '/quitter':
            self.quitter()
            return
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
            rep = u"L'importation de {nb} élèves s'est bien terminée.".format(nb=self.server.nb_import)
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

    def quitter(self):
        """ Éteint le programme proprement """
        rep = 'Vous pouvez éteindre votre navigateur et reprendre une activité normale.'
        self.repondre(rep)
        self.server.db.fermer()
        # Coupure du serveur web
        time.sleep(0.5)
        logging.info('Extinction du serveur')
        eteindre_serveur(self.server)

    def generer_stats(self, annee):
        """
            Génère des statistiques sur la base

        :param annee: Statistiques pour cette année
        :type annee: int

        :return: un dictionnaire des valeurs triées par catégories

        - ordre
            - pour chaque type de donnée (section, niveau...), l'ordre d'affichage voulu
        - pour l'établissement
            - effectif total
            - proportion de garçon
            - De même, hors BTS
            - proportion d'élèves issus de filière pro
        - par section
            - effectif total (ce qui donne reponse['section'][SECTION]['effectif'] = TOTAL)
            - poids / étab
            - proportion de redoublants
            - proportion de garçon
            - proportion de nouveaux
            - proportion d'élèves issus de section pro dans l'établissement
        - par niveau
            - _idem_
        - provenance
            - établissement : total d'élèves, total d'élèves actuellement en seconde


        Validation des résultats par SQL

        - Nb d'élèves issus de pro / classe
            > SELECT Classe,Niveau,Filière,Section,count(*) NbIssueDePro FROM Affectations NATURAL JOIN Classes WHERE INE IN (SELECT INE FROM Affectations A LEFT JOIN Classes C ON A.Classe = C.Classe WHERE  Année=2012 AND Filière='Pro') AND Année = 2013 GROUP BY Classe
        - Dénombrement des élèves / établissement d'origine
            > SELECT Établissement,count(*) NbÉlèvesEnProvenance FROM Affectations WHERE INE IN (SELECT INE FROM Affectations A LEFT JOIN Classes C ON A.Classe = C.Classe WHERE Niveau="Seconde" AND Année=<ANNEE>) AND Année=<ANNEE>-1 GROUP BY Établissement
        - Nombre d'années de scolarisation / élève
            > SELECT INE,count(*) FROM Affectations WHERE Établissement="Jean Moulin" GROUP BY INE
        """

        # Récupération des infos : classes, effectif...
        classes = self.server.db.lire_classes()
        classes_pro = filtrer_dict(classes, 'Filière', 'Pro')
        data = {}
        total_scol = 0
        # Pour chaque élève
        for d in self.server.db.lire().values():
            p = d['Parcours']
            if d['Genre'] == 2: # une femme
                h = (0,1)
            else: # == 1
                h = (1,0)
            doub = p[annee][2]
            if doub == 9: doub = 0

            nouveau = 0
            frompro = 0
            if annee-1 in p:
                etab_1 = p[annee-1][1]
                if etab_1 != self.server.nom_etablissement:
                    nouveau = 1
                else:
                    classe = p[annee-1][0]
                    if classe in classes_pro: frompro = 1

            t = [ h[0], h[1], doub, nouveau, frompro ] # Nb : garçon, fille, doublant, nouveau, issu de pro
            classe = p[annee][0]
            if classe in data:
                data[classe] = [sum(x) for x in zip(data[classe], t)] # data[classe] += t
            else:
                data[classe] = t
            # Nombre d'années de scolarisation
            for b in p.values():
                if b[1] == self.server.nom_etablissement:
                    total_scol = total_scol + 1
        logging.debug(data)

        # On génère maintenant le tableau de statistiques
        rep = { 'ordre': {},
                'établissement': {},
                'section': {}, 
                'niveau': {},
                'provenance': {} }
        # Ordre d'affichage des colonnes
        rep['ordre']['niveau'] = rep['ordre']['section'] = \
            ['effectif', 'poids', 'garçon', 'doublant', 'nouveau', 'issue de pro']
        rep['ordre']['provenance'] = ['total', 'en seconde']
        # Calculs
        eff_total = sum([sum(x[:2]) for x in data.values()]) # Effectif total
        eff_total_bts = 0
        total_garcon = 0
        total_garcon_bts = 0
        total_doublant = 0
        total_issue_de_pro = 0
        # Pour chaque classe
        for cla, val in sorted(data.items()):
            g, f, doub, nouveau, frompro = val
            eff = g + f
            section_classe = classes[cla]['Section']
            niveau_classe = classes[cla]['Niveau']
            total_garcon = total_garcon + g
            total_doublant = total_doublant + doub
            total_issue_de_pro = total_issue_de_pro + frompro
            #tp = self.server.db.taux_de_passage(cla)

            # Par Section
            if section_classe:
                if not section_classe in rep['section']:
                    rep['section'][section_classe] = {}
                dict_add(rep['section'][section_classe], 'effectif', eff)
                dict_add(rep['section'][section_classe], 'garçon', g)
                dict_add(rep['section'][section_classe], 'doublant', doub)
                dict_add(rep['section'][section_classe], 'nouveau', nouveau)
                dict_add(rep['section'][section_classe], 'issue de pro', frompro)
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
                dict_add(rep['niveau'][niveau_classe], 'nouveau', nouveau)
                dict_add(rep['niveau'][niveau_classe], 'issue de pro', frompro)

        # Calcul des proportions : Poids, Garçon, Doublant
        for key, val in rep['section'].items():
            rep['section'][key]['poids'] = en_pourcentage(val['effectif']/eff_total)
            rep['section'][key]['garçon'] = en_pourcentage(val['garçon']/val['effectif'])
            rep['section'][key]['doublant'] = en_pourcentage(val['doublant']/val['effectif'])
            rep['section'][key]['nouveau'] = en_pourcentage(val['nouveau']/val['effectif'])
            rep['section'][key]['issue de pro'] = en_pourcentage(val['issue de pro']/val['effectif'])
        for key, val in rep['niveau'].items():
            rep['niveau'][key]['poids'] = en_pourcentage(val['effectif']/eff_total)
            rep['niveau'][key]['garçon'] = en_pourcentage(val['garçon']/val['effectif'])
            rep['niveau'][key]['doublant'] = en_pourcentage(val['doublant']/val['effectif'])
            rep['niveau'][key]['nouveau'] = en_pourcentage(val['nouveau']/val['effectif'])
            rep['niveau'][key]['issue de pro'] = en_pourcentage(val['issue de pro']/val['effectif'])
        # Pour l'établissement
        eff_hors_bts = eff_total - eff_total_bts
        rep['établissement']['Effectif total'] = eff_total
        rep['établissement']['Proportion garçon'] = en_pourcentage(total_garcon / eff_total)
        a = (total_garcon - total_garcon_bts)/eff_hors_bts
        rep['établissement']['Proportion garçon (hors BTS)'] = en_pourcentage(a)
        rep['établissement']['Proportion doublant'] = en_pourcentage(total_doublant / eff_total)
        rep['établissement']['Proportion issue de Pro'] = en_pourcentage(total_issue_de_pro / eff_total)
        rep['établissement']['Années de scolarisation moyennes par élève'] = str(round(total_scol / eff_total, 1)) + ' ans'
        # Provenance
        aff = self.server.db.lire_affectations()
        annee_pre = annee-1
        for k,v in aff.items():
            annee_aff = v['Année']
            etab = v['Établissement']
            if not etab in rep['provenance']:
                rep['provenance'][etab] = {'en seconde':0, 'total':0}
            if annee_aff == annee_pre: # On ne compte que les affectations de l'année précédente
                dict_add(rep['provenance'][etab], 'total', 1)
            elif annee_aff == annee:
                if v['Niveau'] == "Seconde": # Pour les élèves de seconde...
                    a = v['INE']+'__'+str(annee_pre)
                    if a in aff:
                        #... on recherche l'établissement de l'année précédent (si possible)
                        etab_pre = aff[a]['Établissement']
                        if not etab_pre in rep['provenance']:
                            rep['provenance'][etab_pre] = {'en seconde':0, 'total':0}
                        dict_add(rep['provenance'][etab_pre], 'en seconde', 1)
        return rep

    def importer_xml(self, data):
        """
            Parse le xml à importer

        :param data: le fichier à importer (passé en POST)
        :type data: flux de fichier xml
        """
        self.server.nb_import = 0
        les_classes = list(self.server.db.lire_classes().keys())
        classes_a_ajouter = []
        # Écriture de l'xml dans un fichier
        fichier_tmp = 'importation.xml'
        f = open(fichier_tmp, 'w', encoding='ISO-8859-15')
        f.write(data)
        f.close()
        # Parsing
        tree = ET.parse(fichier_tmp)
        root = tree.getroot()
        self.server.maj_date( debut_AS( int(root.findtext('.//PARAMETRES/ANNEE_SCOLAIRE')) ) )
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
            if self.server.db.ecrire(enr, self.server.date, self.server.nom_etablissement):
                self.server.nb_import = self.server.nb_import + 1
            if not (classe in les_classes or classe in classes_a_ajouter or classe is None) :
                classes_a_ajouter.append(classe)
        # Ici, les données élèves ont été importé ; il ne reste qu'à ajouter les classes inconnues
        self.server.db.ecrire_classes(classes_a_ajouter)
