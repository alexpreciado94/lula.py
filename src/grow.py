"""
LULA GROW v7.0 — PROMETHEUS ARCHITECTURE (DEFINITIVO)
Optimizado para CNN-1D y NPU RK3588 (INT8 w8a8)
"""

import os, sys, time, json, joblib, ccxt
import numpy as np
import pandas as pd
import pandas_ta as ta
import yfinance as yf
from datetime import datetime
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.utils import class_weight

# Desactivar avisos de TensorFlow
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf

# ══════════════════════════════════════════════════════════════
#  CONFIGURACIÓN GLOBAL
# ══════════════════════════════════════════════════════════════
SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "NEAR/USDT", "FET/USDT",
    "PENDLE/USDT", "RENDER/USDT", "SUI/USDT", "LINK/USDT", "AVAX/USDT",
    "POL/USDT", "XRP/USDT", "PEPE/USDT", "ADA/USDT", "DOT/USDT",
    "XMR/USDT"  # <--- Agregada para la Bóveda de Riqueza
]
TIME_STEPS = 10 
# Features de alta fidelidad sincronizadas con brain.py
FEATURES = ["returns", "rsi", "volatility", "rvol", "corr_spx", "dist_ema"]
# Ruta absoluta para Docker

# Rutas relativas a la carpeta src (donde vive grow.py)
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"

# Asegurar que las carpetas existan
LOG_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "grow.log"

class C:
    G = "\033[38;5;82m"; RE = "\033[38;5;196m"; CY = "\033[38;5;51m"; R = "\033[0m"

def log(msg, col=C.CY):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    clean_msg = f"[{timestamp}] [GROW v7] {msg}"
    
    # Imprimir en consola con colores
    print(f"{col}[GROW v7]{C.R} {msg}")
    
    # Guardar en archivo (sin colores ANSI)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(clean_msg + "\n")
    except Exception as e:
        print(f"❌ Error escribiendo log: {e}")


# ══════════════════════════════════════════════════════════════
#  INGENIERÍA DE FEATURES (VOLATILITY ADAPTIVE)
# ══════════════════════════════════════════════════════════════
def prepare_dataframe(df, sp500_df=None):
    df = df.copy()
    df["returns"] = np.log(df["close"] / df["close"].shift(1))
    df["rsi"] = df.ta.rsi(length=14) / 100.0
    atr = df.ta.atr(length=14)
    df["volatility"] = (atr / df["close"]).fillna(0)
    df["rvol"] = (df["volume"] / df["volume"].rolling(20).mean()).fillna(1)
    ema200 = df.ta.ema(length=200)
    df["dist_ema"] = ((df["close"] - ema200) / ema200).fillna(0)

    # 1. Fallback Macro robusto contra NaNs
    if sp500_df is not None:
        df = df.join(sp500_df, how="left").ffill().bfill()
        df["corr_spx"] = df["close"].rolling(24).corr(df["sp500"]).fillna(0)
    else:
        df["corr_spx"] = 0.0

    # 2. TARGET MÁS REALISTA: 1.2 * ATR (Antes era 1.5, era muy difícil de alcanzar)
    future_max = df["close"].shift(-4).rolling(window=4).max()
    df["target"] = (future_max > (df["close"] + (atr * 1.2))).astype(int)

    return df.dropna(subset=FEATURES + ["target"])


# ══════════════════════════════════════════════════════════════
#  ARQUITECTURA CNN-1D (DETECTA FORMAS EN LA GRÁFICA)
# ══════════════════════════════════════════════════════════════
def build_model(input_shape):
    inputs = tf.keras.Input(shape=input_shape)
    x = tf.keras.layers.BatchNormalization()(inputs)
    
    # Capas Convolucionales para patrones temporales
    x = tf.keras.layers.Conv1D(64, kernel_size=3, padding="same", activation="swish")(x)
    x = tf.keras.layers.MaxPooling1D(pool_size=2)(x)
    x = tf.keras.layers.Conv1D(128, kernel_size=2, padding="same", activation="swish")(x)
    
    # FIX 1: GlobalMaxPooling1D en lugar de GlobalAveragePooling1D
    # Preserva los picos de activación que indican patrones de entrada.
    # El average aplana todo hacia el prior de clase y causa predicciones idénticas.
    x = tf.keras.layers.GlobalMaxPooling1D()(x)
    
    x = tf.keras.layers.Dense(64, activation="swish")(x)
    x = tf.keras.layers.Dropout(0.3)(x)
    outputs = tf.keras.layers.Dense(1, activation="sigmoid")(x)
    
    return tf.keras.Model(inputs, outputs)

