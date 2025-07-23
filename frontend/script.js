document.addEventListener('DOMContentLoaded', () => {
    // --- Elementos del DOM ---
    const cameraCountSpan = document.getElementById('camera-count');
    const startBtn = document.getElementById('start-btn');
    const cancelBtn = document.getElementById('cancel-btn');
    const processBtn = document.getElementById('process-btn');
    const recordingControls = document.getElementById('recording-controls');
    const patientIdInput = document.getElementById('patient-id');
    const sessionIdInput = document.getElementById('session-id');

    // --- Estado de la aplicación ---
    let state = {
        cameras: 0,
        isRecording: false,
        sessionId: null,
        patientId: null
    };

    // --- API Endpoints optimizados ---
    const API = {
        health: '/api/system/health',
        discoverCameras: '/api/cameras/discover',
        initializeCameras: '/api/cameras/initialize',
        startRecording: '/api/recording/start',
        stopRecording: '/api/recording/stop',
        cancelRecording: '/api/recording/cancel',
        recordingStatus: '/api/recording/status'
    };

    // --- Funciones utilitarias ---
    
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
    }

    // --- Funciones principales ---

    /**
     * Verifica el estado del sistema y descubre cámaras
     */
    async function initializeSystem() {
        try {
            showMessage('Inicializando sistema...');
            
            // 1. Verificar salud del sistema
            const healthResponse = await fetch(API.health);
            if (!healthResponse.ok) {
                throw new Error('Backend no disponible');
            }
            
            // 2. Descubrir cámaras
            const camerasResponse = await fetch(API.discoverCameras);
            if (!camerasResponse.ok) {
                throw new Error('Error al descubrir cámaras');
            }
            
            const camerasData = await camerasResponse.json();
            if (!camerasData.success) {
                throw new Error(camerasData.error || 'Error desconocido al descubrir cámaras');
            }
            
            state.cameras = camerasData.total_cameras;
            
            // 3. Inicializar cámaras automáticamente si las hay
            if (state.cameras > 0) {
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
            // Validar datos
            const patientId = patientIdInput.value.trim() || `patient_${new Date().toISOString().split('T')[0]}`;
            
            showMessage(`Iniciando grabación para paciente: ${patientId}`);
            
            // Deshabilitar botón mientras procesa
            startBtn.disabled = true;
            startBtn.textContent = "Iniciando...";
            
            const response = await fetch(API.startRecording, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ patient_id: patientId })
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `Error del servidor: ${response.status}`);
            }
            
            const data = await response.json();
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
            showMessage(`Error al iniciar grabación: ${error.message}`, 'error');
            alert(`No se pudo iniciar la grabación: ${error.message}`);
        } finally {
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
            processBtn.textContent = "Procesando...";
            
            const response = await fetch(API.stopRecording, { 
                method: 'POST' 
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `Error del servidor: ${response.status}`);
            }
            
            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || 'Error al finalizar grabación');
            }
            
            showMessage(`Grabación finalizada. Chunks procesados: ${data.final_chunks_count || 0}`, 'success');
            alert("¡Grabación finalizada y procesada con éxito!");
            
            // Reset state
            state.sessionId = null;
            state.patientId = null;
            sessionIdInput.value = "";
            patientIdInput.value = "";
            
            toggleRecordingControls(false);
            
        } catch (error) {
            showMessage(`Error al procesar: ${error.message}`, 'error');
            alert(`Hubo un problema al procesar: ${error.message}`);
        } finally {
            processBtn.disabled = false;
            processBtn.textContent = "Procesar";
        }
    }

    /**
     * Cancela la grabación
     */
    async function handleCancelRecording() {
        try {
            if (!confirm('¿Está seguro de que desea cancelar la grabación? Se perderán todos los datos.')) {
                return;
            }
            
            showMessage('Cancelando grabación...');
            
            const response = await fetch(API.cancelRecording, { 
                method: 'POST' 
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `Error del servidor: ${response.status}`);
            }
            
            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || 'Error al cancelar grabación');
            }
            
            showMessage('Grabación cancelada exitosamente', 'success');
            
            // Reset state
            state.sessionId = null;
            state.patientId = null;
            sessionIdInput.value = "";
            patientIdInput.value = "";
            
            toggleRecordingControls(false);
            
        } catch (error) {
            showMessage(`Error al cancelar: ${error.message}`, 'error');
            alert(`Hubo un problema al cancelar: ${error.message}`);
        }
    }

    // --- Event Listeners ---
    startBtn.addEventListener('click', handleStartRecording);
    cancelBtn.addEventListener('click', handleCancelRecording);
    processBtn.addEventListener('click', handleProcessRecording);

    // --- Inicialización ---
    showMessage('Cargando aplicación...');
    initializeSystem();
    
    // Actualizar estado cada 30 segundos
    setInterval(() => {
        if (!state.isRecording) {
            initializeSystem();
        }
    }, 30000);
});
