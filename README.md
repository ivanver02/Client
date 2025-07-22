# Sistema de Cámaras Orbbec

Sistema de captura multi-cámara para cámaras Orbbec Gemini 335L que genera chunks de video de 5 segundos y los envía a un servidor de procesamiento.

## Características

- 🎬 Captura simultánea de 3-5 cámaras Orbbec Gemini 335L
- 📹 Chunks de video de 5 segundos en formato MP4
- 🌐 API REST para control remoto
- 📤 Envío automático a servidor de procesamiento  
- 🔧 Modo simulación para desarrollo sin hardware
- 🧵 Grabación multi-hilo con sincronización por software
- 🎯 Sistema modular y extensible

## Estructura del Proyecto

```
├── main.py                     # Punto de entrada principal
├── requirements.txt            # Dependencias Python
├── backend/            
│   ├── api/                   # API REST con Flask
│   │   └── app.py            # Endpoints de control
│   ├── camera_manager/        # Gestión de cámaras
│   │   └── camera_manager.py # Core de cámaras
│   ├── video_processor/       # Procesamiento de video
│   │   └── video_processor.py# Chunks y encoding
│   ├── config/               # Configuración del sistema
│   │   └── settings.py       # Settings centralizados
│   ├── examples/             # Scripts de prueba
│   │   ├── test_multicamera.py # Test independiente
│   │   └── output/           # Videos generados
│   │       ├── camera0/      # Chunks cámara 0
│   │       ├── camera1/      # Chunks cámara 1
│   │       └── camera2/      # Chunks cámara 2
│   └── sdk/                  # SDK de Orbbec
│       └── pyorbbecsdk/      # Repositorio clonado
├── docs/                     # Documentación
└── README.md
```

## Instalación Rápida

### Opción 1: Instalación Automática (Recomendada) 
```bash
# Ejecutar el script de instalación
instalar.bat
```
Este script hace **toda la configuración necesaria** automáticamente.

### Opción 2: Instalación Manual
```bash
git clone <este-repositorio>
cd <directorio-del-proyecto>
pip install -r requirements.txt
```

⚠️ **IMPORTANTE**: El SDK requiere configuración manual. Ver documentación completa:

👉 **[Guía completa de instalación del SDK](docs/INSTALACION_SDK.md)**

**Resumen rápido**:
```bash
cd backend/sdk
git clone https://github.com/orbbec/pyorbbecsdk.git
cd pyorbbecsdk
pip install -r requirements.txt
mkdir build && cd build
cmake .. && cmake --build . --config Release
cd ..
copy build\Release\*.pyd .
copy lib\win_x64\* . -Recurse -Force
```

### Verificación de la instalación
```bash
# Verificar que todo funciona correctamente
verificar.bat
```

### Probar el sistema
```bash
# Prueba independiente (recomendado primero)
cd backend/examples
python test_multicamera.py

# Sistema completo
python main.py
```

## Script de Prueba Independiente

El script `backend/examples/test_multicamera.py` permite probar el sistema con cámaras reales:

- ✅ **SOLO cámaras físicas Orbbec Gemini 335L** (sin simulación)
- 📹 Detecta y graba las 3 cámaras conectadas simultáneamente
- 💾 Guarda chunks como 0.mp4, 1.mp4, 2.mp4... en cada directorio de cámara
- 👀 Muestra preview de la primera cámara con OpenCV
- ⌨️ Presiona 'q' para finalizar
- 📊 Muestra estadísticas de frames por chunk

### Cámaras detectadas automáticamente:
- **Cámara 0**: Orbbec Gemini 335Le - S/N: CPE745P0002V
- **Cámara 1**: Orbbec Gemini 335Le - S/N: CPE745P0002B  
- **Cámara 2**: Orbbec Gemini 335Le - S/N: CPE345P0007S

```bash
pip install -r requirements.txt
```

### 4. Instalar PyOrbbecSDK

Seguir las instrucciones en `docs/INSTALACION_PYORBBECSDK.txt` para instalar el SDK de Orbbec.

Alternativamente, copiar el SDK compilado al directorio `backend/sdk/`.

## 🎮 Uso

### Iniciar el sistema

```bash
python main.py
```

El servidor estará disponible en: `http://127.0.0.1:5000`

### API Endpoints

#### Gestión de Cámaras

- `GET /api/cameras/discover` - Descubrir cámaras conectadas
- `POST /api/cameras/initialize` - Inicializar cámaras para grabación
- `GET /api/cameras/status` - Estado actual de las cámaras

