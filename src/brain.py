import pandas as pd
import pandas_ta as ta
import numpy as np
import joblib
from rknnlite.api import RKNNLite

class Brain:
    def __init__(self, model_path, scaler_path):
        print(f"⚙️ Iniciando Protocolo MADNESS desde: {model_path}")
        
        self.rknn = RKNNLite()
        if self.rknn.load_rknn(model_path) != 0:
            raise Exception("❌ Fallo crítico: No se puede cargar madness.rknn")
            
        if self.rknn.init_runtime(core_mask=RKNNLite.NPU_CORE_0) != 0:
            raise Exception("❌ Fallo crítico: No se puede acceder a la NPU")
            
        try:
            self.scaler = joblib.load(scaler_path)
        except:
            raise Exception(f"❌ No se encuentra el archivo {scaler_path}")

    def analyze(self, crypto_bars, sp500_data):
        """
        Recibe velas cripto Y datos SP500.
        Devuelve: (Probabilidad, RSI, Precio)
        """
        # 1. Cripto DataFrame
        df = pd.DataFrame(crypto_bars, columns=['ts', 'o', 'h', 'l', 'close', 'v'])
        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        df.set_index('ts', inplace=True)
        
        # 2. Macro DataFrame (SP500)
        if sp500_data is None or sp500_data.empty:
            print("⚠️ Madness: Sin datos SP500. Usando fallback.")
            df['sp500'] = df['close'] 
        else:
            # Eliminar zona horaria para evitar conflictos
            if df.index.tz is None and sp500_data.index.tz is not None:
                sp500_data.index = sp500_data.index.tz_localize(None)
            
            # Unir y rellenar
            df = df.join(sp500_data.rename('sp500'), how='left')
            df['sp500'] = df['sp500'].ffill().bfill()

        # 3. Indicadores (8 Features)
        df['rsi'] = df.ta.rsi(close=df['close'], length=14)
        df['ema20'] = df.ta.ema(close=df['close'], length=20)
        df['atr'] = df.ta.atr(high=df['high'], low=df['low'], close=df['close'], length=14)
        
        df['sp500_rsi'] = df.ta.rsi(close=df['sp500'], length=14)
        df['corr_spx'] = df['close'].rolling(24).corr(df['sp500'])
        
        # Limpieza de NaN por rolling
        df.fillna(method='bfill', inplace=True)
        
        # Seleccionar features
        features = ['rsi', 'ema20', 'atr', 'close', 'v', 'sp500', 'sp500_rsi', 'corr_spx']
        
        # Inferencia
        if df.iloc[-1][features].isnull().values.any():
            return None, None, None
            
        last_row = df.iloc[[-1]][features]
        input_data = self.scaler.transform(last_row.values).astype(np.float32)
        
        outputs = self.rknn.inference(inputs=[input_data])
        probabilidad = outputs[0][0][0]
        
        return probabilidad, df['rsi'].iloc[-1], df['close'].iloc[-1]
        
    def release(self):
        self.rknn.release()