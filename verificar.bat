@echo off
REM Script de verificación del Sistema de Cámaras Orbbec
REM Ejecutar para diagnosticar problemas

echo ========================================
echo Sistema de Camaras Orbbec - Verificacion
echo ========================================
echo.

REM Verificar Python
echo 🔍 Verificando Python...
python --version
if %errorlevel% neq 0 (
    echo ❌ ERROR: Python no disponible
    goto :end
)
echo ✅ Python OK
echo.

REM Verificar CMake
echo 🔍 Verificando CMake...
cmake --version | findstr /r "cmake"
if %errorlevel% neq 0 (
    echo ❌ ERROR: CMake no disponible
) else (
    echo ✅ CMake OK
)
echo.

REM Verificar dependencias base
echo 🔍 Verificando dependencias base...
python -c "import cv2; print(f'✅ OpenCV: {cv2.__version__}')" 2>nul || echo ❌ OpenCV no disponible
python -c "import numpy as np; print(f'✅ NumPy: {np.__version__}')" 2>nul || echo ❌ NumPy no disponible
python -c "import flask; print(f'✅ Flask: {flask.__version__}')" 2>nul || echo ❌ Flask no disponible
echo.

REM Verificar SDK
echo 🔍 Verificando SDK de Orbbec...
if not exist "backend\sdk\pyorbbecsdk" (
    echo ❌ ERROR: SDK no encontrado en backend\sdk\pyorbbecsdk
    goto :end
)

cd backend\sdk\pyorbbecsdk

REM Verificar archivos compilados
if not exist "*.pyd" (
    echo ❌ ERROR: Archivos .pyd no encontrados - SDK no compilado
    goto :cleanup
)
echo ✅ Archivos .pyd encontrados

REM Verificar DLLs
if not exist "OrbbecSDK.dll" (
    echo ❌ ERROR: OrbbecSDK.dll no encontrado
    goto :cleanup
)
echo ✅ DLLs principales encontradas

REM Probar importación
echo 🔍 Probando importación del SDK...
python -c "from pyorbbecsdk import *; print('✅ SDK importado correctamente')" 2>nul
if %errorlevel% neq 0 (
    echo ❌ ERROR: No se puede importar el SDK
    echo Posibles soluciones:
    echo 1. Ejecutar instalar.bat
    echo 2. Copiar DLLs manualmente: copy lib\win_x64\*.dll .
    goto :cleanup
)

REM Verificar Context
echo 🔍 Probando inicialización...
python -c "from pyorbbecsdk import *; ctx = Context(); print('✅ Context inicializado')" 2>nul
if %errorlevel% neq 0 (
    echo ❌ ERROR: No se puede inicializar Context
    goto :cleanup
)

REM Verificar cámaras
echo 🔍 Verificando cámaras conectadas...
python -c "
from pyorbbecsdk import *
ctx = Context()
devices = ctx.query_devices()
count = devices.get_count()
print(f'🔍 Cámaras detectadas: {count}')
if count == 0:
    print('⚠️  No se detectaron cámaras. Verificar:')
    print('   - Cámaras conectadas por USB')
    print('   - Drivers instalados')
    print('   - Permisos de acceso')
else:
    for i in range(count):
        device = devices.get_device_by_index(i)
        info = device.get_device_info()
        print(f'📷 Cámara {i}: {info.get_name()} - S/N: {info.get_serial_number()}')
" 2>nul

if %errorlevel% neq 0 (
    echo ❌ ERROR: No se pueden verificar las cámaras
    goto :cleanup
)

echo.
echo ✅ Verificación completada
echo.
echo 🔨 Para probar el sistema completo:
echo cd backend\examples
echo python test_multicamera.py

:cleanup
cd ..\..

:end
echo.
pause
