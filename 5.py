#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek-SQL 单文件完整版 - 智能WITH学习版本
优化点：
1. 根据训练集特点智能判断是否使用WITH
2. 学习训练集中CTE的使用模式
3. 只在复杂查询时推荐使用WITH
4. 保持训练集的原始SQL模式
"""

import os
import json
import pandas as pd
import requests
import time
from typing import List, Optional, Dict, Any
import logging
from tqdm import tqdm
import re
import random

# -------------------- 日志配置 --------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ===================== 核心类 =====================
class DeepSeekSQLGenerator:
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        self.schema_info = ""
        self.formula_info = ""
        self.common_expr = ""
        self.few_shot_examples = []
        self.cte_usage_pattern = {}  # 存储CTE使用模式分析结果

    # ---------- 表结构加载（含容错） ----------
    def load_schema(self, schema_file_path: str):
        try:
            with open(schema_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            try:
                schema_data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.warning(f"标准JSON解析失败: {e}，尝试修复格式...")
                content = self._fix_json_format(content)
                schema_data = json.loads(content)

            desc = "数据库表结构信息:\n\n"
            for table in schema_data:
                desc += f"表名: {table.get('name', '')}\n描述: {table.get('describe', '')}\n字段信息:\n"
                detail = table.get("detail", "")
                if isinstance(detail, str):
                    for line in detail.strip().split('\n'):
                        if line.strip():
                            desc += f"  {line.strip()}\n"
                desc += "\n"
            self.schema_info = desc
            logger.info("数据库表结构加载成功")
            return True
        except Exception as e:
            logger.error(f"加载表结构失败: {e}")
            return self._load_schema_as_text(schema_file_path)

    def _fix_json_format(self, content: str) -> str:
        content = content.lstrip('\ufeff').replace("'", '"')
        content = re.sub(r',\s*}', '}', content)
        content = re.sub(r',\s*]', ']', content)
        content = re.sub(r'//.*', '', content)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        return content

    def _load_schema_as_text(self, schema_file_path: str) -> bool:
        try:
            with open(schema_file_path, 'r', encoding='utf-8') as f:
                self.schema_info = f"数据库表结构信息（原始格式）:\n\n{f.read()}"
            logger.info("使用备用方法加载表结构成功")
            return True
        except Exception as e:
            logger.error(f"备用方法加载表结构也失败: {e}")
            self.schema_info = self._get_basic_schema()
            return True

    def _get_basic_schema(self) -> str:
        return """主要数据库表结构:
1. ods_sc01_ntjt_zhgr_heat_station_info - 换热站业务信息表
   主要字段: stn_id, stn_name, stn_state, plan_num, heat_method, build_type, heat_area

2. ods_sc01_ntjt_zhgr_heat_station_inst_data - 换热站实时数据表
   主要字段: stn_id, data_time, stn_prim_sup_temp, stn_prim_ret_temp, stn_prim_total_hheat

3. ods_sc01_ntjt_zhgr_heat_source_info - 热源厂信息表
   主要字段: src_id, src_name, src_type, src_state, heat_area

4. ods_sc01_ntjt_zhgr_heat_source_inst_data - 热源实时数据表
   主要字段: src_id, data_time, src_sup_temp, src_ret_temp, src_sup_total_hheat

5. ods_sc01_ntjt_zhgr_heat_weather_info_log - 天气数据表
   主要字段: data_time, temp, rh, wind_speed

6. ods_sc01_ntjt_zhgr_heat_heatpump_inst_data - 热泵实时数据表
   主要字段: pump_id, data_time, circulate_water_sup_htemp

7. ods_sc01_ntjt_zhgr_heat_boiler_inst_data - 锅炉实时数据表
   主要字段: blr_id, data_time, blr_sup_temp, blr_ret_temp

8. ods_sc01_ntjt_zhgr_heat_instruction_issue_detail - 阀门指令下发表
   主要字段: stn_busi_id, valve_id, issue_result
