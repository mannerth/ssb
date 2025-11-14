import openai
import json
import time
import os
import pandas as pd
import re
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
import logging
from collections import defaultdict
import numpy as np
from difflib import SequenceMatcher
import hashlib

training_file_path = "算法训练集（75道问题及sql语句）.xlsx"


class AdvancedErrorPatternLearner:
    """高级错误模式学习器"""

    def __init__(self, config_dir="config"):
        self.config_dir = config_dir
        self.error_patterns = []
        self.correction_rules = []
        self.error_stats = defaultdict(int)
        self.success_patterns = []  # 成功模式记录
        self.pattern_cache = {}
        self.similarity_cache = {}
        self.learning_rate = 0.1  # 学习率，控制模式更新速度
        self.load_error_patterns()

    def load_error_patterns(self):
        """加载错误模式"""
        try:
            file_path = os.path.join(self.config_dir, "error_patterns.json")
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.error_patterns = data.get('error_patterns', [])
                    self.correction_rules = data.get('correction_rules', [])
                    self.error_stats = defaultdict(int, data.get('error_stats', {}))
                    self.success_patterns = data.get('success_patterns', [])

                    # 按出现频率和修正成功率排序
                    self.error_patterns.sort(key=lambda x: x.get('occurrences', 0) *
                                                           (x.get('correction_success_rate', 0.5)), reverse=True)
        except Exception as e:
            print(f"加载错误模式失败: {e}")

    def save_error_patterns(self):
        """保存错误模式"""
        try:
            file_path = os.path.join(self.config_dir, "error_patterns.json")
            data = {
                'error_patterns': self.error_patterns,
                'correction_rules': self.correction_rules,
                'error_stats': dict(self.error_stats),
                'success_patterns': self.success_patterns
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存错误模式失败: {e}")

    def add_error_pattern(self, question, wrong_sql, correct_sql, error_type, error_description, confidence_impact):
        """添加错误模式 - 增强版"""
        question_pattern = self.extract_enhanced_question_pattern(question)
        sql_pattern = self.extract_enhanced_sql_pattern(wrong_sql)

        pattern = {
            'question_pattern': question_pattern,
            'sql_pattern': sql_pattern,
            'error_type': error_type,
            'error_description': error_description,
            'correction': correct_sql,
            'occurrences': 1,
            'confidence_impact': confidence_impact,
            'correction_success_rate': 0.5,  # 初始修正成功率
            'last_used': time.time()
        }

        # 检查是否已存在类似模式
        existing_pattern = None
        max_similarity = 0

        for p in self.error_patterns:
            q_similarity = self.enhanced_pattern_similarity(question_pattern, p['question_pattern'])
            s_similarity = self.enhanced_pattern_similarity(sql_pattern, p['sql_pattern'])
            total_similarity = 0.6 * q_similarity + 0.4 * s_similarity

            if total_similarity > max_similarity and total_similarity > 0.7:
                max_similarity = total_similarity
                existing_pattern = p

        if existing_pattern:
            # 更新现有模式
            existing_pattern['occurrences'] += 1
            existing_pattern['confidence_impact'] = (
                    existing_pattern['confidence_impact'] * (1 - self.learning_rate) +
                    confidence_impact * self.learning_rate
            )
            existing_pattern['last_used'] = time.time()
        else:
            self.error_patterns.append(pattern)

        self.error_stats[error_type] += 1

        # 重新排序
        self.error_patterns.sort(key=lambda x: x.get('occurrences', 0) *
                                               (x.get('correction_success_rate', 0.5)), reverse=True)
        self.save_error_patterns()

    def add_success_pattern(self, question, sql, validation_confidence):
        """添加成功模式"""
        pattern = {
            'question_pattern': self.extract_enhanced_question_pattern(question),
            'sql_pattern': self.extract_enhanced_sql_pattern(sql),
            'confidence': validation_confidence,
            'timestamp': time.time()
        }

        # 只保留高质量的成功模式
        if validation_confidence >= 85:
            self.success_patterns.append(pattern)
            # 限制成功模式数量
            if len(self.success_patterns) > 100:
                self.success_patterns.sort(key=lambda x: x['confidence'], reverse=True)
                self.success_patterns = self.success_patterns[:80]

    def extract_enhanced_question_pattern(self, question):
        """增强版问题模式提取"""
        cache_key = f"q_{hashlib.md5(question.encode()).hexdigest()}"
        if cache_key in self.pattern_cache:
            return self.pattern_cache[cache_key]

        # 深度模式提取
        pattern = question.lower()

        # 替换具体值
        pattern = re.sub(r'\d{4}-\d{4}', 'YYYY-YYYY', pattern)  # 年份范围
        pattern = re.sub(r'\d{4}年', 'YYYY年', pattern)  # 年份
        pattern = re.sub(r'\d{1,2}月', 'MM月', pattern)  # 月份
        pattern = re.sub(r'\d+', 'NUM', pattern)  # 数字

        # 识别业务实体
        business_entities = {
            '换热站': 'HEAT_STATION',
            '热源厂': 'HEAT_SOURCE',
            '热量': 'HEAT_VALUE',
            '温度': 'TEMPERATURE',
            '压力': 'PRESSURE',
            '流量': 'FLOW_RATE'
        }

        for entity, code in business_entities.items():
            pattern = pattern.replace(entity, code)

        self.pattern_cache[cache_key] = pattern
        return pattern

    def extract_enhanced_sql_pattern(self, sql):
        """增强版SQL模式提取"""
        cache_key = f"s_{hashlib.md5(sql.encode()).hexdigest()}"
        if cache_key in self.pattern_cache:
            return self.pattern_cache[cache_key]

        # 深度SQL结构分析
        pattern = sql.upper()

        # 替换具体值但保留结构
        pattern = re.sub(r'\d{4}-\d{2}-\d{2}', 'DATE', pattern)  # 日期
        pattern = re.sub(r"'[^']*'", 'STRING', pattern)  # 字符串
        pattern = re.sub(r'\b\d+\b', 'NUM', pattern)  # 数字

        # 标准化SQL结构
        pattern = re.sub(r'\s+', ' ', pattern)  # 标准化空格
        pattern = re.sub(r'SELECT\s+.*?\s+FROM', 'SELECT ... FROM', pattern)
        pattern = re.sub(r'WHERE\s+.*?(?=GROUP BY|ORDER BY|LIMIT|$)', 'WHERE ...', pattern)

        self.pattern_cache[cache_key] = pattern
        return pattern

    def enhanced_pattern_similarity(self, text1, text2):
        """增强版模式相似度计算"""
        cache_key = f"sim_{hashlib.md5((text1 + text2).encode()).hexdigest()}"
        if cache_key in self.similarity_cache:
            return self.similarity_cache[cache_key]

        # 使用多种相似度计算方法
        sequence_similarity = SequenceMatcher(None, text1, text2).ratio()

        # 词级相似度
        words1 = set(re.findall(r'[A-Z_]+|[\u4e00-\u9fff]+', text1))
        words2 = set(re.findall(r'[A-Z_]+|[\u4e00-\u9fff]+', text2))

        if words1 and words2:
            jaccard_similarity = len(words1.intersection(words2)) / len(words1.union(words2))
        else:
            jaccard_similarity = 0

        # 综合相似度
        total_similarity = 0.6 * sequence_similarity + 0.4 * jaccard_similarity

        self.similarity_cache[cache_key] = total_similarity
        return total_similarity

    def suggest_enhanced_correction(self, question, sql_query, validation_feedback):
        """增强版修正建议"""
        question_pattern = self.extract_enhanced_question_pattern(question)
        sql_pattern = self.extract_enhanced_sql_pattern(sql_query)

        best_error_match = None
        best_error_score = 0
        best_success_match = None
        best_success_score = 0

        # 检查错误模式
        for pattern in self.error_patterns[:25]:  # 只检查前25个高频错误
            q_similarity = self.enhanced_pattern_similarity(question_pattern, pattern['question_pattern'])

            if q_similarity < 0.4:
                continue

            s_similarity = self.enhanced_pattern_similarity(sql_pattern, pattern['sql_pattern'])

            # 综合评分，考虑频率和修正成功率
            total_score = (0.6 * q_similarity + 0.4 * s_similarity) * \
                          (1 + min(pattern['occurrences'] / 20, 2)) * \
                          pattern['correction_success_rate']

            if total_score > best_error_score and total_score > 0.6:
                best_error_score = total_score
                best_error_match = pattern

        # 检查成功模式
        for pattern in self.success_patterns[:20]:  # 只检查前20个高质量成功模式
            q_similarity = self.enhanced_pattern_similarity(question_pattern, pattern['question_pattern'])

            if q_similarity < 0.5:
                continue

            total_score = q_similarity * (pattern['confidence'] / 100)

            if total_score > best_success_score and total_score > 0.7:
                best_success_score = total_score
                best_success_match = pattern

        # 优先使用成功模式
        if best_success_match and best_success_score > 0.8:
            return {
                'correction': best_success_match['sql_pattern'].replace('SELECT ... FROM', 'SELECT * FROM').replace(
                    'WHERE ...', ''),
                'confidence': min(best_success_score * 120, 98),
                'source': 'success_pattern',
                'match_score': best_success_score
            }
        elif best_error_match:
            return {
                'correction': best_error_match['correction'],
                'confidence': min(best_error_score * 100, 95),
                'source': 'error_pattern',
                'match_score': best_error_score,
                'error_type': best_error_match['error_type']
            }

        return None


class SemanticUnderstandingEngine:
    """语义理解引擎"""

    def __init__(self, client, config_dir):
        self.client = client
        self.config_dir = config_dir
        self.cache = {}

    def analyze_question_intent(self, question):
        """深度分析问题意图"""
        cache_key = f"intent_{hashlib.md5(question.encode()).hexdigest()}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        analysis_prompt = f"""
请深度分析以下能源供热领域问题的意图：

问题："{question}"

请从以下维度分析：
1. 核心查询目标（要获取什么信息）
2. 业务实体（涉及哪些设备、指标）
3. 时间范围要求
4. 聚合计算需求
5. 排序和限制需求
6. 关联表需求

请按JSON格式返回分析结果：
{{
    "core_intent": "核心查询目标",
    "business_entities": ["实体1", "实体2"],
    "time_requirements": "时间要求描述",
    "aggregation_needs": "聚合需求",
    "sorting_limits": "排序限制",
    "table_relationships": "表关联需求",
    "complexity_level": "high/medium/low"
}}
"""
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是能源供热领域的语义分析专家。"},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.1,
                max_tokens=1500
            )

            result = response.choices[0].message.content.strip()

            # 提取JSON部分
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                self.cache[cache_key] = analysis
                return analysis
            else:
                #  fallback
                return {
                    "core_intent": "未知",
                    "business_entities": [],
                    "time_requirements": "",
                    "aggregation_needs": "",
                    "sorting_limits": "",
                    "table_relationships": "",
                    "complexity_level": "medium"
                }

        except Exception as e:
            logging.error(f"语义分析失败: {e}")
            return {
                "core_intent": "未知",
                "business_entities": [],
                "time_requirements": "",
                "aggregation_needs": "",
                "sorting_limits": "",
                "table_relationships": "",
                "complexity_level": "medium"
            }

    def rewrite_question_for_clarity(self, question, intent_analysis):
        """重写问题以提高清晰度"""
        rewrite_prompt = f"""
原始问题："{question}"

语义分析：{json.dumps(intent_analysis, ensure_ascii=False)}

请将这个问题重写为更清晰、更明确的SQL生成指令，确保：
1. 明确指定需要的表和字段
2. 清晰描述查询条件
3. 明确聚合和排序要求
4. 使用标准的业务术语

请只返回重写后的问题：
"""
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是问题重写专家。"},
                    {"role": "user", "content": rewrite_prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logging.error(f"问题重写失败: {e}")
            return question


class MultiStrategySQLGenerator:
    """多策略SQL生成器"""

    def __init__(self, client, config_dir):
        self.client = client
        self.config_dir = config_dir
        self.strategies = [
            self.direct_generation,
            self.step_by_step_generation,
            self.schema_based_generation,
            self.example_based_generation
        ]

    def direct_generation(self, question, system_prompt):
        """直接生成策略"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请为以下问题生成SQL：{question}"}
        ]

        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.1,
            max_tokens=2000
        )

        return response.choices[0].message.content.strip()

    def step_by_step_generation(self, question, system_prompt):
        """逐步推理生成策略"""
        steps_prompt = f"""
请为以下问题生成SQL，按步骤思考：

问题：{question}

思考步骤：
1. 确定核心查询目标
2. 识别需要的表和字段
3. 分析查询条件和关联关系
4. 确定聚合和排序需求
5. 编写完整SQL

请先输出思考过程，然后输出SQL。
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": steps_prompt}
        ]

        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.1,
            max_tokens=3000
        )

        return response.choices[0].message.content.strip()

    def schema_based_generation(self, question, system_prompt):
        """基于表结构的生成策略"""
        schema_prompt = f"""
