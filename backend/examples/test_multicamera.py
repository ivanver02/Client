#!/usr/bin/env python3
"""
Script de prueba para captura multi-cámara REAL con Orbbec Gemini 335L
Solo funciona con cámaras físicas conectadas - NO simulación
Presiona 'q' para finalizar la grabación
"""
import os
import sys
import time
import threading
import cv2
import numpy as np
from datetime import datetime

# Añadir el SDK al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sdk', 'pyorbbecsdk'))

# Configuración
CHUNK_DURATION = 5  # segundos
NUM_CAMERAS = 3
FPS = 30
RESOLUTION = (640, 480)

# Importación del SDK - SOLO CÁMARAS REALES
try:
    from pyorbbecsdk import *
    print("✅ PyOrbbecSDK disponible")
    
    # Verificar cámaras conectadas
    ctx = Context()
    devices = ctx.query_devices()
    camera_count = devices.get_count()
    print(f"🔍 Cámaras Orbbec detectadas: {camera_count}")
    
    if camera_count == 0:
        print("❌ ERROR: No se detectaron cámaras Orbbec conectadas")
        print("   Verificar:")
        print("   - Cámaras conectadas por USB")
        print("   - Drivers instalados correctamente")
        print("   - Permisos de acceso USB")
        exit(1)
    elif camera_count != NUM_CAMERAS:
        print(f"⚠️  ADVERTENCIA: Se detectaron {camera_count} cámaras, pero se esperan {NUM_CAMERAS}")
        response = input("¿Continuar con las cámaras detectadas? (s/N): ")
        if response.lower() != 's':
            exit(1)
        NUM_CAMERAS = camera_count
    
except ImportError as e:
    print(f"❌ ERROR: PyOrbbecSDK no disponible: {e}")
    print("   Soluciones:")
    print("   1. Verificar que el SDK esté compilado correctamente")
    print("   2. Comprobar que las DLLs estén en el directorio correcto")
    print("   3. Reinstalar dependencias: pip install -r requirements.txt")
    exit(1)


class OrbbecCameraRecorder:
    """Grabador para una cámara Orbbec real"""
    
    def __init__(self, camera_id, output_dir):
        self.camera_id = camera_id
        self.output_dir = output_dir
        self.pipeline = None
        self.device = None
        self.current_writer = None
        self.chunk_number = 0
        self.recording = False
        self.thread = None
        
        # Crear directorio de salida
        os.makedirs(self.output_dir, exist_ok=True)
        
    def initialize(self):
        """Inicializar la cámara Orbbec real"""
        try:
            # Obtener dispositivo específico
            devices = ctx.query_devices()
            if self.camera_id >= devices.get_count():
                print(f"❌ Error: Cámara {self.camera_id} no disponible")
                return False
                
            self.device = devices.get_device_by_index(self.camera_id)
            device_info = self.device.get_device_info()
            print(f"📷 Cámara {self.camera_id}: {device_info.get_name()} - S/N: {device_info.get_serial_number()}")
            
            # Crear pipeline
            self.pipeline = Pipeline(self.device)
            config = Config()
            
            # Configurar stream de color
            try:
                profile_list = self.pipeline.get_stream_profile_list(OBSensorType.COLOR_SENSOR)
                if profile_list.get_count() == 0:
                    print(f"❌ Error: No hay perfiles de color disponibles para cámara {self.camera_id}")
                    return False
                
                # Buscar perfil compatible
                color_profile = None
                for i in range(profile_list.get_count()):
                    profile = profile_list.get_stream_profile_by_index(i).as_video_stream_profile()
                    if (profile.get_width() == RESOLUTION[0] and 
                        profile.get_fps() == FPS and 
                        profile.get_format() in [OBFormat.RGB, OBFormat.BGR, OBFormat.YUYV]):
                        color_profile = profile
                        break
                
                if color_profile is None:
                    # Usar perfil por defecto
                    color_profile = profile_list.get_default_video_stream_profile()
                    print(f"⚠️  Usando perfil por defecto para cámara {self.camera_id}: {color_profile.get_width()}x{color_profile.get_height()}@{color_profile.get_fps()}fps")
                
                config.enable_stream(color_profile)
                self.pipeline.start(config)
                
                print(f"✅ Cámara real {self.camera_id} inicializada")
                return True
                
            except Exception as e:
                print(f"❌ Error configurando cámara {self.camera_id}: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Error inicializando cámara {self.camera_id}: {e}")
            return False
    
    def get_frame(self):
        """Obtener frame de la cámara Orbbec real"""
        try:
            if not self.pipeline:
                return None
                
            frames = self.pipeline.wait_for_frames(100)
            if frames is None:
                return None
                
            color_frame = frames.get_color_frame()
            if color_frame is None:
                return None
            
            # Convertir frame de Orbbec a OpenCV
            width = color_frame.get_width()
            height = color_frame.get_height()
            color_format = color_frame.get_format()
            
            # Obtener datos del frame
            data = np.asanyarray(color_frame.get_data())
            
            if color_format == OBFormat.RGB:
                image = np.reshape(data, (height, width, 3))
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                return image
            elif color_format == OBFormat.BGR:
                image = np.reshape(data, (height, width, 3))
                return image
            elif color_format == OBFormat.YUYV:
                # Convertir YUYV a BGR
                yuv = np.reshape(data, (height, width, 2))
                image = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_YUYV)
                return image
            else:
                print(f"⚠️  Formato no soportado: {color_format}")
                return None
                
        except Exception as e:
            print(f"❌ Error obteniendo frame de cámara {self.camera_id}: {e}")
            return None
    
    def start_new_chunk(self):
        """Iniciar nuevo chunk de video"""
        if self.current_writer:
            self.current_writer.release()
        
        filename = f"{self.chunk_number}.mp4"
        filepath = os.path.join(self.output_dir, filename)
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.current_writer = cv2.VideoWriter(
            filepath, fourcc, FPS, RESOLUTION
        )
        
        if not self.current_writer.isOpened():
            print(f"❌ Error creando video writer para cámara {self.camera_id}")
            return False
            
        print(f"📹 Cámara {self.camera_id}: Iniciando chunk {self.chunk_number}")
        return True
    
    def write_frame(self, frame):
        """Escribir frame al chunk actual"""
        if self.current_writer and frame is not None:
            # Redimensionar frame si es necesario
            if frame.shape[:2] != (RESOLUTION[1], RESOLUTION[0]):
                frame = cv2.resize(frame, RESOLUTION)
            
            self.current_writer.write(frame)
            return True
        return False
    
    def finalize_chunk(self):
        """Finalizar el chunk actual"""
        if self.current_writer:
            self.current_writer.release()
            self.current_writer = None
            print(f"✅ Cámara {self.camera_id}: Chunk {self.chunk_number} finalizado")
            self.chunk_number += 1
            return True
        return False
    
    def start_recording(self):
        """Iniciar grabación en hilo separado"""
        if self.recording:
            return False
            
        self.recording = True
        self.thread = threading.Thread(target=self._recording_loop, daemon=True)
        self.thread.start()
        return True
    
    def stop_recording(self):
        """Detener grabación"""
        self.recording = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=10)
        self.finalize_chunk()
    
    def _recording_loop(self):
        """Bucle principal de grabación"""
        try:
            while self.recording:
                # Iniciar nuevo chunk
                if not self.start_new_chunk():
                    break
                
                start_time = time.time()
                frames_written = 0
                
                # Grabar durante CHUNK_DURATION segundos
                while (time.time() - start_time) < CHUNK_DURATION and self.recording:
                    frame = self.get_frame()
                    if frame is not None:
                        if self.write_frame(frame):
                            frames_written += 1
                    
                    # Control de velocidad
                    time.sleep(1.0 / FPS)
                
                # Finalizar chunk
                self.finalize_chunk()
                print(f"📊 Cámara {self.camera_id}: {frames_written} frames en chunk {self.chunk_number-1}")
                
        except Exception as e:
            print(f"❌ Error en grabación de cámara {self.camera_id}: {e}")
        finally:
            self.recording = False
    
    def cleanup(self):
        """Limpiar recursos"""
        self.stop_recording()
        if self.current_writer:
            self.current_writer.release()
        if self.pipeline:
            try:
                self.pipeline.stop()
            except:
                pass


