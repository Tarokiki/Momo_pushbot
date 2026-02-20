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


def short(text, n=200):
    text = (text or "").replace("\n", " ")
    return text[:n]


def get_access_token():
    url = (
        "https://api.weixin.qq.com/cgi-bin/token"
        f"?grant_type=client_credential&appid={WX_APPID}&secret={WX_SECRET}"
    )
    r = requests.get(url, timeout=20)
    return r.json()["access_token"]


def get_weather(city):
    url = (
        "https://api.qweather.com/v7/weather/now"
        f"?location={city}&key={QWEATHER_KEY}"
    )

    r = requests.get(url, timeout=20)

    if r.status_code != 200:
        raise RuntimeError(f"Weather HTTP {r.status_code}: {short(r.text)}")

    j = r.json()

    if j.get("code") != "200":
        raise RuntimeError(f"Weather API error: {j}")

    now = j["now"]

    return now["text"], now["temp"], now["feelsLike"]


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
        f"{weather_you[0]} {weather_you[1]}°C feels {weather_you[2]}°C\n\n"
        f"{BF_CITY} {now_bf.strftime('%Y-%m-%d %H:%M')}\n"
        f"{weather_bf[0]} {weather_bf[1]}°C feels {weather_bf[2]}°C"
    )

    return {
        "touser": WX_OPENID,
        "template_id": WX_TEMPLATE_ID,
        "data": {
            "msg": {
                "value": content
            }
        }
    }


def send_message(token, payload):
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    r = requests.post(url, json=payload, timeout=20)
    print(r.json())


def main():
    payload = build_message()
    if payload is None:
        return
    token = get_access_token()
    send_message(token, payload)


if __name__ == "__main__":
    main()
