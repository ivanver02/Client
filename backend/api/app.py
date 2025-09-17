import os
import time
import requests
import mimetypes
import re
from flask import Flask, request, jsonify, send_from_directory, send_file, make_response
from flask_cors import CORS
from datetime import datetime

from ..camera_manager import camera_manager
from ..video_processor import video_processor, VideoChunk
from ..config.settings import SystemConfig, CameraConfig

# Variable global para rastrear cancelaciones por fallo de cámaras
camera_failure_detected = False


def create_app() -> Flask:
    # Configurar MIME types para video
    mimetypes.add_type('video/mp4', '.mp4')
    mimetypes.add_type('video/webm', '.webm')
    mimetypes.add_type('video/ogg', '.ogv')
    
    # Ajustar la ruta para que apunte a la carpeta 'frontend' en el directorio raíz
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'frontend'))
    app = Flask(__name__, static_folder=frontend_dir)
    CORS(app)  # Permitir requests desde el frontend
    
    # Configuración
    app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max
    
    # RUTAS PARA SERVIR EL FRONTEND
    @app.route('/')
    def index():
        """Servir el archivo principal del frontend"""
        return send_from_directory(app.static_folder, 'index.html')

    @app.route('/<path:path>')
    def serve_static(path):
        """Servir otros archivos estáticos (JS, CSS, videos, etc.)"""
        file_path = os.path.join(app.static_folder, path)
        
        # Si es un archivo de video, usar headers específicos con Range requests
        if path.endswith(('.mp4', '.webm', '.ogv', '.avi', '.mov')):
            if os.path.exists(file_path):
                # Obtener el tamaño del archivo
                file_size = os.path.getsize(file_path)
                
                # Verificar si es una solicitud de rango (Range request)
                range_header = request.headers.get('Range')
                
                if range_header:
                    # Parsear el header Range
                    byte_start = 0
                    byte_end = file_size - 1
                    
                    range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
                    if range_match:
                        byte_start = int(range_match.group(1))
                        if range_match.group(2):
                            byte_end = int(range_match.group(2))
                    
                    # Asegurar que no exceda el tamaño del archivo
                    byte_end = min(byte_end, file_size - 1)
                    
                    # Leer el rango específico
                    with open(file_path, 'rb') as f:
                        f.seek(byte_start)
                        data = f.read(byte_end - byte_start + 1)
                    
                    # Crear respuesta parcial (206)
                    response = make_response(data)
                    response.status_code = 206
                    response.headers['Content-Range'] = f'bytes {byte_start}-{byte_end}/{file_size}'
                    response.headers['Accept-Ranges'] = 'bytes'
                    response.headers['Content-Length'] = str(len(data))
                    response.headers['Content-Type'] = 'video/mp4' if path.endswith('.mp4') else 'video/webm'
                    return response
                else:
                    # Respuesta completa con headers para video
                    response = send_file(file_path, 
                                       mimetype='video/mp4' if path.endswith('.mp4') else 'video/webm',
                                       as_attachment=False,
                                       conditional=True)
                    response.headers['Accept-Ranges'] = 'bytes'
                    response.headers['Content-Length'] = str(file_size)
                    response.headers['Cache-Control'] = 'no-cache'
                    return response
        
        return send_from_directory(app.static_folder, path)

    # Almacenamiento de videos anotados
    annotated_base = os.path.join(frontend_dir, 'data', 'annotated_videos')
    os.makedirs(annotated_base, exist_ok=True)

    # Memoria de uploads por sesión para saber cuándo están todos
    annotated_sessions = {}

    @app.route('/debug/video-info')
    def video_info():
        """Debug info del video"""
        video_path = os.path.join(frontend_dir, 'data', 'annotated_videos', 'patient34', 'session20', 'camera0', '0.mp4')
        
        info = {
            'path': video_path,
            'exists': os.path.exists(video_path),
            'size': os.path.getsize(video_path) if os.path.exists(video_path) else 0,
            'frontend_dir': frontend_dir,
            'url_path': 'data/annotated_videos/patient34/session20/camera0/0.mp4'
        }
        
        # Intentar obtener info del códec si está disponible
        try:
            import subprocess
            if os.path.exists(video_path):
                # Usar ffprobe si está disponible
                try:
                    result = subprocess.run([
                        'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', video_path
                    ], capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        import json
                        probe_data = json.loads(result.stdout)
                        info['codec_info'] = probe_data
                except:
                    info['codec_info'] = 'ffprobe no disponible'
        except:
            info['codec_info'] = 'Error obteniendo info de códec'
        
        return jsonify(info)

    @app.route('/api/convert-video', methods=['POST'])
    def convert_video():
        """Convertir video a formato web-compatible"""
        try:
            data = request.get_json()
            input_path = data.get('input_path')
            patient_id = data.get('patient_id', 'patient34')
            session_id = data.get('session_id', 'session20') 
            camera_id = data.get('camera_id', 'camera0')
            
            if not input_path:
                return jsonify({'success': False, 'error': 'input_path requerido'}), 400
            
            # Ruta completa del archivo original
            original_file = os.path.join(frontend_dir, input_path)
            
            if not os.path.exists(original_file):
                return jsonify({'success': False, 'error': 'Archivo no encontrado'}), 404
            
            # Crear directorio para archivos convertidos
            converted_dir = os.path.join(frontend_dir, 'data', 'converted_videos', patient_id, session_id, camera_id)
            os.makedirs(converted_dir, exist_ok=True)
            
            # Archivo de salida
            output_file = os.path.join(converted_dir, '0_converted.mp4')
            relative_output = f'data/converted_videos/{patient_id}/{session_id}/{camera_id}/0_converted.mp4'
            
            # Usar ffmpeg para convertir a formato web-compatible
            import subprocess
            
            try:
                # Comando ffmpeg optimizado para web
                cmd = [
                    'ffmpeg', 
                    '-i', original_file,
                    '-c:v', 'libx264',           # Codec H.264
                    '-profile:v', 'baseline',    # Perfil baseline (más compatible)
                    '-level', '3.0',             # Nivel 3.0 (compatible con móviles)
                    '-pix_fmt', 'yuv420p',       # Formato de pixel compatible
                    '-c:a', 'aac',               # Codec audio AAC
                    '-b:a', '128k',              # Bitrate audio
                    '-movflags', '+faststart',   # Mueve metadatos al inicio (clave!)
                    '-y',                        # Sobrescribir si existe
                    output_file
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    return jsonify({
                        'success': True, 
                        'converted_path': relative_output,
                        'original_size': os.path.getsize(original_file),
                        'converted_size': os.path.getsize(output_file),
                        'message': 'Video convertido exitosamente'
                    })
                else:
                    return jsonify({
                        'success': False, 
                        'error': f'Error de ffmpeg: {result.stderr}'
                    }), 500
                    
            except subprocess.TimeoutExpired:
                return jsonify({'success': False, 'error': 'Timeout en conversión'}), 500
            except FileNotFoundError:
                return jsonify({'success': False, 'error': 'ffmpeg no encontrado. Instalar FFmpeg.'}), 500
            except Exception as e:
                return jsonify({'success': False, 'error': f'Error en conversión: {str(e)}'}), 500
                
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/reconstruction/<patient_id>/<session_id>')
    def get_reconstruction_videos(patient_id, session_id):
        """Obtener y convertir automáticamente todos los videos de una sesión"""
        try:
            # Directorio base de videos anotados
            annotated_dir = os.path.join(frontend_dir, 'data', 'annotated_videos', f'patient{patient_id}', f'session{session_id}')
            
            if not os.path.exists(annotated_dir):
                return jsonify({'success': False, 'error': 'Sesión no encontrada'}), 404
            
            videos = []
            conversion_errors = []
            
            # Buscar todas las cámaras en el directorio
            for camera_folder in os.listdir(annotated_dir):
                camera_path = os.path.join(annotated_dir, camera_folder)
                
                if os.path.isdir(camera_path) and camera_folder.startswith('camera'):
                    camera_id = camera_folder.replace('camera', '')
                    
                    # Buscar videos en esta cámara
                    for video_file in os.listdir(camera_path):
                        if video_file.endswith('.mp4'):
                            original_path = os.path.join(camera_path, video_file)
                            chunk_name = video_file.replace('.mp4', '')
                            
                            # Crear directorio de salida
                            converted_dir = os.path.join(frontend_dir, 'data', 'converted_videos', f'patient{patient_id}', f'session{session_id}', f'camera{camera_id}')
                            os.makedirs(converted_dir, exist_ok=True)
                            
                            # Archivo convertido
                            converted_file = os.path.join(converted_dir, f'{chunk_name}_converted.mp4')
                            relative_converted = f'data/converted_videos/patient{patient_id}/session{session_id}/camera{camera_id}/{chunk_name}_converted.mp4'
                            
                            # Verificar si ya está convertido
                            if os.path.exists(converted_file):
                                videos.append({
                                    'camera_id': camera_id,
                                    'chunk_name': chunk_name,
                                    'converted_path': relative_converted,
                                    'status': 'ready'
                                })
                            else:
                                # Convertir automáticamente
                                try:
                                    import subprocess
                                    cmd = [
                                        'ffmpeg', 
                                        '-i', original_path,
                                        '-c:v', 'libx264',
                                        '-profile:v', 'baseline',
                                        '-level', '3.0',
                                        '-pix_fmt', 'yuv420p',
                                        '-c:a', 'aac',
                                        '-b:a', '128k',
                                        '-movflags', '+faststart',
                                        '-y',
                                        converted_file
                                    ]
                                    
                                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                                    
                                    if result.returncode == 0:
                                        videos.append({
                                            'camera_id': camera_id,
                                            'chunk_name': chunk_name,
                                            'converted_path': relative_converted,
                                            'status': 'converted'
                                        })
                                    else:
                                        conversion_errors.append(f'Camera {camera_id}, chunk {chunk_name}: {result.stderr[:100]}')
                                        
                                except Exception as e:
                                    conversion_errors.append(f'Camera {camera_id}, chunk {chunk_name}: {str(e)}')
            
            # Organizar por cámara
            cameras = {}
            for video in videos:
                camera_id = video['camera_id']
                if camera_id not in cameras:
                    cameras[camera_id] = []
                cameras[camera_id].append(video)
            
            # Ordenar cámaras y chunks
            for camera_id in cameras:
                cameras[camera_id].sort(key=lambda x: int(x['chunk_name']) if x['chunk_name'].isdigit() else 0)
            
            return jsonify({
                'success': True,
                'patient_id': patient_id,
                'session_id': session_id,
                'cameras': cameras,
                'total_videos': len(videos),
                'conversion_errors': conversion_errors
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/annotated_videos/upload', methods=['POST'])
    def upload_annotated_video():
        try:
            patient_id = str(request.form.get('patient_id'))
            session_id = str(request.form.get('session_id'))
            camera_id = str(request.form.get('camera_id'))
            chunk_number = str(request.form.get('chunk_number', '0'))
            f = request.files.get('file')
            if not all([patient_id, session_id, camera_id, f]):
                return jsonify({'success': False, 'error': 'Parametros incompletos'}), 400
            out_dir = os.path.join(annotated_base, f"patient{patient_id}", f"session{session_id}", f"camera{camera_id}")
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, f"{chunk_number}.mp4")
            f.save(out_path)
            key = (patient_id, session_id, chunk_number)
            sess = annotated_sessions.setdefault(key, set())
            sess.add(camera_id)
            return jsonify({'success': True, 'stored': out_path, 'cameras_received': list(sess)})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    # Callback para envío de chunks al servidor
    def upload_chunk_to_server(chunk: VideoChunk):
        """Enviar chunk al servidor de procesamiento"""
        try:
            url = f"{SystemConfig.SERVER.base_url}{SystemConfig.SERVER.upload_endpoint}" 
            
            # Preparar datos del chunk
            files = {
                'file': open(chunk.file_path, 'rb')  # Server espera 'file'
            }
            
            data = {
                'chunk_id': chunk.chunk_id,
                'camera_id': chunk.camera_id,
                'session_id': chunk.session_id,
                'patient_id': chunk.patient_id,
                'chunk_number': chunk.sequence_number,  # Server espera chunk_number
                'duration_seconds': chunk.duration_seconds,
                'timestamp': chunk.timestamp.isoformat(),
                'file_size_bytes': chunk.file_size_bytes
            }
            
            print(f"Uploading chunk: Camera ID {chunk.camera_id}, Chunk ID {chunk.chunk_id}, Session ID {chunk.session_id}")
            
            response = requests.post(url, files=files, data=data, timeout=30)
            
            if response.status_code == 200:
                print(f"Chunk enviado exitosamente: {chunk.chunk_id}")
                # Eliminar archivo local después del envío exitoso
                try:
                    os.remove(chunk.file_path)
                except Exception as e:
                    print(f"Error eliminando archivo local: {e}")
            elif response.status_code == 500:
                # Verificar si es un error de fallo de cámaras
                try:
                    error_data = response.json()
                    if error_data.get('error') == 'CAMERA_FAILURE_DETECTED':
                        print(f"FALLO DE CÁMARAS DETECTADO POR EL SERVIDOR")
                        print(f"Mensaje: {error_data.get('message', 'Error de cámaras')}")
                        print(f"Acción requerida: {error_data.get('action_required', 'Reiniciar switch')}")
                        
                        # Marcar que hubo un fallo de cámaras
                        global camera_failure_detected
                        camera_failure_detected = True
                        
                        # Cancelar la sesión actual inmediatamente
                        try:
                            print("Cancelando sesión local debido a fallo de cámaras...")
                            video_processor.cancel_current_session()
                            print("Sesión local cancelada por fallo de cámaras")
                        except Exception as cancel_error:
                            print(f"Error cancelando sesión local: {cancel_error}")
                        
                        return  # No continuar procesando este chunk
                except:
                    pass  # Si no se puede parsear como JSON, continuar con el manejo normal
                    
                print(f"Error 500 enviando chunk: {response.status_code} - {response.text}")
            else:
                print(f"Error enviando chunk: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"Error en upload_chunk_to_server: {e}")
        finally:
            # Cerrar archivo
            print("Se ha mandado el chunk correctamente.")
            try:
                files['file'].close()
            except:
                pass
    
    # Registrar callback
    video_processor.add_upload_callback(upload_chunk_to_server)
    
    # ENDPOINTS DE CÁMARAS
    
    @app.route('/api/cameras/discover', methods=['GET'])
    def discover_cameras():
        """Dice cuántas cámaras hay conectadas"""
        try:
            cameras = camera_manager.discover_cameras()
            return jsonify({
                'success': True,
                'cameras': [
                    {
                        'camera_id': cam.camera_id,
                        'serial_number': cam.serial_number,
                        'is_connected': cam.is_connected
                    }
                    for cam in cameras
                ],
                'total_cameras': len(cameras)
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/cameras/initialize', methods=['POST'])
    def initialize_cameras():
        """Inicializar cámaras para grabación"""
        try:
            data = request.get_json() or {}
            camera_ids = data.get('camera_ids', [])
            
            if not camera_ids:
                # Descubrir e inicializar todas las cámaras disponibles
                discovered = camera_manager.discover_cameras()
                camera_ids = [cam.camera_id for cam in discovered]
            
            initialized = []
            errors = []
            
            for camera_id in camera_ids:
                # Crear nueva configuración para cada cámara
                config = CameraConfig(
                    camera_id=camera_id,
                    resolution_width=SystemConfig.DEFAULT_CAMERA_CONFIG.resolution_width,
                    resolution_height=SystemConfig.DEFAULT_CAMERA_CONFIG.resolution_height,
                    fps=SystemConfig.DEFAULT_CAMERA_CONFIG.fps,
                    format=SystemConfig.DEFAULT_CAMERA_CONFIG.format
                )
                
                if camera_manager.initialize_camera(camera_id, config):
                    initialized.append(camera_id)
                    time.sleep(0.5)
                else:
                    errors.append(f"Error inicializando cámara {camera_id}")
            
            return jsonify({
                'success': len(errors) == 0,
                'initialized_cameras': initialized,
                'errors': errors,
                'total_initialized': len(initialized)
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/cameras/status', methods=['GET'])
    def camera_status():
        """Obtener estado de las cámaras"""
        try:
            status = {}
            for camera_id in camera_manager.cameras:
                frame = camera_manager.get_frame(camera_id)
                status[camera_id] = {
                    'is_active': frame is not None,
                    'last_frame_received': datetime.now().isoformat() if frame is not None else None
                }
            
            return jsonify({
                'success': True,
                'cameras': status,
                'recording_active': camera_manager.recording_active
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    # ENDPOINTS DE GRABACIÓN
    
    @app.route('/api/recording/start', methods=['POST'])
    def start_recording():
        """Iniciar grabación"""
        try:
            data = request.get_json() or {}
            patient_id = data.get('patient_id', '1')
            session_id = data.get('session_id', '1')
            
            # Reiniciar flag de fallo de cámaras al iniciar nueva sesión
            global camera_failure_detected
            camera_failure_detected = False
            
            # Verificar que hay cámaras inicializadas
            if not camera_manager.cameras:
                return jsonify({
                    'success': False,
                    'error': 'No hay cámaras inicializadas. Inicialice las cámaras primero.'
                }), 400
            
            # Iniciar sesión
            result_session_id = video_processor.start_session(patient_id, session_id)
            
            # Notificar al servidor que la sesión inició (el servidor maneja automáticamente el cierre de sesiones anteriores)
            try:
                url = f"{SystemConfig.SERVER.base_url}{SystemConfig.SERVER.session_start_endpoint}"
                start_response = requests.post(url, json={
                    'patient_id': patient_id,
                    'session_id': session_id,  # Usar el session_id del frontend
                    'cameras_count': len(camera_manager.cameras)
                }, timeout=10)
                
                if start_response.status_code != 200:
                    print(f"Error notificando inicio de sesión al servidor: {start_response.status_code}")
            except Exception as e:
                print(f"Error notificando inicio de sesión al servidor: {e}")
                # No fallar si el servidor no responde, continuar con grabación local
            
            # Iniciar grabación
            if video_processor.start_recording():
                return jsonify({
                    'success': True,
                    'session_id': session_id,
                    'patient_id': patient_id,
                    'cameras_recording': list(camera_manager.cameras.keys()),
                    'cameras_initialized': len(camera_manager.cameras),
                    'chunk_duration_seconds': SystemConfig.RECORDING.chunk_duration_seconds
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Error iniciando grabación'
                }), 500
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/recording/status', methods=['GET'])
    def get_recording_status():
        """Obtener estado actual de la grabación"""
        try:
            global camera_failure_detected
            
            # Manejar casos donde video_processor puede no estar inicializado
            try:
                is_recording = video_processor.recording_active if video_processor else False
                session_id = video_processor.session_id if video_processor else None
                patient_id = video_processor.patient_id if video_processor else None
            except AttributeError:
                is_recording = False
                session_id = None
                patient_id = None
            
            cameras_info = []
            try:
                for camera_id, camera in camera_manager.cameras.items():
                    cameras_info.append({
                        'camera_id': camera_id,
                        'is_connected': getattr(camera, 'is_connected', False),
                        'is_recording': getattr(camera, 'is_recording', False)
                    })
            except AttributeError:
                # Si camera_manager.cameras no existe o está vacío
                pass
            
            # Determinar si la sesión fue cancelada por fallo de cámaras
            session_cancelled_by_camera_failure = camera_failure_detected and not is_recording and session_id is None
            
            return jsonify({
                'success': True,
                'is_recording': is_recording,
                'session_id': session_id,
                'patient_id': patient_id,
                'cameras': cameras_info,
                'total_cameras': len(cameras_info),
                'session_cancelled': not is_recording and session_id is None,
                'camera_failure_detected': camera_failure_detected,
                'session_cancelled_by_camera_failure': session_cancelled_by_camera_failure
            })
            
        except Exception as e:
            print(f"Error en get_recording_status: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'camera_failure_detected': camera_failure_detected,
                'session_cancelled_by_camera_failure': camera_failure_detected
            }), 200  # Cambiar a 200 para que el frontend pueda procesar la respuesta

    @app.route('/api/recording/stop', methods=['POST'])
    def stop_recording():
        """Finalizar grabación"""
        try:
            print("Procesando finalización de grabación...")
            final_chunks = video_processor.stop_recording()
            
            # Enviar chunks finales inmediatamente al servidor
            if final_chunks:
                print(f"Enviando {len(final_chunks)} chunks finales al servidor...")
                for chunk in final_chunks:
                    try:
                        # Usar el mismo callback que se usa para chunks regulares
                        upload_chunk_to_server(chunk)
                        print(f"Chunk final enviado: Cámara {chunk.camera_id}, Duración: {chunk.duration_seconds:.2f}s")
                    except Exception as upload_error:
                        print(f"Error enviando chunk final de cámara {chunk.camera_id}: {upload_error}")
            
            # Dar un momento para que se completen las subidas
            time.sleep(2)
            
            # Notificar al servidor que la sesión terminó
            try:
                url = f"{SystemConfig.SERVER.base_url}{SystemConfig.SERVER.session_end_endpoint}"
                end_response = requests.post(url, json={
                    'session_id': video_processor.session_id,
                    'patient_id': video_processor.patient_id,
                    'final_chunks_count': len(final_chunks),
                    'reason': 'session_completed'
                }, timeout=10)
                
                if end_response.status_code == 200:
                    print("Sesión finalizada correctamente en el servidor (datos preservados)")
                elif end_response.status_code == 400:
                    print("Info: No había sesión activa en el servidor para finalizar")
                else:
                    print(f"Warning: Respuesta inesperada del servidor al finalizar: {end_response.status_code}")
            except Exception as e:
                print(f"Error notificando fin de sesión al servidor: {e}")
            
            return jsonify({
                'success': True,
                'session_id': video_processor.session_id,
                'final_chunks_count': len(final_chunks),
                'message': f'Grabación finalizada correctamente. {len(final_chunks)} chunks finales enviados.'
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/recording/cancel', methods=['POST'])
    def cancel_recording():
        """Cancelar grabación"""
        try:
            session_id = video_processor.session_id
            patient_id = video_processor.patient_id
            
            video_processor.cancel_recording()
            
            # Notificar al servidor que la sesión fue cancelada
            try:
                url = f"{SystemConfig.SERVER.base_url}{SystemConfig.SERVER.session_cancel_endpoint}"
                cancel_response = requests.post(url, json={
                    'session_id': session_id,
                    'patient_id': patient_id,
                    'reason': 'cancelled_by_user'
                }, timeout=10)
                
                if cancel_response.status_code == 200:
                    print("Sesión cancelada correctamente en el servidor (datos eliminados)")
                elif cancel_response.status_code == 400:
                    print("Info: No había sesión activa en el servidor para cancelar")
                else:
                    print(f"Warning: Respuesta inesperada del servidor al cancelar: {cancel_response.status_code}")
            except Exception as e:
                print(f"Error notificando cancelación al servidor: {e}")
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'message': 'Grabación cancelada y archivos eliminados'
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/recording/status', methods=['GET'])
    def recording_status():
        """Obtener estado de la grabación"""
        try:
            return jsonify({
                'success': True,
                'recording_active': video_processor.recording_active,
                'session_id': video_processor.session_id,
                'patient_id': video_processor.patient_id,
                'cameras_count': len(camera_manager.cameras)
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    # ENDPOINTS DE SISTEMA
    
    @app.route('/api/system/health', methods=['GET'])
    def system_health():
        """Verificar estado del sistema"""
        try:
            return jsonify({
                'success': True,
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'cameras_initialized': len(camera_manager.cameras),
                'recording_active': video_processor.recording_active,
                'temp_dir': SystemConfig.TEMP_VIDEO_DIR,
                'server_config': {
                    'base_url': SystemConfig.SERVER.base_url,
                    'upload_endpoint': SystemConfig.SERVER.upload_endpoint
                }
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'status': 'unhealthy'
            }), 500
    
    @app.route('/api/system/cleanup', methods=['POST'])
    def cleanup_system():
        """Limpiar recursos del sistema"""
        try:
            camera_manager.cleanup()
            
            return jsonify({
                'success': True,
                'message': 'Sistema limpiado correctamente'
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    # IMPORTANTE: devolver la instancia de Flask
    return app

def run_server(): # Ejecuta el servidor Flask
    
    # Crear directorios necesarios
    SystemConfig.ensure_directories()
    
    app = create_app()
    
    print(f"Iniciando servidor de cámaras Orbbec...")
    print(f"URL: http://{SystemConfig.LOCAL_API_HOST}:{SystemConfig.LOCAL_API_PORT}")
    print(f"Directorio temporal: {SystemConfig.TEMP_VIDEO_DIR}")
    print(f"Servidor de procesamiento: {SystemConfig.SERVER.base_url}")

    app.run(
    host="0.0.0.0",  # Escuchar en todas las interfaces para permitir acceso remoto
        port=SystemConfig.LOCAL_API_PORT,
        debug=True,
        threaded=True
    )
