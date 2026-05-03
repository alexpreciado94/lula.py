"""
LULA BRAIN v7.5 — NEURAL TENSOR ENGINE (MLP EDITION)
Sincronizado con Multi-Scaler y limpieza de logs de inferencia.
"""
import joblib
import numpy as np
import pandas as pd
import pandas_ta as ta
from rknn.api import RKNN
import os

os.environ['RKNN_LOG_LEVEL'] = '1' 

TIME_STEPS = 10

class SuppressOutput:
    def __enter__(self):
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr

class Brain:
    def __init__(self, model_path, scaler_path):
        import os, sys
        
        # --- SILENCIADOR DE ARRANQUE (Mata avisos de versión y drivers) ---
        f = open(os.devnull, 'w')
        _old_stdout = sys.stdout
        _old_stderr = sys.stderr
        sys.stdout = f
        sys.stderr = f

        try:
            self.rknn = RKNN(verbose=False)
            
            # 1. Carga del modelo consolidado
            if self.rknn.load_rknn(model_path) != 0:
                # Restauramos consola antes de lanzar el error para poder leerlo
                sys.stdout, sys.stderr = _old_stdout, _old_stderr
                raise Exception("❌ Error al cargar .rknn")
                
            # 2. Runtime en los 3 núcleos de la NPU (0x07)
            if self.rknn.init_runtime(target="rk3588", core_mask=0x07) != 0:
                sys.stdout, sys.stderr = _old_stdout, _old_stderr
                raise Exception("❌ Error NPU RK3588")

        finally:
            # --- RESTAURACIÓN DE CONSOLA ---
            sys.stdout = _old_stdout
            sys.stderr = _old_stderr
            f.close()
        
        # 3. Carga del Diccionario de Scalers Independientes
        self.scalers = joblib.load(scaler_path)
        self.features = ["returns", "rsi", "volatility", "rvol", "corr_spx", "dist_ema"]
        
        # Este mensaje ya saldrá limpio en tu consola
        print(f"🧠 Brain v7.5 listo: {len(self.scalers)} scalers cargados.")


    def prepare_data(self, symbol, bars, sp500_data):
        """Limpia y prepara la matriz de datos aplanada para MLP"""
        try:
            # Buscamos el scaler del símbolo, si no existe usamos el primero disponible
            scaler = self.scalers.get(symbol, next(iter(self.scalers.values())))
            df = pd.DataFrame(bars, columns=["ts", "open", "high", "low", "close", "volume"])
            
            # Feature Engineering v7.5
            df["returns"] = np.log(df["close"] / df["close"].shift(1))
            df["rsi"] = df.ta.rsi(length=14) / 100.0
            df["volatility"] = (df.ta.atr(length=14) / df["close"]).fillna(0)
            df["rvol"] = (df["volume"] / df["volume"].rolling(20).mean()).fillna(1.0)
            df["ema200"] = df.ta.ema(length=200)
            df["dist_ema"] = ((df["close"] - df["ema200"]) / df["ema200"]).fillna(0)
            df["corr_spx"] = 0.0 # Placeholder para contexto macro

            if len(df) < 200: return None, None

            # --- APLANADO (FLATTEN) PARA MODELO MLP ---
            last_seq = df[self.features].tail(TIME_STEPS).values
            scaled = scaler.transform(last_seq).flatten() # De (10,6) a (60,)
            
            return scaled.astype(np.float32), df.iloc[-1]
        except Exception as e:
            print(f"⚠️ Error data {symbol}: {e}")
            return None, None

    def analyze_batch(self, assets_raw_data, sp500_data):
        """Manda las secuencias a la NPU y limpia logs de formato"""
        import sys, os
        results = {}
        
        # Abrimos devnull una sola vez para ahorrar recursos
        with open(os.devnull, 'w') as fnull:
            for item in assets_raw_data:
                sym = item['symbol']
                seq, last_row = self.prepare_data(sym, item['bars'], sp500_data)
                
                if seq is not None:
                    try:
                        inp = seq.reshape(1, -1)
                        
                        # --- SILENCIADOR QUIRÚRGICO ---
                        _old_err = sys.stderr
                        sys.stderr = fnull # Redirigimos errores (donde sale el warning)
                        
                        try:
                            # Cambiamos data_format=None a 'nhwc' para evitar que salte el aviso
                            out = self.rknn.inference(inputs=[inp], data_format='nhwc')
                        finally:
                            sys.stderr = _old_err # Restauramos siempre
                        # ------------------------------

                        raw_prob = float(out[0][0][0])
                        prob = np.sqrt(raw_prob) if raw_prob > 0 else 0.0
                        results[sym] = (prob, last_row['rsi'] * 100, last_row['close'], last_row['rvol'])
                        
                    except Exception: 
                        continue
        return results



    def release(self):
        """Libera los recursos de la NPU"""
        self.rknn.release()
