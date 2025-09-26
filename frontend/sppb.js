document.addEventListener('DOMContentLoaded', () => {
    console.log('SPPB Test - Iniciando aplicación...');

    // --- Elementos del DOM ---
    const elements = {
        // Información de la sesión
        sessionPatientId: document.getElementById('session-patient-id'),
        sessionNumber: document.getElementById('session-number'),
        
        // Videos
        balanceVideo: document.getElementById('balance-video'),
        gaitVideo: document.getElementById('gait-video'),
        chairVideo: document.getElementById('chair-video'),
        
        // Botones de test
        startBalanceTest: document.getElementById('start-balance-test'),
        startGaitTest: document.getElementById('start-gait-test'),
        startChairTest: document.getElementById('start-chair-test'),
        
        // Botones de cancelar
        cancelBalanceTest: document.getElementById('cancel-balance-test'),
        cancelGaitTest: document.getElementById('cancel-gait-test'),
        cancelChairTest: document.getElementById('cancel-chair-test'),
        
        // Otros elementos
        resultsPlaceholder: document.getElementById('results-placeholder'),
        backToMain: document.getElementById('back-to-main')
    };

    // --- Estado de la aplicación ---
    let state = {
        cameras: 0,
        isRecording: false,
        sessionId: null,
        patientId: null,
        statusPollingInterval: null,
        currentTest: null, // 'balance', 'gait', 'chair'
        completedTests: [], // Array para rastrear tests completados
        testOrder: ['balance', 'gait', 'chair'] // Orden obligatorio de los tests
    };

    // --- API Endpoints ---
    const API = {
        health: '/api/system/health',
        discoverCameras: '/api/cameras/discover',
        initializeCameras: '/api/cameras/initialize',
        startRecording: '/api/recording/start',
        stopRecording: '/api/recording/stop',
        cancelRecording: '/api/recording/cancel',
        recordingStatus: '/api/recording/status',
        sessionCheck: '/api/session/check',
        sessionDelete: '/api/session/delete',
        testCancel: '/api/session/test_cancel'
    };

    // --- Funciones auxiliares ---
    function showMessage(message, type = 'info') {
        console.log(`[${type.toUpperCase()}] ${message}`);
    }

    function updateButtonState(button, isRecording, testType) {
        if (isRecording) {
            button.disabled = false;
            button.textContent = `Detener Prueba de ${testType}`;
            button.classList.remove('btn-test');
            button.classList.add('btn-secondary');
        } else {
            button.disabled = false;
            button.textContent = `Empezar Prueba de ${testType}`;
            button.classList.remove('btn-secondary');
            button.classList.add('btn-test');
        }
    }

    function toggleCancelButton(testType, show) {
        const cancelButtons = {
            'balance': elements.cancelBalanceTest,
            'gait': elements.cancelGaitTest,
            'chair': elements.cancelChairTest
        };
        
        const cancelButton = cancelButtons[testType];
        if (cancelButton) {
            if (show) {
                cancelButton.classList.remove('hidden');
                cancelButton.classList.add('btn-cancel');
            } else {
                cancelButton.classList.add('hidden');
                cancelButton.classList.remove('btn-cancel');
            }
        }
    }

    /**
     * Controlar la visibilidad de los videos según el estado del test
     */
    function toggleTestVideo(testType, show) {
        const videos = {
            'balance': elements.balanceVideo,
            'gait': elements.gaitVideo,
            'chair': elements.chairVideo
        };
        
        const video = videos[testType];
        if (video) {
            const videoContainer = video.closest('.form-row.video-row');
            if (videoContainer) {
                if (show) {
                    // Mostrar video
                    video.style.display = 'block';
                    videoContainer.style.display = 'flex';
                } else {
                    // Ocultar completamente el contenedor del video
                    videoContainer.style.display = 'none';
                }
            }
        }
    }

    /**
     * Verificar si un test puede ser iniciado según el orden secuencial
     */
    function canStartTest(testType) {
        const testIndex = state.testOrder.indexOf(testType);
        if (testIndex === -1) return false;
        
        // El primer test siempre puede iniciarse
        if (testIndex === 0) return true;
        
        // Para tests posteriores, verificar que el anterior esté completado
        const previousTest = state.testOrder[testIndex - 1];
        return state.completedTests.includes(previousTest);
    }

    /**
     * Marcar un test como completado y actualizar UI
     */
    function markTestAsCompleted(testType) {
        if (!state.completedTests.includes(testType)) {
            state.completedTests.push(testType);
            console.log(`Test ${testType} marcado como completado. Tests completados:`, state.completedTests);
            updateTestButtonsAvailability();
            updateTestResults(testType);
        }
    }

    /**
     * Actualizar la disponibilidad de los botones según los tests completados
     */
    function updateTestButtonsAvailability() {
        const buttons = {
            'balance': elements.startBalanceTest,
            'gait': elements.startGaitTest,
            'chair': elements.startChairTest
        };
        
        state.testOrder.forEach(testType => {
            const button = buttons[testType];
            if (button) {
                const canStart = canStartTest(testType);
                const isCompleted = state.completedTests.includes(testType);
                
                if (isCompleted) {
                    // Test completado - botón deshabilitado con texto indicativo
                    button.disabled = true;
                    button.textContent = `✓ ${getTestDisplayName(testType)} Completado`;
                    button.classList.remove('btn-test', 'btn-secondary');
                    button.classList.add('btn-secondary');
                    // Ocultar video para tests completados
                    toggleTestVideo(testType, false);
                } else if (canStart && !state.isRecording) {
                    // Test disponible para iniciar
                    button.disabled = false;
                    button.textContent = `Empezar Prueba de ${getTestDisplayName(testType)}`;
                    button.classList.remove('btn-secondary');
                    button.classList.add('btn-test');
                    // Mostrar video para tests disponibles
                    toggleTestVideo(testType, true);
                } else {
                    // Test no disponible todavía
                    button.disabled = true;
                    button.textContent = `Empezar Prueba de ${getTestDisplayName(testType)} (Bloqueado)`;
                    button.classList.remove('btn-test');
                    button.classList.add('btn-secondary');
                    // Ocultar video para tests bloqueados
                    toggleTestVideo(testType, false);
                }
            }
        });
    }

    /**
     * Obtener nombre de display del test
     */
    function getTestDisplayName(testType) {
        const names = {
            'balance': 'Equilibrio',
            'gait': 'Marcha',
            'chair': 'Silla'
        };
        return names[testType] || testType;
    }

    /**
     * Actualizar resultados en la UI cuando se completa un test
     */
    function updateTestResults(testType = null) {
        const resultsContainer = elements.resultsPlaceholder;
        if (resultsContainer) {
            const completedCount = state.completedTests.length;
            const totalTests = state.testOrder.length;
            
            if (completedCount === 0) {
                resultsContainer.textContent = "Pendiente...";
                return;
            }
            
            let resultText = `Tests completados: ${completedCount}/${totalTests}`;
            if (state.completedTests.length > 0) {
                resultText += ` (${state.completedTests.map(t => getTestDisplayName(t)).join(', ')})`;
            }
            
            if (completedCount === totalTests) {
                resultText += ' - ¡Evaluación SPPB completa!';
            }
            
            resultsContainer.textContent = resultText;
        }
    }

    /**
     * Función principal para iniciar/detener grabación de tests
     */
    async function handleTestRecording(testType, buttonElement) {
        // Verificar si el test ya está completado
        if (state.completedTests.includes(testType)) {
            alert(`La prueba de ${getTestDisplayName(testType)} ya ha sido completada.`);
            return;
        }

        // Verificar si el test puede iniciarse según el orden secuencial
        if (!canStartTest(testType)) {
            const testIndex = state.testOrder.indexOf(testType);
            if (testIndex > 0) {
                const previousTest = state.testOrder[testIndex - 1];
                alert(`Para iniciar la prueba de ${getTestDisplayName(testType)}, primero debe completar la prueba de ${getTestDisplayName(previousTest)}.`);
            } else {
                alert(`No se puede iniciar la prueba de ${getTestDisplayName(testType)} en este momento.`);
            }
            return;
        }

        // Si ya hay una grabación en curso, detenerla
        if (state.isRecording && state.currentTest === testType) {
            return await handleStopRecording(testType, buttonElement);
        }

        // Si hay otra prueba en curso, mostrar error
        if (state.isRecording && state.currentTest !== testType) {
            alert(`Ya hay una prueba de ${state.currentTest} en curso. Deténgala primero.`);
            return;
        }

        // Iniciar nueva grabación
        return await handleStartRecording(testType, buttonElement);
    }

    /**
     * Iniciar grabación para un test específico
     */
    async function handleStartRecording(testType, buttonElement) {
        try {
            console.log(`Iniciando grabación para test: ${testType}`);
            
            // Validar datos
            const patientId = elements.sessionPatientId.value.trim() || '1';
            const sessionId = elements.sessionNumber.value.trim() || '1';
            const userHeight = 170; // Valor por defecto
            
            showMessage(`Iniciando grabación de ${testType} para paciente: ${patientId}`);
            
            // Deshabilitar botón mientras procesa
            buttonElement.disabled = true;
            buttonElement.textContent = "Iniciando...";
            
            // 1. Descubrir cámaras
            console.log('Verificando cámaras antes de grabar...');
            const discoverResponse = await fetch(API.discoverCameras);
            if (!discoverResponse.ok) {
                throw new Error('Error descubriendo cámaras');
            }
            
            const discoverData = await discoverResponse.json();
            if (!discoverData.success || discoverData.cameras.length === 0) {
                throw new Error('No se encontraron cámaras conectadas');
            }
            
            // 2. Inicializar cámaras
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

            // 3. Verificar si la sesión ya existe
            const sessionIdForTest = `${sessionId}_${testType}`;
            console.log('Comprobando si la sesión ya existe...');
            const checkResponse = await fetch(API.sessionCheck, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    patient_id: patientId,
                    session_id: sessionIdForTest
                })
            });

            if (!checkResponse.ok) {
                throw new Error('Error comprobando sesión');
            }

            const checkData = await checkResponse.json();
            if (checkData.success && checkData.session_exists) {
                console.log('La sesión ya existe.');

                const userChoice = window.confirm(`La sesión para ${testType} ya existe. ¿Deseas sobrescribirla?`);
                if (userChoice) {
                    console.log('Sobrescribiendo la sesión...');
                    const deleteResponse = await fetch(API.sessionDelete, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            patient_id: patientId,
                            session_id: sessionIdForTest
                        })
                    });

                    if (!deleteResponse.ok) {
                        throw new Error('No se pudo eliminar la sesión existente');
                    }
                } else {
                    console.log('El usuario eligió no sobrescribir la sesión.');
                    return;
                }
            }

            // 4. Iniciar grabación
            console.log('Enviando request a:', API.startRecording);
            const response = await fetch(API.startRecording, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    patient_id: patientId,
                    session_id: sessionIdForTest,
                    user_height: userHeight,
                    test_type: testType
                })
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
            state.isRecording = true;
            state.currentTest = testType;
            
            showMessage(`Grabación de ${testType} iniciada. Session ID: ${data.session_id}`, 'success');
            
            // Actualizar UI del botón
            const testNames = {
                'balance': 'Equilibrio',
                'gait': 'Marcha', 
                'chair': 'Silla'
            };
            updateButtonState(buttonElement, true, testNames[testType]);
            
            // Asegurar que el video esté visible durante la grabación
            toggleTestVideo(testType, true);
            
            // Mostrar botón de cancelar
            toggleCancelButton(testType, true);
            
            // Deshabilitar otros botones de test
            disableOtherTestButtons(testType);
            
        } catch (error) {
            console.error(`Error iniciando grabación de ${testType}:`, error);
            showMessage(`Error al iniciar grabación: ${error.message}`, 'error');
            alert(`No se pudo iniciar la grabación de ${testType}: ${error.message}`);
        } finally {
            if (!state.isRecording) {
                const testNames = {
                    'balance': 'Equilibrio',
                    'gait': 'Marcha', 
                    'chair': 'Silla'
                };
                updateButtonState(buttonElement, false, testNames[testType]);
            }
        }
    }

    /**
     * Detener grabación del test actual
     */
    async function handleStopRecording(testType, buttonElement) {
        try {
            console.log(`Deteniendo grabación de test: ${testType}`);
            
            buttonElement.disabled = true;
            buttonElement.textContent = "Deteniendo...";
            
            const response = await fetch(API.stopRecording, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (!response.ok) {
                throw new Error(`Error del servidor: ${response.status}`);
            }
            
            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || 'Error deteniendo la grabación');
            }
            
            // Actualizar estado
            state.isRecording = false;
            state.currentTest = null;
            
            // Marcar test como completado
            markTestAsCompleted(testType);
            
            showMessage(`Grabación de ${testType} detenida exitosamente`, 'success');
            alert(`Grabación de ${testType} completada y guardada.`);
            
            // Restaurar UI
            const testNames = {
                'balance': 'Equilibrio',
                'gait': 'Marcha', 
                'chair': 'Silla'
            };
            // No usar updateButtonState aquí, ya que markTestAsCompleted maneja la UI
            toggleCancelButton(testType, false);
            
        } catch (error) {
            console.error(`Error deteniendo grabación de ${testType}:`, error);
            showMessage(`Error al detener grabación: ${error.message}`, 'error');
            alert(`Error al detener la grabación de ${testType}: ${error.message}`);
        } finally {
            // Asegurar que el botón se habilite según las reglas secuenciales
            updateTestButtonsAvailability();
        }
    }

    /**
     * Cancelar grabación del test actual
     */
    async function handleCancelTest(testType) {
        try {
            const userConfirm = confirm(`¿Estás seguro de que deseas cancelar la prueba de ${testType}? Se perderán todos los datos grabados.`);
            if (!userConfirm) {
                return;
            }

            console.log(`Cancelando test: ${testType}`);
            showMessage(`Cancelando prueba de ${testType}...`);
            
            // Deshabilitar botones durante cancelación
            const buttons = {
                'balance': { start: elements.startBalanceTest, cancel: elements.cancelBalanceTest },
                'gait': { start: elements.startGaitTest, cancel: elements.cancelGaitTest },
                'chair': { start: elements.startChairTest, cancel: elements.cancelChairTest }
            };
            
            const currentButtons = buttons[testType];
            if (currentButtons) {
                currentButtons.start.disabled = true;
                currentButtons.cancel.disabled = true;
                currentButtons.cancel.textContent = "Cancelando...";
            }
            
            // 1. Cancelar la grabación actual
            const cancelResponse = await fetch(API.cancelRecording, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (!cancelResponse.ok) {
                console.warn('Error cancelando grabación, continuando con cancelación de test...');
            }
            
            // 2. Enviar petición al endpoint de cancelación de test
            const patientId = elements.sessionPatientId.value.trim() || '1';
            const sessionId = elements.sessionNumber.value.trim() || '1';
            const sessionIdForTest = `${sessionId}_${testType}`;
            
            const testCancelResponse = await fetch(API.testCancel, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    patient_id: patientId,
                    session_id: sessionIdForTest,
                    test_type: testType
                })
            });
            
            if (!testCancelResponse.ok) {
                throw new Error(`Error cancelando test en servidor: ${testCancelResponse.status}`);
            }
            
            const cancelData = await testCancelResponse.json();
            if (!cancelData.success) {
                throw new Error(cancelData.error || 'Error cancelando el test');
            }
            
            // 3. Reinicializar cámaras
            console.log('Reinicializando cámaras...');
            const initResponse = await fetch(API.initializeCameras, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });
            
            if (!initResponse.ok) {
                console.warn('Error reinicializando cámaras, pero cancelación completada');
            }
            
            // Actualizar estado
            state.isRecording = false;
            state.currentTest = null;
            
            showMessage(`Prueba de ${testType} cancelada exitosamente`, 'success');
            alert(`La prueba de ${testType} ha sido cancelada. Las cámaras han sido reiniciadas.`);
            
            // Restaurar UI - NO marcar como completado, solo restaurar disponibilidad
            toggleCancelButton(testType, false);
            updateTestButtonsAvailability(); // Usar esta función en lugar de enableAllTestButtons
            
        } catch (error) {
            console.error(`Error cancelando test ${testType}:`, error);
            showMessage(`Error al cancelar prueba: ${error.message}`, 'error');
            alert(`Error al cancelar la prueba de ${testType}: ${error.message}`);
        } finally {
            // Restaurar estado de botones usando la función de disponibilidad
            updateTestButtonsAvailability();
        }
    }

    /**
     * Deshabilitar botones de otros tests durante grabación
     */
    function disableOtherTestButtons(currentTest) {
        // Durante grabación, deshabilitar todos los botones excepto el actual
        state.testOrder.forEach(testType => {
            if (testType !== currentTest) {
                const buttons = {
                    'balance': elements.startBalanceTest,
                    'gait': elements.startGaitTest,
                    'chair': elements.startChairTest
                };
                
                const button = buttons[testType];
                if (button) {
                    button.disabled = true;
                }
            }
        });
    }

    /**
     * Restaurar disponibilidad de botones (reemplaza enableAllTestButtons)
     * Ahora usa la lógica secuencial en lugar de habilitar todos
     */
    function enableAllTestButtons() {
        // Usar la función de disponibilidad secuencial
        updateTestButtonsAvailability();
        
        // Ocultar todos los botones de cancelar
        ['balance', 'gait', 'chair'].forEach(testType => {
            toggleCancelButton(testType, false);
        });
    }

    // --- Funciones de los tests ---
    function startBalanceTest() {
        handleTestRecording('balance', elements.startBalanceTest);
    }

    function startGaitTest() {
        handleTestRecording('gait', elements.startGaitTest);
    }

    function startChairTest() {
        handleTestRecording('chair', elements.startChairTest);
    }

    // --- Funciones para cancelar tests ---
    function cancelBalanceTest() {
        handleCancelTest('balance');
    }

    function cancelGaitTest() {
        handleCancelTest('gait');
    }

    function cancelChairTest() {
        handleCancelTest('chair');
    }

    function backToMain() {
        // Verificar si hay una grabación en curso
        if (state.isRecording) {
            const confirmExit = confirm('Hay una grabación en curso. ¿Estás seguro de que deseas salir? Se cancelará la prueba actual.');
            if (confirmExit && state.currentTest) {
                // Cancelar el test actual antes de salir
                handleCancelTest(state.currentTest).then(() => {
                    window.location.href = 'index.html';
                }).catch(() => {
                    // Si falla la cancelación, permitir salir anyway
                    window.location.href = 'index.html';
                });
                return;
            } else if (!confirmExit) {
                return;
            }
        }
        
        // Navegar de vuelta a la página principal
        window.location.href = 'index.html';
    }

    // --- Event Listeners ---
    if (elements.startBalanceTest) {
        elements.startBalanceTest.addEventListener('click', startBalanceTest);
    }
    
    if (elements.startGaitTest) {
        elements.startGaitTest.addEventListener('click', startGaitTest);
    }
    
    if (elements.startChairTest) {
        elements.startChairTest.addEventListener('click', startChairTest);
    }
    
    // Event listeners para botones de cancelar
    if (elements.cancelBalanceTest) {
        elements.cancelBalanceTest.addEventListener('click', cancelBalanceTest);
    }
    
    if (elements.cancelGaitTest) {
        elements.cancelGaitTest.addEventListener('click', cancelGaitTest);
    }
    
    if (elements.cancelChairTest) {
        elements.cancelChairTest.addEventListener('click', cancelChairTest);
    }
    
    if (elements.backToMain) {
        elements.backToMain.addEventListener('click', backToMain);
    }

    // --- Inicialización ---
    function initializePage() {
        // Obtener datos de la sesión desde localStorage o URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        const patientId = urlParams.get('patientId') || localStorage.getItem('currentPatientId') || 'No especificado';
        const sessionId = urlParams.get('sessionId') || localStorage.getItem('currentSessionId') || 'No especificado';
        
        // Establecer valores en los campos
        if (elements.sessionPatientId) {
            elements.sessionPatientId.value = patientId;
        }
        
        if (elements.sessionNumber) {
            elements.sessionNumber.value = sessionId;
        }
        
        // Inicializar estado de los botones según la lógica secuencial
        updateTestButtonsAvailability();
        updateTestResults(); // Actualizar resultados iniciales
        
        console.log(`SPPB Test inicializado - Paciente: ${patientId}, Sesión: ${sessionId}`);
    }

    // Ejecutar inicialización
    initializePage();
    
    console.log('SPPB Test - Aplicación inicializada correctamente');
});