#### Control de Grabación

- `POST /api/recording/start` - Iniciar grabación
  ```json
  {
    "patient_id": "paciente_001"
  }
  ```

- `POST /api/recording/stop` - Finalizar grabación
- `POST /api/recording/cancel` - Cancelar grabación y limpiar archivos
- `GET /api/recording/status` - Estado de la grabación

#### Sistema

- `GET /api/system/health` - Estado general del sistema
- `POST /api/system/cleanup` - Limpiar recursos

### Flujo de trabajo típico

1. **Descubrir cámaras**: `GET /api/cameras/discover`
2. **Inicializar cámaras**: `POST /api/cameras/initialize`
3. **Iniciar grabación**: `POST /api/recording/start`
4. **Finalizar o cancelar**: `POST /api/recording/stop` o `POST /api/recording/cancel`

## ⚙️ Configuración

### Servidor de procesamiento

Editar `backend/config/settings.py`:

```python
class ServerConfig:
    base_url: str = "http://your-server:8000"
    upload_endpoint: str = "/api/upload-chunk"
    # ... otros endpoints
```

### Configuración de cámaras

```python
class CameraConfig:
    resolution_width: int = 640
    resolution_height: int = 480
    fps: int = 30
```

### Configuración de chunks

```python
class RecordingConfig:
    chunk_duration_seconds: int = 5
    output_format: str = "mp4"
    video_codec: str = "mp4v"
```

## 🔧 Desarrollo

### Modo simulación

Si no hay cámaras físicas conectadas, el sistema automáticamente usa cámaras simuladas para desarrollo.

### Estructura de chunks

Cada chunk incluye:
- `chunk_id`: UUID único
- `camera_id`: Identificador de cámara (0, 1, 2...)
- `session_id`: ID de la sesión de grabación
- `patient_id`: ID del paciente
- `sequence_number`: Número de secuencia del chunk
- `timestamp`: Timestamp de creación
- `duration_seconds`: Duración real del chunk
- `file_size_bytes`: Tamaño del archivo

### Logs

Los logs se guardan automáticamente en el directorio `logs/`.

## 🔍 Troubleshooting

### Cámaras no detectadas

1. Verificar que las cámaras estén conectadas
2. Comprobar instalación del PyOrbbecSDK
3. Revisar permisos de USB

### Error de importación del SDK

```bash
# Verificar instalación
python -c "from pyorbbecsdk import *; print('SDK OK')"
```

### Problemas de red

Verificar conectividad con el servidor de procesamiento:

```bash
curl http://your-server:8000/api/health
```

## 📋 Requisitos

### Hardware

- **Cámaras**: 3-5 × Orbbec Gemini 335L
- **PC**: Windows 10 x64, 8GB RAM mínimo
- **USB**: Puertos USB 3.0 para cada cámara
- **Red**: Conexión estable al servidor de procesamiento

### Software

- Python 3.10+
- PyOrbbecSDK v2.x
- OpenCV 4.8+
- Flask 2.3+

## 🚧 Estado del Proyecto

- ✅ Backend API completo
- ✅ Sistema de captura multi-cámara
- ✅ Procesamiento de chunks automático
- ✅ Envío al servidor de procesamiento
- 🔄 Frontend web (en desarrollo)
- 🔄 Sincronización por hardware (futuro)

## 📞 Soporte y Troubleshooting

### ❌ Problemas Comunes

#### Error: "DLL load failed while importing pyorbbecsdk"
**Solución**: Las DLLs no están copiadas correctamente.
```bash
cd backend/sdk/pyorbbecsdk
copy lib\win_x64\*.dll .
copy lib\win_x64\extensions\**\*.dll . -Recurse -Force
```

#### Error: "No se detectaron cámaras Orbbec conectadas"
**Verificar**:
- Cámaras conectadas por USB 3.0
- Drivers instalados (instalar Orbbec Viewer)
- Cerrar otras aplicaciones que usen las cámaras
- Ejecutar como administrador

#### "Receive rtp packet timed out"
**Es normal**: Estos mensajes no afectan la funcionalidad de las cámaras Orbbec Gemini 335L.

### 📚 Documentación Detallada

👉 **[Guía completa de instalación del SDK](docs/INSTALACION_SDK.md)**

### 🔍 Diagnóstico

Para problemas técnicos, consultar:
1. Logs en `logs/`
2. Estado del sistema: `GET /api/system/health`
3. Ejecutar script de diagnóstico en `docs/INSTALACION_SDK.md`