基于以下表结构为问题生成SQL：

问题：{question}

请仔细分析表结构，确保：
1. 使用正确的表名和字段名
2. 正确处理表关联
3. 使用合适的查询条件

请直接输出SQL：
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": schema_prompt}
        ]

        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.1,
            max_tokens=2000
        )

        return response.choices[0].message.content.strip()

    def example_based_generation(self, question, system_prompt, examples):
        """基于示例的生成策略"""
        examples_text = "\n".join([f"问题：{ex['question']}\nSQL：{ex['sql']}" for ex in examples[:3]])

        example_prompt = f"""
参考以下类似示例：

{examples_text}

请为以下问题生成类似的SQL：

问题：{question}

请直接输出SQL：
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": example_prompt}
        ]

        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.1,
            max_tokens=2000
        )

        return response.choices[0].message.content.strip()

    def generate_with_multiple_strategies(self, question, system_prompt, relevant_examples):
        """使用多策略生成SQL"""
        results = []

        for strategy in self.strategies:
            try:
                if strategy == self.example_based_generation:
                    result = strategy(question, system_prompt, relevant_examples)
                else:
                    result = strategy(question, system_prompt)
                results.append(result)
                time.sleep(0.2)  # 避免API限制
            except Exception as e:
                logging.warning(f"策略 {strategy.__name__} 失败: {e}")
                continue

        return results


class StrictSQLValidator:
    """严格SQL验证器"""

    def __init__(self, client):
        self.client = client
        self.validation_cache = {}

    def comprehensive_validation(self, question, sql_query, intent_analysis):
        """综合验证"""
        cache_key = f"val_{hashlib.md5((question + sql_query).encode()).hexdigest()}"
        if cache_key in self.validation_cache:
            return self.validation_cache[cache_key]

        # 多维度验证
        syntax_check = self.syntax_validation(sql_query)
        business_check = self.business_logic_validation(question, sql_query, intent_analysis)
        semantic_check = self.semantic_validation(question, sql_query, intent_analysis)
        performance_check = self.performance_validation(sql_query)

        # 综合评分
        weights = {
            'syntax': 0.25,
            'business': 0.35,
            'semantic': 0.30,
            'performance': 0.10
        }

        total_confidence = (
                syntax_check['confidence'] * weights['syntax'] +
                business_check['confidence'] * weights['business'] +
                semantic_check['confidence'] * weights['semantic'] +
                performance_check['confidence'] * weights['performance']
        )

        # 合并问题
        all_issues = []
        for check in [syntax_check, business_check, semantic_check, performance_check]:
            if not check.get('passed', True) and check.get('issues'):
                all_issues.extend(check['issues'])

        validation_result = {
            'confidence': total_confidence,
            'passed': total_confidence >= 80 and len(all_issues) == 0,
            'issues': all_issues,
            'detailed_checks': {
                'syntax': syntax_check,
                'business': business_check,
                'semantic': semantic_check,
                'performance': performance_check
            }
        }

        self.validation_cache[cache_key] = validation_result
        return validation_result

    def syntax_validation(self, sql_query):
        """语法验证"""
        issues = []

        # 基础语法检查
        sql_upper = sql_query.upper()

        if not sql_upper.startswith('SELECT'):
            issues.append("SQL必须以SELECT开头")

        if 'FROM' not in sql_upper:
            issues.append("缺少FROM子句")

        # 检查括号匹配
        if sql_upper.count('(') != sql_upper.count(')'):
            issues.append("括号不匹配")

        # 检查危险操作
        dangerous_ops = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE', 'TRUNCATE']
        for op in dangerous_ops:
            if op in sql_upper:
                issues.append(f"包含危险操作: {op}")

        confidence = 100 - len(issues) * 15
        return {
            'confidence': max(confidence, 0),
            'passed': len(issues) == 0,
            'issues': issues
        }

    def business_logic_validation(self, question, sql_query, intent_analysis):
        """业务逻辑验证"""
        issues = []

        validation_prompt = f"""
