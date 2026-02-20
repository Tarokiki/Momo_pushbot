import os
import random
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# ==============================
# 环境变量（GitHub Secrets）
# ==============================

WX_APPID = os.environ["WX_APPID"]
WX_SECRET = os.environ["WX_SECRET"]
WX_OPENID = os.environ["WX_OPENID"]
WX_TEMPLATE_ID = os.environ["WX_TEMPLATE_ID"]
QWEATHER_KEY = os.environ["QWEATHER_KEY"]

FORCE_SEND = os.environ.get("FORCE_SEND", "0") == "1"

# ==============================
# 固定参数
# ==============================

YOU_TZ = "Asia/Tokyo"
BF_TZ = "America/Chicago"

YOU_CITY = "Tokyo"
BF_CITY = "St. Louis"

# ==============================
# 甜甜英文文案
# ==============================

TEXT_POOL = [
    "Hope your day goes smoothly.",
    "Just a tiny reminder: you’re doing great.",
    "Sending you a little sunshine.",
    "Take a deep breath—one step at a time.",
    "Wishing you a calm and productive day.",
    "Stay warm and take care.",
    "Don’t forget to drink some water.",
    "Another day, another chance.",
    "You’ve got this.",
    "Thinking of you today.",
]

# ==============================
# 工具函数
# ==============================

def short(text, n=300):
    text = (text or "").replace("\n", " ")
    return text[:n] + ("..." if len(text) > n else "")


def get_access_token():
    url = (
        "https://api.weixin.qq.com/cgi-bin/token"
        f"?grant_type=client_credential&appid={WX_APPID}&secret={WX_SECRET}"
    )

    r = requests.get(url, timeout=20)

    if r.status_code != 200:
        raise RuntimeError(f"[WeChat Token] HTTP {r.status_code}: {short(r.text)}")

    j = r.json()

    if "access_token" not in j:
        raise RuntimeError(f"[WeChat Token] API error: {j}")

    return j["access_token"]


def get_weather(city_name):
    """
    先通过 GEO 查询 location id
    再通过 Weather Now 获取实时天气
    """

    # ---------- Step 1: GEO ----------
    geo_url = (
        "https://geoapi.qweather.com/v2/city/lookup"
        f"?location={city_name}&key={QWEATHER_KEY}"
    )

    r = requests.get(geo_url, timeout=20)

    if r.status_code != 200:
        raise RuntimeError(f"[QWeather GEO] HTTP {r.status_code}: {short(r.text)}")

    j = r.json()

    if j.get("code") != "200" or not j.get("location"):
        raise RuntimeError(f"[QWeather GEO] API error: {j}")

    location_id = j["location"][0]["id"]

    # ---------- Step 2: Weather ----------
    weather_url = (
        "https://api.qweather.com/v7/weather/now"
        f"?location={location_id}&key={QWEATHER_KEY}"
    )

    r2 = requests.get(weather_url, timeout=20)

    if r2.status_code != 200:
        raise RuntimeError(f"[QWeather NOW] HTTP {r2.status_code}: {short(r2.text)}")

    j2 = r2.json()

    if j2.get("code") != "200":
        raise RuntimeError(f"[QWeather NOW] API error: {j2}")

    now = j2["now"]

    return {
        "text": now.get("text", ""),
        "temp": now.get("temp", ""),
        "feelsLike": now.get("feelsLike", ""),
    }


def build_message():
    now_you = datetime.now(ZoneInfo(YOU_TZ))
    now_bf = datetime.now(ZoneInfo(BF_TZ))

    if not FORCE_SEND:
        if not (now_bf.hour == 10 and now_bf.minute < 5):
            print("Not in send window.")
            return None
    else:
        print("FORCE_SEND enabled")

    weather_you = get_weather(YOU_CITY)
    weather_bf = get_weather(BF_CITY)

    quote = random.choice(TEXT_POOL)

    content = (
        f"{quote}\n\n"
        f"{YOU_CITY} {now_you.strftime('%Y-%m-%d %H:%M')}\n"
        f"{weather_you['text']}  {weather_you['temp']}°C  feels {weather_you['feelsLike']}°C\n\n"
        f"{BF_CITY} {now_bf.strftime('%Y-%m-%d %H:%M')}\n"
        f"{weather_bf['text']}  {weather_bf['temp']}°C  feels {weather_bf['feelsLike']}°C"
    )

    payload = {
        "touser": WX_OPENID,
        "template_id": WX_TEMPLATE_ID,
        "data": {
            "msg": {
                "value": content
            }
        }
    }

    return payload


def send_message(access_token, payload):
    url = (
        "https://api.weixin.qq.com/cgi-bin/message/template/send"
        f"?access_token={access_token}"
    )

    r = requests.post(url, json=payload, timeout=20)

    if r.status_code != 200:
        raise RuntimeError(f"[WeChat Send] HTTP {r.status_code}: {short(r.text)}")

    j = r.json()

    if j.get("errcode") != 0:
        raise RuntimeError(f"[WeChat Send] API error: {j}")

    print("Message sent:", j)


def main():
    payload = build_message()

    if payload is None:
        return

    token = get_access_token()
    send_message(token, payload)


if __name__ == "__main__":
    main()
