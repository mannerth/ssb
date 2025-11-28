import logging
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMConfig:
    api_key: str
    base_url: str
    model: str
    temperature: float
    max_tokens: int
    max_retries: int


@dataclass
class WorkflowConfig:
    confidence_threshold: int
    max_retry_rounds: int
    validation_temperature: float
    validation_max_tokens: int
    confidence_repeat_count: int
    confidence_variation_threshold: int


@dataclass
class ExcelConfig:
    file_path: str
    start_row: int
    start_col: int
    output_col: int
    num_questions: int
    sheet_name: str


@dataclass
class LoggingConfig:
    log_dir: str
    log_name: str
    level: int
    level_str: Optional[str] = field(default="INFO", init=False)

    def __post_init__(self):
        self.level_str = logging.getLevelName(self.level)


@dataclass
class AppSettings:
    llm: LLMConfig
    workflow: WorkflowConfig
    excel: ExcelConfig
    config_dir: str
    training_file_path: str
    logging: LoggingConfig


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    try:
        return int(float(os.getenv(name, default)))
    except ValueError:
        return default


def _log_level_env(name: str, default: str) -> int:
    raw = os.getenv(name, default)
    if raw.isdigit():
        return int(raw)
    return getattr(logging, raw.upper(), logging.INFO)


def load_settings() -> AppSettings:
    llm = LLMConfig(
        api_key=os.getenv(
            "DEEPSEEK_API_KEY",
        ),
        base_url=os.getenv(
            "DEEPSEEK_BASE_URL",
            #"https://www.ssfssp.com:8888/ssp/openApi/GkfFhhUy/kvshB4Rh/LNslKxsF/v1"
            "https://api.deepseek.com/v1"
        ),
        model=os.getenv(
            "DEEPSEEK_MODEL",
            #"DeepSeek-V3"
            "deepseek-chat"
        ),
        temperature=_float_env("GENERATION_TEMPERATURE", 0.1),
        max_tokens=_int_env("GENERATION_MAX_TOKENS", 3000),
        max_retries=_int_env("GENERATION_MAX_RETRIES", 5),
    )
    workflow = WorkflowConfig(
        confidence_threshold=_int_env("CONFIDENCE_THRESHOLD", 90),# 阈值
        max_retry_rounds=_int_env("MAX_RETRY_ROUNDS", 20),# 最大重试
        validation_temperature=_float_env("VALIDATION_TEMPERATURE", 0.1),
        validation_max_tokens=_int_env("VALIDATION_MAX_TOKENS", 4000),
        confidence_repeat_count=_int_env("CONFIDENCE_REPEAT_COUNT", 5),# 重复跳出
        confidence_variation_threshold=_int_env("CONFIDENCE_VARIATION_THRESHOLD", 30),# 允许分差
    )
    excel = ExcelConfig(
        file_path=os.getenv("EXCEL_INPUT_FILE"),
        start_row=_int_env("EXCEL_START_ROW", 2),
        start_col=_int_env("EXCEL_START_COL", 2),
        output_col=_int_env("EXCEL_OUTPUT_COL", 3),
        num_questions=_int_env("EXCEL_NUM_QUESTIONS", 25),
        sheet_name=os.getenv("EXCEL_SHEET_NAME", "Sheet1"),
    )
    logging_cfg = LoggingConfig(
        log_dir=os.getenv("LOG_DIR", "logs"),
        log_name=os.getenv("LOG_NAME", "validation"),
        level=_log_level_env("LOG_LEVEL", "INFO"),
    )
    return AppSettings(
        llm=llm,
        workflow=workflow,
        excel=excel,
        config_dir=os.getenv("APP_CONFIG_DIR", "config"),
        training_file_path=os.getenv("TRAINING_FILE", "data/算法训练集（75道问题及sql语句）.xlsx"),
        logging=logging_cfg,
    )
