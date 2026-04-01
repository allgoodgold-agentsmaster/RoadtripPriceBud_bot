import os
import json
import requests
from datetime import date

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_IDS = [
    os.environ["TELEGRAM_CHAT_ID_OLEKSANDR"],
    os.environ["TELEGRAM_CHAT_ID_VICTORIA"],
]
SERPAPI_KEY = os.environ["SERPAPI_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
HISTORY_FILE = "price_history.json"

def send_message(text):
    for chat_id in CHAT_IDS:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        )

def load_history():
    try:
        with open(HISTORY_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

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

def ask_claude(route, price, airline, hours, mins, history):
    route_key = f"{route['from']}-{route['to']}-{route['date']}"
    past = history.get(route_key, [])

    history_text = ""
    if past:
        history_text = "Price history (oldest to newest):\n"
        for entry in past[-14:]:
            history_text += f"  {entry['date']}: ${entry['price']}\n"
    else:
        history_text = "No price history yet — this is the first check."

    prompt = f"""You are a friendly, smart flight price assistant helping a couple — Oleksandr and Victoria — decide when to book flights.

Route: {route['from']} → {route['to']}
Travel dates: {route['date']}{f" to {route['return_date']}" if route.get('return_date') else ' (one-way)'}
Target price per person: ${route.get('target_price', 'not set')}
Today's price: ${price} ({airline}, {hours}h {mins}m)
Today's date: {date.today()}

{history_text}

Based on the price trend, days until travel, and any patterns you notice, write a short warm message (3-5 sentences max) to Oleksandr and Victoria. Be conversational, not robotic. Give them a concrete recommendation — should they book now, wait, or keep watching? If the trend is clearly going down, say so. If it spiked, warn them. Use simple emojis sparingly. Do not use markdown headers or bullet points — just natural flowing text."""

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 300,
            "messages": [{"role": "user", "content": prompt}],
        }
    )

    data = response.json()
    return data["content"][0]["text"]

def main():
    with open("routes.json") as f:
        routes = json.load(f)

    history = load_history()
    today = str(date.today())

    for route in routes:
        price, airline, hours, mins = check_flight(route)

        if price is None:
            send_message(f"⚠️ Could not fetch price for {route['from']} → {route['to']}. Will try again tomorrow.")
            continue

        route_key = f"{route['from']}-{route['to']}-{route['date']}"
        if route_key not in history:
            history[route_key] = []

        if not history[route_key] or history[route_key][-1]["date"] != today:
            history[route_key].append({"date": today, "price": price})

        message = ask_claude(route, price, airline, hours, mins, history)

        trip = f"{route['from']} → {route['to']}"
        dates = route['date']
        if route.get("return_date"):
            dates += f" – {route['return_date']}"

        full_message = f"✈️ *{trip} · {dates}*\n💰 ${price} today\n\n{message}"
        send_message(full_message)

    save_history(history)

    os.system('git config user.email "bot@flightbot.com"')
    os.system('git config user.name "Flight Bot"')
    os.system('git add price_history.json')
    os.system('git commit -m "Update price history" || echo "No changes"')
    os.system('git push')

if __name__ == "__main__":
    main()
