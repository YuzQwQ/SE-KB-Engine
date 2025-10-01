# 爬虫功能集成说明

## 概述

本文档介绍了已集成到MCP服务器中的网页爬虫工具功能。当代理出现问题时，主模型可以直接使用这些工具进行网页内容抓取。

## 新增的MCP工具

### `crawl_webpage_direct`

**功能描述**: 直接爬取网页内容，不使用代理，适用于解决代理连接超时问题。

**参数**:
- `url` (string): 要爬取的网页URL
- `save_content` (boolean, 可选): 是否保存爬取的内容到文件，默认为True

**返回格式**: JSON字符串，包含以下字段：

#### 成功响应
```json
{
  "status": "success",
  "title": "网页标题",
  "author": "作者信息",
  "publish_time": "发布时间",
  "word_count": 字数,
  "tags": ["标签1", "标签2"],
  "content_preview": "内容预览...",
  "full_content_length": 内容长度,
  "raw_data_size": 原始数据大小,
  "crawl_time": "爬取时间戳",
  "files_saved": {
    "raw_data": "原始数据文件路径",
    "parsed_data": "解析数据文件路径"
  }
}
```

#### 错误响应
```json
{
  "status": "error",
  "error": "错误信息",
  "suggestions": [
    "检查网络连接是否正常",
    "确认URL是否可访问",
    "检查网站是否有反爬虫机制",
    "尝试稍后重试"
  ]
}
```

## 支持的网站类型

1. **CSDN博客**: 特别优化了CSDN文章的解析，能够提取标题、作者、发布时间、标签等信息
2. **通用网页**: 支持大多数标准HTML网页的内容提取
3. **简单静态页面**: 如example.com、httpbin.org等测试网站

## 使用示例

### Python异步调用
```python
import asyncio
import json
from server import crawl_webpage_direct

async def example_usage():
    # 爬取网页内容
    result = await crawl_webpage_direct(
        url="https://example.com",
        save_content=True
    )
    
    # 解析结果
    data = json.loads(result)
    
    if data['status'] == 'success':
        print(f"标题: {data['title']}")
        print(f"内容长度: {data['full_content_length']}")
    else:
        print(f"爬取失败: {data['error']}")

# 运行示例
asyncio.run(example_usage())
```

## 文件存储

爬取的内容会自动保存到以下目录结构：

```
data/
├── raw/          # 原始HTML数据
│   └── [网站]_[标题]_[时间戳].json
└── parsed/       # 解析后的结构化数据
    └── [网站]_[标题]_parsed_[时间戳].json
```

## 错误处理

工具内置了完善的错误处理机制：

1. **网络连接错误**: 自动重试机制
2. **HTTP错误**: 返回具体的状态码和错误信息
3. **解析错误**: 提供详细的错误描述和建议
4. **文件保存错误**: 优雅降级，不影响内容返回

## 性能特点

- **无代理模式**: 避免代理连接超时问题
- **异步处理**: 支持高并发爬取
- **内存优化**: 大文件分块处理
- **缓存机制**: 避免重复爬取相同内容

## 注意事项

1. **遵守robots.txt**: 请确保遵守目标网站的爬虫协议
2. **请求频率**: 避免过于频繁的请求，以免被网站封禁
3. **法律合规**: 仅用于合法的数据获取目的
4. **网站变化**: 某些网站可能会更新反爬虫机制，需要相应调整

## 测试验证

可以运行 `test_mcp_crawler.py` 脚本来验证工具功能：

```bash
python test_mcp_crawler.py
```

测试包括：
- 简单网页爬取测试
- 复杂网站内容提取测试
- 错误处理机制验证

## 技术实现

- **基础爬虫**: 使用 `utils/webpage_crawler.py` 中的 `WebpageCrawler` 类
- **MCP集成**: 通过 `@mcp.tool()` 装饰器注册为MCP工具
- **异步支持**: 完全异步实现，支持并发调用
- **数据格式**: 统一的JSON响应格式，便于主模型处理

---

*最后更新: 2025年10月1日*