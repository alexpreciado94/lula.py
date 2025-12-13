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

    # --- 1. INICIALIZACIÓN DE SISTEMAS ---
    try:
        # Conexión a Exchanges (Generador + Refugio)
        connection = DualExchangeManager()

        # Carga del Cerebro IA en la NPU (RK3588)
        # Rutas absolutas dentro del contenedor Docker
        brain = Brain("/app/data/madness.rknn", "/app/data/scaler.pkl")

        # Inicialización del Guardián (Filtro Macro/Social)
        guardian = Guardian()

    except Exception as e:
        print(f"❌ Error Crítico al iniciar: {e}")
        return

    print(f"✅ Sistemas Online. Gen: {connection.gen.id} | Safe: {connection.safe.id}")

    # --- 2. BUCLE PRINCIPAL (VIGILANCIA PERPETUA) ---
    while True:
        try:
            hora_actual = time.strftime("%H:%M")
            print(f"\n🌙 Ronda de Vigilancia [{hora_actual}]")

            # A. Obtener contexto Macro Global (S&P 500) una vez por ciclo
            sp500_data = connection.get_sp500_data()

            # ---------------------------------------------------------
            # FASE 1: EL GENERADOR (Trading Agresivo en Exchange A)
            # ---------------------------------------------------------
            print("   🏭 [1/4] Motor Generador (Cash Flow)...")
            for coin in GENERATOR_COINS:
                try:
                    # Pasamos el 'guardian' para que autorice o bloquee la operación
                    strategy_generator(connection, brain, guardian, coin, sp500_data)
                except Exception as e:
                    print(f"   ⚠️ Error analizando {coin}: {e}")

            # ---------------------------------------------------------
            # FASE 2: EL PUENTE (Movimiento de Fondos A -> B)
            # ---------------------------------------------------------
            print("   🚚 [2/4] Puente de Liquidez...")
            try:
                manage_bridge(connection)
            except Exception as e:
                print(f"   ⚠️ Error en el Puente: {e}")

            # ---------------------------------------------------------
            # FASE 3: EL REFUGIO (Compra de Privacidad en Exchange B)
            # ---------------------------------------------------------
            print("   🛡️ [3/4] Acumulación de Monero...")
            try:
                # Obtenemos datos de XMR
                xmr_data = connection.get_data(connection.safe, TARGET_COIN)

                if xmr_data:
                    # Analizamos XMR con la IA (Prob, RSI, Precio, RVOL)
                    prob, rsi, price, rvol = brain.analyze(xmr_data, sp500_data)

                    if prob is not None:
                        # Ejecutamos la lógica de ahorro/squeeze
                        manage_wealth(connection, prob, rsi, rvol, price)
            except Exception as e:
                print(f"   ⚠️ Error gestionando refugio: {e}")

            # ---------------------------------------------------------
            # FASE 4: LA BÓVEDA (Auto-Custodia a Trezor)
            # ---------------------------------------------------------
            print("   ❄️ [4/4] Protocolo de Bóveda Fría...")
            try:
                manage_cold_storage(connection)
            except Exception as e:
                print(f"   ⚠️ Error en retiro a fría: {e}")

            # ---------------------------------------------------------
            # DESCANSO (Evita saturar APIs y NPU)
            # ---------------------------------------------------------
            print("💤 Lula durmiendo 60 minutos...")
            time.sleep(3600)

        except KeyboardInterrupt:
            print("\n🛑 Deteniendo Lula manualmente...")
            break
        except Exception as e:
            print(f"⚠️ Error inesperado en el bucle principal: {e}")
            print("   Reiniciando ciclo en 60 segundos...")
            time.sleep(60)

    # --- 3. APAGADO SEGURO ---
    if "brain" in locals():
        brain.release()  # Liberar recursos de la NPU
        print("👋 NPU Liberada. Lula desconectada.")


if __name__ == "__main__":
    main()