def main():
    """Función principal"""
    print("🎬 Sistema de Captura Multi-Cámara Orbbec REAL")
    print("=" * 50)
    print(f"📹 Configuración: {NUM_CAMERAS} cámaras, chunks de {CHUNK_DURATION}s")
    print(f"📁 Salida: backend/examples/output/cameraX/")
    print("⌨️  Presiona 'q' para finalizar la grabación")
    print("=" * 50)
    
    # Crear grabadores para cada cámara
    recorders = []
    base_dir = os.path.dirname(__file__)
    
    for camera_id in range(NUM_CAMERAS):
        output_dir = os.path.join(base_dir, "output", f"camera{camera_id}")
        recorder = OrbbecCameraRecorder(camera_id, output_dir)
        
        if recorder.initialize():
            recorders.append(recorder)
        else:
            print(f"❌ No se pudo inicializar la cámara {camera_id}")
            # Limpiar las cámaras ya inicializadas
            for r in recorders:
                r.cleanup()
            return
    
    if not recorders:
        print("❌ No se pudo inicializar ninguna cámara")
        return
    
    print(f"✅ {len(recorders)} cámaras reales inicializadas correctamente")
    
    try:
        # Iniciar grabación en todas las cámaras
        print("\n🎬 Iniciando grabación...")
        for recorder in recorders:
            recorder.start_recording()
        
        print("✅ Grabación iniciada en todas las cámaras")
        print("👀 Mostrando preview de la primera cámara...")
        
        # Mostrar preview de la primera cámara
        cv2.namedWindow("Preview Camera 0", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Preview Camera 0", 640, 480)
        
        while True:
            # Mostrar frame de la primera cámara
            if recorders:
                frame = recorders[0].get_frame()
                if frame is not None:
                    cv2.imshow("Preview Camera 0", frame)
            
            # Verificar tecla
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\n⏹️  Finalizando grabación...")
                break
                
            # Pequeña pausa
            time.sleep(0.01)
    
    except KeyboardInterrupt:
        print("\n⏹️  Grabación interrumpida por Ctrl+C")
    
    finally:
        # Detener todas las grabaciones
        print("🛑 Deteniendo grabaciones...")
        for recorder in recorders:
            recorder.cleanup()
        
        cv2.destroyAllWindows()
        
        # Mostrar resumen
        print("\n📊 Resumen de grabación:")
        for i, recorder in enumerate(recorders):
            output_dir = os.path.join(base_dir, "output", f"camera{i}")
            if os.path.exists(output_dir):
                files = [f for f in os.listdir(output_dir) if f.endswith('.mp4')]
                print(f"  📹 Cámara {i}: {len(files)} chunks generados")
        
        print(f"\n✅ Grabación finalizada. Archivos en: {os.path.join(base_dir, 'output')}")


if __name__ == "__main__":
    main()
