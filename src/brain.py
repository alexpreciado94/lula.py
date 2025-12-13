import joblib
import numpy as np
import pandas as pd
import pandas_ta as ta  # noqa: F401
from rknnlite.api import RKNNLite

# Configuración de Memoria (Debe coincidir con trainer.py)
TIME_STEPS = 10


class Brain:
    def __init__(self, model_path, scaler_path):
        print(f"⚙️ Iniciando Madness Protocol (LSTM Memory): {model_path}")

        self.rknn = RKNNLite()
        if self.rknn.load_rknn(model_path) != 0:
            raise Exception("❌ Fallo crítico: No se puede cargar madness.rknn")

        if self.rknn.init_runtime(core_mask=RKNNLite.NPU_CORE_0) != 0:
            raise Exception("❌ Fallo crítico: NPU no responde")

        try:
            self.scaler = joblib.load(scaler_path)
        except Exception:
            raise Exception(f"❌ No se encuentra el archivo {scaler_path}")

    def analyze(self, crypto_bars, sp500_data):
        """
        Prepara una SECUENCIA de datos (10 horas) para la NPU.
        """
        # 1. Crear DataFrame
        df = pd.DataFrame(crypto_bars, columns=["ts", "o", "h", "l", "close", "v"])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")
        df.set_index("ts", inplace=True)

        # 2. Merge Macro (S&P 500)
        if sp500_data is None or sp500_data.empty:
            df["sp500"] = df["close"]  # Fallback
        else:
            # Eliminar zona horaria para evitar conflictos
            if df.index.tz is None and sp500_data.index.tz is not None:
                sp500_data.index = sp500_data.index.tz_localize(None)
            df = df.join(sp500_data.rename("sp500"), how="left")
            df["sp500"] = df["sp500"].ffill().bfill()

        # 3. Calcular Indicadores (9 Features)
        # Técnico
        df["rsi"] = df.ta.rsi(close=df["close"], length=14)
        df["ema20"] = df.ta.ema(close=df["close"], length=20)
        df["atr"] = df.ta.atr(
            high=df["h"], low=df["l"], close=df["close"], length=14
        )

        # Volumen (Ballenas)
        df["obv"] = df.ta.obv(close=df["close"], volume=df["v"])
        df["mfi"] = df.ta.mfi(
            high=df["h"],
            low=df["l"],
            close=df["close"],
            volume=df["v"],
            length=14,
        )
        df["vol_sma"] = df["v"].rolling(20).mean()
        df["rvol"] = df["v"] / df["vol_sma"]

        # Macro
        df["sp500_rsi"] = df.ta.rsi(close=df["sp500"], length=14)
        df["corr_spx"] = df["close"].rolling(24).corr(df["sp500"])

        df.fillna(method="bfill", inplace=True)

        # Lista estricta de 9 entradas (Orden idéntico al trainer)
        features = [
            "rsi",
            "ema20",
            "atr",  # Técnico
            "obv",
            "mfi",
            "rvol",  # Volumen
            "close",
            "sp500",
            "corr_spx",  # Macro
        ]

        # Validaciones de integridad
        if df.iloc[-1][features].isnull().values.any():
            return None, None, None, None

        # IMPORTANTE: Necesitamos al menos 10 filas para crear la secuencia
        if len(df) < TIME_STEPS:
            print("⚠️ Datos insuficientes para generar secuencia de memoria.")
            return None, None, None, None

        # 4. Preparar la SECUENCIA (The Movie)
        # Tomamos las últimas 10 filas
        last_sequence = df.iloc[-TIME_STEPS:][features].values

        # Escalamos los datos (El scaler espera 2D: [filas, features])
        scaled_sequence = self.scaler.transform(last_sequence)

        # 5. Formatear para NPU (3D Array)
        # RKNN espera: [Batch, TimeSteps, Features] -> [1, 10, 9]
        input_data = scaled_sequence.reshape(
            1, TIME_STEPS, len(features)
        ).astype(np.float32)

        # 6. Inferencia
        outputs = self.rknn.inference(inputs=[input_data])
        probabilidad = outputs[0][0][0]

        # Retornamos datos de la última vela para la estrategia
        return (
            probabilidad,
            df["rsi"].iloc[-1],
            df["close"].iloc[-1],
            df["rvol"].iloc[-1],
        )

    def release(self):
        self.rknn.release()