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
        self.UPDATE = 2
        self.PENDING = 3
        self.importations = [0]*4

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
            logging.info('Rapport de modifications : {0} échecs ; {1} insertions ; {2} majs ; {3} pending.'.format(
                self.importations[self.FAILED],     self.importations[self.INSERT],
                self.importations[self.UPDATE],     self.importations[self.PENDING]) )
        self.conn.close()

    def maj_champ(self, table, ident, champ, donnee):
        """
            Mets à jour un champ de la base

        :param table: le nom de la table visée
        :param ident: l'identifiant (clé primaire) visé
        :param champ: le champ à modifier
        :param donnee: la nouvelle valoir
        :type table: str
        :type ident: str
        :type champ: str
        :type donnee: str
        """
        if table == 'Élèves':       col = 'INE'
        elif table == 'Classes':    col = 'Classe'
        req = 'UPDATE {tab} SET {champ}="{d}" WHERE {col}="{ident}"'.format(tab=table, col=col, ident=ident, champ=champ, d=donnee)
        try:
            self.curs.execute(req)
        except sqlite3.Error as e:
            logging.error(u"Mise à jour d'un champ : {0}\n{1}".format(e.args[0], req))
            return 'Non'
        self.conn.commit()
        return 'Oui'

    def ecrire(self, enr, date):
        """
            Ajoute les informations d'un élève à la bdd

        :param enr: les données à enregistrer
        :param date: l'objet date de référence pour l'importation
        :type enr: dict
        :type date: datetime
        :return: define du type d'importation effectuée
        :rtype: int
        """
        ofthejedi = self.INSERT # valeur de retour par défaut
        ine = enr['ine']
        classe = enr['classe']
        enr['Diplômé'] = enr['Situation'] = enr['Lieu'] = ''
        raison = []
        if ine is None:
            raison.append("Pas d'INE")
        if classe is None:
            raison.append('Pas de classe')
        if len(raison) > 0:
            if self.ecrire_en_pending(enr, date.year, ', '.join(raison)):
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
        req = 'INSERT INTO Élèves ' \
            + '(INE, Nom, Prénom, Naissance, Genre, Mail, Entrée, Diplômé, Situation, Lieu) ' \
            + 'VALUES ("{0}", "{1}", "{2}", "{3}", {4}, "{5}", {6}, "{7}", "{8}", "{9}")'.format(
                    ine,                enr['nom'],         enr['prénom'],
                    enr['naissance'],   int(enr['genre']),  enr['mail'],
                    int(enr['entrée']), enr['Diplômé'],     enr['Situation'],
                    enr['Lieu'])
        try:
            self.curs.execute(req)
        except sqlite3.IntegrityError:
            # L'élève est déjà présent dans la base
            # On met a jour les infos administratives mais pas les colonnes remplies à la main : Diplômé, Situation et Lieu
            req = 'UPDATE Élèves SET ' \
                + 'Nom="{0}", Prénom="{1}", Naissance="{2}", Genre={3}, Mail="{4}", Entrée={5}'.format(
                        enr['nom'],         enr['prénom'],     enr['naissance'],
                        int(enr['genre']),  enr['mail'],        int(enr['entrée']) ) \
                + ' WHERE INE="{ine}"'.format(ine=ine)
            try:
                self.curs.execute(req)
            except sqlite3.Error as e:
                logging.error(u"Update d'un élève : {0}\n{1}".format(e.args[0], req))
                inc_list(self.importations, self.FAILED)
                return self.FAILED
            ofthejedi = self.UPDATE

        except sqlite3.Error as e:
            # Pour toute autre erreur, on laisse tomber
            logging.error(u"Insertion d'un élève : {0}\n{1}".format(e.args[0], req))
            inc_list(self.importations, self.FAILED)
            return self.FAILED

        # Reste à affecter notre élève à sa classe de cette année et de l'année dernière
        x = self.ecrire_affectation(
                ine,    date.year,     classe,  self.nom_etablissement,  enr['doublement'])
        etab = enr['sad_établissement']
        classe_pre = enr['sad_classe']
        if enr['doublement'] == 1: # Parfois, ces informations ne sont pas redonnées dans SIECLE
            classe_pre = classe
            etab = self.nom_etablissement
        y = self.ecrire_affectation(
                ine,    date.year-1,   classe_pre,  etab,   9)
        # En cas de problème, annulation des modifications précédentes
        if x == self.FAILED:
            raison.append('Pb affectation année en cours')
        if y == self.FAILED:
            #raison.append('Pb affectation année précédente')
            #logging.info(u"{0}".format(enr))
            pass
        if len(raison) > 0:
            self.conn.rollback()
            if self.ecrire_en_pending(enr, date.year, ', '.join(raison)):
                self.conn.commit()
                inc_list(self.importations, self.PENDING)
                return self.PENDING
            else:
                inc_list(self.importations, self.FAILED)
                return self.FAILED

        # Validation de l'écriture et de l'affectation à deux classes
        self.conn.commit()
        inc_list(self.importations, ofthejedi)
        return ofthejedi

    def ecrire_affectation(self, ine, annee, classe, etab, doublement):
        """
            Ajoute une affectations (un élève, dans une classe, dans un établissement)

        :param ine: l'INE de l'élève
        :param annee: l'année de scolarisation
        :param classe: sa classe
        :param etab: le nom de l'établissement
        :param doublement: si c'est un redoublement
        :type ine: str
        :type annee: int
        :type classe: str
        :type etab: str
        :type doublement: int - 0 ou 1
        """
        if classe == "" or etab == "":
            #logging.info("Erreur lors de l'affectation : classe ou établissement en défaut")
            return False
        req = 'INSERT INTO Affectations ' \
              +  '(INE, Année, Classe, Établissement, Doublement) ' \
              + 'VALUES ("{0}", {1}, "{2}", "{3}", {4})'.format( ine, annee, classe, etab, doublement )
        try:
            self.curs.execute(req)
        except sqlite3.IntegrityError as e:
             # L'affectation existe déjà -> maj
            req = 'UPDATE Affectations SET ' \
                  +  'Classe="{0}", Établissement="{1}", Doublement={2}'.format( classe, etab, doublement ) \
                  +  ' WHERE INE="{0}" AND Année={1}'.format( ine, annee )
            try:
                self.curs.execute(req)
            except sqlite3.Error as e:
                logging.error(u"Update d'une affectation : {0}\n{1}".format(e.args[0], req))
                return self.FAILED
            return self.UPDATE
        except sqlite3.Error as e:
            logging.error(u"Insertion d'une affectation : {0}\n{1}".format(e.args[0], req))
            return self.FAILED
        return self.INSERT

    def ecrire_classes(self, classes):
        """
            Insère une liste de classes (fin d'importation)
            
        :param classes: les classes à créer
        :type classes: list
        """
        for cla in classes:
            req = 'INSERT INTO Classes VALUES ("{0}", "", "", "")'.format(cla)
            try:
                self.curs.execute(req)
            except sqlite3.Error as e:
                logging.info(u"Erreur lors de l'ajout de la classe {0}:\n{1}".format(cla, e.args[0]))
        self.conn.commit()

    def ecrire_en_pending(self, enr, annee, raison=""):
        """
            Mise en attente de données incomplètes pour validation ultérieure
            
        :param enr: les données à enregistrer
        :param annee: année de scolarisation
        :param raison: raison de la mise en pending
        :type enr: dict 
        :type annee: int
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

        if r[1] == 0:
            req = 'INSERT INTO Pending ' \
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
        else:
             # Élève déjà en pending
            req = 'UPDATE Pending SET ' \
                + 'INE="{0}", Nom="{1}", Prénom="{2}", Naissance="{3}", Genre={4}, Mail="{5}", Entrée={6}, Classe="{7}", Établissement="{8}", Doublement={9}, Raison="{10}" '.format(
                    enr['ine'],             enr['nom'],             enr['prénom'],
                    enr['naissance'],       int(enr['genre']),      enr['mail'],
                    int(enr['entrée']),     enr['classe'],          enr['sad_établissement'],
                    int(enr['doublement']),     raison) \
                + 'WHERE rowid={rowid}'.format(rowid=r[0])
            try:
                self.curs.execute(req)
            except sqlite3.Error as e:
                logging.error(u"Update en pending : {0}\n{1}".format(e.args[0], req))
                return False
        return True

    def lire(self, annee, orderby, sens='ASC'):
        """
            Lit le contenu de la base élève
        
        :rtype: OrderedDict
        """
        data = collections.OrderedDict()
        req = 'SELECT * FROM Élèves NATURAL JOIN Affectations WHERE Année="{2}" ORDER BY {0} {1}, Nom ASC'.format(orderby, sens, annee)
        for row in self.curs.execute(req).fetchall():
            d = dict_from_row(row)
            ine = d['INE']
            # Calcul de l'âge actuel
            d['Âge'] = nb_annees(date(d['Naissance']))
            data[ine] = d
        # Génération du parcours
        req = 'SELECT INE,Année,Classe,Établissement,Doublement FROM Élèves NATURAL JOIN Affectations ORDER BY Année DESC'
        for row in self.curs.execute(req).fetchall():
            d = dict_from_row(row)
            ine = d['INE']
            an = d['Année']
            e = [ d['Classe'], d['Établissement'], d['Doublement'] ]
            if 'Parcours' not in data[ine].keys():
                data[ine]['Parcours'] = { an: e }
            else:
                # Déjà présent : on ajoute juste une année scolaire
                data[ine]['Parcours'][an] = e
        return data

    def lire_affectations(self):
        """
            Lit le contenu de la table affectations et classes
        
        :rtype: dict
        """
        data = {}
        req = 'SELECT INE, Année, A.Classe, Établissement, Doublement, Niveau, Filière, Section FROM Affectations A LEFT JOIN Classes C ON A.Classe = C.Classe'
        for row in self.curs.execute(req).fetchall():
            d = dict_from_row(row)
            key = d['INE']+'__'+str(d['Année'])
            data[key] = d
        return data

    def lire_classes(self):
        """
            Lit le contenu de la table classes
        
        :rtype: OrderedDict
        """
        data = collections.OrderedDict()
        req = 'SELECT * FROM Classes ORDER BY Classe ASC'
        for row in self.curs.execute(req).fetchall():
            d = dict_from_row(row)
            key = d['Classe']
            data[key] = d
        return data

    def lire_pending(self):
        """
            Lit le contenu de la base des élèves en pending
        
        :rtype: dict
        """
        data = {}
        req = 'SELECT rowid,* FROM Pending ORDER BY Nom,Prénom ASC'
        for row in self.curs.execute(req).fetchall():
            d = dict_from_row(row)
            key = d['rowid']
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
        if info == "totaux": # totaux
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
            sum(CASE WHEN CN.Niveau="Seconde" THEN 1 ELSE 0 END) "en seconde" 
            FROM Affectations A LEFT JOIN Affectations A2 ON A.INE=A2.INE 
            LEFT JOIN Classes CN ON A.Classe = CN.Classe 
            WHERE A.Année={0} AND A2.Année={1} AND {niv} 
            GROUP BY A2.Établissement""".format(annee, annee-1, niv=les_niveaux)
        elif info == "provenance classe": # provenance classe
            req = """SELECT CN.Classe classe, A2.Classe provenance, 
            A2.Établissement, count(*) total 
            FROM Classes CN LEFT JOIN Affectations A ON CN.Classe=A.Classe 
            LEFT JOIN Élèves E ON A.INE=E.INE 
            LEFT JOIN Affectations A2 ON A2.INE=A.INE 
            WHERE A.Année={0} AND A2.Année={1} AND {niv} 
            GROUP BY A2.Classe ORDER BY CN.Classe,A2.Établissement,A2.Classe""".format(annee, annee-1, niv=les_niveaux)
        elif info == "taux de passage": # taux de passage
            req = """SELECT Section, Niveau, INE, Année 
            FROM Affectations A LEFT JOIN Classes CN ON A.Classe=CN.Classe 
            WHERE Section<>'' AND {niv} ORDER BY Section,Niveau""".format(niv=les_niveaux)
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
