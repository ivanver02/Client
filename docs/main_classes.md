# Documentación de Clases Principales

Este documento describe las clases principales del sistema de gestión y procesamiento de video multi-cámara, detallando su propósito y los métodos más relevantes.

---

## 1. `camera_manager.py`: Abstracción del SDK de cámaras

El módulo `camera_manager.py` se encarga de abstraer el SDK específico de las cámaras Orbbec. Si se emplean cámaras de otra marca, se debe implementar un gestor específico para estas. Permite la detección, inicialización y control de múltiples cámaras de forma sincronizada.

### Clases principales

#### `CameraInfo`
Información de una cámara detectada.
- **Atributos:**
  - `camera_id: int`
  - `serial_number: str`
  - `is_connected: bool`
  - `last_frame_time: Optional[datetime]`

#### `OrbbecCamera`
Controlador para una cámara Orbbec.
- **Métodos:**
  - `__init__(device, camera_id, config)`
  - `initialize() -> bool`: Inicializa la cámara y configura el pipeline.
  - `start_recording() -> bool`: Marca el estado de grabación.
  - `stop_recording() -> bool`: Finaliza la grabación.
  - `get_frame() -> Optional[np.ndarray]`: Obtiene el último frame capturado.

---

## 2. `video_processor.py`: Lógica de procesamiento de chunks

El módulo `video_processor.py` gestiona la lógica de grabación, segmentación y procesamiento de los videos capturados por las cámaras. Permite dividir los videos en chunks y preparar los datos para su envío y análisis.

### Clases principales

#### `VideoWriter`
Manejador de escritura de video para una cámara.
- **Métodos:**
  - `__init__(camera_id, output_path)`
  - `initialize(frame_width, frame_height, fps) -> bool`: Inicializa el writer de video.
  - `write_frame(frame) -> bool`: Escribe un frame al video.
  - `finalize() -> Optional[VideoChunk]`: Finaliza el video y retorna información del chunk.

#### `VideoProcessor`
Gestor principal de la lógica de procesamiento de video y chunks.
- **Métodos:**
  - `__init__(self, cameras: List[OrbbecCamera], config: SystemConfig)`: Inicializa el procesador con las cámaras y configuración.
  - `start_recording(self, session_id: str, patient_id: str) -> bool`: Inicia la grabación sincronizada en todas las cámaras.
  - `stop_recording(self) -> List[VideoChunk]`: Finaliza la grabación y procesa los videos en chunks.
  - `cancel_recording(self) -> None`: Cancela la grabación y elimina los datos temporales.

---

## 3. `app.py`: Gestión de endpoints y lógica de sesión

El módulo `app.py` implementa la aplicación Flask que expone los endpoints para el control del sistema, la gestión de sesiones y la interacción con el frontend.

### Funciones principales

- `create_app() -> Flask`: Inicializa la aplicación y configura rutas.
- `upload_chunk_to_server(chunk: VideoChunk)`: Envía un chunk de video al servidor de análisis.

---

## 4. `settings.py`: Configuración global del sistema

El módulo `settings.py` centraliza la configuración del sistema, incluyendo parámetros de cámaras, grabación, rutas y endpoints.

### Clases principales

#### `CameraConfig`
Configuración para una cámara individual.
- **Atributos:**
  - `camera_id: int`
  - `resolution_width: int`
  - `resolution_height: int`
  - `fps: int`
  - `format: str`

#### `RecordingConfig`
Configuración para la grabación.
- **Atributos:**
  - `chunk_duration_seconds: int`
  - `output_format: str`

#### `ServerConfig`
Configuración del servidor remoto.
- **Atributos:**
  - `base_url: str`
  - `upload_endpoint: str`
  - `session_start_endpoint: str`
  - `session_end_endpoint: str`
  - `session_cancel_endpoint: str`

#### `SystemConfig`
Configuración principal del sistema.
- **Atributos y métodos:**
  - `MAX_CAMERAS: int`
  - `DEFAULT_CAMERA_CONFIG: CameraConfig`
  - `RECORDING: RecordingConfig`
  - `SERVER: ServerConfig`
  - `BASE_DIR: str`
  - `TEMP_VIDEO_DIR: str`
  - `LOGS_DIR: str`
  - `LOCAL_API_HOST: str`
  - `LOCAL_API_PORT: int`
  - `ensure_directories()`: Crea los directorios necesarios.

---

## Referencias

Para más detalles sobre la implementación y los métodos disponibles, consulta el código fuente de cada módulo.
