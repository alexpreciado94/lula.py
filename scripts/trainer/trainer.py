import os
import sys

import ccxt
import joblib
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
LIMIT = 4000
EPOCHS = 30
BATCH_SIZE = 32

# Rutas dinámicas
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
DATA_DIR = os.path.join(project_root, "data")

os.makedirs(DATA_DIR, exist_ok=True)
print(f"📂 Raíz del proyecto: {project_root}")
print(f"💾 Guardando archivos en: {DATA_DIR}")


def fetch_merged_data():
    print(f"⬇️  Descargando Cripto ({SYMBOL}) desde Kraken...")
    kraken = ccxt.kraken()
    try:
        bars = kraken.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=LIMIT)
        df = pd.DataFrame(bars, columns=["ts", "open", "high", "low", "close", "volume"])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")
        df.set_index("ts", inplace=True)
    except Exception as e:
        print(f"❌ Error descargando Kraken: {e}")
        sys.exit(1)

    print("⬇️  Descargando S&P 500 (^GSPC) desde Yahoo...")
    try:
        spx = yf.download("^GSPC", period="6mo", interval="1h", progress=False)
        if hasattr(spx.columns, "nlevels") and spx.columns.nlevels > 1:
            spx_close = spx.xs("Close", axis=1, level=0).iloc[:, 0]
        elif "Close" in spx.columns:
            spx_close = spx["Close"]
        else:
            spx_close = spx.iloc[:, 0]
        spx_close.name = "sp500"
    except Exception as e:
        print(f"⚠️ Error Yahoo Finance: {e}. Usando datos sintéticos.")
        spx_close = df["close"]

    print("🔄 Fusionando Mercados (Merge)...")
    df_merged = df.join(spx_close, how="left")
    df_merged["sp500"] = df_merged["sp500"].ffill().bfill()
    return df_merged


def feature_engineering(df):
    print("🧪 Calculando Indicadores (Técnico + VOLUMEN + Macro)...")
    df["rsi"] = df.ta.rsi(close=df["close"], length=14)
    df["ema20"] = df.ta.ema(close=df["close"], length=20)
    df["atr"] = df.ta.atr(high=df["high"], low=df["low"], close=df["close"], length=14)

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

    df["corr_spx"] = df["close"].rolling(24).corr(df["sp500"])

    df.fillna(method="bfill", inplace=True)
    df.dropna(inplace=True)

    df["target"] = (df["close"].shift(-1) > df["close"]).astype(int)
    df.dropna(inplace=True)

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
    print(f"📊 Entrenando con {len(features_list)} variables de entrada.")
    return df[features_list].values, df["target"].values, len(features_list)


def train_pipeline():
    df = fetch_merged_data()
    X, y, input_dim = feature_engineering(df)

    print("⚖️  Normalizando datos (Scaler)...")
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)
    scaler_path = os.path.join(DATA_DIR, "scaler.pkl")
    joblib.dump(scaler, scaler_path)
    print(f"✅ Scaler guardado: {scaler_path}")

    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, shuffle=False)

    print("🧠 Construyendo Red Neuronal (TensorFlow)...")
    model = tf.keras.Sequential(
        [
            tf.keras.Input(shape=(input_dim,)),
            tf.keras.layers.Dense(128, activation="relu"),
            tf.keras.layers.Dropout(0.3),
            tf.keras.layers.Dense(64, activation="relu"),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(32, activation="relu"),
            tf.keras.layers.Dense(1, activation="sigmoid"),
        ]
    )

    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    print("🏃 Iniciando entrenamiento...")
    model.fit(
        X_train,
        y_train,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        validation_data=(X_test, y_test),
    )
    return model, input_dim


def convert_to_rknn(tf_model, input_dim):
    print("\n🔄 EXPORTANDO MODELO...")
    onnx_path = os.path.join(DATA_DIR, f"{MODEL_NAME}.onnx")
    spec = (tf.TensorSpec((1, input_dim), tf.float32, name="input"),)
    model_proto, _ = tf2onnx.convert.from_keras(tf_model, input_signature=spec, opset=13)
    # Importante: usar tf2onnx.utils para guardar o directamente onnx
    import onnx

    onnx.save(model_proto, onnx_path)
    print(f"✅ Modelo ONNX guardado: {onnx_path}")

    rknn_path = os.path.join(DATA_DIR, f"{MODEL_NAME}.rknn")
    try:
        from rknn.api import RKNN

        print("⚙️  Toolkit detectado. Convirtiendo a formato RK3588...")
        rknn = RKNN(verbose=False)
        rknn.config(target_platform="rk3588")
        if rknn.load_onnx(model=onnx_path) != 0:
            print("❌ Error cargando ONNX.")
            return
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
        print("   👉 Opción Docker: Convierte el .onnx a .rknn manualmente")


if __name__ == "__main__":
    print("=== LULA TRAINER (Volumen + Macro Edition) ===")
    trained_model, inputs = train_pipeline()
    convert_to_rknn(trained_model, inputs)
