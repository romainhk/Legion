#!/usr/bin/python
# -*- coding: utf-8  -*-
import logging
import xlrd
import os
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
        rep = ""
        # Fonctions autorisées
        if params.path == '/init':
            # ACTION : Initialisation de l'application (côté client)
            rep = {
                'header': self.server.header,
                'situations': self.server.situations,
                'niveaux' : self.server.niveaux,
                'eps' : self.server.db.lire_classes(self.server.debut_AS.year, niveau='eps'),
                'activités' : self.server.eps_activites }
            self.repondre(rep)
            return True
        elif params.path == '/liste-annees':
            # ACTION : Renvoie la liste des années connues
            rep = self.server.db.lister('Année')
            if len(rep) == 0: # Base non encore initialisée!
                rep = [self.server.debut_AS.year]
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
                # ACTION : Ouverture de la liste principale
                annee = int(query.get('annee', ['{0}'.format(self.server.debut_AS.year)]).pop())
                niveau = query.get('niveau', ['']).pop()
                rep = self.generer_liste(annee, niveau)
            elif params.path == '/stats':
                # ACTION : Ouverture de la page de statistiques
                stat = query['stat'].pop()
                if user == 'admin' or (stat in ['ouverture', 'EPS (activite)'] and user == 'eps'):
                    annee = query.get('annee', [self.server.debut_AS.year]).pop()
                    niveaux = query.get('niveaux', ['0']).pop().split(',')
                    filiere = []
                    for i in query.get('filiere', ['']).pop():
                        if   i == 'G': filiere.append('Générale')
                        elif i == 'P': filiere.append('Pro')
                        elif i == 'T': filiere.append('Technologique')
                        elif i == 'S': filiere.append('Enseignement supérieur')
                    # Pour l'EPS, le découpage est en tier
                    if user == 'admin' and stat == "EPS (activite)":
                        n = []
                        if "Seconde" in niveaux: n.append('BEP')
                        if "Terminale" in niveaux: n.append('BAC')
                        niveaux = n
                    if len(''.join(('niveaux'))) < 45 and len(filiere) < 5:
                        rep = self.generer_stats(stat, int(annee), niveaux, filiere)
            elif params.path == '/maj' and (user == 'admin' or user == 'eps'):
                # ACTION : Mise à jour d'un champ
                ine = query['ine'].pop()
                champ = query['champ'].pop()
                d = query.get('d', ['']).pop()
                tier = query.get('tier', ['2']).pop()
                tier = 'BAC' if tier == '2' else 'BEP' 
                table = 'Élèves'
                champ_can = champ.split(' ')[0] # Champ canonique = que la première partie
                if champ_can == 'Situation':
                    if len(d) > 0: donnee = self.server.situations[int(d)]
                    else: donnee = ''
                elif champ_can == 'Diplômé' or champ_can == 'Lieu':
                    donnee = d
                elif champ_can == 'Activité':
                    donnee = list(self.server.eps_activites.keys())[int(d)]
                    table = 'EPS'
                elif champ_can == 'Note':
                    if d.strip(' ') == '': d = "-1"
                    elif d[0].upper() == 'A': d = "-2"
                    elif d[0].upper() == 'D': d = "-3"
                    donnee = d.replace(',', '.') # virgule anglo-saxone
                    if float(donnee) > 20.0 or float(donnee) < -3.0:
                        self.repondre('Non')
                        return
                    table = 'EPS'
                elif champ_can in ['Protocole', 'Date']:
                    donnee = d
                    table = 'EPS'
                else:
                    self.repondre('Non')
                    return
                rep = self.server.db.maj_champ(table, ine, champ, donnee, tier=tier)
            elif params.path == '/maj_classe' and user == 'admin':
                # ACTION : Changement d'affectation pour une classe
                classe = query['classe'].pop()
                champ = query['champ'].pop()
                # Traduction du val (qui n'est qu'un index)
                if 'val' in query: # val peut être vide
                    if champ == 'Niveau':    les = self.server.niveaux
                    elif champ == 'Section': les = self.server.sections
                    else: return False
                    val = query['val'].pop()
                    if val != '' and int(val) < len(les):
                        val = les[int(val)]
                else:
                    val = ''
                rep = self.server.db.maj_champ('Classes', classe, champ, val)
                # En cas de la modification d'une section, il faux modifier la filière en conséquence
                if champ == "Section":
                    if val == '?' or val == '':
                        fil = ''
                    else:
                        fil = self.server.section_filière[val]
                    self.server.db.maj_champ('Classes', classe, "Filière", fil)
            elif params.path == '/eps':
                # ACTION : Ouverture de la page EPS
                classe = query.get('classe', ['']).pop()
                tier = query.get('tier', ['2']).pop()
                val_tier = ''
                if   tier == '1': val_tier = 'BEP'
                elif tier == '2': val_tier = 'BAC'
                if classe == '': eps = '' # Pas de classe, pas de chocolat
                else:
                    eps = self.server.db.lire_eps(self.server.debut_AS.year, classe, val_tier)
                classes = self.server.db.lire_classes(self.server.debut_AS.year, niveau='eps')
                rep = { 'liste': eps, 'classes': classes, 'tier': tier }
            elif params.path == '/pending' and user == 'admin':
                # ACTION : Ouverture de la page de pending
                rep = { 'pending': self.server.db.lire_pending(),
                        'date': date8601(self.server.date) }
            elif params.path == '/options' and user == 'admin':
                # ACTION : Ouverture de la page des options
                annee = query.get('annee', [self.server.debut_AS.year]).pop()
                rep = { 'affectations': self.server.db.lire_classes(annee), 
                    'niveaux': self.server.niveaux,
                    'sections': self.server.sections,
                    'annee': annee }
            elif params.path == '/quitter':
                # ACTION : Fermeture de l'application
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
            logging.info('Importation de la base élève...')
            fichier_tmp = 'cache/importation.xml'
            for f in form.keys():
                data = form[f].value
                open(fichier_tmp, "wb").write(data)
            statut, message, tot_import = self.importer_xml(fichier_tmp)
            rep['statut'] = statut
            rep['message'] = message
            rep['tot_import'] = tot_import
        elif self.path == '/importation_diplome':
            data = form.getvalue('data')
            logging.info('Importation de la liste des diplômés...')
            fichier_tmp = 'cache/importation_diplome.xls'
            for f in form.keys():
                data = form[f].value
                open(fichier_tmp, "wb").write(data)
            statut, message, tot_import = self.importer_diplome(fichier_tmp)
            os.remove(fichier_tmp)
            rep['statut'] = statut
            rep['message'] = message
            rep['tot_import'] = tot_import
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
        :return: rep
        :rtype: dict
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

    def generer_liste(self, annee, niveau):
        """
            Génère les données pour la liste (vue principale)

        :param annee: année de scolarisation
        :param niveau: groupe de classes
        :type annee: int
        :type niveau: str
        :return: annee, tableau au format html, et nombre total d'élèves
        :rtype: dict
        """
        data = self.server.db.lire(annee, niveau)
        r = ''
        parite = ''
        tab_parcours = {}
        for ine,d in data.items():
            d['Sexe'] = '♂' if d['Sexe'] == 1 else '♀'
            d['Année'] = annee
            s = ''
            # Analyse du parcours
            parcours = collections.OrderedDict()
            parcours_inverse = collections.OrderedDict(sorted(d['Parcours'].items(), key=lambda t: t[0], reverse=True))
            for an,p in parcours_inverse.items():
                if p[2] == 0:   p[2] = 'Non'
                elif p[2] == 1: p[2] = 'Oui'
                else:           p[2] = '?'
                if an not in parcours.keys():
                    parcours[an] = { 'Année': an, 'Classe': p[0], 'Établissement': p[1], 'Doublement': p[2] }
            d['Classe'] = parcours[annee]['Classe']
            d['Établissement'] = parcours[annee]['Établissement']
            d['Doublement'] = parcours[annee]['Doublement']
            # Construction du parcours
            tab_parcours[ine] = ""
            for a,p in parcours.items():
                if a != annee:
                    tab_parcours[ine] = tab_parcours[ine] + \
                        '<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>{3}</td></tr>\n'.format(
                            '{0}-{1}'.format(int(a), int(a)+1),
                            p['Classe'], p['Établissement'], p['Doublement'])
            # Construction de la ligne (année en cours)
            for h in self.server.header:
                if h in ['Diplômé', 'Lieu']:
                    s = s + '<td contenteditable="true">{0}</td>'.format(d[h])
                elif h == 'Situation N+1':
                    # Génération du <select>
                    t = '<option value="">...</option>'
                    for i,b in enumerate(self.server.situations):
                        selected = ""
                        if b == d['Situation']: selected = ' selected="selected"'
                        t = t + '<option value="{1}"{2}>{0}</option>'.format(
                                b,     i,      selected)
                    s = s + '<td><select class="cell_to_select">{0}</select></td>'.format(t)
                else:
                    s = s + '<td>{0}</td>'.format(d[h])
            r = r + '<tr id="{0}">{1}</tr>\n'.format(ine, s)
        return { 'annee': annee, 'html': r, 'parcours': tab_parcours, 'nb eleves': len(data) }

    def generer_stats(self, stat, annee, niveaux, filiere):
        """
            Génère des statistiques sur la base

        :param stat: La stat recherchée
        :param annee: L'année de recherche
        :param niveaux: Les niveaux sur lesquels faire la recherche
        :param filiere: Les filières sur lesquelles faire la recherche
        :type stat: str
        :type annee: int
        :type niveaux: array(str)
        :type filiere: array(str)

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
        - par niveau, par situation
            - _idem_
        - provenance et provenance par classe
            - établissement : total d'élèves, total d'élèves actuellement en seconde
        - taux de passage :
            - le taux de passage pour chaque transition de classe dans une même section
        """
        # Liste des niveaux à prendre en compte au format textuel
        totaux = self.server.db.stats('totaux', annee, niveaux, filiere).pop()
        eff_total = totaux['total'] # Effectif total

        rep = { 'ordre': {}, 'data': {}, 'graph': [] }
        if stat == 'ouverture':
            # Ouverture de la page stat
            # on envoie juste la proportion de classes affectées
            o = self.server.db.stats('ouverture', annee, niveaux, filiere).pop()
            if o['n'] is not None and o['total'] != '0': # Cas d'une base non initialisée
                rep['data'] = round( (100*o['n']) / (o['total']*2) , 0)
            else: rep['data'] = 0
        elif stat == 'Général':
            total_homme = totaux['homme'] # Nombre total d'hommes
            total_doublant = totaux['doublant']
            #total_nouveau = totaux['nouveau']
            total_issue_de_pro = totaux['issue de pro']
            # TODO : pour cette stat, ajouter un taux de confiance ?
            bac_present = totaux['bac présent']
            bac_admis = totaux['bac admis']

            accord = ''
            if eff_total > 1: accord = 's'
            rep['data']['Effectif'] = str(eff_total) + ' élève'+accord
            if eff_total != 0:
                rep['data']['Parité homme / femme'] = en_pourcentage(total_homme / eff_total)+' / '+en_pourcentage(1 - (total_homme/eff_total))
                rep['data']['Proportion de doublants'] = en_pourcentage(total_doublant / eff_total)
                #rep['data']['Proportion issue de Pro'] = en_pourcentage(total_issue_de_pro / eff_total)
                # Années de scolarisation moyenne par élève
                #a = statistics.mean([x['Scolarisation'] for x in self.server.db.stats('annees scolarisation', annee, niveaux, filiere)])
                a = numpy.mean([x['Scolarisation'] for x in self.server.db.stats('annees scolarisation', annee, niveaux, filiere)])
                rep['data']['Nb moyen d\'années de scolarisation par élève'] = str(round( a, 2 )) + ' ans'
                if bac_present > 0:
                    rep['data']['Taux de réussite au BAC'] = en_pourcentage(bac_admis / bac_present)
                prop_homme = round(100*total_homme/eff_total,1)
                rep['graph'].append( self.generer_tarte(
                    { 'Homme': prop_homme, 'Femme': 100-prop_homme }, 'Parité' ) )
        elif stat == 'Par niveau':
            rep['ordre'] = [('niveau','string'),
                            ('effectif','int'),
                            ('poids','float'),
                            ('homme','float'),
                            ('doublant','float'),
                            ('nouveau','float')]
            rep['data'] = []
            avec_BTS = False
            tarte = collections.OrderedDict.fromkeys(niveaux)
            histo = collections.OrderedDict.fromkeys(niveaux)
            for d in self.server.db.stats('par niveau', annee, niveaux, filiere):
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
                    avec_BTS = True
                    a['issue de pro'] = en_pourcentage(d['issue de pro'] / d['effectif'])
                else:
                    a['issue de pro'] = ''

                rep['data'].append(a)
            if avec_BTS:
                rep['ordre'].append( ('issue de pro', 'float') )
            # Génération du graphique des effectifs
            rep['graph'].append(self.generer_tarte( tarte, 'Répartition des effectifs' ))
            rep['graph'].append(self.generer_histo( histo, 'Nombre de nouveaux élèves/doublants par niveau' ))
        elif stat == 'Par section':
            rep['ordre'] = [('section','string'),
                            ('effectif','int'),
                            ('poids','float'),
                            ('homme','float'),
                            ('doublant','float'),
                            ('nouveau','float')]
            rep['data'] = []
            avec_BTS = False
            tarte = collections.OrderedDict.fromkeys(niveaux)
            histo = collections.OrderedDict.fromkeys(niveaux)
            for d in self.server.db.stats('par section', annee, niveaux, filiere):
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
                    avec_BTS = True
                    a['issue de pro'] = en_pourcentage(d['issue de pro'] / d['effectif'])
                else:
                    a['issue de pro'] = ''
                rep['data'].append(a)
            if avec_BTS:
                rep['ordre'].append( ('issue de pro', 'float') )
            # Génération du graphique des effectifs
            rep['graph'].append(self.generer_tarte( tarte, 'Répartition des effectifs' ))
            rep['graph'].append(self.generer_histo( histo, 'Nombre de nouveaux élèves/doublants par section' ))
        elif stat == 'Par situation':
            rep['ordre'] = [('situation n+1','string'),
                            ('effectif','int')]
            rep['data'] = self.server.db.stats('par situation', annee, niveaux, filiere)
        elif stat == 'Provenance':
            rep['ordre'] = [('Établissement','string'),
                            ('total','int'),
                            ('en seconde','int'),
                            ('liste','string')]
            rep['data'] = self.server.db.stats('provenance', annee, niveaux, filiere)
            # Graphique sur les établissement de provenance
            tarte = collections.OrderedDict.fromkeys([])
            autres = 0
            total_hors_etab = sum(
                    [x['total'] for x in rep['data'] if x['Établissement']!=self.server.nom_etablissement])
            for d in rep['data']:
                total = d['total']
                etab = d['Établissement']
                if etab != self.server.nom_etablissement:
                    if (total / total_hors_etab) >= 0.03: # la contribution minimale est de 3%
                        tarte[d['Établissement']] = total
                    else:
                        autres = autres + total
            tarte = collections.OrderedDict(sorted(tarte.items(), key=lambda x: x[1], reverse=True))
            if autres > 0: tarte['« Autres »'] = autres
            rep['graph'].append(self.generer_tarte( tarte, "Arrivants par établissement de provenance" ))
        elif stat == 'Provenance (classe)':
            rep['ordre'] = [('classe', 'string'),
                            ('provenance','string'),
                            ('MEF','string'),
                            ('Établissement','string'),
                            ('total','int'),
                            ('liste','string')]
            rep['data'] = self.server.db.stats('provenance classe', annee, niveaux, filiere)
        elif stat == 'Taux de passage':
            rep['ordre'] = [('section','string'),
                            ('passage','string'),
                            ('effectif N-1','int'),
                            ('taux','float')]
            rep['data'] = []
            passage = self.server.db.stats('taux de passage', annee, niveaux, filiere)
            for sect in self.server.sections:
                # On filtre les éléments de data concernant la section voulue
                antecedents = [sect]
                if 'Première' in niveaux: antecedents.append('GT')
                # ie GT est aussi un antécédent possible si l'on regarde les premières
                e = [dictio for dictio in passage if dictio['Section'] in antecedents]
                for i in range(1,len(self.server.niveaux)):
                    niv = self.server.niveaux[i]
                    niv_pre = self.server.niveaux[i-1]
                    # Élèves au niveau niv de la section sect pour l'année en cours
                    f = [dictio['INE'] for dictio in e if dictio['Niveau'] == niv and dictio['Année'] == annee]
                    # Élèves au niveau précédent de la même section pour l'année passée
                    g = [dictio['INE'] for dictio in e if dictio['Niveau'] == niv_pre and dictio['Année'] == annee-1]
                    #print("========{0}========{1}/{2}\n{f}\n{g}".format(sect,niv_pre,niv,f=f,g=g))
                    if len(f) > 0 and len(g) > 0:
                        # On a des élèves dans deux années successives d'une même section !
                        communs = list (set(g) & set(f)) # l'intersection des deux années
                        #print(communs)
                        taux = en_pourcentage( float(len(communs)) / float(len(g)) )
                        v = { 'section': sect, 'passage': niv_pre+' > '+niv, 'effectif N-1':len(g), 'taux': taux}
                        rep['data'].append(v)
        elif stat == 'EPS (activite)':
            rep['ordre'] = [('activité','string'),
                            ('cp','int'),
                            ('moyenne','float'),
                            ('effectif','int'),
                            ('moyenne ♂','float'),
                            ('effectif ♂','int'),
                            ('moyenne ♀','float'),
                            ('effectif ♀','int')]
            rep['data'] = []
            act = self.server.db.stats('eps activite', annee, niveaux, filiere)
            cp = self.server.db.lire_eps_activites()
            for a in self.server.eps_activites.keys():# pour chaque activité
                somme_h = somme_f = 0
                eff_h = eff_f= 0
                for b in act: # pour chaque ligne de la requête
                    for c in b: # par colonne => par activité (1, 2 ... 5)
                        if b[c] == a: # si c'est l'activité recherchée
                            excl = b['a{0}'.format(c.split(' ')[1])]
                            # Seul compte les notes positives dans le calcul de la moyenne
                            notes_comptantes = b['nombre'] - excl
                            if notes_comptantes > 0:
                                note = b['n{0}'.format(c.split(' ')[1])]
                                if b['Sexe'] == 1:
                                    somme_h = somme_h + note
                                    eff_h = eff_h + notes_comptantes
                                elif b['Sexe'] == 2:
                                    somme_f = somme_f + note
                                    eff_f = eff_f + notes_comptantes
                moyenne = moyenne_h = moyenne_f = '?'
                if eff_h != 0:
                    moyenne_h = round(somme_h/eff_h,2)
                if eff_f != 0:
                    moyenne_f = round(somme_f/eff_f,2)
                if eff_h + eff_f != 0:
                    moyenne = round( (somme_h+somme_f)/(eff_h+eff_f) ,2 )
                v = {   'activité': a, 'cp': cp[a], 'moyenne': moyenne,
                        'moyenne ♂': moyenne_h, 'moyenne ♀': moyenne_f,
                        'effectif': (eff_h + eff_f),
                        'effectif ♂': eff_h, 'effectif ♀': eff_f }
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
        fig = figure(1, figsize=(6,6))
        ax = axes([0.1, 0.1, 0.8, 0.8])

        x = [] # les valeurs à afficher
        labels = [] # les intitulés correspondants
        for k in proportions:
            if proportions[k] is not None: # L'orderedDict créer automatiquement des cases vides
                x.append(proportions[k])
                labels.append(k)
        # Préparation des couleurs
        couleurs = self.server.colors
        if len(proportions) == len(couleurs)+1:
            # La première et la dernière couleur vont être les même !
            # alors on change la cardinalité de l'espace des couleurs en ajoutant du jaune
            couleurs = couleurs + ('#FFFF80',)
        # Génération de la tarte
        pie(x,  labels=labels,
                colors=couleurs,
                autopct='%1.1f%%', # texte dans les parts
                pctdistance=0.8, # distance au centre des textes dans les parts
                shadow=True, startangle=90)
        title(titre, weight='demi') # Ajout d'un titre
        #fig.tight_layout()
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

    def importer_diplome(self, fichier_tmp):
        """
            Parse le xls à importer

        :param data: le fichier à importer (passé en POST)
        :type data: fichier xls (binaire)
        :returns: infos sur le statut de l'importation (statut, message à afficher, nb d'import effectués)
        :rtype: int, str, int
        """
        if not self.server.importation_en_cours:
            self.server.importation_en_cours = True
        else:
            return 1, "Erreur : Importation en cours", 0

        # Parsing du fichier
        workbook = xlrd.open_workbook(fichier_tmp, encoding_override='cp1252')
        sheet = workbook.sheet_by_index(0) # On sélectionne le premier classeur = "Extraction"
        # Lecture des entêtes de colonnes
        row = sheet.row(0)  # La première ligne
        cols = { 'nom': None, 'prénom': None, 'g1': None, 'g2': None }
        second_groupe = False
        for idx, cell_obj in enumerate(row):
            if cell_obj.value == 'Nom candidat': cols['nom'] = idx
            elif cell_obj.value == 'Prénom candidat': cols['prénom'] = idx
            elif cell_obj.value == 'Résultat 1er groupe': cols['g1'] = idx
            elif cell_obj.value == 'Résultat 2eme groupe':
                cols['g2'] = idx
                second_groupe = True

        # Extraction des données
        num_cols = sheet.ncols   # Nombre total de colonnes
        for row_idx in range(1, sheet.nrows):
            nom = sheet.cell(row_idx, cols['nom']).value
            prénom = sheet.cell(row_idx, cols['prénom']).value.capitalize()
            if not second_groupe:
                resultat = sheet.cell(row_idx, cols['g1']).value
            else:
                resultat = sheet.cell(row_idx, cols['g2']).value
            resultat = resultat[0] + resultat[1:].lower()
            try:
                self.server.db.ecrire_diplome(nom, prénom, resultat)
            except Exception as e:
                self.server.importation_en_cours = False
                logging.error("Importation xls : {0}".format(e))
                return 1, "L'importation a échouée :\n{0}".format(e), 0
        self.server.importation_en_cours = False
        return 0, "L'importation s'est bien terminée.", sheet.nrows-1

    def importer_xml(self, fichier_tmp):
        """
            Parse le xml à importer

        :param data: le fichier à importer (passé en POST)
        :type data: fichier xml
        :returns: infos sur le statut de l'importation (statut, message à afficher, nb d'import effectués)
        :rtype: int, str, int
        """
        if not self.server.importation_en_cours:
            self.server.importation_en_cours = True
        else:
            return 1, "Erreur : Importation en cours", 0

        nb_avant_import = self.server.db.importations[self.server.db.INSERT]
        # Parsing du fichier
        tree = ET.parse(fichier_tmp)
        root = tree.getroot()
        # Vérification de la date d'exportation
        annee = int(root.findtext('.//PARAMETRES/ANNEE_SCOLAIRE'))
        date_export_tab = root.findtext('.//PARAMETRES/DATE_EXPORT').split('/')
        date_export = '{a}-{m}-{j}'.format(j=date_export_tab[0], m=date_export_tab[1], a=date_export_tab[2])
        pending = False
        if self.server.date < date(date_export):
            self.server.maj_date(date_export)
            # Nettoyage, si ce n'est pas un import d'une année précédente
            pending = True
            self.server.db.vider_pending()

        les_classes = list(self.server.db.lire_classes(self.server.debut_AS.year).keys())
        classes_a_ajouter = []
        # Traitement des données
        for eleve in root.iter('ELEVE'):
            sortie = eleve.findtext('DATE_SORTIE')
            if sortie:
                # S'il y a une date de sortie, on laisse tomber
                continue
            eid = eleve.get('ELEVE_ID')
            ine = eleve.findtext('ID_NATIONAL')
            nom = eleve.findtext('NOM')
            prenom = eleve.findtext('PRENOM')
            naissance = eleve.findtext('DATE_NAISS')
            sexe = eleve.findtext('CODE_SEXE')
            mef = xstr(eleve.findtext('CODE_MEF'))
            doublement = eleve.findtext('DOUBLEMENT')
            entrée = eleve.findtext('DATE_ENTREE')
            classe = root.findtext(".//*[@ELEVE_ID='{0}']/STRUCTURE[TYPE_STRUCTURE='D']/CODE_STRUCTURE".format(eid))
            sad_etab = xstr(eleve.findtext('SCOLARITE_AN_DERNIER/DENOM_COMPL')).title()
            sad_classe = xstr(eleve.findtext('SCOLARITE_AN_DERNIER/CODE_STRUCTURE')).strip(' ')
            sad_mef = xstr(eleve.findtext('SCOLARITE_AN_DERNIER/CODE_MEF'))
            enr = { 'eid': eid, 'ine': ine, 'nom': nom, 'prénom': prenom, \
                    'naissance': naissance, 'sexe': sexe, 'mef': mef, \
                    'doublement': doublement, 'classe': classe, 'entrée': entrée, \
                    'sad_établissement': sad_etab,   'sad_classe': sad_classe,  'sad_mef': sad_mef }
            try:
                self.server.db.ecrire(enr, annee, pending)
            except Exception as e:
                self.server.importation_en_cours = False
                nb_apres_import = self.server.db.importations[self.server.db.INSERT]
                logging.error("Importation xml : {0}".format(e))
                return 1, "L'importation a échouée.\n{0}".format(e), nb_apres_import-nb_avant_import
            if not (classe in les_classes or classe in classes_a_ajouter or classe is None) :
                classes_a_ajouter.append(classe)
        # Ici, les données élèves ont été importé ; il ne reste qu'à ajouter les classes inconnues
        self.server.db.ecrire_classes(classes_a_ajouter, self.server)

        nb_apres_import = self.server.db.importations[self.server.db.INSERT]
        print(nb_apres_import)
        self.server.importation_en_cours = False
        return 0, "L'importation s'est bien terminée.", nb_apres_import-nb_avant_import
