import requests
import json
from app.models.bank_api_config import BankApiConfig
import logging

logger = logging.getLogger(__name__)

def get_api_config(feature_type):
    """
    获取API配置
    :param feature_type: 1 for authenticate, 2 for transfer
    :return: BankApiConfig object or None
    """
    return BankApiConfig.query.filter_by(feature_type=feature_type).first()

def map_params_to_schema(params, schema):
    """
    根据schema映射参数
    :param params: 原始参数字典
    :param schema: API的input schema
    :return: 映射后的参数字典
    """
    mapped_params = {}
    for key in schema.keys():
        if key in params:
            mapped_params[key] = params[key]
    return mapped_params

def trans_money(from_org, to_org, amount):
    """
    处理组织间的转账
    :param from_org: 转出组织对象
    :param to_org: 转入组织对象
    :param amount: 转账金额
    :return: (success, message)
    """
    try:
        # 获取转账API配置
        config = get_api_config(2)  # 2 for transfer
        if not config:
            return False, "未找到转账API配置"
        
        # 解析input schema
        input_schema = json.loads(config.input_schema)
        
        # 准备原始转账数据
        raw_data = {
            "from_name": from_org.name,
            "from_account": from_org.bank_account,
            "from_bank": from_org.bank_name,
            "password": from_org.bank_password,
            "to_bank": to_org.bank_name,
            "to_name": to_org.name,
            "to_account": to_org.bank_account,
            "amount": amount
        }
        
        # 根据schema映射参数
        transfer_data = map_params_to_schema(raw_data, input_schema)
        
        # 构建API URL
        api_url = f"{config.api_url.rstrip('/')}/{config.api_path.lstrip('/')}"
        
        logger.info(f"发送转账请求到: {api_url}")
        logger.info(f"请求数据: {transfer_data}")
        
        # 调用转账接口
        response = requests.post(
            api_url,
            json=transfer_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        logger.info(f"收到响应: 状态码={response.status_code}")
        logger.info(f"响应内容: {response.text}")
        
        # 解析响应
        result = response.json()
        if result.get("status") == "success":
            return True, "转账成功"
        else:
            return False, result.get("reason", "转账失败")
            
    except Exception as e:
        logger.error(f"转账过程出错: {str(e)}")
        return False, f"转账过程出错: {str(e)}"

def authenticate(from_org):
    """
    认证组织银行账户
    :param from_org: 组织对象
    :return: (success, message)
    """
    try:
        # 获取认证API配置
        config = get_api_config(1)  # 1 for authenticate
        if not config:
            return False, "未找到认证API配置"
        
        # 解析input schema
        input_schema = json.loads(config.input_schema)
        
        # 准备原始认证数据
        raw_data = {
            "account_name": from_org.name,
            "account_number": from_org.bank_account,
            "bank": from_org.bank_name,
            "password": from_org.bank_password,
        }
        
        # 根据schema映射参数
        auth_data = map_params_to_schema(raw_data, input_schema)
        
        # 构建API URL
        api_url = f"{config.api_url.rstrip('/')}/{config.api_path.lstrip('/')}"
        
        logger.info(f"准备认证数据: {from_org.name}, {from_org.bank_account}")
        logger.info(f"发送认证请求到: {api_url}")
        logger.info(f"请求数据: {auth_data}")
        
        # 调用认证接口
        response = requests.post(
            api_url,
            json=auth_data,
            headers={"Content-Type": "application/json"},
            timeout=10
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
        logger.error(f"认证出错: {str(e)}")
        return False, f"认证出错: {str(e)}" 