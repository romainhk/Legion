rem == Compilation du programme ==
rem Necessite : Python for windows 3.3, cx_freeze, 7-zip, numpy, matplotlib...
set build=build\exe.win-amd64-3.4
rem rd /S /Q %build%
C:\Python34\python.exe setup.py build

copy base.sqlite %build%

rem Construction d'une archive
set bin=legion
rmdir /S /Q %bin%
move /Y %build% %bin%
"C:\Program Files\7-Zip\7z.exe" a build\legion.7z %bin%