#!/usr/bin/python
# -*- coding: utf-8  -*-
import sqlite3
import shutil
import datetime
import logging
import os
from liblegion import *

class Database():
    def __init__(self, root):
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

    def ecrire(self, enr, date, nom_etablissement):
        """
            Ajoute les informations d'un élève à la bdd

        :param enr: les données à enregistrer
        :param date: l'objet date de référence pour l'importation
        :param nom_etablissement: le nom de l'établissement [sic]
        :type enr: dict
        :type date: datetime
        :type nom_etablissement: str
        :return: define du type d'importation effectuée
        :rtype: int
        """
        ofthejedi = self.INSERT # valeur de retour par défaut
        ine = enr['ine']
        classe = enr['classe']
        enr['Diplômé'] = enr['Situation'] = enr['Lieu'] = '?'
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

        # Ajout de l'élève
        req = 'INSERT INTO Élèves ' \
            + '(INE, Nom, Prénom, Naissance, Genre, Mail, Entrée, Diplômé, Situation, Lieu) ' \
            + 'VALUES ("{0}", "{1}", "{2}", "{3}", {4}, "{5}", {6}, "{7}", "{8}", "{9}")'.format(
                    ine,                enr['nom'],         enr['prénom'],
                    enr['naissance'],   int(enr['genre']),  enr['mail'],
                    int(enr['entrée']), enr['Diplômé'],    enr['Situation'],
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
                ine,    date.year,     classe,  nom_etablissement,  enr['doublement'])
        etab = enr['sad_établissement']
        classe_pre = enr['sad_classe']
        if enr['doublement'] == 1: # Parfois, ces informations ne sont pas redonnées dans SIECLE
            classe_pre = classe
            etab = nom_etablissement
        y = self.ecrire_affectation(
                ine,    date.year-1,   classe_pre,  etab,   9)
        # En cas de problème, annulation des modifications précédentes
        if x == self.FAILED:
            raison.append('Pb affectation année en cours')
        if y == self.FAILED:
            #raison.append('Pb affectation année précédente')
            logging.warning(u"{0}".format(enr))
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
            logging.info("Erreur lors de l'affectation : classe ou établissement en défaut")
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
        # Protection contre des données qui seraient non valides
        for k, v in enr.items():
            if v is None: enr[k] = '0'

        # On regarde si l'enregistrement est déjà présent
        ine = enr['ine']
        nom = enr['nom']
        prenom = enr['prénom']
        if ine != '0': # Par ine
            condition = 'INE="{0}"'.format(ine)
        elif nom !='0' and prenom != '0': # Par nom/prénom
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
                + '(INE, Nom, Prénom, Naissance, Genre, Mail, Entrée, Diplômé, Situation, Lieu, Année, Classe, Établissement, Doublement, Raison) ' \
                + 'VALUES ("{0}", "{1}", "{2}", "{3}", {4}, "{5}", {6}, "{7}", "{8}", "{9}", {10}, "{11}", "{12}", {13}, "{14}")'.format(
                    enr['ine'],             enr['nom'],             enr['prénom'],
                    enr['naissance'],       int(enr['genre']),      enr['mail'],
                    int(enr['entrée']),     enr['Diplômé'],        enr['Situation'],
                    enr['Lieu'],            annee,                  enr['classe'],
                    enr['sad_établissement'],   int(enr['doublement']),     raison)
            try:
                self.curs.execute(req)
            except sqlite3.Error as e:
                logging.error(u"Insertion en pending : {0}\n{1}".format(e.args[0], req))
                return False
        else:
             # Déjà en pending
            req = 'UPDATE Pending SET ' \
                + 'INE="{0}", Nom="{1}", Prénom="{2}", Naissance="{3}", Genre={4}, Mail="{5}", Entrée={6}, Diplômé="{7}", Situation="{8}", Lieu="{9}", Année={10}, Classe="{11}", Établissement="{12}", Doublement={13}, Raison="{14}" '.format(
                    enr['ine'],             enr['nom'],             enr['prénom'],
                    enr['naissance'],       int(enr['genre']),      enr['mail'],
                    int(enr['entrée']),     enr['Diplômé'],        enr['Situation'],
                    enr['Lieu'],            annee,                  enr['classe'],
                    enr['sad_établissement'],   int(enr['doublement']),     raison) \
                + 'WHERE rowid={rowid}'.format(rowid=r[0])
            try:
                self.curs.execute(req)
            except sqlite3.Error as e:
                logging.error(u"Update en pending : {0}\n{1}".format(e.args[0], req))
                return False
        return True

    def lire(self):
        """
            Lit le contenu de la base
        
        :rtype: dict
        """
        data = {}
        req = 'SELECT * FROM Élèves NATURAL JOIN Affectations ORDER BY Nom,Prénom ASC, Année DESC'
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
                d['Âge'] = nb_annees(datefr(d['Naissance']))
                data[ine] = d
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
        
        :rtype: dict
        """
        data = {}
        req = 'SELECT * FROM Classes ORDER BY Classe ASC'
        for row in self.curs.execute(req).fetchall():
            d = dict_from_row(row)
            key = d['Classe']
            data[key] = d
        return data

    def lire_pending(self):
        """
            Lit le contenu de la base
        
        :rtype: dict
        """
        data = {}
        req = 'SELECT rowid,* FROM Pending ORDER BY Nom,Prénom ASC, Année DESC'
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

    def stats(self, info, annee):
        """ Génère une liste avec les stats voulues
        """
        retourner_uniquement = None # Pour ne retourner que la valeur désignée
        if info == "annees_scolarisation":
            req = 'SELECT INE,count(*) Scolarisation FROM Affectations WHERE Établissement="Jean Moulin" GROUP BY INE'.format(info)
        elif info == "issue_pro":
            req = "SELECT Classe,Niveau,Filière,Section,count(*) NbIssueDePro FROM Affectations NATURAL JOIN Classes WHERE INE IN (SELECT INE FROM Affectations A LEFT JOIN Classes C ON A.Classe = C.Classe WHERE Année={1} AND Filière='Pro') AND Année = {0} GROUP BY Classe".format(annee, annee-1)
            retourner_uniquement = 'NbIssueDePro'
        elif info == "effectif_bts":
            req = 'SELECT count(*) Nb FROM Affectations A LEFT JOIN Classes C ON A.Classe=C.Classe WHERE Année={0} AND Niveau=="BTS"'.format(annee)
            retourner_uniquement = 'Nb'
        elif info == "garcons":
            req = 'SELECT count(*) Nb FROM Élèves E LEFT JOIN Affectations A ON E.INE=A.INE WHERE Genre="1" AND Année={0}'.format(annee)
            retourner_uniquement = 'Nb'
        elif info == "garcons_en_bts":
            req = 'SELECT count(*) Nb FROM Élèves E LEFT JOIN Affectations A ON E.INE=A.INE LEFT JOIN Classes C ON A.Classe=C.Classe WHERE Genre="1" AND Année={0} AND Niveau="BTS"'.format(annee)
            retourner_uniquement = 'Nb'
        elif info == "total_doublant":
            req = 'SELECT count(*) Nb FROM Élèves E LEFT JOIN Affectations A ON E.INE=A.INE LEFT JOIN Classes C ON A.Classe=C.Classe WHERE Doublement="1" AND Année={0}'.format(annee)
            retourner_uniquement = 'Nb'
        elif info == "provenance":
            req = 'SELECT A2.Établissement,count(*) total,sum(CASE WHEN Niveau="Seconde" THEN 1 ELSE 0 END) "en seconde" FROM Affectations A LEFT JOIN Affectations A2 ON A.INE=A2.INE LEFT JOIN Classes C ON A.Classe = C.Classe WHERE A.Année={0} AND A2.Année={1} GROUP BY A2.Établissement'.format(annee, annee-1)
        elif info == "provenance_bts":
            req = 'SELECT C.Classe "classe de bts",A2.Classe provenance,A2.Établissement,count(*) total FROM Classes C LEFT JOIN Affectations A ON C.Classe=A.Classe LEFT JOIN Élèves E ON A.INE=E.INE LEFT JOIN Affectations A2 ON A2.INE=A.INE WHERE Niveau="BTS" AND A.Année={0} AND A2.Année={1} GROUP BY A2.Classe ORDER BY C.Classe,A2.Établissement'.format(annee, annee-1)
        else:
            logging.error('Information "{0}" non disponible'.format(info))
            return []
        try:
            self.curs.execute(req)
        except sqlite3.Error as e:
            logging.error("Erreur lors de la génération de stats '{0}' :\n{1}".format(info, e.args[0]))
        data = []
        for row in self.curs.execute(req).fetchall():
            d = dict_from_row(row)
            data.append(d)
        if retourner_uniquement is not None:
            data = data.pop()[retourner_uniquement]
        logging.debug(data)
        return data
