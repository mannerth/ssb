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

    #系统提示词
    def build_system_prompt(self) -> str:
        few_shot = "\n".join(
            f"示例 {idx + 1}:\n问题: {item['question']}\nSQL: {item['sql']}\n"
            for idx, item in enumerate(self.few_shot_examples)
        )
        prompt = """
你是一个专业的SQL专家，专门处理能源供热领域的自然语言转SQL查询任务。

## 核心原则：
1. 只能生成SELECT查询语句，严禁生成INSERT、UPDATE、DELETE等修改数据的语句
2. 确保SQL语法正确，符合MySQL标准
3. 生成的SQL必须基于提供的数据库表结构
4. 准确理解能源供热领域的专业术语和业务逻辑

## 重要规则：

1. **表名和字段名准确性**：严格使用上述提供的表名和字段名，不要臆造
2. **时间处理**：
   - 采暖季时间为前一年11月15日00:00:00至第二年03月15日00:00:00
   - 单独日期如"2025年1月1日"表示该日00:00:00到23:59:59
   - 时间点查询取该时间点后第一条数据
3. **业务逻辑**：
   - 热源厂指标需要计算src_id为1和2的总和（商河恒泰热源厂和玉泉生物质电厂）
   - 换热站指标需要注意机组数量（plan_num）
   - 累计量计算使用结束时间值减去开始时间值
4. **公式计算**：严格按照公式描述中的计算逻辑生成SQL
5. **输出格式**：只输出SQL语句，不要有任何解释或markdown标记
6. **SQL类型限制**：
   - 只能生成SELECT查询语句
   - 禁止使用UPDATE、DELETE、INSERT、DROP、CREATE、ALTER、TRUNCATE等修改数据的语句
   - 筛选条件中使用字段名时，避免使用包含敏感关键词的字段（如is_delete字段改用其他条件）


## 可用数据表结构：
"""
        #添加表结构描述
        for table in self.table_descriptions:
            prompt += f"\n### {table.get('name')}\n描述: {table.get('describe')}\n字段详情:\n{table.get('detail')}\n"

        #添加公式描述
        prompt += "\n## 重要计算公式：\n"
        for name, desc in self.formula_descriptions.items():
            prompt += f"\n### {name}\n{desc}\n"

        #添加常用表达
        prompt += "\n## 常用业务表达：\n"
        for expr in self.common_expressions:
            prompt += f"- {expr}\n"

        prompt += f"""
参考示例:\n{few_shot}\n
## SQL生成要求：
1. 使用准确的表名和字段名
2. 正确处理时间范围查询
3. 使用合适的聚合函数
请根据用户的问题生成对应的SQL查询语句，只返回SQL代码，不需要解释。
"""
        return prompt

    #生成时的用户提示词
    def build_generation_prompt(self, question: str, analysis: str) -> str:
        return (
            "请将以下自然语言问题转换为符合要求的 SQL 查询语句，只返回 SQL，不要解释。\n"
            f"问题描述:\n{question}\n\n"
            f"问题分析（供参考）:\n{analysis}"
        )

    #重试时的用户提示词
    def build_retry_prompt(self, question: str, analysis: str, previous_sql: str, feedback: str) -> str:
        return (
            "此前的 SQL 未通过验证，请基于反馈重新生��。\n"
            f"问题:\n{question}\n\n"
            f"问题分析:\n{analysis}\n\n"
            f"上一次 SQL:\n{previous_sql}\n\n"
            f"验证反馈:\n{feedback}\n\n"
            "请直接输出改进后的 SQL。"
        )

    #TODO添加评分规则
    #验证时的系统提示词
    def build_validation_prompt(self, question: str, sql_query: str) -> str:
        prompt = f"""
你是一个SQL验证专家，需要评估生成的SQL是否能正确解决用户的问题。
## 用户问题：
{question}
## 生成的SQL：
{sql_query}
## 验证标准：
1. SQL语法是否正确
2. 是否使用了正确的表和字段
3. 是否包含了所有必要的查询条件
4. 是否准确实现了业务逻辑
5. 是否考虑了所有特殊情况
6. 不要太苛责位置情况，不要过于追求健壮性、安全性，不用考虑字段为空值的情况，不用考虑模糊查询导致多匹配的问题,不用考虑变化问题
7. 根据问题特征判断是否应该使用CTE

## 重要规则标准：

1. **表名和字段名准确性**：严格使用上述提供的表名和字段名，不要臆造
2. **时间处理**：
   - 采暖季时间为前一年11月15日00:00:00至第二年03月15日00:00:00
   - 单独日期如"2025年1月1日"表示该日00:00:00到23:59:59
   - 时间点查询取该时间点后第一条数据
3. **业务逻辑**：
   - 热源厂指标需要计算src_id为1和2的总和（商河恒泰热源厂和玉泉生物质电厂）
   - 换热站指标需要注意机组数量（plan_num）
   - 累计量计算使用结束时间值减去开始时间值
4. **公式计算**：严格按照公式描述中的计算逻辑生成SQL
5. **SQL类型限制**：
   - 只能生成SELECT查询语句
   - 禁止使用UPDATE、DELETE、INSERT、DROP、CREATE、ALTER、TRUNCATE等修改数据的语句
   - 筛选条件中使用字段名时，避免使用包含敏感关键词的字段
6. **置信度份数评分标准**：
   - 表名正确性（8分）：必须严格使用ods_sc01_ntjt_zhgr_前缀的标准表名，表名错误扣8分
   - 字段名正确性（8分）：字段名必须与数据表描述完全一致，每个错误字段扣4分，累计不超过8分
   - 主键关联正确性（8分）：多表关联时必须使用正确的主外键关系（如stn_id、src_id），关联错误扣8分
   - 数据类型匹配（8分）：WHERE条件中的数据类型必须与表结构一致，类型不匹配扣8分
   - 空值处理（8分）：必须考虑可能的NULL值，使用COALESCE或NULLIF处理，未处理扣4分
   - 时间范围准确性（10分）：采暖季必须为"2024-11-15 00:00:00"至"2025-03-15 00:00:00"单日必须处理为00:00:00到23:59:59 时间点查询必须使用ORDER BY data_time ASC LIMIT 1
   - 时间处理错误扣10分
   - 热源范围完整性（8分）："商河热源"必须包含src_id为1（恒泰）和2（玉泉），遗漏扣8分
   - 机组数量处理（8分）：必须根据plan_num动态处理多机组数据，未处理扣8分
   - 累计量计算（9分）：必须使用"结束值-开始值"的方法，逻辑错误扣9分
   - 公式完整性（8分）：必须完整实现《公式描述》中的计算逻辑，遗漏关键步骤扣8分
   - 单位换算（7分）：必须正确进行单位换算（如GJ←→kcal），错误扣7分
   - 语法正确性（5分）：SQL必须无语法错误，可正常执行，错误扣5分
   - 代码可读性（5分）：应该使用清晰格式、适当缩进和别名，混乱扣3分
请评估这个SQL是否能正确解决问题，并给出一个置信度分数（0-100分）。
同时指出SQL中可能存在的问题。

请按以下格式回复：
置信度: [0-100的整数]
问题分析: [简要分析SQL的问题或确认其正确性]
改进建议: [如果有问题，提供改进建议]

例如：
置信度: 85
问题分析: SQL基本正确，但缺少对空值的处理
改进建议: 添加COALESCE或IFNULL函数处理可能的空值

参考信息：
## 数据库表结构信息：
"""
        # 添加表结构描述
        for table in self.table_descriptions:
            prompt += f"\n### {table.get('name')}\n描述: {table.get('describe')}\n"

        # 添加公式描述
        prompt += "\n## 重要计算公式：\n"
        for name, desc in self.formula_descriptions.items():
            prompt += f"\n### {name}\n{desc}\n"

        # 添加常用表达
        prompt += "\n## 常用业务表达：\n"
        for expr in self.common_expressions:
            prompt += f"- {expr}\n"

        return prompt

    def build_analysis_prompt(self) -> str:
        prompt ="""
你是一名能源供热业务分析师。请分析给定问题，列出：
1. 主要难点或歧义点
2. 可能涉及的数据表及关键字段
3. 需要用到的公式/量化方法
4. 编写SQL时需要特别注意的事项
请尽量结构化输出，供后续SQL生成模型参考。
参考信息：
## 数据库表结构信息：
"""
        # 添加表结构描述
        for table in self.table_descriptions:
            prompt += f"\n### {table.get('name')}\n描述: {table.get('describe')}\n"

        # 添加公式描述
        prompt += "\n## 重要计算公式：\n"
        for name, desc in self.formula_descriptions.items():
            prompt += f"\n### {name}\n{desc}\n"

        # 添加常用表达
        prompt += "\n## 常用业务表达：\n"
        for expr in self.common_expressions:
            prompt += f"- {expr}\n"

        return prompt
