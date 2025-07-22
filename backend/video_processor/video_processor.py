"""
Procesador de video para crear chunks de 5 segundos y enviarlos al servidor
"""
import os
import threading
import time
import cv2
import uuid
import requests
from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

from ..config.settings import SystemConfig, RecordingConfig
from ..camera_manager import camera_manager


@dataclass
class VideoChunk:
    """Información de un chunk de video"""
    chunk_id: str
    camera_id: int
    session_id: str
    patient_id: str
    sequence_number: int
    file_path: str
    duration_seconds: float
    timestamp: datetime
    file_size_bytes: int


class VideoWriter:
    """Manejador de escritura de video para una cámara"""
    
    def __init__(self, camera_id: int, output_path: str, config: RecordingConfig):
        self.camera_id = camera_id
        self.output_path = output_path
        self.config = config
        self.writer: Optional[cv2.VideoWriter] = None
        self.frame_count = 0
        self.start_time: Optional[datetime] = None
        
    def initialize(self, frame_width: int, frame_height: int, fps: int) -> bool:
        """Inicializar el writer de video"""
        try:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.writer = cv2.VideoWriter(
                self.output_path,
                fourcc,
                fps,
                (frame_width, frame_height)
            )
            
            if not self.writer.isOpened():
                print(f"❌ Error: No se pudo crear el video writer para cámara {self.camera_id}")
                return False
                
            self.start_time = datetime.now()
            print(f"📹 Video writer inicializado para cámara {self.camera_id}: {self.output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error inicializando video writer para cámara {self.camera_id}: {e}")
            return False
    
    def write_frame(self, frame) -> bool:
        """Escribir un frame al video"""
        if self.writer is None or not self.writer.isOpened():
            return False
            
        try:
            self.writer.write(frame)
            self.frame_count += 1
            return True
        except Exception as e:
            print(f"❌ Error escribiendo frame en cámara {self.camera_id}: {e}")
            return False
    
    def finalize(self) -> Optional[VideoChunk]:
        """Finalizar el video y retornar información del chunk"""
        if self.writer is None:
            return None
            
        try:
            self.writer.release()
            self.writer = None
            
            # Verificar que el archivo se creó correctamente
            if not os.path.exists(self.output_path):
                print(f"❌ Error: Archivo de video no encontrado: {self.output_path}")
                return None
            
            file_size = os.path.getsize(self.output_path)
            duration = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
            
            # Generar información del chunk
            chunk_info = VideoChunk(
                chunk_id=str(uuid.uuid4()),
                camera_id=self.camera_id,
                session_id="",  # Se asignará externamente
                patient_id="",  # Se asignará externamente
                sequence_number=0,  # Se asignará externamente
                file_path=self.output_path,
                duration_seconds=duration,
                timestamp=self.start_time or datetime.now(),
                file_size_bytes=file_size
            )
            
            print(f"✅ Chunk finalizado para cámara {self.camera_id}: {file_size} bytes, {duration:.2f}s")
            return chunk_info
            
        except Exception as e:
            print(f"❌ Error finalizando video para cámara {self.camera_id}: {e}")
            return None


