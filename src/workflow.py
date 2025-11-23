import json
import logging
import re
import time
from typing import Dict, Optional

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
        consecutive_confidence_stagnation_limit: int = 3,
    ):
        self.llm_client = llm_client
        self.prompt_builder = prompt_builder
        self.analyzer = analyzer
        self.confidence_threshold = confidence_threshold
        self.max_retry_rounds = max_retry_rounds
        self.validation_temperature = validation_temperature
        self.validation_max_tokens = validation_max_tokens
        self.consecutive_confidence_stagnation_limit = consecutive_confidence_stagnation_limit
        self.validation_results: Dict[str, Dict[str, Dict]] = {}
        self.logger = logging.getLogger(__name__)

    def set_validation_parameters(self, confidence_threshold: Optional[int] = None, max_retry_rounds: Optional[int] = None):
        if confidence_threshold is not None:
            self.confidence_threshold = confidence_threshold
        if max_retry_rounds is not None:
            self.max_retry_rounds = max_retry_rounds

    def _clean_sql(self, sql_query: str) -> str:
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        if not sql_query.upper().startswith("SELECT"):
            select_idx = sql_query.upper().find("SELECT")
            if select_idx == -1:
                raise ValueError("生成内容未包含 SELECT 语句")
            sql_query = sql_query[select_idx:]
        return sql_query

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
        analysis = self.analyzer.analyze(question)
        retry_round = 0
        question_results = []
        while retry_round < self.max_retry_rounds:
            self.logger.info("问题《%s》- 第 %s 轮生成与验证", question, retry_round + 1)
            previous_sql = question_results[-1]["sql"] if question_results else None
            feedback = question_results[-1]["validation"]["feedback"] if question_results else None
            sql_query = self._generate_sql(question, analysis, previous_sql, feedback)
            time.sleep(0.1)
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

            # 检查置信度是否连续N轮停滞
            if len(question_results) >= self.consecutive_confidence_stagnation_limit:
                recent_confidences = [
                    res["validation"]["confidence"] for res in question_results[-self.consecutive_confidence_stagnation_limit:]
                ]
                if len(set(recent_confidences)) == 1:
                    self.logger.warning(
                        "置信度连续 %s 轮停滞在 %s, 提前采纳当前SQL。",
                        self.consecutive_confidence_stagnation_limit,
                        recent_confidences[0],
                    )
                    self.logger.info("采纳SQL: %s", sql_query)
                    break

            retry_round += 1
            time.sleep(0.3)
        self.validation_results[question] = question_results[-1] if question_results else {}
        return question_results[-1]["sql"] if question_results else "ERROR: 未生成 SQL"

    def save_validation_details(self, file_path: str):
        with open(file_path, "w", encoding="utf-8") as fp:
            json.dump(self.validation_results, fp, ensure_ascii=False, indent=2, default=str)
