import os
import sys
import numpy as np
import pandas as pd
import pandas_ta as ta
import ccxt
import tensorflow as tf
import tf2onnx
import onnx
import joblib
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split

# --- CONFIGURACIÓN DE RUTAS ---
# Ubicación: lula_project/scripts/trainer/trainer.py
# Destino:   lula_project/data/

current_dir = os.path.dirname(os.path.abspath(__file__)) # .../trainer
scripts_dir = os.path.dirname(current_dir)               # .../scripts
project_root = os.path.dirname(scripts_dir)              # .../lula_project

DATA_DIR = os.path.join(project_root, 'data')
MODEL_NAME = 'cerebro'

# --- PARÁMETROS DEL ENTRENADOR ---
SYMBOL = 'XMR/USD'      # Entrenamos con Monero (privacidad pura)
TIMEFRAME = '1h'
LIMIT = 5000            # Más datos = Mejor IA
EPOCHS = 20
BATCH_SIZE = 32

print(f"📂 Raíz del proyecto detectada: {project_root}")
print(f"💾 Destino de archivos: {DATA_DIR}")
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_data():
    """Descarga datos históricos de Kraken"""
    print(f"⬇️ Descargando {LIMIT} velas de {SYMBOL}...")
    exchange = ccxt.kraken()
    try:
        bars = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=LIMIT)
        # Kraken devuelve: [timestamp, open, high, low, close, volume]
        df = pd.DataFrame(bars, columns=['ts', 'open', 'high', 'low', 'close', 'volume'])
        return df
    except Exception as e:
        print(f"❌ Error descargando datos: {e}")
        sys.exit(1)

def feature_engineering(df):
    """Calcula indicadores técnicos (Debe ser IDÉNTICO a src/brain.py)"""
    print("🧪 Calculando indicadores técnicos...")
    
    # 1. Indicadores
    df['rsi'] = df.ta.rsi(length=14)
    df['ema20'] = df.ta.ema(length=20)
    df['ema50'] = df.ta.ema(length=50)
    df['atr'] = df.ta.atr(length=14)
    
    df.dropna(inplace=True)
    
    # 2. Definir Target (Objetivo)
    # 1 si el precio sube en la siguiente vela, 0 si baja
    df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
    df.dropna(inplace=True)

    # 3. Seleccionar Features (Entradas)
    features = ['rsi', 'ema20', 'ema50', 'atr', 'close', 'volume']
    
    return df[features].values, df['target'].values

def train_pipeline():
    # A. OBTENCIÓN DE DATOS
    df = fetch_data()
    X, y = feature_engineering(df)

    # B. NORMALIZACIÓN (SCALER)
    print("⚖️ Normalizando datos (0 a 1)...")
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)
    
    # --- GUARDAR SCALER (CRÍTICO PARA LULA) ---
    scaler_path = os.path.join(DATA_DIR, 'scaler.pkl')
    joblib.dump(scaler, scaler_path)
    print(f"✅ Scaler guardado en: {scaler_path}")

    # C. ENTRENAMIENTO
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, shuffle=False)

    print("🧠 Entrenando Red Neuronal (TensorFlow)...")
    model = tf.keras.Sequential([
        tf.keras.Input(shape=(6,)), 
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(32, activation='relu'),
        tf.keras.layers.Dense(1, activation='sigmoid')
    ])

    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    model.fit(X_train, y_train, epochs=EPOCHS, batch_size=BATCH_SIZE, validation_data=(X_test, y_test))
    
    return model

def convert_to_rknn(tf_model):
    """Convierte el modelo de TensorFlow a formato NPU (Rockchip)"""
    print("\n🔄 INICIANDO CONVERSIÓN A NPU FOCUS...")
    
    # 1. Paso Intermedio: Keras -> ONNX
    onnx_path = os.path.join(DATA_DIR, f'{MODEL_NAME}.onnx')
    spec = (tf.TensorSpec((1, 6), tf.float32, name="input"),)
    
    model_proto, _ = tf2onnx.convert.from_keras(tf_model, input_signature=spec, opset=13)
    onnx.save(model_proto, onnx_path)
    print(f"✅ Modelo intermedio ONNX guardado: {onnx_path}")

    # 2. Paso Final: ONNX -> RKNN
    rknn_path = os.path.join(DATA_DIR, f'{MODEL_NAME}.rknn')
    
    try:
        from rknn.api import RKNN
        
        print("⚙️  Detectado rknn-toolkit2. Convirtiendo para RK3588...")
        rknn = RKNN(verbose=False)
        rknn.config(target_platform='rk3588')
        
        if rknn.load_onnx(model=onnx_path) != 0:
            print("❌ Error cargando ONNX en RKNN toolkit.")
            return

        # build(do_quantization=False) genera FP16 (Más preciso, recomendado para bots)
        if rknn.build(do_quantization=False) != 0:
            print("❌ Error construyendo modelo RKNN.")
            return

        if rknn.export_rknn(rknn_path) != 0:
            print("❌ Error exportando archivo final .rknn.")
            return

        print(f"\n🎉 ¡ÉXITO TOTAL! Cerebro generado en: {rknn_path}")
        print("👉 Ahora copia la carpeta 'data' completa a tu Orange Pi.")

    except ImportError:
        print("\n⚠️  ADVERTENCIA: Librería 'rknn-toolkit2' no encontrada.")
        print(f"   Se ha generado correctamente el archivo: {onnx_path}")
        print(f"   Y el escalador: {os.path.join(DATA_DIR, 'scaler.pkl')}")
        print("   ❌ Pero NO se pudo generar el .rknn final en este PC.")
        print("   👉 Necesitas ejecutar este script en un entorno con el toolkit de Rockchip instalado.")

if __name__ == "__main__":
    print("=== ENTRENADOR DE LULA (TRAINER) ===")
    model = train_pipeline()
    convert_to_rknn(model)