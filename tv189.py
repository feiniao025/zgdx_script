#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
天翼超高清全自动任务脚本
"""

import random
import requests
from typing import Optional


# ==================== 配置区 ====================

# 任务中心 Cookie (抓包域名: h5.nty.tv189.com)
USER_COOKIE = ""

# ==================== 常量定义 ====================

BASE_URL = "https://h5.nty.tv189.com"

COMMON_HEADERS = {
    "Host": "h5.nty.tv189.com",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
        "appstore-newtysx-ios-UA-2.30.14.5"
    ),
    "Cookie": USER_COOKIE,
    "Referer": "https://h5.nty.tv189.com/csite/tysx/task/main",
}

VIDEO_REWARD_STAGES = [1, 5, 30]


# ==================== 工具函数 ====================


def api_get(url_path: str) -> Optional[dict]:
    """通用 GET 请求"""
    separator = "&" if "?" in url_path else "?"
    url = f"{BASE_URL}{url_path}{separator}{random.random()}"

    try:
        resp = requests.get(url, headers=COMMON_HEADERS, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except (requests.RequestException, ValueError):
        pass
    return None


# ==================== 任务函数 ====================


def task_sign_in() -> None:
    """每日签到"""
    api_get("/api/portal/task/integralpresentforsign")


def task_share() -> None:
    """分享任务"""
    api_get("/api/portal/task/shareintegralapply")


def task_vip_bonus() -> None:
    """VIP 奖励领取"""
    api_get("/api/portal/task/vipintegralapply")
    api_get("/api/portal/task/getrollvip")


def task_festival() -> None:
    """节日活动奖励"""
    api_get("/api/portal/task/festival-get")


def claim_video_rewards() -> None:
    """领取视频观看奖励"""
    for minutes in VIDEO_REWARD_STAGES:
        url = f"{BASE_URL}/api/portal/task/playtask?e={minutes}"
        try:
            resp = requests.get(url, headers=COMMON_HEADERS, timeout=10)
            result = resp.json()
            if result.get("code") == 0:
                info = result.get("info", {})
                if info.get("resultDetails"):
                    print(f"[成功] 观看{minutes}分钟奖励")
        except (requests.RequestException, ValueError):
            pass


def query_points() -> Optional[float]:
    """查询元气值"""
    data = api_get("/api/portal/task/integralquery")
    if data and "intergral" in data:
        return data["intergral"] / 10
    return None


# ==================== 主函数 ====================


def main() -> None:
    if not USER_COOKIE:
        print("[错误] 请先配置 USER_COOKIE")
        return

    # 执行任务
    task_sign_in()
    task_share()
    task_vip_bonus()
    task_festival()
    claim_video_rewards()

    # 查询最终积分
    points = query_points()
    if points is not None:
        print(f"[积分] 当前元气值: {points}")


if __name__ == "__main__":
    main()
