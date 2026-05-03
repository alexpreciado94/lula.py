import os, ccxt, joblib, numpy as np, pandas as pd, tensorflow as tf, tf2onnx, yfinance as yf
import pandas_ta as ta
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split

# ==========================================
# CONFIGURACIÓN SINCRONIZADA v7.5
# ==========================================
# Añade aquí todas las monedas que quieras que tengan su propio scaler
# ==========================================
# CONFIGURACIÓN SYMBOLS v7.5 (16 ACTIVOS)
# ==========================================
SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "NEAR/USDT", "FET/USDT",
    "PENDLE/USDT", "RENDER/USDT", "SUI/USDT", "LINK/USDT", "AVAX/USDT",
    "POL/USDT", "XRP/USDT", "PEPE/USDT", "ADA/USDT", "DOT/USDT",
    "XMR/USDT"  # <--- Agregada para la Bóveda de Riqueza
]

TIME_STEPS = 10
EPOCHS = 50
FEATURES = ["returns", "rsi", "volatility", "rvol", "corr_spx", "dist_ema"]
INPUT_DIM = TIME_STEPS * len(FEATURES) # 60

# ==========================================
# 1. OBTENCIÓN DE DATOS
# ==========================================
def fetch_sp500():
    print("⬇️  Descargando S&P 500...")
    try:
        raw = yf.download("^GSPC", period="2y", interval="1h", progress=False)
        sp500 = raw["Close"] if "Close" in raw.columns else raw.iloc[:, 0]
        if isinstance(sp500, pd.DataFrame):
            sp500 = sp500.iloc[:, 0]
        sp500 = sp500.to_frame("sp500")
        if hasattr(sp500.index, "tz") and sp500.index.tz is not None:
            sp500.index = sp500.index.tz_localize(None)
        sp500.index = sp500.index.floor("h")
        print(f"   ✅ S&P 500: {len(sp500)} filas.")
        return sp500
    except Exception as e:
        print(f"   ⚠️  Fallo S&P 500 ({e}). Continuando sin macro.")
        return None

def fetch_crypto(symbol):
    print(f"⬇️  Descargando {symbol}...")
    try:
        ex = ccxt.binance()
        bars = ex.fetch_ohlcv(symbol, "1h", limit=5000)
        df = pd.DataFrame(bars, columns=["ts", "open", "high", "low", "close", "volume"])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")
        df.set_index("ts", inplace=True)
        df.index = df.index.floor("h")
        print(f"   ✅ {symbol}: {len(df)} velas.")
        return df
    except Exception as e:
        print(f"   ⚠️  Error {symbol}: {e}")
        return pd.DataFrame()

# ==========================================
# 2. FEATURE ENGINEERING (Sincronizado con Brain)
# ==========================================
def build_features(df, sp500):
    df["returns"] = np.log(df["close"] / df["close"].shift(1))
    df["rsi"] = df.ta.rsi(length=14) / 100.0
    atr = df.ta.atr(length=14)
    df["volatility"] = (atr / df["close"]).fillna(0)
    df["vol_sma"] = df["volume"].rolling(20).mean()
    df["rvol"] = (df["volume"] / df["vol_sma"]).fillna(1.0)
    df["ema200"] = df.ta.ema(length=200)
    df["dist_ema"] = ((df["close"] - df["ema200"]) / df["ema200"]).fillna(0)
    
    if sp500 is not None:
        df = df.join(sp500, how="left").ffill().bfill()
        df["corr_spx"] = df["close"].rolling(24).corr(df["sp500"]).fillna(0)
    else:
        df["corr_spx"] = 0.0

    # Target: subida del 0.5% en las próximas 4h
    df["target"] = (df["close"].shift(-4) > df["close"] * 1.005).astype(int)
    return df.dropna(subset=FEATURES + ["target"])

# ==========================================
# 3. PIPELINE DE ENTRENAMIENTO
# ==========================================
def run_pipeline():
    print("\n🚀 === LULA TRAINER v7.5 (MLP + MULTI-SCALER) ===\n")
    os.makedirs("data", exist_ok=True)
    sp500 = fetch_sp500()
    
    scalers_dict = {}
    all_X, all_y = [], []

    for sym in SYMBOLS:
        df = fetch_crypto(sym)
        if df.empty: continue
        df = build_features(df, sp500)
        
        # --- FIX: ESCALADOR INDEPENDIENTE POR MONEDA ---
        s = MinMaxScaler()
        scaled_data = s.fit_transform(df[FEATURES])
        scalers_dict[sym] = s # Guardamos en el diccionario
        
        target = df["target"].values
        for i in range(len(scaled_data) - TIME_STEPS):
            # Aplanamos la secuencia (10x6 = 60 inputs)
            all_X.append(scaled_data[i : i + TIME_STEPS].flatten())
            all_y.append(target[i + TIME_STEPS])

    # Guardar el diccionario de scalers
    joblib.dump(scalers_dict, "data/scaler.pkl")
    print(f"✅ Diccionario con {len(scalers_dict)} scalers guardado.")
    
    X, y = np.array(all_X), np.array(all_y)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, shuffle=False)

    # --- MODELO MLP COMPATIBLE CON RKNN ---
    inputs = tf.keras.Input(shape=(INPUT_DIM,), name="input")
    x = tf.keras.layers.Dense(128, activation="relu")(inputs)
    x = tf.keras.layers.Dropout(0.2)(x)
    x = tf.keras.layers.Dense(64, activation="relu")(x)
    x = tf.keras.layers.Dense(32, activation="relu")(x)
    outputs = tf.keras.layers.Dense(1, activation="sigmoid", name="output")(x)
    model = tf.keras.Model(inputs=inputs, outputs=outputs)

    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    
    print("\n🧠 Entrenando Red Neuronal...")
    model.fit(X_train, y_train, epochs=EPOCHS, batch_size=64, 
              validation_data=(X_test, y_test), verbose=1)

    # Exportación a ONNX
    print("\n🔄 Exportando a ONNX...")
    spec = (tf.TensorSpec((1, INPUT_DIM), tf.float32, name="input"),)
    tf2onnx.convert.from_keras(model, input_signature=spec, opset=11, output_path="data/madness.onnx")
    
    print("\n✨ PROCESO COMPLETADO ✨")
    print(f"Usa input_size_list=[[1, {INPUT_DIM}]] en el script de conversión RKNN.")

if __name__ == "__main__":
    run_pipeline()
