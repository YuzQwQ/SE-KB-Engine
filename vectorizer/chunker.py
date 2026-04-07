"""
知识分块器
将 JSON 结构化知识转换为可嵌入的文本块
"""

import json
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class Chunk:
    """知识块"""

    id: str  # 唯一标识
    text: str  # 向量化文本
    metadata: Dict[str, Any]  # 元数据


class KnowledgeChunker:
    """知识分块器"""

    def __init__(self):
        # 分块策略映射
        self.chunk_strategies = {
            "concepts": self._chunk_concepts,
            "examples": self._chunk_examples,
            "rules": self._chunk_rules,
            "templates": self._chunk_templates,
            "levels": self._chunk_levels,
            "theory": self._chunk_theory,
            "domain": self._chunk_domain,
            "validation": self._chunk_validation,
        }

    def chunk_file(self, file_path: Path, knowledge_type: str) -> List[Chunk]:
        """
        分块单个文件

        Args:
            file_path: JSON 文件路径
            knowledge_type: 知识类型 (concepts, examples, rules, etc.)

        Returns:
            Chunk 列表
        """
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[Chunker] 读取文件失败 {file_path}: {e}")
            return []

        # 确定分块策略
        strategy = None
        for key, func in self.chunk_strategies.items():
            if key in knowledge_type.lower():
                strategy = func
                break

        if not strategy:
            strategy = self._chunk_generic

        chunks = strategy(data, file_path)

        # 添加通用元数据
        for chunk in chunks:
            chunk.metadata["source_file"] = file_path.name
            chunk.metadata["knowledge_type"] = knowledge_type

        return chunks

    def _chunk_concepts(self, data: Dict, file_path: Path) -> List[Chunk]:
        """分块概念定义"""
        chunks = []
        file_stem = file_path.stem

        # 提取 elements 列表中的每个元素
        elements = data.get("elements", [])

        for i, elem in enumerate(elements):
            elem_id = elem.get("id", f"elem_{i}")
            name = elem.get("name", "")
            definition = elem.get("definition", "")
            naming = elem.get("naming", "")
            properties = elem.get("properties", [])
            examples = elem.get("examples", [])

            # 构造向量化文本
            text_parts = [
                f"DFD概念: {name}",
                f"定义: {definition}",
            ]

            if naming:
                text_parts.append(f"命名规范: {naming}")

            if properties:
                text_parts.append(f"特征: {'; '.join(properties)}")

            if examples:
                text_parts.append(f"示例: {', '.join(examples)}")

            text = "\n".join(text_parts)

            chunks.append(
                Chunk(
                    id=f"{file_stem}_{elem_id}",
                    text=text,
                    metadata={"element_id": elem_id, "element_name": name, "chunk_type": "element"},
                )
            )

        # 如果没有 elements，将整个文件作为一个块
        if not elements:
            chunks.append(self._create_overview_chunk(data, file_path, "concept"))

        return chunks

    def _chunk_examples(self, data: Dict, file_path: Path) -> List[Chunk]:
        """分块案例"""
        chunks = []
        file_stem = file_path.stem

        case_name = data.get("case_name", file_stem)
        description = data.get("description", "")
        requirements = data.get("requirements_text", [])
        dfd_elements = data.get("dfd_elements", {})

        # 1. 案例概述块
        overview_text = self._build_case_overview(
            case_name, description, requirements, dfd_elements
        )
        chunks.append(
            Chunk(
                id=f"{file_stem}_overview",
                text=overview_text,
                metadata={
                    "case_name": case_name,
                    "chunk_type": "case_overview",
                    "complexity": self._calculate_complexity(dfd_elements),
                },
            )
        )

        # 2. 每个处理过程的详细块
        processes = dfd_elements.get("processes", [])
        data_flows = dfd_elements.get("data_flows", [])

        for proc in processes:
            proc_id = proc.get("id", "")
            proc_name = proc.get("name", "")

            # 找到相关的数据流
            inputs = [df for df in data_flows if df.get("to") == proc_id]
            outputs = [df for df in data_flows if df.get("from") == proc_id]

            proc_text = self._build_process_text(proc_id, proc_name, inputs, outputs, case_name)

            chunks.append(
                Chunk(
                    id=f"{file_stem}_{proc_id}",
                    text=proc_text,
                    metadata={
                        "case_name": case_name,
                        "process_id": proc_id,
                        "process_name": proc_name,
                        "chunk_type": "process_detail",
                    },
                )
            )

        return chunks

    def _chunk_rules(self, data: Dict, file_path: Path) -> List[Chunk]:
        """分块规则"""
        chunks = []
        file_stem = file_path.stem

        # 尝试多种规则列表字段名
        rules_list = (
            data.get("rules", [])
            or data.get("validation_rules", [])
            or data.get("modeling_rules", [])
        )

        for i, rule in enumerate(rules_list):
            rule_id = rule.get("id", f"rule_{i}")
            name = rule.get("name", "")
            definition = rule.get("definition", rule.get("detail", ""))
            severity = rule.get("severity", rule.get("level", "info"))
            detect_logic = rule.get("detect_logic", "")

            text_parts = [
                f"DFD规则: {name}",
                f"规则ID: {rule_id}",
                f"定义: {definition}",
                f"严重级别: {severity}",
            ]

            if detect_logic:
                text_parts.append(f"检测逻辑: {detect_logic}")

            text = "\n".join(text_parts)

            chunks.append(
                Chunk(
                    id=f"{file_stem}_{rule_id}",
                    text=text,
                    metadata={
                        "rule_id": rule_id,
                        "rule_name": name,
                        "severity": severity,
                        "chunk_type": "rule",
                    },
                )
            )

        if not rules_list:
            chunks.append(self._create_overview_chunk(data, file_path, "rule"))

        return chunks

    def _chunk_templates(self, data: Dict, file_path: Path) -> List[Chunk]:
        """分块模板"""
        chunks = []
        file_stem = file_path.stem

        categories = data.get("categories", [])

        for cat in categories:
            cat_name = cat.get("name", "")
            templates = cat.get("templates", [])

            for tmpl in templates:
                tmpl_id = tmpl.get("id", "")
                tmpl_name = tmpl.get("name", "")
                dfd_level = tmpl.get("dfd_level", 0)
                pattern_type = tmpl.get("pattern_type", "")
                scenarios = tmpl.get("applicable_scenarios", [])
                notes = tmpl.get("notes", [])

                text_parts = [
                    f"DFD模板: {tmpl_name}",
                    f"分类: {cat_name}",
                    f"DFD层级: Level-{dfd_level}",
                    f"模式类型: {pattern_type}",
                ]

                if scenarios:
                    text_parts.append(f"适用场景: {'; '.join(scenarios)}")

                if notes:
                    text_parts.append(f"说明: {'; '.join(notes)}")

                text = "\n".join(text_parts)

                chunks.append(
                    Chunk(
                        id=f"{file_stem}_{tmpl_id}",
                        text=text,
                        metadata={
                            "template_id": tmpl_id,
                            "template_name": tmpl_name,
                            "category": cat_name,
                            "dfd_level": dfd_level,
                            "pattern_type": pattern_type,
                            "chunk_type": "template",
                        },
                    )
                )

        if not categories:
            chunks.append(self._create_overview_chunk(data, file_path, "template"))

        return chunks

    def _chunk_levels(self, data: Dict, file_path: Path) -> List[Chunk]:
        """分块层次分解原则"""
        chunks = []
        file_stem = file_path.stem

        principles = data.get("leveling_principles", [])
        decomp_rules = data.get("decomposition_rules", [])

        for i, p in enumerate(principles):
            p_id = p.get("id", f"p_{i}")
            desc = p.get("description", "")

            text = f"DFD分层原则: {p_id}\n描述: {desc}"

            chunks.append(
                Chunk(
                    id=f"{file_stem}_{p_id}",
                    text=text,
                    metadata={"principle_id": p_id, "chunk_type": "leveling_principle"},
                )
            )

        for i, r in enumerate(decomp_rules):
            r_id = r.get("id", f"r_{i}")
            desc = r.get("description", "")

            text = f"DFD分解规则: {r_id}\n描述: {desc}"

            chunks.append(
                Chunk(
                    id=f"{file_stem}_{r_id}",
                    text=text,
                    metadata={"rule_id": r_id, "chunk_type": "decomposition_rule"},
                )
            )

        if not principles and not decomp_rules:
            chunks.append(self._create_overview_chunk(data, file_path, "levels"))

        return chunks

    def _chunk_theory(self, data: Dict, file_path: Path) -> List[Chunk]:
        """分块理论知识"""
        chunks = []
        file_stem = file_path.stem

        concepts = data.get("concepts", [])
        principles = data.get("principles", [])

        for i, c in enumerate(concepts):
            c_id = c.get("id", f"c_{i}")
            name = c.get("name", "")
            definition = c.get("definition", "")

            text = f"软件工程概念: {name}\n定义: {definition}"

            chunks.append(
                Chunk(
                    id=f"{file_stem}_{c_id}",
                    text=text,
                    metadata={
                        "concept_id": c_id,
                        "concept_name": name,
                        "chunk_type": "theory_concept",
                    },
                )
            )

        for i, p in enumerate(principles):
            p_id = p.get("id", f"p_{i}")
            detail = p.get("detail", "")

            text = f"软件工程原则: {p_id}\n详情: {detail}"

            chunks.append(
                Chunk(
                    id=f"{file_stem}_{p_id}",
                    text=text,
                    metadata={"principle_id": p_id, "chunk_type": "theory_principle"},
                )
            )

        if not concepts and not principles:
            chunks.append(self._create_overview_chunk(data, file_path, "theory"))

        return chunks

    def _chunk_domain(self, data: Dict, file_path: Path) -> List[Chunk]:
        """分块领域知识"""
        chunks = []
        file_stem = file_path.stem

        domain_name = data.get("name", file_stem)
        description = data.get("description", "")
        terms = data.get("terms", [])

        # 领域概述
        overview_text = f"领域: {domain_name}\n描述: {description}"
        chunks.append(
            Chunk(
                id=f"{file_stem}_overview",
                text=overview_text,
                metadata={"domain_name": domain_name, "chunk_type": "domain_overview"},
            )
        )

        # 术语
        for i, term in enumerate(terms):
            term_name = term.get("term", "")
            term_def = term.get("definition", "")

            text = f"领域术语: {term_name}\n领域: {domain_name}\n定义: {term_def}"

            chunks.append(
                Chunk(
                    id=f"{file_stem}_term_{i}",
                    text=text,
                    metadata={
                        "domain_name": domain_name,
                        "term": term_name,
                        "chunk_type": "domain_term",
                    },
                )
            )

        return chunks

    def _chunk_validation(self, data: Dict, file_path: Path) -> List[Chunk]:
        """分块校验规则"""
        return self._chunk_rules(data, file_path)

    def _chunk_generic(self, data: Dict, file_path: Path) -> List[Chunk]:
        """通用分块策略"""
        return [self._create_overview_chunk(data, file_path, "generic")]

    def _create_overview_chunk(self, data: Dict, file_path: Path, chunk_type: str) -> Chunk:
        """创建概述块"""
        file_stem = file_path.stem

        # 提取关键字段
        text_parts = []
        for key in ["description", "name", "title", "content_slug", "case_name"]:
            if key in data and data[key]:
                text_parts.append(f"{key}: {data[key]}")

        if not text_parts:
            text_parts.append(f"知识文件: {file_stem}")

        return Chunk(
            id=f"{file_stem}_overview",
            text="\n".join(text_parts),
            metadata={"chunk_type": f"{chunk_type}_overview"},
        )

    def _build_case_overview(
        self, case_name: str, description: str, requirements: List[str], dfd_elements: Dict
    ) -> str:
        """构建案例概述文本"""
        text_parts = [
            f"DFD案例: {case_name}",
            f"描述: {description}",
        ]

        if requirements:
            text_parts.append(f"需求: {'; '.join(requirements[:5])}")

        # 提取元素名称
        ee = [e.get("name", "") for e in dfd_elements.get("external_entities", [])]
        p = [e.get("name", "") for e in dfd_elements.get("processes", [])]
        ds = [e.get("name", "") for e in dfd_elements.get("data_stores", [])]

        if ee:
            text_parts.append(f"外部实体: {', '.join(ee)}")
        if p:
            text_parts.append(f"处理过程: {', '.join(p)}")
        if ds:
            text_parts.append(f"数据存储: {', '.join(ds)}")

        return "\n".join(text_parts)

    def _build_process_text(
        self, proc_id: str, proc_name: str, inputs: List[Dict], outputs: List[Dict], case_name: str
    ) -> str:
        """构建处理过程文本"""
        text_parts = [
            f"处理过程: {proc_id} {proc_name}",
            f"所属案例: {case_name}",
        ]

        if inputs:
            input_strs = [f"{df.get('data', '')} (from {df.get('from', '')})" for df in inputs]
            text_parts.append(f"输入数据流: {'; '.join(input_strs)}")

        if outputs:
            output_strs = [f"{df.get('data', '')} (to {df.get('to', '')})" for df in outputs]
            text_parts.append(f"输出数据流: {'; '.join(output_strs)}")

        return "\n".join(text_parts)

    def _calculate_complexity(self, dfd_elements: Dict) -> str:
        """计算案例复杂度"""
        total = (
            len(dfd_elements.get("external_entities", []))
            + len(dfd_elements.get("processes", []))
            + len(dfd_elements.get("data_stores", []))
            + len(dfd_elements.get("data_flows", []))
        )

        if total >= 50:
            return "high"
        elif total >= 25:
            return "medium"
        else:
            return "low"
