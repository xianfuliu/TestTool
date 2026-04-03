# 应用配置
APP_CONFIG = {"name": "接口自动化平台", "version": "1.0.0", "author": "liuxianfu"}

# 业务数据库配置列表，支持配置多个数据库
BIZ_DATABASES = [
    {
        "name": "业务数据库",  # 数据库名称标识
        "host": "47.106.192.83",  # 数据库主机地址
        "port": 3306,  # 数据库端口
        "user": "xvdba",  # 数据库用户名
        "password": "xvdba@2022",  # 数据库密码
        "database": "cfloan_biz",  # 数据库名称
        "charset": "utf8mb4",  # 字符集
        "autocommit": False,  # 是否自动提交事务
    },
    {
        "name": "测试数据库",
        "host": "test.example.com",
        "port": 3306,
        "user": "test_user",
        "password": "test_password",
        "database": "test_db",
        "charset": "utf8mb4",
        "autocommit": False,
    },
    # 可以继续添加更多数据库配置
]
