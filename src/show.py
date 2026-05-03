import os, socket
import time
import re
import socket


class C:
    R = "\033[0m"
    B = "\033[1m"
    # Colores base
    G = "\033[38;5;82m"  # Verde Neón
    C = "\033[38;5;51m"  # Cian
    BL = "\033[38;5;39m"
    RE = "\033[38;5;196m"  # Rojo Sangre
    Y = "\033[38;5;226m"  # Amarillo
    P = "\033[38;5;141m"  # Púrpura
    GR = "\033[38;5;244m"  # Gris
    W = "\033[38;5;255m"  # Blanco
    # Colores adicionales para estados
    O = "\033[38;5;208m"  # Naranja
    M = "\033[38;5;201m"  # Magenta


W_BOX = 85  # Calculado: sum(w+2 for w in [16,8,6,8,7,10,12,8,13]) + 8 separadores
W1, W2, W3, W4, W5, W6, W7, W8, W9 = 14, 8, 6, 8, 7, 10, 12, 8, 13
#   ACTIVO  IA    RSI  IMBAL SCORE SALDO  PRECIO  RIESGO ESTADO

# Mapeo de códigos ANSI a colores CSS Hexadecimales
ANSI_HTML_MAP = {
    "38;5;82m": "#52ff26",  # Verde Neón
    "38;5;51m": "#00f6ff",  # Cian
    "38;5;39m": "#00afff",
    "38;5;196m": "#ff0000",  # Rojo
    "38;5;226m": "#ffff00",  # Amarillo
    "38;5;141m": "#af87ff",  # Púrpura
    "38;5;244m": "#808080",  # Gris
    "38;5;255m": "#ffffff",  # Blanco
    "38;5;208m": "#ff8700",  # Naranja
    "38;5;201m": "#ff00ff",  # Magenta
    "1m": "font-weight:bold;",  # Negrita
    "0m": "</span>",  # Reset
}


def clean_ansi(text):
    return re.compile(r"\x1b\[[0-9;]*m|\ufe0f").sub("", text)


def pad(text, width, align="center"):
    if text is None:
        text = "---"  # Protección contra nulos
    text = str(text)  # Asegurar que es string
    plain = clean_ansi(text)
    # Contar emojis de forma más precisa
    emojis = len(re.findall(r"[^\x00-\x7F]", plain))
    visual_len = len(plain) + emojis
    spaces = max(0, width - visual_len)
    if align == "left":
        return text + (" " * spaces)
    if align == "right":
        return (" " * spaces) + text
    left = spaces // 2
    right = spaces - left
    return (" " * left) + text + (" " * right)


def line(left, mid, right):
    ws = [W1 + 2, W2, W3, W4, W5, W6, W7, W8, W9]
    return f"  {C.GR}{left}{mid.join('─' * (w + 2) for w in ws)}{right}{C.R}"


def format_price(price):
    """Formatea el precio de forma inteligente según su magnitud."""
    if price is None or price == 0:
        return "---"
    if price >= 10000:
        return f"${price:,.0f}"
    elif price >= 100:
        return f"${price:,.2f}"
    elif price >= 1:
        return f"${price:.4f}"
    elif price >= 0.01:
        return f"${price:.5f}"
    else:
        return f"${price:.8f}"


def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return None


def get_dashboard_ip():
    # 1. Prioridad absoluta: YAML / ENV
    external = os.getenv("EXTERNAL_IP")
    if external:
        return external

    # 2. Intentar detectar IP local
    ip = get_lan_ip()

    # 3. Evitar IPs internas de Docker
    if ip and not ip.startswith("172."):
        return ip

    # 4. Fallback seguro
    return "localhost"


def get_npu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = int(f.read()) / 1000
            return f"{temp:.1f}°C"
    except:
        return "??°C"


