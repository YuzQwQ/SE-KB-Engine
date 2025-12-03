# 📘 DFD — Data Flow Diagram 专属知识库

此文件夹包含所有与数据流图（DFD）相关的专业知识，包括：

### 1. concepts/
DFD 元素的概念定义、语义、示例，例如：
- External Entity
- Process
- Data Store
- Data Flow
- 分层结构（Level-0, Level-1, Level-n）

### 2. rules/
DFD 特有建模规则，例如：
- dfd_principles.json（理论/基础规则）
- dfd_modeling_rules.json（建模操作指南）

### 3. validation/
用于自动检查 DFD 合法性的规则，例如：
- 平衡原则
- 数据方向合理性
- 过程输入/输出一致性

### 4. levels/
定义 DFD 层级结构模板，例如：
- Level-0 结构
- Level-1 分解结构

### 5. templates/
可复用的模板：元素结构、层级结构、数据字典模板等。

### 6. examples/
真实案例：需求文本 → 多级 DFD → 数据字典

## 用途
- 为 Agent 生成 DFD 提供完整知识体系  
- 为验证器提供规范化的 reference model  
- 为教学/研究提供参考模型  
