document.addEventListener('DOMContentLoaded', () => {
    try {
        console.log('DOM Content Loaded - Script iniciando...');
        
        // --- Elementos del DOM ---
        const cameraCountSpan = document.getElementById('camera-count');
        const startBtn = document.getElementById('start-btn');
        const cancelBtn = document.getElementById('cancel-btn');
        const processBtn = document.getElementById('process-btn');
        const recordingControls = document.getElementById('recording-controls');
        const patientIdInput = document.getElementById('patient-id');
        const sessionIdInput = document.getElementById('session-id');
    const viewReconstructionBtn = document.getElementById('view-reconstruction-btn');
        
        // Verificar que todos los elementos existan
        console.log(' Verificando elementos del DOM:');
        console.log('- cameraCountSpan:', cameraCountSpan);
        console.log('- startBtn:', startBtn);
        console.log('- cancelBtn:', cancelBtn);
        console.log('- processBtn:', processBtn);
        console.log('- recordingControls:', recordingControls);
        console.log('- patientIdInput:', patientIdInput);
        console.log('- sessionIdInput:', sessionIdInput);
    console.log('- viewReconstructionBtn:', viewReconstructionBtn);

    // --- Estado inicial de la aplicación ---
    let state = {
        cameras: 0,
        isRecording: false,
        sessionId: null,
        patientId: null,
        statusPollingInterval: null, //--- Esto es para comprobar periódicamente si han fallado las cámaras
        annotatedVideoCheckInterval: null,
        lastCheckedPatientId: null,
        lastCheckedSessionId: null
    };

    // --- API Endpoints ---
    const API = {
        health: '/api/system/health',
        discoverCameras: '/api/cameras/discover',
        initializeCameras: '/api/cameras/initialize',
        startRecording: '/api/recording/start',
        stopRecording: '/api/recording/stop',
        cancelRecording: '/api/recording/cancel',
        recordingStatus: '/api/recording/status'
    };

    // --- Log de ayuda ---
    
    function showMessage(message, type = 'info') {
        console.log(`[${type.toUpperCase()}] ${message}`);
        // Opcional: mostrar mensajes en la UI
    }

    function toggleRecordingControls(isRecording) {
        state.isRecording = isRecording;
        startBtn.classList.toggle('hidden', isRecording);
        recordingControls.classList.toggle('hidden', !isRecording);
        
        // Deshabilitar inputs durante grabación
        patientIdInput.disabled = isRecording;
        sessionIdInput.disabled = isRecording;
        
        // Iniciar/detener polling de estado
        if (isRecording) {
            startStatusPolling();
        } else {
            stopStatusPolling();
        }
    }

    /**
     * Iniciar verificación periódica del estado de grabación
     */
    function startStatusPolling() {
        if (state.statusPollingInterval) {
            clearInterval(state.statusPollingInterval);
        }
        
        console.log('Iniciando verificación de estado cada 2 segundos...');
        
        state.statusPollingInterval = setInterval(async () => {
            try {
                console.log('Verificando estado de grabación...');
                const response = await fetch(API.recordingStatus);
                
                if (response.ok) {
                    const statusData = await response.json();
                    console.log('Estado recibido:', statusData);
                    
                    if (statusData.success) {
                        // Verificar si hubo fallo de cámaras
                        if (statusData.session_cancelled_by_camera_failure || statusData.camera_failure_detected) {
                            console.log('FALLO DE CÁMARAS DETECTADO EN STATUS!');
                            handleCameraFailure();
                            return;
                        }
                        
                        // Verificar si la sesión fue cancelada por otra razón
                        if (state.isRecording && statusData.session_cancelled && !statusData.is_recording) {
                            console.log('Sesión cancelada externamente');
                            showMessage('La sesión fue cancelada', 'warning');
                            resetRecordingState();
                        }
                    } else {
                        // Incluso si success=false, verificar si hay fallo de cámaras
                        if (statusData.camera_failure_detected || statusData.session_cancelled_by_camera_failure) {
                            console.log(' FALLO DE CÁMARAS DETECTADO EN ERROR RESPONSE!');
                            handleCameraFailure();
                            return;
                        }
                        console.log('Status response success=false:', statusData.error);
                    }
                } else {
                    console.log('Error en respuesta de status:', response.status, response.statusText);
                }
            } catch (error) {
                console.error('Error verificando estado:', error);
            }
        }, 2000); // Verificar cada 2 segundos
    }

    /**
     * Detener verificación periódica del estado
     */
    function stopStatusPolling() {
        if (state.statusPollingInterval) {
            clearInterval(state.statusPollingInterval);
            state.statusPollingInterval = null;
        }
        if (state.annotatedVideoCheckInterval) {
            clearInterval(state.annotatedVideoCheckInterval);
            state.annotatedVideoCheckInterval = null;
        }
    }

    /**
     * Manejar fallo de cámaras detectado
     */
    function handleCameraFailure() {
        console.log('FALLO DE CÁMARAS DETECTADO');
        
        // Detener polling inmediatamente
        stopStatusPolling();
        
        // Deshabilitar todos los botones inmediatamente
        if (processBtn) {
            processBtn.disabled = true;
            processBtn.textContent = "Sistema Cancelado";
        }
        if (cancelBtn) {
            cancelBtn.disabled = true;
        }
        
        // Mostrar mensaje prominente en consola
        console.error('CANCELANDO SESIÓN POR FALLO DE CÁMARAS - DESCONECTAR Y CONECTAR EL SWITCH');
        showMessage('¡FALLO DE CÁMARAS DETECTADO!', 'error');
        
        // Mostrar alert prominente al usuario
        alert('FALLO DE CÁMARAS DETECTADO\n\n' +
              'Algunas cámaras no funcionaron correctamente.\n\n' +
              'Instrucciones a seguir:\n' +
              '1.  Desconecta el switch de las cámaras\n' +
              '2.  Reinicia el servidor de flask\n' +
              '3.  Reabre el navegador\n' +
              '4.  Vuelve a conectar el switch\n' +
              '5.  Reinicia una nueva grabación\n\n' +
              'La sesión ha sido cancelada automáticamente.');
        
        // Resetear estado inmediatamente
        resetRecordingState();
    }

    /**
     * Resetear estado de grabación
     */
    function resetRecordingState() {
        console.log('Reseteando estado de grabación...');
        
        state.sessionId = null;
        state.patientId = null;
        sessionIdInput.value = "";
        patientIdInput.value = "";
        
        // Resetear botones
        if (processBtn) {
            processBtn.disabled = false;
            processBtn.textContent = "Procesar";
        }
        if (cancelBtn) {
            cancelBtn.disabled = false;
        }
        
        toggleRecordingControls(false);
        
    // Nada que ocultar para reconstrucción (siempre visible)

        // Reinicializar sistema para detectar cámaras nuevamente
        setTimeout(() => {
            console.log('Reinicializando sistema...');
            initializeSystem();
        }, 1000);
    }

    // --- Funciones principales ---

    /**
     * Verifica el estado del sistema y descubre cámaras
     */
    async function initializeSystem() {
        try {
            console.log('Iniciando initializeSystem...');
            showMessage('Inicializando sistema...');
            
            // 1. Verificar salud del sistema
            console.log('Verificando salud del sistema...');
            const healthResponse = await fetch(API.health);
            console.log('Health response status:', healthResponse.status);
            
            if (!healthResponse.ok) {
                throw new Error('Backend no disponible');
            }
            
            // 2. Descubrir cámaras
            console.log('Descubriendo cámaras...');
            const camerasResponse = await fetch(API.discoverCameras);
            console.log('Cameras response status:', camerasResponse.status);
            
            if (!camerasResponse.ok) {
                throw new Error('Error al descubrir cámaras');
            }
            
            const camerasData = await camerasResponse.json();
            console.log('Cameras data:', camerasData);
            
            if (!camerasData.success) {
                throw new Error(camerasData.error || 'Error desconocido al descubrir cámaras');
            }
            
            state.cameras = camerasData.total_cameras;
            console.log('Total cámaras detectadas:', state.cameras);
            
            // 3. Inicializar cámaras automáticamente si las hay
            if (state.cameras > 0) {
                console.log('Inicializando cámaras...');
                const initResponse = await fetch(API.initializeCameras, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({})
                });
                
                if (initResponse.ok) {
                    const initData = await initResponse.json();
                    if (initData.success) {
                        showMessage(`${initData.total_initialized} cámaras inicializadas`);
                    }
                }
            }
            
            // 4. Actualizar UI
            updateCameraStatus();
            
        } catch (error) {
            console.error('Error en initializeSystem:', error);
            showMessage(`Error al inicializar: ${error.message}`, 'error');
            cameraCountSpan.textContent = "Error de conexión";
            startBtn.disabled = true;
        }
    }

    /**
     * Actualiza el estado de las cámaras en la UI
     */
    function updateCameraStatus() {
        if (state.cameras === 0) {
            cameraCountSpan.textContent = "Ninguna cámara detectada";
            startBtn.disabled = true;
        } else {
            cameraCountSpan.textContent = `${state.cameras} ${state.cameras === 1 ? 'cámara detectada' : 'cámaras detectadas'}`;
            startBtn.disabled = false;
        }
    }

    /**
     * Inicia la grabación
     */
    async function handleStartRecording() {
        try {
            console.log('Iniciando proceso de grabación...');
            
            // Validar datos
            const patientId = patientIdInput.value.trim() || '1';
            const sessionId = sessionIdInput.value.trim() || '1';
            console.log('Patient ID:', patientId);
            console.log('Session ID:', sessionId);
            
            showMessage(`Iniciando grabación para paciente: ${patientId}`);
            
            // Deshabilitar botón mientras procesa
            startBtn.disabled = true;
            startBtn.textContent = "Iniciando...";
            
            // 1. Asegurar que las cámaras están descubiertas e inicializadas
            console.log('Verificando cámaras antes de grabar...');
            
            // Descubrir cámaras
            const discoverResponse = await fetch(API.discoverCameras);
            if (!discoverResponse.ok) {
                throw new Error('Error descubriendo cámaras');
            }
            
            const discoverData = await discoverResponse.json();
            if (!discoverData.success || discoverData.cameras.length === 0) {
                throw new Error('No se encontraron cámaras conectadas');
            }
            
            // Inicializar cámaras
            console.log('Inicializando cámaras antes de grabar...');
            const initResponse = await fetch(API.initializeCameras, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });
            
            if (!initResponse.ok) {
                throw new Error('Error inicializando cámaras');
            }
            
            const initData = await initResponse.json();
            if (!initData.success || initData.initialized_cameras.length === 0) {
                throw new Error('No se pudieron inicializar las cámaras');
            }
            
            console.log(`${initData.initialized_cameras.length} cámaras inicializadas para grabación`);
            
            // 2. Iniciar grabación
            console.log('Enviando request a:', API.startRecording);
            const response = await fetch(API.startRecording, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    patient_id: patientId,
                    session_id: sessionId
                })
            });
            
            console.log('Response status:', response.status);
            console.log('Response OK:', response.ok);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                console.error('Error del servidor:', errorData);
                throw new Error(errorData.error || `Error del servidor: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Response data:', data);
            
            if (!data.success) {
                throw new Error(data.error || 'El backend no pudo iniciar la grabación');
            }
            
            // Actualizar estado
            state.sessionId = data.session_id;
            state.patientId = data.patient_id;
            sessionIdInput.value = data.session_id;
            
            showMessage(`Grabación iniciada. Session ID: ${data.session_id}`, 'success');
            toggleRecordingControls(true);
            
        } catch (error) {
            console.error('Error en handleStartRecording:', error);
            showMessage(`Error al iniciar grabación: ${error.message}`, 'error');
            alert(`No se pudo iniciar la grabación: ${error.message}`);
        } finally {
            console.log('Limpiando estado del botón...');
            startBtn.disabled = state.cameras === 0;
            startBtn.textContent = "Comenzar Grabación";
        }
    }

    /**
     * Finaliza la grabación y la procesa
     */
    async function handleProcessRecording() {
        try {
            showMessage('Finalizando grabación...');
            processBtn.disabled = true;
            processBtn.textContent = 'Finalizando...';

            const response = await fetch(API.stopRecording, { method: 'POST' });
            if (!response.ok) {
                throw new Error(`Error finalizando grabación: ${response.statusText}`);
            }
            
            const result = await response.json();
            showMessage(`Grabación finalizada. Session ID: ${result.session_id}. Chunks finales: ${result.final_chunks_count}`);
            
            // Iniciar polling para videos anotados
            startAnnotatedVideoCheck(state.patientId, state.sessionId);

        } catch (error) {
            showMessage(`Error al finalizar: ${error.message}`, 'error');
        } finally {
            toggleRecordingControls(false);
            processBtn.disabled = false;
            processBtn.textContent = 'Finalizar y Procesar';
        }
    }

    /**
     * Cancela la grabación
     */
    async function handleCancelRecording() {
        try {
            showMessage('Cancelando grabación...');
            const response = await fetch(API.cancelRecording, { method: 'POST' });
            if (!response.ok) throw new Error('Error cancelando grabación');
            
            const result = await response.json();
            showMessage(`Grabación cancelada. Session ID: ${result.session_id}`);
        } catch (error) {
            showMessage(`Error al cancelar: ${error.message}`, 'error');
        } finally {
            toggleRecordingControls(false);
        }
    }

    function startAnnotatedVideoCheck(patientId, sessionId) {
        // Solo guardar los identificadores; no es necesario polling ahora
        state.lastCheckedPatientId = patientId;
        state.lastCheckedSessionId = sessionId;
        showMessage(`Modo primer chunk: se asume que los videos estarán disponibles en reconstrucción.`);
    }


    // --- Event Listeners ---
    console.log('Configurando event listeners...');
    
    if (startBtn) {
        startBtn.addEventListener('click', () => {
            console.log('Click en botón de inicio detectado');
            handleStartRecording();
        });
        
        // Test adicional - listener directo
        startBtn.addEventListener('click', () => {
            console.log(' [TEST] Click detectado en startBtn');
        });
        
        console.log('Event listener del botón de inicio configurado');
    } else {
        console.error('No se encontró el botón de inicio (start-btn)');
    }
    
    if (cancelBtn) {
        cancelBtn.addEventListener('click', handleCancelRecording);
        console.log('Event listener del botón de cancelar configurado');
    } else {
        console.error('No se encontró el botón de cancelar (cancel-btn)');
    }
    
    if (processBtn) {
        processBtn.addEventListener('click', handleProcessRecording);
        console.log('Event listener del botón de procesar configurado');
    } else {
        console.error('No se encontró el botón de procesar (process-btn)');
    }

    if (viewReconstructionBtn) {
        viewReconstructionBtn.addEventListener('click', () => {
            const patientId = patientIdInput.value.trim() || state.patientId || '1';
            const sessionId = sessionIdInput.value.trim() || state.sessionId || '1';
            // La URL ahora apunta a un archivo dentro de la carpeta 'frontend'
            const url = `reconstruction.html?patient_id=${patientId}&session_id=${sessionId}`;
            window.open(url, '_blank');
        });
        console.log('Event listener del botón de reconstrucción configurado');
    } else {
        console.error('No se encontró el botón de reconstrucción (view-reconstruction-btn)');
    }

    // --- Inicialización ---
    showMessage('Cargando aplicación...');
    initializeSystem();
    
    // Actualizar estado cada 30 segundos
    setInterval(() => {
        if (!state.isRecording) {
            initializeSystem();
        }
    }, 30000);
    // Limpiar intervals al cerrar la página
    window.addEventListener('beforeunload', () => {
        stopStatusPolling();
    });
    
    } catch (error) {
        console.error('Error crítico en el script:', error);
        alert('Error crítico en la aplicación. Revisa la consola para más detalles.');
    }
});
