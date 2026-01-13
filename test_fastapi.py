"""
FastAPI应用测试脚本
"""
import sys
import os
import requests
import time
import threading

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_fastapi_app():
    """测试FastAPI应用"""
    try:
        # 导入FastAPI应用
        from src.api.main import FastAPIApp
        
        # 创建应用实例
        fastapi_app = FastAPIApp()
        
        # 获取端口信息
        port = fastapi_app.instance_manager.port
        base_url = f"http://localhost:{port}"
        
        print(f"测试FastAPI应用...")
        print(f"服务地址: {base_url}")
        print(f"API文档: {base_url}/docs")
        print(f"健康检查: {base_url}/api/v1/health")
        
        # 在后台线程中运行FastAPI应用
        def run_app():
            try:
                fastapi_app.run()
            except Exception as e:
                print(f"FastAPI应用运行异常: {e}")
        
        # 启动FastAPI服务
        thread = threading.Thread(target=run_app, daemon=True)
        thread.start()
        
        # 等待服务启动
        print("等待服务启动...")
        time.sleep(3)
        
        # 测试健康检查接口
        try:
            response = requests.get(f"{base_url}/api/v1/health", timeout=5)
            if response.status_code == 200:
                print("✓ 健康检查接口测试通过")
                print(f"响应内容: {response.json()}")
            else:
                print(f"✗ 健康检查接口测试失败，状态码: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"✗ 健康检查接口测试失败: {e}")
        
        # 测试系统信息接口
        try:
            response = requests.get(f"{base_url}/api/v1/health/system", timeout=5)
            if response.status_code == 200:
                print("✓ 系统信息接口测试通过")
                print(f"响应内容: {response.json()}")
            else:
                print(f"✗ 系统信息接口测试失败，状态码: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"✗ 系统信息接口测试失败: {e}")
        
        # 测试系统状态接口
        try:
            response = requests.get(f"{base_url}/api/v1/system/status", timeout=5)
            if response.status_code == 200:
                print("✓ 系统状态接口测试通过")
                print(f"响应内容: {response.json()}")
            else:
                print(f"✗ 系统状态接口测试失败，状态码: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"✗ 系统状态接口测试失败: {e}")
        
        print("\n测试完成！")
        print("按Ctrl+C退出测试...")
        
        # 保持运行，让用户可以通过浏览器访问
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n测试结束")
            
    except ImportError as e:
        print(f"导入FastAPI模块失败: {e}")
        print("请确保已安装FastAPI相关依赖:")
        print("pip install fastapi uvicorn pydantic psutil")
    except Exception as e:
        print(f"测试过程中出现错误: {e}")

if __name__ == "__main__":
    test_fastapi_app()