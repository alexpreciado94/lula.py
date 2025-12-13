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

# ==========================================
# CONFIGURACIÓN
# ==========================================
MODEL_NAME = 'madness'   # Nombre del cerebro
SYMBOL = 'XMR/USD'       # Moneda base para aprender (Monero)
TIMEFRAME = '1h'
LIMIT = 4000             # Horas de historia
EPOCHS = 30              # Épocas de entrenamiento
BATCH_SIZE = 32

# Rutas dinámicas (para guardar en lula_project/data/)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
DATA_DIR = os.path.join(project_root, 'data')

os.makedirs(DATA_DIR, exist_ok=True)
print(f"📂 Raíz del proyecto: {project_root}")
print(f"💾 Guardando archivos en: {DATA_DIR}")

# ==========================================
# 1. DESCARGA DE DATOS HÍBRIDOS
# ==========================================
def fetch_merged_data():
    print(f"⬇️  Descargando Cripto ({SYMBOL}) desde Kraken...")
    kraken = ccxt.kraken()
    try:
        bars = kraken.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=LIMIT)
        df = pd.DataFrame(bars, columns=['ts', 'open', 'high', 'low', 'close', 'volume'])
        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        df.set_index('ts', inplace=True)
    except Exception as e:
        print(f"❌ Error descargando Kraken: {e}")
        sys.exit(1)

    print(f"⬇️  Descargando S&P 500 (^GSPC) desde Yahoo...")
    try:
        # Bajamos datos de bolsa para correlación
        spx = yf.download("^GSPC", period="6mo", interval="1h", progress=False)
        
        # Corrección para versiones nuevas de yfinance (MultiIndex)
        if hasattr(spx.columns, 'nlevels') and spx.columns.nlevels > 1:
            spx_close = spx.xs('Close', axis=1, level=0).iloc[:, 0]
        elif 'Close' in spx.columns:
            spx_close = spx['Close']
        else:
            spx_close = spx.iloc[:, 0]
        
        spx_close.name = 'sp500'
    except Exception as e:
        print(f"⚠️ Error Yahoo Finance: {e}. Usando datos sintéticos.")
        spx_close = df['close'] # Fallback

    print("🔄 Fusionando Mercados (Merge)...")
    # Unir datos. Usamos 'left' para mantener el índice horario de Cripto (24/7)
    df_merged = df.join(spx_close, how='left')
    # Rellenar fines de semana de bolsa con el último precio conocido
    df_merged['sp500'] = df_merged['sp500'].ffill().bfill()
    
    return df_merged

# ==========================================
# 2. INGENIERÍA DE CARACTERÍSTICAS (Features)
# ==========================================
def feature_engineering(df):
    print("🧪 Calculando Indicadores (Técnico + VOLUMEN + Macro)...")
    
    # --- A. TÉCNICO BÁSICO ---
    df['rsi'] = df.ta.rsi(close=df['close'], length=14)
    df['ema20'] = df.ta.ema(close=df['close'], length=20)
    df['atr'] = df.ta.atr(high=df['high'], low=df['low'], close=df['close'], length=14)
    
    # --- B. VOLUMEN (Detectando Ballenas/Squeezes) ---
    # OBV: Presión acumulada de compra/venta
    df['obv'] = df.ta.obv(close=df['close'], volume=df['volume'])
    # MFI: Como el RSI pero usando volumen
    df['mfi'] = df.ta.mfi(high=df['high'], low=df['low'], close=df['close'], volume=df['volume'], length=14)
    # RVOL: Volumen Relativo (Volumen hoy vs Media 20 días)
    df['vol_sma'] = df['volume'].rolling(20).mean()
    df['rvol'] = df['volume'] / df['vol_sma']

    # --- C. MACROECONOMÍA ---
    # Correlación de 24h con el S&P 500
    df['corr_spx'] = df['close'].rolling(24).corr(df['sp500'])

    # Limpieza de NaN generados por indicadores
    df.fillna(method='bfill', inplace=True)
    df.dropna(inplace=True)

    # --- DEFINIR TARGET (OBJETIVO) ---
    # 1 si el precio sube en la próxima vela, 0 si baja
    df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
    df.dropna(inplace=True)

    # --- SELECCIÓN FINAL DE FEATURES ---
    # IMPORTANTE: Este orden debe ser IDÉNTICO en brain.py
    features_list = [
        'rsi', 'ema20', 'atr',          # Técnico
        'obv', 'mfi', 'rvol',           # Volumen
        'close', 'sp500', 'corr_spx'    # Precio/Macro
    ]
    
    print(f"📊 Entrenando con {len(features_list)} variables de entrada.")
    return df[features_list].values, df['target'].values, len(features_list)

