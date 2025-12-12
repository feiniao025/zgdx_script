"""
============================================
电信任务自动化脚本 
功能：签到、抽奖、任务完成、喂食等
============================================

环境变量配置：
    chinaTelecomAccount: 手机号#密码 (多个账号用&分隔)
    格式示例: 13800138000#password123&13900139000#password456

cron: 0 8 * * *
new Env('电信任务');
"""

import os
import sys
import json
import time
import random
import string
import base64
import asyncio
import certifi
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

# 加密库
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5, DES3, AES
from Crypto.Util.Padding import pad, unpad

# 同步请求库
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context


# ============================================
# 全局配置
# ============================================

# RSA公钥 - 登录认证用
RSA_PUBLIC_KEY_LOGIN = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDBkLT15ThVgz6/NOl6s8GNPofdWzWbCkWnkaAm7O2LjkM1H7dMvzkiqdxU02jamGRHLX/ZNMCXHnPcW/sDhiFCBN18qFvy8g6VYb9QtroI09e176s+ZCtiv7hbin2cCTj99iUpnEloZm19lwHyo69u5UMiPMpq0/XKBO8lYhN/gwIDAQAB
-----END PUBLIC KEY-----"""

# RSA公钥 - 参数加密用
RSA_PUBLIC_KEY_DATA = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC+ugG5A8cZ3FqUKDwM57GM4io6JGcStivT8UdGt67PEOihLZTw3P7371+N47PrmsCpnTRzbTgcupKtUv8ImZalYk65dU8rjC/ridwhw9ffW2LBwvkEnDkkKKRi2liWIItDftJVBiWOh17o6gfbPoNrWORcAdcbpk2L+udld5kZNwIDAQAB
-----END PUBLIC KEY-----"""

# 3DES密钥和IV
DES3_KEY = b'1234567`90koiuyhgtfrdews'
DES3_IV = 8 * b'\0'

# AES密钥
AES_KEY_DEFAULT = b'34d7cb0bcdf07523'
AES_KEY_LOGIN = 'telecom_wap_2018'

# 缓存文件路径
CACHE_FILE = Path(__file__).parent / 'Cache.json'

# 全局变量
global_logs: List[str] = []
cache: Dict[str, Any] = {}


# ============================================
# SSL适配器配置
# ============================================

class CustomSSLAdapter(HTTPAdapter):
    """自定义SSL适配器，兼容旧版TLS"""

    def __init__(self, *args, **kwargs):
        self.ciphers = 'DEFAULT@SECLEVEL=1:!aNULL:!eNULL:!MD5'
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context(ciphers=self.ciphers)
        context.check_hostname = False
        kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **kwargs)


def create_session() -> requests.Session:
    """创建配置好的请求会话"""
    session = requests.Session()
    session.verify = certifi.where()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Linux; U; Android 12; zh-cn; ONEPLUS A9000 Build/QKQ1.190716.003) AppleWebKit/533.1 (KHTML, like Gecko) Version/5.0 Mobile Safari/533.1'
    })
    session.mount('https://', CustomSSLAdapter())
    return session


# 全局会话
session = create_session()


# ============================================
# 日志函数
# ============================================

def log(message: str) -> None:
    """输出带时间戳的日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{timestamp}] {message}"
    global_logs.append(log_message)
    print(log_message)


def mask_phone(phone: str) -> str:
    """手机号脱敏处理"""
    if len(phone) >= 7:
        return f"{phone[:3]}****{phone[-4:]}"
    return phone


# ============================================
# 工具函数
# ============================================

def get_timestamp() -> str:
    """生成时间戳字符串 (格式：YYYYMMDDHHmmss)"""
    return datetime.now().strftime('%Y%m%d%H%M%S')


def random_string(length: int) -> str:
    """生成指定长度的随机字符串"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


async def wait(ms: int) -> None:
    """异步等待指定毫秒数"""
    await asyncio.sleep(ms / 1000)


def sync_wait(seconds: float) -> None:
    """同步等待指定秒数"""
    time.sleep(seconds)


# ============================================
# 加密函数
# ============================================

def encrypt_des3(data: str) -> str:
    """3DES CBC模式加密"""
    cipher = DES3.new(DES3_KEY, DES3.MODE_CBC, DES3_IV)
    padded_data = pad(data.encode('utf-8'), DES3.block_size)
    encrypted = cipher.encrypt(padded_data)
    return encrypted.hex()


