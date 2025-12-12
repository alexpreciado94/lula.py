import time
import sys
# --- IMPORTS ACTUALIZADOS ---
from connection import KrakenConnection
from brain import Brain
from lullaby import manage_wealth, operate_speculation, GENERATOR_COINS, TARGET_COIN

def main():
    print("\n🎶 LULA (Lullaby Edition) - Iniciando...")
    print("-----------------------------------------")
    
    # 1. CONEXIÓN
    try:
        print("🔌 Conectando a Kraken...")
        connection = KrakenConnection()
    except Exception as e:
        print(f"❌ Error conectando: {e}")
        return

    # 2. CEREBRO (Brain)
    try:
        path_model = '/app/data/cerebro.rknn'
        path_scaler = '/app/data/scaler.pkl'
        brain = Brain(path_model, path_scaler)
        print("🧠 Brain NPU Inicializado correctamente.")
    except Exception as e:
        print(f"❌ Error cargando Brain: {e}")
        return

    print("✅ Todo listo. Entrando en bucle de vigilancia.\n")

    # --- BUCLE INFINITO ---
    try:
        while True:
            hora = time.strftime('%H:%M:%S')
            print(f"🌙 Ronda de vigilancia [{hora}]")
            
            # A) FASE DE TRABAJO (Generar Dinero)
            print("   --- Analizando Mercado (Generadores) ---")
            for coin in GENERATOR_COINS:
                try:
                    operate_speculation(connection, brain, coin)
                except Exception as e:
                    print(f"   ⚠️ Error analizando {coin}: {e}")

            # B) FASE DE AHORRO (Gestión Monero)
            print("   --- Revisando Hucha (XMR) ---")
            try:
                # 1. Obtener datos de Monero
                xmr_data = connection.get_data(TARGET_COIN)
                if xmr_data:
                    prob_xmr, rsi_xmr, price_xmr = brain.analyze(xmr_data)
                    
                    if prob_xmr is not None:
                        # 2. Ejecutar estrategia de ahorro
                        manage_wealth(connection, price_xmr, prob_xmr, rsi_xmr)
            except Exception as e:
                print(f"   ⚠️ Error gestionando patrimonio: {e}")

            # C) DORMIR
            print("💤 Lula durmiendo 60 minutos...\n")
            time.sleep(3600)

    except KeyboardInterrupt:
        print("\n🛑 Deteniendo Lula...")
    finally:
        if 'brain' in locals():
            brain.release()
        print("👋 Lula desconectada. Dulces sueños.")

if __name__ == "__main__":
    main()