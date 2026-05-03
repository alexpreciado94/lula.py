import pandas as pd
import requests
import yfinance as yf
import time
import os
from collections import deque
import json


class Guardian:

    def __init__(self):
        self.posiciones = {} # { "BTC/USDT": {"precio_entrada": 60000, "max_alcanzado": 65000} }
        self.log_path = "/app/data/guardian_audit.json"
        self._fng_cache = {"value": 50, "ts": 0}
        self._last_prices = {}
        self._ema200_data = {}  # {symbol: deque(maxlen=200)}

        self.high_water_mark = 0.0      # Punto más alto del saldo
        self.max_drawdown_limit = 0.12  # v7.5: ampliado al 12% (era 10%)
                                        # El 10% era demasiado estricto para crypto

        self.vix = 20.0
        self.dxy = 100.0
        self.fng = 50

        self.log_path = "/app/data/guardian_audit.json"

    def registrar_entrada(self, symbol, price, prob_ia):
        self.posiciones[symbol] = {
            "precio_entrada": price,
            "max_alcanzado": price,
            "ia_entrada": prob_ia,
            "ts": time.time(),
            "breakeven_activo": False,
            "tramo2_pendiente": 0
        }
        self.save_state()
    
    def evaluar_salida_emergencia(self, symbol, current_price, current_prob):
        pos = self.posiciones.get(symbol)
        if not pos: return False, ""

        # 1. Recuperamos datos base
        precio_ent = pos["precio_entrada"]
        max_alc = pos.get("max_alcanzado", current_price)
        rendimiento = (current_price - precio_ent) / precio_ent
        ia_ent = pos.get("ia_entrada", current_prob)

        # 2. ACTUALIZAR MÁXIMO (Para el Trailing)
        if current_price > max_alc:
            pos["max_alcanzado"] = current_price
            max_alc = current_price

        # --- MEJORA: ESCALERA DE PROTECCIÓN (Smart Trailing) ---
        # En lugar de solo Breakeven, creamos niveles de seguridad:
        
        stop_dinamico = None # El precio por debajo del cual vendemos

        if rendimiento >= 0.08: # Si va ganando > 8% (Moon-shot)
            # Bloqueamos el 70% de la subida máxima (deja aire pero asegura mucho)
            stop_dinamico = max_alc * 0.96 # Permite 4% de retroceso desde el pico
        
        elif rendimiento >= 0.04: # Si va ganando > 4%
            # Aseguramos al menos un 2% de beneficio neto
            stop_dinamico = precio_ent * 1.02
            
        elif rendimiento >= 0.015: # El antiguo nivel de Breakeven
            # Aseguramos salir en positivo (Breakeven + 0.5% para comisiones)
            stop_dinamico = precio_ent * 1.005

        # Ejecución del Stop Dinámico
        if stop_dinamico and current_price <= stop_dinamico:
            return True, f"TRAILING STOP: Bloqueando beneficio en {rendimiento:.2%}"

        # --- MEJORA: FILTRO DE CONFIANZA "MOON-SHOT" ---
        # Si la IA sigue siendo ULTRA-ALTA (>0.85), ignoramos pequeñas caídas
        # Pero si la IA cae mientras el precio lateraliza, salimos.
        delta = ia_ent - current_prob
        if delta > 0.25: # IA se asusta
            if rendimiento > 0.01: # Si ya hay algo de ganancia, cerramos ya
                return True, f"DELTA IA: Confianza bajó {delta:.2f} (Asegurando mini-profit)"
            elif delta > 0.40: # Si la caída de IA es brutal, fuera aunque estemos en pérdidas
                return True, "DELTA IA CRÍTICO: Capitulación de señal"

        return False, "HOLD"

    def actualizar_maximo(self, symbol, current_price):
        """Actualiza el punto más alto para gestionar Trailing Stops."""
        if symbol in self.posiciones:
            if current_price > self.posiciones[symbol]["max_alcanzado"]:
                self.posiciones[symbol]["max_alcanzado"] = current_price

    def get_datos_posicion(self, symbol):
        """Devuelve los datos de entrada para calcular SL."""
        return self.posiciones.get(symbol, {})

    def limpiar_posicion(self, symbol):
        """Borra el rastro al vender."""
        if symbol in self.posiciones:
            del self.posiciones[symbol]
            self.save_state()

    # =========================
    # SISTEMA DE AUDITORÍA
    # =========================

    def _log_event(self, symbol, score_riesgo, ok, msg):
        """Registra por qué el Guardian tomó una decisión."""
        try:
            entry = {
                "ts":       time.strftime("%Y-%m-%d %H:%M:%S"),
                "symbol":   symbol,
                "riesgo":   score_riesgo,
                "permitido": ok,
                "motivo":   msg,
                "macro":    {"vix": round(self.vix, 2), "dxy": round(self.dxy, 2), "fng": self.fng}
            }
            with open(self.log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except:
            pass

    # =========================
    # MACRO DATA
    # =========================

    def actualizar_indicadores(self):
        """
        Actualiza VIX y DXY desde Yahoo Finance y F&G desde alternative.me.
        Cache de 1 hora para F&G.
        """
        try:
            macro = yf.download(
                ["^VIX", "DX-Y.NYB"],
                period="5d", interval="1d",
                progress=False, threads=False
            )
            if not macro.empty:
                self.vix = float(macro["Close"]["^VIX"].ffill().iloc[-1])
                self.dxy = float(macro["Close"]["DX-Y.NYB"].ffill().iloc[-1])
        except:
            pass

        ahora = time.time()
        if ahora - self._fng_cache["ts"] > 3600:
            try:
                r = requests.get("https://api.alternative.me/fng/", timeout=5).json()
                self.fng = int(r["data"][0]["value"])
                self._fng_cache = {"value": self.fng, "ts": ahora}
            except:
                pass

    # =========================
    # EMA200 ACUMULATIVA
    # =========================

    def update_ema200(self, symbol, price):
        """
        Acumula cierres en un deque de 200 velas para calcular EMA200.
        Devuelve el valor de EMA200 si hay suficientes datos, o None.
        """
        if symbol not in self._ema200_data:
            self._ema200_data[symbol] = deque(maxlen=200)

        self._ema200_data[symbol].append(price)
        data = list(self._ema200_data[symbol])

        if len(data) < 200:
            return None  # Insuficientes datos — no filtrar todavía

        # EMA con smoothing estándar
        k = 2 / (len(data) + 1)
        ema = data[0]
        for p in data[1:]:
            ema = p * k + ema * (1 - k)
        return ema

    # =========================
    # RIESGO INTELIGENTE v7.5
    # =========================

    def check_drawdown_safety(self, current_balance):
        """
        Protección de capital por drawdown.
        Límite ampliado al 12% para crypto (volatilidad normal del mercado).
        El High Water Mark se actualiza automáticamente con nuevos máximos.
        """
        if current_balance > self.high_water_mark:
            self.high_water_mark = current_balance
            return True, 0.0

        if self.high_water_mark == 0:
            return True, 0.0

        drawdown = (self.high_water_mark - current_balance) / self.high_water_mark

        if drawdown > self.max_drawdown_limit:
            return False, drawdown  # PELIGRO: Drawdown excedido

        return True, drawdown  # TODO OK

    def analizar_riesgo(self, connection, symbol, crypto_data, res_ia):
        """
        Calcula el score de riesgo para cada activo.

        CAMBIOS v7.5:
        - DXY: umbral subido de 96 → 99 (DXY ~98 es normal, no peligroso)
        - F&G: umbral bajado de 40 → 25 (solo penaliza miedo extremo)
        - VIX: umbral subido de 16 → 18 (VIX ~18 es normal post-2022)
        - Penalización de imbalance negativo suavizada
        - Techo de riesgo final sigue en 70 (MAX_RISK_ALLOWED)
        """
        from lullaby import get_dynamic_threshold
        import random

        prob, rsi, price, rvol = res_ia
        max_r = int(os.getenv("MAX_RISK_ALLOWED", 70))

        # --- EXTENSIÓN: distancia a media reciente ---
        r_extension = 0.0
        try:
            cierres = [float(v[4]) for v in crypto_data[-20:]]
            if cierres:
                media_reciente = sum(cierres) / len(cierres)
                distancia = abs(price - media_reciente) / media_reciente
                if distancia > 0.02:
                    r_extension = distancia * 100
        except:
            pass

        # 1. COMPONENTE INDIVIDUAL
        # Base de 20 puntos — el riesgo cero no existe en crypto
        r_individual = 20.0
        try:
            imb = connection.get_smart_imbalance(symbol)
            r_individual += abs(imb) * 30 if imb < 0 else -(imb * 15)
        except:
            imb = 0

        # RSI: penaliza extremos (muy sobrecomprado o muy sobrevendido)
        r_individual += abs(50 - rsi) * 0.4
        # rvol: volumen alto = más riesgo, pero con techo
        r_individual += min(rvol * 3, 10)
        r_individual += r_extension

        # 2. COMPONENTE MACRO v7.6 — Solo penaliza condiciones realmente malas
        r_macro = 0.0
        r_macro += max(0, (self.vix - 18) * 0.8)   # VIX normal hasta 18
        r_macro += max(0, (self.dxy - 99) * 1.2)   # DXY normal hasta 99
        if self.fng < 25:
            r_macro += (25 - self.fng) * 0.4       # Solo miedo extremo

        # 3. DESCUENTO POR IA — máximo 10 puntos (antes 20, era demasiado)
        # prob=0.9 → -9pts | prob=0.5 → -5pts | prob=0.1 → -1pt
        descuento_ia = prob * 10

        # 4. CÁLCULO FINAL — rango real esperado: 15-65
        riesgo_raw = r_macro + r_individual - descuento_ia + random.uniform(-1.0, 1.0)
        riesgo_final = int(max(10, min(65, riesgo_raw)))
        ok = riesgo_final < max_r

        # Auditoría: registra cuando el riesgo es alto o bloqueante
        if not ok or riesgo_final > 55:
            try:
                entry = {
                    "ts":       time.time(),
                    "sym":      symbol,
                    "r":        riesgo_final,
                    "r_macro":  round(r_macro, 2),
                    "r_indiv":  round(r_individual, 2),
                    "r_ext":    round(r_extension, 2),
                    "vix":      round(self.vix, 2),
                    "dxy":      round(self.dxy, 2),
                    "fng":      self.fng,
                    "prob":     round(prob, 4)
                }
                with open(self.log_path, "a") as f:
                    f.write(json.dumps(entry) + "\n")
            except:
                pass

        return ok, f"{riesgo_final}/70", riesgo_final

    # =========================
    # PERSISTENCIA DE ESTADO
    # =========================

    def save_state(self):
        """Guarda la memoria del Guardian en disco incluyendo posiciones."""
        state = {
            "high_water_mark": self.high_water_mark,
            "ema200_data": {s: list(d) for s, d in self._ema200_data.items()},
            "posiciones": self.posiciones  # Guardamos los precios de entrada
        }
        try:
            os.makedirs("/app/data", exist_ok=True)
            with open("/app/data/guardian_memory.json", "w") as f:
                json.dump(state, f)
        except Exception as e:
            print(f"⚠️ Error guardando Guardian: {e}")

    def load_state(self):
        """Recupera la memoria al arrancar de forma segura."""
        path = "/app/data/guardian_memory.json"
        
        # 1. Inicializamos con valores vacíos por seguridad
        state = {} 
        
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    state = json.load(f)
                
                # Carga de datos antiguos
                self.high_water_mark = state.get("high_water_mark", 0.0)
                
                # Recuperar EMAs
                for s, d in state.get("ema200_data", {}).items():
                    self._ema200_data[s] = deque(d, maxlen=200)
                
                # 2. Recuperar POSICIONES (Precios de entrada para el Stop Loss)
                self.posiciones = state.get("posiciones", {})
                
                print(f"🧠 Memoria recuperada. HWM: ${self.high_water_mark:,.2f} | Posiciones: {len(self.posiciones)}")
                return # Salimos con éxito
            except Exception as e:
                print(f"⚠️ Error leyendo JSON de memoria: {e}")
        
        # 3. Si llegamos aquí es porque no hay archivo o falló: Inicializamos limpio
        print("🆕 Guardian iniciado con memoria limpia.")
        self.posiciones = {}

    def reset_high_water_mark(self, new_balance: float):
        """
        Resetea el High Water Mark al balance actual.
        Útil tras un reset de Testnet o cambio significativo de capital.
        Llama este método manualmente desde el bot si es necesario:
            guardian.reset_high_water_mark(current_balance)
        """
        self.high_water_mark = new_balance
        self.save_state()
        print(f"🔄 High Water Mark reseteado a ${new_balance:,.2f}")