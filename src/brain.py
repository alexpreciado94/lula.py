import pandas as pd
import pandas_ta as ta
import numpy as np
import joblib
from rknnlite.api import RKNNLite

class Brain:
    def __init__(self, model_path, scaler_path):
        print(f"⚙️ Iniciando Brain NPU desde: {model_path}")
        
        # 1. Inicializar API de Rockchip
        self.rknn = RKNNLite()
        
        # 2. Cargar el modelo RKNN
        if self.rknn.load_rknn(model_path) != 0:
            raise Exception("❌ Fallo crítico: No se puede cargar el archivo .rknn")
            
        # 3. Iniciar el entorno de ejecución (Core 0 de la NPU)
        if self.rknn.init_runtime(core_mask=RKNNLite.NPU_CORE_0) != 0:
            raise Exception("❌ Fallo crítico: No se puede acceder a la NPU (/dev/rknpu)")
            
        # 4. Cargar el escalador
        try:
            self.scaler = joblib.load(scaler_path)
        except:
            raise Exception(f"❌ No se encuentra el archivo {scaler_path}")

    def analyze(self, bars):
        """
        Recibe velas crudas.
        Devuelve: (Probabilidad, RSI, Precio)
        """
        df = pd.DataFrame(bars, columns=['ts', 'o', 'h', 'l', 'close', 'v'])
        
        # --- INDICADORES ---
        df['rsi'] = df.ta.rsi(length=14)
        df['ema20'] = df.ta.ema(length=20)
        df['ema50'] = df.ta.ema(length=50)
        df['atr'] = df.ta.atr(length=14)
        
        features = ['rsi', 'ema20', 'ema50', 'atr', 'close', 'v']
        
        if df.iloc[-1][features].isnull().values.any():
            return None, None, None 
            
        last_row = df.iloc[[-1]][features]
        
        # Normalizar y convertir a float32 (Requisito NPU)
        input_data = self.scaler.transform(last_row.values).astype(np.float32)
        
        # --- INFERENCIA NPU ---
        outputs = self.rknn.inference(inputs=[input_data])
        probabilidad = outputs[0][0][0]
        
        return probabilidad, df['rsi'].iloc[-1], df['close'].iloc[-1]
        
    def release(self):
        self.rknn.release()