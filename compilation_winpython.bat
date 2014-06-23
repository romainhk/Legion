rem == Compilation du programme ==
rem Necessite : WinPython 3

rem Emplacement de WinPython. Attention, ça ne supporte pas les accents...
set PATHWINPYTHON=WinPython
set build=build\exe.win-amd64-3.3
rem rd /S /Q %build%
"%PATHWINPYTHON%\WinPython Interpreter.exe" setup.py build

rem Lorsque la seconde fenêtre se referme, appuyez sur une touche
pause

copy base.sqlite %build%

rem Construction d'une archive
set bin=legion
rmdir /S /Q %bin%
move /Y %build% %bin%
"C:\Program Files\7-Zip\7z.exe" a build\legion.7z %bin%
