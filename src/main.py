import time
from connection import DualExchangeManager
from brain import Brain
from lullaby import strategy_generator, strategy_savings, manage_cold_storage, GENERATOR_COINS

def main():
    print("\n🏴‍☠️ LULA (Double-Agent Edition) - Iniciando...")
    
    try:
        # Esto iniciará DOS conexiones
        connection = DualExchangeManager()
        
        # Cerebro único (La IA es la misma para analizar gráficos)
        brain = Brain('/app/data/madness.rknn', '/app/data/scaler.pkl')
    except Exception as e:
        print(f"❌ Error Inicio: {e}")
        return

    print(f"✅ Conectado a {connection.gen.id} (Gen) y {connection.safe.id} (Refugio)")

    while True:
        try:
            print(f"\n🌙 Ronda [{time.strftime('%H:%M')}]")
            sp500 = connection.get_sp500_data()
            
            # 1. TRABAJAR (En Exchange A)
            print("   --- Generando Cash ---")
            for coin in GENERATOR_COINS:
                strategy_generator(connection, brain, coin, sp500)

            # 2. AHORRAR (En Exchange B)
            print("   --- Gestionando XMR ---")
            strategy_savings(connection, brain, sp500)

            # 3. ENVIAR A TREZOR (Salida Final)
            manage_cold_storage(connection)

            print("💤 Durmiendo 60 min...")
            time.sleep(3600)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"⚠️ Error Bucle: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()