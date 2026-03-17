import requests
import csv
import os
from datetime import datetime

# ── Productos a monitorear ─────────────────────────────────────
PRODUCTOS = [
    {
        "nombre":    "Nagato Yuki Figure",
        "url":       "https://ninoma.com/products/the-melancholy-of-haruhi-bicute-bunnies-figure-nagato-yuki",
        "api_url":   "https://ninoma.com/products/the-melancholy-of-haruhi-bicute-bunnies-figure-nagato-yuki.json",
        "csv_file":  "precio_nagato.csv",
        "precio_inicial": 2200,
    },
    {
        "nombre":    "Asahina Mikuru Figure",
        "url":       "https://ninoma.com/products/the-melancholy-of-haruhi-suzumiya-bicute-bunnies-figure-asahina-mikuru",
        "api_url":   "https://ninoma.com/products/the-melancholy-of-haruhi-suzumiya-bicute-bunnies-figure-asahina-mikuru.json",
        "csv_file":  "precio_mikuru.csv",
        "precio_inicial": 2200,
    },
]
# ───────────────────────────────────────────────────────────────


def get_price(api_url, nombre):
    try:
        r = requests.get(api_url, timeout=15)
        r.raise_for_status()
        data = r.json()
        price_str = data["product"]["variants"][0]["price"]
        price = int(float(price_str))
        print(f"  ✅ [{nombre}] Precio obtenido: ¥{price:,}")
        return price
    except Exception as e:
        print(f"  ❌ [{nombre}] Error: {e}")
        return None


def get_last_price(csv_file, precio_inicial):
    if not os.path.exists(csv_file):
        return precio_inicial
    with open(csv_file, "r", encoding="utf-8") as f:
        rows = list(csv.reader(f))
        if len(rows) <= 1:
            return precio_inicial
        for row in reversed(rows[1:]):
            try:
                return int(row[1])
            except (ValueError, IndexError):
                continue
    return precio_inicial


def save_to_csv(csv_file, precio_actual, variacion, precio_anterior):
    file_exists = os.path.exists(csv_file)
    with open(csv_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["fecha_hora", "precio_jpy", "variacion", "precio_anterior"])
        if isinstance(variacion, int):
            var_str = f"+{variacion}" if variacion > 0 else str(variacion)
        else:
            var_str = str(variacion)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            precio_actual,
            var_str,
            precio_anterior,
        ])


def send_ntfy(titulo, mensaje, prioridad="high"):
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        print("⚠️  NTFY_TOPIC no configurado, omitiendo notificación.")
        return
    try:
        titulo_ascii = titulo.encode("ascii", "ignore").decode("ascii").strip()
        r = requests.post(
            f"https://ntfy.sh/{topic}",
            data=mensaje.encode("utf-8"),
            headers={
                "Title": titulo_ascii,
                "Priority": prioridad,
                "Tags": "rotating_light",
                "Content-Type": "text/plain; charset=utf-8",
            },
            timeout=10,
        )
        print(f"  📲 Notificación enviada (status {r.status_code})")
    except Exception as e:
        print(f"  ❌ Error enviando notificación: {e}")


def check_producto(producto):
    """Chequea un producto y retorna mensaje de cambio o None."""
    nombre     = producto["nombre"]
    precio_actual = get_price(producto["api_url"], nombre)

    if precio_actual is None:
        save_to_csv(producto["csv_file"], "ERROR", "N/A",
                    get_last_price(producto["csv_file"], producto["precio_inicial"]))
        return None

    precio_anterior = get_last_price(producto["csv_file"], producto["precio_inicial"])
    variacion = precio_actual - precio_anterior
    save_to_csv(producto["csv_file"], precio_actual, variacion, precio_anterior)

    print(f"  💰 Actual: ¥{precio_actual:,} | Anterior: ¥{precio_anterior:,} | Variación: {'+' if variacion > 0 else ''}{variacion:,}")

    if variacion != 0:
        porcentaje = (variacion / precio_anterior) * 100
        signo = "SUBIO" if variacion > 0 else "BAJO"
        linea = (
            f"{'📈' if variacion > 0 else '📉'} {nombre}: {signo} {porcentaje:+.2f}%\n"
            f"   ¥{precio_anterior:,} → ¥{precio_actual:,}  ({'+' if variacion > 0 else ''}{variacion:,})\n"
            f"   {producto['url']}"
        )
        return linea
    return None


def main():
    print(f"🔍 Chequeando precios... {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    cambios = []
    for producto in PRODUCTOS:
        print(f"→ {producto['nombre']}")
        resultado = check_producto(producto)
        if resultado:
            cambios.append(resultado)
        print()

    if cambios:
        titulo = f"Cambio de precio - {len(cambios)} producto(s)"
        mensaje = "🚨 Cambio de precio detectado!\n\n" + "\n\n".join(cambios)
        print("🚨 ¡Hay cambios! Enviando notificación...")
        send_ntfy(titulo, mensaje)
    else:
        print("✅ Sin cambios en ningún producto.")


if __name__ == "__main__":
    main()
