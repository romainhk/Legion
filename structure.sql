CREATE TABLE "Élèves" (
    -- Les données administratives des élèves
    "INE" TEXT PRIMARY KEY  NOT NULL,
    "Nom" TEXT,
    "Prénom" TEXT,
    "Naissance" DATE,
    "Genre" INTEGER NOT NULL  DEFAULT (0), -- 1=homme, 2=femme
    "Mail" TEXT DEFAULT (null),
    "Entrée" INTEGER DEFAULT (null),
    "Diplômé" TEXT DEFAULT (null),
    "Situation" TEXT DEFAULT (null),
    "Lieu" TEXT DEFAULT (null)
);
CREATE TABLE "Affectations" (
    -- L'affectation des élèves à leur classe et leur établissement
    "INE" TEXT,
    "Année" INTEGER,
    "Classe" TEXT NOT NULL,
    "MEF" TEXT DEFAULT (null),
    "Établissement" TEXT DEFAULT (null),
    "Doublement" INTEGER  DEFAULT (9), -- 0=non, 1=oui, 9=indéterminé
    PRIMARY KEY(INE,Année)
);
CREATE TABLE "Pending" (
    -- Enregistrements en attende de validation
    "INE" TEXT,
    "Nom" TEXT,
    "Prénom" TEXT,
    "Naissance" TEXT,
    "Genre" INTEGER NOT NULL  DEFAULT (0),
    "Mail" TEXT DEFAULT (null),
    "Entrée" INTEGER DEFAULT (null),
    "Classe" TEXT,
    "Établissement" TEXT DEFAULT (null),
    "Doublement" INTEGER  DEFAULT (0),
    "Raison" TEXT DEFAULT (null)
);
CREATE TABLE "Classes" (
    -- Classification des classes de l'établissement
    "Classe" TEXT NOT NULL,
    "Niveau" TEXT NOT NULL,
    "Filière" TEXT NOT NULL,
    "Section" TEXT NOT NULL,
    PRIMARY KEY(Classe)
);
CREATE TABLE "Options" (
    -- Options fixes (hashtable)
    "Nom" TEXT,
    "Valeur" TEXT,
    PRIMARY KEY(Nom)
);
INSERT INTO `Options` VALUES('couleurs','#80C0FF, #FF80BF, #B0FF80, #C080FF, #FFC080, #80FFC0, #FF8080, #80FF80, #8080FF'); -- liste ordonnée des couleurs pour les graphiques
INSERT INTO `Options` VALUES('date export','1970-01-01'); -- date de la plus récente d'exportation importée
INSERT INTO `Options` VALUES('header','Nom, Prénom, Âge, Mail, Genre, Année, Classe, Établissement, Doublement, Entrée, Diplômé, Situation, Lieu'); -- les en-têtes de la liste
INSERT INTO `Options` VALUES('niveaux','Seconde, Première, Terminale, 1BTS, 2BTS, Bac+1, Bac+3'); -- les niveaux
INSERT INTO `Options` VALUES('filières','Générale, Technologique, Pro, Enseignement supérieur'); -- les filières
CREATE TABLE "EPS" (
    -- Les notes d'EPS de chaque élèves
    "INE" TEXT,
    "Tier" INTEGER, -- 1 = BEP, 2 = 1er/Terminal
    "Activité 1" TEXT DEFAULT (''),
    "Note 1" REAL DEFAULT (-1.0), -- 0 >= note >= 20 ; -1 = non noté, -2 = absent, -3 = exempt
    "Activité 2" TEXT DEFAULT (''),
    "Note 2" REAL DEFAULT (-1.0),
    "Activité 3" TEXT DEFAULT (''),
    "Note 3" REAL DEFAULT (-1.0),
    "Activité 4" TEXT DEFAULT (''),
    "Note 4" REAL DEFAULT (-1.0),
    "Activité 5" TEXT DEFAULT (''),
    "Note 5" REAL DEFAULT (-1.0),
    "Verrou" INTEGER DEFAULT(0), -- indice de la note verrouillée ; 0 = aucune
    PRIMARY KEY(INE,Tier)
);
CREATE TABLE "EPS_Activités" (
    -- Liste des activités d'EPS et classement en compétence propre
    "Activité" TEXT,
    "CP" INTEGER,
    PRIMARY KEY(Activité)
);
INSERT INTO `EPS_Activités` VALUES('Course de ½ fond',1);
INSERT INTO `EPS_Activités` VALUES('Course de haies',1);
INSERT INTO `EPS_Activités` VALUES('Course de relais-vitesse',1);
INSERT INTO `EPS_Activités` VALUES('Lancer du disque',1);
INSERT INTO `EPS_Activités` VALUES('Lancer de javelot',1);
INSERT INTO `EPS_Activités` VALUES('Saut en hauteur',1);
INSERT INTO `EPS_Activités` VALUES('Pentabond',1);
INSERT INTO `EPS_Activités` VALUES('Natation de vitesse',1);
INSERT INTO `EPS_Activités` VALUES('Natation de distance',1);
INSERT INTO `EPS_Activités` VALUES('Triathlon',1);
INSERT INTO `EPS_Activités` VALUES('Escalade',2);
INSERT INTO `EPS_Activités` VALUES("Course d'orientation",2);
INSERT INTO `EPS_Activités` VALUES('Natation sauvetage',2);
INSERT INTO `EPS_Activités` VALUES('VTT',2);
INSERT INTO `EPS_Activités` VALUES('Acrosport',3);
INSERT INTO `EPS_Activités` VALUES('Aérobic',3);
INSERT INTO `EPS_Activités` VALUES('Arts du cirque',3);
INSERT INTO `EPS_Activités` VALUES('Danse',3);
INSERT INTO `EPS_Activités` VALUES('Gymnastique',3);
INSERT INTO `EPS_Activités` VALUES('Gymnastique rythmique',3);
INSERT INTO `EPS_Activités` VALUES('Basket-ball',4);
INSERT INTO `EPS_Activités` VALUES('Football',4);
INSERT INTO `EPS_Activités` VALUES('Handball',4);
INSERT INTO `EPS_Activités` VALUES('Rugby',4);
INSERT INTO `EPS_Activités` VALUES('Volley-ball',4);
INSERT INTO `EPS_Activités` VALUES('Badminton',4);
INSERT INTO `EPS_Activités` VALUES('Tennis de table',4);
INSERT INTO `EPS_Activités` VALUES('Boxe française',4);
INSERT INTO `EPS_Activités` VALUES('Judo',4);
INSERT INTO `EPS_Activités` VALUES('Lutte',4);
INSERT INTO `EPS_Activités` VALUES('Course en durée',5);
INSERT INTO `EPS_Activités` VALUES('Musculation',5);
INSERT INTO `EPS_Activités` VALUES('Natation en durée',5);
INSERT INTO `EPS_Activités` VALUES('Step',5);
