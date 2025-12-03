# SE-KB 目录说明

此目录为“软件工程知识库”（Software Engineering Knowledge Base, SE-KB）的标准骨架，用于支持自动化软件工程建模与产物存档。

包含的子目录：
- theory：核心建模理论与原则（不可变基础）
- schema：各图类型的 JSON Schema 定义
- mappings：自然语言→建模元素的映射规则
- domain：行业知识库（角色、术语、常见流等）
- examples：完整案例（需求→多图→数据字典 等）
- artifacts：Agent 生成成果的版本化存档
- meta：知识库自身的清单、溯源与更新策略

使用建议：
- 先加载 `theory` 与 `schema` 再应用 `mappings`
- 参考 `examples` 保持命名与分层一致性
- 所有生成产物统一写入 `artifacts/` 按时间分目录