def decrypt_des3(encrypted_hex: str) -> str:
    """3DES CBC模式解密"""
    encrypted_data = bytes.fromhex(encrypted_hex)
    cipher = DES3.new(DES3_KEY, DES3.MODE_CBC, DES3_IV)
    decrypted = cipher.decrypt(encrypted_data)
    return unpad(decrypted, DES3.block_size).decode('utf-8')


def encrypt_aes_hex(data: str, key: bytes = AES_KEY_DEFAULT) -> str:
    """AES ECB模式加密 (返回十六进制)"""
    if isinstance(data, dict):
        data = json.dumps(data, separators=(',', ':'))
    cipher = AES.new(key, AES.MODE_ECB)
    padded_data = pad(data.encode('utf-8'), AES.block_size)
    encrypted = cipher.encrypt(padded_data)
    return encrypted.hex()


def encrypt_aes_base64(data: str, key: str) -> str:
    """AES ECB模式加密 (返回Base64)"""
    key_bytes = key.encode('utf-8')
    if len(key_bytes) not in [16, 24, 32]:
        raise ValueError(f"AES密钥长度必须为16/24/32字节，当前为{len(key_bytes)}字节")

    cipher = AES.new(key_bytes, AES.MODE_ECB)
    padded_data = pad(data.encode('utf-8'), AES.block_size)
    encrypted = cipher.encrypt(padded_data)
    return base64.b64encode(encrypted).decode('utf-8')


def encrypt_rsa_base64(data: str) -> str:
    """RSA加密 (返回Base64，用于登录认证)"""
    public_key = RSA.import_key(RSA_PUBLIC_KEY_LOGIN)
    cipher = PKCS1_v1_5.new(public_key)
    encrypted = cipher.encrypt(data.encode('utf-8'))
    return base64.b64encode(encrypted).decode('utf-8')


def encrypt_rsa_hex(data: str) -> str:
    """RSA加密 (返回十六进制，支持分段加密)"""
    public_key = RSA.import_key(RSA_PUBLIC_KEY_DATA)
    cipher = PKCS1_v1_5.new(public_key)

    if isinstance(data, dict):
        data = json.dumps(data, separators=(',', ':'))

    # 分段加密，每段32字符
    result = ''
    for i in range(0, len(data), 32):
        chunk = data[i:i+32]
        encrypted = cipher.encrypt(chunk.encode('utf-8'))
        result += encrypted.hex()

    return result


def encode_phone(phone: str) -> str:
    """手机号编码 (每个字符ASCII码+2)"""
    result = []
    for char in phone:
        if char.isdigit():
            digit = int(char)
            if digit <= 7:
                result.append(str(digit + 2))
            elif digit == 8:
                result.append(':')
            elif digit == 9:
                result.append(';')
        else:
            result.append(chr(ord(char) + 2))
    return ''.join(result)


def encode_password(password: str) -> str:
    """密码编码 (每个字符ASCII码+2)"""
    return ''.join(chr(ord(c) + 2) for c in password)


# ============================================
# 缓存管理
# ============================================

def load_cache() -> Dict[str, Any]:
    """加载登录缓存"""
    global cache
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
    except Exception as e:
        log(f"加载缓存失败: {e}")
        cache = {}
    return cache


def save_cache() -> None:
    """保存登录缓存"""
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False)
    except Exception as e:
        log(f"保存缓存失败: {e}")


# ============================================
# 登录相关函数
# ============================================

