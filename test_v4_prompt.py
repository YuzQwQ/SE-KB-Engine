#!/usr/bin/env python3
"""
测试V4版本的requirement_analysis提示词效果（示例驱动策略）
"""

import json
import sys
import os
import shutil

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server import extract_universal_knowledge

def test_v4_requirement_analysis():
    """测试V4版本的需求分析提示词（示例驱动策略）"""
    
    print("=== 测试V4版本的requirement_analysis提示词（示例驱动策略） ===")
    
    # 读取之前保存的内容和元数据
    try:
        with open('temp_content.txt', 'r', encoding='utf-8') as f:
            content = f.read()
        
        with open('temp_metadata.json', 'r', encoding='utf-8') as f:
            metadata = json.load(f)
            
        print(f"内容长度: {len(content)} 字符")
        print(f"元数据: {metadata}")
        
    except FileNotFoundError as e:
        print(f"错误：找不到测试文件 - {e}")
        return False
    
    # 配置文件路径
    original_config_path = 'config/system_prompts.json'
    backup_config_path = 'config/system_prompts_backup_v4.json'
    new_config_path = 'config/system_prompts_v4.json'
    
    try:
        # 备份原配置
        shutil.copy(original_config_path, backup_config_path)
        
        # 使用V4配置
        shutil.copy(new_config_path, original_config_path)
        
        print("\n调用extract_universal_knowledge工具（使用V4示例驱动提示词）...")
        result = extract_universal_knowledge(
            content=content,
            url=metadata.get('url', ''),
            title=metadata.get('title', ''),
            requirement_type="需求分析",
            target_conversion_type="通用知识库"
        )
        
        # 保存结果到文件
        output_file = 'v4_requirement_analysis_result.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"结果已保存到: {output_file}")
        
        # 解析JSON结果进行验证
        try:
            result_data = json.loads(result)
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            return False
        
        print("\n=== V4版本结构验证和最小输出量检查 ===\n")
        return validate_v4_result_structure(result_data)
        
    except Exception as e:
        print(f"错误：调用extract_universal_knowledge失败 - {e}")
        return False
    
    finally:
        # 恢复原配置
        try:
            shutil.copy(backup_config_path, original_config_path)
            os.remove(backup_config_path)
            print("\n✅ 已恢复原始配置文件")
        except Exception as e:
            print(f"⚠️ 恢复配置文件时出错: {e}")

def validate_v4_result_structure(result_data):
    """验证V4版本结果结构和最小输出量"""
    try:
        # 检查是否有success字段和knowledge_base
        if not result_data.get('success'):
            print("❌ 提取失败")
            return False
            
        knowledge_base = result_data.get('knowledge_base', {})
        if not knowledge_base:
            print("❌ 缺少knowledge_base字段")
            return False
        
        # 检查generation_knowledge
        generation_knowledge = knowledge_base.get('generation_knowledge', {})
        if not generation_knowledge:
            print("❌ 缺少必需字段: generation_knowledge")
            return False
        
        # 统计各个字段的提取数量
        concepts = generation_knowledge.get('concepts', [])
        rules = generation_knowledge.get('rules', [])
        patterns = generation_knowledge.get('patterns', [])
        transformations = generation_knowledge.get('transformations', [])
        
        validation_knowledge = knowledge_base.get('validation_knowledge', {})
        criteria = validation_knowledge.get('criteria', [])
        checklist = validation_knowledge.get('checklist', [])
        error_patterns = validation_knowledge.get('error_patterns', [])
        
        examples = knowledge_base.get('examples', {})
        input_examples = examples.get('input_examples', [])
        
        print(f"📊 V4版本（示例驱动）提取统计:")
        print(f"  🧠 Generation Knowledge:")
        print(f"    - Concepts: {len(concepts)} 条")
        print(f"    - Rules: {len(rules)} 条")
        print(f"    - Patterns: {len(patterns)} 条")
        print(f"    - Transformations: {len(transformations)} 条")
        print(f"  ✅ Validation Knowledge:")
        print(f"    - Criteria: {len(criteria)} 条")
        print(f"    - Checklist: {len(checklist)} 条")
        print(f"    - Error Patterns: {len(error_patterns)} 条")
        print(f"  📝 Examples:")
        print(f"    - Input Examples: {len(input_examples)} 条")
        
        # 检查最小输出量要求
        requirements = {
            'concepts': {'actual': len(concepts), 'required': 5},
            'rules': {'actual': len(rules), 'required': 4},
            'patterns': {'actual': len(patterns), 'required': 3},
            'transformations': {'actual': len(transformations), 'required': 2},
            'criteria': {'actual': len(criteria), 'required': 3},
            'checklist': {'actual': len(checklist), 'required': 5},
            'error_patterns': {'actual': len(error_patterns), 'required': 3},
            'input_examples': {'actual': len(input_examples), 'required': 3}
        }
        
        failed_fields = []
        success_fields = []
        
        for field, counts in requirements.items():
            actual = counts['actual']
            required = counts['required']
            if actual < required:
                failed_fields.append(f"{field} (需要{required}条，实际{actual}条)")
            else:
                success_fields.append(f"{field} (需要{required}条，实际{actual}条)")
        
        print(f"\n✅ 满足要求的字段:")
        for field in success_fields:
            print(f"   ✓ {field}")
        
        if failed_fields:
            print(f"\n❌ 未满足最小输出量要求的字段:")
            for field in failed_fields:
                print(f"   ✗ {field}")
        
        # 显示一些示例内容（如果有的话）
        if concepts:
            print(f"\n📝 Concepts示例:")
            for i, concept in enumerate(concepts[:2]):
                name = concept.get('name', 'N/A')
                definition = concept.get('definition', 'N/A')[:100]
                print(f"   {i+1}. {name}: {definition}...")
        
        if rules:
            print(f"\n📋 Rules示例:")
            for i, rule in enumerate(rules[:2]):
                condition = rule.get('condition', 'N/A')
                action = rule.get('action', 'N/A')[:80]
                print(f"   {i+1}. 当{condition}时 -> {action}...")
        
        if patterns:
            print(f"\n🔄 Patterns示例:")
            for i, pattern in enumerate(patterns[:2]):
                name = pattern.get('name', 'N/A')
                structure = pattern.get('structure', 'N/A')[:80]
                print(f"   {i+1}. {name}: {structure}...")
        
        # 判断整体成功
        if not failed_fields:
            print(f"\n🎉 V4版本（示例驱动）：所有字段都满足最小输出量要求！")
            return True
        else:
            print(f"\n💥 V4版本仍有{len(failed_fields)}个字段未达标")
            return False
        
    except Exception as e:
        print(f"❌ 验证过程中出错: {e}")
        return False

if __name__ == "__main__":
    success = test_v4_requirement_analysis()
    if success:
        print("\n🎉 V4版本（示例驱动策略）测试成功！")
    else:
        print("\n💥 V4版本测试失败，需要进一步优化。")