import pandas as pd
import pandas_ta as ta
import numpy as np
import joblib
from rknnlite.api import RKNNLite

class Brain:
    def __init__(self, model_path, scaler_path):
        print(f"⚙️ Iniciando Madness Protocol: {model_path}")
        self.rknn = RKNNLite()
        if self.rknn.load_rknn(model_path) != 0: raise Exception("❌ Fallo RKNN")
        if self.rknn.init_runtime(core_mask=RKNNLite.NPU_CORE_0) != 0: raise Exception("❌ Fallo NPU")
        self.scaler = joblib.load(scaler_path)

    def analyze(self, crypto_bars, sp500_data):
        df = pd.DataFrame(crypto_bars, columns=['ts', 'o', 'h', 'l', 'close', 'v'])
        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        df.set_index('ts', inplace=True)
        
        # --- MERGE MACRO (S&P 500) ---
        if sp500_data is None or sp500_data.empty:
            df['sp500'] = df['close'] 
        else:
            if df.index.tz is None and sp500_data.index.tz is not None:
                sp500_data.index = sp500_data.index.tz_localize(None)
            df = df.join(sp500_data.rename('sp500'), how='left')
            df['sp500'] = df['sp500'].ffill().bfill()

        # --- INDICADORES ---
        df['rsi'] = df.ta.rsi(close=df['close'], length=14)
        df['ema20'] = df.ta.ema(close=df['close'], length=20)
        df['atr'] = df.ta.atr(high=df['h'], low=df['l'], close=df['close'], length=14)
        
        # Macro & Volumen
        df['sp500_rsi'] = df.ta.rsi(close=df['sp500'], length=14)
        df['corr_spx'] = df['close'].rolling(24).corr(df['sp500'])
        
        # Cálculo de RVOL (Volumen Relativo) para estrategia de Squeeze
        df['vol_sma'] = df['v'].rolling(20).mean()
        df['rvol'] = df['v'] / df['vol_sma']
        
        df.fillna(method='bfill', inplace=True)
        
        # Features esperadas por el modelo (Orden estricto del trainer.py)
        features = ['rsi', 'ema20', 'atr', 'close', 'v', 'sp500', 'sp500_rsi', 'corr_spx']
        
        if df.iloc[-1][features].isnull().values.any(): return None, None, None, None
            
        last_row = df.iloc[[-1]][features]
        input_data = self.scaler.transform(last_row.values).astype(np.float32)
        
        # Inferencia NPU
        outputs = self.rknn.inference(inputs=[input_data])
        probabilidad = outputs[0][0][0]
        
        # Retornamos Probabilidad, RSI, Precio y RVOL (para el detector de squeeze)
        return probabilidad, df['rsi'].iloc[-1], df['close'].iloc[-1], df['rvol'].iloc[-1]
        
    def release(self): self.rknn.release()