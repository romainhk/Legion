rem == Compilation du programme ==
rem Necessite : Python for windows 3.3, cx_freeze et 7zip SFX M
set build=build\exe.win-amd64-3.3
rem rd /S /Q %build%
C:\Python33\python.exe setup.py build

set output=legion
rem rd /S /Q %output%
rem mkdir %output%

rem xcopy /Y %build%\* %output%
rem cp base.sqlite %output%

rem 7zip sfx
