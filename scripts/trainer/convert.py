"""
export_onnx.py — Ejecutar DESPUÉS de que trainer.py haya generado data/model.h5
Usa from_keras directo, sin tf.function, para máxima compatibilidad con RKNN 2.3.2
"""

import tensorflow as tf
import tf2onnx
import numpy as np

INPUT_DIM = 90  # TIME_STEPS(10) * FEATURES(9)

print("📂 Cargando modelo...")
model = tf.keras.models.load_model("data/model.h5")
model.summary()

print("\n🔄 Convirtiendo a ONNX via from_keras...")
spec = (tf.TensorSpec((1, INPUT_DIM), tf.float32, name="input"),)  # batch=1 fijo

model_proto, _ = tf2onnx.convert.from_keras(
    model, input_signature=spec, opset=11, output_path="data/madness.onnx"
)

print("✅ data/madness.onnx generado.")
print("\n👉 Ahora ejecuta el comando Docker:")
print("""
docker exec -it lula_final python3 -c "
from rknn.api import RKNN
rknn = RKNN()
rknn.config(target_platform='rk3588', optimization_level=0)
rknn.load_onnx(
    model='/app/data/madness.onnx',
    inputs=['input'],
    input_size_list=[[1, 90]]
)
rknn.build(do_quantization=False)
rknn.export_rknn('/app/data/madness.rknn')
print('RKNN generado!')
"
""")
