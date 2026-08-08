# Multi-Camera Medical Frontend for Gait Analysis

This project is a hardware integrated acquisition platform for markerless gait analysis, developed in collaboration between the **University of Malaga** and **Costa del Sol Hospital**. It combines an Orbbec multi-camera setup, a Python acquisition backend, video chunking, session management, and a web interface designed for use in clinical and research environments.

The frontend was built to solve the part of the computer-vision pipeline that happens before model inference: discovering and controlling the cameras, acquiring video reliably, organizing patient sessions, and transmitting the resulting data to the analysis server. This makes it the interface between the physical capture system and the downstream 2D pose-estimation and 3D reconstruction pipeline.

The project works together with the `markerless-gait-analysis-backend` repository:

- **markerless-gait-analysis-frontend**: discovers and controls the cameras, records synchronized multi-camera video, manages sessions, and sends video chunks.
- **markerless-gait-analysis-backend**: detects 2D keypoints, combines pose-estimation models, reconstructs the pose in 3D, and performs biomechanical analysis.

Both repositories form the complete workflow for multi-camera gait analysis.

## System Overview

The client manages Orbbec Gemini 335Le cameras and provides a browser-based interface for the operator. It supports:

- camera discovery and initialization;
- synchronized recording across multiple cameras;
- configuration of recording resolution, frame rate, and format;
- patient and session identification;
- segmentation of recordings into processable video chunks;
- transmission of chunks to the analysis server;
- real-time session and camera-status monitoring;
- cancellation and cleanup of temporary recording data.

The architecture separates hardware-specific camera control from video processing and HTTP API logic. This allows the Orbbec implementation to be replaced by a different camera manager if another acquisition device is used.

## Repository Structure

```text
Client/
├── main.py
├── instalar.bat
├── requirements.txt
├── backend/
│   ├── api/
│   │   ├── app.py
│   │   └── __init__.py
│   ├── camera_manager/
│   │   ├── camera_manager.py
│   │   └── __init__.py
│   ├── config/
│   │   └── settings.py
│   ├── sdk/
│   │   └── pyorbbecsdk/
│   ├── tests/
│   │   └── grabacion_simple.py
│   ├── video_processor/
│   │   ├── video_processor.py
│   │   └── __init__.py
│   └── __init__.py
├── docs/
│   ├── INSTALACION_SDK.md
│   └── main_classes.md
├── frontend/
│   ├── index.html
│   ├── script.js
│   └── style.css
├── .github/
│   └── copilot-instructions.md
├── .gitignore
├── .gitmodules
└── LICENSE.md
```

## Acquisition Pipeline

### 1. Camera discovery and initialization

The camera manager discovers the connected Orbbec devices, initializes them, and applies the recording configuration. Camera-specific operations are isolated in `backend/camera_manager/camera_manager.py` so that the rest of the application is independent of the device SDK.

### 2. Session creation and recording

The operator starts a session from the web interface by providing a patient identifier and session identifier. The video processor starts acquisition across the available cameras and stores the recordings in temporary chunks.

### 3. Chunk processing and transmission

The recording is divided into chunks that can be processed incrementally. When the recording ends, the client prepares the chunks, sends them to the analysis server, and removes temporary data when appropriate.

### 4. Operator interaction

The web interface exposes the current state of the system and the connected cameras. The operator can start or cancel a session, while the backend coordinates the corresponding hardware, storage, and server requests.

## API Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/system/health` | Check system health and camera availability. |
| `GET` | `/api/cameras/discover` | Discover connected cameras. |
| `POST` | `/api/cameras/initialize` | Initialize the cameras for a session. |
| `POST` | `/api/recording/start` | Start recording across all cameras. |
| `POST` | `/api/recording/stop` | Stop recording and process the captured videos. |
| `POST` | `/api/recording/cancel` | Cancel recording and remove temporary data. |
| `GET` | `/api/session/status` | Query the current session status. |
| `GET` | `/api/chunks/list` | List the recorded video chunks. |

## Main Components

Detailed documentation of the main classes and methods is available in [`docs/main_classes.md`](docs/main_classes.md).

- [`camera_manager.py`](backend/camera_manager/camera_manager.py): abstracts the Orbbec SDK and manages camera discovery, initialization, and multi-camera control. A different camera brand can be supported by implementing another manager with the same role.
- [`video_processor.py`](backend/video_processor/video_processor.py): manages recording, video segmentation, temporary storage, and preparation of chunks for transmission and analysis.
- [`app.py`](backend/api/app.py): implements the Flask application and exposes the endpoints for camera control, session management, recording, and communication with the analysis server.
- [`settings.py`](backend/config/settings.py): centralizes camera parameters, recording options, paths, server endpoints, and other runtime configuration.

## Running the frontend

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

If required, install the Orbbec SDK using the provided script:

```bash
instalar.bat
```

Configure the analysis server address and port in [`backend/config/settings.py`](backend/config/settings.py). The default configuration points to `192.168.159.101:11299`, but it must be adjusted to match the deployment environment.

Start the client backend:

```bash
python main.py
```

Then open [`frontend/index.html`](frontend/index.html) in a browser, or access `http://localhost:5000` if the backend is configured to serve the frontend.

## Configuration and Dependencies

- Runtime configuration is centralized in [`backend/config/`](backend/config/).
- [`backend/config/settings.py`](backend/config/settings.py) contains camera, recording, storage, and server-connection settings.
- The Orbbec SDK must be installed and correctly configured. See [`docs/INSTALACION_SDK.md`](docs/INSTALACION_SDK.md) for detailed instructions.
- [`instalar.bat`](instalar.bat) automates the installation and verification of the SDK and project dependencies.
- [`backend/sdk/pyorbbecsdk`](backend/sdk/pyorbbecsdk) must contain the SDK cloned from the official Orbbec repository. A project-adapted fork may be required if the upstream SDK is not compatible with the application.

The system currently targets Orbbec Gemini 335Le cameras, but the camera-management abstraction allows the acquisition layer to be adapted to other devices.

## Development and Testing

The [`backend/tests/`](backend/tests/) directory contains manual test scripts and prototypes, including [`grabacion_simple.py`](backend/tests/grabacion_simple.py). Camera discovery and recording should be tested before using the system in a clinical session.

## Research and Clinical Context

Reliable data acquisition is essential in a multi-view computer-vision system. A missing camera, inconsistent recording configuration, or poorly organized session can affect every subsequent stage, from 2D keypoint detection to 3D reconstruction. This client therefore treats acquisition, synchronization, session provenance, and operator feedback as first-class parts of the research pipeline.

The system is intended for research and clinical evaluation support. Its outputs should be interpreted by qualified professionals and are not, by themselves, a medical diagnosis.

## License

This project is licensed under the Apache License 2.0. See [`LICENSE.md`](LICENSE.md) for the complete terms.

Developed by the **University of Malaga** and **Costa del Sol Hospital**.
