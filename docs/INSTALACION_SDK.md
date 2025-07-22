# Instalación y Configuración del SDK Orbbec

Esta guía documenta todos los pasos necesarios para configurar el PyOrbbecSDK en el proyecto, independientemente del código específico. Estos pasos deben realizarse **siempre** que se clone el repositorio.

## 🔧 Requisitos del Sistema

### Software necesario:
- **Python 3.8+** (recomendado 3.10)
- **CMake 3.15+**
- **Visual Studio Build Tools** (o Visual Studio Community)
- **Git**

### Hardware:
- Una o más cámaras **Orbbec Gemini 335L** conectadas por USB

## 📥 Instalación Paso a Paso

### 1. Clonar el repositorio del proyecto
```bash
git clone <url-del-proyecto>
cd <directorio-del-proyecto>
```

### 2. Instalar dependencias base
```bash
pip install -r requirements.txt
```

### 3. Clonar el SDK de Orbbec
```bash
cd backend/sdk
git clone https://github.com/orbbec/pyorbbecsdk.git
cd pyorbbecsdk
```

### 4. Instalar dependencias específicas del SDK
```bash
pip install -r requirements.txt
```

### 5. Compilar el SDK con CMake
```bash
mkdir build
cd build
cmake ..
cmake --build . --config Release
```

### 6. **CRÍTICO**: Copiar archivos compilados y DLLs
```bash
# Volver al directorio raíz del SDK
cd ..

# Copiar el módulo Python compilado
copy build\Release\*.pyd .

# Copiar las DLLs necesarias del SDK
copy lib\win_x64\* . -Recurse -Force
```

### 7. Verificar la instalación
```bash
python -c "from pyorbbecsdk import *; print('SDK disponible')"
```

### 8. Probar detección de cámaras
```bash
python -c "from pyorbbecsdk import *; ctx = Context(); devices = ctx.query_devices(); print(f'Cámaras detectadas: {devices.get_count()}')"
```

## 🚨 Problemas Comunes y Soluciones

### Error: "DLL load failed while importing pyorbbecsdk"

**Causa**: Las DLLs del SDK no están en el directorio correcto.

**Solución**:
```bash
cd backend/sdk/pyorbbecsdk
copy lib\win_x64\*.dll .
copy lib\win_x64\extensions\**\*.dll . -Recurse -Force
```

### Error: "Directory 'install/lib' is empty or does not exist"

**Causa**: El SDK no se compiló correctamente.

**Solución**:
```bash
cd backend/sdk/pyorbbecsdk
rmdir build /s /q  # Limpiar build anterior
mkdir build
cd build
cmake ..
cmake --build . --config Release --verbose
```

### Error: "No se detectaron cámaras Orbbec conectadas"

**Posibles causas y soluciones**:

1. **Cámaras no conectadas**:
   - Verificar conexiones USB
   - Probar diferentes puertos USB

2. **Drivers no instalados**:
   - Instalar Orbbec Viewer desde el sitio oficial
   - Verificar en Administrador de dispositivos

3. **Permisos USB**:
   - Ejecutar como administrador
   - Verificar políticas de seguridad

4. **Conflicto con otras aplicaciones**:
   - Cerrar Orbbec Viewer u otras aplicaciones que usen las cámaras
   - Reiniciar el sistema

### Advertencia: "Receive rtp packet timed out"

**Es normal**: Estos mensajes aparecen durante el funcionamiento normal de las cámaras Orbbec Gemini 335L y no afectan la funcionalidad.

## 📁 Estructura de Archivos Después de la Instalación

```
backend/sdk/pyorbbecsdk/
├── pyorbbecsdk.cp310-win_amd64.pyd    # Módulo compilado
├── OrbbecSDK.dll                      # DLL principal
├── *.dll                              # DLLs adicionales
├── extensions/                        # Extensiones del SDK
├── build/                            # Archivos de compilación
├── lib/                              # Bibliotecas originales
└── sdk/                              # SDK original
```

## 🔍 Verificación de la Instalación Correcta

### Test 1: Importación del SDK
```bash
cd backend/examples
python -c "from pyorbbecsdk import *; print('✅ SDK importado correctamente')"
```