问题：{question}
预期意图：{json.dumps(intent_analysis, ensure_ascii=False)}
生成的SQL：{sql_query}

请从能源供热业务角度严格验证：
1. 是否使用了正确的业务计算公式
2. 时间范围处理是否符合业务规范
3. 热源厂、换热站等业务实体处理是否正确
4. 累计量、瞬时量计算是否符合业务逻辑
5. 是否考虑了供暖季等特殊业务时间
6. 表关联和字段使用是否正确

请指出任何业务逻辑问题，按以下格式回复：
问题：[具体问题描述]
严重程度：[high/medium/low]
"""
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是能源供热业务验证专家。"},
                    {"role": "user", "content": validation_prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )

            result = response.choices[0].message.content.strip()

            # 解析业务问题
            if "问题：" in result:
                problem_lines = [line for line in result.split('\n') if line.startswith('问题：')]
                for line in problem_lines:
                    problem = line.replace('问题：', '').strip()
                    if problem and problem != '无':
                        issues.append(f"业务逻辑: {problem}")

            confidence = 100 - len(issues) * 20
            return {
                'confidence': max(confidence, 0),
                'passed': len(issues) == 0,
                'issues': issues
            }

        except Exception as e:
            logging.error(f"业务逻辑验证失败: {e}")
            return {
                'confidence': 50,
                'passed': False,
                'issues': ["业务逻辑验证过程出错"]
            }

    def semantic_validation(self, question, sql_query, intent_analysis):
        """语义一致性验证"""
        issues = []

        semantic_prompt = f"""
