import pandas as pd
import pandas_ta as ta
import numpy as np
import joblib
from rknnlite.api import RKNNLite

class CerebroNPU:
    def __init__(self, model_path, scaler_path):
        print("⚡ Inicializando NPU...")
        self.rknn = RKNNLite()
        
        # Cargar modelo RKNN
        if self.rknn.load_rknn(model_path) != 0:
            raise Exception("Fallo al cargar cerebro.rknn")
            
        # Asignar al Core 0 de la NPU
        if self.rknn.init_runtime(core_mask=RKNNLite.NPU_CORE_0) != 0:
            raise Exception("Fallo al iniciar Runtime NPU")
            
        # Cargar Scaler
        self.scaler = joblib.load(scaler_path)

    def predecir(self, df):
        """Recibe DataFrame, devuelve Probabilidad (0-1)"""
        # 1. Calcular indicadores (IGUAL AL ENTRENAMIENTO)
        df['rsi'] = df.ta.rsi(length=14)
        df['ema20'] = df.ta.ema(length=20)
        df['ema50'] = df.ta.ema(length=50)
        df['atr'] = df.ta.atr(length=14)
        
        # 2. Preparar última fila
        features = ['rsi', 'ema20', 'ema50', 'atr', 'close', 'volume']
        last_row = df.iloc[[-1]][features]
        
        # 3. Normalizar y convertir a float32 (Requisito NPU)
        input_data = self.scaler.transform(last_row.values).astype(np.float32)
        
        # 4. Inferencia
        outputs = self.rknn.inference(inputs=[input_data])
        probabilidad = outputs[0][0][0] # Ajustar según tu modelo
        
        return probabilidad, df['rsi'].iloc[-1]

    def cerrar(self):
        self.rknn.release()