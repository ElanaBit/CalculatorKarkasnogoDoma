@echo off
chcp 65001 >nul
cd /d "%~dp0"
setlocal

echo ============================================
echo  Сборка приложения "Калькулятор каркасного дома"
echo ============================================
echo.
echo [1/2] Сборка exe (PyInstaller)...
pyinstaller app.spec --noconfirm
if errorlevel 1 (
  echo.
  echo ОШИБКА: сборка exe не удалась.
  exit /b 1
)
echo Готово: dist\КалькуляторКаркасногоДома.exe
echo.

echo [2/2] Сборка установщика (Inno Setup 6)...
set "ISCC64=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
set "ISCC32=C:\Program Files\Inno Setup 6\ISCC.exe"
if exist "%ISCC64%" (
  "%ISCC64%" installer.iss
  if errorlevel 1 goto :iskip
) else if exist "%ISCC32%" (
  "%ISCC32%" installer.iss
  if errorlevel 1 goto :iskip
) else (
  echo.
  echo Внимание: Inno Setup 6 не найден.
  echo Установите его с https://jrsoftware.org/isdl.php и запустите build.bat повторно,
  echo или используйте готовый dist\КалькуляторКаркасногоДома.exe (уже собран).
  goto :done
)
echo.
echo Установщик готов: installer\Калькулятор_КаркасногоДома_Установка.exe
goto :done

:iskip
echo ОШИБКА: не удалось собрать установщик. Проверьте Inno Setup.
:done
endlocal
pause
