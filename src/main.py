import logging
import os

from .analyzer import QuestionAnalyzer
from .config_loader import (
    load_common_expressions,
    load_formula_descriptions,
    load_few_shot_examples,
    load_table_descriptions,
)
from .excel_processor import ExcelProcessor
from .llm_client import LLMClient
from .prompt_builder import PromptBuilder
from .settings import AppSettings, load_settings
from .workflow import SQLGenerationWorkflow

DEEPSEEK_MODEL = "DeepSeek-V3"


def build_workflow(settings: AppSettings) -> SQLGenerationWorkflow:
    formula_desc = load_formula_descriptions(settings.config_dir)
    common_expr = load_common_expressions(settings.config_dir)
    table_desc = load_table_descriptions(settings.config_dir)
    few_shot = load_few_shot_examples(settings.training_file_path)
    llm_client = LLMClient(
        api_key=settings.llm.api_key,
        base_url=settings.llm.base_url,
        model=settings.llm.model,
        max_retries=settings.llm.max_retries,
        default_temperature=settings.llm.temperature,
        default_max_tokens=settings.llm.max_tokens,
    )
    prompt_builder = PromptBuilder(table_desc, formula_desc, common_expr, few_shot)
    analyzer = QuestionAnalyzer(llm_client, prompt_builder)
    return SQLGenerationWorkflow(
        llm_client,
        prompt_builder,
        analyzer,
        confidence_threshold=settings.workflow.confidence_threshold,
        max_retry_rounds=settings.workflow.max_retry_rounds,
        validation_temperature=settings.workflow.validation_temperature,
        validation_max_tokens=settings.workflow.validation_max_tokens,
    )


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    settings = load_settings()
    if not os.path.exists(settings.config_dir):
        raise FileNotFoundError(f"配置目录不存在: {settings.config_dir}")
    workflow = build_workflow(settings)
    processor = ExcelProcessor(workflow)
    result = processor.process(
        file_path=settings.excel.file_path,
        start_row=settings.excel.start_row,
        start_col=settings.excel.start_col,
        output_col=settings.excel.output_col,
        num_questions=settings.excel.num_questions,
        sheet_name=settings.excel.sheet_name,
    )
    print(f"处理完成: {result}")


if __name__ == "__main__":
    main()