问题："{question}"
生成的SQL：{sql_query}

请验证SQL是否准确反映了用户问题的语义意图：
1. 查询结果是否完整回答了用户问题
2. 筛选条件是否完整且准确
3. 排序和限制是否符合问题要求
4. 字段选择是否恰当
5. 是否遗漏了重要的查询条件

请指出任何语义不一致问题：
"""
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是语义一致性验证专家。"},
                    {"role": "user", "content": semantic_prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )

            result = response.choices[0].message.content.strip()

            # 简单的语义问题检测
            if any(word in result.lower() for word in ['不匹配', '遗漏', '不完整', '不准确', '错误']):
                if '没有问题' not in result and '完全匹配' not in result:
                    issues.append("语义一致性存在问题")

            confidence = 90 if len(issues) == 0 else 60
            return {
                'confidence': confidence,
                'passed': len(issues) == 0,
                'issues': issues
            }

        except Exception as e:
            logging.error(f"语义验证失败: {e}")
            return {
                'confidence': 60,
                'passed': False,
                'issues': ["语义验证过程出错"]
            }

    def performance_validation(self, sql_query):
        """性能验证"""
        issues = []
        sql_upper = sql_query.upper()

        # 检查明显的性能问题
        if sql_upper.count('SELECT') > 2:
            issues.append("可能包含过多子查询，影响性能")

        if 'CROSS JOIN' in sql_upper:
            issues.append("使用CROSS JOIN可能导致性能问题")

        if "LIKE '%" in sql_upper:
            issues.append("前导通配符LIKE查询影响性能")

        confidence = 100 - len(issues) * 10
        return {
            'confidence': max(confidence, 70),
            'passed': len(issues) == 0,
            'issues': issues
        }


class UltraAccurateTextToSQL:
    """超高准确率Text-to-SQL系统"""

    def __init__(self, api_key, config_dir="config", base_url="https://api.deepseek.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.config_dir = config_dir

        # 配置客户端
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)

        # 首先设置日志
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        # 加载领域知识
        self.formula_descriptions = self.load_formula_descriptions()
        self.common_expressions = self.load_common_expressions()
        self.table_descriptions = self.load_table_descriptions()
        self.load_optimized_few_shot_examples(training_file_path)

        # 初始化高级组件
        self.error_learner = AdvancedErrorPatternLearner(config_dir)
        self.semantic_engine = SemanticUnderstandingEngine(self.client, config_dir)
        self.multi_strategy_generator = MultiStrategySQLGenerator(self.client, config_dir)
        self.strict_validator = StrictSQLValidator(self.client)

        # 高级参数
        self.confidence_threshold = 90  # 提高置信度阈值
        self.max_retry_rounds = 8
        self.enable_semantic_rewrite = True
        self.enable_multi_strategy = True

        # 结果记录
        self.validation_results = {}
        self.generation_stats = defaultdict(int)

    def load_formula_descriptions(self):
        """加载公式描述"""
        try:
            file_path = os.path.join(self.config_dir, "formula_descriptions.json")
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"加载公式描述失败: {e}")
            return {}

    def load_common_expressions(self):
        """加载常用表达"""
        try:
            file_path = os.path.join(self.config_dir, "common_expressions.json")
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"加载常用表达失败: {e}")
            return []

    def load_table_descriptions(self):
        """加载数据表描述"""
        try:
            file_path = os.path.join(self.config_dir, "table_descriptions.json")
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"加载数据表描述失败: {e}")
            return []

    def load_optimized_few_shot_examples(self, training_file_path: str):
        """加载优化的few-shot示例"""
        try:
            if os.path.exists(training_file_path):
                df = pd.read_excel(training_file_path)
                df = df.dropna(subset=['题目', '生成的sql'])
                df = df[df['生成的sql'].str.strip().astype(bool)]

                # 高质量示例筛选
                high_quality_examples = []
                for _, row in df.iterrows():
                    sql = row['生成的sql'].upper()
                    question = row['题目']

                    # 筛选标准：语法正确、业务相关、结构清晰
                    if (self.is_sql_well_structured(sql) and
                            self.is_business_relevant(question) and
                            len(sql) < 500):  # 避免过于复杂的SQL
                        high_quality_examples.append({
                            "question": row['题目'],
                            "sql": row['生成的sql']
                        })

                # 按查询类型分类
                categorized_examples = self.categorize_examples(high_quality_examples)

                # 平衡选取
                self.few_shot_examples = self.balance_example_selection(categorized_examples, 50)
                self.logger.info(f"加载 {len(self.few_shot_examples)} 个高质量few-shot示例")
            else:
                self.few_shot_examples = []
                self.logger.warning("训练文件不存在")
        except Exception as e:
            self.logger.error(f"加载示例失败: {e}")
            self.few_shot_examples = []

    def is_sql_well_structured(self, sql):
        """检查SQL结构是否良好"""
        sql_upper = sql.upper()
        return (
                sql_upper.startswith('SELECT') and
                'FROM' in sql_upper and
                sql_upper.count('(') == sql_upper.count(')')
        )

    def is_business_relevant(self, question):
        """检查问题是否业务相关"""
        business_keywords = {'热量', '温度', '压力', '流量', '换热站', '热源厂', '供暖季', '累计'}
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in business_keywords)

    def categorize_examples(self, examples):
        """分类示例"""
        categories = {
            'time_query': [],
            'aggregation': [],
            'multi_table': [],
            'ranking': [],
            'complex': []
        }

        for example in examples:
            sql = example['sql'].upper()
            question = example['question']

            if 'JOIN' in sql and ('SUM' in sql or 'COUNT' in sql):
                categories['complex'].append(example)
            elif 'JOIN' in sql:
                categories['multi_table'].append(example)
            elif 'SUM' in sql or 'AVG' in sql or 'COUNT' in sql:
                categories['aggregation'].append(example)
            elif 'ORDER BY' in sql and 'LIMIT' in sql:
                categories['ranking'].append(example)
            elif 'BETWEEN' in sql or 'DATE' in sql:
                categories['time_query'].append(example)

        return categories

    def balance_example_selection(self, categorized_examples, total_count):
        """平衡选取示例"""
        examples = []
        examples_per_category = max(1, total_count // len(categorized_examples))

        for category in categorized_examples.values():
            if len(category) > examples_per_category:
                examples.extend(category[:examples_per_category])
            else:
                examples.extend(category)

        # 补充不足
        if len(examples) < total_count:
            all_examples = []
            for category in categorized_examples.values():
                all_examples.extend(category)

            # 去重
            seen = set()
            unique_examples = []
            for ex in all_examples:
                key = (ex['question'], ex['sql'])
                if key not in seen:
                    seen.add(key)
                    unique_examples.append(ex)

            # 添加未包含的示例
            for ex in unique_examples:
                if ex not in examples and len(examples) < total_count:
                    examples.append(ex)

        return examples[:total_count]

    def build_ultimate_system_prompt(self, question, intent_analysis):
        """构建终极系统提示词"""
        # 选择最相关示例
        relevant_examples = self.select_highly_relevant_examples(question, intent_analysis)

        examples_text = ""
        for i, ex in enumerate(relevant_examples[:3]):
            examples_text += f"示例{i + 1}:\n问题: {ex['question']}\nSQL: {ex['sql']}\n\n"

        # 构建终极提示词
        ultimate_prompt = f"""你是顶级的能源供热SQL专家，需要生成100%准确的SQL查询。