"""

    # ---------- 其余辅助数据加载 ----------
    def load_formula_descriptions(self, formula_file_path: str):
        try:
            self.formula_info = open(formula_file_path, encoding='utf-8').read() if os.path.exists(
                formula_file_path) else "公式描述文件未找到"
            logger.info("公式描述加载成功")
        except Exception as e:
            logger.error(f"加载公式描述失败: {e}")
            self.formula_info = "公式描述加载失败"
        return True

    def load_common_expressions(self, common_expr_file_path: str):
        try:
            self.common_expr = open(common_expr_file_path, encoding='utf-8').read() if os.path.exists(
                common_expr_file_path) else "常用表达文件未找到"
            logger.info("常用表达加载成功")
        except Exception as e:
            logger.error(f"加载常用表达失败: {e}")
            self.common_expr = "常用表达加载失败"
        return True

    def load_few_shot_examples(self, training_file_path: str, num_examples: int = 35):
        """
        智能版：从训练文件中加载few-shot示例，学习训练集中的CTE使用模式
        """
        try:
            if os.path.exists(training_file_path):
                # 加载训练数据
                df = pd.read_excel(training_file_path)
                df = df.dropna(subset=['题目', '生成的sql'])
                df = df[df['生成的sql'].str.strip().astype(bool)]

                total_examples = len(df)
                logger.info(f"训练集中共有 {total_examples} 个有效示例")

                # 分析训练集中的CTE使用模式
                self._analyze_cte_patterns(df)

                # 如果示例总数小于等于需要的数量，直接返回所有示例
                if total_examples <= num_examples:
                    self.few_shot_examples = [
                        {"question": row['题目'], "sql": row['生成的sql']}
                        for _, row in df.iterrows()
                    ]
                    logger.info(f"直接使用全部 {len(self.few_shot_examples)} 个示例")
                    return True

                # 智能选择代表性示例
                selected_examples = self._select_balanced_examples(df, num_examples)

                # 转换为最终格式
                self.few_shot_examples = [
                    {"question": row['题目'], "sql": row['生成的sql']}
                    for _, row in selected_examples.iterrows()
                ]

                logger.info(f"成功选择 {len(self.few_shot_examples)} 个代表性示例")
                self._display_selection_summary(selected_examples, df)

            else:
                self.few_shot_examples = []
                logger.warning("训练文件不存在，已跳过few-shot示例")
        except Exception as e:
            logger.error(f"加载few-shot示例失败: {e}")
            self.few_shot_examples = []
        return True

    def _analyze_cte_patterns(self, df: pd.DataFrame):
        """分析训练集中的CTE使用模式"""
        # 标记是否包含CTE
        df['has_cte'] = df['生成的sql'].str.contains(r'\bWITH\b', case=False, regex=True)

        cte_count = df['has_cte'].sum()
        total_count = len(df)
        cte_ratio = cte_count / total_count * 100

        logger.info(f"CTE使用分析: {cte_count}/{total_count} ({cte_ratio:.1f}%) 的示例使用了CTE")

        # 分析使用CTE的查询特征
        cte_examples = df[df['has_cte']]
        non_cte_examples = df[~df['has_cte']]

        # 分析查询复杂度
        def calculate_complexity(sql):
            # 计算SQL复杂度指标
            complexity_score = 0
            complexity_score += len(re.findall(r'\bSELECT\b', sql, re.IGNORECASE))
            complexity_score += len(re.findall(r'\bFROM\b', sql, re.IGNORECASE))
            complexity_score += len(re.findall(r'\bWHERE\b', sql, re.IGNORECASE))
            complexity_score += len(re.findall(r'\bJOIN\b', sql, re.IGNORECASE))
            complexity_score += len(re.findall(r'\bGROUP BY\b', sql, re.IGNORECASE))
            complexity_score += len(re.findall(r'\bORDER BY\b', sql, re.IGNORECASE))
            complexity_score += len(re.findall(r'\bUNION\b', sql, re.IGNORECASE))
            complexity_score += len(re.findall(r'\(SELECT', sql, re.IGNORECASE))
            return complexity_score

        df['complexity'] = df['生成的sql'].apply(calculate_complexity)

        # 分析CTE使用场景
        cte_complexity_avg = cte_examples['complexity'].mean() if len(cte_examples) > 0 else 0
        non_cte_complexity_avg = non_cte_examples['complexity'].mean() if len(non_cte_examples) > 0 else 0

        logger.info(f"平均复杂度 - 使用CTE: {cte_complexity_avg:.2f}, 不使用CTE: {non_cte_complexity_avg:.2f}")

        # 存储CTE使用模式
        self.cte_usage_pattern = {
            'cte_ratio': cte_ratio,
            'cte_complexity_threshold': cte_complexity_avg,
            'typical_cte_scenarios': self._identify_cte_scenarios(cte_examples),
            'typical_non_cte_scenarios': self._identify_non_cte_scenarios(non_cte_examples)
        }

        logger.info(f"CTE使用模式分析完成")

    def _identify_cte_scenarios(self, cte_examples: pd.DataFrame) -> List[str]:
        """识别典型的CTE使用场景"""
        scenarios = []

        # 分析CTE示例的共同特征
        for _, row in cte_examples.iterrows():
            sql = row['生成的sql']
            question = row['题目']

            # 识别常见CTE使用模式
            if re.search(r'供暖季|月度|统计|累计', question):
                scenarios.append("时间范围统计查询")
            elif re.search(r'多个.*热源|多个.*换热站', question):
                scenarios.append("多表关联复杂查询")
            elif re.search(r'分别.*多少|各.*多少', question):
                scenarios.append("分组统计查询")
            elif len(re.findall(r'SELECT', sql, re.IGNORECASE)) > 2:
                scenarios.append("多层嵌套查询")

        # 返回去重后的场景
        return list(set(scenarios))

    def _identify_non_cte_scenarios(self, non_cte_examples: pd.DataFrame) -> List[str]:
        """识别典型的不使用CTE的场景"""
        scenarios = []

        for _, row in non_cte_examples.iterrows():
            sql = row['生成的sql']
            question = row['题目']

            # 识别简单查询模式
            if re.search(r'是多少|是什么|状态|ID|名称', question) and len(sql) < 200:
                scenarios.append("简单属性查询")
            elif re.search(r'平均|最高|最低', question) and 'AVG' in sql.upper():
                scenarios.append("简单聚合查询")
            elif len(re.findall(r'SELECT', sql, re.IGNORECASE)) == 1:
                scenarios.append("单表简单查询")

        return list(set(scenarios))

    def _select_balanced_examples(self, df: pd.DataFrame, num_examples: int) -> pd.DataFrame:
        """选择平衡的示例，包含CTE和非CTE的典型代表"""
        cte_examples = df[df['has_cte']]
        non_cte_examples = df[~df['has_cte']]

        # 根据CTE比例分配名额
        cte_ratio = len(cte_examples) / len(df)
        cte_count = min(int(num_examples * cte_ratio), len(cte_examples))
        non_cte_count = num_examples - cte_count

        # 选择代表性的CTE示例（按复杂度排序）
        if cte_count > 0:
            selected_cte = cte_examples.nlargest(cte_count, 'complexity')
        else:
            selected_cte = pd.DataFrame()

        # 选择代表性的非CTE示例（按复杂度排序，但要确保多样性）
        if non_cte_count > 0:
            # 先选择一些中等复杂度的示例
            medium_complexity = non_cte_examples[
                (non_cte_examples['complexity'] >= 3) &
                (non_cte_examples['complexity'] <= 6)
                ]

            if len(medium_complexity) >= non_cte_count:
                selected_non_cte = medium_complexity.sample(n=non_cte_count)
            else:
                # 如果中等复杂度不足，补充其他复杂度的示例
                selected_non_cte = non_cte_examples.sample(n=non_cte_count)
        else:
            selected_non_cte = pd.DataFrame()

        # 合并结果
        if not selected_cte.empty and not selected_non_cte.empty:
            result = pd.concat([selected_cte, selected_non_cte])
        elif not selected_cte.empty:
            result = selected_cte
        else:
            result = selected_non_cte

        return result.head(num_examples)

    def _display_selection_summary(self, selected: pd.DataFrame, all_data: pd.DataFrame):
        """显示选择摘要"""
        selected_cte = selected['has_cte'].sum()
        selected_total = len(selected)
        all_cte = all_data['has_cte'].sum()
        all_total = len(all_data)

        logger.info(f"示例选择摘要:")
        logger.info(f"  - 选择CTE示例: {selected_cte}/{selected_total} ({selected_cte / selected_total * 100:.1f}%)")
        logger.info(f"  - 训练集CTE比例: {all_cte}/{all_total} ({all_cte / all_total * 100:.1f}%)")
        logger.info(f"  - 平均复杂度: {selected['complexity'].mean():.2f}")

    def _should_use_cte(self, question: str) -> bool:
        """根据问题特征判断是否应该使用CTE"""
        question_lower = question.lower()

        # 基于训练集分析的模式来判断
        cte_scenarios = self.cte_usage_pattern.get('typical_cte_scenarios', [])
        non_cte_scenarios = self.cte_usage_pattern.get('typical_non_cte_scenarios', [])

        # 检查是否匹配CTE使用场景
        for scenario in cte_scenarios:
            if scenario == "时间范围统计查询" and any(
                    keyword in question_lower for keyword in ['供暖季', '月度', '每月', '各月']):
                return True
            elif scenario == "多表关联复杂查询" and any(
                    keyword in question_lower for keyword in ['多个', '分别', '各']):
                return True
            elif scenario == "分组统计查询" and any(keyword in question_lower for keyword in ['分别', '各', '统计']):
                return True

        # 检查是否匹配非CTE场景
        for scenario in non_cte_scenarios:
            if scenario == "简单属性查询" and any(
                    keyword in question_lower for keyword in ['是多少', '是什么', '状态', 'id', '名称']):
                return False
            elif scenario == "简单聚合查询" and any(keyword in question_lower for keyword in ['平均', '最高', '最低']):
                return False

        # 默认根据训练集的CTE比例决定
        cte_ratio = self.cte_usage_pattern.get('cte_ratio', 0)
        return random.random() < (cte_ratio / 100)

    # ---------- Prompt 构建 ----------
    def create_prompt(self, question: str) -> str:
        # 构建few-shot示例文本
        few_shot_text = "\n".join(
            [f"示例 {i}:\n问题: {ex['question']}\nSQL: {ex['sql']}\n"
             for i, ex in enumerate(self.few_shot_examples, 1)]
        ) if self.few_shot_examples else ""

        # 根据问题特征决定是否推荐使用CTE
        should_use_cte = self._should_use_cte(question)
        cte_advice = ""

        if should_use_cte:
            cte_advice = "注意：对于这类复杂查询，建议使用CTE（WITH子句）来提高可读性和维护性。"
        else:
            cte_advice = "对于这类相对简单的查询，可以使用直接的SELECT语句。"

        prompt = f"""你是一个专业的Text-to-SQL转换专家，专门处理能源供热领域的数据库查询。

