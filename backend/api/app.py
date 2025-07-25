import os
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
from typing import Dict, Any

from ..camera_manager import camera_manager, CameraInfo
from ..video_processor import video_processor, VideoChunk
from ..config.settings import SystemConfig


def create_app() -> Flask:
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
        """Servir otros archivos estáticos (JS, CSS, etc.)"""
        return send_from_directory(app.static_folder, path)

    # Callback para envío de chunks al servidor
    def upload_chunk_to_server(chunk: VideoChunk):
        """Enviar chunk al servidor de procesamiento"""
        try:
            url = f"{SystemConfig.SERVER.base_url}{SystemConfig.SERVER.upload_endpoint}" 
            
            # Preparar datos del chunk
            files = {
                'video': open(chunk.file_path, 'rb')
            }
            
            data = {
                'chunk_id': chunk.chunk_id,
                'camera_id': chunk.camera_id,
                'session_id': chunk.session_id,
                'patient_id': chunk.patient_id,
                'sequence_number': chunk.sequence_number,
                'duration_seconds': chunk.duration_seconds,
                'timestamp': chunk.timestamp.isoformat(),
                'file_size_bytes': chunk.file_size_bytes
            }
            
            response = requests.post(url, files=files, data=data, timeout=30)
            
            if response.status_code == 200:
                print(f"Chunk enviado exitosamente: {chunk.chunk_id}")
                # Eliminar archivo local después del envío exitoso
                try:
                    os.remove(chunk.file_path)
                except Exception as e:
                    print(f"Error eliminando archivo local: {e}")
            else:
                print(f"Error enviando chunk: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"Error en upload_chunk_to_server: {e}")
        finally:
            # Cerrar archivo
            try:
                files['video'].close()
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
                config = SystemConfig.DEFAULT_CAMERA_CONFIG # Parte de la por defecto, y le asigna su id
                config.camera_id = camera_id
                
                if camera_manager.initialize_camera(camera_id, config):
                    initialized.append(camera_id)
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
            patient_id = data.get('patient_id', f'patient_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
            
            # 1. Si no hay cámaras inicializadas, hacer descubrimiento e inicialización automática
            if not camera_manager.cameras:
                print("No hay cámaras inicializadas. Iniciando descubrimiento automático...")
                
                # Descubrir cámaras
                discovered_cameras = camera_manager.discover_cameras()
                if not discovered_cameras:
                    return jsonify({
                        'success': False,
                        'error': 'No se encontraron cámaras conectadas'
                    }), 400
                
                # Inicializar todas las cámaras encontradas
                initialized_count = 0
                for camera_info in discovered_cameras:
                    config = camera_manager.DEFAULT_CAMERA_CONFIG
                    config.camera_id = camera_info.camera_id
                    
                    if camera_manager.initialize_camera(camera_info.camera_id, config):
                        initialized_count += 1
                        print(f"Cámara {camera_info.camera_id} inicializada automáticamente")
                    else:
                        print(f"Error inicializando cámara {camera_info.camera_id}")
                
                if initialized_count == 0:
                    return jsonify({
                        'success': False,
                        'error': 'No se pudo inicializar ninguna cámara'
                    }), 400
                
                print(f"🎯 {initialized_count} cámaras inicializadas automáticamente")
            
            # 2. Iniciar sesión
            session_id = video_processor.start_session(patient_id)
            
            # 3. Iniciar grabación
            if video_processor.start_recording():
                return jsonify({
                    'success': True,
                    'session_id': session_id,
                    'patient_id': patient_id,
                    'cameras_recording': list(camera_manager.cameras.keys()),
                    'cameras_initialized': len(camera_manager.cameras),
                    'chunk_duration_seconds': SystemConfig.RECORDING.chunk_duration_seconds,
                    'auto_initialized': len(camera_manager.cameras) > 0
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
    
    @app.route('/api/recording/stop', methods=['POST'])
    def stop_recording():
        """Finalizar grabación"""
        try:
            final_chunks = video_processor.stop_recording()
            
            # Notificar al servidor que la sesión terminó
            try:
                url = f"{SystemConfig.SERVER.base_url}{SystemConfig.SERVER.session_end_endpoint}"
                requests.post(url, json={
                    'session_id': video_processor.session_id,
                    'patient_id': video_processor.patient_id,
                    'final_chunks_count': len(final_chunks)
                }, timeout=10)
            except Exception as e:
                print(f"Error notificando fin de sesión al servidor: {e}")
            
            return jsonify({
                'success': True,
                'session_id': video_processor.session_id,
                'final_chunks_count': len(final_chunks),
                'message': 'Grabación finalizada correctamente'
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
                requests.post(url, json={
                    'session_id': session_id,
                    'patient_id': patient_id,
                    'reason': 'cancelled_by_user'
                }, timeout=10)
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
        host=SystemConfig.LOCAL_API_HOST,
        port=SystemConfig.LOCAL_API_PORT,
        debug=True,
        threaded=True
    )
