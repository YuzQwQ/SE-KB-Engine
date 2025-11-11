#!/usr/bin/env python3
"""
简单的AI知识提取测试
"""

import json
import sys
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server import extract_knowledge_with_ai

def test_simple_extraction():
    """测试简单的AI知识提取"""
    
    # 简单的测试内容
    test_content = """
    软件需求分析是软件开发过程中的重要环节。
    它包括功能需求和非功能需求的分析。
    功能需求描述系统应该做什么，非功能需求描述系统应该如何工作。
    需求分析的目标是确保开发的软件能够满足用户的实际需要。
    """
    
    print("🧪 开始简单AI知识提取测试...")
    print(f"📄 测试内容: {test_content.strip()}")
    
    try:
        print("\n🔄 调用extract_knowledge_with_ai函数...")
        result = extract_knowledge_with_ai(
            content=test_content,
            url="test://example.com",
            title="软件需求分析测试",
            requirement_type="需求分析",
            target_conversion_type="知识提取",
            prompt_type="universal_knowledge"
        )
        
        print("✅ 函数调用成功")
        print(f"📊 结果类型: {type(result)}")
        print(f"📊 结果长度: {len(result) if result else 0}")
        
        if result:
            # 尝试解析结果
            try:
                result_json = json.loads(result)
                print("✅ 结果JSON解析成功")
                print(f"📊 成功状态: {result_json.get('success', 'unknown')}")
                
                if result_json.get('success'):
                    print("🎉 AI知识提取成功！")
                    # 保存结果
                    with open('simple_ai_result.json', 'w', encoding='utf-8') as f:
                        json.dump(result_json, f, ensure_ascii=False, indent=2)
                    print("💾 结果已保存到: simple_ai_result.json")
                else:
                    print(f"❌ AI知识提取失败: {result_json.get('error', 'unknown error')}")
                    
            except json.JSONDecodeError as e:
                print(f"❌ 结果JSON解析失败: {e}")
                print(f"原始结果: {result[:500]}...")
        else:
            print("❌ 函数返回空结果")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        print(f"详细错误: {traceback.format_exc()}")

if __name__ == "__main__":
    test_simple_extraction()