**Salida esperada**:
```
load extensions from C:\...\backend\sdk\pyorbbecsdk/extensions
✅ SDK importado correctamente
```

### Test 2: Detección de cámaras
```bash
python -c "from pyorbbecsdk import *; ctx = Context(); devices = ctx.query_devices(); print(f'🔍 Cámaras detectadas: {devices.get_count()}')"
```

**Salida esperada** (con 3 cámaras):
```
load extensions from C:\...\backend\sdk\pyorbbecsdk/extensions
🔍 Cámaras detectadas: 3
```

### Test 3: Información de cámaras
```bash
python -c "
from pyorbbecsdk import *
ctx = Context()
devices = ctx.query_devices()
for i in range(devices.get_count()):
    device = devices.get_device_by_index(i)
    info = device.get_device_info()
    print(f'📷 Cámara {i}: {info.get_name()} - S/N: {info.get_serial_number()}')
"
```

**Salida esperada**:
```
load extensions from C:\...\backend\sdk\pyorbbecsdk/extensions
📷 Cámara 0: Orbbec Gemini 335Le - S/N: CPE745P0002V
📷 Cámara 1: Orbbec Gemini 335Le - S/N: CPE745P0002B
📷 Cámara 2: Orbbec Gemini 335Le - S/N: CPE345P0007S
```

## 🛠️ Comandos de Mantenimiento

### Limpiar y recompilar el SDK
```bash
cd backend/sdk/pyorbbecsdk
rmdir build /s /q
mkdir build
cd build
cmake ..
cmake --build . --config Release
cd ..
copy build\Release\*.pyd .
```

### Verificar estado de cámaras
```bash
cd backend/examples
python test_multicamera.py
```

### Limpiar archivos temporales
```bash
# Limpiar chunks de video generados
rmdir backend\examples\output /s /q

# Limpiar archivos de compilación
rmdir backend\sdk\pyorbbecsdk\build /s /q
```

## 📋 Lista de Verificación Post-Instalación

- [ ] Python 3.8+ instalado
- [ ] CMake disponible (`cmake --version`)
- [ ] Visual Studio Build Tools instalados
- [ ] Repositorio PyOrbbecSDK clonado en `backend/sdk/pyorbbecsdk/`
- [ ] Dependencias instaladas (`pip install -r requirements.txt`)
- [ ] SDK compilado exitosamente con CMake
- [ ] Archivo `.pyd` copiado al directorio raíz del SDK
- [ ] DLLs copiadas al directorio raíz del SDK
- [ ] SDK se importa sin errores
- [ ] Cámaras detectadas correctamente
- [ ] Script de prueba ejecuta sin errores

## 🔄 Proceso de Actualización del SDK

Si necesitas actualizar a una versión más reciente del SDK:

```bash
cd backend/sdk/pyorbbecsdk
git pull origin main
pip install -r requirements.txt
rmdir build /s /q
mkdir build
cd build
cmake ..
cmake --build . --config Release
cd ..
copy build\Release\*.pyd .
copy lib\win_x64\* . -Recurse -Force
```

## 📞 Soporte y Diagnóstico

Si encuentras problemas, ejecuta este script de diagnóstico:

```python
import sys
import os

print("=== DIAGNÓSTICO DEL SISTEMA ===")
print(f"Python: {sys.version}")
print(f"Directorio actual: {os.getcwd()}")

try:
    import cv2
    print(f"✅ OpenCV: {cv2.__version__}")
except ImportError:
    print("❌ OpenCV no instalado")

try:
    import numpy as np
    print(f"✅ NumPy: {np.__version__}")
except ImportError:
    print("❌ NumPy no instalado")

try:
    sys.path.insert(0, "../sdk/pyorbbecsdk")
    from pyorbbecsdk import *
    print("✅ PyOrbbecSDK importado")
    
    ctx = Context()
    devices = ctx.query_devices()
    print(f"✅ Cámaras detectadas: {devices.get_count()}")
except Exception as e:
    print(f"❌ Error con PyOrbbecSDK: {e}")
```

---

**Nota importante**: Estos pasos deben ejecutarse **cada vez** que se clone el repositorio en un nuevo sistema. El SDK no se incluye pre-compilado para mantener el repositorio ligero y asegurar compatibilidad con diferentes sistemas.