class VideoProcessor:
    """Procesador principal de video multi-cámara"""
    
    def __init__(self):
        self.recording_active = False
        self.session_id: Optional[str] = None
        self.patient_id: Optional[str] = None
        self.current_writers: Dict[int, VideoWriter] = {}
        self.chunk_sequence: Dict[int, int] = {}  # Secuencia por cámara
        self.recording_thread: Optional[threading.Thread] = None
        self.upload_callbacks: List[Callable[[VideoChunk], None]] = []
        
        # Configuración
        self.config = SystemConfig.RECORDING
        
    def start_session(self, patient_id: str) -> str:
        """Iniciar nueva sesión de grabación"""
        if self.recording_active:
            raise Exception("Ya hay una sesión activa")
            
        self.session_id = str(uuid.uuid4())
        self.patient_id = patient_id
        self.chunk_sequence.clear()
        
        # Inicializar secuencias para cada cámara
        for camera_id in camera_manager.cameras:
            self.chunk_sequence[camera_id] = 0
            
        print(f"🎬 Nueva sesión iniciada: {self.session_id} para paciente: {patient_id}")
        return self.session_id
    
    def start_recording(self) -> bool:
        """Iniciar grabación con chunks automáticos"""
        if self.recording_active:
            return False
            
        if not self.session_id:
            raise Exception("No hay sesión activa. Llamar start_session() primero")
            
        try:
            self.recording_active = True
            
            # Iniciar grabación en cámaras
            if not camera_manager.start_recording_all():
                self.recording_active = False
                return False
            
            # Iniciar hilo de grabación
            self.recording_thread = threading.Thread(target=self._recording_loop, daemon=True)
            self.recording_thread.start()
            
            print(f"🎥 Grabación iniciada para sesión: {self.session_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error iniciando grabación: {e}")
            self.recording_active = False
            return False
    
    def stop_recording(self) -> List[VideoChunk]:
        """Detener grabación y finalizar chunks pendientes"""
        if not self.recording_active:
            return []
            
        print("⏹️  Deteniendo grabación...")
        self.recording_active = False
        
        # Esperar a que termine el hilo de grabación
        if self.recording_thread and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=10)
        
        # Finalizar writers actuales
        final_chunks = []
        for camera_id, writer in self.current_writers.items():
            chunk = self._finalize_writer(camera_id, writer)
            if chunk:
                final_chunks.append(chunk)
        
        self.current_writers.clear()
        camera_manager.stop_recording_all()
        
        print(f"✅ Grabación detenida. {len(final_chunks)} chunks finales generados")
        return final_chunks
    
    def cancel_recording(self) -> bool:
        """Cancelar grabación y limpiar archivos"""
        if not self.recording_active:
            return True
            
        print("❌ Cancelando grabación...")
        self.recording_active = False
        
        # Esperar a que termine el hilo
        if self.recording_thread and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=10)
        
        # Cerrar writers y eliminar archivos
        for camera_id, writer in self.current_writers.items():
            try:
                if writer.writer:
                    writer.writer.release()
                if os.path.exists(writer.output_path):
                    os.remove(writer.output_path)
                    print(f"🗑️  Archivo eliminado: {writer.output_path}")
            except Exception as e:
                print(f"❌ Error eliminando archivo de cámara {camera_id}: {e}")
        
        self.current_writers.clear()
        camera_manager.stop_recording_all()
        
        # Limpiar directorio temporal de la sesión
        self._cleanup_session_files()
        
        print("✅ Grabación cancelada y archivos limpiados")
        return True
    
    def _recording_loop(self):
        """Bucle principal de grabación"""
        try:
            while self.recording_active:
                # Crear nuevos writers si es necesario
                self._create_new_writers()
                
                start_time = time.time()
                frames_written = {camera_id: 0 for camera_id in camera_manager.cameras}
                
                # Grabar durante la duración del chunk
                while (time.time() - start_time) < self.config.chunk_duration_seconds and self.recording_active:
                    # Capturar frames de todas las cámaras (sincronización por software)
                    timestamp = datetime.now()
                    
                    for camera_id in camera_manager.cameras:
                        frame = camera_manager.get_frame(camera_id)
                        if frame is not None and camera_id in self.current_writers:
                            if self.current_writers[camera_id].write_frame(frame):
                                frames_written[camera_id] += 1
                    
                    # Control de velocidad (aproximadamente FPS target)
                    time.sleep(1.0 / 30)  # 30 FPS target
                
                # Finalizar chunk actual y crear el siguiente
                if self.recording_active:
                    self._finalize_current_chunks()
                    
        except Exception as e:
            print(f"❌ Error en bucle de grabación: {e}")
        finally:
            self.recording_active = False
    
    def _create_new_writers(self):
        """Crear nuevos writers para el siguiente chunk"""
        for camera_id in camera_manager.cameras:
            if camera_id not in self.current_writers:
                output_path = self._generate_chunk_path(camera_id)
                writer = VideoWriter(camera_id, output_path, self.config)
                
                # Obtener un frame para determinar dimensiones
                frame = camera_manager.get_frame(camera_id)
                if frame is not None:
                    height, width = frame.shape[:2]
                    fps = camera_manager.camera_configs.get(camera_id, camera_manager.DEFAULT_CAMERA_CONFIG).fps
                    
                    if writer.initialize(width, height, fps):
                        self.current_writers[camera_id] = writer
                    else:
                        print(f"❌ Error inicializando writer para cámara {camera_id}")
    
    def _finalize_current_chunks(self):
        """Finalizar chunks actuales y enviarlos"""
        chunks_to_upload = []
        
        for camera_id, writer in list(self.current_writers.items()):
            chunk = self._finalize_writer(camera_id, writer)
            if chunk:
                chunks_to_upload.append(chunk)
        
        self.current_writers.clear()
        
        # Enviar chunks en paralelo
        for chunk in chunks_to_upload:
            threading.Thread(target=self._upload_chunk, args=(chunk,), daemon=True).start()
    
    def _finalize_writer(self, camera_id: int, writer: VideoWriter) -> Optional[VideoChunk]:
        """Finalizar un writer específico"""
        chunk = writer.finalize()
        if chunk:
            chunk.session_id = self.session_id
            chunk.patient_id = self.patient_id
            chunk.sequence_number = self.chunk_sequence[camera_id]
            self.chunk_sequence[camera_id] += 1
        
        return chunk
    
    def _upload_chunk(self, chunk: VideoChunk):
        """Subir chunk al servidor (placeholder)"""
        try:
            # Llamar callbacks registrados
            for callback in self.upload_callbacks:
                callback(chunk)
                
            print(f"📤 Chunk enviado: Cámara {chunk.camera_id}, Secuencia {chunk.sequence_number}")
            
        except Exception as e:
            print(f"❌ Error enviando chunk: {e}")
    
    def _generate_chunk_path(self, camera_id: int) -> str:
        """Generar ruta para un nuevo chunk"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"cam{camera_id:02d}_{timestamp}.mp4"
        return os.path.join(SystemConfig.TEMP_VIDEO_DIR, self.session_id, filename)
    
    def _cleanup_session_files(self):
        """Limpiar archivos de la sesión actual"""
        if not self.session_id:
            return
            
        session_dir = os.path.join(SystemConfig.TEMP_VIDEO_DIR, self.session_id)
        if os.path.exists(session_dir):
            try:
                import shutil
                shutil.rmtree(session_dir)
                print(f"🗑️  Directorio de sesión eliminado: {session_dir}")
            except Exception as e:
                print(f"❌ Error eliminando directorio de sesión: {e}")
    
    def add_upload_callback(self, callback: Callable[[VideoChunk], None]):
        """Añadir callback para cuando se genere un chunk"""
        self.upload_callbacks.append(callback)


# Singleton del procesador de video
video_processor = VideoProcessor()
