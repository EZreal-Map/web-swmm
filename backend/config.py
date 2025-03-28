from typing import List


class Config:
    # 调试模式
    APP_DEBUG: bool = True
    # 项目信息
    VERSION: str = "0.0.1"
    PROJECT_NAME: str = "SWMM API"
    DESCRIPTION: str = "使用swmm-api处理swmm文件的后端程序"
    # 静态资源目录
    # STATIC_DIR: str = os.path.join(os.getcwd(), "static")
    # 跨域请求
    CORS_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
