import os
import random
import requests
from datetime import datetime, date
from zoneinfo import ZoneInfo

# ====== 环境变量（GitHub Secrets）======
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
NEXT_MEET_DATE = date(2026, 3, 5)

# ====== 文案系统 v2.0（英文，随机发送）======
DAILY_LINES = [
    "I hope your coffee is warm and your code compiles on the first try.",
    "Somewhere between Tokyo and St. Louis, my thoughts are always on you.",
    "I hope today feels lighter than yesterday.",
    "If anything gets hard today, remember I’m quietly on your side.",
    "Even across time zones, you’re still the first person I think of.",
    "I hope the world is gentle with you today.",
    "Save a little piece of your day for me.",
    "May your bugs be small and your wins be big today.",
    "I wish I could see your sleepy face right now.",
    "No matter how busy today gets, I’m still here."
]

ANNIVERSARY_LINES = [
    "Another month loving you, and I’d still choose you all over again.",
    "Every 6th reminds me how lucky I am that we found each other.",
    "I didn’t know distance could feel this steady until you."
]

HUNDRED_DAY_LINES = [
    "{days} days with you, and I still get a little shy thinking about it.",
    "{days} days. That’s a lot of moments I wouldn’t trade for anything.",
    "{days} days of us. I’m proud of what we’re building."
]

FINAL_WEEK_LINES = [
    "One more week. My heart is already walking toward you.",
    "Seven days or less. I’m counting in heartbeats now.",
    "Almost there. I don’t think I’m ready for how happy I’ll be."
]

MEET_TODAY_LINE = "Today. No metaphors. Just me holding you for a long time."

# ====== 工具函数 ======
def qweather_city_lookup(city: str) -> str:
    url = "https://geoapi.qweather.com/v2/city/lookup"
    r = requests.get(url, params={"location": city, "key": QWEATHER_KEY}, timeout=20)
    r.raise_for_status()
    j = r.json()
    if j.get("code") != "200" or not j.get("location"):
        raise RuntimeError(f"QWeather lookup failed for {city}: {j}")
    return j["location"][0]["id"]

def qweather_now(location_id: str) -> dict:
    url = "https://devapi.qweather.com/v7/weather/now"
    r = requests.get(url, params={"location": location_id, "key": QWEATHER_KEY}, timeout=20)
    r.raise_for_status()
    j = r.json()
    if j.get("code") != "200":
        raise RuntimeError(f"QWeather now failed: {j}")
    return j["now"]

def wx_access_token() -> str:
    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {"grant_type": "client_credential", "appid": WX_APPID, "secret": WX_SECRET}
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    j = r.json()
    if "access_token" not in j:
        raise RuntimeError(f"Get access_token failed: {j}")
    return j["access_token"]

def wx_send_template(token: str, payload: dict) -> None:
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    r = requests.post(url, json=payload, timeout=20)
    r.raise_for_status()
    j = r.json()
    if j.get("errcode") != 0:
        raise RuntimeError(f"Send template failed: {j}")

def pick_love_line(now_bf: datetime, together_days: int, countdown_days: int) -> str:
    special_lines = []

    # 每月6号纪念日（按他当地日期）
    if now_bf.day == 6:
        special_lines.append(random.choice(ANNIVERSARY_LINES))

    # 每100天里程碑
    if together_days > 0 and together_days % 100 == 0:
        special_lines.append(random.choice(HUNDRED_DAY_LINES).format(days=together_days))

    # 见面前7天
    if 0 <= countdown_days <= 7:
        special_lines.append(random.choice(FINAL_WEEK_LINES))

    # 见面当天
    if countdown_days == 0:
        return MEET_TODAY_LINE

    base_line = random.choice(DAILY_LINES)
    return " ".join(special_lines + [base_line]) if special_lines else base_line

def main():
    now_bf = datetime.now(ZoneInfo(BF_TZ))

    # 只在 St. Louis 当地时间 10:00 发送（留 5 分钟窗口，适配 Actions 触发抖动）
    if not (now_bf.hour == 10 and now_bf.minute < 5):
        return

    # 计算天数（用日本日期也OK；这里用“今天”即可，误差不会影响体验）
    today = date.today()
    together_days = (today - TOGETHER_SINCE).days
    countdown_days = (NEXT_MEET_DATE - today).days

    # 天气
    you_loc = qweather_city_lookup(YOU_CITY)
    bf_loc = qweather_city_lookup(BF_CITY)
    you_w = qweather_now(you_loc)
    bf_w = qweather_now(bf_loc)

    love_line = pick_love_line(now_bf, together_days, countdown_days)

    payload = {
        "touser": WX_OPENID,
        "template_id": WX_TEMPLATE_ID,
        "data": {
            "time": {"value": f"早呀哥哥～  {now_bf.strftime('%Y-%m-%d %H:%M')}"},
            "bf": {"value": f"{BF_CITY}: {bf_w['text']} {bf_w['temp']}°C"},
            "you": {"value": f"{YOU_CITY}: {you_w['text']} {you_w['temp']}°C"},
            "days": {"value": f"{together_days} days"},
            "countdown": {"value": f"{countdown_days} days"},
            "love": {"value": love_line},
        },
    }

    token = wx_access_token()
    wx_send_template(token, payload)

if __name__ == "__main__":
    main()
