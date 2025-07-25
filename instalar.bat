@echo off
REM Script de instalación automatizada para el Sistema de Cámaras Orbbec
REM Ejecutar este script después de clonar el repositorio

echo ========================================
echo Sistema de Camaras Orbbec - Instalacion
echo ========================================
echo.

REM Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no esta instalado o no esta en el PATH
    echo Por favor instalar Python 3.8+ y volver a ejecutar
    pause
    exit /b 1
)

REM Verificar CMake
cmake --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: CMake no esta instalado o no esta en el PATH
    echo Por favor instalar CMake 3.15+ y volver a ejecutar
    pause
    exit /b 1
)

echo Python y CMake detectados correctamente
echo.

REM Instalar dependencias base
echo Instalando dependencias base...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: No se pudieron instalar las dependencias base
    pause
    exit /b 1
)
echo Dependencias base instaladas
echo.

REM Crear directorio para SDK si no existe
if not exist "backend\sdk" mkdir backend\sdk

REM Clonar SDK de Orbbec
echo Clonando SDK de Orbbec...
cd backend\sdk
if exist "pyorbbecsdk" (
    echo SDK ya existe, actualizando...
    cd pyorbbecsdk
    git pull
    cd ..
) else (
    git clone https://github.com/orbbec/pyorbbecsdk.git
    if %errorlevel% neq 0 (
        echo ERROR: No se pudo clonar el SDK de Orbbec
        cd ..\..
        pause
        exit /b 1
    )
)
echo SDK de Orbbec clonado/actualizado
echo.

REM Instalar dependencias del SDK
echo Instalando dependencias del SDK...
cd pyorbbecsdk
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: No se pudieron instalar las dependencias del SDK
    cd ..\..\..
    pause
    exit /b 1
)
echo Dependencias del SDK instaladas
echo.

REM Compilar SDK
echo Compilando SDK con CMake...
if exist "build" rmdir /s /q build
mkdir build
cd build
cmake ..
if %errorlevel% neq 0 (
    echo ERROR: CMake fallido - verificar Visual Studio Build Tools
    cd ..\..\..\..
    pause
    exit /b 1
)

cmake --build . --config Release
if %errorlevel% neq 0 (
    echo ERROR: Compilacion fallida
    cd ..\..\..\..
    pause
    exit /b 1
)
echo SDK compilado correctamente
echo.

REM Copiar archivos necesarios
echo Copiando archivos compilados...
cd ..
copy build\Release\*.pyd . >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: No se pudieron copiar archivos .pyd
    cd ..\..
    pause
    exit /b 1
)

echo Copiando DLLs...
xcopy lib\win_x64\*.dll . /Y >nul 2>&1
xcopy lib\win_x64\extensions lib\win_x64\extensions /E /Y >nul 2>&1

echo Archivos copiados correctamente
echo.

REM Verificar instalación
echo  Verificando instalación...
python -c "from pyorbbecsdk import *; print(' SDK importado correctamente')" 2>nul
if %errorlevel% neq 0 (
    echo  ERROR: El SDK no se puede importar
    echo Revisar manualmente la instalación
    cd ..\..
    pause
    exit /b 1
)

echo  Verificando detección de cámaras...
python -c "from pyorbbecsdk import *; ctx = Context(); devices = ctx.query_devices(); print(f' Cámaras detectadas: {devices.get_count()}')" 2>nul
if %errorlevel% neq 0 (
    echo  ADVERTENCIA: No se pudieron verificar las cámaras
    echo Esto puede ser normal si no hay cámaras conectadas
)

cd ..\..

echo.
echo ========================================
echo INSTALACION COMPLETADA EXITOSAMENTE
echo ========================================
echo.
echo Próximos pasos:
echo 1. Conectar las cámaras Orbbec Gemini 335L
echo 2. Ejecutar: cd backend\examples
echo 3. Ejecutar: python test_multicamera.py
echo.
echo Para más información consultar:
echo - README.md
echo - docs\INSTALACION_SDK.md
echo.
pause
