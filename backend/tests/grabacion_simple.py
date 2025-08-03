"""
Script simple para grabación continua multi-cámara con Orbbec SDK.
- Inicia grabación en todas las cámaras conectadas.
- Se detiene al presionar 'q' en la ventana de preview o con Ctrl+C.
"""
import os
import sys
import time
import threading
import cv2
import numpy as np

# --- Configuración ---
# Añadir la ruta del SDK de Orbbec al path de Python
# Esto asume que el script está en backend/examples/
SDK_PATH = os.path.join(os.path.dirname(__file__), '..', 'sdk', 'pyorbbecsdk')
sys.path.insert(0, SDK_PATH)

# Configuración de grabación
FPS = 30  # Frames por segundo
RESOLUTION = (640, 480)  # Resolución del video
OUTPUT_BASE_DIR = os.path.join(os.path.dirname(__file__), 'output')

# --- Inicialización del SDK ---
try:
    from pyorbbecsdk import *
    print("SDK de Orbbec importado correctamente.")
except ImportError:
    print("Error: No se pudo importar 'pyorbbecsdk'.")
    print(f"   Asegúrate de que la ruta del SDK es correcta: {SDK_PATH}")
    sys.exit(1)


class OrbbecRecorder:
    """
    Gestiona la grabación de una única cámara Orbbec.
    """
    def __init__(self, device, camera_id):
        self.device = device
        self.camera_id = camera_id
        self.output_path = os.path.join(OUTPUT_BASE_DIR, f"camera{camera_id}", "completo.mp4")
        
        self.pipeline = None
        self.video_writer = None
        self.is_recording = False
        self.recording_thread = None
        self.frames_written = 0
        self.start_time = 0

        # Crear el directorio de salida si no existe
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

    def start(self):
        """Inicializa la cámara y comienza la grabación."""
        try:
            # 1. Crear pipeline y configurar stream de color
            self.pipeline = Pipeline(self.device)
            config = Config()
            profile_list = self.pipeline.get_stream_profile_list(OBSensorType.COLOR_SENSOR)
            
            # Buscar el perfil de video que coincida con la resolución y FPS deseados
            color_profile = profile_list.get_video_stream_profile(RESOLUTION[0], RESOLUTION[1], OBFormat.RGB, FPS)
            if color_profile is None:
                # Si no se encuentra, usar el perfil por defecto
                color_profile = profile_list.get_default_video_stream_profile()
                print(f"Cámara {self.camera_id}: No se encontró el perfil {RESOLUTION}@{FPS} FPS. Usando perfil por defecto.")
            
            config.enable_stream(color_profile)
            self.pipeline.start(config)

            # 2. Configurar el VideoWriter de OpenCV
            fourcc = cv2.VideoWriter_fourcc(*'mp4v') # 'mp4v' es compatible con .mp4
            self.video_writer = cv2.VideoWriter(self.output_path, fourcc, float(color_profile.get_fps()), RESOLUTION)

            if not self.video_writer.isOpened():
                print(f"Error: No se pudo abrir el VideoWriter para la cámara {self.camera_id}")
                return False

            # 3. Iniciar el hilo de grabación
            self.is_recording = True
            self.start_time = time.time()
            self.recording_thread = threading.Thread(target=self._record_loop, daemon=True)
            self.recording_thread.start()
            
            device_info = self.device.get_device_info()
            print(f"Cámara {self.camera_id} ({device_info.get_serial_number()}) grabando en '{self.output_path}'")
            return True

        except Exception as e:
            print(f"Error iniciando la cámara {self.camera_id}: {e}")
            return False

    def _record_loop(self):
        """Bucle que captura frames y los escribe en el archivo de video."""
        while self.is_recording:
            try:
                frames = self.pipeline.wait_for_frames(100)
                if frames is None:
                    continue

                color_frame = frames.get_color_frame()
                if color_frame is None:
                    continue

                # Convertir el frame a un formato que OpenCV pueda usar (BGR)
                data = np.asanyarray(color_frame.get_data())
                image = np.reshape(data, (color_frame.get_height(), color_frame.get_width(), 3))
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

                # Redimensionar si es necesario
                if image.shape[1] != RESOLUTION[0] or image.shape[0] != RESOLUTION[1]:
                    image = cv2.resize(image, RESOLUTION)

                self.video_writer.write(image)
                self.frames_written += 1

            except Exception as e:
                print(f"Error en el bucle de grabación de la cámara {self.camera_id}: {e}")
                break

    def stop(self):
        """Detiene la grabación y libera los recursos."""
        if not self.is_recording:
            return

        self.is_recording = False
        if self.recording_thread:
            self.recording_thread.join(timeout=5) # Esperar a que el hilo termine

        if self.video_writer:
            self.video_writer.release()
        
        if self.pipeline:
            self.pipeline.stop()

        duration = time.time() - self.start_time
        avg_fps = self.frames_written / duration if duration > 0 else 0
        print(f"Cámara {self.camera_id}: Grabación detenida. {self.frames_written} frames guardados en {duration:.2f}s (Avg FPS: {avg_fps:.2f}).")


def main():
    """Función principal del script."""
    print("--- Script de Grabación Simple Multi-Cámara Orbbec ---")
    
    # 1. Detectar cámaras
    try:
        ctx = Context()
        device_list = ctx.query_devices()
        num_devices = device_list.get_count()
        if num_devices == 0:
            print("No se encontraron cámaras Orbbec. Conecta las cámaras y vuelve a intentarlo.")
            return
        print(f"Se encontraron {num_devices} cámaras.")
    except Exception as e:
        print(f"Error al inicializar el contexto o buscar dispositivos: {e}")
        return

    # 2. Crear e iniciar un grabador para cada cámara
    recorders = []
    for i in range(num_devices):
        device = device_list.get_device_by_index(i)
        recorder = OrbbecRecorder(device, i)
        if recorder.start():
            recorders.append(recorder)

    if not recorders:
        print("No se pudo iniciar la grabación en ninguna cámara.")
        return
    
    try:
        while True:
            # Usamos el primer grabador para la vista previa
            # Nota: get_frame no está implementado, así que esta parte es solo para mantener el script vivo
            # y capturar la tecla 'q'. La grabación real ocurre en los hilos.
            
            # Simplemente esperamos la tecla
            key = cv2.waitKey(100) & 0xFF
            if key == ord('q'):
                print("Se presionó 'q'. Deteniendo grabación...")
                break
            
            # Comprobar si alguna grabación ha fallado
            if not all(r.is_recording for r in recorders):
                print("Una de las grabaciones se ha detenido inesperadamente.")
                break

    except KeyboardInterrupt:
        print("\n Ctrl+C presionado. Deteniendo grabación...")
    
    finally:
        # 3. Detener todos los grabadores
        print("\n Deteniendo todas las cámaras...")
        for recorder in recorders:
            recorder.stop()
        
        cv2.destroyAllWindows()
        print("\n Proceso finalizado. Los videos se han guardado en:")
        for recorder in recorders:
            file_size = os.path.getsize(recorder.output_path) / (1024*1024) if os.path.exists(recorder.output_path) else 0
            print(f"  - {recorder.output_path} ({file_size:.2f} MB)")


if __name__ == "__main__":
    main()
