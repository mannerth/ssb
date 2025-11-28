import json
import logging
import re
import time
from typing import Dict, Optional, Callable
import threading

from .analyzer import QuestionAnalyzer
from .llm_client import LLMClient
from .prompt_builder import PromptBuilder


class SQLGenerationWorkflow:
    def __init__(
        self,
        llm_client: LLMClient,
        prompt_builder: PromptBuilder,
        analyzer: QuestionAnalyzer,
        confidence_threshold: int = 75,
        max_retry_rounds: int = 10,
        validation_temperature: float = 0.1,
        validation_max_tokens: int = 4000,
        confidence_repeat_count: int = 3,
        confidence_variation_threshold: int = 3,
        stop_event: Optional[threading.Event] = None,
        status_callback: Optional[Callable[[str], None]] = None,
    ):
        self.llm_client = llm_client
        self.prompt_builder = prompt_builder
        self.analyzer = analyzer
        self.confidence_threshold = confidence_threshold
        self.max_retry_rounds = max_retry_rounds
        self.validation_temperature = validation_temperature
        self.validation_max_tokens = validation_max_tokens
        self.confidence_repeat_count = confidence_repeat_count
        self.confidence_variation_threshold = confidence_variation_threshold
        self.stop_event = stop_event or threading.Event()
        self.status_callback = status_callback
        self.validation_results: Dict[str, Dict[str, Dict]] = {}
        self.logger = logging.getLogger(__name__)

    def set_validation_parameters(self, confidence_threshold: Optional[int] = None, max_retry_rounds: Optional[int] = None):
        if confidence_threshold is not None:
            self.confidence_threshold = confidence_threshold
        if max_retry_rounds is not None:
            self.max_retry_rounds = max_retry_rounds

    def _clean_sql(self, sql_query: str) -> str:
        """验证和清理SQL语句，确保只包含SELECT查询"""
        # 移除Markdown代码块标记
        sql_query = sql_query.replace('```sql', '').replace('```', '').strip()

        # 检查是否包含危险的SQL操作
        dangerous_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE', 'TRUNCATE']
        sql_upper = sql_query.upper()

        for keyword in dangerous_keywords:
            if keyword in sql_upper and f'SELECT' not in sql_upper:
                raise ValueError(f"生成的SQL包含危险操作: {keyword}，只允许SELECT查询")
        return sql_query

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

    def _generate_sql(
        self,
        question: str,
        analysis: str,
        previous_sql: Optional[str] = None,
        validation_feedback: Optional[str] = None,
    ) -> str:
        messages = [{"role": "system", "content": self.prompt_builder.build_system_prompt()}]
        if previous_sql and validation_feedback:
            user_content = self.prompt_builder.build_retry_prompt(question, analysis, previous_sql, validation_feedback)
        else:
            user_content = self.prompt_builder.build_generation_prompt(question, analysis)
        messages.append({"role": "user", "content": user_content})
        sql_query = self.llm_client.chat(messages)
        return self._clean_sql(sql_query)

    def _validate_sql(self, question: str, sql_query: str) -> Dict:
        messages = [
            {"role": "system", "content": self.prompt_builder.build_validation_prompt(question, sql_query)},
            {"role": "user", "content": "请按既定格式返回验证结果。"},
        ]
        response = self.llm_client.chat(
            messages,
            temperature=self.validation_temperature,
            max_tokens=self.validation_max_tokens,
        )
        confidence_match = re.search(r"置信度:\s*(\d+)", response)
        analysis_match = re.search(r"问题分析:\s*(.*?)(?=改进建议:|$)", response, re.DOTALL)
        suggestion_match = re.search(r"改进建议:\s*(.*)", response, re.DOTALL)
        confidence = int(confidence_match.group(1)) if confidence_match else 0
        analysis = analysis_match.group(1).strip() if analysis_match else "未提供分析"
        suggestion = suggestion_match.group(1).strip() if suggestion_match else "无建议"
        feedback = f"置信度: {confidence}%\n问题分析: {analysis}\n改进建议: {suggestion}"
        return {
            "confidence": confidence,
            "analysis": analysis,
            "suggestion": suggestion,
            "feedback": feedback,
            "passed": confidence >= self.confidence_threshold,
            "full_response": response,
        }

    def generate_sql_with_validation(self, question: str) -> str:
        if self.status_callback:
            self.status_callback("环节: 正在分析问题...")
        analysis = self.analyzer.analyze(question)
        retry_round = 0
        question_results = []
        last_val_s:int = 0
        same_s_repeat_count = 0
        while retry_round < self.max_retry_rounds:
            if self.stop_event.is_set():
                self.logger.warning("任务被用户中断。")
                break

            self.logger.info("问题《%s》- 第 %s 轮生成与验证", question, retry_round + 1)

            if self.status_callback:
                self.status_callback(f"环节: [第{retry_round + 1}/{self.max_retry_rounds}轮] 正在生成SQL...")

            previous_sql = question_results[-1]["sql"] if question_results else None
            feedback = question_results[-1]["validation"]["feedback"] if question_results else None
            sql_query = self._generate_sql(question, analysis, previous_sql, feedback)
            time.sleep(0.1)

            if self.status_callback:
                self.status_callback(f"环节: [第{retry_round + 1}/{self.max_retry_rounds}轮] 正在评估SQL...")

            validation = self._validate_sql(question, sql_query)
            self.logger.info(
                "评估置信度: %s, 当前重试轮数: %s/%s",
                validation.get("confidence", "N/A"),
                retry_round + 1,
                self.max_retry_rounds,
            )
            question_results.append({"sql": sql_query, "validation": validation, "round": retry_round + 1})
            if validation["passed"]:
                self.logger.info("采纳SQL: %s", sql_query)
                break

            if validation["confidence"] == last_val_s and self.confidence_threshold - last_val_s <= self.confidence_variation_threshold:
                same_s_repeat_count += 1
                if same_s_repeat_count >= self.confidence_repeat_count:
                    self.logger.warning(
                        "置信度连续 %s 次未提升且在 %s 分差范围内(%s), 提前采纳当前SQL。",
                        self.confidence_repeat_count,
                        self.confidence_variation_threshold,
                        validation["confidence"],
                    )
                    self.logger.info("采纳SQL: %s", sql_query)
                    break
            else:
                last_val_s = validation["confidence"]
                same_s_repeat_count = 1


            # # 检查置信度是否在容差范围内重复n次
            # if len(question_results) >= self.confidence_repeat_count:
            #     recent_confidences = [
            #         res["validation"]["confidence"] for res in question_results[-self.confidence_repeat_count:]
            #     ]
            #     # 计算最大值和最小值的差
            #     confidence_range = max(recent_confidences) - min(recent_confidences)
            #     if confidence_range <= self.confidence_variation_threshold:
            #         self.logger.warning(
            #             "置信度在 %s 分差范围内连续重复 %s 次(%s), 提前采纳当前SQL。",
            #             self.confidence_variation_threshold,
            #             self.confidence_repeat_count,
            #             recent_confidences,
            #         )
            #         self.logger.info("采纳SQL: %s", sql_query)
            #         break

            retry_round += 1
            time.sleep(0.3)
        self.validation_results[question] = question_results[-1] if question_results else {}
        return question_results[-1]["sql"] if question_results else "ERROR: 未生成 SQL"

    def save_validation_details(self, file_path: str):
        with open(file_path, "w", encoding="utf-8") as fp:
            json.dump(self.validation_results, fp, ensure_ascii=False, indent=2, default=str)
