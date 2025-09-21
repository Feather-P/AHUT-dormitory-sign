import requests
import json
import os
from datetime import date
from main import (
    TOKEN_PATH, 
    TASK_PATH, 
    AUTHORIZATION, 
    SIGN_API, 
    generate_flysource_sign,
    read_token,
    read_task
)

def debug_send_sign_request(access_token: str, task_dict: dict) -> bool:
    """调试用的发送签到请求函数，不检查时间"""
    print("调试模式：忽略时间检查，直接发送签到请求...")
    
    # 构建请求参数
    params: dict[str, str] = {
        "taskId": task_dict.get("task_id", ""),
        "roomId": task_dict.get("roomId", ""),
        "locationLat": task_dict.get("locationLat", ""),
        "locationLng": task_dict.get("locationLng", ""),
        "signDate": str(date.today())
    }
    
    # 构建请求头
    headers: dict[str, str] = {
        "Authorization": AUTHORIZATION,
        "Origin": "https://xskq.ahut.edu.cn",
        "Referer": "https://xskq.ahut.edu.cn/wise/pages/ssgl/wqqd",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        "Cookie": "access-token=" + access_token,
        "FlySource-Auth": "bearer " + access_token,
        "FlySource-sign": generate_flysource_sign(SIGN_API, access_token)
    }
    
    try:
        print("正在发送签到请求...")
        print(f"请求参数: {params}")
        print(f"请求头: {headers}")
        
        response = requests.post(url=SIGN_API, params=params, headers=headers)
        response_dict = response.json()
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response_dict}")
        
        if response.status_code == 200 and response_dict.get("code") == 200:
            print("签到成功！")
            return True
        else:
            print(f"签到失败，状态码: {response.status_code}, 响应: {response_dict}")
            return False
    except Exception as e:
        print(f"发送签到请求时发生异常: {e}")
        return False

def main():
    """调试脚本主函数"""
    print("=== 调试签到脚本 ===")
    
    # 读取token
    token_dict = read_token()
    if not token_dict or "access_token" not in token_dict:
        print("无法读取token，请先运行主程序登录")
        return
    
    # 读取任务信息
    task_dict = read_task()
    if not task_dict or "task_id" not in task_dict:
        print("无法读取任务信息，请先运行主程序创建任务")
        return
    
    print(f"当前任务: {task_dict.get('taskName', '')}")
    print(f"任务ID: {task_dict.get('task_id', '')}")
    print(f"签到时间范围: {task_dict.get('signStartTime', '')} - {task_dict.get('signEndTime', '')}")
    
    # 发送签到请求
    debug_send_sign_request(access_token=token_dict["access_token"], task_dict=task_dict)

if __name__ == "__main__":
    main()