def login_phone_main(phone: str, password: str) -> Optional[Dict[str, Any]]:
    """
    主登录函数（带缓存支持）

    Args:
        phone: 手机号
        password: 密码

    Returns:
        登录成功返回用户信息字典，失败返回None
    """
    masked = mask_phone(phone)

    try:
        timestamp = get_timestamp()
        device_uid = random_string(16)

        # 构建登录认证字符串
        auth_string = f"iPhone 14 15.4.{device_uid[:12]}{phone}{timestamp}{password}0$$$0."
        encrypted_auth = encrypt_rsa_base64(auth_string)

        # 编码手机号
        encoded_phone = encode_phone(phone)

        # 如果没有缓存，进行登录请求
        if phone not in cache:
            log(f"[登录操作] {masked} 正在登录...")

            header_info = {
                "code": "userLoginNormal",
                "timestamp": timestamp,
                "broadAccount": "",
                "broadToken": "",
                "clientType": "#10.5.0#channel50#iPhone 14 Pro Max#",
                "shopId": "20002",
                "source": "110003",
                "sourcePassword": "Sid98s",
                "token": "",
                "userLoginName": encoded_phone
            }

            login_request = {
                "headerInfos": header_info,
                "content": {
                    "attach": "test",
                    "fieldData": {
                        "loginType": "4",
                        "accountType": "",
                        "loginAuthCipherAsymmertric": encrypted_auth,
                        "deviceUid": device_uid,
                        "phoneNum": encoded_phone,
                        "isChinatelecom": "0",
                        "systemVersion": "15.4.0",
                        "authentication": encode_password(password)
                    }
                }
            }

            response = session.post(
                'https://appgologin.189.cn:9031/login/client/userLoginNormal',
                json=login_request,
                timeout=15
            )

            data = response.json()

            if 'responseData' not in data or 'data' not in data['responseData']:
                log(f"[登录失败] {masked} 响应数据格式错误")
                return None

            login_result = data['responseData']['data'].get('loginSuccessResult')
            if not login_result:
                log(f"[登录失败] {masked} 登录结果为空")
                return None

            cache[phone] = login_result
            save_cache()
            log(f"[登录成功] {masked} 已缓存token")
        else:
            log(f"[缓存登录] {masked} 使用缓存登录")

        # 获取ticket
        token = cache[phone]['token']
        user_id = cache[phone]['userId']

        # XML请求获取uid
        xml_request = f'''<Request>
            <HeaderInfos>
                <Code>getSingle</Code>
                <Timestamp>{get_timestamp()}</Timestamp>
                <BroadAccount></BroadAccount>
                <BroadToken></BroadToken>
                <ClientType>#9.6.1#channel50#iPhone 14 Pro Max#</ClientType>
                <ShopId>20002</ShopId>
                <Source>110003</Source>
                <SourcePassword>Sid98s</SourcePassword>
                <Token>{token}</Token>
                <UserLoginName>{phone}</UserLoginName>
            </HeaderInfos>
            <Content>
                <Attach>test</Attach>
                <FieldData>
                    <TargetId>{encrypt_des3(user_id)}</TargetId>
                    <Url>4a6862274835b451</Url>
                </FieldData>
            </Content>
        </Request>'''

        xml_response = session.post(
            'https://appgologin.189.cn:9031/map/clientXML',
            data=xml_request,
            headers={'Content-Type': 'application/xml;charset=utf-8'},
            timeout=15
        )

        response_text = xml_response.text

        # 检查token是否过期
        if '过期' in response_text or '校验错误' in response_text:
            log(f"[Token过期] {masked} 清除缓存重新登录")
            del cache[phone]
            save_cache()
            return login_phone_main(phone, password)

        # 解析ticket
        try:
            ticket_start = response_text.find('<Ticket>') + 8
            ticket_end = response_text.find('</Ticket>')
            ticket_encrypted = response_text[ticket_start:ticket_end]
            uid = decrypt_des3(ticket_encrypted)
        except Exception as e:
            log(f"[Ticket错误] {masked} 解析失败: {e}")
            return None

        log(f"[Ticket成功] {masked} 获取ticket成功")

        # 构建用户信息
        user_info = dict(cache[phone])
        user_info['uid'] = uid
        user_info['password'] = password
        user_info['phoneNbr'] = phone

        return user_info

    except Exception as e:
        log(f"[登录错误] {masked} 登录失败: {e}")
        return None


def user_login(user_info: Dict[str, Any]) -> bool:
    """
    统一登录（获取Authorization）

    Args:
        user_info: 用户信息字典

    Returns:
        成功返回True，失败返回False
    """
    masked = mask_phone(user_info['phoneNbr'])

    try:
        login_data = {
            "ticket": user_info['uid'],
            "backUrl": "https%3A%2F%2Fwapact.189.cn%3A9001",
            "platformCode": "P201010301",
            "loginType": 2
        }

        encrypted_data = encrypt_aes_base64(json.dumps(login_data), AES_KEY_LOGIN)

        response = session.post(
            'https://wapact.189.cn:9001/unified/user/login',
            data=encrypted_data,
            headers={
                'Content-Type': 'application/json;charset=UTF-8',
                'Accept': 'application/json, text/javascript, */*; q=0.01'
            },
            timeout=15
        )

        data = response.json()

        if data.get('code') == 0 and 'biz' in data:
            user_info['Authorization'] = f"Bearer {data['biz']['token']}"
            log(f"[统一登录] {masked} 获取Authorization成功")
            return True
        else:
            log(f"[统一登录] {masked} 失败: {data}")
            return False

    except Exception as e:
        log(f"[统一登录] {masked} 错误: {e}")
        return False


