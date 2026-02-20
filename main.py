import os
import re
import json
import random
import requests
from datetime import datetime, date
from zoneinfo import ZoneInfo

# ======================
# GitHub Secrets (WeChat)
# ======================
WX_APPID = os.environ["WX_APPID"]
WX_SECRET = os.environ["WX_SECRET"]
WX_OPENID = os.environ["WX_OPENID"]
WX_TEMPLATE_ID = os.environ["WX_TEMPLATE_ID"]

FORCE_SEND = os.environ.get("FORCE_SEND", "0") == "1"

# ======================
# Config
# ======================
YOU_TZ = "Asia/Tokyo"
BF_TZ = "America/Chicago"  # St. Louis

YOU_CITY = "Tokyo"
BF_CITY = "St. Louis"

TOGETHER_DATE = date(2024, 12, 6)
NEXT_MEET_DATE = date(2026, 3, 5)

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


def _short(s: str, n: int = 220) -> str:
    s = (s or "").strip().replace("\n", " ")
    return s[:n] + ("..." if len(s) > n else "")


def http_get_json(url: str, params: dict | None = None, timeout: int = 15) -> dict:
    r = requests.get(url, params=params, timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {_short(r.text)}")
    try:
        return r.json()
    except Exception:
        raise RuntimeError(f"Invalid JSON: {_short(r.text)}")


def http_post_json(url: str, payload: dict, timeout: int = 15) -> dict:
    r = requests.post(url, json=payload, timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {_short(r.text)}")
    return r.json()


# ======================
# Open-Meteo Weather
# ======================
def get_latlon(city: str) -> tuple[float, float]:
    data = http_get_json(GEOCODE_URL, {"name": city, "count": 1, "language": "en", "format": "json"})
    results = data.get("results") or []
    if not results:
        raise RuntimeError(f"Geocoding not found: {city}")
    item = results[0]
    return float(item["latitude"]), float(item["longitude"])


def get_weather_line(city: str, tz: str) -> str:
    lat, lon = get_latlon(city)
    data = http_get_json(
        WEATHER_URL,
        {
            "latitude": lat,
            "longitude": lon,
            "current_weather": "true",
            "timezone": tz,
        },
    )
    cw = data.get("current_weather")
    if not cw:
        raise RuntimeError(f"No current_weather for {city}")
    temp = cw.get("temperature")
    wind = cw.get("windspeed")
    return f"{city}: {temp}°C (wind {wind} km/h)"


# ======================
# WeChat
# ======================
def get_access_token() -> str:
    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {"grant_type": "client_credential", "appid": WX_APPID, "secret": WX_SECRET}
    data = http_get_json(url, params=params)
    token = data.get("access_token")
    if not token:
        raise RuntimeError(f"Failed to get access_token: {data}")
    return token


def get_template_field_keys(token: str, template_id: str) -> list[str]:
    """
    从微信接口拉取“真实模板内容”，解析出 {{xxx.DATA}} 里的 xxx
    """
    url = f"https://api.weixin.qq.com/cgi-bin/template/get_all_private_template?access_token={token}"
    data = http_get_json(url)

    if "template_list" not in data:
        raise RuntimeError(f"Cannot get template list: {data}")

    tpl = None
    for t in data["template_list"]:
        if t.get("template_id") == template_id:
            tpl = t
            break

    if not tpl:
        raise RuntimeError(
            "Template ID not found in get_all_private_template. "
            "Check WX_TEMPLATE_ID in GitHub Secrets."
        )

    content = tpl.get("content", "")
    # 解析所有 {{xxx.DATA}}
    keys = re.findall(r"\{\{(\w+)\.DATA\}\}", content)

    # 去重但保序
    seen = set()
    uniq = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            uniq.append(k)

    print("=== Template content (from API) ===")
    print(content)
    print("=== Extracted keys ===")
    print(uniq)

    if not uniq:
        raise RuntimeError("No {{xxx.DATA}} fields found in template content returned by API.")

    return uniq


def send_template_message(token: str, payload: dict) -> dict:
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    resp = http_post_json(url, payload)
    if resp.get("errcode") != 0:
        raise RuntimeError(f"WeChat send failed: {resp}")
    return resp


# ======================
# Build message
# ======================
def main():
    now_you = datetime.now(ZoneInfo(YOU_TZ))
    now_bf = datetime.now(ZoneInfo(BF_TZ))

    # 时间闸门：默认只在男友当地 10:00~10:04 发送
    if not FORCE_SEND:
        if not (now_bf.hour == 10 and now_bf.minute < 5):
            print(f"Skip: BF time is {now_bf.strftime('%H:%M')} (need 10:00~10:04).")
            return
    else:
        print("FORCE_SEND enabled, skip time check.")

    # 生成内容
    time_str = now_you.strftime("%Y-%m-%d %H:%M")
    weather_you = get_weather_line(YOU_CITY, YOU_TZ)
    weather_bf = get_weather_line(BF_CITY, BF_TZ)

    days_together = (now_you.date() - TOGETHER_DATE).days
    days_to_meet = (NEXT_MEET_DATE - now_you.date()).days
    love = random.choice(SWEET_LINES)

    # 拿真实字段名（自动适配）
    token = get_access_token()
    keys = get_template_field_keys(token, WX_TEMPLATE_ID)

    # 按顺序塞值：如果模板字段多于6个，多出来的字段填空字符串
    values = [
        time_str,                         # 1 时间
        weather_you,                      # 2 your weather
        weather_bf,                       # 3 my weather
        str(days_together),               # 4 together days
        str(days_to_meet),                # 5 countdown
        love,                             # 6 love line
    ]

    data = {}
    for i, k in enumerate(keys):
        v = values[i] if i < len(values) else ""
        data[k] = {"value": v}

    payload = {
        "touser": WX_OPENID,
        "template_id": WX_TEMPLATE_ID,
        "data": data,
    }

    print("=== Payload (final) ===")
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    result = send_template_message(token, payload)
    print("Sent OK:", result)


if __name__ == "__main__":
    main()
