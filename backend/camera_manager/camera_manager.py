"""
Gestor de cámaras Orbbec para captura multi-cámara sincronizada
"""
import threading
import time
import cv2
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass

# Importación condicional del SDK de Orbbec
try:
    from pyorbbecsdk import *
    ORBBEC_AVAILABLE = True
except ImportError:
    ORBBEC_AVAILABLE = False
    print("⚠️  PyOrbbecSDK no disponible - usando simulación")

from ..config.settings import CameraConfig, SystemConfig


@dataclass
class CameraInfo:
    """Información de una cámara detectada"""
    camera_id: int
    serial_number: str
    is_connected: bool
    last_frame_time: Optional[datetime] = None


class MockCamera:
    """Cámara simulada para desarrollo sin hardware"""
    
    def __init__(self, camera_id: int):
        self.camera_id = camera_id
        self.is_recording = False
        self.frame_count = 0
        
    def start_recording(self):
        self.is_recording = True
        self.frame_count = 0
        
    def stop_recording(self):
        self.is_recording = False
        
    def get_frame(self) -> Optional[np.ndarray]:
        if not self.is_recording:
            return None
            
        # Generar frame simulado con color diferente por cámara
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255)]
        color = colors[self.camera_id % len(colors)]
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = color
        
        # Añadir texto identificativo
        cv2.putText(frame, f"CAM {self.camera_id}", (50, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame, f"Frame: {self.frame_count}", (50, 100), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, datetime.now().strftime("%H:%M:%S.%f")[:-3], (50, 150), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        self.frame_count += 1
        return frame


class CameraManager:
    """Gestor principal de cámaras Orbbec"""
    
    def __init__(self):
        self.cameras: Dict[int, object] = {}
        self.camera_configs: Dict[int, CameraConfig] = {}
        self.recording_threads: Dict[int, threading.Thread] = {}
        self.recording_active = False
        self.frame_callbacks: List[Callable] = []
        
        # Crear directorios necesarios
        SystemConfig.ensure_directories()
        
    def discover_cameras(self) -> List[CameraInfo]:
        """Descubrir cámaras Orbbec conectadas"""
        cameras_found = []
        
        if ORBBEC_AVAILABLE:
            try:
                # Usar SDK real de Orbbec
                context = Context()
                device_list = context.query_device_list()
                
                for i in range(device_list.get_count()):
                    device_info = device_list.get_device_info(i)
                    camera_info = CameraInfo(
                        camera_id=i,
                        serial_number=device_info.get_serial_number(),
                        is_connected=True
                    )
                    cameras_found.append(camera_info)
                    
            except Exception as e:
                print(f"❌ Error descubriendo cámaras reales: {e}")
                # Fallback a simulación
                cameras_found = self._create_mock_cameras()
        else:
            # Usar cámaras simuladas
            cameras_found = self._create_mock_cameras()
            
        return cameras_found
    
    def _create_mock_cameras(self) -> List[CameraInfo]:
        """Crear cámaras simuladas para desarrollo"""
        print("🔧 Creando 3 cámaras simuladas para desarrollo")
        return [
            CameraInfo(camera_id=i, serial_number=f"MOCK_{i:03d}", is_connected=True)
            for i in range(3)
        ]
    
    def initialize_camera(self, camera_id: int, config: CameraConfig) -> bool:
        """Inicializar una cámara específica"""
        try:
            if ORBBEC_AVAILABLE:
                # Configurar cámara real
                pipeline = Pipeline()
                config_ob = Config()
                
                profile_list = pipeline.get_stream_profile_list(OBSensorType.COLOR_SENSOR)
                color_profile = profile_list.get_video_stream_profile(
                    config.resolution_width, 0, OBFormat.RGB, config.fps
                )
                config_ob.enable_stream(color_profile)
                pipeline.start(config_ob)
                
                self.cameras[camera_id] = pipeline
                
            else:
                # Usar cámara simulada
                self.cameras[camera_id] = MockCamera(camera_id)
            
            self.camera_configs[camera_id] = config
            print(f"✅ Cámara {camera_id} inicializada correctamente")
            return True
            
        except Exception as e:
            print(f"❌ Error inicializando cámara {camera_id}: {e}")
            return False
    
    def get_frame(self, camera_id: int) -> Optional[np.ndarray]:
        """Obtener frame de una cámara específica"""
        if camera_id not in self.cameras:
            return None
            
        try:
            camera = self.cameras[camera_id]
            
            if ORBBEC_AVAILABLE and hasattr(camera, 'wait_for_frames'):
                # Cámara real
                frames = camera.wait_for_frames(100)
                if frames is None:
                    return None
                    
                color_frame = frames.get_color_frame()
                if color_frame is None:
                    return None
                    
                # Convertir a formato OpenCV
                return self._frame_to_bgr_image(color_frame)
                
            else:
                # Cámara simulada
                return camera.get_frame()
                
        except Exception as e:
            print(f"❌ Error obteniendo frame de cámara {camera_id}: {e}")
            return None
    
    def _frame_to_bgr_image(self, frame) -> Optional[np.ndarray]:
        """Convertir frame de Orbbec a imagen BGR para OpenCV"""
        try:
            width = frame.get_width()
            height = frame.get_height()
            color_format = frame.get_format()
            data = np.asanyarray(frame.get_data())
            
            if color_format == OBFormat.RGB:
                image = np.reshape(data, (height, width, 3))
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            elif color_format == OBFormat.BGR:
                image = np.reshape(data, (height, width, 3))
            else:
                print(f"⚠️  Formato no soportado: {color_format}")
                return None
                
            return image
            
        except Exception as e:
            print(f"❌ Error convirtiendo frame: {e}")
            return None
    
    def start_recording_all(self) -> bool:
        """Iniciar grabación en todas las cámaras"""
        if self.recording_active:
            print("⚠️  Ya hay una grabación en curso")
            return False
            
        try:
            self.recording_active = True
            
            # Iniciar grabación en cada cámara
            for camera_id in self.cameras:
                if ORBBEC_AVAILABLE:
                    pass  # La grabación se maneja en el bucle principal
                else:
                    # Cámara simulada
                    self.cameras[camera_id].start_recording()
            
            print(f"🎬 Grabación iniciada en {len(self.cameras)} cámaras")
            return True
            
        except Exception as e:
            print(f"❌ Error iniciando grabación: {e}")
            self.recording_active = False
            return False
    
    def stop_recording_all(self) -> bool:
        """Detener grabación en todas las cámaras"""
        try:
            self.recording_active = False
            
            # Detener grabación en cada cámara
            for camera_id in self.cameras:
                if not ORBBEC_AVAILABLE:
                    self.cameras[camera_id].stop_recording()
            
            print("⏹️  Grabación detenida en todas las cámaras")
            return True
            
        except Exception as e:
            print(f"❌ Error deteniendo grabación: {e}")
            return False
    
    def cleanup(self):
        """Limpiar recursos"""
        try:
            self.stop_recording_all()
            
            # Cerrar pipelines de cámaras reales
            if ORBBEC_AVAILABLE:
                for camera_id, pipeline in self.cameras.items():
                    if hasattr(pipeline, 'stop'):
                        pipeline.stop()
            
            self.cameras.clear()
            self.camera_configs.clear()
            print("🧹 Recursos de cámaras liberados")
            
        except Exception as e:
            print(f"❌ Error en cleanup: {e}")


# Singleton del gestor de cámaras
camera_manager = CameraManager()
