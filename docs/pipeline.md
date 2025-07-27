# Pipeline de Ejecución - Proyecto Code

## 📋 Descripción General

Este documento describe el flujo completo de ejecución del sistema de captura multi-cámara, desde que el usuario presiona "Comenzar Grabación" hasta que los chunks de video son enviados al servidor de procesamiento.

## 🔄 Flujo Principal de Ejecución

### **FASE 1: INICIALIZACIÓN DEL SISTEMA**

#### 1.1. `DOMContentLoaded Event` 
**Archivo:** `frontend/script.js:1`
**Descripción:** Evento que se ejecuta cuando el DOM está completamente cargado, inicializa toda la aplicación frontend.

#### 1.2. `initializeSystem()`
**Archivo:** `frontend/script.js:66`
**Descripción:** Función principal que verifica el estado del backend, descubre cámaras disponibles y las inicializa automáticamente.

#### 1.3. `fetch(API.health)`
**Archivo:** `frontend/script.js:73` → `backend/api/app.py:130`
**Descripción:** Verificación de que el backend está disponible y funcionando correctamente.

#### 1.4. `fetch(API.discoverCameras)`
**Archivo:** `frontend/script.js:80` → `backend/api/app.py:75`
**Descripción:** Descubre todas las cámaras Orbbec conectadas al sistema.

##### 1.4.1. `camera_manager.discover_cameras()`
**Archivo:** `backend/camera_manager/camera_manager.py:318`
**Descripción:** Detecta físicamente las cámaras Orbbec usando el SDK y devuelve información básica.

#### 1.5. `fetch(API.initializeCameras)`
**Archivo:** `frontend/script.js:95` → `backend/api/app.py:95`
**Descripción:** Inicializa automáticamente todas las cámaras encontradas para prepararlas para grabación.

##### 1.5.1. `camera_manager.initialize_camera()`
**Archivo:** `backend/camera_manager/camera_manager.py:140`
**Descripción:** Configura cada cámara individual con la resolución y FPS especificados.

##### 1.5.2. `OrbbecCamera.__init__()`
**Archivo:** `backend/camera_manager/camera_manager.py:32`
**Descripción:** Constructor de la clase que representa una cámara Orbbec específica.

##### 1.5.3. `OrbbecCamera.initialize()`
**Archivo:** `backend/camera_manager/camera_manager.py:45`
**Descripción:** Establece conexión física con la cámara y configura el pipeline de captura.

#### 1.6. `updateCameraStatus()`
**Archivo:** `frontend/script.js:126`
**Descripción:** Actualiza la interfaz de usuario con el número de cámaras detectadas.

---

### **FASE 2: INICIO DE GRABACIÓN**

#### 2.1. `startBtn.addEventListener('click')`
**Archivo:** `frontend/script.js:319`
**Descripción:** Event listener que detecta cuando el usuario presiona el botón "Comenzar Grabación".

#### 2.2. `handleStartRecording()`
**Archivo:** `frontend/script.js:142`
**Descripción:** Función principal que gestiona todo el proceso de inicio de grabación.

#### 2.3. Pre-verificación de cámaras
**Archivo:** `frontend/script.js:157-185`
**Descripción:** Se asegura de que las cámaras estén descubiertas e inicializadas antes de comenzar.

##### 2.3.1. `fetch(API.discoverCameras)` (Re-verificación)
**Archivo:** `frontend/script.js:160`
**Descripción:** Segunda verificación para asegurar que las cámaras siguen disponibles.

##### 2.3.2. `fetch(API.initializeCameras)` (Re-inicialización)
**Archivo:** `frontend/script.js:168`
**Descripción:** Re-inicialización de las cámaras para asegurar estado correcto.

#### 2.4. `fetch(API.startRecording)`
**Archivo:** `frontend/script.js:187` → `backend/api/app.py:187`
**Descripción:** Solicitud POST para iniciar la grabación con el ID del paciente.

##### 2.4.1. `video_processor.start_session()`
**Archivo:** `backend/video_processor/video_processor.py:71`
**Descripción:** Crea una nueva sesión de grabación con ID único y directorio de trabajo.

##### 2.4.2. `video_processor.start_recording()`
**Archivo:** `backend/video_processor/video_processor.py:148`
**Descripción:** Inicia el proceso de grabación por chunks con hilos de ejecución.

##### 2.4.3. `camera_manager.start_recording_all()`
**Archivo:** `backend/camera_manager/camera_manager.py:287`
**Descripción:** Activa el modo grabación en todas las cámaras inicializadas.

##### 2.4.4. `OrbbecCamera.start_recording()`
**Archivo:** `backend/camera_manager/camera_manager.py:83`
**Descripción:** Marca cada cámara individual como en modo grabación.

##### 2.4.5. `threading.Thread(target=_recording_loop)`
**Archivo:** `backend/video_processor/video_processor.py:162`
**Descripción:** Inicia hilo de grabación por chunks en background.

#### 2.5. `toggleRecordingControls(true)`
**Archivo:** `frontend/script.js:218`
**Descripción:** Cambia la interfaz para mostrar controles de grabación activa.

---

### **FASE 3: PROCESO DE GRABACIÓN POR CHUNKS**

#### 3.1. `_recording_loop()`
**Archivo:** `backend/video_processor/video_processor.py:164`
**Descripción:** Bucle principal que gestiona la grabación automática en chunks de 5 segundos.

##### 3.1.1. `_create_chunk_recorders()`
**Archivo:** `backend/video_processor/video_processor.py:246`
**Descripción:** Crea grabadores individuales para cada cámara con archivos MP4 únicos.

