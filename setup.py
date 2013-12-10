# -*- coding: utf-8 -*-

# Run the build process by running the command 'python setup.py build'

from cx_Freeze import setup, Executable

build_exe_options = { "optimize": 1 }
executables = [
    Executable('legion.py')
]

setup(name='legion',
      version='0.3',
      description='Legion',
	  options = {"build_exe": build_exe_options},
      executables=executables
      )