def print_boot_sequence():
    print(f"\n  {C.G}🚀 [ {C.B}CARGANDO PROTOCOLO LULA CA$H FLOW v6.0{C.R}{C.G} ... ]{C.R}")
    print(f"  {C.C}>> 🧠 NPU RK3588 ............. [ {C.G}ONLINE ✅{C.C} ]{C.R}")
    print(f"  {C.C}>> 🔌 ENLACE EXCHANGES ....... [ {C.G}ONLINE ✅{C.C} ]{C.R}")
    print(f"  {C.G}>> 🖥️ DASHBOARD: {C.W}http://{get_dashboard_ip()}:5000{C.R}")
    time.sleep(0.3)


def print_ui_header(vix, dxy, fng, cycle, total_equity, equity_init):
    now = time.strftime("%H:%M:%S")

    # Cálculo de rendimiento
    ganancia = total_equity - equity_init
    pct = (ganancia / equity_init * 100) if equity_init > 0 else 0
    color_g = C.G if ganancia >= 0 else C.RE
    signo = "+" if ganancia >= 0 else ""

    l1 = f"\n  {C.C}🧬 {C.B}{C.W}LULA CA$H FLOW v6.0{C.R} {C.GR}[ {C.P}ESTRATEGIA CARPE DIEM{C.GR} ]{C.R}"
    l2 = f"  {C.W}╔" + "═" * W_BOX + "╗"

    # Línea 1: Info Sistema + Rendimiento
    hw = (
        f"{C.P}💾 NPU:{C.G}OK{C.W} | {C.C}🌐 RED:{C.G}ACTIVA{C.W} | "
        f"{C.Y}💰 CAP:{C.W}${total_equity:.2f} | "
        f"{color_g}📈 {signo}${ganancia:.2f} ({pct:+.2f}%){C.W} | "
        f"{C.M}🔄 C:#{cycle}"
    )

    # Línea 2: Macro
    macro = f"{C.B}{C.W}📊 MACRO > {C.Y}VIX:{vix:.2f} {C.W}| {C.C}DXY:{dxy:.2f} {C.W}| {C.P}F&G:{fng} {C.W}| {C.RE}🔥 {get_npu_temp()}{C.W}"

    l3 = f"  {C.W}║ {pad(hw, W_BOX - 4, 'left')} {C.W}║"
    l4 = f"  {C.W}║ {pad(macro, W_BOX - 2, 'left')} {C.W}║"
    l5 = f"  {C.W}╚" + "═" * W_BOX + "╝"

    headers = [
        pad("ACTIVO", W1 + 2),
        pad("IA", W2),
        pad("RSI", W3),
        pad("IMBAL", W4),
        pad("SCORE", W5),
        pad("SALDO", W6),
        pad("PRECIO", W7),  # ← NUEVA COLUMNA
        pad("RIESGO", W8),
        pad("ESTADO", W9),
    ]
    l6 = line("┌", "┬", "┐")
    l7 = (
        f"  {C.GR}│ {C.B}{C.W}{headers[0]} {C.GR}│ {C.W}{headers[1]} {C.GR}│ {C.W}{headers[2]} "
        f"{C.GR}│ {C.W}{headers[3]} {C.GR}│ {C.W}{headers[4]} {C.GR}│ {C.W}{headers[5]} "
        f"{C.GR}│ {C.W}{headers[6]} {C.GR}│ {C.W}{headers[7]} {C.GR}│ {C.W}{headers[8]} {C.GR}│"
    )
    l8 = line("├", "┼", "┤")

    full_header = "\n".join([l1, l2, l3, l4, l5, l6, l7, l8])
    print(full_header)
    return full_header


