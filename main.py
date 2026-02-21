# -*- coding: utf-8 -*-
import os
import sys
import json
import random
import datetime as dt
import requests


# ---------------------------
# Config (ENV)
# ---------------------------
WX_APPID = os.getenv("WX_APPID", "").strip()
WX_SECRET = os.getenv("WX_SECRET", "").strip()
WX_OPENID = os.getenv("WX_OPENID", "").strip()
WX_TEMPLATE_ID = os.getenv("WX_TEMPLATE_ID", "").strip()

# Cities (can be Chinese/Japanese/English, open-meteo geocoding supports many)
YOU_CITY = os.getenv("YOU_CITY", "Tokyo").strip()
BF_CITY = os.getenv("BF_CITY", "St. Louis").strip()

# Dates (YYYY-MM-DD). Optional; if empty -> still sends something readable.
TOGETHER_DATE = os.getenv("TOGETHER_DATE", "").strip()     # e.g. 2024-01-01
COUNTDOWN_DATE = os.getenv("COUNTDOWN_DATE", "").strip()   # e.g. 2026-12-31

# For debugging
DEBUG = os.getenv("DEBUG", "1").strip() == "1"

# If FORCE_SEND=1 then skip time window checks (you already use it)
FORCE_SEND = os.getenv("FORCE_SEND", "").strip() == "1"


SWEET_LINES = [
    "If today feels heavy, lean on me. I’m right here.",
    "I hope you eat something warm and take a tiny breath for us.",
    "Even on ordinary days, you’re still my favorite place.",
    "I’m cheering for you quietly, constantly, stubbornly.",
    "Miss you is my daily routine, loving you is my default setting.",
    "One day closer to seeing you—until then, I’ll hold you in my thoughts.",
    "Whatever the weather says, my forecast is: you + me = home.",
    "I love you in the small moments, the loud moments, and the in-between.",
    "When you’re tired, remember: you don’t have to be strong alone.",
    "Today, please be gentle with yourself—for me, too.",
]


# ---------------------------
# Helpers
# ---------------------------
def _short(s: str, n: int = 220) -> str:
    s = (s or "").replace("\n", "\\n")
    return s[:n] + ("..." if len(s) > n else "")


def _require_env():
    missing = [k for k, v in {
        "WX_APPID": WX_APPID,
        "WX_SECRET": WX_SECRET,
        "WX_OPENID": WX_OPENID,
        "WX_TEMPLATE_ID": WX_TEMPLATE_ID,
    }.items() if not v]
    if missing:
        raise RuntimeError(f"Missing env: {', '.join(missing)}")


def get_access_token() -> str:
    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {
        "grant_type": "client_credential",
        "appid": WX_APPID,
        "secret": WX_SECRET,
    }
    r = requests.get(url, params=params, timeout=20)
    data = r.json()
    if "access_token" not in data:
        raise RuntimeError(f"get_access_token failed: {_short(json.dumps(data, ensure_ascii=False))}")
    return data["access_token"]


def geocode_city(city: str):
    """
    open-meteo geocoding (no key)
    https://open-meteo.com/en/docs/geocoding-api
    """
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": city, "count": 1, "language": "en", "format": "json"}
    r = requests.get(url, params=params, timeout=20)
    if r.status_code != 200:
        return None
    try:
        j = r.json()
    except Exception:
        return None
    results = j.get("results") or []
    if not results:
        return None
    x = results[0]
    return {
        "name": x.get("name") or city,
        "country": x.get("country") or "",
        "lat": x.get("latitude"),
        "lon": x.get("longitude"),
        "timezone": x.get("timezone") or "auto",
    }


def weather_code_to_text(code: int) -> str:
    # Minimal mapping (enough for cute display)
    m = {
        0: "Clear",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Rime fog",
        51: "Light drizzle",
        53: "Drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Rain",
        65: "Heavy rain",
        71: "Slight snow",
        73: "Snow",
        75: "Heavy snow",
        80: "Rain showers",
        81: "Rain showers",
        82: "Violent showers",
        95: "Thunderstorm",
    }
    return m.get(code, f"Weather code {code}")


def get_weather(city: str) -> str:
    """
    Returns a short text, never empty.
    """
    try:
        geo = geocode_city(city)
        if not geo or geo["lat"] is None or geo["lon"] is None:
            return f"{city}: N/A"

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": geo["lat"],
            "longitude": geo["lon"],
            "current_weather": "true",
            "timezone": "auto",
        }
        r = requests.get(url, params=params, timeout=20)
        if r.status_code != 200:
            return f"{geo['name']}: N/A"

        j = r.json()
        cw = j.get("current_weather") or {}
        temp = cw.get("temperature")
        wind = cw.get("windspeed")
        code = cw.get("weathercode")

        parts = []
        label = geo["name"]
        if geo.get("country"):
            label = f"{label}, {geo['country']}"

        if code is not None:
            parts.append(weather_code_to_text(int(code)))
        if temp is not None:
            parts.append(f"{temp}°C")
        if wind is not None:
            parts.append(f"wind {wind} km/h")

        if not parts:
            return f"{label}: N/A"
        return f"{label}: " + ", ".join(parts)

    except Exception:
        return f"{city}: N/A"


def parse_date(s: str):
    if not s:
        return None
    try:
        return dt.datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def days_between(start_date: dt.date, end_date: dt.date) -> int:
    return (end_date - start_date).days


def build_message() -> dict:
    now = dt.datetime.now()
    today = now.date()

    you_weather = get_weather(YOU_CITY)
    bf_weather = get_weather(BF_CITY)

    together_date = parse_date(TOGETHER_DATE)
    countdown_date = parse_date(COUNTDOWN_DATE)

    if together_date:
        together_days = days_between(together_date, today)
        together_text = f"{together_days} days"
    else:
        together_text = "N/A"

    if countdown_date:
        cd = days_between(today, countdown_date)
        countdown_text = f"{cd} days"
    else:
        countdown_text = "N/A"

    love_line = random.choice(SWEET_LINES)

    # IMPORTANT: keys MUST match template placeholders exactly:
    # time, bf, you, days, countdown, love
    data = {
        "time": {"value": now.strftime("%Y-%m-%d %H:%M")},
        "bf": {"value": bf_weather},
        "you": {"value": you_weather},
        "days": {"value": together_text},
        "countdown": {"value": countdown_text},
        "love": {"value": love_line},
    }

    payload = {
        "touser": WX_OPENID,
        "template_id": WX_TEMPLATE_ID,
        "data": data,
    }
    return payload


def send_template_message(payload: dict) -> dict:
    token = get_access_token()
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    r = requests.post(url, json=payload, timeout=20)
    try:
        data = r.json()
    except Exception:
        raise RuntimeError(f"WeChat send non-json response: HTTP {r.status_code}: {_short(r.text)}")
    return data


def main():
    _require_env()

    if FORCE_SEND:
        print("FORCE_SEND enabled, skip time check.")
    else:
        # If you want time gating later, add it here.
        pass

    payload = build_message()

    if DEBUG:
        print("=== Payload (final) ===")
        safe = dict(payload)
        safe["touser"] = "***"
        safe["template_id"] = "***"
        print(json.dumps(safe, ensure_ascii=False, indent=2))

    resp = send_template_message(payload)

    if DEBUG:
        print("=== WeChat response ===")
        print(json.dumps(resp, ensure_ascii=False, indent=2))

    # WeChat success: errcode == 0
    if resp.get("errcode") != 0:
        raise RuntimeError(f"WeChat send failed: {_short(json.dumps(resp, ensure_ascii=False))}")

    print("Send OK.")


if __name__ == "__main__":
    main()
