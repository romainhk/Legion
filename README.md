# Legion

Legion est un logiciel de suivi de cohorte pour lycée.

## Nécessite
* une exportation xml des données élève de SIECLE
* jquery / TableSorter (inclus)

## Build
> python setup.py bdist --format=zip

## Exécution sous windows
Le plus simple est de récupérer WinPython qui fournit toutes les dépendances nécessaires : http://winpython.sourceforge.net/
Il faut l'extraire à coté de legion, puis exécuter "lancer_avec_winpython.bat".

## Utilisation
Exécutez legion.py ; celui-ci ouvre automatiquement une interface web sur l'adresse http://localhost:5432
