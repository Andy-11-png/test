# Flask MySQL 项目

这是一个使用 Flask 和 MySQL 5.7 的示例项目。

## 项目结构

```
app/
├── static/          # 静态文件
│   ├── css/        # CSS 文件
│   ├── js/         # JavaScript 文件
│   └── images/     # 图片文件
├── templates/      # HTML 模板
├── models/         # 数据模型
├── controllers/    # 控制器
└── config/         # 配置文件
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置

1. 复制 `.env.example` 为 `.env`
2. 修改 `.env` 文件中的数据库配置

## 运行

```bash
python run.py
```

## 数据库设置

1. 确保 MySQL 5.7 已安装并运行
2. 创建数据库：

```sql
CREATE DATABASE flask_db;
```

## 功能特性

- 模块化结构
- MySQL 数据库集成
- 蓝图路由管理
- 环境变量配置
- 静态文件管理
