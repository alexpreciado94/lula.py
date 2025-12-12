import pandas as pd
import pandas_ta as ta
import numpy as np
import joblib
from rknnlite.api import RKNNLite

class Brain:
    def __init__(self, model_path, scaler_path):
        print(f"⚙️ Iniciando Madness Protocol (Volumen Edition): {model_path}")
        self.rknn = RKNNLite()
        if self.rknn.load_rknn(model_path) != 0: raise Exception("❌ Fallo RKNN")
        if self.rknn.init_runtime(core_mask=RKNNLite.NPU_CORE_0) != 0: raise Exception("❌ Fallo NPU")
        self.scaler = joblib.load(scaler_path)

    def analyze(self, crypto_bars, sp500_data):
        df = pd.DataFrame(crypto_bars, columns=['ts', 'o', 'h', 'l', 'close', 'v'])
        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        df.set_index('ts', inplace=True)
        
        # --- MERGE MACRO ---
        if sp500_data is None or sp500_data.empty:
            df['sp500'] = df['close'] 
        else:
            if df.index.tz is None and sp500_data.index.tz is not None:
                sp500_data.index = sp500_data.index.tz_localize(None)
            df = df.join(sp500_data.rename('sp500'), how='left')
            df['sp500'] = df['sp500'].ffill().bfill()

        # --- NUEVOS INDICADORES DE VOLUMEN (EL REY) ---
        # 1. OBV (On Balance Volume): ¿Entra o sale dinero real?
        df['obv'] = df.ta.obv(close=df['close'], volume=df['v'])
        
        # 2. MFI (Money Flow Index): RSI pero con volumen. Detecta presión de compra.
        df['mfi'] = df.ta.mfi(high=df['h'], low=df['l'], close=df['close'], volume=df['v'], length=14)
        
        # 3. RVOL (Relative Volume): ¿Es el volumen de hoy anormalmente alto?
        # Si esto se dispara, algo gordo va a pasar.
        df['vol_sma'] = df['v'].rolling(20).mean()
        df['rvol'] = df['v'] / df['vol_sma']

        # Indicadores Clásicos
        df['rsi'] = df.ta.rsi(close=df['close'], length=14)
        df['atr'] = df.ta.atr(high=df['h'], low=df['l'], close=df['close'], length=14)
        df['corr_spx'] = df['close'].rolling(24).corr(df['sp500'])
        
        df.fillna(method='bfill', inplace=True)
        
        # Ahora tenemos más features para la IA
        # IMPORTANTE: Si cambias esto, DEBES RE-ENTRENAR trainer.py con las mismas columnas
        features = ['rsi', 'mfi', 'rvol', 'atr', 'obv', 'close', 'sp500', 'corr_spx']
        
        if df.iloc[-1][features].isnull().values.any(): return None, None, None, None
            
        # Preparamos datos
        last_row = df.iloc[[-1]][features]
        input_data = self.scaler.transform(last_row.values).astype(np.float32)
        outputs = self.rknn.inference(inputs=[input_data])
        
        # Retornamos también el RVOL (Volumen Relativo) para la estrategia
        return outputs[0][0][0], df['rsi'].iloc[-1], df['close'].iloc[-1], df['rvol'].iloc[-1]
        
    def release(self): self.rknn.release()