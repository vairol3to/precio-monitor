import requests
import csv
import os
import re
import json
from datetime import datetime
from bs4 import BeautifulSoup

URL = "https://articulo.mercadolibre.com.ar/MLA-933472088-bicicleta-paseo-dama-rodado-26-canasto-mimbre-portaequipajes-_JM"
API_URL = "https://api.mercadolibre.com/items/MLA933472088"
CSV_FILE = "precio_historial.csv"
PRECIO_INICIAL = 395000

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


def get_price_from_api():
    """Intenta obtener el precio desde la API pública de MercadoLibre."""
    try:
        r = requests.get(API_URL, timeout=15)
        if r.status_code == 200:
            data = r.json()
            price = data.get("price")
            if price:
                print(f"✅ Precio obtenido via API: {price}")
                return int(price)
    except Exception as e:
        print(f"API falló: {e}")
    return None


def get_price_from_html():
    """Obtiene el precio scrapeando el HTML de la página."""
    try:
        r = requests.get(URL, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Método 1: JSON-LD estructurado
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    data = data[0]
                offers = data.get("offers", {})
                price = offers.get("price") or data.get("price")
                if price:
                    print(f"✅ Precio obtenido via JSON-LD: {price}")
                    return int(float(str(price).replace(".", "").replace(",", "")))
            except Exception:
                continue

        # Método 2: Variable JS __PRELOADED_STATE__ o similar
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string and "price" in script.string:
                match = re.search(r'"price"\s*:\s*(\d+(?:\.\d+)?)', script.string)
                if match:
                    price = int(float(match.group(1)))
                    if 10000 < price < 10000000:  # rango razonable en ARS
                        print(f"✅ Precio obtenido via JS embed: {price}")
                        return price

        # Método 3: Selectores CSS
        selectors = [
            ("span", {"class": "andes-money-amount__fraction"}),
            ("span", {"class": "price-tag-fraction"}),
            ("span", {"class": re.compile(r"price")}),
        ]
        for tag, attrs in selectors:
            el = soup.find(tag, attrs)
            if el:
                text = el.text.strip().replace(".", "").replace(",", "").replace("$", "")
                if text.isdigit() and int(text) > 1000:
                    print(f"✅ Precio obtenido via CSS selector: {text}")
                    return int(text)

        # Método 4: Meta tag
        meta = soup.find("meta", {"itemprop": "price"})
        if meta and meta.get("content"):
            price = int(float(meta["content"]))
            print(f"✅ Precio obtenido via meta tag: {price}")
            return price

    except Exception as e:
        print(f"HTML scraping falló: {e}")

    return None


def get_price():
    price = get_price_from_api()
    if price:
        return price
    return get_price_from_html()


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
        print("❌ ERROR: No se pudo obtener el precio por ningún método.")
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
