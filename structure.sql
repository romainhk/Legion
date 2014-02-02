CREATE TABLE "Élèves" (
    "INE" TEXT PRIMARY KEY  DEFAULT (null) ,
    "Nom" TEXT,
    "Prénom" TEXT,
    "Naissance" TEXT,
    "Genre" INTEGER NOT NULL  DEFAULT (0) ,
    "Mail" TEXT DEFAULT (null) ,
    "Entrée" INTEGER DEFAULT (null) ,
    "SAD_établissement" TEXT DEFAULT (null) ,
    "SAD_classe" TEXT DEFAULT (null) ,
    "Diplômé" TEXT DEFAULT (null) ,
    "Après" TEXT
);
CREATE TABLE "Affectations"(
    "Classe" TEXT, 
    "Année" INTEGER,
    "INE" TEXT,
    "Doublement" INTEGER NOT NULL  DEFAULT (0),
    PRIMARY KEY(Classe,Année,INE)
);
