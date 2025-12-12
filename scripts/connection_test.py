#!/usr/bin/env python3
import ccxt
import os
import sys
from dotenv import load_dotenv

# --- COLORES PARA LA TERMINAL ---
VERDE = '\033[92m'
AMARILLO = '\033[93m'
ROJO = '\033[91m'
RESET = '\033[0m'

def test_kraken_connection():
    print(f"\n{AMARILLO}🔌 LULA: Iniciando Test de Conexión a Kraken...{RESET}")
    print("------------------------------------------------")

    # 1. LOCALIZAR Y CARGAR EL .ENV
    # El script está en /scripts, así que el .env está un nivel arriba (..)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    env_path = os.path.join(project_root, '.env')

    print(f"📂 Buscando configuración en: {env_path}")

    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"{VERDE}✅ Archivo .env encontrado.{RESET}")
    else:
        print(f"{ROJO}❌ Error: No existe el archivo .env en la raíz del proyecto.{RESET}")
        print("   Por favor, crea el archivo .env con tus claves API_KEY y SECRET_KEY.")
        sys.exit(1)

    # 2. OBTENER CLAVES
    api_key = os.getenv('API_KEY')
    secret_key = os.getenv('SECRET_KEY')

    if not api_key or not secret_key:
        print(f"{ROJO}❌ Error: Las claves están vacías dentro del .env{RESET}")
        sys.exit(1)

    # 3. CONECTAR A KRAKEN
    try:
        print(f"{AMARILLO}📡 Intentando conectar con Kraken...{RESET}")
        exchange = ccxt.kraken({
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True,
        })

        # --- PRUEBA 1: API PÚBLICA (Ver precio XMR) ---
        # Esto prueba que tienes internet y que Kraken no te ha baneado la IP
        print(f"\n🔹 Prueba 1: Consultar Precio Público (XMR/USD)...")
        ticker = exchange.fetch_ticker('XMR/USD')
        precio = ticker['last']
        print(f"{VERDE}✅ ÉXITO. Precio actual de Monero: ${precio} USD{RESET}")

        # --- PRUEBA 2: API PRIVADA (Ver Saldo) ---
        # Esto prueba que tus claves API son válidas y tienen permisos de lectura
        print(f"\n🔹 Prueba 2: Consultar Saldo Privado...")
        balance = exchange.fetch_balance()
        
        # Filtramos para mostrar solo lo que tiene dinero (> 0)
        total = balance['total']
        activos = {k: v for k, v in total.items() if v > 0}

        print(f"{VERDE}✅ AUTENTICACIÓN CORRECTA.{RESET}")
        print("💰 Tu Cartera:")
        
        if activos:
            for moneda, cantidad in activos.items():
                print(f"   - {moneda}: {cantidad}")
        else:
            print(f"   {AMARILLO}(La cuenta conecta bien, pero el saldo es 0){RESET}")

    except ccxt.AuthenticationError:
        print(f"{ROJO}❌ ERROR DE AUTENTICACIÓN:{RESET}")
        print("   Tus API Keys son incorrectas o no tienen permisos de 'Consulta de Fondos'.")
        print("   Revisa el archivo .env")
    except ccxt.NetworkError:
        print(f"{ROJO}❌ ERROR DE RED:{RESET}")
        print("   No se puede conectar con Kraken. Verifica tu conexión a internet o DNS.")
    except Exception as e:
        print(f"{ROJO}❌ ERROR DESCONOCIDO:{RESET} {e}")

    print("------------------------------------------------")

if __name__ == "__main__":
    try:
        test_kraken_connection()
    except KeyboardInterrupt:
        print("\nTest cancelado.")