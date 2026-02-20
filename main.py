import os
import random
import requests
from datetime import datetime, date
from zoneinfo import ZoneInfo

# ====== GitHub Secrets ======
WX_APPID = os.environ["WX_APPID"]
WX_SECRET = os.environ["WX_SECRET"]
WX_OPENID = os.environ["WX_OPENID"]
WX_TEMPLATE_ID = os.environ["WX_TEMPLATE_ID"]
QWEATHER_KEY = os.environ["QWEATHER_KEY"]

# ====== 固定参数 ======
YOU_TZ = "Asia/Tokyo"
BF_TZ = "America/Chicago"  # St. Louis

YOU_CITY = "Tokyo"
BF_CITY = "St. Louis"

TOGETHER_SINCE = date(2024, 12, 6)
NEXT_MEET = date(2026, 3, 5)

# ====== 英文 love lines ======
LOVE_LINES = [
    "You are the calm in my chaos.",
    "No matter the distance, I'm always right beside you.",
    "You make ordinary days feel magical.",
    "I fall for you a little more every day.",
    "Even miles apart, my heart stays with you.",
    "You're my favorite notification.",
    "Being yours is my favorite thing.",
    "You are my safest place in this world.",
    "Loving you feels like home.",
    "Forever isn't long enough with you."
]


def get_access_token():
    url = (
        "https://api.weixin.qq.com/cgi-bin/token"
        f"?grant_type=client_credential&appid={WX_APPID}&secret={WX_SECRET}"
    )
    return requests.get(url).json()["access_token"]


def get_weather(city):
    geo_url = f"https://geoapi.qweather.com/v2/city/lookup?location={city}&key={QWEATHER_KEY}"
    geo = requests.get(geo_url).json()
    location_id = geo["location"][0]["id"]

    weather_url = f"https://devapi.qweather.com/v7/weather/now?location={location_id}&key={QWEATHER_KEY}"
    weather = requests.get(weather_url).json()
    now = weather["now"]

    return f"{now['text']} {now['temp']}°C"


def main():
    now_you = datetime.now(ZoneInfo(YOU_TZ))
    now_bf = datetime.now(ZoneInfo(BF_TZ))

    # ✅ 加入强制发送开关
    if os.environ.get("FORCE_SEND") != "1":
        if not (now_bf.hour == 10 and now_bf.minute < 5):
            return

    days_together = (date.today() - TOGETHER_SINCE).days
    days_to_meet = (NEXT_MEET - date.today()).days

    weather_you = get_weather(YOU_CITY)
    weather_bf = get_weather(BF_CITY)

    love_line = random.choice(LOVE_LINES)

    access_token = get_access_token()

    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"

    data = {
        "touser": WX_OPENID,
        "template_id": WX_TEMPLATE_ID,
        "data": {
            "time": {"value": now_bf.strftime("%Y-%m-%d %H:%M")},
            "weather_bf": {"value": weather_bf},
            "weather_you": {"value": weather_you},
            "days_together": {"value": str(days_together)},
            "days_to_meet": {"value": str(days_to_meet)},
            "love_line": {"value": love_line},
        }
    }

    requests.post(url, json=data)


if __name__ == "__main__":
    main()
