<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Instrucciones para Copilot - Sistema de Cámaras Orbbec

## Contexto del proyecto

Este es un sistema de captura multi-cámara para cámaras Orbbec Gemini 335Le que:
- Captura video sincronizado de 3-5 cámaras simultáneamente
- Genera chunks de video de 5 segundos en formato MP4
- Envía los chunks a un servidor de procesamiento vía API REST
- Está diseñado para grabar personas desde múltiples ángulos

## Arquitectura

- **Backend**: Sistema modular con Flask API, gestión de cámaras, y procesamiento de video
- **Frontend**: Interfaz web simple con HTML/CSS/JS (en desarrollo)
- **SDK**: Utiliza PyOrbbecSDK v2.x para control de hardware

## Patrones de código

### Gestión de errores
- Usar try-except con logging descriptivo
- Retornar always JSON responses en la API
- Incluir cleanup de recursos en finally blocks

### Concurrencia
- Threading para captura multi-cámara
- Callbacks para procesamiento asíncrono
- Singleton patterns para managers globales

### Configuración
- Dataclasses para configuraciones tipadas
- Settings centralizados en config/settings.py
- Variables de entorno para configuración externa

## Convenciones de naming

- **Cámaras**: `camera_id` (int), empezando en 0
- **Chunks**: `chunk_id` (UUID), `sequence_number` (int por cámara)
- **Sesiones**: `session_id` (UUID), `patient_id` (string)
- **Endpoints**: snake_case, prefijo `/api/`

## Funcionalidades clave

1. **Descubrimiento automático** de cámaras Orbbec
2. **Simulación** cuando no hay hardware físico
3. **Chunks automáticos** cada 5 segundos
4. **Sincronización por software** entre cámaras
5. **Upload automático** al servidor de procesamiento
6. **Cleanup automático** en cancelación

## Aspectos importantes

- El sistema debe funcionar sin cámaras físicas (modo simulación)
- La sincronización actual es por software, futura implementación por hardware
- Los chunks se eliminan localmente después del envío exitoso
- La API debe ser RESTful y bien documentada
- El frontend debe ser minimalista con color celeste

## Testing

- Priorizar funcionalidad sobre testing exhaustivo
- Usar cámaras simuladas para desarrollo
- Verificar cleanup de recursos y archivos
- Probar escenarios de cancelación y error

Cuando generes código para este proyecto, mantén estos patrones y considera siempre la modularidad y el manejo de recursos.
