import logging, random, json, os, time, requests
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("main")

RAPIDAPI_KEY = os.environ["RAPIDAPI_KEY"]
TG_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TG_CHAT = os.environ["TELEGRAM_CHAT_ID"]
MAX_PRICE = int(os.getenv("MAX_PRICE", "150"))
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

def search(origin, date):
    url = "https://sky-scrapper.p.rapidapi.com/api/v1/flights/searchFlightEverywhere"
    headers = {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": "sky-scrapper.p.rapidapi.com"}
    params = {"originSkyId": origin, "travelDate": date, "currency": "EUR"}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=25)
        if r.status_code != 200:
            log.warning("API %d for %s", r.status_code, origin)
            return []
        return r.json().get("data", [])
    except Exception as e:
        log.error("Search error: %s", e)
        return []

def escape(text):
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return str(text)

def send(deal):
    text = (
        f"✈️  *{escape(deal['origin'])} → {escape(deal['dest'])}*\n"
        f"💰  *{escape(str(deal['price']))} EUR*\n"
        f"📅  {escape(deal['date'])}\n"
        f"📉  _{escape(deal['reason'])}_\n"
        f"[Uçuşları Ara]({deal['link']})"
    )
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    r = requests.post(url, json={
        "chat_id": TG_CHAT, "text": text,
        "parse_mode": "MarkdownV2", "disable_web_page_preview": True
    }, timeout=15)
    if r.status_code != 200:
        log.error("Telegram error %d: %s", r.status_code, r.text[:200])

def main():
    state = load_state()
    dates = get_dates()
    deals = []

    for origin in ORIGINS:
        for date in dates:
            items = search(origin, date)
            for item in items:
                try:
                    meta = item.get("Meta", {})
                    payload = item.get("Payload", {})
                    price = float(payload.get("Price", 9999))
                    dest = meta.get("SkyId", meta.get("CityName", "??"))[:3].upper()
                    if price > MAX_PRICE:
                        continue
                    key = f"{origin}-{dest}-{date}"
                    prev = state.get(key, {}).get("price", 9999)
                    if prev <= price * 1.1:
                        continue
                    link = f"https://www.skyscanner.com/transport/flights/{origin.lower()}/{dest.lower()}/{date.replace('-','')}/?adultsv2=1&currency=EUR"
                    reason = "Yeni firsat" if prev == 9999 else f"Fiyat dustu (onceki {prev:.0f} EUR)"
                    deals.append({"origin": origin, "dest": dest, "date": date,
                                  "price": price, "reason": reason, "link": link, "key": key})
                except:
                    continue

    deals.sort(key=lambda x: x["price"])
    log.info("Bulunan firsat: %d", len(deals))

    sent = 0
    for deal in deals[:10]:
        send(deal)
        state[deal["key"]] = {"price": deal["price"], "date": deal["date"]}
        sent += 1
        time.sleep(1.5)

    if sent == 0:
        log.info("Gonderilecek firsat yok.")

    save_state(state)
    log.info("Tamamlandi. %d mesaj gonderildi.", sent)

if __name__ == "__main__":
    main()