# ==========================================
# 3. PIPELINE DE ENTRENAMIENTO
# ==========================================
def train_pipeline():
    df = fetch_merged_data()
    X, y, input_dim = feature_engineering(df)

    print("⚖️  Normalizando datos (Scaler)...")
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)
    
    # GUARDAR SCALER (Vital para la Orange Pi)
    scaler_path = os.path.join(DATA_DIR, 'scaler.pkl')
    joblib.dump(scaler, scaler_path)
    print(f"✅ Scaler guardado: {scaler_path}")

    # Separar Train/Test
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, shuffle=False)

    print("🧠 Construyendo Red Neuronal (TensorFlow)...")
    model = tf.keras.Sequential([
        tf.keras.Input(shape=(input_dim,)), 
        
        # Capas densas con Dropout para evitar memorización
        tf.keras.layers.Dense(128, activation='relu'),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(32, activation='relu'),
        
        # Salida binaria (0 o 1)
        tf.keras.layers.Dense(1, activation='sigmoid')
    ])

    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    
    print("🏃 Iniciando entrenamiento...")
    model.fit(X_train, y_train, epochs=EPOCHS, batch_size=BATCH_SIZE, validation_data=(X_test, y_test))
    
    return model, input_dim

# ==========================================
# 4. CONVERSIÓN A RKNN (NPU)
# ==========================================
def convert_to_rknn(tf_model, input_dim):
    print("\n🔄 EXPORTANDO MODELO...")
    
    # A) Keras -> ONNX
    onnx_path = os.path.join(DATA_DIR, f'{MODEL_NAME}.onnx')
    spec = (tf.TensorSpec((1, input_dim), tf.float32, name="input"),)
    
    model_proto, _ = tf2onnx.convert.from_keras(tf_model, input_signature=spec, opset=13)
    onnx.save(model_proto, onnx_path)
    print(f"✅ Modelo ONNX guardado: {onnx_path}")

    # B) ONNX -> RKNN
    rknn_path = os.path.join(DATA_DIR, f'{MODEL_NAME}.rknn')
    
    try:
        from rknn.api import RKNN
        print("⚙️  Toolkit detectado. Convirtiendo a formato RK3588...")
        
        rknn = RKNN(verbose=False)
        rknn.config(target_platform='rk3588')
        
        if rknn.load_onnx(model=onnx_path) != 0:
            print("❌ Error cargando ONNX.")
            return

        # FP16 para equilibrio precisión/velocidad
        if rknn.build(do_quantization=False) != 0:
            print("❌ Error construyendo RKNN.")
            return

        if rknn.export_rknn(rknn_path) != 0:
            print("❌ Error exportando RKNN.")
            return

        print(f"\n🎉 ¡MADNESS GENERADO CON ÉXITO! : {rknn_path}")

    except ImportError:
        print("\n⚠️  ADVERTENCIA: 'rknn-toolkit2' no encontrado en este PC.")
        print(f"   Se ha generado el archivo intermedio: {onnx_path}")
        print("   👉 Opción Docker: Usa el comando 'docker run' de Rockchip para convertir el .onnx a .rknn")

if __name__ == "__main__":
    print("=== LULA TRAINER (Volumen + Macro Edition) ===")
    trained_model, inputs = train_pipeline()
    convert_to_rknn(trained_model, inputs)