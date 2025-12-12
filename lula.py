import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import joblib
import time
import os
from rknnlite.api import RKNNLite # <--- LA MAGIA DE ROCKCHIP
from dotenv import load_dotenv

load_dotenv()
exchange = ccxt.binance()
symbol = 'BTC/USDT'

# Cargar Escalador (necesario para preprocesar igual)
scaler = joblib.load('data/scaler.pkl')

# Cargar Cerebro NPU
print("⚡ Inicializando NPU en RK3588...")
rknn_lite = RKNNLite()

# Cargar modelo
ret = rknn_lite.load_rknn('./cerebro.rknn')
if ret != 0:
    print('Error cargando RKNN')
    exit(ret)

# Inicializar entorno de ejecución (Core 0 de la NPU)
ret = rknn_lite.init_runtime(core_mask=RKNNLite.NPU_CORE_0)
if ret != 0:
    print('Error inicializando runtime NPU')
    exit(ret)

print("✅ NPU Lista y esperando datos.")

def preparar_datos():
    # ... (Mismo código de antes para bajar datos y calcular indicadores) ...
    bars = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['rsi'] = df.ta.rsi(length=14)
    df['ema20'] = df.ta.ema(length=20)
    df['ema50'] = df.ta.ema(length=50)
    df['atr'] = df.ta.atr(length=14)
    
    last_row = df.iloc[[-1]][['rsi', 'ema20', 'ema50', 'atr', 'close', 'volume']]
    
    # Importante: RKNN espera float32 explícito
    datos_listos = scaler.transform(last_row.values).astype(np.float32)
    return datos_listos, df['close'].iloc[-1]

while True:
    try:
        entrada_ia, precio = preparar_datos()
        
        # INFERENCIA EN NPU
        # RKNN espera una lista de entradas y devuelve una lista de salidas
        outputs = rknn_lite.inference(inputs=[entrada_ia])
        
        # El resultado suele venir en arrays de numpy dentro de una lista
        prediccion = outputs[0][0][0] # Ajustar índices según estructura de salida
        
        print(f"Precio: {precio} | NPU Score: {prediccion:.4f}")
        
        if prediccion > 0.7:
            print("🚀 COMPRA (By NPU)")
        elif prediccion < 0.3:
            print("📉 VENTA (By NPU)")
            
        time.sleep(3600)

    except Exception as e:
        print(f"Error: {e}")
        time.sleep(60)
        
# Al cerrar, liberar NPU
rknn_lite.release()