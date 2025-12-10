"""
诊断 .env 配置问题
"""

import os
from pathlib import Path

def diagnose():
    print("=" * 60)
    print("🔍 诊断 .env 配置")
    print("=" * 60)
    
    env_path = Path('.env')
    
    # 检查 .env 文件是否存在
    print(f"\n📁 .env 文件位置: {env_path.absolute()}")
    print(f"   文件存在: {'✅ 是' if env_path.exists() else '❌ 否'}")
    
    if not env_path.exists():
        print("\n❌ .env 文件不存在！请创建 .env 文件并添加配置。")
        print("\n示例 .env 内容:")
        print("-" * 40)
        print("""# Preselector (小模型筛选)
FILTER_BASE_URL=https://api.siliconflow.cn/v1
FILTER_API_KEY=sk-your-key-here
FILTER_MODEL_ID=Qwen/Qwen2.5-7B-Instruct

# 主抽取模型
KB_BASE_URL=https://api.siliconflow.cn/v1
KB_API_KEY=sk-your-key-here
KB_MODEL_ID=Qwen/Qwen2.5-72B-Instruct""")
        return
    
    # 读取并解析 .env 文件
    print("\n📄 .env 文件内容分析:")
    print("-" * 40)
    
    env_vars = {}
    try:
        content = env_path.read_text(encoding='utf-8')
        lines = content.splitlines()
        
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            if not line_stripped:
                continue
            if line_stripped.startswith('#'):
                print(f"   行 {i}: [注释] {line_stripped[:50]}")
                continue
            
            if '=' in line_stripped:
                key, value = line_stripped.split('=', 1)
                key = key.strip()
                value = value.strip()
                env_vars[key] = value
                
                # 检查值是否有问题
                issues = []
                if not value:
                    issues.append("值为空")
                if value.startswith('"') and not value.endswith('"'):
                    issues.append("引号不匹配")
                if '=' in value and not value.startswith('sk-'):
                    issues.append("⚠️ 值中包含 '='，可能是配置错误")
                
                display_value = f"{value[:30]}..." if len(value) > 30 else value
                status = "⚠️" if issues else "✅"
                print(f"   行 {i}: {status} {key} = {display_value}")
                if issues:
                    for issue in issues:
                        print(f"          └─ {issue}")
            else:
                print(f"   行 {i}: ❓ 无法解析: {line_stripped[:40]}")
    
    except Exception as e:
        print(f"   ❌ 读取失败: {e}")
        return
    
    # 检查关键变量
    print("\n🔑 关键配置检查:")
    print("-" * 40)
    
    required_vars = {
        'FILTER_BASE_URL': '小模型 API 地址',
        'FILTER_API_KEY': '小模型 API 密钥',
        'FILTER_MODEL_ID': '小模型 ID',
        'KB_BASE_URL': '主模型 API 地址',
        'KB_API_KEY': '主模型 API 密钥',
        'KB_MODEL_ID': '主模型 ID',
    }
    
    preselector_ready = True
    for var, desc in required_vars.items():
        value = env_vars.get(var, '')
        env_value = os.getenv(var, '')
        
        if var.startswith('FILTER_'):
            if not value:
                preselector_ready = False
        
        if value:
            display = f"{value[:20]}..." if len(value) > 20 else value
            print(f"   ✅ {var}: {display}")
        else:
            print(f"   ❌ {var}: 未配置 ({desc})")
    
    # 判断模式
    print("\n🎯 Adapter 模式判断:")
    print("-" * 40)
    
    filter_url = env_vars.get('FILTER_BASE_URL', '')
    filter_key = env_vars.get('FILTER_API_KEY', '')
    use_enhanced = env_vars.get('USE_ENHANCED_ADAPTERS', '').lower()
    
    if use_enhanced in ('true', '1', 'yes', 'on'):
        print("   模式: 强制 Enhanced (USE_ENHANCED_ADAPTERS=true)")
    elif use_enhanced in ('false', '0', 'no', 'off'):
        print("   模式: 强制 Legacy (USE_ENHANCED_ADAPTERS=false)")
    elif filter_url and filter_key:
        print("   模式: Enhanced (自动检测到 FILTER_* 配置)")
    else:
        print("   模式: Legacy (未检测到 FILTER_* 配置)")
        print(f"         FILTER_BASE_URL: {'有' if filter_url else '无'}")
        print(f"         FILTER_API_KEY: {'有' if filter_key else '无'}")
    
    # 手动加载并验证
    print("\n🔄 手动加载 .env 到环境变量...")
    for key, value in env_vars.items():
        if os.getenv(key) is None:
            os.environ[key] = value
    
    # 再次检查
    print("\n📊 加载后的环境变量:")
    print("-" * 40)
    for var in required_vars:
        val = os.getenv(var, '')
        display = f"{val[:30]}..." if len(val) > 30 else val
        print(f"   {var}: {display if val else '(空)'}")
    
    # 测试 registry
    print("\n🧪 测试 Registry 模式:")
    print("-" * 40)
    try:
        from registry import get_registry_mode, _use_enhanced_adapters
        mode = get_registry_mode()
        print(f"   Registry 模式: {mode}")
        print(f"   _use_enhanced_adapters(): {_use_enhanced_adapters()}")
    except Exception as e:
        print(f"   ❌ 导入失败: {e}")
    
    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)


if __name__ == "__main__":
    diagnose()

