rem Compilation du programme
rem Necessite : Python for windows 3.3, cx_freeze
C:\Python33\python.exe setup.py build
set output=build-legion
mkdir %output%
xcopy /Y build\exe.win-amd64-3.3\* %output%
for /r web %%x in (*) do xcopy /s /c /d /e /h /i /r /y %%x %output%\web\