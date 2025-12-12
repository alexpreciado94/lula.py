import os
import sys

# Intentamos importar la librería del Toolkit de Rockchip
try:
    from rknn.api import RKNN
except ImportError:
    print("\n❌ ERROR CRÍTICO: No tienes instalado 'rknn-toolkit2'.")
    print("   Este script debe ejecutarse en un PC (Linux/Docker) con el toolkit de Rockchip.")
    print("   No intentes correrlo en la Orange Pi directamente.")
    sys.exit(1)

# --- 1. CONFIGURACIÓN DE RUTAS ---
# El script está en: lula_project/scripts/npu_focus.py
# Buscamos datos en: lula_project/data/

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir) # Subimos un nivel
DATA_DIR = os.path.join(project_root, 'data')

ONNX_MODEL = os.path.join(DATA_DIR, 'cerebro.onnx')
RKNN_MODEL = os.path.join(DATA_DIR, 'cerebro.rknn')

def convert_onnx_to_rknn():
    print(f"⚙️  Iniciando NPU FOCUS (Conversor RK3588)...")
    print(f"📂 Buscando modelo en: {ONNX_MODEL}")

    if not os.path.exists(ONNX_MODEL):
        print(f"❌ Error: No existe el archivo {ONNX_MODEL}")
        print("   Ejecuta primero 'trainer.py' para generar el modelo ONNX.")
        return

    # 1. Crear Objeto RKNN
    rknn = RKNN(verbose=True)

    # 2. Configurar para Orange Pi 5 Max (Chip RK3588)
    # 'i8' significa input de 8 bits, pero usamos dataset para cuantizar
    # OJO: Para trading, recomendamos fp16 (coma flotante) para precisión
    print("--> Configurando Target RK3588...")
    rknn.config(target_platform='rk3588')

    # 3. Cargar ONNX
    print("--> Cargando ONNX...")
    ret = rknn.load_onnx(model=ONNX_MODEL)
    if ret != 0:
        print('❌ Fallo cargando ONNX')
        sys.exit(1)

    # 4. Construir (Build)
    # do_quantization=False genera un modelo FP16 (Más preciso, ideal para bots)
    # do_quantization=True genera un modelo INT8 (Más rápido, menos preciso)
    print("--> Construyendo modelo RKNN (Modo FP16)...")
    ret = rknn.build(do_quantization=False)
    if ret != 0:
        print('❌ Fallo construyendo RKNN')
        sys.exit(1)

    # 5. Exportar
    print(f"--> Guardando archivo en {RKNN_MODEL}...")
    ret = rknn.export_rknn(RKNN_MODEL)
    if ret != 0:
        print('❌ Fallo exportando RKNN')
        sys.exit(1)

    print("\n✅ ¡CONVERSIÓN COMPLETADA!")
    print(f"🚀 Archivo listo para subir a la Orange Pi: {RKNN_MODEL}")

if __name__ == "__main__":
    convert_onnx_to_rknn()