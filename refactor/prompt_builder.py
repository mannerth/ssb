import json
import os

from refactor import config


class PromptBuilder:

    def __init__(self):
        # 从文件加载领域知识
        self.config_dir = config.data_files_path
        self.formula_descriptions = self.load_formula_descriptions()
        self.common_expressions = self.load_common_expressions()
        self.table_descriptions = self.load_table_descriptions()
        self.load_few_shot_examples(config.training_file_path)

    def load_formula_descriptions(self):
        """从文件加载公式描述"""
        try:
            file_path = os.path.join(self.config_dir, "formula_descriptions.json")
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"公式描述文件未找到: {file_path}")
            return {}
        except Exception as e:
            self.logger.error(f"加载公式描述失败: {e}")
            return {}

    def load_common_expressions(self):
        """从文件加载常用表达"""
        try:
            file_path = os.path.join(self.config_dir, "common_expressions.json")
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"常用表达文件未找到: {file_path}")
            return []
        except Exception as e:
            self.logger.error(f"加载常用表达失败: {e}")
            return []

    def load_table_descriptions(self):
        """从文件加载数据表描述"""
        try:
            file_path = os.path.join(self.config_dir, "table_descriptions.json")
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"数据表描述文件未找到: {file_path}")
            return []
        except Exception as e:
            self.logger.error(f"加载数据表描述失败: {e}")
            return []


    def build_system_prompt(self):
        """构建系统提示词"""

        few_shot_text = "\n".join(
            [f"示例 {i}:\n问题: {ex['question']}\nSQL: {ex['sql']}\n"
             for i, ex in enumerate(self.few_shot_examples, 1)]
        )

        system_prompt = """
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

        # 添加表结构描述
        for table in self.table_descriptions:
            system_prompt += f"\n### {table['name']}\n"
            system_prompt += f"描述: {table['describe']}\n"
            system_prompt += f"字段详情:\n{table['detail']}\n"

        # 添加公式描述
        system_prompt += "\n## 重要计算公式：\n"
        for formula_name, formula_desc in self.formula_descriptions.items():
            system_prompt += f"\n### {formula_name}\n{formula_desc}\n"

        # 添加常用表达
        system_prompt += "\n## 常用业务表达：\n"
        for expr in self.common_expressions:
            system_prompt += f"- {expr}\n"

        system_prompt += f"""
## SQL生成要求：
1. 使用准确的表名和字段名
2. 正确处理时间范围查询
3. 使用合适的聚合函数


参考示例:
{few_shot_text}

请根据用户的问题生成对应的SQL查询语句，只返回SQL代码，不需要解释。
"""
        return system_prompt
