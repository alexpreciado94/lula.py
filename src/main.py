import time
from connection import DualExchangeManager
from brain import Brain
from guardian import Guardian
from lullaby import strategy_generator, manage_wealth, manage_bridge, manage_cold_storage, GENERATOR_COINS, TARGET_COIN

def main():
    print("\n🏴‍☠️ LULA (Full-Stack Sovereign) - Iniciando...")
    
    try:
        # 1. Infraestructura
        connection = DualExchangeManager()
        brain = Brain('/app/data/madness.rknn', '/app/data/scaler.pkl')
        guardian = Guardian() # Lógica Macro/Fundamental
    except Exception as e:
        print(f"❌ Error Inicio: {e}"); return

    print(f"✅ Sistema Online. Gen: {connection.gen.id} | Safe: {connection.safe.id}")

    while True:
        try:
            print(f"\n🌙 Ronda [{time.strftime('%H:%M')}]")
            sp500 = connection.get_sp500_data()
            
            # 1. FASE GENERACIÓN (Mercenarios + Guardián)
            print("   🏭 [1/4] Generando Cash...")
            for coin in GENERATOR_COINS:
                strategy_generator(connection, brain, guardian, coin, sp500)

            # 2. FASE PUENTE (Mover ganancias)
            print("   🚚 [2/4] Puente de Fondos...")
            manage_bridge(connection)

            # 3. FASE REFUGIO (Comprar XMR)
            print("   🛡️ [3/4] Comprando Privacidad...")
            # Necesitamos datos de XMR
            xmr_data = connection.get_data(connection.safe, TARGET_COIN)
            if xmr_data:
                prob, rsi, price, rvol = brain.analyze(xmr_data, sp500)
                if prob: manage_wealth(connection, prob, rsi, rvol, price)

            # 4. FASE BÓVEDA (Self-Custody)
            print("   ❄️ [4/4] Enviando a Bóveda...")
            manage_cold_storage(connection)

            print("💤 Durmiendo 60 min...")
            time.sleep(3600)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"⚠️ Error Bucle Principal: {e}")
            time.sleep(60)

    if 'brain' in locals(): brain.release()

if __name__ == "__main__":
    main()