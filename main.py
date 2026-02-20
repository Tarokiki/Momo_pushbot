import os
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# ======================
# GitHub Secrets
# ======================
WX_APPID = os.environ["WX_APPID"]
WX_SECRET = os.environ["WX_SECRET"]
WX_OPENID = os.environ["WX_OPENID"]
WX_TEMPLATE_ID = os.environ["WX_TEMPLATE_ID"]

YOU_TZ = "Asia/Tokyo"


def http_get_json(url, params):
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def get_access_token():
    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {
        "grant_type": "client_credential",
        "appid": WX_APPID,
        "secret": WX_SECRET
    }
    data = http_get_json(url, params)
    if "access_token" not in data:
        raise RuntimeError(f"get_access_token failed: {data}")
    return data["access_token"]


def send_template(payload):
    token = get_access_token()
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={token}"
    r = requests.post(url, json=payload, timeout=15)
    data = r.json()
    print("WeChat response:", data)
    if data.get("errcode") != 0:
        raise RuntimeError(f"WeChat send failed: {data}")
    print("Sent OK.")


def build_payload_debug():
    now_you = datetime.now(ZoneInfo(YOU_TZ)).strftime("%Y-%m-%d %H:%M:%S")

    # ✅ 写死每个字段，专门用来确认模板字段名是否对得上
    payload = {
        "touser": WX_OPENID,
        "template_id": WX_TEMPLATE_ID,
        "data": {
            "time": {"value": f"TIME_OK {now_you}"},
            "bf": {"value": "BF_OK AAA"},
            "you": {"value": "YOU_OK BBB"},
            "days": {"value": "DAYS_OK 123"},
            "countdown": {"value": "COUNTDOWN_OK 456"},
            "love": {"value": "LOVE_OK CCC"}
        }
    }

    print("=== Payload to send ===")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print("=======================")

    return payload


def main():
    # 强制发一次
    payload = build_payload_debug()
    send_template(payload)


if __name__ == "__main__":
    main()
