import requests
import json
import hashlib
import os
import time
import base64
from urllib.parse import urlparse, quote
from datetime import date
import random

# 登录API端点
LOGIN_URL: str = "https://xskq.ahut.edu.cn/api/flySource-auth/oauth/token"
# 寝室打卡列表API端点
DORM_LIST_URL: str = "https://xskq.ahut.edu.cn/api/flySource-yxgl/dormSignTask/getListForApp"
# 日志API端点
LOG_URL: str = "https://xskq.ahut.edu.cn/api/flySource-base/apiLog/save"
# 任务详情获取API端点
GET_TASK_URL: str = "https://xskq.ahut.edu.cn/api/flySource-yxgl/dormSignTask/getTaskByIdForApp"
# 微信认证API端点
WECHAT_URL: str = "https://xskq.ahut.edu.cn/api/flySource-base/wechat/getWechatMpConfig"
# 这个AUTHORIZATION是请求头中的一个不知道是什么，疑似是固定的，先硬编码写着了
AUTHORIZATION: str = "Basic Zmx5U291cmNlOkZseVNvdXJjZV9TREVLT0ZTSURGODIzMjlGOHNkODcyM2RTODdEQVM="
# 签到API
SIGN_API: str = "https://xskq.ahut.edu.cn/api/flySource-yxgl/dormSignRecord/add"


# 设置账号和密码的储存路径
PASS_PATH: str = "../storage/pass.json"
# 设置Token的储存路径
TOKEN_PATH: str = "../storage/token.json"
# 当前进行任务储存信息的路径
TASK_PATH: str = "../storage/task.json"

