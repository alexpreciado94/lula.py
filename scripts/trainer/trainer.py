import os
import sys

import ccxt
import joblib
import numpy as np
import onnx
import pandas as pd

# --- GESTIÓN DE IMPORTACIÓN DE PANDAS_TA ---
try:
    import pandas_ta as ta
except ImportError:
    import pandas_ta_classic as ta  # noqa: F401

import tensorflow as tf
import tf2onnx
import yfinance as yf
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler

# ==========================================
# CONFIGURACIÓN
# ==========================================
MODEL_NAME = "madness"
SYMBOL = "XMR/USD"
TIMEFRAME = "1h"
LIMIT = 5000
EPOCHS = 35
BATCH_SIZE = 32
TIME_STEPS = 10

# Rutas
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
DATA_DIR = os.path.join(project_root, "data")
os.makedirs(DATA_DIR, exist_ok=True)

print(f"📂 Raíz: {project_root}")
print(f"🧠 Memoria de la IA: {TIME_STEPS} horas")


# ==========================================
# 1. OBTENCIÓN DE DATOS (ROBUSTA)
# ==========================================
def fetch_merged_data():
    print(f"⬇️  Descargando datos ({SYMBOL})...")
    kraken = ccxt.kraken()
    try:
        bars = kraken.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=LIMIT)
        df = pd.DataFrame(bars, columns=["ts", "open", "high", "low", "close", "volume"])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")
        df.set_index("ts", inplace=True)
        
        # Limpieza inicial de zona horaria
        if df.index.tz is not None:
            df.index = df.index.tz_convert(None)
            
    except Exception as e:
        print(f"❌ Error Kraken: {e}")
        sys.exit(1)

    print("⬇️  Intentando descargar S&P 500...")
    spx_close = None
    try:
        # Descargamos periodo amplio para asegurar coincidencias
        spx = yf.download("^GSPC", period="2y", interval="1h", progress=False)
        
        if not spx.empty:
            # Extracción segura de la columna Close
            if hasattr(spx.columns, "nlevels") and spx.columns.nlevels > 1:
                spx_close = spx.xs("Close", axis=1, level=0).iloc[:, 0]
            elif "Close" in spx.columns:
                spx_close = spx["Close"]
            else:
                spx_close = spx.iloc[:, 0]
            
            spx_close.name = "sp500"
            # Eliminar zona horaria para coincidir con Kraken
            if spx_close.index.tz is not None:
                spx_close.index = spx_close.index.tz_convert(None)

    except Exception as e:
        print(f"⚠️ Fallo Yahoo ({e}).")

    # Fusión
    if spx_close is not None:
        df = df.join(spx_close, how="left")
    else:
        df["sp500"] = np.nan

    # Rellenar huecos
    df["sp500"] = df["sp500"].ffill()
    df["sp500"] = df["sp500"].bfill()

    # --- SALVAVIDAS FINAL ---
    # Si después de todo la columna sigue vacía (por fechas no coincidentes),
    # usamos el precio de cierre como dato sintético para no romper la IA.
    if df["sp500"].isnull().all():
        print("⚠️ AVISO: S&P 500 no sincronizó. Usando fallback (Close Price).")
        df["sp500"] = df["close"]

    print(f"✅ Datos listos: {len(df)} filas.")
    return df


# ==========================================
# 2. CARACTERÍSTICAS
# ==========================================
def feature_engineering(df):
    print("🧪 Calculando indicadores...")
    
    # Copia para evitar advertencias de pandas
    df = df.copy()

    # Técnico
    df["rsi"] = df.ta.rsi(close=df["close"], length=14)
    df["ema20"] = df.ta.ema(close=df["close"], length=20)
    df["atr"] = df.ta.atr(
        high=df["high"], low=df["low"], close=df["close"], length=14
    )

    # Volumen
    df["obv"] = df.ta.obv(close=df["close"], volume=df["volume"])
    df["mfi"] = df.ta.mfi(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        volume=df["volume"],
        length=14,
    )
    df["vol_sma"] = df["volume"].rolling(20).mean()
    df["rvol"] = df["volume"] / df["vol_sma"]

    # Macro
    df["corr_spx"] = df["close"].rolling(24).corr(df["sp500"])

    # Limpieza de NaN
    df = df.ffill().bfill()
    df.dropna(inplace=True)

    # Definir Target
    df["target"] = (df["close"].shift(-1) > df["close"]).astype(int)
    df.dropna(inplace=True)

    # CHECK DE SEGURIDAD
    if len(df) == 0:
        print("❌ ERROR CRÍTICO: 0 datos tras limpieza.")
        sys.exit(1)

    # LISTA DE FEATURES (9 ENTRADAS)
    features_list = [
        "rsi",
        "ema20",
        "atr",
        "obv",
        "mfi",
        "rvol",
        "close",
        "sp500",
        "corr_spx",
    ]

    return df[features_list].values, df["target"].values, len(features_list)


