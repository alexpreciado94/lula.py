import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import tensorflow as tf
import tf2onnx
import onnx
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler

# ==========================================
# 1. CONFIGURACIÓN Y DATOS
# ==========================================
print("⬇️ Descargando datos de Binance...")
exchange = ccxt.binance()
# Bajamos muchas velas para que aprenda bien
bars = exchange.fetch_ohlcv('BTC/USDT', timeframe='1h', limit=2000)
df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

# ==========================================
# 2. INGENIERÍA DE CARACTERÍSTICAS (Features)
# ==========================================
# NOTA: Estos indicadores deben ser IDÉNTICOS en lula.py
df['rsi'] = df.ta.rsi(length=14)
df['ema20'] = df.ta.ema(length=20)
df['ema50'] = df.ta.ema(length=50)
df['atr'] = df.ta.atr(length=14)
df.dropna(inplace=True) # Borrar nulos

# Definir el objetivo (Target): 1 si el precio sube, 0 si baja
df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
df.dropna(inplace=True)

# Seleccionar columnas de entrada
features = ['rsi', 'ema20', 'ema50', 'atr', 'close', 'volume']
X = df[features].values
y = df['target'].values

# ==========================================
# 3. NORMALIZACIÓN (Vital para IA)
# ==========================================
scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X)

# GUARDAR EL ESCALADOR (Muy importante)
# Lula lo necesita para entender los precios en vivo
joblib.dump(scaler, 'scaler.pkl')
print("✅ Escalador guardado como 'scaler.pkl'")

# Separar Test y Train
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, shuffle=False)

# ==========================================
# 4. DISEÑO DE LA RED NEURONAL
# ==========================================
model = tf.keras.Sequential([
    # Entrada: 6 neuronas (porque tenemos 6 features)
    tf.keras.Input(shape=(6,)), 
    tf.keras.layers.Dense(64, activation='relu'),
    tf.keras.layers.Dropout(0.2),
    tf.keras.layers.Dense(32, activation='relu'),
    # Salida: 1 neurona (Probabilidad 0 a 1)
    tf.keras.layers.Dense(1, activation='sigmoid')
])

model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

# ==========================================
# 5. ENTRENAMIENTO
# ==========================================
print("🧠 Entrenando cerebro...")
model.fit(X_train, y_train, epochs=20, batch_size=32, validation_data=(X_test, y_test))

# ==========================================
# 6. EXPORTACIÓN PARA NPU (ONNX)
# ==========================================
print("🔄 Convirtiendo a formato ONNX (Para la Orange Pi)...")

# Definir la firma de entrada (Batch size 1, 6 floats)
spec = (tf.TensorSpec((1, 6), tf.float32, name="input"),)

# Convertir de Keras a ONNX
output_path = "cerebro.onnx"
model_proto, _ = tf2onnx.convert.from_keras(model, input_signature=spec, opset=13)
onnx.save(model_proto, output_path)

print(f"🚀 ¡ÉXITO! Archivo '{output_path}' generado.")
print("PASO SIGUIENTE: Usa rknn-toolkit2 para convertir 'cerebro.onnx' a 'cerebro.rknn'")