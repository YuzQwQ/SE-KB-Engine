# 📘 mappings/ — 自然语言 → 建模元素 映射规则

此目录存放从**非结构化文本**中抽取图元素所需的「语言映射规则」。

例如：
- 输入：“用户提交订单” → Process: Submit Order
- 输入：“订单数据被保存” → Data Store: OrderFile（write）

## 包含内容

- **dfd_mappings.json**  
  需求文本 → DFD 四要素的映射规则、关键词、句型模式。

- **uml_mappings.json**  
  文本 → 类/关系/属性 的模式。

- **domain_role_maps.json**  
  领域通用角色映射（如 User, Admin, Customer）。

## 用途
- Crawler + NLP 模块解析网页 / 文本  
- Agent 自动建模  
- 文本分析 → 图生成  