def print_coin_row(symbol, prob, rsi, imb, score, val, risk, status, price=0.0):
    """
    CAMBIO: Se añade parámetro `price` al final (default 0.0 → retrocompatible).
    La columna PRECIO se inserta entre SALDO y RIESGO.
    """
    # Lógica de colores dinámica
    c_rsi = C.C if rsi < 40 else (C.RE if rsi > 70 else C.W)
    c_score = C.G if score > 70 else (C.RE if score < 30 else C.W)
    c_imb = C.G if imb > 0.10 else (C.RE if imb < -0.20 else C.W)

    status_upper = status.upper()
    if "AHORROS" in status_upper:
        stat_color = C.BL
    elif "COMPRA" in status_upper:
        stat_color = C.G
    elif "ACECHO" in status_upper:
        stat_color = C.Y
    elif "HOLDING" in status_upper:
        stat_color = C.G
    elif "VENTA" in status_upper:
        stat_color = C.RE
    elif "RIESGO" in status_upper:
        stat_color = C.RE
    else:
        stat_color = C.GR  # REPOSO y resto

    if prob == 0:
        dna_color = C.GR
    elif prob < 0.05:
        dna_color = C.C
    else:
        dna_color = C.P

    # Color del precio: cian neutro (es info, no señal)
    precio_str = format_price(price)
    c_precio = C.C if price > 0 else C.GR

    row_data = [
        pad(f"{C.P}🧬 {C.W}{symbol}", W1 + 2),
        pad(f"{C.C}{prob:.4f}", W2),
        pad(f"{c_rsi}{int(rsi)}", W3),
        pad(f"{c_imb}{imb:+.2f}", W4),
        pad(f"{c_score}{score}", W5),
        pad(f"{C.G}$ {val:.2f}", W6),
        pad(f"{c_precio}{precio_str}", W7),  # ← NUEVA COLUMNA
        pad(f"{C.Y}{risk}{C.GR}/70", W8),
        pad(f"{stat_color}{status}", W9 - 1),
    ]

    row_str = (
        f"  {C.GR}│ {row_data[0]} {C.GR}│ {row_data[1]} {C.GR}│ {row_data[2]} "
        f"{C.GR}│ {row_data[3]} {C.GR}│ {row_data[4]} {C.GR}│ {row_data[5]} "
        f"{C.GR}│ {row_data[6]} {C.GR}│ {row_data[7]} {C.GR}│ {row_data[8]} {C.GR}│"
    )
    print(row_str)
    return row_str


def print_ui_footer(wake_time):
    l1 = line("└", "┴", "┘")
    l2 = f"  {C.G}🗝️ BÓVEDA:{C.B}OK{C.R} | {C.C}🌉 PUENTE:{C.B}ACTIVO{C.R} | {C.M}ɱ ACUMULANDO_XMR:{C.G}ON{C.R}"
    l3 = f"  {C.GR}>> {C.Y}💤 REPOSO: 10 min {C.GR}[ despertar: {C.B}{C.W}{wake_time}{C.GR} ]{C.R}"
    full_footer = "\n".join([l1, l2, l3])
    print(full_footer)
    return full_footer


def ansi_to_html(text):
    text = text.replace("\033[0m", "</span>")

    for code, style in ANSI_HTML_MAP.items():
        if code == "0m":
            continue
        ansi_code = f"\033[{code}"

        if "38;5;" in code:
            html_tag = f"</span><span style='color:{style}'>"
        elif code == "1m":
            html_tag = f"<span style='{style}'>"
        else:
            continue

        text = text.replace(ansi_code, html_tag)

    return text


def update_web_dashboard(content=""):
    try:
        path = "/app/data/index.html"
        html_colored_content = ansi_to_html(content)

        with open(path, "w", encoding="utf-8") as f:
            f.write(
                "<!DOCTYPE html><html><head>"
                "<meta charset='utf-8'>"
                "<meta http-equiv='refresh' content='10'>"
                "<style>"
                "body{background:#000; color:#fff; font-family:'Consolas', 'Monaco', monospace; padding:20px; font-size:14px;}"
                "pre{line-height:1.2; margin:0; white-space: pre;}"
                "span{text-shadow: none !important;}"
                "</style></head>"
                f"<body><pre>{html_colored_content}</pre></body></html>"
            )
    except Exception as e:
        print(f"Error Web: {e}")
