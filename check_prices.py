import os
import json
import requests

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_IDS = [
    os.environ["TELEGRAM_CHAT_ID_OLEKSANDR"],
    os.environ["TELEGRAM_CHAT_ID_VICTORIA"],
]
SERPAPI_KEY = os.environ["SERPAPI_KEY"]

def send_message(text):
    for chat_id in CHAT_IDS:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        )

def check_flight(route):
    params = {
        "engine": "google_flights",
        "departure_id": route["from"],
        "arrival_id": route["to"],
        "outbound_date": route["date"],
        "currency": "USD",
        "api_key": SERPAPI_KEY,
    }
    if route.get("return_date"):
        params["return_date"] = route["return_date"]
        params["type"] = "1"
    else:
        params["type"] = "2"

    response = requests.get("https://serpapi.com/search", params=params)
    data = response.json()

    try:
        best = data["best_flights"][0]
        price = best["price"]
        airline = best["flights"][0]["airline"]
        duration = best["total_duration"]
        hours = duration // 60
        mins = duration % 60
        return price, airline, hours, mins
    except (KeyError, IndexError):
        return None, None, None, None

def main():
    with open("routes.json") as f:
        routes = json.load(f)

    for route in routes:
        price, airline, hours, mins = check_flight(route)

        if price is None:
            send_message(f"⚠️ Could not fetch price for {route['from']} → {route['to']}. Will try again tomorrow.")
            continue

        target = route.get("target_price")
        trip = f"{route['from']} → {route['to']}"
        dates = route['date']
        if route.get("return_date"):
            dates += f" – {route['return_date']}"

        if target and price <= target:
            msg = (
                f"✅ *Price alert, Oleksandr & Victoria!*\n\n"
                f"✈️ {trip}\n"
                f"📅 {dates}\n"
                f"💰 *${price}* per person — below your ${target} target!\n"
                f"🛫 {airline} · {hours}h {mins}m\n\n"
                f"Might be a good time to book! 🎉"
            )
        else:
            msg = (
                f"📊 *Daily flight update*\n\n"
                f"✈️ {trip}\n"
                f"📅 {dates}\n"
                f"💰 ${price} per person"
                + (f" (target: ${target})" if target else "")
                + f"\n🛫 {airline} · {hours}h {mins}m\n\n"
                f"Hang tight, not there yet 🙂"
            )

        send_message(msg)

if __name__ == "__main__":
    main()
