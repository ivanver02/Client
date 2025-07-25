"""
Configuración principal del sistema de cámaras Orbbec
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class CameraConfig:
    """Configuración para una cámara individual"""
    camera_id: int
    resolution_width: int = 640
    resolution_height: int = 480
    fps: int = 30
    format: str = "RGB"


@dataclass
class RecordingConfig:
    """Configuración para grabación"""
    chunk_duration_seconds: int = 5
    output_format: str = "mp4"
    video_codec: str = "mp4v"
    quality: int = 90  # 0-100


@dataclass
class ServerConfig:
    """Configuración del servidor remoto"""
    base_url: str = "http://localhost:8000"
    upload_endpoint: str = "/api/chunks/receive"
    session_start_endpoint: str = "/api/session/start"
    session_end_endpoint: str = "/api/session/end" 
    session_cancel_endpoint: str = "/api/session/cancel"


class SystemConfig:
    """Configuración principal del sistema"""
    
    # Cámaras
    MAX_CAMERAS = 5
    DEFAULT_CAMERA_CONFIG = CameraConfig(camera_id=0)
    
    # Grabación
    RECORDING = RecordingConfig()
    
    # Servidor
    SERVER = ServerConfig()
    
    # Rutas
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    TEMP_VIDEO_DIR = os.path.join(BASE_DIR, "temp_videos")
    LOGS_DIR = os.path.join(BASE_DIR, "logs")
    
    # API Local
    LOCAL_API_HOST = "127.0.0.1"
    LOCAL_API_PORT = 5000
    
    @classmethod
    def ensure_directories(cls):
        """Crear directorios necesarios si no existen"""
        os.makedirs(cls.TEMP_VIDEO_DIR, exist_ok=True)
        os.makedirs(cls.LOGS_DIR, exist_ok=True)