def md5_encrypt(text: str):
    """MD5加密"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def generate_flysource_sign(url: str, token: str) -> str:
    # 1. 提取 URL 中 /api 到第一个 ? 的部分，并加上 ?sign=
    parsed = urlparse(url)
    path_part = parsed.path
    string_i = f"{path_part}?sign="

    # 生成时间戳并加上 token 的前 10 个字符
    timestamp = str(int(time.time() * 1000))
    token_prefix = token[:10]
    timestamp_with_token = timestamp + token_prefix

    # 第一次 MD5 加密
    first_md5 = hashlib.md5(timestamp_with_token.encode('utf-8')).hexdigest()

    # 第二次 MD5 加密：string_i + 第一次 MD5
    second_input = string_i + first_md5
    second_md5 = hashlib.md5(second_input.encode('utf-8')).hexdigest()

    # Base64 加密时间戳
    timestamp_b64 = base64.b64encode(timestamp.encode('utf-8')).decode('utf-8')

    flysource_sign = f"{second_md5}1.{timestamp_b64}"
    return flysource_sign

def initialize_passwd():
    account: str = input("请输入认证系统账号：")
    passwd: str = input("请输入认证系统密码：")
    data: dict[str, str] = {
        "account": account,
        "password": passwd
    }
    
    os.makedirs(os.path.dirname(PASS_PATH), exist_ok=True)

    with open(PASS_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def read_passwd() -> dict[str, str]:
    try:
        with open(PASS_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except FileNotFoundError:
        print("密码文件不存在，请先初始化密码。")
        initialize_passwd()
        return read_passwd()
    except json.JSONDecodeError:
        print("密码文件格式错误，请重新初始化密码。")
        initialize_passwd()
        return read_passwd()

def read_token() -> dict[str, str]:
    try:
        with open(TOKEN_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # 检查token是否过期
            created_at = data.get("created_at")
            expires_in = data.get("expires_in")
            
            if created_at and expires_in:
                current_time = int(time.time())
                created_time = int(created_at)
                expire_time = created_time + int(expires_in)
                
                if current_time >= expire_time:
                    print("Token已过期，请重新登录。")
                    # 触发重新登录
                    store = read_passwd()
                    account = store.get("account")
                    password = store.get("password")
                    if account and password:
                        login_result = login("000000", account, password)
                        if login_result:
                            # 重新登录成功，再次读取token
                            return read_token()
                        else:
                            print("重新登录失败，请检查账号密码。")
                            return {}
                    else:
                        print("账号或密码信息缺失，请重新初始化密码。")
                        initialize_passwd()
                        return {}
            
            return data
    except FileNotFoundError:
        print("Token文件不存在，请先登录。")
        initialize_passwd()
        return read_passwd()
    except json.JSONDecodeError:
        print("Token文件格式错误，请重新登录。")
        initialize_passwd()
        return read_passwd()

def read_task() -> dict[str, str]:
    try:
        with open(TASK_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        print("任务文件不存在，请先登录并创建任务。")
        return {}
    except json.JSONDecodeError:
        print("任务文件格式错误，请重新创建任务。")
        return {}

def login(tenant_id: str, username: str, password: str) -> bool:

    headers: dict[str, str] = {
        "Tenant-Id": tenant_id,
        "Authorization": AUTHORIZATION,
        "Origin": "https://xskq.ahut.edu.cn",
        "Referer": "https://xskq.ahut.edu.cn/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",   
    }

    params: dict[str, str] = {
        "tenantId": tenant_id,
        "username": username,
        "password": md5_encrypt(password),
        "type": "account",
        "grant_type": "password",
        "scope": "all"
    }

    response = requests.post(url=LOGIN_URL, headers=headers, params=params)
    json_data: dict[str, str] = {}
    
    try:
        json_data = response.json()
        # 检查响应是否成功
        if response.status_code != 200:
            print(f"登录失败，HTTP状态码: {response.status_code}")
            return False
        
        access_token = json_data.get("access_token")
        if access_token is None:
            print("登录响应中未找到access_token")
            return False
        refresh_token = json_data.get("refresh_token")
        if refresh_token is None:
            print("登录响应中未找到refresh_token")
            return False
            
        # 构建token字典
        token_dict: dict[str, str] = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": json_data.get("token_type", "bearer"),
            "expires_in": json_data.get("expires_in", ""),
            "created_at": str(int(time.time())),
            "user_id": json_data.get("userId", ""),
        }
        
        os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
        
        with open(TOKEN_PATH, "w", encoding="utf-8") as f:
            json.dump(token_dict, f, indent=4, ensure_ascii=False)
        
        user_id: str = json_data.get("userId", "")
        user_name: str = json_data.get("userName", "")
        print(f"欢迎 {user_name} 同学！登录成功，token已保存，请核对您的学号是否为: {user_id}")
        return True
        
    except requests.exceptions.JSONDecodeError:
        print("登录端点响应不是能被解析的json格式，端点可能已被修改")
        return False
    except Exception as e:
        print(f"保存token时发生错误: {str(e)}")
        return False
    
def send_log(access_token: str) -> bool:
    params: dict[str, str] = {
        "menuTitle": "晚寝签到"
    }

    headers: dict[str, str] = {
        "Authorization": AUTHORIZATION,
        "Origin": "https://xskq.ahut.edu.cn",
        "Referer": "https://xskq.ahut.edu.cn/wise/pages/ssgl/wqqd",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        "FlySource-Auth": "bearer "+ access_token,
        "FlySource-sign": generate_flysource_sign(LOG_URL, access_token)
    }
    try:
        requests.get(url=LOG_URL, params=params, headers=headers)
        return True
    except Exception as e:
        print(f"发送日志请求时发生异常:{e}")
        return False

def get_dorm_list(access_token: str):

    # 在获取列表之前需要先发送日志
    send_log(access_token=access_token)

    params: dict[str, int] = {
        "current": 1,
        "size": 15
    }

    headers: dict[str, str] = {
        "Authorization": AUTHORIZATION,
        "Origin": "https://xskq.ahut.edu.cn",
        "Referer": "https://xskq.ahut.edu.cn/wise/pages/ssgl/wqqd",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        "Cookie": "access-token=" + access_token,
        "FlySource-Auth": "bearer "+ access_token,
        "FlySource-sign": generate_flysource_sign(DORM_LIST_URL, access_token)
    }

    response = requests.get(url=DORM_LIST_URL, params=params, headers=headers)
    response_dict = response.json()

    records = response_dict["data"]["records"]
    return records

def verify_wechat(access_token: str, task_id: str, user_id: str):
    """获取微信认证配置"""
    # 构建configUrl参数
    config_url = WECHAT_URL + f"?taskId={task_id}&autoSign=1&scanSign=0&userId={user_id}"
    
    encoded_config_url = quote(config_url, safe='')
    
    params: dict[str, str] = {
        "configUrl": encoded_config_url
    }

    headers: dict[str, str] = {
        "Authorization": AUTHORIZATION,
        "Origin": "https://xskq.ahut.edu.cn",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        "Cookie": "access-token=" + access_token,
        "FlySource-Auth": "bearer "+ access_token,
        "FlySource-sign": generate_flysource_sign(WECHAT_URL, access_token)
    }

    response = requests.get(url=WECHAT_URL, params=params, headers=headers)
    response_dict = response.json()
    return response_dict["data"]


def get_task_info(access_token: str, task_id: str, sign_date:str):

    params: dict[str, str] = {
        "taskId": task_id,
        "signDate": sign_date
    }

    headers: dict[str, str] = {
        "Authorization": AUTHORIZATION,
        "Origin": "https://xskq.ahut.edu.cn",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        "Cookie": "access-token=" + access_token,
        "FlySource-Auth": "bearer "+ access_token,
        "FlySource-sign": generate_flysource_sign(GET_TASK_URL, access_token)
    }

    response = requests.get(url=GET_TASK_URL, headers=headers, params=params)
    response_dict = response.json()
    return response_dict["data"]

def send_sign_request(access_token: str, task_dict: dict) -> bool:
    """发送签到请求"""

    send_log(access_token=access_token)
    
    # 在正式签到之前先调用微信认证
    task_id = task_dict.get("task_id", "")
    user_id = task_dict.get("user_id", "")
    if task_id and user_id:
        try:
            verify_wechat(access_token=access_token, task_id=task_id, user_id=user_id)
            print("微信认证成功")
        except Exception as e:
            print(f"微信认证失败: {e}")
            return False
    else:
        print("任务ID或用户ID缺失，无法进行微信认证")
        return False
    
    from datetime import datetime
    
    current_time = datetime.now().time()
    sign_start_time = datetime.strptime(task_dict.get("signStartTime", ""), "%H:%M:%S").time()
    sign_end_time = datetime.strptime(task_dict.get("signEndTime", ""), "%H:%M:%S").time()
    
    # 检查当前时间是否在签到时间范围内
    if sign_start_time <= current_time <= sign_end_time:
        print(f"当前时间在签到时间范围内({sign_start_time}-{sign_end_time})，开始签到...")
        

        timestamp = time.time()
        local_time = time.localtime(timestamp)
        formatted_time = time.strftime('%H:%M:%S', local_time)

        today = date.today()
        weekday = today.weekday()
        chinese_weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        chinese_weekday = chinese_weekdays[weekday]

        # 构建请求参数
        params: dict = {
            "fileId": "",
            "imgBase64": "/static/images/dormitory/photo.png",
            "locationAccuracy": round(random.uniform(1.0, 25.0), 1),
            "roomId": task_dict.get("roomId", ""),
            "scanCode": "",
            "scanType": "",
            "signAddress": "",
            "signDate": str(date.today()),
            "signLat": round(random.uniform(float(task_dict.get("locationLat", "0")) - 0.00002, float(task_dict.get("locationLat", "0")) + 0.00002), 5),
            "signLng": round(random.uniform(float(task_dict.get("locationLng", "0")) - 0.00002, float(task_dict.get("locationLng", "0")) + 0.00002), 5),
            "signTime": formatted_time,
            "signType": 0,
            "signWeek": chinese_weekday,
            "taskId": task_dict.get("task_id", ""),
        }
        
        # 构建请求头
        headers: dict[str, str] = {
            "Authorization": AUTHORIZATION,
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": "https://xskq.ahut.edu.cn",
            "Priority": "u=1, i",
            "Referer": "https://xskq.ahut.edu.cn/wise/pages/ssgl/dormsign?taskId="+task_dict.get("task_id", "") + "&autoSign=1&scanSign=0&userId="+task_dict.get("user_id", ""),
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
            "Cookie": "access-token=" + access_token,
            "FlySource-Auth": "bearer " + access_token,
            "FlySource-sign": generate_flysource_sign(SIGN_API, access_token)
        }
        
        try:
            response = requests.post(url=SIGN_API, json=params, headers=headers)
            response_dict = response.json()
            
            if response.status_code == 200 and response_dict.get("code") == 200:
                print("签到成功！")
                return True
            else:
                print(f"签到失败，状态码: {response.status_code}, 响应: {response_dict}")
                return False
        except Exception as e:
            print(f"发送签到请求时发生异常: {e}")
            return False
    else:
        print(f"当前时间不在签到时间范围内({sign_start_time}-{sign_end_time})")
        return False

def select_task(max: int) -> int:
    task_select = input("请选择要签到的任务序号: ")
    if str.isdigit(task_select):
        if max < int(task_select):
            print("选择的任务数量大于了获取到的任务总数，请重新输入")
            return select_task(max)
        else:
            return int(task_select)
    else:
        print("输入的不是一个整数，请重新输入")
        return select_task(max)

def save_payload(access_token: str, task_id: str):

    task_info = get_task_info(access_token=access_token, task_id=task_id, sign_date=str(date.today()))
    # 从token中获取user_id
    token_dict = read_token()
    user_id = token_dict.get("user_id", "")
    
    # 构建payload dict
    payload_dict: dict = {
        "task_id": task_id,
        "taskName": task_info["taskName"],
        "taskStartDate": task_info["taskStartDate"],
        "taskEndDate": task_info["taskEndDate"],
        "signStartTime": task_info["signStartTime"],
        "signEndTime": task_info["signEndTime"],
        "roomId": task_info["dormitoryRegisterVO"]["roomId"],
        "locationLat": task_info["dormitoryRegisterVO"]["locationLat"],
        "locationLng": task_info["dormitoryRegisterVO"]["locationLng"],
        "user_id": user_id
    }

    os.makedirs(os.path.dirname(TASK_PATH), exist_ok=True)
        
    with open(TASK_PATH, "w", encoding="utf-8") as f:
        json.dump(payload_dict, f, indent=4, ensure_ascii=False)

    print(f"已储存 {task_info["taskName"]} 任务")

def create_task(dorm_sign_list, token_dict):
    print(f"从系统中获取到了 {len(dorm_sign_list)} 个晚寝签到任务：")
    for index, sign_element in enumerate(dorm_sign_list):
        print(f"=============第{index + 1}个=============")
        print(f"签到任务名称: {sign_element.get("taskName")}")
        print(f"任务id: {sign_element.get("taskId")}")
        print(f"开始日期: {sign_element.get("taskStartDate")}")
        print(f"结束日期: {sign_element.get("taskEndDate")}")
        print(f"需要签到: {sign_element.get("signWeek")}")
        print(f"===============================")
    
    selected_task = select_task(len(dorm_sign_list))
    selected_task_id = dorm_sign_list[selected_task - 1].get("taskId", "")

    save_payload(access_token=token_dict["access_token"], task_id=selected_task_id)
def main():
    # 如果不存在文件就先初始化密码
    if os.path.exists(PASS_PATH) == False:
        initialize_passwd()
    
    # 如果token文件不存在就先登录
    if os.path.exists(TOKEN_PATH) == False:

        store: dict[str, str] = read_passwd()
        account = store.get("account")
        password = store.get("password")

        if account is not None and password is not None:
            login_result = login("000000", account, password)
            if not login_result:
                print("登录失败，请检查账号密码是否正确。")
                retry = input("是否重新初始化密码？(Y/n): ")
                if retry == 'Y':
                    initialize_passwd()
                    main()  # 重新尝试登录
        else:
            print("账号或密码信息缺失，请重新初始化密码。")
            initialize_passwd()
            main()  # 重新尝试登录
    
    token_dict = read_token()
    dorm_sign_list: list[dict[str, str]] = get_dorm_list(token_dict["access_token"])

    #如果不存在就先创建任务
    task_dict: dict[str, str] = read_task()
    
    # 检查是否需要重新创建任务
    need_create_task = False
    
    # 如果任务文件不存在，需要创建任务
    if os.path.exists(TASK_PATH) == False:
        need_create_task = True
    else:
        # 检查当前日期是否在任务日期范围内
        current_date = date.today()
        task_start_date = date.fromisoformat(task_dict.get("taskStartDate", ""))
        task_end_date = date.fromisoformat(task_dict.get("taskEndDate", ""))
        
        if current_date < task_start_date or current_date > task_end_date:
            print("当前日期不在任务日期范围内，需要重新创建任务")
            need_create_task = True
    
    # 如果需要创建任务，则调用create_task函数
    if need_create_task:
        create_task(dorm_sign_list, token_dict)
        # 重新读取任务信息
        task_dict = read_task()
    
    # 检查当前时间是否在签到时间范围内，如果是，则发送签到请求
    send_sign_request(access_token=token_dict["access_token"], task_dict=task_dict)

if __name__ == "__main__":
    main()