数据库表结构信息:
{self.schema_info}

常用表达说明:
{self.common_expr}

公式描述:
{self.formula_info}

任务要求:
1. 根据自然语言问题生成准确的SQL查询语句
2. 只返回SQL语句，不要额外的解释
3. 确保SQL语法正确，符合数据库表结构
4. 使用LIKE进行模糊匹配时，使用'%关键词%'格式
5. 时间范围查询要包含开始和结束时间
6. 对于统计查询，确保使用正确的聚合函数
7. 注意表之间的关联关系
8. {cte_advice}

重要说明：
- 对于复杂查询（如涉及多个表连接、子查询、时间范围统计等），推荐使用CTE（WITH子句）
- 对于简单查询（如单表查询、简单属性查询），可以直接使用SELECT语句
- 请参考训练集中的示例模式来决定是否使用CTE

参考示例:
{few_shot_text}

请为以下问题生成SQL查询:

问题: {question}

SQL:"""
        return prompt

    # ---------- API 调用 ----------
    def call_deepseek_api(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.1) -> Optional[str]:
        try:
            data = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False
            }
            response = requests.post(f"{self.base_url}/chat/completions",
                                     headers=self.headers,
                                     json=data,
                                     timeout=60)
            if response.status_code == 200:
                sql = response.json()['choices'][0]['message']['content'].strip()
                return self._clean_sql(sql)
            else:
                logger.error(f"API调用失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"调用DeepSeek API异常: {e}")
            return None

    def _clean_sql(self, sql: str) -> str:
        if not sql:
            return "生成失败"
        sql = re.sub(r'(?s)```sql(.*?)```', r'\1', sql)
        sql = re.sub(r'(?s)```(.*?)```', r'\1', sql)
        lines = [ln.strip() for ln in sql.splitlines()
                 if ln.strip() and not re.match(r'(--|/\*|\*/|说明:|注意:|提示:|回答:)', ln.strip())]
        cleaned_sql = '\n'.join(lines).strip()

        return cleaned_sql

    # ---------- 批量生成 ----------
    def generate_sql_for_questions(self, questions: List[str], output_file: str, batch_delay: int = 2):
        results = []
        for i, question in enumerate(tqdm(questions, desc="生成SQL"), 1):
            if pd.notna(question) and str(question).strip():
                q_text = str(question).strip()
                logger.info(f"处理问题 {i}: {q_text[:50]}...")
                prompt = self.create_prompt(q_text)
                sql = self.call_deepseek_api(prompt)

                results.append({"序号": i, "题目": q_text, "生成的sql": sql or "生成失败"})
                if i < len(questions):
                    time.sleep(batch_delay)
            else:
                results.append({"序号": i, "题目": question, "生成的sql": "问题为空"})

        # 统计CTE使用情况
        cte_count = sum(1 for r in results if r['生成的sql'].upper().startswith('WITH'))
        total_valid = sum(1 for r in results if r['生成的sql'] not in ["生成失败", "问题为空"])

        logger.info(f"CTE使用统计: {cte_count}/{total_valid} ({cte_count / max(total_valid, 1) * 100:.1f}%) 使用了CTE")

        pd.DataFrame(results).to_excel(output_file, index=False)
        logger.info(f"SQL生成完成，结果已保存到: {output_file}")
        return pd.DataFrame(results)

    def generate_sql_for_excel(self,
                               input_file: str,
                               output_file: str,
                               question_column: str = "题目"):
        """为Excel文件中的问题生成SQL"""
        try:
            if not os.path.exists(input_file):
                logger.error(f"输入文件不存在: {input_file}")
                return None
            df = pd.read_excel(input_file)
            if question_column not in df.columns:
                logger.error(f"列 '{question_column}' 在文件中不存在")
                logger.info(f"可用的列: {list(df.columns)}")
                return None
            questions = df[question_column].tolist()

            # 直接调用generate_sql_for_questions，使用默认的batch_delay
            results_df = self.generate_sql_for_questions(questions, output_file)

            success = len([s for s in results_df['生成的sql'] if s not in {"生成失败", "问题为空"}])
            total = len(questions)
            logger.info(f"SQL生成统计: 成功 {success}/{total} ({success / total * 100:.1f}%)")
            return results_df
        except Exception as e:
            logger.error(f"处理Excel文件失败: {e}")
            return None


# ===================== 主函数 =====================
def main():
    CONFIG = {
        "api_key": "sk-ccaa87bceda64383a44a36bd0c60c32b",  # ← 换成你的
        "schema_file_path": r"config/table_descriptions.json",
        "training_file_path": r"算法训练集（75道问题及sql语句）.xlsx",
        "formula_file_path": r"config/formula_descriptions.json",
        "common_expr_file_path": r"config/common_expressions.json",
        "input_file_path": r"算法训练集（75道问题及sql语句）.xlsx",
        "output_file_path": r"output.xlsx"
    }

    generator = DeepSeekSQLGenerator(CONFIG["api_key"])
    logger.info("开始加载数据...")
    generator.load_schema(CONFIG["schema_file_path"])
    generator.load_formula_descriptions(CONFIG["formula_file_path"])
    generator.load_common_expressions(CONFIG["common_expr_file_path"])
    generator.load_few_shot_examples(CONFIG["training_file_path"])

    logger.info("开始生成SQL语句...")
    results = generator.generate_sql_for_excel(
        input_file=CONFIG["input_file_path"],
        output_file=CONFIG["output_file_path"]
    )

    if results is not None:
        logger.info("SQL生成任务完成！")
        print(f"\n结果已保存到: {CONFIG['output_file_path']}")
    else:
        logger.error("SQL生成失败")


if __name__ == "__main__":
    main()