# ══════════════════════════════════════════════════════════════
#  PROCESO DE ENTRENAMIENTO Y COMPILACIÓN NPU
# ══════════════════════════════════════════════════════════════
def run_training():
    # Asegurar que el directorio existe antes de empezar
    DATA_DIR.mkdir(parents=True, exist_ok=True) 

    log("🚀 Iniciando Reentrenamiento v7 (Convolutional Mode)...", C.G)
    
    # IMPORTANTE: Definimos 'ex' aquí arriba para que esté disponible en el fallback macro
    ex = ccxt.binance()

    # 1. Obtener Datos Macro (S&P 500 con Fallback a BTC Proxy)
    try:
        log("Intentando descargar datos macro S&P 500...")
        # Forzamos multi_level_index=False para evitar el error de DataFrame
        spx_raw = yf.download("^GSPC", period="2y", interval="1h", progress=False, multi_level_index=False)
        
        if spx_raw.empty: 
            raise Exception("Yahoo retornó DataFrame vacío")
        
        # Seleccionamos 'Close' de forma segura
        spx = pd.DataFrame(spx_raw['Close']).rename(columns={'Close': 'sp500'})
        spx.index = spx.index.tz_localize(None).floor("h")
        log("Macro S&P 500 cargada con éxito.", C.G)
        
    except Exception as e:
        log(f"⚠️ Error Yahoo Finance: {e}. Usando BTC como Proxy Macro...", C.RE)
        # FALLBACK: Ahora 'ex' ya existe, por lo que no dará UnboundLocalError
        bars_btc = ex.fetch_ohlcv("BTC/USDT", "1h", limit=5000)
        spx = pd.DataFrame(bars_btc, columns=["ts", "open", "high", "low", "close", "volume"])
        spx["ts"] = pd.to_datetime(spx["ts"], unit="ms")
        spx.set_index("ts", inplace=True)
        spx = spx[["close"]].rename(columns={"close": "sp500"})
        spx.index = spx.index.floor("h")

    # 2. Descargar Historial Cripto para el resto de símbolos
    all_dfs = []
    sym_names = []  # FIX 2: guardamos los nombres para el scaler por símbolo
    for sym in SYMBOLS:
        log(f"Descargando {sym}...")
        try:
            bars = ex.fetch_ohlcv(sym, "1h", limit=5000)
            df = pd.DataFrame(bars, columns=["ts", "open", "high", "low", "close", "volume"])
            df = prepare_dataframe(df, spx)
            all_dfs.append(df)
            sym_names.append(sym)
        except Exception as e:
            log(f"Error descargando {sym}: {e}", C.RE)
            continue

    # FIX 2: Scaler por símbolo en lugar de uno global.
    # Un scaler global aplana las diferencias entre activos muy distintos
    # (ej. NEAR volátil vs XRP plano) y la CNN no puede distinguirlos.
    scalers = {}
    for sym, df in zip(sym_names, all_dfs):
        sc = StandardScaler()
        sc.fit(df[FEATURES])
        scalers[sym] = sc
        log(f"Scaler ajustado para {sym}", C.CY)

    # Guardamos todos los scalers en un único archivo
    joblib.dump(scalers, DATA_DIR / "scaler.pkl")

    # 3. Crear Tensores 3D (Samples, Time, Features)
    X, y = [], []
    for sym, df in zip(sym_names, all_dfs):
        scaled_vals = scalers[sym].transform(df[FEATURES])
        target_vals = df["target"].values
        for i in range(len(scaled_vals) - TIME_STEPS):
            X.append(scaled_vals[i : i + TIME_STEPS])
            y.append(target_vals[i + TIME_STEPS])

    X, y = np.array(X), np.array(y)

    # FIX 3: Diagnóstico de balance de clases antes de entrenar.
    # Si el prior es muy bajo (< 5%) la red tenderá a colapsar aunque uses class_weight.
    counts = np.bincount(y)
    ratio = counts[1] / len(y) * 100
    log(f"Balance de clases — Negativas: {counts[0]} | Positivas: {counts[1]} | Prior: {ratio:.1f}%", C.G)
    if ratio < 5.0:
        log("⚠️  Prior muy bajo (<5%). Considera bajar el multiplicador ATR en el target.", C.RE)
    
    # 4. Compensar desbalance (darle peso a los aciertos de compra)
    weights = class_weight.compute_class_weight('balanced', classes=np.unique(y), y=y)
    class_weights = {0: weights[0], 1: weights[1]}
    
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.15, shuffle=True)

    # 5. Entrenamiento del Modelo
    model = build_model((TIME_STEPS, len(FEATURES)))
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss="binary_crossentropy", metrics=["accuracy"])
    
    log("Entrenando red neuronal convolucional...")
    model.fit(
        X_train, y_train, validation_data=(X_val, y_val),
        epochs=100, batch_size=64, verbose=0,
        class_weight=class_weights,
        callbacks=[tf.keras.callbacks.EarlyStopping(patience=12, restore_best_weights=True)]
    )

    # 6. Exportación ONNX con Batch Size Fijo (Solución al error unk__74)
    log("Exportando Cerebro a ONNX (Batch=1)...", C.G)
    # Nota: scaler.pkl ya fue guardado arriba (contiene el dict de scalers por símbolo)
    
    import tf2onnx
    # Fijamos el primer parámetro a 1 en lugar de None
    spec = (tf.TensorSpec((1, TIME_STEPS, len(FEATURES)), tf.float32, name="input"),)
    tf2onnx.convert.from_keras(model, input_signature=spec, output_path=str(DATA_DIR / "madness.onnx"))

    # 7. Compilación RKNN para NPU RK3588 (INT8)
    try:
        from rknn.api import RKNN
        import shutil
        rknn = RKNN()
        log("Compilando para NPU RK3588 (Toolkit 2.3.2)...")
        
        rknn.config(
            target_platform='rk3588', 
            quantized_dtype='w8a8',
            optimization_level=1 # Nivel 1 es seguro y estable
        )        
        
        # --- SOLUCIÓN PARA EL DATASET (Muestras Individuales) ---
        calib_dir = Path("calib_samples")
        if calib_dir.exists(): shutil.rmtree(calib_dir)
        calib_dir.mkdir()
        
        # Tomamos 32 muestras (suficiente para calibrar INT8)
        indices = np.random.choice(X_train.shape[0], 32, replace=False)
        with open("dataset.txt", "w") as f:
            for i, idx in enumerate(indices):
                sample = X_train[idx].reshape(1, TIME_STEPS, len(FEATURES)).astype(np.float32)
                sample_path = calib_dir / f"sample_{i}.npy"
                np.save(sample_path, sample)
                f.write(f"{sample_path}\n") # Escribimos la ruta de cada archivo individual
        
        log(f"Grafo RKNN con 32 muestras de calibración...")
        
        # Carga del ONNX
        if rknn.load_onnx(model=str(DATA_DIR / "madness.onnx"),
                          inputs=['input'],
                          input_size_list=[[1, TIME_STEPS, len(FEATURES)]]) == 0:
            
            if rknn.build(do_quantization=True, dataset="dataset.txt") == 0:
                rknn.export_rknn(str(DATA_DIR / "madness.rknn"))
                log("🧠 CEREBRO V7 INSTALADO CON ÉXITO EN NPU.", C.G)
            else:
                log("Error en fase Build RKNN.", C.RE)
        else:
            log("Error cargando el archivo ONNX.", C.RE)
            
    except Exception as e:
        log(f"Fallo en compilación NPU: {e}", C.RE)


if __name__ == "__main__":
    run_training()