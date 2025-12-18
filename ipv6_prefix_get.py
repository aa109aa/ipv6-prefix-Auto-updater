import datetime
import requests
import hashlib
import random
import re
from bs4 import BeautifulSoup

# ================================
# 该脚本主要针对光猫型号：ZXHN F7610M
# 全局变量：用户名、密码、IP、日志文件
# ================================
username="username"
password="password"
base_url = "http://192.168.6.1/"
ipv6_prefix_record = "/root/ipv6_update/ipv6_prefix_record.txt"

# ============================================================
# 工具函数
# ============================================================
def sha256(text: str) -> str:
    """对文本执行 SHA256 加密"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def extract_tokens(html: bytes):
    """从 HTML 中提取 LoginToken 和 CheckToken"""
    soup = BeautifulSoup(html, "html.parser")
    script_tags = soup.find_all("script")
    login_token = None
    check_token = None
    for script in script_tags:
        content = script.string
        if not content:
            continue
        m1 = re.search(r'getObj\("Frm_Logintoken"\)\.value = "([^"]+)"', content)
        m2 = re.search(r'getObj\("Frm_Loginchecktoken"\)\.value = "([^"]+)"', content)
        if m1:
            login_token = m1.group(1)
        if m2:
            check_token = m2.group(1)
    return login_token, check_token

def extract_error_message(html: bytes):
    """提取登录失败提示文本"""
    soup = BeautifulSoup(html, "html.parser")
    script_tags = soup.find_all("script")
    for script in script_tags:
        content = script.string
        if not content:
            continue
        err = re.search(r'getObj\("errmsg"\)\.innerHTML = "([^"]+)"', content)
        if err:
            return err.group(1)
    return "未知错误"

# ============================================================
# 登录光猫
# ============================================================
def login(username, password):
    """登录光猫后台"""
    global base_url
    global ipv6_prefix_record
    session = requests.Session()
    session.verify = False
    # 第一次 GET 取 token
    rsp = session.get(base_url)
    token1, token2 = extract_tokens(rsp.content)
    if not token1 or not token2:
        print("无法提取 token，登录失败")
        return None
    # 生成随机数 + 加密密码
    rand = str(random.randint(10000000, 99999999))
    enc_pwd = sha256(password + rand)
    payload = {
        "Frm_Logintoken": token1,
        "Frm_Loginchecktoken": token2,
        "Right": "",
        "Username": username,
        "UserRandomNum": rand,
        "Password": enc_pwd,
        "action": "login"
    }
    login_rsp = session.post(base_url, data=payload)
    cookies = session.cookies.get_dict()
    if '_Tokens' not in cookies or 'SID' not in cookies:
        failure_r =  extract_error_message(login_rsp.content)
        with open(ipv6_prefix_record, "a", encoding="utf-8") as file:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file.write(f"\n{failure_r} - {current_time}")
        print("登录失败：", failure_r,current_time)
        return None
    # print("登录成功")
    return session

# ============================================================
# 获取 IPv6 前缀
# ============================================================
def get_ipv6_prefix(session: requests.Session):
    global base_url

    headers = {
        "Referer": base_url + "start.ghtml",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    url = base_url + "template.gch"
    params = {
        "pid": "1002",
        "nextpage": "status_wanstatu_ipv6wansta_t.gch"
    }

    rsp = session.get(url, headers=headers, params=params)
    rsp.encoding = "gb2312"

    soup = BeautifulSoup(rsp.text, "html.parser")

    prefix_td = soup.find("td", string="前缀")

    if not prefix_td:
        prefix = "未找到 IPv6 前缀"
    else:
        prefix = prefix_td.find_next(
            "td", class_="tdright"
        ).text.strip()

    # 尝试登出（不影响主流程）
    try:
        m = re.search(r'session_token\s*=\s*"(\d+)"', rsp.text)
        if m:
            session.post(
                base_url,
                headers=headers,
                data={
                    "logout": "1",
                    "_SESSION_TOKEN": m.group(1)
                },
                verify=False,
                timeout=5
            )
    except Exception as e:
        print("登出失败，一分钟后自动登出:", e)

    return prefix

# ============================================================
# 主程序
# ============================================================
def main():
    global ipv6_prefix_record
    session = login(username, password)
    if not session:
        return
    prefix = get_ipv6_prefix(session)
    with open(ipv6_prefix_record, "a", encoding="utf-8") as file:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file.write(f"\n{prefix} - {current_time}")
        print(f"当前 IPv6 前缀：{prefix} - {current_time}")

if __name__ == "__main__":
    main()