import time
import sys
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

    # 2. CEREBRO (MADNESS)
    try:
        # --- CAMBIO DE NOMBRE AQUÍ ---
        path_model = '/app/data/madness.rknn' 
        # -----------------------------
        path_scaler = '/app/data/scaler.pkl'
        
        brain = Brain(path_model, path_scaler)
        print("🧠 Madness NPU cargado correctamente.")
    except Exception as e:
        print(f"❌ Error cargando Madness: {e}")
        print("   ¡Recuerda ejecutar trainer.py para generar madness.rknn!")
        return

    print("✅ Todo listo. Entrando en bucle de vigilancia.\n")

    try:
        while True:
            hora = time.strftime('%H:%M:%S')
            print(f"🌙 Ronda de vigilancia [{hora}]")
            
            # 1. OBTENER DATO MACRO (SP500)
            print("🌎 Obteniendo estado del S&P 500...")
            sp500_data = connection.get_sp500_data()

            # 2. FASE DE TRABAJO
            print("   --- Analizando Mercado ---")
            for coin in GENERATOR_COINS:
                try:
                    operate_speculation(connection, brain, coin, sp500_data)
                except Exception as e:
                    print(f"   ⚠️ Error analizando {coin}: {e}")

            # 3. FASE DE AHORRO (XMR)
            print("   --- Revisando Hucha (XMR) ---")
            try:
                xmr_data = connection.get_data(TARGET_COIN)
                if xmr_data:
                    prob_xmr, rsi_xmr, price_xmr = brain.analyze(xmr_data, sp500_data)
                    
                    if prob_xmr is not None:
                        manage_wealth(connection, price_xmr, prob_xmr, rsi_xmr)
            except Exception as e:
                print(f"   ⚠️ Error gestionando patrimonio: {e}")

            print("💤 Lula durmiendo 60 minutos...\n")
            time.sleep(3600)

    except KeyboardInterrupt:
        print("\n🛑 Deteniendo Lula...")
    finally:
        if 'brain' in locals():
            brain.release()
        print("👋 Lula desconectada.")

if __name__ == "__main__":
    main()