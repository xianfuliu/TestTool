import socket


def get_local_ip():
    """获取本机IP地址"""
    try:
        # 创建一个UDP套接字连接到一个外部服务器（不实际发送数据）
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Google的公共DNS
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        return "127.0.0.1"  # 失败则返回本地回环地址


print("本机IP地址:", get_local_ip())
