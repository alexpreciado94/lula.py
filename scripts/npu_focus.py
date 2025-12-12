from rknn.api import RKNN

# Crear objeto RKNN
rknn = RKNN(verbose=True)

# 1. Configurar para RK3588 (El chip de tu Orange Pi 5)
rknn.config(target_platform='rk3588')

# 2. Cargar el modelo ONNX
print('--> Cargando modelo ONNX')
ret = rknn.load_onnx(model='./cerebro.onnx')
if ret != 0:
    print('Error cargando onnx')
    exit(ret)

# 3. Construir (Compilar para la NPU)
print('--> Construyendo modelo RKNN')
ret = rknn.build(do_quantization=False) # False para máxima precisión (float16)
if ret != 0:
    print('Error building rknn')
    exit(ret)

# 4. Exportar el archivo final
print('--> Exportando cerebro.rknn')
ret = rknn.export_rknn('./cerebro.rknn')
if ret != 0:
    print('Error exportando rknn')
    exit(ret)

print('🚀 ¡LISTO! Sube "cerebro.rknn" a tu Orange Pi.')