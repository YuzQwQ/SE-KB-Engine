# 📘 schema/ — 各类图的 JSON Schema 定义

用于约束智能体输出的 JSON 结构是否合法。

每个 Schema 对应 diagrams 中的一个图类型。

## 包含内容

- **dfd.schema.json**  
  DFD 完整 JSON 输出的 Schema，包括：elements、flows、levels、metadata 等。

- **class.schema.json**  
  UML 类图的 JSON Schema。

- **sequence.schema.json**  
  UML 时序图的 JSON Schema。

## 用途
- Agent 生成图时的结构校验  
- CI 校验知识库文件合法性  
- UI/渲染器根据 Schema 构建视图  
