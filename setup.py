# -*- coding: utf-8 -*-

# Run the build process by running the command 'python setup.py build'

from cx_Freeze import setup, Executable

executables = [
    Executable('legion.py')
]

setup(name='legion',
      version='0.1',
      description='Legion',
      executables=executables
      )