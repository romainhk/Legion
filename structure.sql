CREATE TABLE "Élèves" (
    "INE" TEXT PRIMARY KEY  DEFAULT (null) ,
    "Nom" TEXT,
    "Prénom" TEXT,
    "Doublement" TEXT NOT NULL  DEFAULT (0) ,
    "Naissance" NUMERIC,
    "Genre" INTEGER NOT NULL  DEFAULT (0) ,
    "Entrée" TEXT
)
CREATE TABLE "Affectations"(
    Classe TEXT, 
    Année INTEGER,
    INE TEXT,
    PRIMARY KEY(Classe,Année,INE)
)
