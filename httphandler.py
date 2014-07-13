#!/usr/bin/python
# -*- coding: utf-8  -*-
import time
import logging
#import statistics
import numpy
import collections # OrderedDict
#web
import http.server
import json
import urllib
from urllib.parse import urlparse, parse_qs
import xml.etree.ElementTree as ET
import cgi, http.cookies
#lib spécifique
from liblegion import *
#graphiques
from pylab import *
import os
import numpy as np

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
        try:
            a = self.server.cookie["session"].value
        except (http.cookies.CookieError, KeyError):
            print("session cookie not set!")
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
            if champ == 'Situation': donnee = self.server.situations[int(donnee)]
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
                if val == '?' or val == '':
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
        #http://pymotw.com/2/BaseHTTPServer/
        rep = "";
        form = cgi.FieldStorage(
            fp=self.rfile, 
            headers=self.headers,
            environ={'REQUEST_METHOD':'POST',
                     'CONTENT_TYPE':self.headers['Content-Type'],
                     })
        if self.path == '/auth':
            mdp = form.getvalue('mdp')
            print(mdp)
            print(self.server.mdp)
            if mdp == self.server.mdp:
                self.server.cookie['session'] = 'ok'
                expiration = datetime.datetime.now() + datetime.timedelta(minutes=30)
                self.server.cookie['session']['expires'] = expiration.strftime("%a, %d-%b-%Y %H:%M:%S PST")
                rep = 'reussie'
        elif self.path == '/importation':
            data = form.getvalue('data')
            logging.info('Importation du fichier...')
            self.importer_xml(data)
            rep = "L'importation s'est bien terminée."
        #else:
        #    return True
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
        # Suppression des fichiers de cache
        for root, dirs, filenames in os.walk('cache'):
            for f in filenames:
                os.remove(os.path.join(root, f))
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

        rep = { 'ordre': {}, 'data': {}, 'graph': [] }
        if stat == 'Général':
            total_homme = totaux['homme'] # Nombre total d'hommes
            total_doublant = totaux['doublant']
            #total_nouveau = totaux['nouveau']
            total_issue_de_pro = totaux['issue de pro']
            # TODO : pour cette stat, ajouter un taux de confiance ?

            accord = ''
            if eff_total > 1: accord = 's'
            rep['data']['Effectif'] = str(eff_total) + ' élève'+accord
            if eff_total != 0:
                rep['data']['Parité homme / femme'] = en_pourcentage(total_homme / eff_total)+' / '+en_pourcentage(1 - (total_homme/eff_total))
                rep['data']['Proportion de doublants'] = en_pourcentage(total_doublant / eff_total)
                #rep['data']['Proportion issue de Pro'] = en_pourcentage(total_issue_de_pro / eff_total)
                # Années de scolarisation moyenne par élève
                #a = statistics.mean([x['Scolarisation'] for x in self.server.db.stats('annees scolarisation', annee, les_niveaux)])
                a = numpy.mean([x['Scolarisation'] for x in self.server.db.stats('annees scolarisation', annee, les_niveaux)])
                rep['data']['Nb moyen d\'années de scolarisation par élève'] = str(round( a, 2 )) + ' ans'
                prop_homme = round(100*total_homme/eff_total,1)
                rep['graph'].append( self.generer_tarte(
                    { 'Homme': prop_homme, 'Femme': 100-prop_homme }, 'Parité' ) )
        elif stat == 'Par niveau':
            rep['ordre'] = ['niveau', 'effectif', 'poids', 'homme', 'doublant', 'nouveau', 'issue de pro']
            rep['data'] = []
            tarte = collections.OrderedDict.fromkeys(les_niveaux)
            histo = collections.OrderedDict.fromkeys(les_niveaux)
            for d in self.server.db.stats('par niveau', annee, les_niveaux):
                a = {}
                a['niveau'] = d['Niveau']
                g_niv = a['niveau']
                if a['niveau'] == '':
                    a['niveau'] = '<i>Inconnu</i>'
                    g_niv = '?'
                a['effectif'] = d['effectif']
                tarte[g_niv] = round(100*int(a['effectif']),1)

                a['poids'] = en_pourcentage(d['effectif'] / eff_total)
                a['homme'] = en_pourcentage(d['homme'] / d['effectif'])
                a['doublant'] = en_pourcentage(d['doublant'] / d['effectif'])
                
                a['nouveau'] = en_pourcentage(d['nouveau']/d['effectif'])
                histo[g_niv] = [ d['nouveau'], d['doublant'], d['effectif']-d['nouveau']-d['doublant'] ]

                if a['niveau'] == '1BTS' or a['niveau'] == '2BTS':
                    a['issue de pro'] = en_pourcentage(d['issue de pro'] / d['effectif'])
                else:
                    a['issue de pro'] = ''
                rep['data'].append(a)
            # Génération du graphique des effectifs
            rep['graph'].append(self.generer_tarte( tarte, 'Répartition des effectifs' ))
            rep['graph'].append(self.generer_histo( histo, 'Nombre de nouveaux élèves/doublants par niveau' ))
        elif stat == 'Par section':
            rep['ordre'] = ['section', 'effectif', 'poids', 'homme', 'doublant', 'nouveau', 'issue de pro']
            rep['data'] = []
            tarte = collections.OrderedDict.fromkeys(les_niveaux)
            histo = collections.OrderedDict.fromkeys(les_niveaux)
            for d in self.server.db.stats('par section', annee, les_niveaux):
                a = {}
                a['section'] = d['Section']
                g_niv = a['section']
                if a['section'] == '':
                    a['section'] = '<i>Inconnue</i>'
                    g_niv = '?'
                a['effectif'] = d['effectif']
                tarte[g_niv] = round(100*int(a['effectif']),1)

                a['poids'] = en_pourcentage(d['effectif'] / eff_total)
                a['homme'] = en_pourcentage(d['homme'] / d['effectif'])
                a['doublant'] = en_pourcentage(d['doublant'] / d['effectif'])

                a['nouveau'] = en_pourcentage(d['nouveau']/d['effectif'])
                histo[g_niv] = [ d['nouveau'], d['doublant'], d['effectif']-d['nouveau']-d['doublant'] ]

                sf = self.server.section_filière
                if a['section'] in sf and sf[a['section']] == 'Enseignement supérieur':
                    a['issue de pro'] = en_pourcentage(d['issue de pro'] / d['effectif'])
                else:
                    a['issue de pro'] = ''
                rep['data'].append(a)
            # Génération du graphique des effectifs
            rep['graph'].append(self.generer_tarte( tarte, 'Répartition des effectifs' ))
            rep['graph'].append(self.generer_histo( histo, 'Nombre de nouveaux élèves/doublants par section' ))
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

    def generer_tarte(self, proportions, titre):
        """
            Génère un graphique en tarte

        :param proportions: les proportions / 100
        :param titre: le titre du graphique
        :type proportions: list
        :type titre: string
        :return: le nom du fichier généré
        :rtype: string
        """
        fichier = generer_nom_fichier('cache/tarte_')
        # Création d'un espace de dessin
        figure(1, figsize=(6,6))
        ax = axes([0.1, 0.1, 0.8, 0.8])

        x = [] # les valeurs à afficher
        labels = [] # les intitulés correspondants
        for k in proportions:
            if proportions[k] is not None: # L'orderedDict créer automatiquement des cases vides
                x.append(proportions[k])
                labels.append(k)
        # Génération de la tarte
        pie(x,  labels=labels,
                colors=self.server.colors,
                autopct='%1.1f%%', # texte dans les parts
                pctdistance=0.8, # distance au centre des textes dans les parts
                shadow=True, startangle=90)
        title(titre, weight='demi') # Ajout d'un titre
        savefig(fichier, transparent=True) # Génération du fichier
        clf() # Nettoyage du graphique pour le run suivant
        return fichier

    def generer_histo(self, proportions, titre):
        """
            Génère un graphique en histogramme

        :param proportions: les proportions / 100
        :param titre: le titre du graphique
        :type proportions: dict
        :type titre: string
        :return: le nom du fichier généré
        :rtype: string
        """
        fichier = generer_nom_fichier('cache/histo_')
        x = [] # les valeurs à afficher
        doublants = [] # les doublants à ajouter au dessus
        reste = [] # le reste des élèves
        labels = [] # les intitulés correspondants
        for k in proportions:
            if proportions[k] is not None: # L'orderedDict créer automatiquement des cases vides
                x.append(proportions[k][0])
                doublants.append(proportions[k][1])
                reste.append(proportions[k][2])
                labels.append(k)
        pos = np.arange(len(labels))
        width = 0.8 # la largeur de chaque barre
        # Construction des axes
        ax = axes()
        ax.set_xticks(pos + (width / 2))
        ax.set_xticklabels(labels)
        ax.set_xlabel( titre, labelpad=12, weight='demi' )
        # Dessinnement
        bar(pos, x, width, color=self.server.colors)
        bar(pos, doublants, width, color='w', bottom=x)
        r=bar(pos, reste, width, color='0.8', bottom=numpy.sum( (x,doublants), 0), alpha=0.4)
        xlim(pos.min(), pos.max()+width) # On force l'affiche des colonnes vides
        leg = legend( [Rectangle((0, 0), 1, 1, fc="w"), Rectangle((0, 0), 1, 1, fc="0.8", alpha=0.4)], \
                ['Doublants', 'Restant'] ) # Légende
        leg.get_frame().set_alpha(0)

        savefig(fichier, transparent=True)
        clf()
        return fichier

    def importer_xml(self, data):
        """
            Parse le xml à importer

        :param data: le fichier à importer (passé en POST)
        :type data: flux de fichier xml
        """
        les_classes = list(self.server.db.lire_classes().keys())
        classes_a_ajouter = []
        # Écriture de l'xml dans un fichier
        fichier_tmp = 'cache/importation.xml'
        f = open(fichier_tmp, 'w', encoding='ISO-8859-15')
        f.write(data)
        f.close()
        # Nettoyage
        self.server.db.vider_pending()
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
