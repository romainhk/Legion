# Legion

Legion est un logiciel de suivi de cohorte pour lycée.

## Nécessite
* une exportation xml des données élève de SIECLE ;
* jquery / TableSorter (inclus) ;
* un interpréteur python 33 ;
* matplotlib, pylab, numpy... (pour la partie graphique) ;
* et pour une utilisation sous windows : cx\_freeze, pywin32.

## Exécution
Sous linux :
> python3 legion.py

Sous windows, le plus simple est d'installer WinPython, un environnement python qui inclu tout sauf cx\_freeze, puis exécuter "lancer_avec_winpython.bat".

## Build
> python setup.py build

## Utilisation
Exécutez legion.py ou legion.exe ; celui-ci ouvre automatiquement une interface web sur l'adresse http://localhost:5432
