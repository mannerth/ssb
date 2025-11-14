import openai
import json
import time
import os
import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
import logging

training_file_path = "算法训练集（75道问题及sql语句）.xlsx"

class DeepSeekTextToSQL:
    def __init__(self, api_key, config_dir="config", base_url="https://api.deepseek.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.config_dir = config_dir


        # 配置OpenAI客户端
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url
        )

        # 从文件加载领域知识
        self.formula_descriptions = self.load_formula_descriptions()
        self.common_expressions = self.load_common_expressions()
        self.table_descriptions = self.load_table_descriptions()
        self.load_few_shot_examples( training_file_path )

        # 设置日志
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

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
3. 注意NULL值处理
4. 使用合适的聚合函数
5. 确保查询性能优化

参考示例:
{few_shot_text}

请根据用户的问题生成对应的SQL查询语句，只返回SQL代码，不需要解释。
"""
        return system_prompt

    def call_deepseek_api(self, question, max_retries=3):
        """使用OpenAI库调用DeepSeek API"""
        messages = [
            {"role": "system", "content": self.build_system_prompt()},
            {"role": "user", "content": f"请将以下自然语言问题转换为SQL查询语句：\n\n{question}"}
        ]

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages,
                    temperature=0.1,  # 低温度确保稳定性
                    max_tokens=2000
                )

                sql_query = response.choices[0].message.content.strip()

                # 清理SQL语句，确保只包含SELECT查询
                sql_query = self.validate_and_clean_sql(sql_query)

                return sql_query

            except Exception as e:
                self.logger.error(f"API调用异常: {e}, 尝试第 {attempt + 1} 次")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    raise Exception(f"DeepSeek API调用失败，已重试{max_retries}次: {str(e)}")

    def validate_and_clean_sql(self, sql_query):
        """验证和清理SQL语句，确保只包含SELECT查询"""
        # 移除Markdown代码块标记
        sql_query = sql_query.replace('```sql', '').replace('```', '').strip()

        # 检查是否包含危险的SQL操作
        dangerous_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE', 'TRUNCATE']
        sql_upper = sql_query.upper()

        for keyword in dangerous_keywords:
            if keyword in sql_upper and f'SELECT' not in sql_upper:
                raise ValueError(f"生成的SQL包含危险操作: {keyword}，只允许SELECT查询")

        # 确保以SELECT开头
        if not sql_upper.startswith('SELECT'):
            # 尝试找到SELECT语句的开始
            select_index = sql_upper.find('SELECT')
            if select_index != -1:
                sql_query = sql_query[select_index:]
            else:
                raise ValueError("生成的SQL不包含SELECT语句")

        return sql_query

    def process_excel_file(self, file_path, start_row, start_col, output_col, num_questions, sheet_name=None):
        """
        处理Excel文件

        参数:
        - file_path: Excel文件路径
        - start_row: 问题开始的行号（从1开始）
        - start_col: 问题所在的列号（从1开始）
        - output_col: 输出SQL的列号（从1开始）
        - num_questions: 要处理的问题数量
        - sheet_name: 工作表名称，默认为第一个工作表
        """
        try:
            # 读取Excel文件
            workbook = load_workbook(file_path)
            if sheet_name:
                worksheet = workbook[sheet_name]
            else:
                worksheet = workbook.active

            self.logger.info(f"开始处理Excel文件: {file_path}")
            self.logger.info(f"从第{start_row}行第{get_column_letter(start_col)}列开始，处理{num_questions}个问题")

            processed_count = 0
            errors = []

            for i in range(num_questions):
                current_row = start_row + i

                # 读取问题
                question_cell = worksheet.cell(row=current_row, column=start_col)
                question = str(question_cell.value).strip() if question_cell.value else ""

                if not question or question.lower() in ['', 'none', 'null']:
                    self.logger.warning(f"第{current_row}行问题为空，跳过")
                    continue

                self.logger.info(f"处理第{current_row}行问题: {question}")

                try:
                    # 调用API生成SQL
                    sql_query = self.call_deepseek_api(question)

                    # 写入SQL到指定列
                    output_cell = worksheet.cell(row=current_row, column=output_col)
                    output_cell.value = sql_query

                    self.logger.info(f"第{current_row}行SQL生成成功")
                    print(sql_query)
                    processed_count += 1

                    # 添加延迟避免API限制
                    # time.sleep(1)

                except Exception as e:
                    error_msg = f"第{current_row}行处理失败: {str(e)}"
                    self.logger.error(error_msg)
                    errors.append(error_msg)

                    # 写入错误信息
                    output_cell = worksheet.cell(row=current_row, column=output_col)
                    output_cell.value = f"ERROR: {str(e)}"

            # 保存文件
            output_file = file_path.replace('.xlsx', '_with_sql.xlsx')
            workbook.save(output_file)

            self.logger.info(f"处理完成！成功处理 {processed_count}/{num_questions} 个问题")
            self.logger.info(f"结果已保存到: {output_file}")

            if errors:
                self.logger.warning("处理过程中出现以下错误:")
                for error in errors:
                    self.logger.warning(f"  - {error}")

            return {
                'processed_count': processed_count,
                'total_questions': num_questions,
                'output_file': output_file,
                'errors': errors
            }

        except Exception as e:
            self.logger.error(f"处理Excel文件时发生错误: {e}")
            raise

    def process_single_question(self, question):
        """处理单个问题（用于测试）"""
        try:
            sql_query = self.call_deepseek_api(question)
            return {
                'question': question,
                'sql_query': sql_query,
                'status': 'success'
            }
        except Exception as e:
            return {
                'question': question,
                'error': str(e),
                'status': 'error'
            }

    def load_few_shot_examples(self, training_file_path: str, num_examples: int = 75):
        """
        从训练文件中加载few-shot示例，尽可能覆盖多种查询类型。

        Args:
            training_file_path: 训练文件路径
            num_examples: 需要加载的示例数量，默认15个
        """
        try:
            if os.path.exists(training_file_path):
                df = pd.read_excel(training_file_path)
                # 数据清洗
                df = df.dropna(subset=['题目', '生成的sql'])
                df = df[df['生成的sql'].str.strip().astype(bool)]

                # 定义查询模式及其目标数量（这里我们定义多种模式，并分配不同的数量）
                # 注意：总示例数量为num_examples，所以各模式的数量分配需要满足总和为num_examples
                patterns = [
                    (r'SELECT.*FROM.*WHERE.*LIKE', 2),  # 模糊查询
                    (r'SELECT.*FROM.*WHERE.*\b(AND|OR)\b.*\b(AND|OR)\b', 2),  # 多条件查询
                    (r'AVG|MAX|MIN|SUM', 2),  # 聚合函数
                    (r'GROUP BY', 2),  # 分组
                    (r'JOIN', 2),  # 连接
                    (r'ORDER BY', 2),  # 排序
                    (r'LIMIT', 1),  # 限制行数
                    (r'子查询|\(SELECT', 2),  # 子查询
                ]

                examples = []
                used_indices = set()

                # 首先，按模式选取示例
                for pattern, count in patterns:
                    # 从尚未被选中的行中选取匹配模式的示例
                    matches = df[
                        ~df.index.isin(used_indices) & df['生成的sql'].str.contains(pattern, na=False, regex=True)]
                    if len(matches) < count:
                        # 如果匹配的数量不足，则使用所有匹配的
                        selected = matches
                    else:
                        selected = matches.head(count)
                    for idx, row in selected.iterrows():
                        examples.append({"question": row['题目'], "sql": row['生成的sql']})
                        used_indices.add(idx)

                # 如果示例数量不足，随机从剩余样本中抽取补足
                if len(examples) < num_examples:
                    remaining = df[~df.index.isin(used_indices)]
                    need = num_examples - len(examples)
                    if len(remaining) < need:
                        additional = remaining
                    else:
                        additional = remaining.sample(n=need)
                    for idx, row in additional.iterrows():
                        examples.append({"question": row['题目'], "sql": row['生成的sql']})
                        used_indices.add(idx)

                # 如果示例数量超过num_examples，则截断
                self.few_shot_examples = examples[:num_examples]
                print(f"成功加载 {len(self.few_shot_examples)} 个few-shot示例")
            else:
                self.few_shot_examples = []
                print("训练文件不存在，已跳过few-shot示例")
        except Exception as e:
            print(f"加载few-shot示例失败: {e}")
            self.few_shot_examples = []
        return True

# 使用示例
def main():
    # 初始化配置
    API_KEY = "sk-ccaa87bceda64383a44a36bd0c60c32b"  # 替换为你的DeepSeek API密钥
    CONFIG_DIR = "config"  # 配置文件目录


    # 检查配置文件是否存在
    if not os.path.exists(CONFIG_DIR):
        print(f"配置目录 '{CONFIG_DIR}' 不存在，请创建并添加配置文件")
        return

    text_to_sql = DeepSeekTextToSQL(API_KEY, CONFIG_DIR)

    # 配置Excel处理参数
    EXCEL_FILE = "question.xlsx"  # 输入Excel文件路径
    START_ROW = 2  # 问题开始的行号（从1开始）
    START_COL = 2  # 问题所在的列号（从1开始，A列）
    OUTPUT_COL = 3  # 输出SQL的列号（从1开始，B列）
    NUM_QUESTIONS = 75  # 要处理的问题数量

    # 处理Excel文件
    result = text_to_sql.process_excel_file(
        file_path=EXCEL_FILE,
        start_row=START_ROW,
        start_col=START_COL,
        output_col=OUTPUT_COL,
        num_questions=NUM_QUESTIONS,
        sheet_name="Sheet1"  # 可选，默认为激活的工作表
    )

    print(f"处理完成: {result}")


# 测试单个问题
def test_single_question():
    API_KEY = "sk-346c1477c72543d492b21113e9973dd9"
    CONFIG_DIR = "config"

    text_to_sql = DeepSeekTextToSQL(API_KEY, CONFIG_DIR)

    test_question = "查询商河恒泰热源厂在2024年11月15日到2025年3月15日期间的热单耗"

    result = text_to_sql.process_single_question(test_question)
    print("测试结果:")
    print(f"问题: {result['question']}")
    if result['status'] == 'success':
        print(f"SQL: {result['sql_query']}")
    else:
        print(f"错误: {result['error']}")


if __name__ == "__main__":
    # 运行主程序
    main()

    # 或者测试单个问题
    # test_single_question()