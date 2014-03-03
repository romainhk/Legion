import webbrowser
import threading
import datetime

"""
    Librairie contenant les fonctions générales
"""

def xstr(s):
    """ Converti un None en chaine vide """
    if s is None:
        return ''
    return str(s)

def dict_from_row(row):
    """ Converti un sqlite.Row en dictionnaire """
    return dict(zip(row.keys(), row))

def dict_add(dictionnaire, index, val):
    """ Ajoute val à la clé 'index' du dictionnaire, si l'entrée existe """
    if index in dictionnaire:
        dictionnaire[index] = dictionnaire[index] + val
    else:
        dictionnaire[index] = val

def open_browser(port):
    """ Ouvre un navigateur web sur la bonne page """
    def _open_browser():
        webbrowser.open(u'http://localhost:{port}'.format(port=port))
    thread = threading.Timer(0.5, _open_browser)
    thread.start()

def datefr(chaine):
    """ Converti une date au format français en objet Date
    """
    return datetime.datetime.strptime(chaine, "%d/%m/%Y")

def yearsago(years, from_date=None):
    """ La date d'il y a quelques années
    """
    if from_date is None:
        from_date = datetime.datetime.now()
    try:
        return from_date.replace(year=from_date.year - years)
    except:
        # Must be 2/29!
        return from_date.replace(month=2, day=28, year=from_date.year-years)

def nb_annees(begin, end=None):
    """ Nombre d'années depuis ...
    """
    if end is None:
        end = datetime.datetime.now()
    nb_annees = int((end - begin).days / 365.25)
    if begin > yearsago(nb_annees, end):
        return nb_annees - 1
    else:
        return nb_annees

def debut_AS(annee):
    """ Converti une année en objet Date le jour de la rentrée scolaire
    """
    return datetime.date(year=annee, month=9, day=1)

def en_pourcentage(nombre):
    """ Met en forme un nombre en pourcentage """
    return str( round(100*nombre,1) ) + ' %'
