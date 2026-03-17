import requests
import csv
import os
from datetime import datetime
from bs4 import BeautifulSoup

URL = "https://articulo.mercadolibre.com.ar/MLA-933472088-bicicleta-paseo-dama-rodado-26-canasto-mimbre-portaequipajes-_JM"
CSV_FILE = "precio_historial.csv"
PRECIO_INICIAL = 395000


def get_price():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(URL, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Intentar diferentes selectores de precio
        selectors = [
            {"class": "andes-money-amount__fraction"},
            {"class": "price-tag-fraction"},
        ]
        for sel in selectors:
            el = soup.find("span", sel)
            if el:
                price_text = el.text.strip().replace(".", "").replace(",", "").replace("$", "")
                if price_text.isdigit():
                    return int(price_text)

        # Fallback: meta tag
        meta = soup.find("meta", {"itemprop": "price"})
        if meta and meta.get("content"):
            return int(float(meta["content"]))

        return None
    except Exception as e:
        print(f"Error al obtener precio: {e}")
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
            writer.writerow(["fecha_hora", "precio", "variacion", "precio_anterior"])
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

    print(f"💰 Precio actual:   ${precio_actual:,}")
    print(f"💰 Precio anterior: ${precio_anterior:,}")
    print(f"📊 Variación:       {'+' if variacion > 0 else ''}{variacion:,}")

    if variacion != 0:
        porcentaje = (variacion / precio_anterior) * 100
        signo = "📈 SUBIÓ" if variacion > 0 else "📉 BAJÓ"
        print(f"\n🚨 ¡El precio {signo}! {porcentaje:+.2f}%")
    else:
        print("✅ Sin cambios de precio.")


if __name__ == "__main__":
    main()
