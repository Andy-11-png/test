import requests
import json

def trans_money(from_org, to_org, amount):
    """
    处理组织间的转账
    :param from_org: 转出组织对象
    :param to_org: 转入组织对象
    :param amount: 转账金额
    :return: (success, message)
    """
    try:
        # 准备转账数据
        transfer_data = {      
            "from_name": from_org.name,
            "from_account": from_org.bank_account,
            "from_bank": from_org.bank_name,
            "password": from_org.bank_password,
            "to_bank": to_org.bank_name,
            "to_name": to_org.name,
            "to_account": to_org.bank_account,
            "amount": amount
        }
        
        # TODO: 改成接口
        # 调用转账接口
        response = requests.post(
            "http://172.16.160.88:8001/hw/bank/transfer",#改成接口
            json=transfer_data,
            headers={"Content-Type": "application/json"}
        )
        
        # 解析响应
        result = response.json()
        if result.get("status") == "success":
            return True, "转账成功"
        else:
            return False, result.get("reason", "转账失败")
            
    except Exception as e:
        return False, f"转账过程出错: {str(e)}" 

def authenticate(from_org):
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"准备认证数据: {from_org.name}, {from_org.bank_account}")
        transfer_data = {
            "account_name": from_org.name,
            "account_number": from_org.bank_account,
            "bank": from_org.bank_name,
            "password": from_org.bank_password,
        }
        
        logger.info(f"发送认证请求到: http://172.16.160.88:8001/hw/bank/authenticate")
        logger.info(f"请求数据: {transfer_data}")
        
        # 这里添加超时参数，防止请求卡住
        response = requests.post(
            "http://172.16.160.88:8001/hw/bank/authenticate",
            json=transfer_data,
            headers={"Content-Type": "application/json"},
            timeout=10  # 添加超时设置
        )
        
        logger.info(f"收到响应: 状态码={response.status_code}")
        logger.info(f"响应内容: {response.text}")
        
        # 解析响应
        result = response.json()
        if result.get("status") == "success":
            return True, "认证成功"
        else:
            return False, result.get("reason", "没有此记录")
            
    except Exception as e:
        return False, f"认证出错: {str(e)}" 