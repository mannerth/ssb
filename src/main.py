import logging
import os
import sys
from pathlib import Path

# 添加根目录到路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.analyzer import QuestionAnalyzer
from src.config_loader import (
    load_common_expressions,
    load_formula_descriptions,
    load_few_shot_examples,
    load_table_descriptions,
)
from src.excel_processor import ExcelProcessor
from src.llm_client import LLMClient
from src.prompt_builder import PromptBuilder
from src.settings import (
    AppSettings,
    ExcelConfig,
    LLMConfig,
    LoggingConfig,
    WorkflowConfig,
    load_settings,
)
from src.workflow import SQLGenerationWorkflow
from src.logger_manager import setup_logging

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
        confidence_repeat_count=settings.workflow.confidence_repeat_count,
        confidence_variation_threshold=settings.workflow.confidence_variation_threshold,
    )


def main():
    settings = load_settings()
    
    # 转绝对路径
    project_root = Path(__file__).parent.parent
    
    # 修正配置路径
    if not os.path.isabs(settings.config_dir):
        config_dir = project_root / settings.config_dir
    else:
        config_dir = Path(settings.config_dir)
    
    # 修正训练文件路径
    if not os.path.isabs(settings.training_file_path):
        training_file_path = project_root / settings.training_file_path
    else:
        training_file_path = Path(settings.training_file_path)
    
    # 修正 Excel 路径
    if not os.path.isabs(settings.excel.file_path):
        excel_file_path = project_root / settings.excel.file_path
    else:
        excel_file_path = Path(settings.excel.file_path)
    
    # 修正日志路径
    if not os.path.isabs(settings.logging.log_dir):
        log_dir = project_root / settings.logging.log_dir
    else:
        log_dir = Path(settings.logging.log_dir)
    
    # 更新 settings 对象
    updated_settings = AppSettings(
        llm=settings.llm,
        workflow=settings.workflow,
        excel=ExcelConfig(
            file_path=str(excel_file_path),
            start_row=settings.excel.start_row,
            start_col=settings.excel.start_col,
            output_col=settings.excel.output_col,
            num_questions=settings.excel.num_questions,
            sheet_name=settings.excel.sheet_name,
        ),
        config_dir=str(config_dir),
        training_file_path=str(training_file_path),
        logging=LoggingConfig(
            log_dir=str(log_dir),
            log_name=settings.logging.log_name,
            level=settings.logging.level,
        ),
    )
    
    setup_logging(
        log_dir=updated_settings.logging.log_dir,
        log_name=updated_settings.logging.log_name,
        level=updated_settings.logging.level,
    )
    logger = logging.getLogger(__name__)
    if not os.path.exists(updated_settings.config_dir):
        raise FileNotFoundError(f"配置目录不存在: {updated_settings.config_dir}")
    workflow = build_workflow(updated_settings)
    processor = ExcelProcessor(workflow)
    result = processor.process(
        file_path=updated_settings.excel.file_path,
        start_row=updated_settings.excel.start_row,
        start_col=updated_settings.excel.start_col,
        output_col=updated_settings.excel.output_col,
        num_questions=updated_settings.excel.num_questions,
        sheet_name=updated_settings.excel.sheet_name,
    )
    logger.info("处理完成: %s", result)
    print(f"处理完成: {result}")


if __name__ == "__main__":
    main()
