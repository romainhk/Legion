# -*- coding: utf-8 -*-

# Run the build process by running the command 'python setup.py build'

from cx_Freeze import setup, Executable
import platform, os

if platform.system() == 'Windows':
    base = 'Console'
else:
    base = None

# Liste les fichiers à embarquer aussi
dir = os.getcwd();
includefiles=[]
for root, subFolders, files in os.walk(dir+os.sep+'web'):
    # Adresse relative du dossier exploré
    sub=root.replace(dir, '').strip('\\')
    for file in files:
        includefiles.append(os.path.join(sub, file))
includefiles.append('README.md')

print(includefiles)

executables = [ Executable(
    script='legion.py',
    base=base,
    targetName='legion.exe',
    compress=True,
    appendScriptToLibrary=False,
    appendScriptToExe=True
    ) ]

build_exe_options = { "optimize": 1, 'include_files':includefiles }

setup(name='legion',
      version='0.3',
      description='Legion',
      author='Romain Hennuyer',
      author_email='romain.hennuyer@ac-lille.fr',
      #url='',
      license='GPLv3',
	  options = {"build_exe": build_exe_options},
      executables=executables
      )