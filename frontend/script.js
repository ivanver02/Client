document.addEventListener('DOMContentLoaded', () => {
    try {
        console.log('🚀 DOM Content Loaded - Script iniciando...');
        
        // --- Elementos del DOM ---
        const cameraCountSpan = document.getElementById('camera-count');
        const startBtn = document.getElementById('start-btn');
        const cancelBtn = document.getElementById('cancel-btn');
        const processBtn = document.getElementById('process-btn');
        const recordingControls = document.getElementById('recording-controls');
        const patientIdInput = document.getElementById('patient-id');
        const sessionIdInput = document.getElementById('session-id');
        
        // Verificar que todos los elementos existan
        console.log('🔍 Verificando elementos del DOM:');
        console.log('  - cameraCountSpan:', cameraCountSpan);
        console.log('  - startBtn:', startBtn);
        console.log('  - cancelBtn:', cancelBtn);
        console.log('  - processBtn:', processBtn);
        console.log('  - recordingControls:', recordingControls);
        console.log('  - patientIdInput:', patientIdInput);
        console.log('  - sessionIdInput:', sessionIdInput);

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
            console.log('🔧 Iniciando initializeSystem...');
            showMessage('Inicializando sistema...');
            
            // 1. Verificar salud del sistema
            console.log('🏥 Verificando salud del sistema...');
            const healthResponse = await fetch(API.health);
            console.log('🏥 Health response status:', healthResponse.status);
            
            if (!healthResponse.ok) {
                throw new Error('Backend no disponible');
            }
            
            // 2. Descubrir cámaras
            console.log('🔍 Descubriendo cámaras...');
            const camerasResponse = await fetch(API.discoverCameras);
            console.log('🔍 Cameras response status:', camerasResponse.status);
            
            if (!camerasResponse.ok) {
                throw new Error('Error al descubrir cámaras');
            }
            
            const camerasData = await camerasResponse.json();
            console.log('🔍 Cameras data:', camerasData);
            
            if (!camerasData.success) {
                throw new Error(camerasData.error || 'Error desconocido al descubrir cámaras');
            }
            
            state.cameras = camerasData.total_cameras;
            console.log('📊 Total cámaras detectadas:', state.cameras);
            
            // 3. Inicializar cámaras automáticamente si las hay
            if (state.cameras > 0) {
                console.log('⚙️ Inicializando cámaras...');
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
            console.error('❌ Error en initializeSystem:', error);
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
            console.log('🎬 Iniciando proceso de grabación...');
            
            // Validar datos
            const patientId = patientIdInput.value.trim() || `patient_${new Date().toISOString().split('T')[0]}`;
            console.log('📝 Patient ID:', patientId);
            
            showMessage(`Iniciando grabación para paciente: ${patientId}`);
            
            // Deshabilitar botón mientras procesa
            startBtn.disabled = true;
            startBtn.textContent = "Iniciando...";
            
            console.log('📡 Enviando request a:', API.startRecording);
            const response = await fetch(API.startRecording, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ patient_id: patientId })
            });
            
            console.log('📥 Response status:', response.status);
            console.log('📥 Response OK:', response.ok);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                console.error('❌ Error del servidor:', errorData);
                throw new Error(errorData.error || `Error del servidor: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('📊 Response data:', data);
            
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
            console.error('❌ Error en handleStartRecording:', error);
            showMessage(`Error al iniciar grabación: ${error.message}`, 'error');
            alert(`No se pudo iniciar la grabación: ${error.message}`);
        } finally {
            console.log('🔄 Limpiando estado del botón...');
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
    console.log('🔗 Configurando event listeners...');
    
    if (startBtn) {
        startBtn.addEventListener('click', () => {
            console.log('🔘 Click en botón de inicio detectado');
            handleStartRecording();
        });
        
        // Test adicional - listener directo
        startBtn.addEventListener('click', () => {
            console.log('🔘 [TEST] Click detectado en startBtn');
        });
        
        console.log('✅ Event listener del botón de inicio configurado');
    } else {
        console.error('❌ No se encontró el botón de inicio (start-btn)');
    }
    
    if (cancelBtn) {
        cancelBtn.addEventListener('click', handleCancelRecording);
        console.log('✅ Event listener del botón de cancelar configurado');
    } else {
        console.error('❌ No se encontró el botón de cancelar (cancel-btn)');
    }
    
    if (processBtn) {
        processBtn.addEventListener('click', handleProcessRecording);
        console.log('✅ Event listener del botón de procesar configurado');
    } else {
        console.error('❌ No se encontró el botón de procesar (process-btn)');
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
    
    } catch (error) {
        console.error('❌ Error crítico en el script:', error);
        alert('Error crítico en la aplicación. Revisa la consola para más detalles.');
    }
});
