import sqlite3
import shutil
import datetime
import logging
import os
from liblegion import *

class Database():
    def __init__(self, root):
        bdd = root+os.sep+'base.sqlite'
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

    def get_stats(self, annee):
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
        return data

    def maj_champ(self, table, ident, champ, donnee):
        """ Mets à jour un champ de la base """
        if table == 'Élèves':       col = 'INE'
        elif table == 'Classes':    col = 'Classe'
        req = u'UPDATE {tab} SET {champ}="{d}" WHERE {col}="{ident}"'.format(tab=table, col=col, ident=ident, champ=champ, d=donnee)
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

    def inserer_affectation(self, ine, annee, classe, etab, doublement):
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

    def in_pending(self, enr, annee):
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

    def ecrire(self, enr):
        """ Ajoute les informations d'un élève à la bdd """
        ine = enr['ine']
        classe = enr['classe']
        enr[u'Diplômé'] = enr[u'Situation'] = enr['Lieu'] = '?'
        if ine is None or classe is None:
            self.in_pending(enr, self.date.year)
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
            x = self.inserer_affectation(
                    ine,    annee,     classe,  'Jean Moulin',  enr['doublement'])
            etab = enr['sad_établissement']
            classe_pre = enr['sad_classe']
            if enr['doublement']: # Parfois, ces informations ne sont pas redonnées dans SIECLE
                classe_pre = classe
                etab = 'Jean Moulin'
            y = self.inserer_affectation(
                    ine,    annee-1,   classe_pre,  etab,   9)
            # En cas de problème, annulation des modifications précédentes
            if not x or not y:
                self.conn.rollback()
                #logging.warning(u"Rollback suite à un problème d'affectation\n{0}".format(enr))
                self.in_pending(enr, annee)

        else:
            #logging.warning(u"L'élève {0} est déjà présent dans la base {1}".format(ine, self.date.year))
            pass

        # Validation de l'affectation à une classe
        self.conn.commit()
        self.nb_import = self.nb_import + 1

    def lire(self):
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

    def lire_pending(self):
        """ Lit le contenu de la base """
        data = {}
        req = u'SELECT * FROM Pending ORDER BY Nom,Prénom ASC, Année DESC'
        for row in self.curs.execute(req).fetchall():
            d = dict_from_row(row)
            ine = d['INE']
            data[ine] = d
        return data

    def lire_classes(self):
        """ Lit le contenu de la table classes """
        data = {}
        req = u'SELECT * FROM Classes ORDER BY Classe ASC'
        for row in self.curs.execute(req).fetchall():
            d = dict_from_row(row)
            classe = d['Classe']
            data[classe] = d
        return data