def sso_hom_login(ticket: str) -> Optional[Dict[str, Any]]:
    """
    SSO登录（获取sign）

    Args:
        ticket: 登录ticket

    Returns:
        成功返回包含sign的字典，失败返回None
    """
    try:
        response = session.get(
            f'https://wappark.189.cn/jt-sign/ssoHomLogin?ticket={ticket}',
            timeout=15
        )
        return response.json()
    except Exception as e:
        log(f"[SSO登录] 失败: {e}")
        return None


# ============================================
# 签到相关函数
# ============================================

def web_sign(user_info: Dict[str, Any], sso_data: Dict[str, Any]) -> None:
    """每日签到"""
    masked = mask_phone(user_info['phoneNbr'])

    try:
        sign_data = {
            "phone": user_info['phoneNbr'],
            "sysType": "",
            "date": int(time.time() * 1000)
        }

        response = session.post(
            'https://wappark.189.cn/jt-sign/webSign/sign',
            json={"encode": encrypt_aes_hex(json.dumps(sign_data))},
            headers={
                'Content-Type': 'application/json;charset=utf-8',
                'sign': sso_data['sign']
            },
            timeout=15
        )

        data = response.json()
        msg = data.get('data', {}).get('msg', '未知结果')
        log(f"[签到结果] {masked} {msg}")

    except Exception as e:
        log(f"[签到失败] {masked} {e}")


def user_status_info(user_info: Dict[str, Any], sso_data: Dict[str, Any]) -> None:
    """查询连签7天状态"""
    masked = mask_phone(user_info['phoneNbr'])

    try:
        request_data = {"phone": user_info['phoneNbr']}

        response = session.post(
            'https://wappark.189.cn/jt-sign/api/home/userStatusInfo',
            json={"para": encrypt_rsa_hex(json.dumps(request_data))},
            headers={
                'Content-Type': 'application/json;charset=utf-8',
                'sign': sso_data['sign']
            },
            timeout=15
        )

        data = response.json()
        sign_day = data.get('data', {}).get('signDay', '0')
        log(f"[连签进度] {masked} 连签{sign_day}天")

        # 连签7天领取奖励
        if sign_day == '7':
            log(f"[连签奖励] {masked} 开始领取连签7天奖励")
            exchange_prize(user_info, sso_data, '7')

    except Exception as e:
        log(f"[连签查询] {masked} 失败: {e}")


def continue_sign_days(user_info: Dict[str, Any], sso_data: Dict[str, Any]) -> None:
    """查询累计签到天数"""
    masked = mask_phone(user_info['phoneNbr'])

    try:
        request_data = {"phone": user_info['phoneNbr']}

        response = session.post(
            'https://wappark.189.cn/jt-sign/webSign/continueSignDays',
            json={"para": encrypt_rsa_hex(json.dumps(request_data))},
            headers={
                'Content-Type': 'application/json;charset=utf-8',
                'sign': sso_data['sign']
            },
            timeout=15
        )

        data = response.json()
        sign_days = data.get('continueSignDays', '0')
        log(f"[累签天数] {masked} 累计签到{sign_days}天")

        # 累签15天或28天领取奖励
        if sign_days in ['15', '28']:
            log(f"[累签奖励] {masked} 开始领取累签{sign_days}天奖励")
            sync_wait(3)
            exchange_prize(user_info, sso_data, sign_days)

    except Exception as e:
        log(f"[累签查询] {masked} 失败: {e}")


def exchange_prize(user_info: Dict[str, Any], sso_data: Dict[str, Any], prize_type: str) -> None:
    """
    领取签到奖励

    Args:
        user_info: 用户信息
        sso_data: SSO登录数据
        prize_type: 奖励类型 ('7', '15', '28')
    """
    masked = mask_phone(user_info['phoneNbr'])

    try:
        request_data = {
            "phone": user_info['phoneNbr'],
            "type": prize_type
        }

        response = session.post(
            'https://wappark.189.cn/jt-sign/webSign/exchangePrize',
            json={"para": encrypt_rsa_hex(json.dumps(request_data))},
            headers={
                'Content-Type': 'application/json;charset=utf-8',
                'sign': sso_data['sign']
            },
            timeout=15
        )

        data = response.json()

        # 尝试获取奖励信息
        win_title = (data.get('prizeDetail', {}).get('biz', {}).get('winTitle') or
                     data.get('resoultMsg') or
                     data.get('msg') or
                     '未知结果')

        log(f"[奖励领取] {masked} 连签{prize_type}天: {win_title}")

    except Exception as e:
        log(f"[奖励领取] {masked} 连签{prize_type}天失败: {e}")
        sync_wait(2)
        # 重试一次
        try:
            exchange_prize(user_info, sso_data, prize_type)
        except:
            pass


