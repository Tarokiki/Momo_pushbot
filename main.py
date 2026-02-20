import os
import random
import requests
from datetime import datetime, date
from zoneinfo import ZoneInfo


# ====== 环境变量（GitHub Secrets）======
WX_APPID = os.environ["WX_APPID"]
WX_SECRET = os.environ["WX_SECRET"]
WX_OPENID = os.environ["WX_OPENID"]          # 接收者 openid
WX_TEMPLATE_ID = os.environ["WX_TEMPLATE_ID"]
QWEATHER_KEY = os.environ["QWEATHER_KEY"]

# 可选：Actions 里手动跑时设置 FORCE_SEND=1 可强制发送
FORCE_SEND = os.environ.get("FORCE_SEND", "0") == "1"


# ====== 固定参数 ======
YOU_TZ = "Asia/Tokyo"
BF_TZ = "America/Chicago"   # St. Louis
YOU_CITY = "Tokyo"
BF_CITY = "St. Louis"


# ====== 文案池（你觉得肉麻可以随时改这里）======
QUOTES = [
    "Hope your day goes smoothly.",
    "Just a tiny reminder: you’re doing great.",
    "Sending you a little sunshine.",
    "Take a deep breath—one step at a time.",
    "Wishing you a calm and productive day.",
]


def _short(text: str, n: int = 200) -> str:
    """截断长文本，方便日志显示"""
    text = (text or "").strip().replace("\n", " ")
    return text[:n] + ("..." if len(text) > n else "")


def get_access_token() -> str:
    """获取微信公众号 access_token"""
    url = (
        "https://api.weixin.qq.com/cgi-bin/token"
        f"?grant_type=client_credential&appid={WX_APPID}&secret={WX_SECRET}"
    )
    r = requests.get(url, timeout=15)
    if r.status_code != 200:
        raise RuntimeError(f"[WeChat token] HTTP {r.status_code}: {_short(r.text)}")

    j = r.json()
    if "access_token" not in j:
        raise RuntimeError(f"[WeChat token] bad response: {j}")
    return j["access_token"]


def get_weather(city: str) -> dict:
    """
    获取城市天气：
    - 城市查询（GEO）：geoapi.qweather.com
    - 天气实况（NOW）：devapi.qweather.com
    """
    # 1) 城市查询（正确域名 geoapi）
    geo_url = (
        "https://geoapi.qweather.com/v2/city/lookup"
        f"?location={city}&key={QWEATHER_KEY}"
    )
    r = requests.get(geo_url, timeout=15)
    if r.status_code != 200:
        raise RuntimeError(f"[QWeather GEO] HTTP {r.status_code}: {_short(r.text)}")

    geo = r.json()
    if str(geo.get("code")) != "200" or not geo.get("location"):
        raise RuntimeError(f"[QWeather GEO] bad response: {geo}")

    location_id = geo["location"][0]["id"]

    # 2) 天气实况（正确域名 devapi）
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


def build_message() -> dict:
    """构造模板消息 payload（字段名要和你公众号模板里的关键词对应）"""
    now_you = datetime.now(ZoneInfo(YOU_TZ))
    now_bf = datetime.now(ZoneInfo(BF_TZ))

    weather_you = get_weather(YOU_CITY)
    weather_bf = get_weather(BF_CITY)

    quote = random.choice(QUOTES)

    # 这里的 keyword1/keyword2/... 必须与你的模板消息“关键词”一致
    # 如果你的模板不是 keyword1 这种命名，告诉我模板截图我给你改到完全匹配
    data = {
        "first": {"value": "Daily Weather", "color": "#173177"},
        "keyword1": {"value": now_you.strftime("%Y-%m-%d %H:%M") + f" ({YOU_CITY})"},
        "keyword2": {"value": f"{weather_you['text']}  {weather_you['temp_c']}°C  feels {weather_you['feels_c']}°C"},
        "keyword3": {"value": now_bf.strftime("%Y-%m-%d %H:%M") + f" ({BF_CITY})"},
        "keyword4": {"value": f"{weather_bf['text']}  {weather_bf['temp_c']}°C  feels {weather_bf['feels_c']}°C"},
        "remark": {"value": quote},
    }

    payload = {
        "touser": WX_OPENID,
        "template_id": WX_TEMPLATE_ID,
        "data": data,
    }
    return payload


def send_template_message(token: str, payload: dict) -> dict:
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    r = requests.post(url, json=payload, timeout=15)
    if r.status_code != 200:
        raise RuntimeError(f"[WeChat send] HTTP {r.status_code}: {_short(r.text)}")

    j = r.json()
    # errcode=0 表示成功
    if int(j.get("errcode", -1)) != 0:
        raise RuntimeError(f"[WeChat send] failed: {j}")
    return j


def main():
    # 时间限制：默认只在男朋友时区 10:00-10:04 之间发送（每天一次窗口）
    # Actions 手动跑测试：在 workflow 里设置 FORCE_SEND=1 可以跳过限制
    now_bf = datetime.now(ZoneInfo(BF_TZ))

    if not FORCE_SEND:
        if not (now_bf.hour == 10 and now_bf.minute < 5):
            print(f"Skip: BF time is {now_bf.strftime('%H:%M')} (need 10:00-10:04).")
            return
    else:
        print("FORCE_SEND=1, skip time check.")

    token = get_access_token()
    payload = build_message()
    resp = send_template_message(token, payload)
    print("Sent OK:", resp)


if __name__ == "__main__":
    main()
