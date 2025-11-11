#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
演示HTML标题结构保留功能
使用模拟的CSDN文章HTML内容进行测试
"""

import json
from utils.html_cleaner import clean_html_with_structure, is_html_content, html_cleaner

def create_demo_html():
    """创建模拟的CSDN文章HTML内容"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>软件开发需求分析模板：完整指南与实践案例</title>
        <meta charset="utf-8">
    </head>
    <body>
        <div class="article-header">
            <h1>软件开发需求分析模板：完整指南与实践案例</h1>
            <div class="author">作者：普通网友</div>
            <div class="publish-time">发布时间：2025-08-18 12:23:33</div>
        </div>
        
        <div class="article-content">
            <p>本文还有配套的精品资源，点击获取。简介：需求分析是软件开发的起始点，定义项目范围和目标。</p>
            
            <h2>1. 软件开发项目需求分析概论</h2>
            <p>在软件开发的世界里，需求分析扮演着至关重要的角色。它是项目成功与否的关键因素，因为它确定了项目的基础和目标。</p>
            
            <h3>1.1 需求分析的定义</h3>
            <p>需求分析可以定义为一个过程，用来确认用户或利益相关者对软件产品的需求，并对这些需求进行详细记录。</p>
            
            <h3>1.2 需求分析的重要性</h3>
            <p>要理解需求分析的重要性，我们需要认识到它在以下几个方面的作用：</p>
            <ul>
                <li><strong>明确目标</strong>：帮助团队理解项目的真正目标</li>
                <li><strong>降低风险</strong>：提前识别潜在的问题和挑战</li>
                <li><strong>控制成本</strong>：避免后期的重大修改和返工</li>
            </ul>
            
            <h2>2. 需求分析的基本流程</h2>
            <p>需求分析通常包括以下几个关键步骤：</p>
            
            <h3>2.1 需求收集</h3>
            <p>需求收集是需求分析的第一步，主要通过以下方式进行：</p>
            <ul>
                <li>用户访谈</li>
                <li>问卷调查</li>
                <li>现场观察</li>
                <li>文档分析</li>
            </ul>
            
            <h3>2.2 需求分析与建模</h3>
            <p>收集到需求后，需要对其进行分析和建模：</p>
            
            <h4>2.2.1 功能需求分析</h4>
            <p>功能需求描述系统应该做什么，包括：</p>
            <ul>
                <li>用户管理功能</li>
                <li>数据处理功能</li>
                <li>报表生成功能</li>
            </ul>
            
            <h4>2.2.2 非功能需求分析</h4>
            <p>非功能需求描述系统应该如何工作，包括：</p>
            <ul>
                <li>性能要求</li>
                <li>安全要求</li>
                <li>可用性要求</li>
            </ul>
            
            <h3>2.3 需求验证</h3>
            <p>需求验证确保收集到的需求是正确、完整和一致的。</p>
            
            <h2>3. 需求文档编写</h2>
            <p>需求文档是需求分析的重要输出物，应该包含以下内容：</p>
            
            <h3>3.1 项目概述</h3>
            <p>项目背景、目标和范围的描述。</p>
            
            <h3>3.2 功能需求</h3>
            <p>详细描述系统的功能要求。</p>
            
            <h3>3.3 非功能需求</h3>
            <p>系统的质量属性和约束条件。</p>
            
            <h2>4. 需求管理</h2>
            <p>需求管理是一个持续的过程，包括需求的跟踪、变更控制和版本管理。</p>
            
            <h3>4.1 需求跟踪</h3>
            <p>建立需求与设计、实现、测试之间的可追溯性。</p>
            
            <h3>4.2 变更管理</h3>
            <p>建立需求变更的流程和控制机制。</p>
            
            <h2>5. 最佳实践与案例</h2>
            <p>基于实际项目经验总结的最佳实践。</p>
            
            <h3>5.1 敏捷开发中的需求分析</h3>
            <p>在敏捷开发环境下如何进行有效的需求分析。</p>
            
            <h3>5.2 大型项目的需求管理</h3>
            <p>大型复杂项目中的需求管理策略和方法。</p>
            
            <div class="conclusion">
                <h2>总结</h2>
                <p>需求分析是软件开发成功的关键，需要系统化的方法和持续的管理。通过遵循标准的流程和最佳实践，可以显著提高项目的成功率。</p>
            </div>
        </div>
        
        <div class="article-footer">
            <p>本文为原创内容，转载请注明出处。</p>
        </div>
    </body>
    </html>
    """

def test_html_structure_demo():
    """测试HTML标题结构功能的完整演示"""
    print("=== HTML标题结构保留功能演示 ===\n")
    
    # 1. 创建演示HTML内容
    html_content = create_demo_html()
    print(f"1. 创建演示HTML内容:")
    print(f"   HTML内容长度: {len(html_content)} 字符")
    
    # 2. 检测HTML内容
    print(f"\n2. HTML内容检测:")
    is_html = is_html_content(html_content)
    print(f"   是否为HTML内容: {'是' if is_html else '否'}")
    
    if not is_html:
        print("   ❌ HTML检测失败")
        return
    
    # 3. 进行结构化清理
    print(f"\n3. 结构化清理:")
    cleaning_result = clean_html_with_structure(html_content)
    
    print(f"   原始HTML长度: {len(html_content)} 字符")
    print(f"   清理后长度: {len(cleaning_result['cleaned_content'])} 字符")
    print(f"   提取标题数量: {len(cleaning_result['title_structure'])}")
    
    # 4. 显示提取的标题结构
    print(f"\n4. 提取的标题结构:")
    if cleaning_result['title_structure']:
        for i, title in enumerate(cleaning_result['title_structure'], 1):
            indent = "  " * (title['level'] - 1)
            print(f"   {i:2d}. {indent}[H{title['level']}] {title['text']}")
    else:
        print("   ❌ 未提取到标题结构")
        return
    
    # 5. 生成标题上下文
    print(f"\n5. 标题上下文生成:")
    title_context = html_cleaner.format_title_structure_as_context(
        cleaning_result['title_structure']
    )
    print(f"   上下文长度: {len(title_context)} 字符")
    print(f"   上下文内容:")
    print(title_context)
    
    # 6. 显示清理后的内容片段
    print(f"\n6. 清理后内容预览 (前500字符):")
    cleaned_preview = cleaning_result['cleaned_content'][:500]
    print(cleaned_preview)
    if len(cleaning_result['cleaned_content']) > 500:
        print("...")
    
    # 7. 模拟AI知识提取输入
    print(f"\n7. AI知识提取输入准备:")
    ai_input = f"{title_context}\n\n{cleaning_result['cleaned_content'][:1000]}"
    print(f"   AI输入总长度: {len(ai_input)} 字符")
    print(f"   包含标题上下文: 是")
    print(f"   标题上下文占比: {len(title_context)/len(ai_input)*100:.1f}%")
    
    # 8. 保存结果
    result_data = {
        'demo_info': {
            'original_html_length': len(html_content),
            'cleaned_content_length': len(cleaning_result['cleaned_content']),
            'title_count': len(cleaning_result['title_structure']),
            'title_context_length': len(title_context),
            'ai_input_length': len(ai_input)
        },
        'title_structure': cleaning_result['title_structure'],
        'title_context': title_context,
        'cleaned_content_preview': cleaning_result['cleaned_content'][:1000],
        'ai_input_preview': ai_input[:1000]
    }
    
    with open('html_structure_demo_result.json', 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 演示结果已保存到 html_structure_demo_result.json")
    
    # 9. 总结
    print(f"\n{'='*60}")
    print("=== 功能演示总结 ===")
    print(f"✅ HTML内容检测: 通过")
    print(f"✅ 标题结构提取: {len(cleaning_result['title_structure'])} 个标题")
    print(f"✅ 内容清理: {len(html_content)} → {len(cleaning_result['cleaned_content'])} 字符")
    print(f"✅ 上下文生成: {len(title_context)} 字符")
    print(f"✅ AI输入准备: {len(ai_input)} 字符")
    
    # 分析标题层级分布
    level_count = {}
    for title in cleaning_result['title_structure']:
        level = title['level']
        level_count[level] = level_count.get(level, 0) + 1
    
    print(f"\n📊 标题层级分布:")
    for level in sorted(level_count.keys()):
        print(f"   H{level}: {level_count[level]} 个")
    
    print(f"\n🎉 HTML标题结构保留功能演示完成！")
    print(f"   该功能可以有效提取文档结构，为AI提供更好的上下文信息。")
    
    return result_data

def main():
    """主函数"""
    try:
        result = test_html_structure_demo()
        
        if result:
            print(f"\n🔍 详细信息:")
            print(f"   - 原始HTML: {result['demo_info']['original_html_length']} 字符")
            print(f"   - 清理后内容: {result['demo_info']['cleaned_content_length']} 字符")
            print(f"   - 标题数量: {result['demo_info']['title_count']} 个")
            print(f"   - 上下文长度: {result['demo_info']['title_context_length']} 字符")
            print(f"   - AI输入长度: {result['demo_info']['ai_input_length']} 字符")
            
    except Exception as e:
        print(f"❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()