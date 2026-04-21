import logging, random, json, os, time, requests
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("main")

RAPIDAPI_KEY = os.environ["RAPIDAPI_KEY"]
TG_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TG_CHAT = os.environ["TELEGRAM_CHAT_ID"]
MAX_PRICE = int(os.getenv("MAX_PRICE", "500"))
STATE_FILE = "state.json"
ORIGINS = ["IST", "SAW", "ESB", "ADB"]

def get_dates():
    today = datetime.utcnow().date()
    start = today + timedelta(days=7)
    end = today + timedelta(days=60)
    days = (end - start).days
    offsets = sorted(random.sample(range(days), min(3, days)))
    return [(start + timedelta(days=d)).isoformat() for d in offsets]

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {}

def save_state(state):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    pruned = {k: v for k, v in state.items() if v.get("date", "9999") >= today}
    with open(STATE_FILE, "w") as f:
        json.dump(pruned, f, indent=1)

def send_raw(text):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    r = requests.post(url, json={
        "chat_id": TG_CHAT,
        "text": text,
        "disable_web_page_preview": True
    }, timeout=15)
    log.info("Telegram: %d", r.status_code)
    return r.status_code == 200

def search(origin, date):
    url = "https://sky-scrapper.p.rapidapi.com/api/v1/flights/searchFlightEverywhere"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "sky-scrapper.p.rapidapi.com"
    }
    params = {"originSkyId": origin, "travelDate": date, "currency": "EUR"}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=25)
        log.info("API %s %s: %d", origin, date, r.status_code)
        if r.status_code != 200:
            log.warning("API hata: %s", r.text[:300])
            return []
        data = r.json()
        items = data.get("data", [])
        log.info("Sonuc sayisi: %d", len(items))
        if items:
            log.info("Ornek: %s", json.dumps(items[0])[:400])
        return items
    except Exception as e:
        log.error("Hata: %s", e)
        return []

def parse_price(item):
    for path in [["Payload","Price"],["Payload","price"],["price"],["content","Price"]]:
        try:
            val = item
            for k in path:
                val = val[k]
            return float(val)
        except:
            continue
    return None

def parse_dest(item):
    meta = item.get("Meta", {})
    for key in ["SkyId","CityId","CountryId","CityName","CountryNameEnglish"]:
        val = meta.get(key)
        if val:
            return str(val)[:3].upper()
    return "???"

def main():
    send_raw("âï¸ UcuzUcus Bot aktif - ucuz ucuslar aranÄ±yor...")
    time.sleep(1)

    state = load_state()
    dates = get_dates()
    deals = []

    log.info("Tarihler: %s | MAX: %d EUR", dates, MAX_PRICE)

    for origin in ORIGINS:
        for date in dates:
            items = search(origin, date)
            for item in items:
                try:
                    price = parse_price(item)
                    if price is None:
                        continue
                    dest = parse_dest(item)
                    if price > MAX_PRICE:
                        continue
                    key = f"{origin}-{dest}-{date}"
                    prev = state.get(key, {}).get("price", 9999)
                    if prev <= price * 1.1:
                        continue
                    link = (f"https://www.skyscanner.com/transport/flights/"
                            f"{origin.lower()}/{dest.lower()}/"
                            f"{date.replace('-','')}/?adultsv2=1&currency=EUR")
                    reason = "Yeni firsat" if prev == 9999 else f"Fiyat dustu (once {prev:.0f} EUR)"
                    deals.append({
                        "origin": origin, "dest": dest, "date": date,
                        "price": price, "reason": reason, "link": link, "key": key
                    })
                except Exception as e:
                    log.debug("Parse hatasi: %s", e)

    deals.sort(key=lambda x: x["price"])
    log.info("Firsat sayisi: %d", len(deals))

    if not deals:
        send_raw("â¹ï¸ Bu taramada uygun fiyat bulunamadi. Yarin tekrar bakacagim.")
    else:
        sent = 0
        for deal in deals[:10]:
            text = (
                f"âï¸ {deal['origin']} â {deal['dest']}\n"
                f"ð° {deal['price']:.0f} EUR\n"
                f"ð {deal['date']}\n"
                f"ð {deal['reason']}\n"
                f"ð {deal['link']}"
            )
            if send_raw(text):
                state[deal["key"]] = {"price": deal["price"], "date": deal["date"]}
                sent += 1
            time.sleep(1.5)
        log.info("Gonderildi: %d", sent)

    save_state(state)

if __name__ == "__main__":
    main()
