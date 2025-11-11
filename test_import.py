#!/usr/bin/env python3
"""
测试函数导入
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from server import extract_knowledge_with_ai
    print("✅ 成功导入 extract_knowledge_with_ai 函数")
    
    # 测试函数是否可调用
    if callable(extract_knowledge_with_ai):
        print("✅ 函数可调用")
    else:
        print("❌ 函数不可调用")
        
except ImportError as e:
    print(f"❌ 导入失败: {e}")
except Exception as e:
    print(f"❌ 其他错误: {e}")
    import traceback
    print(f"详细错误: {traceback.format_exc()}")