# ============================================
# 抽奖相关函数
# ============================================

def query_turn_table(user_info: Dict[str, Any]) -> None:
    """查询金豆转盘信息并执行抽奖"""
    masked = mask_phone(user_info['phoneNbr'])

    try:
        response = session.get(
            f'https://wapact.189.cn:9001/gateway/golden/api/queryTurnTable?userType=1&_={int(time.time()*1000)}',
            headers={'Authorization': user_info.get('Authorization', '')},
            timeout=15
        )

        data = response.json()

        if data.get('code') == 0 and 'biz' in data:
            activity_id = data['biz']['wzTurntable']['code']
            handle_lottery(user_info, activity_id)
        else:
            log(f"[转盘查询] {masked} 失败: {data}")

    except Exception as e:
        log(f"[转盘查询] {masked} 错误: {e}")


def handle_lottery(user_info: Dict[str, Any], activity_id: str) -> None:
    """执行金豆转盘抽奖"""
    masked = mask_phone(user_info['phoneNbr'])

    try:
        # 查询可抽奖次数
        check_response = session.get(
            f'https://wapact.189.cn:9001/gateway/standQuery/detail/check?activityId={activity_id}&_={int(time.time()*1000)}',
            headers={'Authorization': user_info.get('Authorization', '')},
            timeout=15
        )

        check_data = check_response.json()

        if check_data.get('code') != 0:
            log(f"[抽奖查询] {masked} 失败")
            return

        result_info = check_data.get('biz', {}).get('resultInfo', {})
        max_count = result_info.get('userMaximum', 0)
        used_count = result_info.get('userCount', 0)
        remaining = max_count - used_count

        log(f"[抽奖次数] {masked} 可抽奖{remaining}次")

        # 执行抽奖
        for i in range(remaining):
            try:
                lottery_response = session.post(
                    'https://wapact.189.cn:9001/gateway/golden/api/lottery',
                    json={"activityId": activity_id},
                    headers={'Authorization': user_info.get('Authorization', '')},
                    timeout=15
                )

                lottery_data = lottery_response.json()
                title = lottery_data.get('biz', {}).get('resultInfo', {}).get('title', '抽奖失败')
                log(f"[抽奖结果] {masked} 第{i+1}次: {title}")

                sync_wait(3)

            except Exception as e:
                log(f"[抽奖错误] {masked} 第{i+1}次: {e}")
                sync_wait(3)

    except Exception as e:
        log(f"[抽奖处理] {masked} 错误: {e}")


# ============================================
# 任务相关函数
# ============================================

def get_task_list(user_info: Dict[str, Any], sso_data: Dict[str, Any]) -> None:
    """获取并完成任务列表"""
    masked = mask_phone(user_info['phoneNbr'])

    try:
        request_data = {
            "phone": user_info['phoneNbr'],
            "shopId": "20001",
            "type": "hg_qd_zrwzjd"
        }

        response = session.post(
            'https://wappark.189.cn/jt-sign/webSign/homepage',
            json={"para": encrypt_rsa_hex(json.dumps(request_data))},
            headers={
                'Content-Type': 'application/json;charset=utf-8',
                'sign': sso_data['sign']
            },
            timeout=15
        )

        data = response.json()
        ad_items = data.get('data', {}).get('biz', {}).get('adItems', [])

        for task_item in ad_items:
            state = task_item.get('taskState', '')
            content = task_item.get('contentOne', '')
            title = task_item.get('title', '未知任务')

            # 任务状态为0或1且内容为18的任务
            if state in ['0', '1'] and content == '18':
                log(f"[任务执行] {masked} 开始: {title}")
                complete_task(user_info, sso_data, task_item)
                sync_wait(1.5)

    except Exception as e:
        log(f"[任务列表] {masked} 获取失败: {e}")


