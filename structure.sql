CREATE TABLE "Élèves" (
    -- Les données administratives des élèves
    "INE" TEXT PRIMARY KEY  NOT NULL,
    "Nom" TEXT,
    "Prénom" TEXT,
    "Naissance" TEXT,
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
    "Établissement" TEXT DEFAULT (null),
    "Doublement" INTEGER  DEFAULT (0), -- 0=non, 1=oui, 9=indéterminé
    PRIMARY KEY(INE,Année)
);
CREATE TABLE "Pending" (
    -- Enregistrements en attende de validation
    "ID" INTEGER  AUTO_INCREMENT,
    "INE" TEXT,
    "Nom" TEXT,
    "Prénom" TEXT,
    "Naissance" TEXT,
    "Genre" INTEGER NOT NULL  DEFAULT (0),
    "Mail" TEXT DEFAULT (null),
    "Entrée" INTEGER DEFAULT (null),
    "Diplômé" TEXT DEFAULT (null),
    "Situation" TEXT DEFAULT (null),
    "Lieu" TEXT DEFAULT (null),
    "Année" INTEGER,
    "Classe" TEXT,
    "Établissement" TEXT DEFAULT (null),
    "Doublement" INTEGER  DEFAULT (0),
    PRIMARY KEY(ID)
);
