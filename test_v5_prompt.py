#!/usr/bin/env python3
"""
测试V5版本的requirement_analysis提示词效果（分段提取策略）
专门针对generation_knowledge部分
"""

import json
import sys
import os
import shutil

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server import extract_universal_knowledge

def test_v5_requirement_analysis():
    """测试V5版本的需求分析提示词（分段提取策略）"""
    
    print("=== 测试V5版本的requirement_analysis提示词（分段提取策略） ===")
    
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
    backup_config_path = 'config/system_prompts_backup_v5.json'
    new_config_path = 'config/system_prompts_v5.json'
    
    try:
        # 备份原配置
        shutil.copy(original_config_path, backup_config_path)
        
        # 使用V5配置
        shutil.copy(new_config_path, original_config_path)
        
        print("\n调用extract_universal_knowledge工具（使用V5分段提取提示词）...")
        result = extract_universal_knowledge(
            content=content,
            url=metadata.get('url', ''),
            title=metadata.get('title', ''),
            requirement_type="需求分析",
            target_conversion_type="通用知识库"
        )
        
        # 保存结果到文件
        output_file = 'v5_requirement_analysis_result.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"结果已保存到: {output_file}")
        
        # 解析JSON结果进行验证
        try:
            result_data = json.loads(result)
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            return False
        
        print("\n=== V5版本结构验证和generation_knowledge检查 ===\n")
        return validate_v5_result_structure(result_data)
        
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

def validate_v5_result_structure(result_data):
    """验证V5版本结果结构，重点检查generation_knowledge"""
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
        
        print(f"📊 V5版本（分段提取）统计:")
        print(f"  🧠 Generation Knowledge:")
        print(f"    - Concepts: {len(concepts)} 条")
        print(f"    - Rules: {len(rules)} 条")
        print(f"    - Patterns: {len(patterns)} 条")
        print(f"    - Transformations: {len(transformations)} 条")
        
        # 检查最小输出量要求
        requirements = {
            'concepts': {'actual': len(concepts), 'required': 3},
            'rules': {'actual': len(rules), 'required': 3},
            'patterns': {'actual': len(patterns), 'required': 3},
            'transformations': {'actual': len(transformations), 'required': 3}
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
            for i, concept in enumerate(concepts[:3]):
                name = concept.get('name', 'N/A')
                definition = concept.get('definition', 'N/A')[:100]
                category = concept.get('category', 'N/A')
                importance = concept.get('importance', 'N/A')
                print(f"   {i+1}. {name} ({category}, 重要度:{importance})")
                print(f"      定义: {definition}...")
        
        if rules:
            print(f"\n📋 Rules示例:")
            for i, rule in enumerate(rules[:3]):
                condition = rule.get('condition', 'N/A')
                action = rule.get('action', 'N/A')[:80]
                priority = rule.get('priority', 'N/A')
                print(f"   {i+1}. 当{condition}时 -> {action}... (优先级:{priority})")
        
        if patterns:
            print(f"\n🔄 Patterns示例:")
            for i, pattern in enumerate(patterns[:3]):
                name = pattern.get('name', 'N/A')
                structure = pattern.get('structure', 'N/A')[:80]
                usage = pattern.get('usage', 'N/A')[:60]
                print(f"   {i+1}. {name}: {structure}...")
                print(f"      用途: {usage}...")
        
        if transformations:
            print(f"\n🔄 Transformations示例:")
            for i, transformation in enumerate(transformations[:3]):
                input_format = transformation.get('input_format', 'N/A')
                output_format = transformation.get('output_format', 'N/A')
                steps = transformation.get('transformation_steps', [])
                print(f"   {i+1}. {input_format} -> {output_format}")
                print(f"      步骤: {', '.join(steps[:3])}...")
        
        # 判断整体成功
        if not failed_fields:
            print(f"\n🎉 V5版本（分段提取）：所有generation_knowledge字段都满足要求！")
            return True
        else:
            print(f"\n💥 V5版本仍有{len(failed_fields)}个字段未达标")
            return False
        
    except Exception as e:
        print(f"❌ 验证过程中出错: {e}")
        return False

if __name__ == "__main__":
    success = test_v5_requirement_analysis()
    if success:
        print("\n🎉 V5版本（分段提取策略）测试成功！")
    else:
        print("\n💥 V5版本测试失败，需要进一步优化。")