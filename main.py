import os
import random
import requests
from datetime import datetime, date
from zoneinfo import ZoneInfo


# ====== 环境变量（GitHub Secrets） ======
WX_APPID = os.environ["WX_APPID"]
WX_SECRET = os.environ["WX_SECRET"]
WX_OPENID = os.environ["WX_OPENID"]
WX_TEMPLATE_ID = os.environ["WX_TEMPLATE_ID"]
QWEATHER_KEY = os.environ["QWEATHER_KEY"]

FORCE_SEND = os.environ.get("FORCE_SEND", "0") == "1"


# ====== 固定参数 ======
YOU_TZ = "Asia/Tokyo"
BF_TZ = "America/Chicago"

YOU_CITY = "Tokyo,JP"
BF_CITY = "St Louis,US"

TOGETHER_DATE = date(2024, 12, 6)
NEXT_MEET_DATE = date(2026, 3, 5)

GREETING = "早呀哥哥～"

LOVE_LINES = [
    "You’re my favorite notification.",
    "I’m rooting for you in everything you do.",
    "I wish I could be there to steal one real hug.",
    "You make my days softer, even from far away.",
    "If today gets heavy, lean on me—always.",
    "I’m proud of you, more than you think.",
    "I love the life we’re building, one day at a time.",
    "You’re the calm I keep coming back to.",
    "I’m so lucky it’s you.",
    "No matter the distance, you’re still my home base.",
]


def _short(text: str, n: int = 200) -> str:
    return (text or "").replace("\n", " ").strip()[:n]


# ====== 天气 ======
def get_weather(city: str) -> dict:
    geo_url = (
        "https://devapi.qweather.com/v2/city/lookup"
        f"?location={city}&key={QWEATHER_KEY}"
    )

    r = requests.get(geo_url, timeout=15)
    if r.status_code != 200:
        raise RuntimeError(f"[QWeather GEO] HTTP {r.status_code}: {_short(r.text)}")

    geo = r.json()
    if str(geo.get("code")) != "200" or not geo.get("location"):
        raise RuntimeError(f"[QWeather GEO] bad response: {geo}")

    location_id = geo["location"][0]["id"]

    now_url = (
        "https://devapi.qweather.com/v7/weather/now"
        f"?location={location_id}&key={QWEATHER_KEY}"
    )

    r2 = requests.get(now_url, timeout=15)
    if r2.status_code != 200:
        raise RuntimeError(f"[QWeather NOW] HTTP {r2.status_code}: {_short(r2.text)}")

    w = r2.json()
    if str(w.get("code")) != "200":
        raise RuntimeError(f"[QWeather NOW] bad response: {w}")

    now = w["now"]
    return {
        "text": now.get("text", ""),
        "temp_c": now.get("temp", ""),
        "feels_c": now.get("feelsLike", ""),
    }


# ====== 微信 ======
def get_access_token() -> str:
    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {
        "grant_type": "client_credential",
        "appid": WX_APPID,
        "secret": WX_SECRET,
    }

    r = requests.get(url, params=params, timeout=15)
    data = r.json()

    if "access_token" not in data:
        raise RuntimeError(f"[WeChat token] failed: {data}")

    return data["access_token"]


def send_template_message(token: str, payload: dict):
    url = "https://api.weixin.qq.com/cgi-bin/message/template/send"
    r = requests.post(url, params={"access_token": token}, json=payload, timeout=15)
    data = r.json()

    if data.get("errcode") != 0:
        raise RuntimeError(f"[WeChat send] failed: {data}")

    return data


# ====== 构建消息 ======
def build_message() -> dict:
    now_you = datetime.now(ZoneInfo(YOU_TZ))
    now_bf = datetime.now(ZoneInfo(BF_TZ))

    if not FORCE_SEND:
        if not (now_bf.hour == 10 and 0 <= now_bf.minute < 5):
            print("Skip: not in send time window.")
            return {}

    weather_you = get_weather(YOU_CITY)
    weather_bf = get_weather(BF_CITY)

    today = now_you.date()
    days_together = (today - TOGETHER_DATE).days
    days_to_meet = (NEXT_MEET_DATE - today).days

    love = random.choice(LOVE_LINES)

    first = (
        f"{GREETING}\n"
        f"Tokyo {now_you.strftime('%Y-%m-%d %H:%M')} / "
        f"St. Louis {now_bf.strftime('%Y-%m-%d %H:%M')}"
    )

    payload = {
        "touser": WX_OPENID,
        "template_id": WX_TEMPLATE_ID,
        "data": {
            "first": {"value": first},
            "keyword1": {"value": f"Tokyo: {weather_you['text']} {weather_you['temp_c']}°C"},
            "keyword2": {"value": f"St. Louis: {weather_bf['text']} {weather_bf['temp_c']}°C"},
            "keyword3": {"value": f"Together: {days_together} days"},
            "keyword4": {"value": f"Next meet: {days_to_meet} days"},
            "remark": {"value": love},
        },
    }

    return payload


# ====== 主函数 ======
def main():
    payload = build_message()
    if not payload:
        return

    token = get_access_token()
    result = send_template_message(token, payload)
    print("Sent:", result)


if __name__ == "__main__":
    main()
