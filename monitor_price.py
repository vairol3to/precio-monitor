import requests
import csv
import os
from datetime import datetime

# ── Configuración ──────────────────────────────────────────────
PRODUCT_URL  = "https://ninoma.com/products/the-melancholy-of-haruhi-bicute-bunnies-figure-nagato-yuki"
API_URL      = "https://ninoma.com/products/the-melancholy-of-haruhi-bicute-bunnies-figure-nagato-yuki.json"
CSV_FILE     = "precio_historial.csv"
PRECIO_INICIAL = 2200   # ¥2,200 JPY (precio de referencia inicial)
# ───────────────────────────────────────────────────────────────


def get_price():
    """Obtiene el precio via la API JSON de Shopify (sin bloqueos)."""
    try:
        r = requests.get(API_URL, timeout=15)
        r.raise_for_status()
        data = r.json()
        # El precio está en variants[0].price (viene como string, ej: "2200.00")
        price_str = data["product"]["variants"][0]["price"]
        price = int(float(price_str))
        currency = data["product"]["variants"][0].get("presentment_prices", [{}])
        print(f"✅ Precio obtenido: {price}")
        return price
    except Exception as e:
        print(f"❌ Error al obtener precio: {e}")
        return None


def get_last_price():
    if not os.path.exists(CSV_FILE):
        return PRECIO_INICIAL
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        rows = list(csv.reader(f))
        if len(rows) <= 1:
            return PRECIO_INICIAL
        for row in reversed(rows[1:]):
            try:
                return int(row[1])
            except (ValueError, IndexError):
                continue
    return PRECIO_INICIAL


def save_to_csv(precio_actual, variacion, precio_anterior):
    file_exists = os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
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


def main():
    print(f"🔍 Chequeando precio... {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    precio_actual = get_price()

    if precio_actual is None:
        print("❌ ERROR: No se pudo obtener el precio.")
        save_to_csv("ERROR", "N/A", get_last_price())
        return

    precio_anterior = get_last_price()
    variacion = precio_actual - precio_anterior
    save_to_csv(precio_actual, variacion, precio_anterior)

    print(f"💰 Precio actual:   ¥{precio_actual:,}")
    print(f"💰 Precio anterior: ¥{precio_anterior:,}")
    print(f"📊 Variación:       {'+' if variacion > 0 else ''}{variacion:,}")

    if variacion != 0:
        porcentaje = (variacion / precio_anterior) * 100
        signo = "📈 SUBIÓ" if variacion > 0 else "📉 BAJÓ"
        print(f"🚨 ¡El precio {signo}! {porcentaje:+.2f}%")
    else:
        print("✅ Sin cambios de precio.")


if __name__ == "__main__":
    main()