## 绝对原则：
1. 只生成SELECT语句，严禁任何数据修改操作
2. 100%准确的表名和字段名
3. 严格遵守业务规则和计算公式
4. 完美处理时间范围和业务逻辑

## 核心业务规则：
{self.build_business_rules_section()}

## 数据表结构：
{self.build_table_structure_section()}

## 计算公式：
{self.build_formula_section()}

## 高质量示例：
{examples_text}

## 当前问题分析：
核心意图: {intent_analysis.get('core_intent', '未知')}
业务实体: {', '.join(intent_analysis.get('business_entities', []))}
时间要求: {intent_analysis.get('time_requirements', '无')}

请为以下问题生成完美的SQL，确保100%准确：
问题: {question}

只返回SQL代码："""

        return ultimate_prompt

    def build_business_rules_section(self):
        """构建业务规则部分"""
        rules = [
            "采暖季时间: 前一年11月15日00:00:00至第二年03月15日00:00:00",
            "热源厂指标: 计算src_id为1和2的总和",
            "换热站指标: 注意机组数量(plan_num)",
            "累计量计算: 结束时间值减去开始时间值",
            "时间点查询: 取该时间点后第一条数据"
        ]
        return "\n".join([f"- {rule}" for rule in rules])

    def build_table_structure_section(self):
        """构建表结构部分"""
        section = ""
        for table in self.table_descriptions:
            section += f"{table['name']}: {table['describe']}\n"
        return section

    def build_formula_section(self):
        """构建公式部分"""
        section = ""
        for name, desc in self.formula_descriptions.items():
            section += f"{name}: {desc}\n"
        return section

    def select_highly_relevant_examples(self, question, intent_analysis):
        """选择高度相关示例"""
        question_entities = set(intent_analysis.get('business_entities', []))
        question_intent = intent_analysis.get('core_intent', '')

        scored_examples = []

        for example in self.few_shot_examples:
            score = 0

            # 意图相似度
            if any(word in example['question'] for word in question_intent.split()):
                score += 3

            # 实体匹配度
            example_entities = set(re.findall(r'[换热站|热源厂|热量|温度|压力|流量]', example['question']))
            entity_overlap = len(question_entities.intersection(example_entities))
            score += entity_overlap * 2

            # 语义相似度
            semantic_similarity = SequenceMatcher(None, question.lower(), example['question'].lower()).ratio()
            score += semantic_similarity * 5

            scored_examples.append((score, example))

        scored_examples.sort(key=lambda x: x[0], reverse=True)
        return [ex[1] for _, ex in scored_examples[:5]]

    def extract_sql_from_response(self, response):
        """从响应中提取SQL"""
        # 多种提取策略
        patterns = [
            r'```sql\n(.*?)\n```',
            r'SELECT.*?(?=;|$)',
            r'最终SQL:\s*(SELECT.*)',
            r'SQL:\s*(SELECT.*)'
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                sql = match.group(1) if match.lastindex else match.group(0)
                return self.clean_sql(sql)

        # 查找SELECT开头的行
        for line in response.split('\n'):
            line = line.strip()
            if line.upper().startswith('SELECT'):
                return self.clean_sql(line)

        return None

    def clean_sql(self, sql):
        """清理SQL"""
        sql = re.sub(r'```sql|```', '', sql).strip()
        sql = re.sub(r'^SQL:\s*', '', sql, flags=re.IGNORECASE)
        return sql

    def ultra_accurate_sql_generation(self, question):
        """超高准确率SQL生成"""
        self.logger.info(f"开始处理问题: {question}")

        # 阶段1: 深度语义理解
        intent_analysis = self.semantic_engine.analyze_question_intent(question)
        self.logger.info(f"语义分析完成: {intent_analysis['core_intent']}")

        # 阶段2: 问题优化（可选）
        optimized_question = question
        if self.enable_semantic_rewrite and intent_analysis['complexity_level'] == 'high':
            optimized_question = self.semantic_engine.rewrite_question_for_clarity(question, intent_analysis)
            self.logger.info(f"问题优化: {optimized_question}")

        best_sql = None
        best_confidence = 0
        best_validation = None

        # 阶段3: 多轮生成和验证
        for retry_round in range(self.max_retry_rounds):
            self.logger.info(f"第 {retry_round + 1} 轮生成")

            # 生成策略选择
            if retry_round == 0 and self.enable_multi_strategy:
                # 第一轮使用多策略
                sql_candidates = self.generate_with_multiple_strategies(optimized_question, intent_analysis)
            else:
                # 后续轮次使用最佳策略
                sql_candidates = [self.generate_with_best_strategy(optimized_question, intent_analysis, retry_round)]

            # 验证每个候选SQL
            for sql_candidate in sql_candidates:
                if not sql_candidate:
                    continue

                validation_result = self.strict_validator.comprehensive_validation(
                    optimized_question, sql_candidate, intent_analysis
                )

                # 记录生成统计
                self.generation_stats[f'round_{retry_round}'] += 1

                # 更新最佳结果
                if validation_result['confidence'] > best_confidence:
                    best_confidence = validation_result['confidence']
                    best_sql = sql_candidate
                    best_validation = validation_result

                # 如果达到超高置信度，立即返回
                if validation_result['confidence'] >= 95 and validation_result['passed']:
                    self.logger.info(f"达到超高置信度 {validation_result['confidence']}%，立即返回")
                    self.record_success(optimized_question, best_sql, best_confidence)
                    return best_sql

            # 检查是否应该继续
            if best_confidence >= self.confidence_threshold and best_validation and best_validation['passed']:
                self.logger.info(f"达到置信度阈值 {best_confidence}%，停止重试")
                break

            # 错误模式学习和修正
            if retry_round > 0 and best_sql and best_validation:
                correction = self.error_learner.suggest_enhanced_correction(
                    optimized_question, best_sql, str(best_validation.get('issues', []))
                )
                if correction and correction['confidence'] > 80:
                    self.logger.info(f"应用增强修正，置信度: {correction['confidence']}")
                    # 在下一轮中使用修正建议

            time.sleep(0.3)  # 避免API限制

        # 记录最终结果
        if best_sql and best_validation and best_validation['passed']:
            self.record_success(optimized_question, best_sql, best_confidence)
        elif best_sql:
            self.record_attempt(optimized_question, best_sql, best_confidence, best_validation)

        return best_sql or "ERROR: 无法生成满足要求的SQL"

    def generate_with_multiple_strategies(self, question, intent_analysis):
        """多策略生成"""
        system_prompt = self.build_ultimate_system_prompt(question, intent_analysis)
        relevant_examples = self.select_highly_relevant_examples(question, intent_analysis)

        strategies_results = self.multi_strategy_generator.generate_with_multiple_strategies(
            question, system_prompt, relevant_examples
        )

        # 提取和清理SQL
        sql_candidates = []
        for result in strategies_results:
            sql = self.extract_sql_from_response(result)
            if sql and self.validate_sql_basics(sql):
                sql_candidates.append(sql)

        return sql_candidates

    def generate_with_best_strategy(self, question, intent_analysis, retry_round):
        """使用最佳策略生成"""
        system_prompt = self.build_ultimate_system_prompt(question, intent_analysis)

        # 根据轮次选择策略
        if retry_round % 3 == 0:
            result = self.multi_strategy_generator.step_by_step_generation(question, system_prompt)
        elif retry_round % 3 == 1:
            result = self.multi_strategy_generator.schema_based_generation(question, system_prompt)
        else:
            relevant_examples = self.select_highly_relevant_examples(question, intent_analysis)
            result = self.multi_strategy_generator.example_based_generation(question, system_prompt, relevant_examples)

        sql = self.extract_sql_from_response(result)
        return sql if sql and self.validate_sql_basics(sql) else None

    def validate_sql_basics(self, sql):
        """基础SQL验证"""
        if not sql or not sql.strip():
            return False

        sql_upper = sql.upper()

        # 基本语法检查
        if not sql_upper.startswith('SELECT'):
            return False

        if 'FROM' not in sql_upper:
            return False

        # 危险操作检查
        dangerous_ops = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE', 'TRUNCATE']
        if any(op in sql_upper for op in dangerous_ops):
            return False

        return True

    def record_success(self, question, sql, confidence):
        """记录成功"""
        self.error_learner.add_success_pattern(question, sql, confidence)
        self.validation_results[question] = {
            'sql': sql,
            'confidence': confidence,
            'status': 'success'
        }

    def record_attempt(self, question, sql, confidence, validation):
        """记录尝试"""
        if validation and validation.get('issues'):
            confidence_impact = 100 - confidence
            self.error_learner.add_error_pattern(
                question, sql, "", "validation_failed",
                "; ".join(validation['issues']), confidence_impact
            )

        self.validation_results[question] = {
            'sql': sql,
            'confidence': confidence,
            'status': 'partial' if confidence >= 70 else 'failed',
            'validation': validation
        }

    def process_excel_file(self, file_path, start_row, start_col, output_col, num_questions, sheet_name=None):
        """处理Excel文件"""
        try:
            workbook = load_workbook(file_path)
            if sheet_name:
                worksheet = workbook[sheet_name]
            else:
                worksheet = workbook.active

            self.logger.info(f"开始超高准确率处理: {file_path}")

            processed_count = 0
            success_count = 0
            high_confidence_count = 0

            for i in range(num_questions):
                current_row = start_row + i
                question_cell = worksheet.cell(row=current_row, column=start_col)
                question = str(question_cell.value).strip() if question_cell.value else ""

                if not question:
                    continue

                self.logger.info(f"处理第{current_row}行: {question[:60]}...")

                try:
                    sql_query = self.ultra_accurate_sql_generation(question)

                    # 记录结果
                    output_cell = worksheet.cell(row=current_row, column=output_col)
                    output_cell.value = sql_query

                    processed_count += 1

                    # 统计成功情况
                    if question in self.validation_results:
                        result = self.validation_results[question]
                        if result['status'] == 'success':
                            success_count += 1
                        if result.get('confidence', 0) >= 90:
                            high_confidence_count += 1

                    # 进度保存
                    if processed_count % 3 == 0:
                        temp_file = file_path.replace('.xlsx', '_ultra_temp.xlsx')
                        workbook.save(temp_file)
                        self.logger.info(
                            f"进度保存: {processed_count} 问题，成功率: {success_count / processed_count * 100:.1f}%")

                    time.sleep(0.5)  # 控制处理速度

                except Exception as e:
                    self.logger.error(f"第{current_row}行处理失败: {str(e)}")
                    output_cell = worksheet.cell(row=current_row, column=output_col)
                    output_cell.value = f"ERROR: {str(e)}"

            # 保存最终结果
            output_file = file_path.replace('.xlsx', '_ultra_accurate.xlsx')
            workbook.save(output_file)

            # 保存详细报告
            self.save_detailed_report(output_file.replace('.xlsx', '_report.json'))

            success_rate = success_count / processed_count * 100 if processed_count > 0 else 0
            high_confidence_rate = high_confidence_count / processed_count * 100 if processed_count > 0 else 0

            self.logger.info(
                f"处理完成! 总数: {processed_count}, 成功率: {success_rate:.1f}%, 高置信度: {high_confidence_rate:.1f}%")

            return {
                'processed_count': processed_count,
                'success_count': success_count,
                'success_rate': success_rate,
                'high_confidence_rate': high_confidence_rate,
                'output_file': output_file
            }

        except Exception as e:
            self.logger.error(f"Excel处理失败: {e}")
            raise

    def save_detailed_report(self, file_path):
        """保存详细报告"""
        report = {
            'validation_results': self.validation_results,
            'generation_stats': dict(self.generation_stats),
            'error_stats': dict(self.error_learner.error_stats),
            'timestamp': time.time()
        }

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            self.logger.info(f"详细报告已保存: {file_path}")
        except Exception as e:
            self.logger.error(f"保存报告失败: {e}")

    def process_single_question(self, question):
        """处理单个问题"""
        start_time = time.time()

        try:
            sql_query = self.ultra_accurate_sql_generation(question)
            processing_time = time.time() - start_time

            result = {
                'question': question,
                'sql_query': sql_query,
                'processing_time': processing_time,
                'status': 'success'
            }

            if question in self.validation_results:
                validation_info = self.validation_results[question]
                result.update({
                    'confidence': validation_info.get('confidence', 0),
                    'validation_status': validation_info.get('status', 'unknown')
                })

            return result

        except Exception as e:
            return {
                'question': question,
                'error': str(e),
                'processing_time': time.time() - start_time,
                'status': 'error'
            }


# 使用示例
def main():
    API_KEY = "sk-ccaa87bceda64383a44a36bd0c60c32b"
    CONFIG_DIR = "config"

    if not os.path.exists(CONFIG_DIR):
        print(f"配置目录 '{CONFIG_DIR}' 不存在")
        return

    # 创建超高准确率实例
    ultra_sql = UltraAccurateTextToSQL(API_KEY, CONFIG_DIR)

    # 配置参数
    ultra_sql.confidence_threshold = 90  # 超高置信度阈值
    ultra_sql.max_retry_rounds = 8
    ultra_sql.enable_semantic_rewrite = True
    ultra_sql.enable_multi_strategy = True

    # 在这里修改文件路径
    EXCEL_FILE = r"question.xlsx" # 修改为你的实际文件路径
    START_ROW = 2
    START_COL = 2
    OUTPUT_COL = 3
    NUM_QUESTIONS = 25

    print("开始超高准确率SQL生成...")
    result = ultra_sql.process_excel_file(
        file_path=EXCEL_FILE,
        start_row=START_ROW,
        start_col=START_COL,
        output_col=OUTPUT_COL,
        num_questions=NUM_QUESTIONS
    )

    print(f"超高准确率处理完成: {result}")


def test_ultra_accuracy():
    """测试超高准确率"""
    API_KEY = "sk-ccaa87bceda64383a44a36bd0c60c32b"
    CONFIG_DIR = "config"

    ultra_sql = UltraAccurateTextToSQL(API_KEY, CONFIG_DIR)
    ultra_sql.confidence_threshold = 90

    test_questions = [
        "2024-2025供暖季用热量最多的5个换热站是哪5个？",
        "查询2024年1月1日当天所有热源厂的总供热量",
        "找出2024年供暖季平均温度最高的3个换热站",
        "统计2024年各热源厂的累计供热量",
        "查询2024年12月1日到2024年12月31日期间，每个换热站的用热量排名"
    ]

    print("=== 超高准确率测试 ===")

    for i, question in enumerate(test_questions, 1):
        print(f"\n--- 测试问题 {i} ---")
        print(f"问题: {question}")

        start_time = time.time()
        result = ultra_sql.process_single_question(question)
        end_time = time.time()

        print(f"处理时间: {end_time - start_time:.2f}秒")
        print(f"SQL: {result['sql_query']}")

        if 'confidence' in result:
            print(f"置信度: {result['confidence']}%")
            print(f"状态: {result['validation_status']}")

        if result['status'] == 'error':
            print(f"错误: {result['error']}")


if __name__ == "__main__":
    # 运行主程序
    main()

    # 测试超高准确率
    # test_ultra_accuracy()
