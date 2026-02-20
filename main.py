import os
import random
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# ======================
# GitHub Secrets (WeChat)
# ======================
WX_APPID = os.environ["WX_APPID"]
WX_SECRET = os.environ["WX_SECRET"]
WX_OPENID = os.environ["WX_OPENID"]
WX_TEMPLATE_ID = os.environ["WX_TEMPLATE_ID"]

# ======================
# Fixed config
# ======================
YOU_TZ = "Asia/Tokyo"
BF_TZ = "America/Chicago"  # St. Louis
YOU_CITY = "Tokyo"
BF_CITY = "St. Louis"

# Sweet 10 lines (keep it sweet)
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

# Open-Meteo endpoints (NO KEY needed)
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


def _short(s: str, n: int = 180) -> str:
    s = (s or "").strip().replace("\n", " ")
    return s[:n] + ("..." if len(s) > n else "")


def http_get_json(url: str, params: dict, timeout: int = 15) -> dict:
    r = requests.get(url, params=params, timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {_short(r.text)}")
    try:
        return r.json()
    except Exception:
        raise RuntimeError(f"Invalid JSON: {_short(r.text)}")


def get_latlon(city: str) -> tuple[float, float, str]:
    """
    Use Open-Meteo geocoding to resolve city -> lat/lon.
    """
    data = http_get_json(GEOCODE_URL, {"name": city, "count": 1, "language": "en", "format": "json"})
    results = data.get("results") or []
    if not results:
        raise RuntimeError(f"Geocoding not found for city='{city}'")
    item = results[0]
    lat = float(item["latitude"])
    lon = float(item["longitude"])
    # A nicer display name if available
    disp = item.get("name", city)
    country = item.get("country")
    admin1 = item.get("admin1")
    nice = disp
    if admin1:
        nice += f", {admin1}"
    if country:
        nice += f", {country}"
    return lat, lon, nice


def get_weather(city: str, tz: str) -> dict:
    """
    Returns dict with: name, temp_c, wind_kmh, code, time_local
    Uses Open-Meteo current weather.
    """
    lat, lon, nice = get_latlon(city)

    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": "true",
        "timezone": tz,  # let Open-Meteo format time in the target tz
    }
    data = http_get_json(WEATHER_URL, params)

    cw = data.get("current_weather")
    if not cw:
        raise RuntimeError(f"No current_weather returned for '{city}'")

    # Open-Meteo returns temperature in Celsius by default
    temp_c = cw.get("temperature")
    wind_kmh = cw.get("windspeed")
    code = cw.get("weathercode")
    time_str = cw.get("time")  # already in timezone=tz

    return {
        "name": nice,
        "temp_c": temp_c,
        "wind_kmh": wind_kmh,
        "code": code,
        "time_local": time_str,
    }


def weather_code_text(code: int | None) -> str:
    """
    Simple mapping. (Not exhaustive but good enough.)
    Open-Meteo weather codes: https://open-meteo.com/en/docs
    """
    if code is None:
        return "Unknown"
    mapping = {
        0: "Clear",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Rime fog",
        51: "Light drizzle",
        53: "Drizzle",
        55: "Heavy drizzle",
        61: "Light rain",
        63: "Rain",
        65: "Heavy rain",
        71: "Light snow",
        73: "Snow",
        75: "Heavy snow",
        80: "Rain showers",
        81: "Heavy showers",
        82: "Violent showers",
        95: "Thunderstorm",
        96: "Thunderstorm + hail",
        99: "Thunderstorm + heavy hail",
    }
    return mapping.get(int(code), f"Code {code}")


def get_access_token() -> str:
    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {"grant_type": "client_credential", "appid": WX_APPID, "secret": WX_SECRET}
    data = http_get_json(url, params)
    token = data.get("access_token")
    if not token:
        raise RuntimeError(f"Failed to get access_token: {_short(str(data))}")
    return token


def send_template_message(payload: dict) -> dict:
    token = get_access_token()
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    r = requests.post(url, json=payload, timeout=15)
    if r.status_code != 200:
        raise RuntimeError(f"WeChat send HTTP {r.status_code}: {_short(r.text)}")
    data = r.json()
    # errcode == 0 means ok
    if data.get("errcode") != 0:
        raise RuntimeError(f"WeChat send failed: {_short(str(data))}")
    return data


def build_message() -> dict:
    # get time in both zones (for display)
    now_you = datetime.now(ZoneInfo(YOU_TZ))
    now_bf = datetime.now(ZoneInfo(BF_TZ))

    weather_you = get_weather(YOU_CITY, YOU_TZ)
    weather_bf = get_weather(BF_CITY, BF_TZ)

    sweet = random.choice(SWEET_LINES)

    # You can adjust these fields to match your template's keywords
    # Common: first, keyword1..keyword5, remark
    first_text = "Daily love push 💌"
    remark_text = sweet

    you_line = f"{weather_you['name']}: {weather_you['temp_c']}°C, {weather_code_text(weather_you['code'])}"
    bf_line = f"{weather_bf['name']}: {weather_bf['temp_c']}°C, {weather_code_text(weather_bf['code'])}"

    time_line = f"Tokyo {now_you.strftime('%Y-%m-%d %H:%M')} | St. Louis {now_bf.strftime('%Y-%m-%d %H:%M')}"

    payload = {
        "touser": WX_OPENID,
        "template_id": WX_TEMPLATE_ID,
        # "url": "",  # optional
        "data": {
            "first": {"value": first_text},
            "keyword1": {"value": time_line},
            "keyword2": {"value": you_line},
            "keyword3": {"value": bf_line},
            "keyword4": {"value": sweet},
            "remark": {"value": remark_text},
        },
    }
    return payload


def main():
    # Time gate: only send at BF 10:00-10:04 unless FORCE_SEND=1
    force = os.environ.get("FORCE_SEND", "").strip() == "1"
    now_bf = datetime.now(ZoneInfo(BF_TZ))

    if force:
        print("FORCE_SEND enabled, skip time check.")
    else:
        # Only allow 10:00-10:04 (inclusive minute 0-4)
        if not (now_bf.hour == 10 and now_bf.minute < 5):
            print(f"Skip: BF time now {now_bf.strftime('%H:%M')}, not in 10:00-10:04 window.")
            return

    payload = build_message()
    resp = send_template_message(payload)
    print("Sent OK:", resp)


if __name__ == "__main__":
    main()
