搜索引擎解析配置

将原有 `configs/parsers` 下的各引擎配置迁移至此，统一在 `config/parsers` 维护：

- `google.json`
- `bing.json`
- `baidu.json`
- `duckduckgo.json`

代码默认从 `config/parsers` 加载解析配置。