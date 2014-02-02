import webbrowser
import threading

"""
    Librairies contenant les fonctions générales
"""

def xstr(s):
    """ Converti un None en chaine vide """
    if s is None:
        return ''
    return str(s)

def dict_from_row(row):
    """ Converti un sqlite.Row en dictionnaire """
    return dict(zip(row.keys(), row))

def open_browser(port):
    """ Ouvre un navigateur web sur la bonne page """
    def _open_browser():
        webbrowser.open(u'http://localhost:{port}'.format(port=port))
    thread = threading.Timer(0.5, _open_browser)
    thread.start()

