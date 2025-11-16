from logging import Logger
import openai
import json
import time
import os
import pandas as pd
import re
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
import config
from logger_manager import LogManager

class TextToSQL:

    def __init__(self):
        self.api_key: str = config.API_KEY
        self.base_url: str = config.DEEPSEEK_BASE_URL
        self.config_dir: str = config.data_files_path

        #日志
        self.logger: Logger = LogManager().get_logger()

        # 配置OpenAI客户端
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

        # 验证和重试参数
        self.confidence_threshold = config.PASS_LINE  # 置信度阈值，可调整 (0-100)
        self.max_retry_rounds = config.MAX_RETRY  # 最大重试轮数，可调整

        # 验证结果记录
        self.validation_results = {}