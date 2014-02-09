CREATE TABLE "Élèves" (
    "INE" TEXT PRIMARY KEY  DEFAULT (null) ,
    "Nom" TEXT,
    "Prénom" TEXT,
    "Naissance" TEXT,
    "Genre" INTEGER NOT NULL  DEFAULT (0) ,
    "Mail" TEXT DEFAULT (null) ,
    "Entrée" INTEGER DEFAULT (null) ,
    "Diplômé" TEXT DEFAULT (null) ,
    "Situation" TEXT DEFAULT (null) ,
    "Lieu" TEXT DEFAULT (null)
);
CREATE TABLE "Affectations"(
    "INE" TEXT,
    "Année" INTEGER,
    "Classe" TEXT NOT NULL, 
    "Établissement" TEXT DEFAULT (null) ,
    PRIMARY KEY(INE,Année)
);
