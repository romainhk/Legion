#!/usr/bin/python
# -*- coding: utf-8  -*-
import csv, sqlite3

class Legion:
    """ Classe Legion
    """
    def __init__(self, fichier):
        self.fichier = fichier
        self.enreg = {}
        self.header = []
        self.annee = 2013
        #DB
        bdd = 'base.sqlite'
        try:
            self.conn = sqlite3.connect(bdd)
        except:
            pywikibot.output("Impossible d'ouvrir la base sqlite {0}".format(bdd))
            exit(2)
        self.conn.row_factory = sqlite3.Row
        self.curs = self.conn.cursor()
        # TODO : faire une sauvegarde de la base

    def open_csv(self):
        """ Importe le csv
        """
        iINE = 0 # position de l'INE
        with open(self.fichier, 'r') as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='"')
            for row in reader:
                if reader.line_num == 1: # première ligne = entêtes
                    self.header = row
                    try:
                        iINE = row.index('INE')
                    except:
                        print('Impossible de trouver la colonne INE')
                        return False
                    #for h in row:
                    #    self.enreg[h] = []
                    continue
                #self.enreg[row.pop(iINE)] = row
                if row[iINE] not in self.enreg:
                    self.enreg[row[iINE]] = row
                else:
                    print('Enregistrement en double : {0}').format(row)
                #for h, v in zip(self.header, row):
                #    self.enreg[h].append(v)

    def writetodb(self):
        """ Ecrit un enregistrement dans la base
        """
        try:
            iINE = self.header.index(u'INE')
            iNom = self.header.index(u'Nom')
            iPre = self.header.index(u'Prénom')
            iClasse = self.header.index(u'Classe')
        except:
            print(u"Le fichier csv n'est pas au bon format.")
            return False
        for k,v in self.enreg.items():
            req = u'INSERT INTO Élèves ' \
                + u'(INE, Nom, Prénom, Classe, Année) VALUES ("%s", "%s", "%s", "%s", %i)' \
                % (v[iINE], v[iNom], v[iPre], v[iClasse], self.annee)
            try:
                self.curs.execute(req)
            except sqlite3.Error as e:
                print(req)
                print(u"Erreur lors de l'insertion :\n%s" % (e.args[0]))
            self.conn.commit()

    def readfromdb(self):
        """ Lit le contenu de la base
        """
        for row in self.curs.execute(u'SELECT * FROM Élèves ORDER BY INE'):
            print(row['INE'])
        
    def run(self):
        self.open_csv()
        print(self.header)
        print(self.enreg)
        #self.writetodb()
        self.readfromdb()

def main():
    legion = Legion('export.csv')
    legion.run()

if __name__ == "__main__":
    try:
        main()
    finally:
        pass
