#!/usr/bin/python
# -*- coding: utf-8  -*-
import sqlite3
import shutil
import datetime
import logging
import os
import collections # OrderedDict
from liblegion import *

class Database():
    """
        La base de donnée [sic]
    """
    def __init__(self, root, nom_etablissement):
        self.nom_etablissement = nom_etablissement
        self.nom_base = 'base.sqlite'
        bdd = root + os.sep + self.nom_base
        if os.path.isfile(bdd):
            self.old_db = bdd+'.'+datetime.date.today().isoformat()
            # Sauvegarde de la base
            shutil.copy(bdd, self.old_db)
        else:
            logging.error("La base sqlite ({0}) n'est pas accessible. Impossible de continuer.".format(bdd))
            exit(2)

        try:
            self.conn = sqlite3.connect(bdd, check_same_thread=False)
            # Par défaut, sqlite interdit l'accès si la connexion avec la base a été fait depuis un autre thread
            # mais c'est le cas de l'HttpHandler, qui est créé à chaque requête.
            # check_same_thread permet de surmonter ça et d'autoriser l'handler à appeler des fonctions de Database
            #ref: http://stackoverflow.com/questions/393554/python-sqlite3-and-concurrency
        except:
            logging.error("Impossible de se connecter à la base de données ({0})".format(bdd))
            exit(3)
        self.conn.row_factory = sqlite3.Row
        self.curs = self.conn.cursor()
        # defines
        self.FAILED = 0
        self.INSERT = 1
        self.PENDING = 2
        self.importations = [0]*3

    def fermer(self):
        """
            Gère les sauvegardes de la base de données
            & Ferme proprement la base
        """
        nb_changements = self.conn.total_changes
        logging.info('{0} changements effectués sur la base.'.format(nb_changements))
        if nb_changements == 0:
            # Si aucuns changements, on supprime la sauvegarde créé au lancement
            os.remove(self.old_db)
        else:
            logging.info('Rapport de modifications : {0} échecs ; {1} insertions/majs ; {2} pending.'.format(
                self.importations[self.FAILED],     self.importations[self.INSERT],
                self.importations[self.PENDING]) )
        self.conn.close()

    def maj_champ(self, table, ident, champ, donnee, tier=2):
        """
            Mets à jour un champ de la base

        :param table: le nom de la table visée
        :param ident: l'identifiant (clé primaire) visé
        :param champ: le champ à modifier
        :param donnee: la nouvelle valoir
        :param tier: (OPT - EPS) le tier voulu (1 ou 2)
        :type table: str
        :type ident: str
        :type champ: str
        :type donnee: str
        :type tier: int
        """
        if table == 'Élèves':
            col = 'INE'
            cond = '{col}="{ident}"'.format(col=col, ident=ident)
        elif table == 'Classes':
            col = 'Classe'
            cond = '{col}="{ident}"'.format(col=col, ident=ident)
        elif table == 'EPS':
            col = 'INE'
            cond = '{col}="{ident}" AND Tier={tier}'.format(col=col, ident=ident, tier=tier)
        req = 'UPDATE {tab} SET "{champ}"="{d}" WHERE {cond}'.format(tab=table, cond=cond, champ=champ, d=donnee)
        try:
            self.curs.execute(req)
        except sqlite3.Error as e:
            logging.error(u"Mise à jour d'un champ : {0}\n{1}".format(e.args[0], req))
            return 'Non'
        self.conn.commit()
        return 'Oui'

    def ecrire(self, enr, annee, mise_en_pending=False):
        """
            Ajoute les informations d'un élève à la bdd

        :param enr: les données à enregistrer
        :param annee: l'année de référence pour l'importation
        :param mise_en_pending: s'il faut mettre les erreurs en pending, ou non
        :type enr: dict
        :type annee: int
        :type mise_en_pending: booléen
        :return: define du type d'importation effectuée
        :rtype: int
        """
        ine = enr['ine']
        classe = enr['classe']
        enr['Diplômé'] = enr['Situation'] = enr['Lieu'] = ''
        raison = []
        # Écriture des données en pending ?
        if mise_en_pending:
            if ine is None:
                raison.append("Pas d'INE")
            if classe is None:
                raison.append('Pas de classe')
            if len(raison) > 0:
                if self.ecrire_en_pending(enr, ', '.join(raison)):
                    self.conn.commit()
                    inc_list(self.importations, self.PENDING)
                    return self.PENDING
                else:
                    inc_list(self.importations, self.FAILED)
                    return self.FAILED
        # Conversion de la date au format ISO-8601
        n = enr['naissance'].split('/')
        enr['naissance'] = '{0}-{1}-{2}'.format(n[2], n[1], n[0])

        # Ajout de l'élève
        req = 'INSERT OR REPLACE INTO Élèves ' \
            + '(ELEVE_ID, INE, Nom, Prénom, Naissance, Genre, Mail, Entrée, Diplômé, Situation, Lieu) ' \
            + 'VALUES ("{0}", "{1}", "{2}", "{3}", "{4}", {5}, "{6}", {7}, "{8}", "{9}", "{10}")'.format(
                    enr['eid'],         ine,                enr['nom'],
                    enr['prénom'],      enr['naissance'],   int(enr['genre']),
                    enr['mail'],        int(enr['entrée']), enr['Diplômé'],
                    enr['Situation'],   enr['Lieu'])
        try:
            self.curs.execute(req)
        except sqlite3.Error as e:
            # Pour toute autre erreur, on laisse tomber
            logging.error(u"Insertion d'un élève : {0}\n{1}".format(e.args[0], req))
            inc_list(self.importations, self.FAILED)
            return self.FAILED

        # Ajout de l'élève dans la base EPS (dans les 2 niveaux)
        for i in range(1,3):
            req = 'INSERT OR IGNORE INTO EPS (INE, Tier) VALUES ("{0}", {1})'.format(ine, i)
            self.curs.execute(req)
        # Reste à affecter notre élève à sa classe de cette année et de l'année dernière
        x = self.ecrire_affectation(
                ine, annee, classe, enr['mef'], self.nom_etablissement, enr['doublement'])
        etab = enr['sad_établissement']
        classe_pre = enr['sad_classe']
        if enr['doublement'] == 1: # Parfois, ces informations ne sont pas redonnées dans SIECLE
            classe_pre = classe
            etab = self.nom_etablissement
        y = self.ecrire_affectation(
                ine, annee-1, classe_pre, enr['sad_mef'], etab, 9)
        # En cas de problème, annulation des modifications précédentes
        if x == self.FAILED:
            raison.append('Pb affectation année en cours')
        if y == self.FAILED:
            #raison.append('Pb affectation année précédente')
            #logging.info(u"{0}".format(enr))
            pass
        if len(raison) > 0:
            self.conn.rollback()
            if self.ecrire_en_pending(enr, ', '.join(raison)):
                self.conn.commit()
                inc_list(self.importations, self.PENDING)
                return self.PENDING
            else:
                inc_list(self.importations, self.FAILED)
                return self.FAILED

        # Validation de l'écriture et de l'affectation à deux classes
        self.conn.commit()
        inc_list(self.importations, self.INSERT)
        return self.INSERT

    def ecrire_affectation(self, ine, annee, classe, mef, etab, doublement):
        """
            Ajoute une affectations (un élève, dans une classe, dans un établissement)

        :param ine: l'INE de l'élève
        :param annee: l'année de scolarisation
        :param classe: sa classe
        :param mef: le code mef de la classe affectée
        :param etab: le nom de l'établissement
        :param doublement: si c'est un redoublement
        :type ine: str
        :type annee: int
        :type classe: str
        :type mef: str
        :type etab: str
        :type doublement: int - 0 ou 1
        """
        if classe == "" or etab == "":
            #logging.info("Erreur lors de l'affectation : classe ou établissement en défaut")
            return False
        req = 'INSERT OR REPLACE INTO Affectations ' \
              +  '(INE, Année, Classe, MEF, Établissement, Doublement) ' \
              + 'VALUES ("{0}", {1}, "{2}", "{3}", "{4}", {5})'.format( ine, annee, classe, mef, etab, doublement )
        try:
            self.curs.execute(req)
        except sqlite3.Error as e:
            logging.error(u"Insertion d'une affectation : {0}\n{1}".format(e.args[0], req))
            return self.FAILED
        return self.INSERT

    def ecrire_classes(self, classes, server):
        """
            Insère une liste de classes (fin d'importation)
            
        :param classes: les classes à créer
        :param server: pointeur vers le serveur (pour accéder à ses données)
        :type classes: list
        :type server: pointeur
        """
        sorted_sections = sorted(server.sections, key=len, reverse=True)
        for cla in classes:
            # Recherche automatique de la section
            sec = ''
            for section in sorted_sections:
                if section in cla:
                    sec = section
                    break
            # Recherche automatique de la filière
            fil = ''
            if sec != '':
                fil = server.section_filière[sec]
            # Recherche automatique du niveau
            niv = ''
            if fil != 'Enseignement supérieur':
                if cla[0] == '2':   niv = server.niveaux[0]
                elif cla[0] == '1': niv = server.niveaux[1]
                elif cla[0] == 'T': niv = server.niveaux[2]
            # Insertion
            req = 'INSERT INTO Classes VALUES ("{0}", "{1}", "{2}", "{3}")'.format(cla, niv, fil, sec)
            try:
                self.curs.execute(req)
            except sqlite3.Error as e:
                logging.info(u"Erreur lors de l'ajout de la classe {0}:\n{1}".format(cla, e.args[0]))
        self.conn.commit()

    def ecrire_en_pending(self, enr, raison=""):
        """
            Mise en attente de données incomplètes pour validation ultérieure
            
        :param enr: les données à enregistrer
        :param raison: raison de la mise en pending
        :type enr: dict 
        :type raison: str
        :rtype: booléen
        """
        JOCKER = '0' # Nécessairement un int
        # Protection contre des données qui seraient non valides
        for k, v in enr.items():
            if v is None: enr[k] = JOCKER

        # On regarde si l'enregistrement est déjà présent
        ine = enr['ine']
        nom = enr['nom']
        prenom = enr['prénom']
        if ine != JOCKER: # Par ine
            condition = 'INE="{0}"'.format(ine)
        elif nom != JOCKER and prenom != JOCKER: # Par nom/prénom
            condition = 'Nom="{0}" AND Prénom="{1}"'.format(nom, prenom)
        else:
            # Impossible de savoir si c'est un doublon -> on fait tout simplement une insertion
            condition = ''
            r = [0,0]
        if condition != '':
            req = 'SELECT rowid,COUNT(*) FROM Pending WHERE {0}'.format(condition)
            try:
                 self.curs.execute(req)
            except sqlite3.Error as e:
                logging.error(u"Test de duplicata en pending : {0}\n{1}".format(e.args[0], req))
                return False
            r = self.curs.fetchone()

        req = 'INSERT OR REPLACE INTO Pending ' \
                + '(INE, Nom, Prénom, Naissance, Genre, Mail, Entrée, Classe, Établissement, Doublement, Raison) ' \
                + 'VALUES ("{0}", "{1}", "{2}", "{3}", {4}, "{5}", {6}, "{7}", "{8}", {9}, "{10}")'.format(
                    enr['ine'],             enr['nom'],             enr['prénom'],
                    enr['naissance'],       int(enr['genre']),      enr['mail'],
                    int(enr['entrée']),     enr['classe'],          enr['sad_établissement'],
                    int(enr['doublement']),     raison)
        try:
            self.curs.execute(req)
        except sqlite3.Error as e:
            logging.error(u"Insertion en pending : {0}\n{1}".format(e.args[0], req))
            return False
        return True

    def ecrire_option(self, nom, valeur):
        """
            Sauvegarde une option dans la BDD
            
        :param nom: la clef
        :param valeur: la valeur [sic]
        :type nom: str
        :type valeur: str
        """
        req = 'INSERT OR REPLACE INTO Options (Nom, Valeur) VALUES ("{0}", "{1}")'.format(nom, valeur)
        try:
            self.curs.execute(req)
        except sqlite3.Error as e:
            logging.info(u"Erreur lors de la sauvegarde de l'option {0}:\n{1}".format(nom, e.args[0]))
        self.conn.commit()

    def lire(self, annee, orderby, sens='ASC', niveau=''):
        """
            Lit le contenu de la base élève
        
        :param annee: année de scolarisation
        :param orderby: clé de tri
        :param sens: ordre de tri (ASC ou DESC)
        :param niveau: groupe de classes (Seconde, BTS...)
        :type annee: int
        :type orderby: str
        :type sens: str
        :type niveau: str
        :rtype: OrderedDict
        """
        data = collections.OrderedDict()
        niv= ''
        if niveau in ['Seconde', 'Première', 'Terminal']:
            niv= 'AND Niveau="{0}"'.format(niveau)
        elif niveau == 'BTS':
            niv= 'AND (Niveau="1BTS" OR Niveau="2BTS")'
        # Listage des élèves
        req = 'SELECT * FROM Élèves E NATURAL JOIN Affectations A JOIN Classes C ON A.Classe=C.Classe WHERE Année="{2}" {niv} ORDER BY {0} {1}, Nom ASC'.format(orderby, sens, annee, niv=niv)
        for row in self.curs.execute(req).fetchall():
            d = dict_from_row(row)
            ine = d['INE']
            # Calcul de l'âge actuel
            d['Âge'] = nb_annees(date(d['Naissance']))
            data[ine] = d
        # Génération du parcours
        req = 'SELECT INE,Année,A.Classe,Établissement,Doublement FROM Élèves E NATURAL JOIN Affectations A JOIN Classes C ON A.Classe=C.Classe WHERE Année<="{0}" {niv} ORDER BY Année DESC'.format(annee,niv=niv)
        for row in self.curs.execute(req).fetchall():
            d = dict_from_row(row)
            ine = d['INE']
            if ine in data: # ?
                an = d['Année']
                e = [ d['Classe'], d['Établissement'], d['Doublement'] ]
                if 'Parcours' not in data[ine].keys():
                    data[ine]['Parcours'] = { an: e }
                else:
                    # Déjà présent : on ajoute juste une année scolaire
                    data[ine]['Parcours'][an] = e
        return data

    def lire_classes(self, annee, niveau=''):
        """
            Lit le contenu de la table classes
        
        :param annee:  l'année [sic]
        :param niveau: si vaut 'eps', permet de limiter les classes aux 2e, 1er, Term
        :type annee: int
        :rtype: OrderedDict
        """
        data = collections.OrderedDict()
        n = ''
        if niveau == 'eps':
            n = 'AND (C.Niveau="Seconde" OR C.Niveau="Première" OR C.Niveau="Terminale")'
        req = 'SELECT * FROM Classes C NATURAL JOIN Affectations A WHERE A.Année={0} {1} ORDER BY Classe ASC'.format(annee, n)
        for row in self.curs.execute(req).fetchall():
            d = dict_from_row(row)
            key = d['Classe']
            data[key] = d
        return data

    def lire_eps(self, annee, classe, tier):
        """
            Lit les notes et activités d'EPS de toute une classe
        
        :param annee: année de scolarisation
        :param classe: la classe [sic]
        :param tier: le tier voulu (1 ou 2 pour BEP ou BAC)
        :type annee: int
        :type classe: str
        :type tier: int
        :rtype: OrderedDict
        """
        data = collections.OrderedDict()
        req = """SELECT *,EA1.CP AS CP1, EA2.CP AS CP2,EA3.CP AS CP3, EA4.CP AS CP4,EA5.CP AS CP5 
        FROM Élèves El JOIN EPS E ON E.INE=El.INE 
        JOIN Affectations A ON A.INE=El.INE 
        LEFT JOIN EPS_Activités EA1 ON LOWER(EA1.Activité)=LOWER(E."Activité 1")
        LEFT JOIN EPS_Activités EA2 ON LOWER(EA2.Activité)=LOWER(E."Activité 2")
        LEFT JOIN EPS_Activités EA3 ON LOWER(EA3.Activité)=LOWER(E."Activité 3")
        LEFT JOIN EPS_Activités EA4 ON LOWER(EA4.Activité)=LOWER(E."Activité 4")
        LEFT JOIN EPS_Activités EA5 ON LOWER(EA5.Activité)=LOWER(E."Activité 5")
        WHERE E."Activité 1" IS NOT NULL AND E."Activité 2" IS NOT NULL
        AND E."Activité 3" IS NOT NULL AND E."Activité 5" IS NOT NULL
        AND E."Activité 5" IS NOT NULL AND Classe="{0}" AND A.Année="{1}" AND Tier={2}
        ORDER BY Nom,Prénom ASC """.format(classe, annee, tier)
        for row in self.curs.execute(req).fetchall():
            d = dict_from_row(row)
            d['Élèves'] = d['Nom'] + ' ' + d['Prénom']
            d['x̄'] = 'Pas assez de notes'
            # Calcul de la note du BAC : 
            notes = []
            for i in range(1,6): # Récupération des notes
                note = d['Note {0}'.format(i)]
                cp = d['CP{0}'.format(i)]
                if note is None or cp is None: note = -1
                notes.append( (note, cp) )
            selection = [] # Notes sélectionnées
            indices = [] # L'indice correspondant
            cp = [] # Les Compétences Propres correspondantes
            # Nombre d'éléments positifs sur les notes de terminal
            notes_term = sum(x >= 0 for x,y in notes[2:])
            if notes_term < 2: d['x̄'] = 'Manque note Term'
            else:
                for k in reversed(range(1,4)):
                    if k > 1:
                        # Sélection des deux premières notes en terminal
                        select_range = range(2,len(notes))
                    else:
                        select_range = range(0,len(notes))
                    maximum = -1
                    indice = -1
                    for l in select_range:
                        note = notes[l][0]
                        competence = notes[l][1]
                        if note > maximum and l not in indices and competence not in cp:
                            maximum = note
                            indice = l
                    if maximum > -1 and indice > -1:
                        selection.append(maximum)
                        indices.append(indice)
                        cp.append(notes[indice][1])
                # Calcul de la moyenne
                if len(selection) == 3:
                    d['x̄'] = round(sum(selection) / 3.0, 2)
                    d['Notes'] = [a+1 for a in indices] # les gens normaux comptent à partir de 1
                else:
                    d['Notes'] = []

            data[d['INE']] = d
        return data

    def lire_eps_activites(self):
        """
            Lit les activités d'EPS
        
        :rtype: OrderedDict
        """
        data = collections.OrderedDict()
        req = 'SELECT * FROM EPS_Activités ORDER BY CP,Activité'
        for row in self.curs.execute(req).fetchall():
            d = dict_from_row(row)
            clé = d['Activité'].capitalize()
            data[clé] = d['CP']
        return data

    def lire_options(self):
        """
            Lit les options fixées dans la base de données
        
        :rtype: dict
        """
        data = {}
        req = 'SELECT * FROM Options'
        try:
            self.curs.execute(req)
        except sqlite3.Error as e:
            logging.error("Erreur lors de la lecture des options :\n{0}".format(e.args[0]))
        return {item[0]:item[1] for item in self.curs.fetchall()}

    def lire_pending(self):
        """
            Lit le contenu de la base des élèves en pending
        
        :rtype: OrderedDict
        """
        data = collections.OrderedDict()
        req = 'SELECT rowid,* FROM Pending ORDER BY Nom,Prénom ASC'
        for row in self.curs.execute(req).fetchall():
            d = dict_from_row(row)
            key = '{0}-{1}'.format(d['Nom'], d['rowid'])
            data[key] = d
        return data

    def lister(self, info):
        """
            Génère une liste des INE, des classes ou des années connues

        :param info: l'information recherchée dans 'Affectations'
        :type info: str
        :rtype: list
        """
        req = 'SELECT DISTINCT {0} FROM Affectations ORDER BY {0} ASC'.format(info)
        try:
            self.curs.execute(req)
        except sqlite3.Error as e:
            logging.error("Erreur lors du listage '{0}' :\n{1}".format(info, e.args[0]))
        return [item[0] for item in self.curs.fetchall()]

    def stats(self, info, annee, niveaux):
        """
            Génère une liste avec les stats voulues

        :param info: la stat recherchée
        :param annee: son année de validité
        :param niveaux: les niveaux à prendre en compte
        :type info: str
        :type annee: int
        :type niveaux: array(str)
        """
        les_niveaux = '('+' OR '.join(['CN.Niveau="'+s+'"' for s in niveaux])+')'
        if info == "ouverture": # ouverture
            req = """SELECT 
            sum(CASE WHEN "Niveau" LIKE "" THEN 0 ELSE 1 END)+sum(CASE WHEN "Section" LIKE "" THEN 0 ELSE 1 END) AS n,
            count(*) AS total FROM Classes
            WHERE Classe IN (SELECT DISTINCT Classe FROM Affectations WHERE Année={0})""".format(annee)
        elif info == "totaux": # totaux
            # Calcul des totaux :
            # Nombre d'élèves, d'hommes, doublants, nouveaux, issues de pro
            req = """SELECT count(*) total, 
            COALESCE(sum(CASE WHEN Genre="1" THEN 1 ELSE 0 END),0) homme, 
            IFNULL(sum(CASE WHEN Doublement="1" THEN 1 ELSE 0 END),0) doublant, 
            COALESCE(sum(CASE WHEN A.INE IN (SELECT INE FROM Affectations WHERE Année={0} AND Établissement<>"{etab}") THEN 1 ELSE 0 END),0) nouveau, 
            IFNULL(sum(CASE WHEN A.Classe IN (SELECT Classe FROM Classes C2 WHERE Filière="Pro") THEN 1 ELSE 0 END),0) "issue de pro" 
            FROM Affectations A JOIN Classes CN ON A.Classe=CN.Classe JOIN Élèves E ON A.INE=E.INE 
            WHERE Établissement="{etab}" AND Année={0} AND {niv}""".format(annee, etab=self.nom_etablissement, niv=les_niveaux)
        elif info == "par niveau": # par niveau
            req = """SELECT Niveau, count(A.INE) effectif, 
            sum(CASE WHEN Genre="1" THEN 1 ELSE 0 END) homme, 
            sum(CASE WHEN Doublement="1" THEN 1 ELSE 0 END) doublant, 
            sum(CASE WHEN A.INE IN (SELECT INE FROM Affectations WHERE Année={1} AND Établissement<>"{etab}") THEN 1 ELSE 0 END) nouveau, 
            sum(CASE WHEN A.Classe IN (SELECT Classe FROM Classes C2 WHERE Filière="Pro") THEN 1 ELSE 0 END) "issue de pro" 
            FROM Affectations A JOIN Classes CN ON A.Classe=CN.Classe JOIN Élèves E ON A.INE=E.INE 
            WHERE Établissement="{etab}" AND Année={0} AND {niv} 
            GROUP BY Niveau""".format(annee, annee-1, etab=self.nom_etablissement, niv=les_niveaux)
        elif info == "par section": # par section
            req = """SELECT Section, count(A.INE) effectif, 
            sum(CASE WHEN Genre="1" THEN 1 ELSE 0 END) homme, 
            sum(CASE WHEN Doublement="1" THEN 1 ELSE 0 END) doublant, 
            sum(CASE WHEN A.INE IN (SELECT INE FROM Affectations WHERE Année={1} AND Établissement<>"{etab}") THEN 1 ELSE 0 END) nouveau, 
            sum(CASE WHEN A.Classe IN (SELECT Classe FROM Classes C2 WHERE Filière="Pro") THEN 1 ELSE 0 END) "issue de pro" 
            FROM Affectations A JOIN Classes CN ON A.Classe=CN.Classe JOIN Élèves E ON A.INE=E.INE 
            WHERE Établissement="{etab}" AND Année={0} AND {niv} 
            GROUP BY Section""".format(annee, annee-1, etab=self.nom_etablissement, niv=les_niveaux)
        elif info == "par situation": # par situation
            req = """SELECT (CASE WHEN Situation="" THEN '?' ELSE Situation END) as situation,
            count(*) as effectif FROM Élèves E
            JOIN Affectations A ON E.INE=A.INE JOIN Classes CN ON A.Classe=CN.Classe 
            WHERE A.Année={0} AND Établissement="{etab}" AND {niv}
            GROUP BY Situation""".format(annee, etab=self.nom_etablissement, niv=les_niveaux)
        elif info == "annees scolarisation": # annees scolarisation
            req = """SELECT INE, count(*) Scolarisation 
            FROM Affectations A JOIN Classes CN ON A.Classe=CN.Classe 
            WHERE Établissement="{0}" AND {niv} 
            GROUP BY INE""".format(self.nom_etablissement, niv=les_niveaux)
            # Autre calcul utilisant la date d'entrée
            #(pb: l'élèves a pu partir puis revenir l'année suivante)
            #req = 'SELECT A.INE,{0}-Entrée+1 AS Scolarisation FROM Affectations A JOIN Élèves E ON A.INE=E.INE WHERE Établissement="Jean Moulin"'.format(annee)
        elif info == "provenance": # provenance
            req = """SELECT A2.Établissement, count(*) total, 
            sum(CASE WHEN CN.Niveau="Seconde" THEN 1 ELSE 0 END) "en seconde", 
	    (CASE WHEN A2.Établissement!="{etab}" THEN 
                GROUP_CONCAT(A.Classe||" / "||E.Nom||" "||E.Prénom, ", <br>")
                ELSE "..." END) AS liste
            FROM Affectations A LEFT JOIN Affectations A2 ON A.INE=A2.INE 
            LEFT JOIN Classes CN ON A.Classe = CN.Classe 
            JOIN Élèves E ON E.INE=A.INE
            WHERE A.Année={0} AND A2.Année={1} AND {niv} 
            GROUP BY A2.Établissement""".format(annee, annee-1, niv=les_niveaux, etab=self.nom_etablissement)
        elif info == "provenance classe": # provenance classe
            req = """SELECT CN.Classe classe, IFNULL(A2.Classe,'inconnue') AS provenance,
            IFNULL(A2.Établissement, 'inconnu') AS Établissement, IFNULL(A2.MEF, '?') AS MEF, count(*) AS total, 
            GROUP_CONCAT(E.Nom||" "||E.Prénom, ", <br>") AS liste            
            FROM Classes CN LEFT JOIN Affectations A ON CN.Classe=A.Classe 
            LEFT JOIN Affectations A2 ON A.INE=A2.INE AND A2.Année={1}
            JOIN Élèves E ON E.INE=A.INE
            WHERE A.Année={0} AND {niv}  GROUP BY A2.Classe,A.Classe
            ORDER BY CN.Classe,A2.Établissement,A2.Classe""".format(annee, annee-1, niv=les_niveaux)
        elif info == "taux de passage": # taux de passage
            req = """SELECT Section, Niveau, INE, Année 
            FROM Affectations A LEFT JOIN Classes CN ON A.Classe=CN.Classe 
            WHERE Section<>'' AND {niv} ORDER BY Section,Niveau""".format(niv=les_niveaux)
        elif info == "eps activite": # EPS: moyenne par activité
            req = """SELECT "Activité 1", sum(CASE WHEN "Note 1">0 THEN "Note 1" ELSE 0 END) as n1,
            "Activité 2", sum(CASE WHEN "Note 2">0 THEN "Note 2" ELSE 0 END) as n2,
            "Activité 3", sum(CASE WHEN "Note 3">0 THEN "Note 3" ELSE 0 END) as n3,
            "Activité 4", sum(CASE WHEN "Note 4">0 THEN "Note 4" ELSE 0 END) as n4,
            "Activité 5", sum(CASE WHEN "Note 5">0 THEN "Note 5" ELSE 0 END) as n5,
            E.Genre, count(*) as nombre
            FROM EPS JOIN Affectations A, Classes CN ON A.INE=EPS.INE AND CN.Classe=A.Classe
            LEFT JOIN Élèves E ON E.INE=A.INE
            WHERE A.Année={0} AND Établissement="{etab}" AND {niv}
            GROUP BY E.Genre, "Activité 1","Activité 2","Activité 3","Activité 4","Activité 5" """.format(annee, etab=self.nom_etablissement, niv=les_niveaux)
        else:
            logging.error('Information "{0}" non disponible'.format(info))
            return []
        logging.debug('> {0}'.format(req))
        try:
            self.curs.execute(req)
        except sqlite3.Error as e:
            logging.error("Erreur lors de la génération de stats '{0}' :\n{1}".format(info, e.args[0]))
        data = []
        for row in self.curs.execute(req).fetchall():
            d = dict_from_row(row)
            data.append(d)
        #logging.debug(data)
        return data

    def vider_pending(self):
        """
            Vide le contenu de la table Pending (avant un nouvel import)
        """
        req = 'DELETE FROM Pending'
        try:
            self.curs.execute(req)
        except sqlite3.Error as e:
            logging.error(u"Delete du pending : {0}\n{1}".format(e.args[0], req))
            return False
        return True
