import time
import pandas as pd
from security import get_exchange_secure, log_enc
from analysis import CerebroNPU
from strategy import gestionar_oportunidad_xmr

# CONFIGURACIÓN
PARES_ESPECULATIVOS = ['SOL/USDT', 'ETH/USDT', 'BTC/USDT', 'PEPE/USDT']
PAR_REFUGIO = 'XMR/USDT'

def main():
    print("🏴‍☠️ DARK LULA INICIANDO SISTEMAS...")
    
    # 1. Conexión Segura (Vía Tor)
    # Usamos Kraken o KuCoin (Binance no tiene XMR)
    exchange = get_exchange_secure('kraken') 
    
    # 2. Cargar Cerebro
    try:
        cerebro = CerebroNPU('/app/data/cerebro.rknn', '/app/data/scaler.pkl')
    except Exception as e:
        print(f"❌ Error NPU: {e}")
        return

    while True:
        try:
            print(f"\n⏳ Analizando ciclo de mercado ({time.strftime('%H:%M')})...")
            
            # --- FASE 1: TRADING ESPECULATIVO (Generar Cash) ---
            for par in PARES_ESPECULATIVOS:
                bars = exchange.fetch_ohlcv(par, '1h', limit=100)
                df = pd.DataFrame(bars, columns=['ts', 'o', 'h', 'l', 'close', 'volume'])
                
                prob, rsi = cerebro.predecir(df)
                print(f"   🔹 {par}: IA Score {prob:.2f} | RSI {rsi:.1f}")
                
                if prob > 0.85:
                    log_enc(f"Señal COMPRA agresiva en {par}")
                    # exchange.create_market_buy_order(...) # Descomentar para activar
            
            # --- FASE 2: ACUMULACIÓN INTELIGENTE (XMR) ---
            print("   🕵️ Analizando Monero...")
            bars_xmr = exchange.fetch_ohlcv(PAR_REFUGIO, '1h', limit=100)
            df_xmr = pd.DataFrame(bars_xmr, columns=['ts', 'o', 'h', 'l', 'close', 'volume'])
            
            prob_xmr, rsi_xmr = cerebro.predecir(df_xmr)
            precio_xmr = df_xmr['close'].iloc[-1]
            
            compra, mensaje = gestionar_oportunidad_xmr(exchange, precio_xmr, rsi_xmr, prob_xmr)
            
            if compra:
                cantidad_usdt = mensaje
                log_enc(f"🎯 OPORTUNIDAD XMR DETECTADA. Invirtiendo {cantidad_usdt} USDT")
                # cantidad_xmr = cantidad_usdt / precio_xmr
                # exchange.create_market_buy_order(PAR_REFUGIO, cantidad_xmr)
            else:
                print(f"   💤 XMR: {mensaje}")

        except Exception as e:
            print(f"⚠️ Error en ciclo: {e}")
            log_enc(f"ERROR: {e}")
        
        # Esperar 1 hora
        time.sleep(3600)

if __name__ == "__main__":
    main()