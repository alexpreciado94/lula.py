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
# El script está en: lula_project/scripts/trainer/trainer.py
# Queremos llegar a: lula_project/data

current_dir = os.path.dirname(os.path.abspath(__file__)) # .../trainer
scripts_dir = os.path.dirname(current_dir)               # .../scripts
project_root = os.path.dirname(scripts_dir)              # .../lula_project (RAÍZ)

DATA_DIR = os.path.join(project_root, 'data')
MODEL_NAME = 'cerebro'

# --- CONFIGURACIÓN DE ENTRENAMIENTO ---
SYMBOL = 'XMR/USD'      
TIMEFRAME = '1h'
LIMIT = 2000            
EPOCHS = 20             
BATCH_SIZE = 32

print(f"📂 Raíz del proyecto: {project_root}")
print(f"💾 Los archivos se guardarán en: {DATA_DIR}")
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_data():
    print(f"⬇️ Descargando {LIMIT} velas de {SYMBOL} desde Kraken...")
    exchange = ccxt.kraken()
    try:
        bars = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=LIMIT)
        df = pd.DataFrame(bars, columns=['ts', 'open', 'high', 'low', 'close', 'volume'])
        return df
    except Exception as e:
        print(f"❌ Error descargando datos: {e}")
        sys.exit(1)

def process_data(df):
    print("🧪 Feature Engineering (Calculando indicadores)...")
    
    # INDICADORES (Deben coincidir exactamente con src/brain.py)
    df['rsi'] = df.ta.rsi(length=14)
    df['ema20'] = df.ta.ema(length=20)
    df['ema50'] = df.ta.ema(length=50)
    df['atr'] = df.ta.atr(length=14)
    
    df.dropna(inplace=True)
    
    # Target: 1 si el precio sube en la siguiente vela
    df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
    df.dropna(inplace=True)

    features = ['rsi', 'ema20', 'ema50', 'atr', 'close', 'volume']
    return df[features].values, df['target'].values

def train_model():
    df = fetch_data()
    X, y = process_data(df)

    print("⚖️ Normalizando datos...")
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Guardar Scaler
    scaler_path = os.path.join(DATA_DIR, 'scaler.pkl')
    joblib.dump(scaler, scaler_path)
    print(f"✅ Scaler guardado en: {scaler_path}")

    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, shuffle=False)

    print("🧠 Construyendo Modelo TensorFlow...")
    model = tf.keras.Sequential([
        tf.keras.Input(shape=(6,)), 
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(32, activation='relu'),
        tf.keras.layers.Dense(1, activation='sigmoid')
    ])

    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

    print("🏃 Entrenando...")
    model.fit(X_train, y_train, epochs=EPOCHS, batch_size=BATCH_SIZE, validation_data=(X_test, y_test))

    return model

def export_to_rknn(tf_model):
    print("\n🔄 Iniciando Conversión a NPU (RK3588)...")
    
    # A) Keras -> ONNX
    onnx_path = os.path.join(DATA_DIR, f'{MODEL_NAME}.onnx')
    spec = (tf.TensorSpec((1, 6), tf.float32, name="input"),)
    model_proto, _ = tf2onnx.convert.from_keras(tf_model, input_signature=spec, opset=13)
    onnx.save(model_proto, onnx_path)
    print(f"✅ Modelo ONNX guardado: {onnx_path}")

    # B) ONNX -> RKNN
    rknn_path = os.path.join(DATA_DIR, f'{MODEL_NAME}.rknn')
    
    try:
        from rknn.api import RKNN
        
        rknn = RKNN(verbose=False)
        rknn.config(target_platform='rk3588')
        
        print("--> Cargando ONNX...")
        if rknn.load_onnx(model=onnx_path) != 0:
            print('Error cargando ONNX')
            return

        print("--> Construyendo RKNN...")
        if rknn.build(do_quantization=False) != 0:
            print('Error building RKNN')
            return

        print(f"--> Exportando {rknn_path}...")
        if rknn.export_rknn(rknn_path) != 0:
            print('Error exporting RKNN')
            return

        print(f"\n🎉 ¡ÉXITO! Cerebro generado: {rknn_path}")
        
    except ImportError:
        print("\n⚠️  AVISO: Librería 'rknn-toolkit2' no detectada.")
        print(f"   Se ha generado el archivo .onnx en: {onnx_path}")
        print("   Puedes convertirlo a .rknn en otro entorno si este falla.")

if __name__ == "__main__":
    model = train_model()
    export_to_rknn(model)