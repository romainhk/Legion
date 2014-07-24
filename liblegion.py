#!/usr/bin/python
# -*- coding: utf-8  -*-
import webbrowser
import threading
import datetime
import random, string

"""
    Librairie contenant les fonctions générales
"""

def xstr(s):
    """
        Converti un None en chaine vide
    """
    if s is None:
        return ''
    return str(s)

def dict_from_row(row):
    """
        Converti un sqlite.Row en dictionnaire
    
    :rtype: dict
    """
    return dict(zip(row.keys(), row))

def inc_list(liste, index):
    """
        Incrémente un élément de la liste
    """
    liste[index] = liste[index] + 1

def date(chaine):
    """
        Converti une date au format de la base (ISO-8601) en objet Date
    
    :rtype: datetime
    """
    return datetime.datetime.strptime(chaine, "%Y-%m-%d")

def yearsago(years, from_date=None):
    """
        La date d'il y a quelques années
    """
    if from_date is None:
        from_date = datetime.datetime.now()
    try:
        return from_date.replace(year=from_date.year - years)
    except:
        # Must be 2/29!
        return from_date.replace(month=2, day=28, year=from_date.year-years)

def nb_annees(begin, end=None):
    """
        Nombre d'années depuis ...
    
    :rtype: int
    """
    if end is None:
        end = datetime.datetime.now()
    nb_annees = int((end - begin).days / 365.25)
    if begin > yearsago(nb_annees, end):
        return nb_annees - 1
    else:
        return nb_annees

def debut_AS(annee):
    """
        Converti une année en objet Date le jour de la rentrée scolaire
    
    :rtype: datetime
    """
    return datetime.date(year=annee, month=9, day=1)

def en_pourcentage(nombre):
    """
        Met en forme un nombre réel en pourcentage à 10^-1
    
    :rtype: str
    """
    return str( round(100*nombre,1) ) + ' %'

def filtrer_dict(dictionnaire, clef, valeur):
    """
        Filtre les éléments d'un dictionnaire de dictionnaires, dont la sous-valeur "clef" vaut "valeur"
    
    :example: { {clef: valeur, clef2: xxx}, {clef: autre_valeur, clef2: yyy} }
    :rtype: dict
    """
    premier_element = next (iter (dictionnaire.values()))
    if clef in premier_element:
        return dict((k, v) for k, v in dictionnaire.items() if v[clef]==valeur)
    else:
        return dictionnaire

def generer_nom_fichier(prefix, extension='png'):
    """
        Génère aléatoirement un nom de fichier

    :param prefix: le préfix à apposer devant le nom
    :type prefix: str
    :rtype: str
    """
    ident = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(12))
    return prefix + ident + '.' + extension

def eteindre_serveur(serveur):
    """
        Tue le serveur web

    :param serveur: le serveur à éteindre
    :type serveur: référence
    """
    assassin = threading.Thread(target=serveur.shutdown)
    assassin.daemon = True
    assassin.start()
