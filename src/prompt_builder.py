from typing import Dict, List


class PromptBuilder:
    def __init__(
        self,
        table_descriptions: List[Dict[str, str]],
        formula_descriptions: Dict[str, str],
        common_expressions: List[str],
        few_shot_examples: List[Dict[str, str]],
    ):
        self.table_descriptions = table_descriptions
        self.formula_descriptions = formula_descriptions
        self.common_expressions = common_expressions
        self.few_shot_examples = few_shot_examples

    def build_system_prompt(self) -> str:
        few_shot = "\n".join(
            f"示例 {idx + 1}:\n问题: {item['question']}\nSQL: {item['sql']}\n"
            for idx, item in enumerate(self.few_shot_examples)
        )
        prompt = """
你是一个专业的SQL专家，专门处理能源供热领域的自然语言转SQL查询任务。
...existing code...
        """
        for table in self.table_descriptions:
            prompt += f"\n### {table.get('name')}\n描述: {table.get('describe')}\n字段详情:\n{table.get('detail')}\n"
        prompt += "\n## 重要计算公式：\n"
        for name, desc in self.formula_descriptions.items():
            prompt += f"\n### {name}\n{desc}\n"
        prompt += "\n## 常用业务表达：\n"
        for expr in self.common_expressions:
            prompt += f"- {expr}\n"
        prompt += f"\n参考示例:\n{few_shot}\n"
        return prompt

    def build_generation_prompt(self, question: str, analysis: str) -> str:
        return (
            "请将以下自然语言问题转换为符合要求的 SQL 查询语句，只返回 SQL，不要解释。\n"
            f"问题描述:\n{question}\n\n"
            f"问题分析（供参考）:\n{analysis}"
        )

    def build_retry_prompt(self, question: str, analysis: str, previous_sql: str, feedback: str) -> str:
        return (
            "此前的 SQL 未通过验证，请基于反馈重新生��。\n"
            f"问题:\n{question}\n\n"
            f"问题分析:\n{analysis}\n\n"
            f"上一次 SQL:\n{previous_sql}\n\n"
            f"验证反馈:\n{feedback}\n\n"
            "请直接输出改进后的 SQL。"
        )

    def build_validation_prompt(self, question: str, sql_query: str) -> str:
        prompt = f"""
你是一个SQL验证专家，需要���估生成的SQL是否正确。

## 用户问题：
{question}

## 生成的SQL：
{sql_query}
...existing code...
"""
        for table in self.table_descriptions:
            prompt += f"\n### {table.get('name')}\n描述: {table.get('describe')}\n"
        prompt += "\n## 重要计算公式：\n"
        for name, desc in self.formula_descriptions.items():
            prompt += f"\n### {name}\n{desc}\n"
        prompt += "\n## 常用业务表达：\n"
        for expr in self.common_expressions:
            prompt += f"- {expr}\n"
        return prompt

    def build_analysis_prompt(self) -> str:
        return """
你是一名能源供热业务分析师。请分析给定问题，列出：
1. 主要难点或歧义点
2. 可能涉及的数据表及关键字段
3. 需要用到的公式/量化方法
4. 编写SQL时需要特别注意的事项
请尽量结构化输出，供后续SQL生成模型参考。
"""

