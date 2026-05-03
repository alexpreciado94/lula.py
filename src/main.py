import os, time, threading, warnings, json
from brain import Brain
from connection import DualExchangeManager
from guardian import Guardian
import show as ui
import lullaby as strat
import feelings
import sub

warnings.filterwarnings("ignore")


def start_web_server():
    from http.server import HTTPServer, SimpleHTTPRequestHandler

    class TinyHandler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def do_GET(self):
            if self.path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
                return
            try:
                return super().do_GET()
            except (BrokenPipeError, ConnectionResetError):
                pass

    os.makedirs("/app/data", exist_ok=True)
    os.chdir("/app/data")
    try:
        server = HTTPServer(("0.0.0.0", 5000), TinyHandler)
        server.serve_forever()
    except:
        pass


def rotar_capital(connection, prices_map, full_bal, nivel_ataque):
    """
    Rotación activa desde ETH y BTC hacia altcoins con señal.
    ALTA    → 1.5% ETH + 1.0% BTC (máx $500 + $300)
    EXTREMA → 3.0% ETH + 2.0% BTC (máx $500 + $300)
    """
    liberado = 0.0
    pct_eth = 0.03 if nivel_ataque == "EXTREMA" else 0.015
    pct_btc = 0.02 if nivel_ataque == "EXTREMA" else 0.010

    for coin, pct, cap in [("ETH", pct_eth, 500), ("BTC", pct_btc, 300)]:
        try:
            qty = full_bal.get(coin, {}).get("total", 0)
            precio = prices_map.get(f"{coin}/USDT", 0)
            valor = qty * precio
            if valor > 1000 and precio > 0:
                monto = min(valor * pct, cap)
                q = connection.gen.amount_to_precision(f"{coin}/USDT", monto / precio)
                connection.gen.create_market_order(f"{coin}/USDT", "sell", q)
                liberado += monto
                print(f"🔄 ROTACIÓN {coin}: -${monto:.2f} liberados")
                time.sleep(1)
        except Exception as e:
            print(f"⚠️ Error rotando {coin}: {e}")

    return liberado


def get_xmr_row(connection, ok_macro):
    """
    Obtiene precio y saldo de XMR desde CoinEx (connection.safe).
    """
    try:
        xmr_bal = connection.get_balance(connection.safe)
        xmr_qty = xmr_bal.get("XMR", {}).get("total", 0) if xmr_bal else 0
        ticker = connection.safe.fetch_ticker("XMR/USDT")
        xmr_p = ticker.get("last", 0)
        xmr_val = xmr_qty * xmr_p
        return xmr_p, xmr_val
    except:
        return 0.0, 0.0


# ─────────────────────────────────────────────────────────────
# RESET DIARIO — Persistencia del equity inicial por día
# ─────────────────────────────────────────────────────────────
DAILY_STATE_PATH = "/app/data/daily_state.json"


def load_daily_state(current_equity):
    """
    Carga el equity_inicial del día actual.
    Si el archivo no existe o es de un día anterior, reinicia con el equity actual.
    Devuelve (equity_inicial, cycle_offset).
    """
    today = time.strftime("%Y-%m-%d")
    try:
        if os.path.exists(DAILY_STATE_PATH):
            with open(DAILY_STATE_PATH, "r") as f:
                state = json.load(f)
            if state.get("date") == today:
                print(
                    f"📅 Sesión del día {today} restaurada. "
                    f"Equity inicial: ${state['equity_init']:.2f} | "
                    f"Ciclos previos: {state.get('cycle_offset', 0)}"
                )
                return float(state["equity_init"]), int(state.get("cycle_offset", 0))
    except Exception as e:
        print(f"⚠️ Error leyendo estado diario: {e}")

    # Nuevo día → guardamos el estado fresco
    save_daily_state(today, current_equity, 0)
    print(f"🆕 Nuevo día {today}. Equity base: ${current_equity:.2f}")
    return current_equity, 0


def save_daily_state(date, equity_init, cycle_offset):
    """Persiste el estado diario en disco."""
    try:
        os.makedirs("/app/data", exist_ok=True)
        with open(DAILY_STATE_PATH, "w") as f:
            json.dump({"date": date, "equity_init": equity_init, "cycle_offset": cycle_offset}, f)
    except Exception as e:
        print(f"⚠️ Error guardando estado diario: {e}")


