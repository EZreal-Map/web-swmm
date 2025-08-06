"""
SWMM API 配置管理
分模块的配置系统：系统配置、日志配置、数据库配置
"""

import os
from typing import List, Optional
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


def parse_cors_origins() -> List[str]:
    """解析 CORS origins"""
    origins = os.getenv("CORS_ORIGINS", "*")
    if origins == "*":
        return ["*"]
    return [origin.strip() for origin in origins.split(",")]


def parse_cors_list(env_key: str, default: str = "*") -> List[str]:
    """解析 CORS 列表配置"""
    value = os.getenv(env_key, default)
    if value == "*":
        return ["*"]
    return [item.strip() for item in value.split(",")]


class SystemConfig:
    """系统配置 - FastAPI 相关配置"""

    # ==================== 项目元信息 ====================
    VERSION: str = "0.0.1"
    PROJECT_NAME: str = "SWMM API"
    DESCRIPTION: str = "使用swmm-api处理swmm文件的后端程序"

    # ==================== 应用配置 ====================
    APP_DEBUG: bool = os.getenv("APP_DEBUG", "false").lower() == "true"

    # ==================== 服务器配置 ====================
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8080"))

    # ==================== CORS配置 ====================
    CORS_ORIGINS: List[str] = parse_cors_origins()
    CORS_ALLOW_CREDENTIALS: bool = (
        os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() == "true"
    )
    CORS_ALLOW_METHODS: List[str] = parse_cors_list("CORS_ALLOW_METHODS")
    CORS_ALLOW_HEADERS: List[str] = parse_cors_list("CORS_ALLOW_HEADERS")

    @classmethod
    def get_server_url(cls) -> str:
        """获取完整的服务器URL"""
        return f"http://{cls.HOST}:{cls.PORT}"

    @classmethod
    def print_config(cls) -> None:
        """打印系统配置"""
        print("🔧 系统配置 (FastAPI):")
        print("=" * 50)
        print(f"📊 项目: {cls.PROJECT_NAME} v{cls.VERSION}")
        print(f"📝 描述: {cls.DESCRIPTION}")
        print(f"🐛 热启动: {cls.RELOAD}")
        print(f"🌐 服务器: {cls.get_server_url()}")
        print(f"🔄 CORS Origins: {cls.CORS_ORIGINS}")
        print(f"🔐 CORS Credentials: {cls.CORS_ALLOW_CREDENTIALS}")
        print("=" * 50)


class LoggerConfig:
    """日志配置"""

    # ==================== 日志级别配置 ====================
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # ==================== 文件日志配置 ====================
    ENABLE_FILE_LOGGING: bool = (
        os.getenv("ENABLE_FILE_LOGGING", "true").lower() == "true"
    )
    LOG_DIR: str = os.getenv("LOG_DIR", "logs")
    LOG_FILENAME: str = os.getenv("LOG_FILENAME", "app.log")

    # ==================== 日志轮转配置 ====================
    LOG_FILE_MAX_SIZE_MB: int = int(os.getenv("LOG_FILE_MAX_SIZE_MB", "10"))
    LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "5"))

    # ==================== 第三方库日志级别 ====================
    WATCHFILES_LOG_LEVEL: str = os.getenv("WATCHFILES_LOG_LEVEL", "WARNING")
    UVICORN_LOG_LEVEL: str = os.getenv("UVICORN_LOG_LEVEL", "ERROR")
    UVICORN_ACCESS_LOG_LEVEL: str = os.getenv("UVICORN_ACCESS_LOG_LEVEL", "CRITICAL")
    FASTAPI_LOG_LEVEL: str = os.getenv("FASTAPI_LOG_LEVEL", "ERROR")

    @classmethod
    def get_log_file_path(cls) -> str:
        """获取完整的日志文件路径"""
        return os.path.join(cls.LOG_DIR, cls.LOG_FILENAME)

    @classmethod
    def get_max_bytes(cls) -> int:
        """获取日志文件最大字节数"""
        return cls.LOG_FILE_MAX_SIZE_MB * 1024 * 1024

    @classmethod
    def print_config(cls) -> None:
        """打印日志配置"""
        print("📝 日志配置:")
        print("=" * 50)
        print(f"📊 日志级别: {cls.LOG_LEVEL}")
        print(f"📁 日志目录: {cls.LOG_DIR}")
        print(f"📄 日志文件: {cls.LOG_FILENAME}")
        print(f"🗂️ 完整路径: {cls.get_log_file_path()}")
        print(f"📏 文件大小限制: {cls.LOG_FILE_MAX_SIZE_MB}MB")
        print(f"🗃️ 备份文件数: {cls.LOG_BACKUP_COUNT}")
        print(f"📤 文件日志: {'启用' if cls.ENABLE_FILE_LOGGING else '禁用'}")
        print("=" * 50)


class DatabaseConfig:
    """数据库配置"""

    # ==================== 数据库基础配置 ====================
    DB_TYPE: str = os.getenv("DB_TYPE", "postgresql")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "")

    # ==================== 连接池配置 ====================
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))

    @classmethod
    def get_database_url(cls) -> str:
        return (
            f"{cls.DB_TYPE}://{cls.DB_USER}:{cls.DB_PASSWORD}@"
            f"{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
        )

    @classmethod
    def get_connection_params(cls) -> dict:
        """获取数据库连接参数字典"""
        return {
            "host": cls.DB_HOST,
            "port": cls.DB_PORT,
            "user": cls.DB_USER,
            "password": cls.DB_PASSWORD,
            "dbname": cls.DB_NAME,
        }

    @classmethod
    def print_config(cls) -> None:
        """打印数据库配置"""
        print("🗄️ 数据库配置:")
        print("=" * 50)
        print(f"🔗 数据库类型: {cls.DB_TYPE}")
        print(f"🌐 主机: {cls.DB_HOST}:{cls.DB_PORT}")
        print(f"👤 用户: {cls.DB_USER}")
        print(f"🗃️ 数据库: {cls.DB_NAME}")
        print(f"🔐 密码: {'***' if cls.DB_PASSWORD else '未设置'}")
        print(f"🏊 连接池大小: {cls.DB_POOL_SIZE}")
        print(f"📈 最大溢出: {cls.DB_MAX_OVERFLOW}")
        print(f"⏱️ 连接超时: {cls.DB_POOL_TIMEOUT}s")
        print(f"🔗 连接字符串: {cls.get_database_url()}")
        print("=" * 50)


# 用于测试配置
if __name__ == "__main__":
    print("🔧 完整配置信息:")
    print("=" * 60)
    SystemConfig.print_config()
    LoggerConfig.print_config()
    DatabaseConfig.print_config()
