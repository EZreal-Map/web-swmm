import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from config import LoggerConfig


class ColoredFormatter(logging.Formatter):
    """带颜色的控制台日志格式器"""

    # ANSI颜色代码
    COLORS = {
        "DEBUG": "\033[36m",  # 青色
        "INFO": "\033[32m",  # 绿色
        "WARNING": "\033[33m",  # 黄色
        "ERROR": "\033[31m",  # 红色
        "CRITICAL": "\033[35m",  # 紫色
        "RESET": "\033[0m",  # 重置
    }

    def format(self, record):
        # 保存原始级别名
        original_levelname = record.levelname

        # 添加颜色
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"

        # 格式化消息
        formatted = super().format(record)

        # 恢复原始级别名
        record.levelname = original_levelname

        return formatted


def setup_logging():
    """初始化日志配置 - 只执行一次"""
    # 避免重复配置
    if hasattr(setup_logging, "_configured"):
        return
    setup_logging._configured = True
    # 创建日志目录
    log_dir = Path(LoggerConfig.LOG_DIR)
    log_dir.mkdir(exist_ok=True)

    # 设置第三方库的日志级别，减少噪音
    logging.getLogger("watchfiles").setLevel(
        getattr(logging, LoggerConfig.WATCHFILES_LOG_LEVEL)
    )
    logging.getLogger("uvicorn").setLevel(
        getattr(logging, LoggerConfig.UVICORN_LOG_LEVEL)
    )
    logging.getLogger("uvicorn.access").setLevel(
        getattr(logging, LoggerConfig.UVICORN_ACCESS_LOG_LEVEL)
    )
    logging.getLogger("fastapi").setLevel(
        getattr(logging, LoggerConfig.FASTAPI_LOG_LEVEL)
    )


def get_logger(name: str = "app") -> logging.Logger:
    """获取logger"""
    setup_logging()  # 确保已初始化

    logger = logging.getLogger(name)

    # 如果这个logger还没有配置handlers
    if not logger.handlers:
        logger.setLevel(getattr(logging, LoggerConfig.LOG_LEVEL))
        # 控制台输出 - 使用彩色格式器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, LoggerConfig.LOG_LEVEL))

        # 彩色格式器用于控制台
        colored_formatter = ColoredFormatter(
            "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(colored_formatter)
        logger.addHandler(console_handler)

        # 文件输出 - 使用轮转文件处理器（限制大小）
        if LoggerConfig.ENABLE_FILE_LOGGING:
            log_file_path = Path(LoggerConfig.get_log_file_path())

            # 使用轮转文件处理器
            file_handler = RotatingFileHandler(
                log_file_path,
                maxBytes=LoggerConfig.get_max_bytes(),
                backupCount=LoggerConfig.LOG_BACKUP_COUNT,
                encoding="utf-8",
            )
            file_handler.setLevel(getattr(logging, LoggerConfig.LOG_LEVEL))

            # 普通格式器用于文件
            file_formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

        # 防止日志向上传播到根logger
        logger.propagate = False

    return logger


# 预定义的常用logger
app_logger = get_logger("app")
api_logger = get_logger("api")
swmm_logger = get_logger("swmm")
agent_logger = get_logger("agent")
websocket_logger = get_logger("websocket")

# 导出
__all__ = ["get_logger", "app_logger", "api_logger", "swmm_logger", "agent_logger", "websocket_logger"]
