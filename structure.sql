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
    -- Classement des classes (sic)
    "Classe" TEXT NOT NULL,
    "Niveau" TEXT NOT NULL,
    "Filière" TEXT NOT NULL,
    "Section" TEXT NOT NULL,
    PRIMARY KEY(Classe)
);
