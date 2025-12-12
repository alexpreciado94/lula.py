import os
import sys
import numpy as np
import pandas as pd
import pandas_ta as ta
import ccxt
import yfinance as yf
import tensorflow as tf
import tf2onnx
import onnx
import joblib
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split

# --- RUTAS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(scripts_dir)

DATA_DIR = os.path.join(project_root, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# --- CAMBIO DE NOMBRE AQUÍ ---
MODEL_NAME = 'madness'
# -----------------------------

SYMBOL = 'XMR/USD'
LIMIT = 4000 
EPOCHS = 20
BATCH_SIZE = 32

print(f"📂 Raíz: {project_root}")
print(f"💾 Guardando 'madness' en: {DATA_DIR}")

def fetch_data_merged():
    """Descarga Cripto y SP500 y los fusiona"""
    print(f"⬇️ Descargando Cripto ({SYMBOL})...")
    kraken = ccxt.kraken()
    try:
        bars = kraken.fetch_ohlcv(SYMBOL, '1h', limit=LIMIT)
        df_crypto = pd.DataFrame(bars, columns=['ts', 'open', 'high', 'low', 'close', 'volume'])
        df_crypto['ts'] = pd.to_datetime(df_crypto['ts'], unit='ms')
        df_crypto.set_index('ts', inplace=True)
    except Exception as e:
        print(f"❌ Error descargando cripto: {e}")
        sys.exit(1)

    print(f"⬇️ Descargando S&P 500 (^GSPC)...")
    try:
        df_spx = yf.download("^GSPC", period="6mo", interval="1h", progress=False)
        if 'Close' in df_spx.columns:
            spx_close = df_spx['Close']
        else:
            spx_close = df_spx.iloc[:, 0] 
        spx_close.name = 'sp500'
    except Exception as e:
        print(f"⚠️ Error S&P 500: {e}. Usando datos sintéticos.")
        spx_close = df_crypto['close'] # Fallback

    print("🔄 Sincronizando Mercados (Merge)...")
    df_merged = df_crypto.join(spx_close, how='left')
    df_merged['sp500'] = df_merged['sp500'].ffill().bfill()
    
    return df_merged

def feature_engineering(df):
    print("🧪 Calculando indicadores Híbridos...")
    
    # Indicadores Cripto
    df['rsi'] = df.ta.rsi(close=df['close'], length=14)
    df['ema20'] = df.ta.ema(close=df['close'], length=20)
    df['atr'] = df.ta.atr(high=df['high'], low=df['low'], close=df['close'], length=14)
    
    # Indicadores Macro
    df['sp500_rsi'] = df.ta.rsi(close=df['sp500'], length=14)
    df['corr_spx'] = df['close'].rolling(24).corr(df['sp500'])

    df.dropna(inplace=True)
    df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
    df.dropna(inplace=True)

    features = ['rsi', 'ema20', 'atr', 'close', 'volume', 'sp500', 'sp500_rsi', 'corr_spx']
    return df[features].values, df['target'].values

def train_pipeline():
    df = fetch_data_merged()
    X, y = feature_engineering(df)

    print("⚖️ Normalizando...")
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)
    
    scaler_path = os.path.join(DATA_DIR, 'scaler.pkl')
    joblib.dump(scaler, scaler_path)
    print(f"✅ Scaler guardado en: {scaler_path}")

    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, shuffle=False)

    print(f"🧠 Entrenando Madness (Inputs: {X.shape[1]})...")
    model = tf.keras.Sequential([
        tf.keras.Input(shape=(8,)), 
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(32, activation='relu'),
        tf.keras.layers.Dense(1, activation='sigmoid')
    ])

    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    model.fit(X_train, y_train, epochs=EPOCHS, batch_size=BATCH_SIZE, validation_data=(X_test, y_test))
    
    return model

def convert_to_rknn(tf_model):
    print("\n🔄 CONVIRTIENDO A NPU (MADNESS)...")
    
    # 1. Keras -> ONNX
    onnx_path = os.path.join(DATA_DIR, f'{MODEL_NAME}.onnx')
    spec = (tf.TensorSpec((1, 8), tf.float32, name="input"),) # Input shape 8
    
    model_proto, _ = tf2onnx.convert.from_keras(tf_model, input_signature=spec, opset=13)
    onnx.save(model_proto, onnx_path)
    print(f"✅ Modelo ONNX: {onnx_path}")

    # 2. ONNX -> RKNN
    rknn_path = os.path.join(DATA_DIR, f'{MODEL_NAME}.rknn')
    
    try:
        from rknn.api import RKNN
        rknn = RKNN(verbose=False)
        rknn.config(target_platform='rk3588')
        
        if rknn.load_onnx(model=onnx_path) != 0: return
        if rknn.build(do_quantization=False) != 0: return
        if rknn.export_rknn(rknn_path) != 0: return

        print(f"\n🎉 ¡MADNESS GENERADO!: {rknn_path}")

    except ImportError:
        print("\n⚠️  RKNN Toolkit no detectado. Se generó 'madness.onnx'.")

if __name__ == "__main__":
    model = train_pipeline()
    convert_to_rknn(model)