"""
检查 LLM Preselector 配置是否正确

用法: python scripts/check_config.py
"""

import os
import sys
from pathlib import Path

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_env():
    """加载 .env 文件"""
    env_path = Path('.env')
    loaded = {}
    if env_path.exists():
        print(f"✅ 找到 .env 文件: {env_path.absolute()}")
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                k, v = k.strip(), v.strip()
                if k and v:
                    loaded[k] = v
                    if os.getenv(k) is None:
                        os.environ[k] = v
    else:
        print("❌ 未找到 .env 文件")
    return loaded


def check_preselector_config():
    """检查 Preselector 配置"""
    print("\n" + "=" * 50)
    print("🔍 Preselector 配置检查")
    print("=" * 50)
    
    filter_url = os.getenv('FILTER_BASE_URL', '')
    filter_key = os.getenv('FILTER_API_KEY', '')
    filter_model = os.getenv('FILTER_MODEL_ID', 'Qwen/Qwen2.5-7B-Instruct')
    
    print(f"\nFILTER_BASE_URL: {filter_url if filter_url else '❌ 未设置'}")
    print(f"FILTER_API_KEY: {'✅ 已设置 (' + filter_key[:10] + '...)' if filter_key else '❌ 未设置'}")
    print(f"FILTER_MODEL_ID: {filter_model}")
    
    if filter_url and filter_key:
        print("\n✅ Preselector 配置完整，将启用 Enhanced 模式")
        return True
    else:
        print("\n⚠️ Preselector 配置不完整，将使用 Legacy 模式")
        return False


def check_main_llm_config():
    """检查主 LLM 配置"""
    print("\n" + "=" * 50)
    print("🔍 主 LLM 配置检查")
    print("=" * 50)
    
    kb_url = os.getenv('KB_BASE_URL', '')
    kb_key = os.getenv('KB_API_KEY', '')
    kb_model = os.getenv('KB_MODEL_ID', '')
    
    print(f"\nKB_BASE_URL: {kb_url if kb_url else '❌ 未设置'}")
    print(f"KB_API_KEY: {'✅ 已设置 (' + kb_key[:10] + '...)' if kb_key else '❌ 未设置'}")
    print(f"KB_MODEL_ID: {kb_model if kb_model else '❌ 未设置'}")
    
    if kb_url and kb_key and kb_model:
        print("\n✅ 主 LLM 配置完整")
        return True
    else:
        print("\n⚠️ 主 LLM 配置不完整")
        return False


def check_registry_mode():
    """检查 Registry 模式"""
    print("\n" + "=" * 50)
    print("🔍 Registry 模式检查")
    print("=" * 50)
    
    from registry import get_registry_mode, _use_enhanced_adapters
    
    mode = get_registry_mode()
    print(f"\n当前模式: {mode.upper()}")
    print(f"_use_enhanced_adapters(): {_use_enhanced_adapters()}")
    
    explicit = os.getenv('USE_ENHANCED_ADAPTERS', '')
    if explicit:
        print(f"USE_ENHANCED_ADAPTERS 显式设置为: {explicit}")
    else:
        print("USE_ENHANCED_ADAPTERS 未显式设置，使用自动检测")


def test_preselector_connection():
    """测试 Preselector API 连接"""
    print("\n" + "=" * 50)
    print("🔍 测试 Preselector API 连接")
    print("=" * 50)
    
    filter_url = os.getenv('FILTER_BASE_URL', '')
    filter_key = os.getenv('FILTER_API_KEY', '')
    
    if not filter_url or not filter_key:
        print("\n⚠️ 未配置，跳过连接测试")
        return
    
    try:
        import httpx
        url = f"{filter_url.rstrip('/')}/models"
        headers = {'Authorization': f'Bearer {filter_key}'}
        
        print(f"\n正在测试连接: {url}")
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200:
                print("✅ API 连接成功!")
                data = resp.json()
                if 'data' in data:
                    models = [m.get('id', '') for m in data['data'][:5]]
                    print(f"   可用模型: {models}")
            else:
                print(f"❌ API 返回错误: {resp.status_code}")
                print(f"   响应: {resp.text[:200]}")
    except Exception as e:
        print(f"❌ 连接失败: {e}")


def main():
    print("=" * 50)
    print("🔧 LLM Preselector 配置诊断")
    print("=" * 50)
    
    loaded = load_env()
    print(f"\n从 .env 加载的变量: {list(loaded.keys())}")
    
    preselector_ok = check_preselector_config()
    main_llm_ok = check_main_llm_config()
    check_registry_mode()
    
    if preselector_ok:
        test_preselector_connection()
    
    print("\n" + "=" * 50)
    print("📋 总结")
    print("=" * 50)
    
    if preselector_ok and main_llm_ok:
        print("\n✅ 所有配置正确，系统应使用 Enhanced 模式")
    elif main_llm_ok:
        print("\n⚠️ Preselector 未配置，系统将使用 Legacy 模式")
        print("   要启用 Enhanced 模式，请配置 FILTER_BASE_URL 和 FILTER_API_KEY")
    else:
        print("\n❌ 配置不完整，请检查 .env 文件")


if __name__ == "__main__":
    main()

