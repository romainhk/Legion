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
CREATE TABLE "EPS" (
    -- Les notes d'EPS de chaque élèves
    "INE" TEXT,
    "Année" INTEGER,
    "Activité 1" TEXT DEFAULT (''),
    "Note 1" REAL DEFAULT (-1.0), -- 0 >= note >= 20 ; -1 = exempt
    "Activité 2" TEXT DEFAULT (''),
    "Note 2" REAL DEFAULT (-1.0),
    "Activité 3" TEXT DEFAULT (''),
    "Note 3" REAL DEFAULT (-1.0),
    "Activité 4" TEXT DEFAULT (''),
    "Note 4" REAL DEFAULT (-1.0),
    "Activité 5" TEXT DEFAULT (''),
    "Note 5" REAL DEFAULT (-1.0),
    PRIMARY KEY(INE,Année)
);
