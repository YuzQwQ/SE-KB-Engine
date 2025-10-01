#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公网访问模式启动脚本

这个脚本会启动Web服务器并允许外部网络访问。
其他人可以通过你的IP地址访问这个服务。

使用方法:
1. 直接运行: python start_public_server.py
2. 自定义端口: python start_public_server.py --port 9000
3. 自定义主机: python start_public_server.py --host 192.168.1.100

安全提醒:
- 确保你的防火墙允许指定端口的访问
- 在公网环境中使用时要注意安全性
- 建议在受信任的网络环境中使用
"""

import os
import sys
import argparse
import asyncio
from web_client import MCPWebClient


def get_local_ip():
    """获取本机IP地址"""
    import socket
    try:
        # 连接到一个远程地址来获取本机IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def print_access_info(host, port):
    """打印访问信息"""
    local_ip = get_local_ip()
    
    print("\n" + "="*60)
    print("🌐 MCP Web客户端 - 公网访问模式")
    print("="*60)
    print(f"📱 本地访问地址: http://127.0.0.1:{port}")
    
    if host == "0.0.0.0":
        print(f"🌍 局域网访问地址: http://{local_ip}:{port}")
        print(f"🔗 外部访问地址: http://[你的公网IP]:{port}")
    else:
        print(f"🌍 指定访问地址: http://{host}:{port}")
    
    print(f"📚 API文档: http://{host if host != '0.0.0.0' else local_ip}:{port}/docs")
    print("\n💡 使用提示:")
    print("   - 其他人可以通过上述地址访问你的服务")
    print("   - 确保防火墙允许该端口的访问")
    print("   - 按 Ctrl+C 停止服务器")
    print("="*60 + "\n")


async def main():
    parser = argparse.ArgumentParser(description="启动MCP Web客户端 - 公网访问模式")
    parser.add_argument("--host", default="0.0.0.0", 
                       help="服务器主机地址 (默认: 0.0.0.0 - 允许所有IP访问)")
    parser.add_argument("--port", type=int, default=8000,
                       help="服务器端口 (默认: 8000)")
    
    args = parser.parse_args()
    
    # 设置环境变量
    os.environ["WEB_HOST"] = args.host
    os.environ["WEB_PORT"] = str(args.port)
    
    client = MCPWebClient()
    
    try:
        print("🔧 正在连接到MCP服务器...")
        # 连接到MCP服务器
        server_script = "server.py"
        await client.connect_to_server(server_script)
        
        print_access_info(args.host, args.port)
        
        # 启动Web服务器
        await client.start_server(host=args.host, port=args.port)
        
    except KeyboardInterrupt:
        print("\n👋 正在关闭服务器...")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        print("\n🔍 可能的解决方案:")
        print("   1. 检查端口是否被占用")
        print("   2. 确保有足够的权限")
        print("   3. 检查防火墙设置")
        sys.exit(1)
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())