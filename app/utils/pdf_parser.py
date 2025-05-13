import PyPDF2
import re
import logging

logger = logging.getLogger(__name__)

def extract_org_info(pdf_path):
    """
    从PDF文件中提取组织信息
    返回包含组织名称、简称和银行账号的字典
    """
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            
            logger.debug(f"Extracted text from PDF: {text}")

            # 使用正则表达式提取信息，处理可能的换行符
            text = text.replace('\n', ' ')  # 将换行符替换为空格
            
            # 使用非贪婪匹配来提取信息
            org_name_match = re.search(r'组织名称[:：]\s*([^组织简称]+)', text)
            short_name_match = re.search(r'组织简称[:：]\s*([^银行账号]+)', text)
            bank_account_match = re.search(r'银行账号[:：]\s*([^\s]+)', text)

            org_info = {
                'name': org_name_match.group(1).strip() if org_name_match else None,
                'short_name': short_name_match.group(1).strip() if short_name_match else None,
                'bank_account': bank_account_match.group(1).strip() if bank_account_match else None
            }

            logger.debug(f"Parsed org info: {org_info}")

            # 验证所有必要信息是否都提取到了
            if not all(org_info.values()):
                missing_fields = [k for k, v in org_info.items() if not v]
                logger.error(f"Missing required information in PDF. Missing fields: {missing_fields}")
                return None

            return org_info

    except Exception as e:
        logger.error(f"Error extracting organization info from PDF: {str(e)}")
        return None 