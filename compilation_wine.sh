#!/bin/bash
# Pas envie de démarrer un windows ?
# => Compilez Legion en utilisant wine
#
# == Prérequis : Installation des programmes ==
# > wine msiexec /i python-3.4.0.msi
# > wine msiexec /i cx_Freeze-4.3.3.win32-py3.4.msi
#
# Nécessite aussi vcredist

PYDIR="c:/Python34"
PYTHON="wine $PYDIR/python.exe"
#WINPWD=`winepath -w \`pwd\``
BUILD=build/exe.win32-3.4

# Compilation
$PYTHON setup.py build

# Construction de l'archive
BIN=legion
CIBLE=legion.zip
rm -rf $BIN $CIBLE
mv $BUILD $BIN
zip -r $CIBLE $BIN
