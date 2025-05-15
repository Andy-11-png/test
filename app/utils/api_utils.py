import json
import requests
from flask import jsonify
from app.models.org_api_config import OrgApiConfig
import os

def get_org_api_config(org_id, feature_type):
    """获取组织的API配置"""
    return OrgApiConfig.query.filter_by(
        org_id=org_id,
        feature_type=feature_type
    ).first()

def generate_form_from_schema(schema_str):
    """根据JSON schema生成表单HTML"""
    try:
        schema = json.loads(schema_str)
        if not isinstance(schema, dict):
            return ""
        
        html = ""
        for field, value in schema.items():
            html += f'<div class="form-group">'
            html += f'<label for="{field}">{field}</label>'
            
            # 根据字段名判断输入类型
            if field.lower() == 'photo' or field.lower().endswith('_photo'):
                html += f'<input type="file" class="form-control" id="{field}" name="{field}" accept="image/*" required>'
                # 添加文件预览和base64转换的JavaScript
                html += f'''
                <script>
                    document.getElementById('{field}').addEventListener('change', function(e) {{
                        const file = e.target.files[0];
                        if (file) {{
                            const reader = new FileReader();
                            reader.onload = function(e) {{
                                // 将base64数据存储到隐藏字段中
                                const base64Data = e.target.result;
                                const hiddenInput = document.createElement('input');
                                hiddenInput.type = 'hidden';
                                hiddenInput.name = '{field}_base64';
                                hiddenInput.value = base64Data;
                                document.getElementById('{field}').parentNode.appendChild(hiddenInput);
                            }};
                            reader.readAsDataURL(file);
                        }}
                    }});
                </script>
                '''
            elif field.lower() == 'id' or field.lower().endswith('_id'):
                html += f'<input type="text" class="form-control" id="{field}" name="{field}" required>'
            else:
                html += f'<input type="text" class="form-control" id="{field}" name="{field}" required>'
            
            html += '</div>'
        return html
    except json.JSONDecodeError:
        return ""

def call_api(config, data, files=None):
    """
    调用配置的API
    
    Args:
        config: API配置对象
        data: 请求数据
        files: 文件数据字典 {field_name: file_path}
    
    Returns:
        dict: API响应结果
    """
    try:
        # 构建完整的URL
        url = f"{config.api_url.rstrip('/')}/{config.api_path.lstrip('/')}"
        
        # 准备请求数据
        request_data = {}
        for key, value in data.items():
            # 如果是base64数据，直接使用
            if isinstance(value, str) and value.startswith('data:'):
                request_data[key] = value
            else:
                request_data[key] = value
        
        # 打印请求信息用于调试
        print(f"API URL: {url}")
        print(f"Request Method: {config.method}")
        print(f"Request Data: {json.dumps(request_data, indent=2)}")
        
        # 根据API路径和功能选择不同的请求格式
        api_path_lower = config.api_path.lower()
        
        if config.method == 'POST':
            # 处理文件上传
            request_files = {}
            if files:
                for field_name, file_path in files.items():
                    if os.path.exists(file_path):
                        request_files[field_name] = open(file_path, 'rb')
            
            # 1. 学生认证功能 - multipart/form-data
            if 'student/authenticate' in api_path_lower or 'student/verify' in api_path_lower:
                if request_files:
                    response = requests.post(url, data=request_data, files=request_files)
                else:
                    response = requests.post(url, data=request_data)
            
            # 2. 学生搜索功能 - 标准JSON
            elif 'student/search' in api_path_lower or 'student/query' in api_path_lower:
                response = requests.post(
                    url,
                    json=request_data,
                    headers={
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    }
                )
            
            # 3. 论文搜索功能 - 使用raw JSON字符串
            elif 'thesis/search' in api_path_lower or 'paper/search' in api_path_lower:
                response = requests.post(
                    url,
                    data=json.dumps(request_data),
                    headers={
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    }
                )
            
            # 4. 论文下载功能 
            # 4. 论文下载功能 
            elif 'thesis/pdf' in api_path_lower or 'paper/download' in api_path_lower or 'thesis/download' in api_path_lower:
                # 使用表单数据格式而非JSON
                response = requests.post(
                    url,
                    data=request_data,  # 使用表单数据格式
                    headers={
                        'Accept': 'application/json'
                    }
                )
            
            # 5 & 6. 其他功能 - 使用原始格式
            else:
                if request_files:
                    response = requests.post(url, data=request_data, files=request_files)
                else:
                    response = requests.post(
                        url,
                        json=request_data,
                        headers={
                            'Content-Type': 'application/json',
                            'Accept': 'application/json'
                        }
                    )
        else:
            # GET请求
            response = requests.get(
                url,
                params=request_data,
                headers={'Accept': 'application/json'}
            )
        
        # 打印响应信息用于调试
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {response.headers}")
        try:
            print(f"Response Body: {response.text}")
        except:
            pass
        
        # 处理响应
        if response.status_code == 200:
            try:
                return response.json()
            except ValueError:
                return {'error': '无效的API响应格式'}
        else:
            # 尝试获取更详细的错误信息
            try:
                error_detail = response.json()
                return {'error': f'API调用失败1: {response.status_code}', 'detail': error_detail}
            except:
                return {'error': f'API调用失败2: {response.status_code}', 'detail': response.text}
            
    except Exception as e:
        print(f"API调用异常: {str(e)}")
        return {'error': str(e)}
    finally:
        # 关闭并清理文件
        if files and 'request_files' in locals():
            for file_obj in request_files.values():
                try:
                    file_obj.close()
                except:
                    pass
            
            # 删除临时文件
            for file_path in files.values():
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except:
                        pass