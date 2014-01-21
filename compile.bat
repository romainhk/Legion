rem == Compilation du programme ==
rem Necessite : Python for windows 3.3, cx_freeze
set build=build\exe.win-amd64-3.3
rem rd /S /Q %build%
C:\Python33\python.exe setup.py build

rem set output=legion
rem rd /S /Q %output%
rem mkdir %output%
rem xcopy /Y %build%\* %output%

copy base.sqlite %build%

rem Le dossier "%build%" contient maintenant de quoi executer Legion sur windows