def check_daily_reset(equity_init, cycle, equity_actual):
    """
    Comprueba si han pasado las 00:00. Si es así, resetea equity_init y cycle.
    Devuelve (equity_init, cycle) actualizados.
    """
    today = time.strftime("%Y-%m-%d")
    try:
        if os.path.exists(DAILY_STATE_PATH):
            with open(DAILY_STATE_PATH, "r") as f:
                state = json.load(f)
            if state.get("date") != today:
                # ¡Nuevo día! Cerramos el anterior y arrancamos fresco
                print(f"\n🌅 RESET DIARIO — {today} — Equity base: ${equity_actual:.2f}\n")
                save_daily_state(today, equity_actual, 0)
                return equity_actual, 1  # cycle vuelve a 1
    except Exception as e:
        print(f"⚠️ Error en check_daily_reset: {e}")
    return equity_init, cycle


def main():
    # 1. BOOT SEQUENCE
    try:
        connection = DualExchangeManager()
        connection.revisar_log_ordenes(strat.GENERATOR_COINS)
        brain = Brain("/app/data/madness.rknn", "/app/data/scaler.pkl")
        guardian = Guardian()
        guardian.load_state()
    except Exception as e:
        print(f"❌ Error de Arranque Crítico: {e}")
        return

    print("\033[H\033[J", end="")
    ui.print_boot_sequence()

    # ── Equity inicial del día (persistido) ────────────────────
    equity_raw = connection.get_total_equity_usd() or 100.0
    equity_inicial, cycle_offset = load_daily_state(equity_raw)
    # ────────────────────────────────────────────────────────────

    threading.Thread(target=sub.start_web_server, daemon=True).start()

    # ─── Tiempos de ciclo ──────────────────────────────────────
    SLEEP_NORMAL = 600  # 10 min — sin actividad
    SLEEP_POST_OP = 15  # 15 seg — tras compra o venta
    SLEEP_WATCHING = 60  # 1 min  — señal en ACECHO
    # ───────────────────────────────────────────────────────────

    MAX_ROTACIONES_POR_CICLO = 2

    cycle = 1 + cycle_offset  # Continúa desde donde se quedó hoy
    while True:
        try:
            hubo_operacion = False
            hay_acecho = False
            rotaciones_ciclo = 0

            # ── Comprobación de reset diario al inicio de cada ciclo ──
            equity_inicial, cycle = check_daily_reset(
                equity_inicial, cycle, connection.get_total_equity_usd() or equity_inicial
            )
            # ──────────────────────────────────────────────────────────

            # 2. MACRO Y SALDOS
            guardian.actualizar_indicadores()
            sp500 = connection.get_sp500_data()
            full_bal = connection.get_balance(connection.gen)
            total_equity = connection.get_total_equity_usd()
            usdt_free = full_bal.get("USDT", {}).get("free", 0) if full_bal else 0

            # 3. SEGURIDAD
            ok_drawdown, _ = guardian.check_drawdown_safety(total_equity)
            ok_macro = (guardian.vix < 25 and guardian.dxy < 103) if ok_drawdown else False

            header = ui.print_ui_header(
                guardian.vix, guardian.dxy, guardian.fng, cycle, total_equity, equity_inicial
            )
            web_buffer = (header or "") + "\n"

            # 4. RECOLECCIÓN — Solo GENERATOR_COINS (sin XMR, Binance no lo tiene)
            raw_market_data = connection.get_data_batch(strat.GENERATOR_COINS, limit=200)
            prices_map = {s: b[-1][4] for s, b in raw_market_data.items() if b}

            # 5. INFERENCIA NPU
            batch_input = [{"symbol": s, "bars": b} for s, b in raw_market_data.items() if b]
            ai_results = brain.analyze_batch(batch_input, sp500)

            # 6. PROCESAMIENTO DE SEÑALES
            analyzed_assets = []
            for symbol, (prob, rsi, price, rvol) in ai_results.items():
                try:
                    score = strat.calculate_weighted_score(
                        prob, rsi, 0, rvol=rvol, vix=guardian.vix
                    )
                    bars = next(
                        (item["bars"] for item in batch_input if item["symbol"] == symbol), []
                    )
                    analyzed_assets.append(
                        {
                            "symbol": symbol,
                            "prob": prob,
                            "rsi": rsi,
                            "price": price,
                            "rvol": rvol,
                            "score": score,
                            "bars": bars,
                        }
                    )
                except:
                    continue

            analyzed_assets = sorted(analyzed_assets, key=lambda x: x["score"], reverse=True)

            # ============================================================
            # 7. EJECUCIÓN — Motor de Trading v7.7
            # ============================================================
            # --- NUEVA MEJORA: CÁLCULO DE EXPOSICIÓN GLOBAL ---
            # Sumamos cuánto dinero hay invertido en total en este momento
            total_invertido = sum(
                (full_bal.get(s.split("/")[0], {}).get("total", 0) * prices_map.get(s, 0))
                for s in strat.GENERATOR_COINS
            )

            # Consultamos a feelings.py si el mercado da permiso (Filtro IMBAL de BTC)
            # 1. Obtener datos macro y permiso (ahora pasando total_equity)
            btc_imb_global = connection.get_smart_imbalance("BTC/USDT")
            import feelings

            m_status, max_exp_pct, max_pos, current_tier = feelings.get_market_permission(
                btc_imb_global, guardian.dxy, guardian.vix, guardian.fng, total_equity
            )

            # 2. Contar posiciones abiertas actualmente
            posiciones_activas = len(
                [
                    s
                    for s in guardian.posiciones
                    if (full_bal.get(s.split("/")[0], {}).get("total", 0) * prices_map.get(s, 0))
                    > 5.0
                ]
            )

            for asset in analyzed_assets:
                symbol, prob, rsi, price = (
                    asset["symbol"],
                    asset["prob"],
                    asset["rsi"],
                    asset["price"],
                )
                score, bars, rvol = asset["score"], asset["bars"], asset["rvol"]

                # Datos de la posición actual (si existe)
                pos_data = guardian.get_datos_posicion(symbol)
                base_asset = symbol.split("/")[0].upper()
                held = full_bal.get(base_asset, {}).get("total", 0) if full_bal else 0
                val_usd = held * price
                sin_posicion = val_usd < 16.0

                # --- NUEVA MEJORA: EVALUAR SALIDA DE EMERGENCIA (DELTA IA / BREAKEVEN) ---
                if not sin_posicion:
                    debe_salir_ya, motivo_emergencia = guardian.evaluar_salida_emergencia(
                        symbol, price, prob
                    )
                    if debe_salir_ya:
                        try:
                            qty_v = connection.gen.amount_to_precision(symbol, held)
                            connection.gen.create_market_order(symbol, "sell", qty_v)
                            guardian.limpiar_posicion(symbol)
                            hubo_operacion = True
                            print(f"🚨 SALIDA EMERGENCIA: {symbol} | {motivo_emergencia}")
                            continue  # Pasamos al siguiente activo
                        except Exception as e:
                            print(f"⚠️ Error en salida emergencia {symbol}: {e}")

                # Status label normal
                imb = connection.get_smart_imbalance(symbol)
                ok_risk, risk_msg, riesgo_n = guardian.analizar_riesgo(
                    connection, symbol, bars, (prob, rsi, price, rvol)
                )

                status = strat.get_status_label(
                    prob,
                    score,
                    (ok_macro and ok_risk),
                    val_usd,
                    rsi,
                    symbol=symbol,
                    price=price,
                    guardian=guardian,
                )

                if "ACECHO" in status:
                    hay_acecho = True

                # --- SECCIÓN DE SALIDA POR ESTRATEGIA (NORMAL) ---
                if val_usd > 5.0 and ("VENTA" in status or "STOP" in status or "SCORE" in status):
                    try:
                        qty_v = connection.gen.amount_to_precision(symbol, held)
                        connection.gen.create_market_order(symbol, "sell", qty_v)
                        guardian.limpiar_posicion(symbol)
                        usdt_free += val_usd
                        hubo_operacion = True
                        print(f"{status}: {symbol} | Salida estratégica")
                    except Exception as e:
                        print(f"⚠️ Error en salida {symbol}: {e}")

                # --- SECCIÓN DE COMPRA (CON BLINDAJE v6.2) ---
                if "🚀 COMPRA" in status and sin_posicion:
                    # 1. Comprobamos límite de posiciones del Tier
                    if posiciones_activas >= max_pos:
                        if cycle % 5 == 0:
                            print(
                                f"⏳ Límite de posiciones alcanzado para Tier {current_tier} ({max_pos})"
                            )
                        continue

                    # 2. Comprobamos freno de mano por riesgo global
                    if total_invertido > (total_equity * max_exp_pct):
                        if cycle % 5 == 0:
                            print(
                                f"🛡️ BLOQUEO RIESGO GLOBAL: {m_status} (Límite: {max_exp_pct*100}%)"
                            )
                        continue

                    if usdt_free > 10.5:
                        # IA-WEIGHTING: get_position_size ahora ajusta el monto según la prob
                        tramo1, tramo2 = strat.get_position_size(
                            usdt_free, total_equity, val_usd, score, prob=prob
                        )

                        if tramo1 >= 10.0:
                            try:
                                ejecutado = strat.execute_twap(
                                    connection, symbol, tramo1, price, label="T1"
                                )
                                if ejecutado > 0:
                                    # IMPORTANTE: Ahora pasamos 'prob' para el cálculo de Delta IA futuro
                                    guardian.registrar_entrada(symbol, price, prob)
                                    usdt_free -= ejecutado
                                    total_invertido += ejecutado
                                    posiciones_activas += 1  # Actualizamos el contador
                                    hubo_operacion = True

                                    if tramo2 >= 10.0:
                                        guardian.posiciones[symbol]["tramo2_pendiente"] = tramo2
                                        guardian.save_state()
                            except Exception as e:
                                print(f"⚠️ Error en compra {symbol}: {e}")

                # --- SCALING IN: Tramo 2 si prob sigue confirmando (posición ya abierta) ---
                elif val_usd >= 5.0:
                    datos_pos = guardian.get_datos_posicion(symbol)
                    tramo2_pendiente = datos_pos.get("tramo2_pendiente", 0)
                    scale_threshold_high = float(os.getenv("SCALE_IN_THRESHOLD_HIGH", 0.75))

                    if (
                        tramo2_pendiente >= 10.0
                        and prob >= scale_threshold_high
                        and usdt_free > tramo2_pendiente
                    ):
                        try:
                            ejecutado2 = strat.execute_twap(
                                connection, symbol, tramo2_pendiente, price, label="T2"
                            )
                            if ejecutado2 > 0:
                                usdt_free -= ejecutado2
                                hubo_operacion = True
                                guardian.posiciones[symbol].pop("tramo2_pendiente", None)
                                guardian.save_state()
                                print(
                                    f"  ↳ Scaling In T2 ejecutado: ${ejecutado2:.2f} @ ${price:.4f}"
                                )
                        except Exception as e:
                            print(f"⚠️ Error en Tramo 2 {symbol}: {e}")

                # ── Precio actual desde prices_map para la columna PRECIO ──
                current_price = prices_map.get(symbol, price)
                row = ui.print_coin_row(
                    symbol, prob, rsi, imb, score, val_usd, riesgo_n, status, price=current_price
                )
                web_buffer += (row or "") + "\n"

            # ── Fila especial XMR ──
            try:
                xmr_p, xmr_val = get_xmr_row(connection, ok_macro)
                xmr_status = strat.get_status_label(0, -1, ok_macro, xmr_val, 50, symbol="XMR/USDT")
                row_xmr = ui.print_coin_row(
                    "XMR/USDT", 0.0, 50, 0.0, -1, xmr_val, 0, xmr_status, price=xmr_p
                )
                web_buffer += (row_xmr or "") + "\n"
            except:
                pass

            # 8. SLEEP INTELIGENTE
            if hubo_operacion:
                proximo_wake = time.time() + SLEEP_POST_OP
                sleep_label = f"⚡ Actualizando en {SLEEP_POST_OP}s"
                sleep_dur = SLEEP_POST_OP
            elif hay_acecho:
                proximo_wake = time.time() + SLEEP_WATCHING
                sleep_label = f"📡 Acecho activo — refresco en 1 min"
                sleep_dur = SLEEP_WATCHING
            else:
                proximo_wake = time.time() + SLEEP_NORMAL
                sleep_label = f"💤 REPOSO: 10 min"
                sleep_dur = SLEEP_NORMAL

            wake_str = time.strftime("%H:%M", time.localtime(proximo_wake))
            footer_line = ui.print_ui_footer(wake_str)
            footer_real = footer_line.replace("💤 REPOSO: 10 min", sleep_label)
            ui.update_web_dashboard(web_buffer + (footer_real or ""))

            # 9. FINALIZACIÓN DE CICLO
            try:
                reserva_cash = float(os.getenv("MIN_CASH_RESERVE", 100.0))
                lote_bridge = float(os.getenv("MIN_BRIDGE_BATCH", 50.0))
                if usdt_free > (reserva_cash + lote_bridge):
                    connection.bridge_transfer(
                        usdt_free - reserva_cash, os.getenv("REFUGE_ADDR"), "TRX"
                    )

                if xmr_p and xmr_p > 0:
                    xmr_pct_actual = xmr_val / total_equity if total_equity > 0 else 0
                    if xmr_pct_actual < float(os.getenv("MAX_XMR_PCT", 0.4)):
                        strat.manage_wealth(connection, 0.50, 40, xmr_p, ok_macro)
            except:
                pass

            # ── Guardamos el progreso del ciclo actual para restaurar tras reinicios ──
            save_daily_state(time.strftime("%Y-%m-%d"), equity_inicial, cycle)

            cycle += 1
            guardian.save_state()
            time.sleep(sleep_dur)

        except Exception as e:
            print(f"⚠️ Alerta de Sistema (Main Loop): {type(e).__name__} - {e}")
            print("⏳ Reintentando en 60 segundos...")
            time.sleep(60)


if __name__ == "__main__":
    main()
