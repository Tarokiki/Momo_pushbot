import os
import random
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

WX_APPID = os.environ["WX_APPID"]
WX_SECRET = os.environ["WX_SECRET"]
WX_OPENID = os.environ["WX_OPENID"]
WX_TEMPLATE_ID = os.environ["WX_TEMPLATE_ID"]
QWEATHER_KEY = os.environ["QWEATHER_KEY"]

FORCE_SEND = os.environ.get("FORCE_SEND", "0") == "1"

YOU_TZ = "Asia/Tokyo"
BF_TZ = "America/Chicago"

YOU_CITY = "Tokyo"
BF_CITY = "St. Louis"

QUOTES = [
    "Hope your day goes smoothly.",
    "Just a tiny reminder: you’re doing great.",
    "Sending you a little sunshine.",
    "Take a deep breath—one step at a time.",
    "Wishing you a calm and productive day.",
]


def get_access_token():
    url = (
        "https://api.weixin.qq.com/cgi-bin/token"
        f"?grant_type=client_credential&appid={WX_APPID}&secret={WX_SECRET}"
    )
    r = requests.get(url)
    return r.json()["access_token"]


def get_weather(city):
    url = (
        "https://devapi.qweather.com/v7/weather/now"
        f"?location={city}&key={QWEATHER_KEY}"
    )

    r = requests.get(url)
    if r.status_code != 200:
        raise RuntimeError(f"Weather HTTP {r.status_code}: {r.text}")

    j = r.json()
    if j.get("code") != "200":
        raise RuntimeError(f"Weather API error: {j}")

    now = j["now"]
    return now["text"], now["temp"], now["feelsLike"]


def build_message():
    now_you = datetime.now(ZoneInfo(YOU_TZ))
    now_bf = datetime.now(ZoneInfo(BF_TZ))

    weather_you = get_weather(YOU_CITY)
    weather_bf = get_weather(BF_CITY)

    quote = random.choice(QUOTES)

    return {
        "touser": WX_OPENID,
        "template_id": WX_TEMPLATE_ID,
        "data": {
            "first": {"value": "Daily Weather Update"},
            "keyword1": {"value": f"{YOU_CITY} {now_you.strftime('%Y-%m-%d %H:%M')}"},
            "keyword2": {"value": f"{weather_you[0]} {weather_you[1]}°C feels {weather_you[2]}°C"},
            "keyword3": {"value": f"{BF_CITY} {now_bf.strftime('%Y-%m-%d %H:%M')}"},
            "keyword4": {"value": f"{weather_bf[0]} {weather_bf[1]}°C feels {weather_bf[2]}°C"},
            "remark": {"value": quote},
        },
    }


def send_message(token, payload):
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    r = requests.post(url, json=payload)
    j = r.json()

    if j.get("errcode") != 0:
        raise RuntimeError(f"WeChat error: {j}")

    print("Message sent:", j)


def main():
    if not FORCE_SEND:
        now_bf = datetime.now(ZoneInfo(BF_TZ))
        if not (now_bf.hour == 10 and now_bf.minute < 5):
            print("Not in send window.")
            return
    else:
        print("FORCE_SEND enabled")

    token = get_access_token()
    payload = build_message()
    send_message(token, payload)


if __name__ == "__main__":
    main()
