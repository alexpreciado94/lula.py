import time
import os
import numpy as np
import pandas as pd
import pandas_ta as ta
import ccxt
import joblib
from dotenv import load_dotenv
from rknnlite.api import RKNNLite  # <--- Librería exclusiva de Rockchip

# --- 1. CONFIGURACIÓN INICIAL ---
print("⚙️ Iniciando sistema Lula...")
load_dotenv()

# Conexión a Binance
exchange = ccxt.binance({
    'apiKey': os.getenv('API_KEY'),
    'secret': os.getenv('SECRET_KEY'),
    'enableRateLimit': True
})
symbol = 'BTC/USDT'
timeframe = '1h'

# Cargar el Traductor (Scaler)
# Docker buscará esto en la carpeta mapeada /app/data/
path_scaler = 'data/scaler.pkl' 
path_model = 'data/cerebro.rknn'

print(f"📂 Cargando escalador desde {path_scaler}...")
try:
    scaler = joblib.load(path_scaler)
except Exception as e:
    print(f"❌ Error crítico: No se encuentra {path_scaler}. Entrena primero.")
    exit()

# --- 2. INICIALIZAR NPU (EL CEREBRO) ---
print(f"⚡ Cargando modelo NPU desde {path_model}...")
rknn_lite = RKNNLite()

# Cargar modelo
ret = rknn_lite.load_rknn(path_model)
if ret != 0:
    print('❌ Error cargando RKNN model')
    exit(ret)

# Iniciar hardware (Usamos el Core 0 de la NPU)
ret = rknn_lite.init_runtime(core_mask=RKNNLite.NPU_CORE_0)
if ret != 0:
    print('❌ Error inicializando runtime NPU')
    exit(ret)

print("✅ LULA ONLINE. NPU lista para inferencia.")

# --- FUNCIONES AUXILIARES ---

def obtener_datos_ia():
    """Descarga datos, calcula indicadores y normaliza para la IA"""
    try:
        # 1. Descargar velas
        bars = exchange.fetch_ohlcv(symbol, timeframe, limit=100)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # 2. Calcular Indicadores (DEBEN SER IDÉNTICOS AL ENTRENAMIENTO)
        df['rsi'] = df.ta.rsi(length=14)
        df['ema20'] = df.ta.ema(length=20)
        df['ema50'] = df.ta.ema(length=50)
        df['atr'] = df.ta.atr(length=14)
        
        # 3. Preparar el último dato
        # Seleccionamos las mismas columnas que en el entrenamiento
        features = ['rsi', 'ema20', 'ema50', 'atr', 'close', 'volume']
        last_row = df.iloc[[-1]][features]
        
        # 4. Normalizar (Escalar)
        # Convertimos a numpy y transformamos con el scaler cargado
        datos_normalizados = scaler.transform(last_row.values)
        
        # 5. Convertir a float32 (Requisito estricto de RKNN)
        datos_listos = datos_normalizados.astype(np.float32)
        
        return datos_listos, df['close'].iloc[-1]
    
    except Exception as e:
        print(f"⚠️ Error obteniendo datos: {e}")
        return None, None

def ejecutar_orden(tipo, precio):
    """Aquí iría la lógica real de compra/venta"""
    # IMPORTANTE: Aquí debes añadir lógica para no comprar si ya compraste, etc.
    print(f"💰 ORDEN ENVIADA: {tipo} a precio aprox {precio}")
    # exchange.create_market_order(symbol, tipo, 0.001) # Descomentar para real

# --- 3. BUCLE PRINCIPAL (MAIN LOOP) ---
while True:
    print(f"\n⏳ Analizando mercado ({time.strftime('%H:%M:%S')})...")
    
    input_ia, precio_actual = obtener_datos_ia()
    
    if input_ia is not None:
        # --- INFERENCIA NPU ---
        # La NPU espera una lista de inputs
        outputs = rknn_lite.inference(inputs=[input_ia])
        
        # Extraer el resultado (es un array dentro de arrays)
        # La salida es la probabilidad (0 a 1)
        probabilidad = outputs[0][0][0]
        
        print(f"💎 BTC: {precio_actual} USDT")
        print(f"🧠 Confianza IA (Score): {probabilidad:.4f}")
        
        # --- TOMA DE DECISIONES ---
        if probabilidad > 0.75:
            print("🚀 SEÑAL: FUERTE ALCISTA (COMPRAR)")
            ejecutar_orden('buy', precio_actual)
            
        elif probabilidad < 0.25:
            print("📉 SEÑAL: FUERTE BAJISTA (VENDER)")
            ejecutar_orden('sell', precio_actual)
            
        else:
            print("😐 SEÑAL: INCERTIDUMBRE (ESPERAR)")
            
    else:
        print("⚠️ No se pudieron obtener datos, reintentando...")

    # Esperar 1 hora (3600 segundos) para la siguiente vela
    # Se puede optimizar para esperar menos y chequear más a menudo
    print("💤 Durmiendo 60 minutos...")
    time.sleep(3600)

# Al cerrar el programa (Ctrl+C), liberamos la NPU
rknn_lite.release()