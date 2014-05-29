#!/usr/bin/python
# -*- coding: utf-8  -*-
import time
import logging
import statistics
#web
import http.server
import json
import urllib
from urllib.parse import urlparse, parse_qs
import xml.etree.ElementTree as ET
#lib spécifique
from liblegion import *

class HttpHandler(http.server.SimpleHTTPRequestHandler):
    """
        Traite les requêtes HTTP issues du serveur web

        self.server est une référence vers le serveur d'origine
    """
    def do_GET(self):
        """ Traitement des GET """
        # Analyse de l'url
        params = urlparse(self.path)
        query = parse_qs(params.query)
        rep = "";
        if params.path == '/liste':
            rep = { 'annee': self.server.date.year, 'data': self.server.db.lire() }
        elif params.path == '/stats':
            stat = query['stat'].pop()
            annee = query['annee'].pop()
            niveaux = query['niveaux'].pop().split(',')
            rep = self.generer_stats(stat, int(annee), niveaux)
        elif params.path == '/maj':
            ine = query['ine'].pop()
            champ = query['champ'].pop()
            if 'd' in query:
                donnee = query['d'].pop()
            else:
                donnee = ''
            if champ == 'Situations': donnee = self.server.situations[int(donnee)]
            rep = self.server.db.maj_champ('Élèves', ine, champ, donnee)
        elif params.path == '/maj_classe':
            classe = query['classe'].pop()
            champ = query['champ'].pop()
            # Traduction du val (qui n'est qu'un index)
            if 'val' in query: # val peut être vide
                if champ == 'Niveau':    les = self.server.niveaux
                elif champ == 'Section': les = self.server.sections
                val = query['val'].pop()
                if val != '' and int(val) < len(les):
                    val = les[int(val)]
            else:
                val = ''
            # MAJ
            rep = self.server.db.maj_champ('Classes', classe, champ, val)
            # En cas de la modification d'une section, il faux modifier la filière en conséquence
            if champ == "Section":
                if val == '?':
                    fil = ''
                else:
                    fil = self.server.section_filière[val]
                self.server.db.maj_champ('Classes', classe, "Filière", fil)
        elif params.path == '/pending':
            rep = self.server.db.lire_pending()
        elif params.path == '/liste-annees':
            rep = self.server.db.lister('Année')
        elif params.path == '/options':
            rep = { 'affectations': self.server.db.lire_classes(), 
                'niveaux': self.server.niveaux,
                'sections': self.server.sections }
        elif params.path == '/init':
            rep = {
                    'header': self.server.header,
                    'situations': self.server.situations,
                    'niveaux' : self.server.niveaux }
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
            rep = u"L'importation s'est bien terminée."
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

    def generer_stats(self, stat, annee, niveaux):
        """
            Génère des statistiques sur la base

        :param stat: La stat recherchée
        :param annee: L'année de recherche
        :param niveaux: Les niveaux sur lesquels faire la recherche
        :type stat: str
        :type annee: int
        :type niveaux: array(str)

        :return: dict(  'data'  : [ les données à afficher ],
                        'ordre' : [ ordre d'affichage des colonnes ] }

        - pour l'établissement
            - effectif total
            - proportion de garçon
            - De même, hors BTS
            - proportion d'élèves issus de filière pro
        - par section
            - effectif total
            - poids / étab
            - proportion de redoublants
            - proportion de garçon
            - proportion de nouveaux
            - proportion d'élèves issus de section pro dans l'établissement
        - par niveau
            - _idem_
        - provenance et provenance par classe
            - établissement : total d'élèves, total d'élèves actuellement en seconde
        - taux de passage :
            - le taux de passage pour chaque transition de classe dans une même section
        """
        # Liste des niveaux à prendre en compte au format textuel
        les_niveaux = [self.server.niveaux[int(n)] for n in niveaux]
        totaux = self.server.db.stats('totaux', annee, les_niveaux).pop()
        eff_total = totaux['total'] # Effectif total

        rep = { 'ordre': {}, 'data': {} }
        if stat == 'Général':
            total_homme = totaux['homme'] # Nombre total d'hommes
            total_doublant = totaux['doublant']
            #total_nouveau = totaux['nouveau']
            total_issue_de_pro = totaux['issue de pro']
            # TODO : pour cette stat, ajouter un taux de confiance

            #rep['ordre'] = []
            rep['data']['Effectif'] = eff_total
            rep['data']['Proportion garçon'] = en_pourcentage(total_homme / eff_total)
            rep['data']['Proportion doublant'] = en_pourcentage(total_doublant / eff_total)
            #rep['data']['Proportion issue de Pro'] = en_pourcentage(total_issue_de_pro / eff_total)
            # Années de scolarisation moyenne par élève
            a = statistics.mean([x['Scolarisation'] for x in self.server.db.stats('annees scolarisation', annee, les_niveaux)])
            rep['data']['Années de scolarisation moyenne par élève'] = str(round( a, 2 )) + ' ans'
        elif stat == 'Par niveau':
            rep['ordre'] = ['niveau', 'effectif', 'poids', 'homme', 'doublant', 'nouveau', 'issue de pro']
            rep['data'] = []
            for d in self.server.db.stats('par niveau', annee, les_niveaux):
                a = {}
                a['niveau'] = d['Niveau']
                if a['niveau'] == '': a['niveau'] = '<i>Inconnu</i>'
                a['effectif'] = d['effectif']
                a['poids'] = en_pourcentage(d['effectif'] / eff_total)
                a['homme'] = en_pourcentage(d['homme'] / d['effectif'])
                a['doublant'] = en_pourcentage(d['doublant'] / d['effectif'])
                a['nouveau'] = en_pourcentage(d['nouveau'] / d['effectif'])
                if a['niveau'] == '1BTS' or a['niveau'] == '2BTS':
                    a['issue de pro'] = en_pourcentage(d['issue de pro'] / d['effectif'])
                else:
                    a['issue de pro'] = ''
                rep['data'].append(a)
        elif stat == 'Par section':
            rep['ordre'] = ['section', 'effectif', 'poids', 'homme', 'doublant', 'nouveau', 'issue de pro']
            rep['data'] = []
            for d in self.server.db.stats('par section', annee, les_niveaux):
                a = {}
                a['section'] = d['Section']
                if a['section'] == '': a['section'] = '<i>Inconnue</i>'
                a['effectif'] = d['effectif']
                a['poids'] = en_pourcentage(d['effectif'] / eff_total)
                a['homme'] = en_pourcentage(d['homme'] / d['effectif'])
                a['doublant'] = en_pourcentage(d['doublant'] / d['effectif'])
                a['nouveau'] = en_pourcentage(d['nouveau'] / d['effectif'])
                sf = self.server.section_filière
                if a['section'] in sf and sf[a['section']] == 'Enseignement supérieur':
                    a['issue de pro'] = en_pourcentage(d['issue de pro'] / d['effectif'])
                else:
                    a['issue de pro'] = ''
                rep['data'].append(a)
        elif stat == 'Provenance':
            rep['ordre'] = ['Établissement', 'total', 'en seconde']
            rep['data'] = self.server.db.stats('provenance', annee, les_niveaux)
        elif stat == 'Provenance (classe)':
            rep['ordre'] = ['classe', 'provenance', 'Établissement', 'total']
            rep['data'] = self.server.db.stats('provenance classe', annee, les_niveaux)
        elif stat == 'Taux de passage':
            rep['ordre'] = ['section', 'passage', 'taux']
            rep['data'] = []
            passage = self.server.db.stats('taux de passage', annee, les_niveaux)
            for sect in self.server.sections:
                # On filtre les éléments de data concernant la section voulue
                e = [dictio for dictio in passage if dictio['Section'] == sect]
                for i in range(1,len(self.server.niveaux)):
                    niv = self.server.niveaux[i]
                    niv_pre = self.server.niveaux[i-1]
                    # Élèves au niveau niv de la section sect pour l'année en cours
                    f = [dictio['INE'] for dictio in e if dictio['Niveau'] == niv and dictio['Année'] == annee]
                    # Élèves au niveau précédent de la même section pour l'année passée
                    g = [dictio['INE'] for dictio in e if dictio['Niveau'] == niv_pre and dictio['Année'] == annee-1]
                    if len(f) > 0 and len(g) > 0:
                        # On a des élèves dans deux années successives d'une même section !
                        communs = list (set(g) & set(f)) # l'intersection des deux années
                        taux = en_pourcentage( float(len(communs)) / float(len(g)) )
                        v = { 'section': sect, 'passage': niv_pre+' > '+niv, 'taux': taux}
                        rep['data'].append(v)
        else:
            logging.error('Statistique {0} inconnue'.format(stat))

        #logging.debug(rep)
        return rep

    def importer_xml(self, data):
        """
            Parse le xml à importer

        :param data: le fichier à importer (passé en POST)
        :type data: flux de fichier xml
        """
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
            sortie = eleve.findtext('DATE_SORTIE')
            if sortie and sortie.split('/')[1] == '09':
                # Si la date de sortie est en septembre, il s'agit d'un élève affecté automatiquement au lycée
                # mais qui est parti dans un autre
                # => On laisse tomber
                continue
            eid = eleve.get('ELEVE_ID')
            ine = eleve.findtext('ID_NATIONAL')
            nom = eleve.findtext('NOM')
            prenom = eleve.findtext('PRENOM')
            naissance = eleve.findtext('DATE_NAISS')
            genre = eleve.findtext('CODE_SEXE')
            mail = xstr(eleve.findtext('MEL'))
            doublement = eleve.findtext('DOUBLEMENT')
            j, m, entrée = eleve.findtext('DATE_ENTREE').split('/')
            classe = root.findtext(".//*[@ELEVE_ID='{0}']/STRUCTURE[TYPE_STRUCTURE='D']/CODE_STRUCTURE".format(eid))
            sad_etab = xstr(eleve.findtext('SCOLARITE_AN_DERNIER/DENOM_COMPL')).title()
            sad_classe = xstr(eleve.findtext('SCOLARITE_AN_DERNIER/CODE_STRUCTURE')).strip(' ')
            enr = { 'eid': eid, 'ine': ine, 'nom': nom, 'prénom': prenom, \
                    'naissance': naissance, 'genre': genre, 'mail': mail, \
                    'doublement': doublement, 'classe': classe, 'entrée': entrée, \
                    'sad_établissement': sad_etab,   'sad_classe': sad_classe }
            self.server.db.ecrire(enr, self.server.date)
            if not (classe in les_classes or classe in classes_a_ajouter or classe is None) :
                classes_a_ajouter.append(classe)
        # Ici, les données élèves ont été importé ; il ne reste qu'à ajouter les classes inconnues
        self.server.db.ecrire_classes(classes_a_ajouter)
