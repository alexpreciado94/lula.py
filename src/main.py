import time

from brain import Brain
from connection import DualExchangeManager
from guardian import Guardian
from lullaby import (
    GENERATOR_COINS,
    TARGET_COIN,
    manage_bridge,
    manage_cold_storage,
    manage_wealth,
    strategy_generator,
)


def main():
    print("\n🏴‍☠️ LULA (Full-Stack Sovereign) - Iniciando...")

    try:
        connection = DualExchangeManager()
        brain = Brain("/app/data/madness.rknn", "/app/data/scaler.pkl")
        guardian = Guardian()
    except Exception as e:
        print(f"❌ Error Inicio: {e}")
        return

    print(
        f"✅ Sistema Online. Gen: {connection.gen.id} | Safe: {connection.safe.id}"
    )

    while True:
        try:
            print(f"\n🌙 Ronda [{time.strftime('%H:%M')}]")
            sp500 = connection.get_sp500_data()

            print("   🏭 [1/4] Generando Cash...")
            for coin in GENERATOR_COINS:
                strategy_generator(connection, brain, guardian, coin, sp500)

            print("   🚚 [2/4] Puente de Fondos...")
            manage_bridge(connection)

            print("   🛡️ [3/4] Comprando Privacidad...")
            xmr_data = connection.get_data(connection.safe, TARGET_COIN)
            if xmr_data:
                prob, rsi, price, rvol = brain.analyze(xmr_data, sp500)
                if prob:
                    manage_wealth(connection, prob, rsi, rvol, price)

            print("   ❄️ [4/4] Enviando a Bóveda...")
            manage_cold_storage(connection)

            print("💤 Durmiendo 60 min...")
            time.sleep(3600)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"⚠️ Error Bucle Principal: {e}")
            time.sleep(60)

    if "brain" in locals():
        brain.release()


if __name__ == "__main__":
    main()