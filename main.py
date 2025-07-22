#!/usr/bin/env python3
"""
Script principal para ejecutar el sistema de cámaras Orbbec
"""
import sys
import os

# Añadir el directorio backend al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.api import run_server


def main():
    """Función principal"""
    try:
        print("🎬 Sistema de Cámaras Orbbec - Iniciando...")
        print("=" * 50)
        
        # Ejecutar servidor
        run_server()
        
    except KeyboardInterrupt:
        print("\n⏹️  Sistema detenido por el usuario")
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
