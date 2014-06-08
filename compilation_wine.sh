#!/bin/bash
# Pas envie de démarrer un windows ?
# => Compilez Legion en utilisant wine
#
# == Prérequis : Installation des programmes ==
# WinPython
#> wine64 WinPython-64bit-3.3.5.0.exe
#> wine64 msiexec /i cx_Freeze-4.3.3.win-amd64-py3.4.msi

#PYDIR="c:/Python34"
PYDIR="c:/WinPython-64bit-3.3.5.0/python-3.3.5.amd64"
PYTHON="wine $PYDIR/python.exe"
BUILD=build/exe.win-amd64-3.3

# Compilation
$PYTHON setup.py build

# Construction de l'archive
BIN=legion
CIBLE=legion.zip
rm -rf $BIN $CIBLE
mv $BUILD $BIN
zip -r $CIBLE $BIN
