#!/usr/bin/python
# -*- coding: utf-8  -*-
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
import matplotlib
# On force le mode de matplotlib pour les serveurs sans serveur X
matplotlib.use('Agg')
from pylab import *

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
        # Fonctions autorisées
        if params.path == '/init':
            rep = {
                'header': self.server.header,
                'situations': self.server.situations,
                'niveaux' : self.server.niveaux,
                'eps' : self.server.db.lire_classes(self.server.date.year, niveau='eps'),
                'activités' : self.server.eps_activites }
            self.repondre(rep)
            return True
        elif params.path == '/liste-annees':
            rep = self.server.db.lister('Année')
            if len(rep) == 0: # Base non encore initialisée!
                rep = [self.server.date.year]
            self.repondre(rep)
            return True
        # On vérifie que le cookie n'a pas expiré
        now = datetime.datetime.now()
        ip = self.client_address[0]
        if ip in self.server.cookie:
            if self.server.cookie[ip].output(attrs='session') == '':
                return
            #expires = datetime.datetime.strptime(self.server.cookie[ip]['expires'], "%a, %d-%b-%Y %H:%M:%S PST")
            user = self.server.cookie[ip].value
            # Fonctions à accès limité
            if params.path == '/liste' and user == 'admin':
                annee = int(query.get('annee', ['{0}'.format(self.server.date.year)]).pop())
                orderby = query.get('col', ['Nom,Prénom']).pop()
                if orderby == '': orderby = 'Nom,Prénom'
                if orderby == 'Âge': orderby = 'Naissance'
                sens = query.get('sens', ['ASC']).pop().upper()
                if sens == '': sens = 'ASC'
                niveau = query.get('niveau', ['']).pop()
                rep = self.generer_liste(annee, orderby, sens, niveau)
            elif params.path == '/stats':
                stat = query['stat'].pop()
                if user == 'admin' or (stat == 'EPS (activite)' and user == 'eps'):
                    annee = query.get('annee', [self.server.date.year]).pop()
                    niveaux = query.get('niveaux', ['0']).pop().split(',')
                    rep = self.generer_stats(stat, int(annee), niveaux)
            elif params.path == '/maj' and (user == 'admin' or user == 'eps'):
                ine = query['ine'].pop()
                champ = query['champ'].pop()
                d = query.get('d', ['-1']).pop()
                table = 'Élèves'
                champ_can = champ.split(' ')[0] # Champ canonique = que la première partie
                if champ_can == 'Situation':
                    donnee = self.server.situations[int(d)]
                elif champ_can == 'Diplômé' or champ_can == 'Lieu':
                    donnee = d
                elif champ_can == 'Activité':
                    donnee = list(self.server.eps_activites.keys())[int(d)]
                    table = 'EPS'
                elif champ_can == 'Note':
                    donnee = d.replace(',', '.') # virgule anglo-saxone
                    if float(donnee) > 20.0 or float(donnee) < 0.0:
                        self.repondre('Non')
                        return
                    table = 'EPS'
                else:
                    self.repondre('Non')
                    return
                if d == '-1': donnee = '' # Cas d'une RAZ
                rep = self.server.db.maj_champ(table, ine, champ, donnee)
            elif params.path == '/maj_classe' and user == 'admin':
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
            elif params.path == '/eps':
                classe = query.get('classe', ['']).pop()
                if classe == '': eps = '' # Pas de classe, pas de chocolat
                else: eps = self.server.db.lire_eps(self.server.date.year, classe)
                rep = { 'liste': eps }
            elif params.path == '/pending' and user == 'admin':
                rep = self.server.db.lire_pending()
            elif params.path == '/options' and user == 'admin':
                rep = { 'affectations': self.server.db.lire_classes(self.server.date.year), 
                    'niveaux': self.server.niveaux,
                    'sections': self.server.sections }
            elif params.path == '/quitter':
                logging.info('Déconnection du client {0}'.format(ip))
                if ip in self.server.cookie:
                    self.server.cookie.pop(ip)
                rep = 'Vous pouvez éteindre votre navigateur et reprendre une activité normale.'
                self.repondre(rep)
                return
            else:
                # Par défaut, on sert le fichier
                http.server.SimpleHTTPRequestHandler.do_GET(self)
                return True
            self.maj_cookie(ip) # On renouvèle le cookie après l'utilisation d'une fonction
            self.repondre(rep)
        else:
            # Autre pages (on ne sert que les fichiers)
            http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        """ Traitement des POST """
        #http://pymotw.com/2/BaseHTTPServer/
        rep = { 'statut': 1, 'message': '' };
        form = cgi.FieldStorage(
            fp=self.rfile, 
            headers=self.headers,
            environ={'REQUEST_METHOD':'POST',
                     'CONTENT_TYPE':self.headers['Content-Type'],
                     })
        if self.path == '/auth':
            now = datetime.datetime.now()
            ip = self.client_address[0]
            # On vérifie le nombre de connexions récentes ...
            if ip in self.server.auth_tries:
                a = {}
                for at in self.server.auth_tries[ip]:
                    if now - at <= datetime.timedelta(minutes=30):
                        if ip in a: a.append(at)
                        else:       a = [at]
                self.server.auth_tries[ip] = a
            else:
                self.server.auth_tries[ip] = [now]
            if len(self.server.auth_tries[ip]) < 6: # s'il y en a pas eu trop
                login = ''
                user = ''
                if ip in self.server.cookie:
                    user = self.server.cookie[ip].value
                if len(user) > 0:
                    # Déjà authentifié
                    login = user
                else:
                    # Test du mdp
                    mdp = form.getvalue('mdp')
                    if mdp == self.server.mdp_admin:
                        login = 'admin'
                    elif mdp == self.server.mdp_eps:
                        login = 'eps'
                    else:
                        rep['message'] = 'Mauvais mot de passe'
                if login != '': rep = self.authentifier(login, ip, rep)
            else: # Blocage !
                logging.warning('Trop d\'authentifications. Bloquage de {0}.'.format(self.client_address[0]))
                return False
        elif self.path == '/importation':
            data = form.getvalue('data')
            logging.info('Importation du fichier...')
            self.importer_xml(data)
            rep['statut'] = 0
            rep['message'] = "L'importation s'est bien terminée."
        self.repondre(rep)

    def maj_cookie(self, ip):
        """
            Mise à jour de la date d'expiration du cookie
        :param ip: adresse IP du client
        :type ip: str
        """
        expiration = datetime.datetime.now() + datetime.timedelta(minutes=10)
        self.server.cookie[ip]['expires'] = expiration.strftime("%a, %d-%b-%Y %H:%M:%S PST")

    def authentifier(self, user, ip, rep):
        """
            Authentifie un utilisateur
        :param user: le nom de l'utilisateur
        :param ip: son adresse IP
        :param rep: la réponse à retourner
        :type user: str
        :type ip: str
        :type rep: dict
        """
        self.server.cookie[ip] = user
        self.maj_cookie(ip)
        rep['statut'] = 0
        rep['message'] = user
        logging.info('Authentification de {0} depuis {1}'.format(user, self.client_address[0]))
        return rep

    def repondre(self, reponse):
        """
            Envoie une réponse http [sic]

        :param reponse: la réponse
        :type reponse: objet, généralement str ou dictionnaire
        """
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(bytes(json.dumps(reponse), 'UTF-8'))
        self.wfile.flush()

    def generer_liste(self, annee, orderby, sens, niveau):
        """
            Génère les données pour la liste (vue principale)

        :param annee: année de scolarisation
        :param orderby: clé de tri
        :param sens: ordre de tri (ASC ou DESC)
        :param niveau: groupe de classes
        :type annee: int
        :type orderby: str
        :type sens: str
        :type niveau: str
        :return: annee, tableau au format html, et nombre total d'élèves
        :rtype: dict
        """
        if sens == 'ASC':
            data = self.server.db.lire(annee, orderby, sens, niveau)
            self.server.lire = data
        elif sens == 'DESC':
            # On inverse simplement la recherche précédente ; gain de temps de ~30 %
            ordre = list(self.server.lire.keys())[::-1]
            c = collections.OrderedDict.fromkeys(ordre)
            for a in ordre:
                c[a] = self.server.lire[a]
            data = c
        r = ''
        parite = ''
        for ine,d in data.items():
            d['Genre'] = 'Homme' if d['Genre'] == 1 else 'Femme'
            d['Année'] = annee
            s = ''
            # Analyse du parcours
            parcours = collections.OrderedDict()
            parcours_inverse = collections.OrderedDict(sorted(d['Parcours'].items(), key=lambda t: t[0], reverse=True))
            for an,p in parcours_inverse.items():
                if sens == 'ASC':
                    if p[2] == 0:   p[2] = 'Non'
                    elif p[2] == 1: p[2] = 'Oui'
                    else:           p[2] = '?'
                if an not in parcours.keys():
                    parcours[an] = { 'Année': an, 'Classe': p[0], 'Établissement': p[1], 'Doublement': p[2] }
            d['Classe'] = parcours[annee]['Classe']
            d['Établissement'] = parcours[annee]['Établissement']
            d['Doublement'] = parcours[annee]['Doublement']
            # Construction de la première ligne
            for h in self.server.header:
                if h in ['Année', 'Classe', 'Établissement', 'Doublement']:
                    s = s + '<td>{0}</td>'.format(parcours[annee][h])
                elif h in ['Diplômé', 'Lieu']:
                    s = s + '<td contenteditable="true">{0}</td>'.format(d[h])
                else:
                    s = s + '<td>{0}</td>'.format(d[h])
            # Construction des lignes / sous-lignes
            for a,p in parcours.items():
                if a != annee:
                    s = s + '<tr class="sousligne"><td colspan="5"></td><td>{0}</td><td>{1}</td><td>{2}</td><td>{3}</td><td colspan="4"></td></tr>\n'.format(a,p['Classe'],p['Établissement'],p['Doublement'])
            parite = 'paire' if parite == 'impaire' else 'impaire'
            r = r + '<tr id="{0}" class="{1}">{2}</tr>\n'.format(ine, parite, s)
        return { 'annee': annee, 'html': r, 'nb eleves': len(data) }

    def generer_stats(self, stat, annee, niveaux):
        """
            Génère des statistiques sur la base

        :param stat: La stat recherchée
        :param annee: L'année de recherche
        :param niveaux: Les niveaux sur lesquels faire la recherche
        :type stat: str
        :type annee: int
        :type niveaux: array(str)

        :rtype: dict
        :return: 'data'  : [ les données à afficher ],
                 'ordre' : [ (ordre d'affichage des colonnes, type de donnees) ]

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
        if stat == 'ouverture':
            # Ouverture de la page stat
            # on envoie juste la proportion de classes affectées
            o = self.server.db.stats('ouverture', annee, les_niveaux).pop()
            if o['n'] is not None and o['total'] != '0': # Cas d'une base non initialisée
                rep['data'] = round( (100*o['n']) / (o['total']*2) , 0)
            else: rep['data'] = 0
        elif stat == 'Général':
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
            rep['ordre'] = [('niveau','string'),
                            ('effectif','int'),
                            ('poids','float'),
                            ('homme','float'),
                            ('doublant','float'),
                            ('nouveau','float'),
                            ('issue de pro','float')]
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
            rep['ordre'] = [('section','string'),
                            ('effectif','int'),
                            ('poids','float'),
                            ('homme','float'),
                            ('doublant','float'),
                            ('nouveau','float'),
                            ('issue de pro','float')]
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
            rep['ordre'] = [('Établissement','string'),
                            ('total','int'),
                            ('en seconde','int')]
            rep['data'] = self.server.db.stats('provenance', annee, les_niveaux)
        elif stat == 'Provenance (classe)':
            rep['ordre'] = [('classe', 'string'),
                            ('provenance','string'),
                            ('MEF','string'),
                            ('Établissement','string'),
                            ('total','int'),
                            ('liste','string')]
            rep['data'] = self.server.db.stats('provenance classe', annee, les_niveaux)
        elif stat == 'Taux de passage':
            rep['ordre'] = [('section','string'),
                            ('passage','string'),
                            ('taux','float')]
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
        elif stat == 'EPS (activite)':
            rep['ordre'] = [('activité','string'),
                            ('moyenne','float'),
                            ('effectif','int')]
            rep['data'] = []
            act = self.server.db.stats('eps activite', annee, les_niveaux)
            for a in self.server.eps_activites.keys():
                somme = 0
                eff= 0
                for b in act: # pour chaque ligne
                    for c in b: # pour chaque activité
                        if b[c] == a: # si on trouve l'activité
                            somme = somme + b['n{0}'.format(c.split(' ')[1])]
                            eff = eff + b['nombre']
                if eff != 0: moyenne = round(somme/eff,2)
                else: moyenne = '?'
                v = { 'activité': a, 'moyenne': moyenne, 'effectif': eff}
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
        :type titre: str
        :return: le nom du fichier généré
        :rtype: str
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
        :type titre: str
        :return: le nom du fichier généré
        :rtype: str
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
        les_classes = list(self.server.db.lire_classes(self.server.date.year).keys())
        classes_a_ajouter = []
        # Écriture de l'xml dans un fichier
        fichier_tmp = 'cache/importation.xml'
        f = open(fichier_tmp, 'w', encoding='ISO-8859-15')
        f.write(data)
        f.close()
        # Parsing du fichier
        tree = ET.parse(fichier_tmp)
        root = tree.getroot()
        # Nettoyage, si ce n'est pas un import d'une année précédente
        annee = int(root.findtext('.//PARAMETRES/ANNEE_SCOLAIRE'))
        pending = False
        if self.server.date.year == annee:
            pending = True
            self.server.db.vider_pending()
        # Traitement des données
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
            mef = xstr(eleve.findtext('CODE_MEF'))
            doublement = eleve.findtext('DOUBLEMENT')
            j, m, entrée = eleve.findtext('DATE_ENTREE').split('/')
            classe = root.findtext(".//*[@ELEVE_ID='{0}']/STRUCTURE[TYPE_STRUCTURE='D']/CODE_STRUCTURE".format(eid))
            sad_etab = xstr(eleve.findtext('SCOLARITE_AN_DERNIER/DENOM_COMPL')).title()
            sad_classe = xstr(eleve.findtext('SCOLARITE_AN_DERNIER/CODE_STRUCTURE')).strip(' ')
            sad_mef = xstr(eleve.findtext('SCOLARITE_AN_DERNIER/CODE_MEF'))
            enr = { 'eid': eid, 'ine': ine, 'nom': nom, 'prénom': prenom, \
                    'naissance': naissance, 'genre': genre, 'mail': mail, 'mef': mef, \
                    'doublement': doublement, 'classe': classe, 'entrée': entrée, \
                    'sad_établissement': sad_etab,   'sad_classe': sad_classe,  'sad_mef': sad_mef }
            self.server.db.ecrire(enr, annee, pending)
            if not (classe in les_classes or classe in classes_a_ajouter or classe is None) :
                classes_a_ajouter.append(classe)
        # Ici, les données élèves ont été importé ; il ne reste qu'à ajouter les classes inconnues
        self.server.db.ecrire_classes(classes_a_ajouter, self.server)
