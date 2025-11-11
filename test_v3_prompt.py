#!/usr/bin/env python3
"""
测试V3版本的requirement_analysis提示词效果
"""

import json
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server import extract_universal_knowledge

def test_v3_requirement_analysis():
    """测试V3版本的需求分析提示词"""
    
    print("=== 测试V3版本的requirement_analysis提示词 ===")
    
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
    
    # 临时修改系统提示词配置
    original_config_path = 'config/system_prompts.json'
    backup_config_path = 'config/system_prompts_backup.json'
    new_config_path = 'config/system_prompts_v3.json'
    
    try:
        # 备份原配置
        import shutil
        shutil.copy(original_config_path, backup_config_path)
        
        # 使用新配置
        shutil.copy(new_config_path, original_config_path)
        
        print("\n调用extract_universal_knowledge工具（使用V3提示词）...")
        result = extract_universal_knowledge(
            content=content,
            url=metadata.get('url', ''),
            title=metadata.get('title', ''),
            requirement_type="需求分析",
            target_conversion_type="通用知识库"
        )
        
        # 保存结果到文件
        output_file = 'v3_requirement_analysis_result.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"结果已保存到: {output_file}")
        
        # 解析JSON结果进行验证
        try:
            result_data = json.loads(result)
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            return False
        
        print("\n=== V3版本结构验证和最小输出量检查 ===")
        return validate_v3_result_structure(result_data)
        
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

def validate_v3_result_structure(result_data):
    """验证V3版本结果结构和最小输出量"""
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
        
        # 检查各个子字段的最小输出量
        concepts = generation_knowledge.get('concepts', [])
        rules = generation_knowledge.get('rules', [])
        patterns = generation_knowledge.get('patterns', [])
        transformations = generation_knowledge.get('transformations', [])
        
        print(f"📊 V3版本提取统计:")
        print(f"  - Concepts: {len(concepts)} 条")
        print(f"  - Rules: {len(rules)} 条")
        print(f"  - Patterns: {len(patterns)} 条")
        print(f"  - Transformations: {len(transformations)} 条")
        
        # 检查validation_knowledge
        validation_knowledge = knowledge_base.get('validation_knowledge', {})
        if validation_knowledge:
            criteria = validation_knowledge.get('criteria', [])
            checklist = validation_knowledge.get('checklist', [])
            error_patterns = validation_knowledge.get('error_patterns', [])
            print(f"  - Validation Criteria: {len(criteria)} 条")
            print(f"  - Validation Checklist: {len(checklist)} 条")
            print(f"  - Error Patterns: {len(error_patterns)} 条")
        
        # 检查examples
        examples = knowledge_base.get('examples', {})
        if examples:
            input_examples = examples.get('input_examples', [])
            print(f"  - Input Examples: {len(input_examples)} 条")
        
        # 检查最小输出量要求
        min_requirements = {
            'concepts': 5,
            'rules': 4,
            'patterns': 3,
            'transformations': 2
        }
        
        failed_fields = []
        success_fields = []
        
        for field, min_count in min_requirements.items():
            actual_count = len(generation_knowledge.get(field, []))
            if actual_count < min_count:
                failed_fields.append(f"{field} (需要至少{min_count}条，实际{actual_count}条)")
            else:
                success_fields.append(f"{field} (需要{min_count}条，实际{actual_count}条)")
        
        print(f"\n✅ 满足要求的字段:")
        for field in success_fields:
            print(f"   - {field}")
        
        if failed_fields:
            print(f"\n❌ 未满足最小输出量要求的字段:")
            for field in failed_fields:
                print(f"   - {field}")
            return False
        
        print("\n🎉 V3版本：所有字段都满足最小输出量要求！")
        
        # 显示一些示例内容
        if concepts:
            print(f"\n📝 Concepts示例:")
            for i, concept in enumerate(concepts[:2]):
                print(f"   {i+1}. {concept.get('name', 'N/A')}: {concept.get('definition', 'N/A')[:100]}...")
        
        if rules:
            print(f"\n📋 Rules示例:")
            for i, rule in enumerate(rules[:2]):
                print(f"   {i+1}. {rule.get('condition', 'N/A')} -> {rule.get('action', 'N/A')[:80]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 验证过程中出错: {e}")
        return False

if __name__ == "__main__":
    success = test_v3_requirement_analysis()
    if success:
        print("\n🎉 V3版本测试成功！提示词优化生效。")
    else:
        print("\n💥 V3版本测试失败！需要进一步优化提示词。")