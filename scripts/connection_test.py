#!/usr/bin/env python3
import os
import sys

import ccxt
from dotenv import load_dotenv

# Colores
VERDE = "\033[92m"
ROJO = "\033[91m"
AMARILLO = "\033[93m"
RESET = "\033[0m"


def test_exchange(role_name, exchange_id, api_key, secret, password=None):
    print(f"\n📡 Probando {role_name} ({AMARILLO}{exchange_id.upper()}{RESET})...")

    if not exchange_id or not api_key:
        print(f"{ROJO}❌ Falta configuración en .env para {role_name}{RESET}")
        return False

    try:
        # Carga dinámica
        exchange_class = getattr(ccxt, exchange_id)
        config = {"apiKey": api_key, "secret": secret, "enableRateLimit": True}
        if password:
            config["password"] = password

        exchange = exchange_class(config)

        # 1. Prueba Pública
        try:
            # Probamos con BTC/USDT que está en todos lados
            ticker = exchange.fetch_ticker("BTC/USDT")
            print(f"   ✅ API Pública: BTC a ${ticker['last']}")
        except Exception as e:
            print(f"   {ROJO}❌ Fallo API Pública: {e}{RESET}")
            return False

        # 2. Prueba Privada
        try:
            balance = exchange.fetch_balance()
            total = balance.get("total", {})
            # Filtrar saldos > 0
            funds = {k: v for k, v in total.items() if v > 0}
            print("   ✅ API Privada (Saldo): OK")
            if funds:
                print(f"      💰 Fondos detectados: {funds}")
            else:
                print("      💰 Cartera vacía (pero conectada).")
        except Exception as e:
            print(f"   {ROJO}❌ Fallo API Privada (Auth): {e}{RESET}")
            return False

        return True

    except Exception as e:
        print(f"{ROJO}❌ Error fatal conectando a {exchange_id}: {e}{RESET}")
        return False


def main():
    print(f"{VERDE}🔌 LULA CONNECTION DIAGNOSTIC TOOL{RESET}")

    # Buscar .env
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    env_path = os.path.join(project_root, ".env")

    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        print(f"{ROJO}❌ No se encuentra el archivo .env en {project_root}{RESET}")
        sys.exit(1)

    # Test 1: Generador
    gen_id = os.getenv("GEN_EXCHANGE_ID")
    gen_key = os.getenv("GEN_API_KEY")
    gen_sec = os.getenv("GEN_SECRET_KEY")
    test_exchange("GENERADOR", gen_id, gen_key, gen_sec)

    # Test 2: Refugio
    xmr_id = os.getenv("XMR_EXCHANGE_ID")
    xmr_key = os.getenv("XMR_API_KEY")
    xmr_sec = os.getenv("XMR_SECRET_KEY")
    xmr_pass = os.getenv("XMR_PASSWORD")
    test_exchange("REFUGIO", xmr_id, xmr_key, xmr_sec, xmr_pass)

    print("\n------------------------------------------------")


if __name__ == "__main__":
    main()