# ==========================================
# 3. CREACIÓN DE SECUENCIAS (MEMORIA)
# ==========================================
def create_sequences(data, target, time_steps):
    Xs, ys = [], []
    for i in range(len(data) - time_steps):
        Xs.append(data[i : (i + time_steps)])
        ys.append(target[i + time_steps])
    return np.array(Xs), np.array(ys)


# ==========================================
# 4. ENTRENAMIENTO
# ==========================================
def train_pipeline():
    df = fetch_merged_data()
    X, y, input_dim = feature_engineering(df)

    print("⚖️  Normalizando...")
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)
    joblib.dump(scaler, os.path.join(DATA_DIR, "scaler.pkl"))

    print(f"🎞️ Generando secuencias de {TIME_STEPS} pasos...")
    X_seq, y_seq = create_sequences(X_scaled, y, TIME_STEPS)

    if len(X_seq) == 0:
        print("❌ Error: No hay secuencias suficientes.")
        sys.exit(1)

    X_train, X_test, y_train, y_test = train_test_split(
        X_seq, y_seq, test_size=0.2, shuffle=False
    )

    print(f"🧠 Construyendo LSTM (Input: {TIME_STEPS}x{input_dim})...")

    model = tf.keras.Sequential(
        [
            tf.keras.Input(shape=(TIME_STEPS, input_dim)),
            tf.keras.layers.LSTM(64, return_sequences=False),
            tf.keras.layers.Dropout(0.3),
            tf.keras.layers.Dense(32, activation="relu"),
            tf.keras.layers.Dense(1, activation="sigmoid"),
        ]
    )

    model.compile(
        optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"]
    )

    print("🏃 Entrenando...")
    model.fit(
        X_train,
        y_train,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        validation_data=(X_test, y_test),
    )

    return model, input_dim


# ==========================================
# 5. EXPORTACIÓN A RKNN
# ==========================================
def convert_to_rknn(tf_model, input_dim):
    print("\n🔄 EXPORTANDO MODELO...")

    # --- FIX KERAS 3 ---
    if not hasattr(tf_model, "output_names"):
        if isinstance(tf_model.layers[-1].output, list):
             tf_model.output_names = [f"output_{i}" for i in range(len(tf_model.layers[-1].output))]
        else:
             tf_model.output_names = ["output_0"]

    onnx_path = os.path.join(DATA_DIR, f"{MODEL_NAME}.onnx")
    spec = (tf.TensorSpec((1, TIME_STEPS, input_dim), tf.float32, name="input"),)

    model_proto, _ = tf2onnx.convert.from_keras(
        tf_model, input_signature=spec, opset=13
    )
    import onnx
    onnx.save(model_proto, onnx_path)
    print(f"✅ Modelo ONNX guardado: {onnx_path}")

    rknn_path = os.path.join(DATA_DIR, f"{MODEL_NAME}.rknn")

    try:
        from rknn.api import RKNN

        print("⚙️  Toolkit detectado. Convirtiendo...")
        rknn = RKNN(verbose=False)
        rknn.config(target_platform="rk3588")

        if rknn.load_onnx(model=onnx_path) != 0:
            print("❌ Error cargar ONNX")
            return
        if rknn.build(do_quantization=False) != 0:
            print("❌ Error build RKNN")
            return
        if rknn.export_rknn(rknn_path) != 0:
            print("❌ Error export RKNN")
            return

        print(f"\n🎉 ¡MADNESS (Memory Edition) GENERADO!: {rknn_path}")

    except ImportError:
        print("\n⚠️  Toolkit RKNN no encontrado en este PC.")
        print(f"   Se ha generado el archivo intermedio: {onnx_path}")
        print("   👉 Como estás en Mac, usa el comando Docker para convertir a .rknn")


if __name__ == "__main__":
    print("=== LULA TRAINER (LSTM Memory Edition) ===")
    model, features = train_pipeline()
    convert_to_rknn(model, features)