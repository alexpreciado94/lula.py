import os
import sys

import ccxt
import joblib
import numpy as np
import onnx
import pandas as pd
import pandas_ta as ta  # noqa: F401
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
# 1. OBTENCIÓN DE DATOS
# ==========================================
def fetch_merged_data():
    print(f"⬇️  Descargando datos ({SYMBOL} + SP500)...")
    kraken = ccxt.kraken()
    try:
        bars = kraken.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=LIMIT)
        df = pd.DataFrame(bars, columns=["ts", "open", "high", "low", "close", "volume"])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")
        df.set_index("ts", inplace=True)
    except Exception as e:
        print(f"❌ Error Kraken: {e}")
        sys.exit(1)

    try:
        spx = yf.download("^GSPC", period="6mo", interval="1h", progress=False)
        if hasattr(spx.columns, "nlevels") and spx.columns.nlevels > 1:
            spx_close = spx.xs("Close", axis=1, level=0).iloc[:, 0]
        elif "Close" in spx.columns:
            spx_close = spx["Close"]
        else:
            spx_close = spx.iloc[:, 0]
        spx_close.name = "sp500"
    except Exception:
        print("⚠️ Fallo Yahoo. Usando fallback.")
        spx_close = df["close"]

    df = df.join(spx_close, how="left")
    df["sp500"] = df["sp500"].ffill().bfill()
    return df


# ==========================================
# 2. CARACTERÍSTICAS
# ==========================================
def feature_engineering(df):
    print("🧪 Calculando indicadores...")

    # Técnico
    df["rsi"] = df.ta.rsi(close=df["close"], length=14)
    df["ema20"] = df.ta.ema(close=df["close"], length=20)
    df["atr"] = df.ta.atr(high=df["high"], low=df["low"], close=df["close"], length=14)

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

    df.fillna(method="bfill", inplace=True)
    df.dropna(inplace=True)

    # Definir Target (Predicción a 1 hora)
    df["target"] = (df["close"].shift(-1) > df["close"]).astype(int)
    df.dropna(inplace=True)

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
    """
    Transforma los datos planos en bloques de tiempo (3D Array).
    De [Filas, Features] pasamos a [Muestras, TimeSteps, Features]
    """
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

    # Separar Train/Test (sin barajar para mantener orden temporal)
    X_train, X_test, y_train, y_test = train_test_split(X_seq, y_seq, test_size=0.2, shuffle=False)

    print(f"🧠 Construyendo LSTM (Input: {TIME_STEPS}x{input_dim})...")

    # --- ARQUITECTURA LSTM ---
    model = tf.keras.Sequential(
        [
            # Capa de entrada explícita: (Tiempo, Características)
            tf.keras.Input(shape=(TIME_STEPS, input_dim)),
            # Capa LSTM: Aprende patrones temporales
            tf.keras.layers.LSTM(64, return_sequences=False),
            tf.keras.layers.Dropout(0.3),
            # Capas Densas para decisión final
            tf.keras.layers.Dense(32, activation="relu"),
            tf.keras.layers.Dense(1, activation="sigmoid"),
        ]
    )

    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])

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

    onnx_path = os.path.join(DATA_DIR, f"{MODEL_NAME}.onnx")

    # Firma de entrada actualizada: (1, TIME_STEPS, FEATURES)
    spec = (tf.TensorSpec((1, TIME_STEPS, input_dim), tf.float32, name="input"),)

    model_proto, _ = tf2onnx.convert.from_keras(tf_model, input_signature=spec, opset=13)
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

        # Importante: force_builtin_perm=True ayuda con capas LSTM en algunos casos
        if rknn.build(do_quantization=False) != 0:
            print("❌ Error build RKNN")
            return
        if rknn.export_rknn(rknn_path) != 0:
            print("❌ Error export RKNN")
            return

        print(f"\n🎉 ¡MADNESS (Memory Edition) GENERADO!: {rknn_path}")

    except ImportError:
        print("\n⚠️  Toolkit no encontrado. Usa Docker para convertir el .onnx")


if __name__ == "__main__":
    print("=== LULA TRAINER (LSTM Memory Edition) ===")
    model, features = train_pipeline()
    convert_to_rknn(model, features)
