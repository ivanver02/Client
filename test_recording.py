#!/usr/bin/env python3
"""
Script de prueba para verificar si la grabación funciona
"""
import requests
import time
import json

BASE_URL = "http://127.0.0.1:5000"

def test_recording():
    print("🧪 Probando el sistema de grabación...")
    
    # 1. Verificar estado del sistema
    response = requests.get(f"{BASE_URL}/api/system/health")
    if response.status_code == 200:
        print("✅ Backend funcionando")
    else:
        print("❌ Backend no responde")
        return
    
    # 2. Descubrir cámaras
    response = requests.get(f"{BASE_URL}/api/cameras/discover")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ {data['total_cameras']} cámaras detectadas")
    else:
        print("❌ Error descubriendo cámaras")
        return
    
    # 3. Inicializar cámaras
    response = requests.post(f"{BASE_URL}/api/cameras/initialize", json={})
    if response.status_code == 200:
        data = response.json()
        print(f"✅ {data['total_initialized']} cámaras inicializadas")
    else:
        print("❌ Error inicializando cámaras")
        return
    
    # 4. Iniciar grabación
    response = requests.post(f"{BASE_URL}/api/recording/start", json={"patient_id": "test_patient"})
    if response.status_code == 200:
        data = response.json()
        session_id = data['session_id']
        print(f"✅ Grabación iniciada - Session ID: {session_id}")
    else:
        print(f"❌ Error iniciando grabación: {response.text}")
        return
    
    # 5. Esperar unos segundos
    print("⏱️  Grabando por 10 segundos...")
    time.sleep(10)
    
    # 6. Detener grabación
    response = requests.post(f"{BASE_URL}/api/recording/stop")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Grabación detenida - Chunks: {data.get('final_chunks_count', 0)}")
    else:
        print(f"❌ Error deteniendo grabación: {response.text}")

if __name__ == "__main__":
    test_recording()
