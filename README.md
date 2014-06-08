# Legion

Legion est un logiciel de suivi de cohorte pour lycée.

## Nécessite
* une exportation xml des données élève de SIECLE
* jquery / TableSorter (inclus)

## Build
Pour pouvoir compiler l'application sous windows, il faut :
* un interpréteur python 33 :
* cx\_freeze : 
* pywin32 : 
* matplotlib, pylab, numpy... (pour la partie graphique)

Le plus simple est d'installer WinPython, un environnement python qui inclu tout (sauf cx\_freeze)

> python setup.py bdist --format=zip

## Exécution sous windows
Le plus simple est de récupérer WinPython qui fournit toutes les dépendances nécessaires : http://winpython.sourceforge.net/
Il faut l'extraire à coté de legion, puis exécuter "lancer_avec_winpython.bat".

## Utilisation
Exécutez legion.py ; celui-ci ouvre automatiquement une interface web sur l'adresse http://localhost:5432
