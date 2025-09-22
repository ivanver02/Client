# Gestor de cámaras para captura multi-cámara sincronizada
# Emplea el SDK de Orbbec, si se emplean cámaras de otra marca, se debe implementar un gestor específico para estas
import cv2
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass

# Importación del SDK de Orbbec
try:
    from pyorbbecsdk import *
    from pyorbbecsdk import Pipeline, Device, Config, Context, FrameSet
    from pyorbbecsdk import OBSensorType, OBFormat
    ORBBEC_AVAILABLE = True
except ImportError:
    raise ImportError(
        "PyOrbbecSDK no está disponible. "
        "Instala el SDK de Orbbec correctamente antes de usar este sistema. "
        "Ver docs/INSTALACION_SDK.md para instrucciones."
    )

from ..config.settings import CameraConfig, SystemConfig

# Muestra el estado de una cámara en tiempo real
@dataclass
class CameraInfo:
    """Información de una cámara detectada"""
    camera_id: int
    serial_number: str
    is_connected: bool
    last_frame_time: Optional[datetime] = None


class OrbbecCamera:
    """
    Controlador para una cámara Orbbec
    Si se emplease otra cámara, se debe crear una clase similar adaptada a su SDK, que implemente los mismos métodos.
    """
    
    def __init__(self, device, camera_id: int, config: CameraConfig):
        self.device = device
        self.camera_id = camera_id
        self.config = config
        self.pipeline = None
        self.is_recording = False
        self.color_profile = None
        
    def initialize(self) -> bool:
        """Inicializar la cámara"""
        try:
            self.pipeline = Pipeline(self.device)
            ob_config = Config()
            
            # Obtener perfil de color
            profile_list = self.pipeline.get_stream_profile_list(OBSensorType.COLOR_SENSOR)
            
            # Intentar usar la resolución configurada
            self.color_profile = profile_list.get_video_stream_profile(
                self.config.resolution_width, 
                self.config.resolution_height, 
                OBFormat.RGB, 
                self.config.fps
            )
            
            if not self.color_profile:
                # Usar perfil por defecto si no encuentra la resolución específica
                self.color_profile = profile_list.get_default_video_stream_profile()
                print(f"Cámara {self.camera_id}: Usando resolución por defecto: "
                      f"{self.color_profile.get_width()}x{self.color_profile.get_height()}@{self.color_profile.get_fps()}fps")
            
            ob_config.enable_stream(self.color_profile)

            if self.camera_id == 3 or self.camera_id == 4:
                # Habilitar sensor de profundidad si está disponible
                try:
                    depth_profile_list = self.pipeline.get_stream_profile_list(OBSensorType.DEPTH_SENSOR)
                    if depth_profile_list.get_count() > 0:
                        depth_profile = depth_profile_list.get_default_video_stream_profile()
                        ob_config.enable_stream(depth_profile)
                        print(f"Cámara {self.camera_id}: Sensor de profundidad habilitado")
                    else:
                        print(f"Cámara {self.camera_id}: Sensor de profundidad no disponible")
                except Exception as e:
                    print(f"Cámara {self.camera_id}: Error habilitando sensor de profundidad: {e}")

            self.pipeline.start(ob_config)
            
            print(f"Cámara {self.camera_id} inicializada correctamente")
            return True
            
        except Exception as e:
            print(f"Error inicializando cámara {self.camera_id}: {e}")
            return False
    
    def start_recording(self) -> bool:
        """Iniciar modo de grabación (solo marca el estado, no graba archivos)"""
        if not self.pipeline:
            print(f"Cámara {self.camera_id}: No inicializada")
            return False
            
        self.is_recording = True
        print(f"Cámara {self.camera_id}: Modo grabación activado")
        return True
    
    def stop_recording(self) -> bool:
        """Detener modo de grabación"""
        self.is_recording = False
        print(f"Cámara {self.camera_id}: Modo grabación desactivado")
        return True
    
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
                print(f"Formato de color no soportado: {color_format}")
                return None
                
            return image
            
        except Exception as e:
            print(f"Error convirtiendo frame: {e}")
            return None
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Obtener frame actual de la cámara (para preview)"""
        if not self.pipeline:
            print(f"Cámara {self.camera_id}: Pipeline no inicializado")
            return None
            
        try:
            #print(f"Cámara {self.camera_id}: Intentando obtener frames...")
            # Obtener frames con timeout más largo
            frames = self.pipeline.wait_for_frames(1000)  
            if not frames:
                print(f"Cámara {self.camera_id}: wait_for_frames devolvió None")
                return None, None
                
            #print(f"Cámara {self.camera_id}: Frames obtenidos, buscando color frame...")
            color_frame = frames.get_color_frame()
            if not color_frame:
                print(f"Cámara {self.camera_id}: No se pudo obtener color frame")
                return None, None
            
            #print(f"Cámara {self.camera_id}: Color frame obtenido, convirtiendo...")
            # Convertir a formato OpenCV (BGR)
            result = self._frame_to_bgr_image(color_frame)
            if result is None:
                print(f"Cámara {self.camera_id}: Error en conversión de frame")

            timestamp = datetime.now()
                
            return result, timestamp
            
        except Exception as e:
            print(f"Error obteniendo frame de cámara {self.camera_id}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_depth_frame(self) -> Optional[np.ndarray]:
        """Obtener frame de profundidad y de color de una cámara específica"""
        if not self.pipeline:
            print(f"Cámara {self.camera_id}: Pipeline no inicializado")
            return None
            
        try:
            # Obtener frames con timeout
            frames = self.pipeline.wait_for_frames(1000)
            if not frames:
                print(f"Cámara {self.camera_id}: No se pudieron obtener frames")
                return None, None, None
            
            timestamp = datetime.now()
            
            #print(f"Cámara {self.camera_id}: Frames obtenidos, buscando color frame...")
            color_frame = frames.get_color_frame()
            if not color_frame:
                print(f"Cámara {self.camera_id}: No se pudo obtener color frame")
                return None, None, None
            
            #print(f"Cámara {self.camera_id}: Color frame obtenido, convirtiendo...")
            # Convertir a formato OpenCV (BGR)
            color_frame = self._frame_to_bgr_image(color_frame)
            if color_frame is None:
                print(f"Cámara {self.camera_id}: Error en conversión de frame")
                
            # Obtener frame de profundidad
            depth_frame = frames.get_depth_frame()
            if not depth_frame:
                print(f"Cámara {self.camera_id}: No se pudo obtener depth frame")
                return color_frame, None, timestamp
            
            # Convertir a numpy array
            width = depth_frame.get_width()
            height = depth_frame.get_height()
            depth_data = np.asanyarray(depth_frame.get_data())
            
            print(f"Debug - Cámara {self.camera_id}: Depth frame - width={width}, height={height}, data_size={len(depth_data)}")
            
            # Los datos de profundidad suelen ser de 16 bits (2 bytes por píxel)
            # Verificar si necesitamos reinterpretar los datos
            expected_size = width * height
            if len(depth_data) == expected_size * 2:
                # Datos de 16 bits, convertir a uint16
                depth_data = depth_data.view(np.uint16)
                print(f"Debug - Cámara {self.camera_id}: Converted to uint16, new size={len(depth_data)}")
            
            # Reshape a formato de imagen (height, width)
            depth_image = depth_data.reshape((height, width))
            
            return color_frame, depth_image, timestamp
            
        except Exception as e:
            print(f"Error obteniendo depth frame de cámara {self.camera_id}: {e}")
            return None
    
    def get_real_fps(self) -> int: # Se emplea en _create_new_writers en video_processor.py
        """Obtener el FPS real del perfil de la cámara"""
        if self.color_profile:
            return self.color_profile.get_fps()
        return 30  # FPS por defecto
    
    def cleanup(self):
        """Limpiar recursos de la cámara"""
        try:
            if self.pipeline:
                self.pipeline.stop()
                self.pipeline = None
            print(f"Cámara {self.camera_id}: Recursos liberados")
        except Exception as e:
            print(f"Error limpiando cámara {self.camera_id}: {e}")


class CameraManager:
    """Gestor principal de cámaras Orbbec"""
    
    def __init__(self):
        self.cameras: Dict[int, OrbbecCamera] = {}
        self.camera_configs: Dict[int, CameraConfig] = {}
        self.recording_active = False
        self.context = None
        
        # Crear directorios necesarios
        SystemConfig.ensure_directories()
        
        # Inicializar contexto Orbbec
        try:
            self.context = Context()
            print("Contexto Orbbec inicializado")
        except Exception as e:
            raise RuntimeError(f"Error inicializando contexto Orbbec: {e}")
    
    def discover_cameras(self) -> List[CameraInfo]:
        """Descubrir cámaras Orbbec conectadas"""
        cameras_found = []

        # Mapeo fijo de serial_number a camera_id
        serial_to_id_map = SystemConfig.SERIAL_TO_ID_MAP

        try:
            device_list = self.context.query_devices()
            device_count = device_list.get_count()

            if device_count == 0:
                print("No se encontraron cámaras Orbbec conectadas")
                return cameras_found

            print(f"Encontradas {device_count} cámaras Orbbec")

            # Verificar si el número de cámaras coincide con el tamaño del diccionario
            use_serial_mapping = device_count == len(serial_to_id_map)

            # Inicializar el array con None para mantener posiciones
            cameras_found = [None] * device_count

            for i in range(device_count):
                try:
                    device = device_list[i]
                    device_info = device.get_device_info()
                    serial_number = device_info.get_serial_number()

                    # Asignar camera_id basado en el serial_number solo si coincide el tamaño
                    if use_serial_mapping:
                        camera_id = serial_to_id_map.get(serial_number, i)  # Usar índice como fallback
                    else:
                        camera_id = i  # Asignar ID basado en el índice

                    camera_info = CameraInfo(
                        camera_id=camera_id,
                        serial_number=serial_number,
                        is_connected=True
                    )

                    # Insertar en la posición correspondiente
                    cameras_found[camera_id] = camera_info

                    print(f"Cámara {camera_id}: S/N {serial_number}")

                except Exception as e:
                    print(f"Error procesando cámara {i}: {e}")

            # Filtrar posiciones vacías en caso de errores
            cameras_found = [camera for camera in cameras_found if camera is not None]

        except Exception as e:
            print(f"Error descubriendo cámaras: {e}")
            raise RuntimeError(f"Error crítico en descubrimiento de cámaras: {e}")

        return cameras_found
    
    def initialize_camera(self, camera_id: int, config: CameraConfig) -> bool:
        """Inicializar una cámara específica"""
        try:
            # Verificar si la cámara ya está inicializada
            if camera_id in self.cameras:
                print(f"Cámara {camera_id} ya está inicializada")
                return True

            device_list = self.context.query_devices()

            if camera_id >= device_list.get_count():
                print(f"Cámara {camera_id}: ID fuera de rango")
                return False

            device = device_list[camera_id]
            camera = OrbbecCamera(device, camera_id, config)

            if camera.initialize():
                self.cameras[camera_id] = camera
                self.camera_configs[camera_id] = config
                return True
            else:
                return False

        except Exception as e:
            print(f"Error inicializando cámara {camera_id}: {e}")
            return False
    
    def get_frame(self, camera_id: int) -> Optional[np.ndarray]:
        """Obtener frame de una cámara específica"""
        if camera_id not in self.cameras:
            return None
        
        return self.cameras[camera_id].get_frame()

    def get_depth_frame(self, camera_id: int) -> Optional[np.ndarray]:
        """Obtener frame de profundidad y de color de una cámara específica"""
        if camera_id not in self.cameras:
            return None

        return self.cameras[camera_id].get_depth_frame()

    def start_recording_all(self) -> bool:
        """Iniciar modo de grabación en todas las cámaras"""
        if self.recording_active:
            print("Ya hay una grabación en curso")
            return False
        
        if not self.cameras:
            print("No hay cámaras inicializadas")
            return False
        
        try:
            success_count = 0
            for camera_id, camera in self.cameras.items():
                if camera.start_recording():
                    success_count += 1
                else:
                    print(f"Error iniciando grabación en cámara {camera_id}")
            
            if success_count > 0:
                self.recording_active = True
                print(f"Grabación iniciada en {success_count} cámaras")
                return True
            else:
                print("No se pudo iniciar grabación en ninguna cámara")
                return False
                
        except Exception as e:
            print(f"Error iniciando grabación: {e}")
            return False
    
    def stop_recording_all(self) -> bool:
        """Detener grabación en todas las cámaras"""
        if not self.recording_active:
            return True
        
        try:
            for camera_id, camera in self.cameras.items():
                camera.stop_recording()
            
            self.recording_active = False
            print("Grabación detenida en todas las cámaras")
            return True
            
        except Exception as e:
            print(f"Error deteniendo grabación: {e}")
            return False
    
    def cleanup(self):
        """Limpiar todos los recursos"""
        try:
            # Detener grabación si está activa
            if self.recording_active:
                self.stop_recording_all()
            
            # Limpiar cada cámara
            for camera in self.cameras.values():
                camera.cleanup()
            
            self.cameras.clear()
            self.camera_configs.clear()
            
            print("Gestor de cámaras: Recursos liberados")
            
        except Exception as e:
            print(f"Error limpiando gestor de cámaras: {e}")


# Instancia global del gestor de cámaras
camera_manager = CameraManager()
