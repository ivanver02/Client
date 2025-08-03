# Sistema de Cámaras Orbbec para Análisis de Marcha

Este proyecto es el backend y frontend para la gestión, grabación y procesamiento de video multi-cámara, desarrollado por la Universidad de Málaga y el Hospital Costa del Sol. El sistema permite la captura sincronizada de video, gestión de sesiones y control de cámaras Orbbec, así como la interacción con el usuario a través de una interfaz web.

Este proyecto (Code) está diseñado para funcionar conjuntamente con el repositorio [Server](../Server/README.md), que se encarga del procesamiento avanzado de los videos, detección de keypoints y reconstrucción 3D. Code gestiona la captura, grabación y envío de video multi-cámara. Ambos forman el flujo completo de análisis de marcha, permitiendo una integración clínica e investigadora robusta. Para el funcionamiento completo, consulta y utiliza ambos repositorios.

---
## Descripción del proyecto

El sistema gestiona la detección y control de cámaras Orbbec Gemini 335Le, la grabación de video en sesiones clínicas, el procesamiento y envío de chunks de video al servidor de análisis, y la interacción con el usuario mediante un frontend web. Permite la evaluación multi-cámara y la gestión eficiente de los datos de pacientes y sesiones.

---
## Estructura de archivos del proyecto

```
Code/
├── [main.py](main.py)
├── [instalar.bat](instalar.bat)
├── [requirements.txt](requirements.txt)
├── backend/
│   ├── api/
│   │   ├── [app.py](backend/api/app.py)
│   │   └── [__init__.py](backend/api/__init__.py)
│   ├── camera_manager/
│   │   ├── [camera_manager.py](backend/camera_manager/camera_manager.py)
│   │   └── [__init__.py](backend/camera_manager/__init__.py)
│   ├── config/
│   │   └── [settings.py](backend/config/settings.py)
│   ├── sdk/
│   │   └── pyorbbecsdk/
│   ├── tests/
│   │   └── [grabacion_simple.py](backend/tests/grabacion_simple.py)
│   ├── video_processor/
│   │   ├── [video_processor.py](backend/video_processor/video_processor.py)
│   │   └── [__init__.py](backend/video_processor/__init__.py)
│   └── [__init__.py](backend/__init__.py)
├── docs/
│   ├── [INSTALACION_SDK.md](docs/INSTALACION_SDK.md)
│   └── [main_classes.md](docs/main_classes.md)
├── frontend/
│   ├── [index.html](frontend/index.html)
│   ├── [script.js](frontend/script.js)
│   └── [style.css](frontend/style.css)
└── [.gitignore](.gitignore)
```

---
## Cómo ejecutar el servidor y acceder al frontend

1. Instala las dependencias:
```bash
pip install -r requirements.txt
```
2. Ejecuta el script de instalación para el SDK de Orbbec (si es necesario):
```bash
instalar.bat
```
3. Inicia el backend:
```bash
python main.py
```
4. Accede al frontend abriendo el archivo [`frontend/index.html`](frontend/index.html) en tu navegador o accediendo a `http://localhost:5000` si el backend está configurado para servir el frontend.

---
## API Endpoints

- `GET /api/system/health`: Verifica el estado del sistema y las cámaras.
- `GET /api/cameras/discover`: Descubre las cámaras conectadas.
- `POST /api/cameras/initialize`: Inicializa las cámaras para la sesión.
- `POST /api/recording/start`: Inicia la grabación en todas las cámaras.
- `POST /api/recording/stop`: Finaliza la grabación y procesa los videos.
- `POST /api/recording/cancel`: Cancela la grabación y elimina los datos temporales.
- `GET /api/session/status`: Consulta el estado actual de la sesión.
- `GET /api/chunks/list`: Lista los chunks de video grabados.

---
## Consideraciones importantes

- El SDK de Orbbec debe estar correctamente instalado y configurado. Consulta [`docs/INSTALACION_SDK.md`](docs/INSTALACION_SDK.md) para instrucciones detalladas.
- El script [`instalar.bat`](instalar.bat) automatiza la instalación y verificación del SDK y dependencias.
- El sistema está diseñado para funcionar con cámaras Orbbec Gemini 335Le, pero puede adaptarse a otros modelos implementando un gestor específico en lugar de [`backend/camera_manager/camera_manager.py`](backend/camera_manager/camera_manager.py).
- La carpeta [`backend/sdk/pyorbbecsdk`](backend/sdk/pyorbbecsdk) debe contener el SDK clonado desde el repositorio oficial de Orbbec. Si no funciona, en mi perfil de GitHub encontrarás un fork con el SDK adaptado para este proyecto.

---
## Pipeline completo del proyecto

1. **Descubrimiento y configuración de cámaras:**
   - Se detectan las cámaras conectadas mediante el gestor [`backend/camera_manager/camera_manager.py`](backend/camera_manager/camera_manager.py).
   - Se inicializan las cámaras y se configuran los parámetros de grabación (resolución, fps, formato).
2. **Inicio de sesión y grabación:**
   - El usuario inicia una sesión desde el frontend, proporcionando el ID de paciente y sesión.
   - Se inicia la grabación sincronizada en todas las cámaras mediante el módulo [`backend/video_processor/video_processor.py`](backend/video_processor/video_processor.py).
   - Los videos se dividen en chunks y se almacenan temporalmente.
3. **Finalización y procesamiento:**
   - Al finalizar la grabación, los chunks se procesan y se envían al servidor de análisis.
   - El backend gestiona el envío de los datos y la limpieza de archivos temporales.
4. **Interacción y control desde el frontend:**
   - El usuario puede cancelar la sesión en cualquier momento, lo que elimina los datos grabados.
   - El estado del sistema y las cámaras se muestra en tiempo real en el frontend.

**Clases principales involucradas:**

La descripción detallada de las clases y métodos principales se encuentra en [`docs/main_classes.md`](docs/main_classes.md).

- **[`backend/camera_manager/camera_manager.py`](backend/camera_manager/camera_manager.py)**: Abstrae el SDK específico de las cámaras Orbbec, permitiendo la detección, inicialización y control sincronizado de múltiples cámaras. Si se emplean cámaras de otra marca, se debe implementar un gestor específico para estas.
- **[`backend/video_processor/video_processor.py`](backend/video_processor/video_processor.py)**: Gestiona la lógica de grabación, segmentación y procesamiento de los videos capturados, dividiéndolos en chunks y preparando los datos para su envío y análisis.
- **[`backend/api/app.py`](backend/api/app.py)**: Implementa la aplicación Flask que expone los endpoints para el control del sistema, la gestión de sesiones y la interacción con el frontend.
- **[`backend/config/settings.py`](backend/config/settings.py)**: Centraliza la configuración global del sistema, incluyendo parámetros de cámaras, grabación, rutas y endpoints.

---
## Configuraciones

- Toda la configuración está centralizada en la carpeta [`backend/config/`](backend/config/).
- El archivo principal es [`backend/config/settings.py`](backend/config/settings.py), donde se definen rutas, parámetros de grabación, endpoints y configuración de cámaras.

---
## Testing

- La carpeta [`backend/tests/`](backend/tests/) contiene scripts para pruebas manuales y prototipos, como [`grabacion_simple.py`](backend/tests/grabacion_simple.py).
- Se recomienda probar la detección y grabación de cámaras antes de iniciar sesiones clínicas.

---
## Licencia

Este proyecto está licenciado bajo Apache License 2.0. Consulta el archivo [`LICENSE.md`](LICENSE.md) para más detalles.

---
## Créditos

Desarrollado por la Universidad de Málaga y el Hospital Costa del Sol.
