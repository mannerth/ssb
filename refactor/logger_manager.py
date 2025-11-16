import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Union


class LogManager:
    """
    日志管理工具类
    功能：每次程序运行时自动创建新的日志文件
    """

    def __init__(self,
                 log_dir: Optional[Union[str, Path]] = None,
                 log_name: Optional[str] = None,
                 level: int = logging.INFO,
                 format_string: Optional[str] = None,
                 max_file_size: int = 10 * 1024 * 1024,  # 10MB
                 backup_count: int = 5):
        """
        初始化日志管理器

        Args:
            log_dir: 日志目录路径，如果为None则使用当前目录下的logs文件夹
            log_name: 日志文件基础名称，如果为None则使用程序名称
            level: 日志级别
            format_string: 日志格式字符串
            max_file_size: 单个日志文件最大大小（字节）
            backup_count: 备份文件数量
        """
        self.log_dir = self._setup_log_dir(log_dir)
        self.log_name = log_name or self._get_default_log_name()
        self.level = level
        self.format_string = format_string or self._get_default_format()
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.logger = None
        self.current_log_file = None

    def _setup_log_dir(self, log_dir: Optional[Union[str, Path]]) -> Path:
        """设置并创建日志目录"""
        if log_dir is None:
            log_dir = Path.cwd() / "logs"
        else:
            log_dir = Path(log_dir)

        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    def _get_default_log_name(self) -> str:
        """获取默认日志名称"""
        return Path(sys.argv[0]).stem if sys.argv[0] else "app"

    def _get_default_format(self) -> str:
        """获取默认日志格式"""
        return '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'

    def _generate_log_filename(self) -> str:
        """生成唯一的日志文件名，包含时间戳"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{self.log_name}_{timestamp}.log"

    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """
        获取配置好的logger实例

        Args:
            name: logger名称，如果为None则使用基础日志名称

        Returns:
            logging.Logger: 配置好的logger实例
        """
        if self.logger is not None:
            return self.logger

        logger_name = name or self.log_name
        logger = logging.getLogger(logger_name)
        logger.setLevel(self.level)

        # 避免重复添加handler
        if logger.handlers:
            return logger

        # 生成新的日志文件
        self.current_log_file = self.log_dir / self._generate_log_filename()

        # 创建文件handler
        file_handler = logging.FileHandler(self.current_log_file, encoding='utf-8')

        # 创建控制台handler
        console_handler = logging.StreamHandler(sys.stdout)

        # 设置格式
        formatter = logging.Formatter(self.format_string)
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 添加handler到logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        self.logger = logger
        return logger

    def get_current_log_path(self) -> Optional[Path]:
        """获取当前日志文件路径"""
        return self.current_log_file

    def change_log_level(self, level: int):
        """动态修改日志级别"""
        self.level = level
        if self.logger:
            self.logger.setLevel(level)
            for handler in self.logger.handlers:
                handler.setLevel(level)

    def add_file_handler(self, filename: str, level: Optional[int] = None):
        """
        添加额外的文件handler

        Args:
            filename: 文件名
            level: 日志级别，如果为None则使用当前级别
        """
        if not self.logger:
            return

        file_path = self.log_dir / filename
        file_handler = logging.FileHandler(file_path, encoding='utf-8')
        file_handler.setLevel(level or self.level)
        formatter = logging.Formatter(self.format_string)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def cleanup_old_logs(self, days: int = 30):
        """
        清理指定天数前的旧日志文件

        Args:
            days: 保留天数
        """
        cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)

        for log_file in self.log_dir.glob(f"{self.log_name}_*.log"):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    logging.info(f"Deleted old log file: {log_file}")
                except OSError as e:
                    logging.error(f"Failed to delete {log_file}: {e}")


# 使用示例
def __demo_usage():
    """演示使用方法"""

    # 基本用法
    log_manager = LogManager()
    logger = log_manager.get_logger()

    logger.info("这是一条信息日志")
    logger.error("这是一条错误日志")

    print(f"日志文件保存在: {log_manager.get_current_log_path()}")

    # 自定义配置
    custom_manager = LogManager(
        log_dir="./custom_logs",  # 自定义日志目录
        log_name="my_app",  # 自定义日志名称
        level=logging.DEBUG,  # 调试级别
        format_string='%(asctime)s - %(levelname)s - %(message)s'  # 简化格式
    )

    custom_logger = custom_manager.get_logger()
    custom_logger.debug("调试信息")
    custom_logger.warning("警告信息")

    # 动态修改日志级别
    custom_manager.change_log_level(logging.ERROR)
    custom_logger.debug("这条日志不会显示")  # 因为级别已改为ERROR
    custom_logger.error("这条错误日志会显示")
