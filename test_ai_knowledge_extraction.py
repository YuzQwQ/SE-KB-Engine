#!/usr/bin/env python3
"""
测试新的AI驱动知识提取函数
验证其能正确使用提示词进行知识提取
"""

import json
import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server import extract_knowledge_with_ai

def load_test_content():
    """加载之前保存的测试内容"""
    try:
        with open('test_content.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data['content'], data['metadata']
    except FileNotFoundError:
        print("❌ 未找到test_content.json文件，请先运行之前的测试脚本")
        return None, None
    except Exception as e:
        print(f"❌ 加载测试内容失败: {e}")
        return None, None

def validate_ai_result_structure(result_data):
    """验证AI提取结果的结构和内容质量"""
    try:
        # 检查基本结构
        if not isinstance(result_data, dict):
            print("❌ 结果不是字典格式")
            return False
        
        if not result_data.get('success'):
            print(f"❌ 提取失败: {result_data.get('error', '未知错误')}")
            return False
        
        knowledge_base = result_data.get('knowledge_base', {})
        if not knowledge_base:
            print("❌ 未找到knowledge_base字段")
            return False
        
        # 检查metadata
        metadata = knowledge_base.get('metadata', {})
        required_metadata = ['knowledge_id', 'title', 'description', 'version', 'created_time']
        for field in required_metadata:
            if field not in metadata:
                print(f"❌ metadata缺少字段: {field}")
                return False
        
        # 检查generation_knowledge
        gen_knowledge = knowledge_base.get('generation_knowledge', {})
        if not gen_knowledge:
            print("❌ 未找到generation_knowledge字段")
            return False
        
        # 验证每个字段的内容数量
        validation_results = {}
        
        # 检查concepts
        concepts = gen_knowledge.get('concepts', [])
        validation_results['concepts'] = len(concepts)
        if len(concepts) < 3:
            print(f"⚠️  concepts数量不足: {len(concepts)} < 3")
        else:
            print(f"✅ concepts数量充足: {len(concepts)}")
        
        # 检查rules
        rules = gen_knowledge.get('rules', [])
        validation_results['rules'] = len(rules)
        if len(rules) < 3:
            print(f"⚠️  rules数量不足: {len(rules)} < 3")
        else:
            print(f"✅ rules数量充足: {len(rules)}")
        
        # 检查patterns
        patterns = gen_knowledge.get('patterns', [])
        validation_results['patterns'] = len(patterns)
        if len(patterns) < 3:
            print(f"⚠️  patterns数量不足: {len(patterns)} < 3")
        else:
            print(f"✅ patterns数量充足: {len(patterns)}")
        
        # 检查transformations
        transformations = gen_knowledge.get('transformations', [])
        validation_results['transformations'] = len(transformations)
        if len(transformations) < 3:
            print(f"⚠️  transformations数量不足: {len(transformations)} < 3")
        else:
            print(f"✅ transformations数量充足: {len(transformations)}")
        
        # 检查validation_knowledge
        val_knowledge = knowledge_base.get('validation_knowledge', {})
        criteria = val_knowledge.get('criteria', [])
        validation_results['criteria'] = len(criteria)
        if len(criteria) < 3:
            print(f"⚠️  criteria数量不足: {len(criteria)} < 3")
        else:
            print(f"✅ criteria数量充足: {len(criteria)}")
        
        # 检查examples
        examples = knowledge_base.get('examples', {})
        input_examples = examples.get('input_examples', [])
        validation_results['input_examples'] = len(input_examples)
        if len(input_examples) < 3:
            print(f"⚠️  input_examples数量不足: {len(input_examples)} < 3")
        else:
            print(f"✅ input_examples数量充足: {len(input_examples)}")
        
        # 计算总体评分
        total_fields = len(validation_results)
        sufficient_fields = sum(1 for count in validation_results.values() if count >= 3)
        score = (sufficient_fields / total_fields) * 100
        
        print(f"\n📊 AI提取结果评估:")
        print(f"   - 总字段数: {total_fields}")
        print(f"   - 达标字段数: {sufficient_fields}")
        print(f"   - 总体评分: {score:.1f}%")
        
        # 显示详细统计
        print(f"\n📈 详细统计:")
        for field, count in validation_results.items():
            status = "✅" if count >= 3 else "❌"
            print(f"   - {field}: {count} 条 {status}")
        
        return score >= 70  # 70%以上算通过
        
    except Exception as e:
        print(f"❌ 验证过程出错: {e}")
        return False

def test_ai_knowledge_extraction():
    """测试AI驱动的知识提取功能"""
    print("🚀 开始测试AI驱动知识提取功能...")
    
    # 加载测试内容
    with open('temp_content.txt', 'r', encoding='utf-8') as f:
        full_content = f.read()
    
    # 截取前3000字符进行测试，避免超时
    content = full_content[:3000] + "..." if len(full_content) > 3000 else full_content
    
    with open('temp_metadata.json', 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    url = metadata['url']
    title = metadata['title']
    
    print(f"📄 测试内容长度: {len(content)} 字符")
    print(f"📋 元数据: {metadata}")
    
    try:
        # 调用新的AI驱动知识提取函数
        print("\n🔄 调用extract_knowledge_with_ai函数...")
        result_json = extract_knowledge_with_ai(
            content=content,
            url=url,
            title=title,
            requirement_type="需求分析",
            target_conversion_type="数据流图",
            prompt_type="universal_knowledge"
        )
        
        # 解析结果
        try:
            result_data = json.loads(result_json)
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析错误: {e}")
            print(f"原始响应: {result_json[:500]}...")
            return False
        
        # 保存结果到文件
        output_file = 'ai_knowledge_extraction_result.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        print(f"💾 结果已保存到: {output_file}")
        
        # 验证结果结构和质量
        if validate_ai_result_structure(result_data):
            print("\n🎉 AI知识提取测试通过！")
            return True
        else:
            print("\n❌ AI知识提取测试失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程出错: {e}")
        import traceback
        print(f"🔍 详细错误信息: {traceback.format_exc()}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("🧪 AI驱动知识提取功能测试")
    print("=" * 60)
    
    success = test_ai_knowledge_extraction()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 所有测试通过！AI驱动知识提取功能正常工作")
    else:
        print("❌ 测试失败！需要进一步调试")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    main()