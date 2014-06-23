# -*- coding: utf-8 -*-

# Lancer la compilation avec la commande 'python setup.py build'

from cx_Freeze import setup, Executable
import platform, os

if platform.system() == 'Windows':
    base = 'Console'
    # Winpython ne compile pas bien si on n'insère pas obligatoirement ce paquet
    packages = ['matplotlib.backends.backend_tkagg']
else:
    base = None
    packages = []

# Liste les fichiers à embarquer aussi
dir = os.getcwd();
includefiles=[]
ignoredDirs= ['web'+os.sep+'cache', 'web'+os.sep+'sources']
for root, subFolders, files in os.walk(dir+os.sep+'web'):
    # Adresse relative du dossier exploré
    sub=root.replace(dir, '').strip(os.sep)
    if not sub in ignoredDirs:
        for f in files:
            if not f.endswith('~'): # exclusion des fichiers temporaires
                includefiles.append(os.path.join(sub, f))
includefiles.append('README.md')
includefiles.append('LICENSE')
includefiles.append('LICENSE_GPL')
includefiles.append('config.cfg')
includefiles.append('base.sqlite')
print(includefiles)

executables = [ Executable(
    script='legion.py',
    base=base,
    targetName='legion.exe',
    compress=True,
    appendScriptToLibrary=False,
    appendScriptToExe=True
    ) ]

build_exe_options = { "optimize": 1, 'include_files':includefiles, 'include_msvcr':1, 'packages':packages }

setup(name='legion',
      version='0.8',
      description='Legion',
      author='Romain Hennuyer',
      author_email='romain.hennuyer@gmail.com',
      #url='',
      license='GPLv3',
	  options = {"build_exe": build_exe_options},
      executables=executables
      )
