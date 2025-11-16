from typing import Dict

from .llm_client import LLMClient
from .prompt_builder import PromptBuilder


class QuestionAnalyzer:
    def __init__(self, llm_client: LLMClient, prompt_builder: PromptBuilder):
        self.llm_client = llm_client
        self.prompt_builder = prompt_builder
        self._cache: Dict[str, str] = {}

    def analyze(self, question: str) -> str:
        if question in self._cache:
            return self._cache[question]
        messages = [
            {"role": "system", "content": self.prompt_builder.build_analysis_prompt()},
            {"role": "user", "content": f"请分析以下问题：\n{question}"},
        ]
        analysis = self.llm_client.chat(messages, temperature=0.2, max_tokens=800)
        self._cache[question] = analysis
        return analysis