##### 3.1.2. `ChunkRecorder.__init__()`
**Archivo:** `backend/video_processor/video_processor.py:24`
**Descripción:** Inicializa grabador de chunk individual con configuración de video.

##### 3.1.3. `ChunkRecorder.start_recording()`
**Archivo:** `backend/video_processor/video_processor.py:43`
**Descripción:** Inicia grabación de chunk específico con VideoWriter de OpenCV.

##### 3.1.4. `ChunkRecorder.record_frames()`
**Archivo:** `backend/video_processor/video_processor.py:51`
**Descripción:** Captura y escribe frames por 5 segundos exactos.

##### 3.1.5. `OrbbecCamera.get_frame()`
**Archivo:** `backend/camera_manager/camera_manager.py:98`
**Descripción:** Obtiene frame individual de la cámara Orbbec física.

##### 3.1.6. `ChunkRecorder.stop_recording()`
**Archivo:** `backend/video_processor/video_processor.py:58`
**Descripción:** Finaliza grabación de chunk y libera recursos de video.

#### 3.2. `_create_video_chunk()`
**Archivo:** `backend/video_processor/video_processor.py:193`
**Descripción:** Crea objeto VideoChunk con metadatos completos del archivo grabado.

#### 3.3. `upload_chunk_to_server()` (Callback)
**Archivo:** `backend/api/app.py:32`
**Descripción:** Callback automático que envía cada chunk al servidor de procesamiento.

##### 3.3.1. `requests.post()` → Server `/api/chunks/receive`
**Archivo:** `backend/api/app.py:43`
**Descripción:** Envío HTTP del archivo chunk con metadatos al servidor de procesamiento.

##### 3.3.2. `os.remove(chunk.file_path)`
**Archivo:** `backend/api/app.py:59`
**Descripción:** Eliminación del archivo local después del envío exitoso.

---

### **FASE 4: FINALIZACIÓN DE GRABACIÓN**

#### 4.1. `handleProcessRecording()` (Usuario presiona "Finalizar y Procesar")
**Archivo:** `frontend/script.js:236`
**Descripción:** Función que maneja la finalización de la grabación por parte del usuario.

#### 4.2. `fetch(API.stopRecording)`
**Archivo:** `frontend/script.js:242` → `backend/api/app.py:215`
**Descripción:** Solicitud POST para detener la grabación y finalizar la sesión.

##### 4.2.1. `video_processor.stop_recording()`
**Archivo:** `backend/video_processor/video_processor.py:175`
**Descripción:** Detiene el bucle de grabación y finaliza chunks pendientes.

##### 4.2.2. `camera_manager.stop_recording_all()`
**Archivo:** `backend/camera_manager/camera_manager.py:300`
**Descripción:** Desactiva modo grabación en todas las cámaras.

##### 4.2.3. `OrbbecCamera.stop_recording()`
**Archivo:** `backend/camera_manager/camera_manager.py:89`
**Descripción:** Desactiva modo grabación en cada cámara individual.

##### 4.2.4. `video_processor.end_session()`
**Archivo:** `backend/video_processor/video_processor.py:104`
**Descripción:** Finaliza la sesión y envía notificación al servidor.

##### 4.2.5. `requests.post()` → Server `/api/session/end`
**Archivo:** `backend/video_processor/video_processor.py:118`
**Descripción:** Notifica al servidor que la sesión ha finalizado para procesar keypoints.

#### 4.3. `toggleRecordingControls(false)`
**Archivo:** `frontend/script.js:261`
**Descripción:** Restaura la interfaz al estado inicial.

---

### **FASE 5: CANCELACIÓN (Alternativa)**

#### 5.1. `handleCancelRecording()` (Usuario presiona "Cancelar")
**Archivo:** `frontend/script.js:280`
**Descripción:** Función que maneja la cancelación de la grabación.

#### 5.2. `fetch(API.cancelRecording)`
**Archivo:** `frontend/script.js:286` → `backend/api/app.py:252`
**Descripción:** Solicitud POST para cancelar la grabación.

##### 5.2.1. `video_processor.cancel_session()`
**Archivo:** `backend/video_processor/video_processor.py:124`
**Descripción:** Cancela la sesión y limpia archivos temporales.

##### 5.2.2. `requests.post()` → Server `/api/session/cancel`
**Archivo:** `backend/video_processor/video_processor.py:136`
**Descripción:** Notifica al servidor que la sesión ha sido cancelada.

---

## 📊 Resumen del Flujo

```
Usuario presiona "Comenzar Grabación"
         ↓
handleStartRecording() verifica cámaras
         ↓
Solicitud POST a /api/recording/start
         ↓
video_processor inicia sesión y grabación
         ↓
Bucle automático graba chunks de 5s
         ↓
Cada chunk se envía automáticamente al Server
         ↓
Usuario presiona "Finalizar y Procesar"
         ↓
handleProcessRecording() detiene grabación
         ↓
Solicitud POST a /api/recording/stop
         ↓
video_processor finaliza sesión
         ↓
Notificación al Server de sesión finalizada
```

## ⚡ Características Clave

- **Grabación Automática por Chunks:** 5 segundos por chunk
- **Multi-Cámara Sincronizada:** Todas las cámaras graban simultáneamente
- **Envío Automático:** Chunks se envían al servidor inmediatamente
- **Limpieza Automática:** Archivos locales se eliminan tras envío exitoso
- **Verificación Previa:** Se verifica estado de cámaras antes de cada operación
- **Gestión de Sesiones:** Cada grabación tiene ID único de sesión
- **Manejo de Errores:** Captura y manejo de errores en cada fase
