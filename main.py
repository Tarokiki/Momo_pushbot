import os
import random
import requests
from datetime import datetime, date
from zoneinfo import ZoneInfo

# ======================
# GitHub Secrets
# ======================
WX_APPID = os.environ["WX_APPID"]
WX_SECRET = os.environ["WX_SECRET"]
WX_OPENID = os.environ["WX_OPENID"]
WX_TEMPLATE_ID = os.environ["WX_TEMPLATE_ID"]

YOU_TZ = "Asia/Tokyo"
BF_TZ = "America/Chicago"

YOU_CITY = "Tokyo"
BF_CITY = "St. Louis"

ANNIVERSARY_DATE = date(2024, 8, 1)  # 改成你们在一起的日期

SWEET_LINES = [
    "You're my favorite notification.",
    "Being yours is my favorite thing.",
    "You are my safest place in this world.",
    "Loving you feels like home.",
    "Forever isn't long enough with you.",
    "Even ordinary days feel special with you.",
    "I choose you—again and again.",
    "You make my heart feel quiet and warm.",
    "If you’re smiling, I’m okay.",
    "I’m lucky that I get to love you.",
]

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


def http_get_json(url, params):
    r = requests.get(url, params=params, timeout=15)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text}")
    return r.json()


def get_latlon(city):
    data = http_get_json(GEOCODE_URL, {
        "name": city,
        "count": 1,
        "language": "en",
        "format": "json"
    })
    result = data["results"][0]
    return result["latitude"], result["longitude"]


def get_weather(city, tz):
    lat, lon = get_latlon(city)
    data = http_get_json(WEATHER_URL, {
        "latitude": lat,
        "longitude": lon,
        "current_weather": "true",
        "timezone": tz
    })
    cw = data["current_weather"]
    return f"{city}: {cw['temperature']}°C"


def get_access_token():
    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {
        "grant_type": "client_credential",
        "appid": WX_APPID,
        "secret": WX_SECRET
    }
    return http_get_json(url, params)["access_token"]


def send_template(payload):
    token = get_access_token()
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    r = requests.post(url, json=payload, timeout=15)
    data = r.json()
    if data.get("errcode") != 0:
        raise RuntimeError(f"WeChat send failed: {data}")
    print("Sent OK:", data)


def build_payload():
    now_you = datetime.now(ZoneInfo(YOU_TZ))
    now_bf = datetime.now(ZoneInfo(BF_TZ))

    weather_you = get_weather(YOU_CITY, YOU_TZ)
    weather_bf = get_weather(BF_CITY, BF_TZ)

    days_together = (date.today() - ANNIVERSARY_DATE).days
    countdown = 1000 - days_together  # 举例：1000天纪念

    love_line = random.choice(SWEET_LINES)

    payload = {
        "touser": WX_OPENID,
        "template_id": WX_TEMPLATE_ID,
        "data": {
            "time": {"value": now_you.strftime("%Y-%m-%d %H:%M")},
            "bf": {"value": weather_you},
            "you": {"value": weather_bf},
            "days": {"value": str(days_together)},
            "countdown": {"value": str(countdown)},
            "love": {"value": love_line}
        }
    }

    return payload


def main():
    force = os.environ.get("FORCE_SEND") == "1"
    now_bf = datetime.now(ZoneInfo(BF_TZ))

    if not force:
        if not (now_bf.hour == 10 and now_bf.minute < 5):
            print("Not in send window.")
            return
    else:
        print("FORCE_SEND enabled.")

    payload = build_payload()
    send_template(payload)


if __name__ == "__main__":
    main()