def complete_task(user_info: Dict[str, Any], sso_data: Dict[str, Any], task_item: Dict[str, Any]) -> None:
    """完成单个任务"""
    masked = mask_phone(user_info['phoneNbr'])
    title = task_item.get('title', '未知任务')

    try:
        request_data = {
            "phone": user_info['phoneNbr'],
            "jobId": task_item.get('taskId', '')
        }

        response = session.post(
            'https://wappark.189.cn/jt-sign/webSign/polymerize',
            json={"para": encrypt_rsa_hex(json.dumps(request_data))},
            headers={
                'Content-Type': 'application/json;charset=utf-8',
                'sign': sso_data['sign']
            },
            timeout=15
        )

        data = response.json()
        result_msg = data.get('resoultMsg', '未知结果')
        log(f"[任务完成] {masked} {title}: {result_msg}")

    except Exception as e:
        log(f"[任务失败] {masked} {title}: {e}")


def food(user_info: Dict[str, Any], sso_data: Dict[str, Any]) -> None:
    """喂食功能（最多10次）"""
    masked = mask_phone(user_info['phoneNbr'])

    try:
        request_data = {"phone": user_info['phoneNbr']}

        for i in range(1, 11):
            try:
                response = session.post(
                    'https://wappark.189.cn/jt-sign/paradise/food',
                    json={"para": encrypt_rsa_hex(json.dumps(request_data))},
                    headers={
                        'Content-Type': 'application/json;charset=utf-8',
                        'sign': sso_data['sign']
                    },
                    timeout=15
                )

                data = response.json()
                result_msg = data.get('resoultMsg', '未知结果')
                log(f"[喂食结果] {masked} 第{i}次: {result_msg}")

                if result_msg == "今天已达到最大喂食次数":
                    log(f"[喂食完成] {masked} 今日喂食次数已达上限")
                    break

                if i < 10:
                    sync_wait(1)

            except Exception as e:
                log(f"[喂食失败] {masked} 第{i}次: {e}")
                break

    except Exception as e:
        log(f"[喂食错误] {masked} {e}")


# ============================================
# 主流程函数
# ============================================

def main_flow(phone: str, password: str) -> None:
    """单账号主流程"""
    masked = mask_phone(phone)

    try:
        # 1. 登录
        login_result = login_phone_main(phone, password)
        if not login_result:
            log(f"[流程跳过] {masked} 登录失败，跳过后续操作")
            return

        # 2. 统一登录获取Authorization（用于金豆抽奖）
        user_login(login_result)

        # 查询金豆转盘并抽奖
        if login_result.get('Authorization'):
            query_turn_table(login_result)

        # 3. SSO登录获取sign（用于签到等功能）
        sso_data = sso_hom_login(login_result['uid'])
        if sso_data:
            # 4. 签到
            web_sign(login_result, sso_data)

            # 5. 查询连签状态
            user_status_info(login_result, sso_data)
            sync_wait(3)

            # 6. 查询累签状态
            continue_sign_days(login_result, sso_data)

            # 7. 完成任务
            get_task_list(login_result, sso_data)

            # 8. 喂食
            food(login_result, sso_data)

        sync_wait(2)

    except Exception as e:
        log(f"[流程错误] {masked} 主流程失败: {e}")


def begin() -> None:
    """程序入口"""
    global cache

    # 加载缓存
    cache = load_cache()

    # 解析环境变量中的账号信息
    accounts_str = os.environ.get('chinaTelecomAccount', '')
    if not accounts_str:
        log("未找到环境变量，请设置环境变量 chinaTelecomAccount")
        log("格式：手机号1#密码1&手机号2#密码2")
        sys.exit(1)

    # 解析账号
    accounts: List[Tuple[str, str]] = []
    for account in accounts_str.split('&'):
        if '#' in account:
            parts = account.split('#')
            if len(parts) >= 2:
                phone = parts[0].strip()
                password = parts[1].strip()
                if phone and password:
                    accounts.append((phone, password))

    if not accounts:
        log("未解析到有效账号，请检查格式")
        sys.exit(1)

    log(f"📱 共找到{len(accounts)}个账号，开始执行任务")

    try:
        # 遍历所有账号执行任务
        for i, (phone, password) in enumerate(accounts, 1):
            masked = mask_phone(phone)
            log(f"\n{'='*20} 账号[{i}] {masked} {'='*20}")
            main_flow(phone, password)
    except Exception as e:
        log(f"全局执行错误: {e}")

    finally:
        sys.exit(0)


# ============================================
# 程序启动
# ============================================

if __name__ == '__main__':
    begin()
