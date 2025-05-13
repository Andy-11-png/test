import logging
import PyPDF2
import re

def extract_bank_info_from_pdf(pdf_path):
    """
    从PDF文件中提取银行信息和用户信息
    返回: (bank_name, bank_account, bank_password, user_name, user_email, user_password, org_name)
    """
    logger = logging.getLogger(__name__)
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            
            # 读取所有页面的文本
            for page in reader.pages:
                text += page.extract_text()
            
            # 记录提取的全部文本，便于调试
            logger.debug(f"提取的PDF文本: {text}")
            # 添加用户姓名模式
            user_name_pattern = r'Name[:：]?\s*([^\n]+)'
            user_name_match = re.search(user_name_pattern, text)
            user_name = ' '.join(user_name_match.group(1).split()).strip() if user_name_match else None
            
            # 添加用户邮箱模式
            user_email_pattern = r'E-mail[:：]?\s*([^\n]+)'
            user_email_match = re.search(user_email_pattern, text)
            user_email = ' '.join(user_email_match.group(1).split()).strip() if user_email_match else None
            
            # 添加用户密码模式
            user_password_pattern = r'Password[:：]?\s*([^\n]+)'
            user_password_match = re.search(user_password_pattern, text)
            user_password = ' '.join(user_password_match.group(1).split()).strip() if user_password_match else None
            
            # 添加组织名称模式
            org_name_pattern = r'Organization Name[:：]?\s*([^\n]+)'
            org_name_match = re.search(org_name_pattern, text)
            org_name = ' '.join(org_name_match.group(1).split()).strip() if org_name_match else None
            # 银行名称模式
            bank_name_pattern = r'Bank Name[:：]?\s*([^\n]+)'
            bank_name_match = re.search(bank_name_pattern, text)
            bank_name = ' '.join(bank_name_match.group(1).split()).strip() if bank_name_match else None
            
            # 改进的银行账号模式 - 查找"账号"附近的所有数字
            account_section_pattern = r'Account[:：]?(.{0,50})'  # 获取"账号"后面的50个字符
            account_section_match = re.search(account_section_pattern, text)
            bank_account = ''.join(re.findall(r'\d', account_section_match.group(1))) if account_section_match else None
            
            # 银行密码模式
            bank_password_pattern = r'Account Password[:：]?\s*([^\n]+)'
            bank_password_match = re.search(bank_password_pattern, text)
            bank_password = ' '.join(bank_password_match.group(1).split()).strip() if bank_password_match else None
            
            
            
            logger.info(f"提取的银行信息: 名称={bank_name}, 账号={bank_account}, 密码={bank_password}")
            logger.info(f"提取的用户信息: 姓名={user_name}, 邮箱={user_email}, 密码={user_password}, 组织名称={org_name}")
            
            return user_name, user_email, user_password, org_name, bank_name, bank_account, bank_password
            
    except Exception as e:
        logger.error(f"从PDF提取信息时出错: {str(e)}")
        return None, None, None, None, None, None, None