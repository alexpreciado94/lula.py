import ccxt, os, sys, time, yfinance as yf
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from datetime import datetime
from pathlib import Path

LOG_ORDERS = Path("/app/logs/orders.log")


class DualExchangeManager:
    def __init__(self, testnet=True):  # Añadimos bandera de testnet
        self.testnet = testnet

        # 🔑 Lógica de llaves: Si es testnet, buscamos variables específicas de testnet
        key_env = "BINANCE_TESTNET_KEY" if testnet else "GEN_API_KEY"
        sec_env = "BINANCE_TESTNET_SECRET" if testnet else "GEN_SECRET_KEY"

        secret = os.getenv(sec_env)
        if not testnet:
            if secret and (secret.startswith("/") or secret.endswith(".pem")):
                if os.path.exists(secret):
                    with open(secret, "r") as f:
                        secret = f.read().strip()

        self.gen = ccxt.binance(
            {
                "apiKey": os.getenv(key_env),
                "secret": secret,
                "enableRateLimit": True,
                "options": {
                    "defaultType": "spot",
                    "adjustForTimeDifference": True,
                    "recvWindow": 60000,
                },
            }
        )

        # 🚀 ACTIVAR MODO SANDBOX (TESTNET)
        if self.testnet:
            self.gen.set_sandbox_mode(True)
            # print("⚠️ LULA v7: TRABAJANDO EN RED DE PRUEBAS (TESTNET)")

        # Exchange secundario (Coinex no suele tener testnet pública tan accesible,
        # así que lo dejamos normal o lo desactivamos en test)
        self.safe = getattr(ccxt, os.getenv("XMR_EXCHANGE_ID", "coinex"))(
            {"apiKey": os.getenv("XMR_API_KEY"), "secret": os.getenv("XMR_SECRET_KEY")}
        )

        self._macro_cache = {"data": None, "ts": 0}

    # 🚀 REQUERIDO PARA V7: Descarga en paralelo
    def get_data_batch(self, symbols, limit=500):
        def fetch(s):
            try:
                return s, self.gen.fetch_ohlcv(s, "1h", limit=limit)
            except:
                return s, None

        with ThreadPoolExecutor(max_workers=len(symbols)) as executor:
            results = dict(executor.map(fetch, symbols))
        return results

    def get_data(self, ex, symbol, limit=500):
        try:
            return ex.fetch_ohlcv(symbol, "1h", limit=limit)
        except:
            return None

    def get_balance(self, ex):
        try:
            return ex.fetch_balance()
        except:
            return None

    def get_sp500_data(self):
        try:
            # Tu lógica original con un pequeño timeout
            spx = yf.download(
                "^GSPC",
                period="1mo",
                interval="1h",
                progress=False,
                multi_level_index=False,
                timeout=5,
            )
            return spx["Close"].copy() if not spx.empty else None
        except:
            return None

    def get_smart_imbalance(self, symbol):
        try:
            book = self.gen.fetch_order_book(symbol, limit=20)
            bids = sum(b[1] for b in book["bids"])
            asks = sum(a[1] for a in book["asks"])
            return (bids - asks) / (bids + asks) if (bids + asks) > 0 else 0
        except:
            return 0

    # 🚀 REQUERIDO PARA V7: Cálculo de capital robusto
    def get_total_equity_usd(self):
        """
        Calcula el valor total de la cuenta en USDT.
        Optimizado para RK3588: Filtra tokens basura de Testnet para evitar lags.
        """
        try:
            balance = self.get_balance(self.gen)
            if not balance or "total" not in balance:
                return 0.0

            totals = balance["total"]
            total_usd = 0.0

            # 1. Sumamos balances en dólares directamente
            total_usd += float(totals.get("USDT", 0.0))
            total_usd += float(totals.get("USDC", 0.0))
            total_usd += float(totals.get("BUSD", 0.0))

            # 2. Definimos qué activos REALMENTE nos interesan (para no saturar la API)
            # Puedes ampliar esta lista con los tokens que quieras tradear
            activos_validos = ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOT", "MATIC"]

            for asset, amount in totals.items():
                # Filtros de limpieza:
                # - Ignorar si no tenemos cantidad significativa
                # - Ignorar stablecoins ya sumadas
                # - FILTRO CRÍTICO TESTNET: Ignorar el valor basura recurrente '18446.0'
                if amount <= 0.0001 or asset in ["USDT", "USDC", "BUSD"] or amount == 18446.0:
                    continue

                # Solo buscamos precio si es un activo conocido o si no estamos en Testnet
                if asset in activos_validos or not self.testnet:
                    try:
                        ticker = self.gen.fetch_ticker(f"{asset}/USDT")
                        valor_asset = amount * ticker.get("last", 0.0)
                        total_usd += valor_asset
                    except:
                        # Si el par no existe en el exchange, simplemente lo saltamos
                        continue

            return round(float(total_usd), 2)

        except Exception as e:
            print(f"⚠️ Error calculando Equity: {e}")
            return 0.0

        except Exception as e:
            print(f"❌ Error crítico en Equity: {e}")
            return 0.0

    def ensure_bnb_for_fees(self):
        """En Testnet, a veces es mejor no forzar la compra de BNB si no hay liquidez"""
        if self.testnet:
            return  # Saltamos en testnet para evitar errores de API
        try:
            bal = self.get_balance(self.gen)
            bnb_total = bal.get("BNB", {}).get("total", 0.0)
            ticker = self.gen.fetch_ticker("BNB/USDT")
            if (bnb_total * ticker["last"]) < 2.0:
                self.gen.create_market_buy_order("BNB/USDT", 10.0 / ticker["last"])
        except:
            pass

    def bridge_transfer(self, amount, addr, net):
        try:
            return self.gen.withdraw("USDT", amount, addr, params={"network": net})
        except:
            return None

    def revisar_log_ordenes(
        self, symbols=["BTC/USDT", "ETH/USDT", "SOL/USDT", "NEAR/USDT", "PEPE/USDT", "FET/USDT"]
    ):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Abrimos el archivo directamente para no ensuciar la consola
        with open(LOG_ORDERS, "a", encoding="utf-8") as f:
            f.write(f"\n[{timestamp}] === REVISIÓN DE ÓRDENES ===\n")

            for symbol in symbols:
                try:
                    orders = self.gen.fetch_orders(symbol, limit=5)
                    if not orders:
                        f.write(f"[{timestamp}] [{symbol}] Sin historial.\n")
                        continue
                    for o in orders:
                        f.write(
                            f"[{timestamp}] 🔹 {symbol} | {o['side'].upper()} | {o['status']} | Cant: {o['amount']} | Precio: {o['price']}\n"
                        )
                except Exception as e:
                    f.write(f"[{timestamp}] ❌ Error en {symbol}: {e}\n")

            f.write(f"[{timestamp}] ============================\n")
