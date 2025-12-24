from fastapi import FastAPI, Request
from config import SystemConfig
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import time
from utils.logger import app_logger, api_logger
from contextlib import asynccontextmanager
from utils.agent.async_store_manager import AsyncStoreManager
from utils.agent.graph_manager import GraphInstance

# 路由
from apis.conduit import conduitRouter
from apis.junction import junctionsRouter
from apis.outfall import outfallRouter
from apis.transect import transectsRouter
from apis.timeseries import timeseriesRouter
from apis.raingage_router import raingageRouter
from apis.calculate import calculateRouter
from apis.subcatchment import subcatchment
from apis.agent.chat import chatRouter
from apis.show import showRouter


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_logger.info("正在启动后端API服务...")
    # 初始化异步全局StoreManager(异步)
    await AsyncStoreManager.init()  # (不要Agent功能，想要不报错，可以注释掉)
    # 初始Graph实例
    GraphInstance.init()  # (不要Agent功能，想要不报错，可以注释掉)
    yield
    app_logger.info("正在关闭后端API服务...")
    # 关闭异步全局StoreManager
    await AsyncStoreManager.close()  # (不要Agent功能，想要不报错，可以注释掉)


application = FastAPI(
    debug=SystemConfig.APP_DEBUG,
    description=SystemConfig.DESCRIPTION,
    version=SystemConfig.VERSION,
    title=SystemConfig.PROJECT_NAME,
    lifespan=lifespan,
)

application.add_middleware(
    CORSMiddleware,
    allow_origins=SystemConfig.CORS_ORIGINS,
    allow_credentials=SystemConfig.CORS_ALLOW_CREDENTIALS,
    allow_methods=SystemConfig.CORS_ALLOW_METHODS,
    allow_headers=SystemConfig.CORS_ALLOW_HEADERS,
)


# 请求日志中间件
@application.middleware("http")
async def log_requests(request: Request, call_next):
    """简单的请求日志记录"""
    start_time = time.time()

    response = await call_next(request)

    duration = (time.time() - start_time) * 1000
    api_logger.info(
        f"{request.method} {request.url.path} - {response.status_code} - {duration:.1f}ms"
    )

    return response


# 路由
# SWMM相关路由
application.include_router(junctionsRouter, prefix="/swmm", tags=["节点"])
application.include_router(conduitRouter, prefix="/swmm", tags=["渠道"])
application.include_router(outfallRouter, prefix="/swmm", tags=["出口"])
application.include_router(transectsRouter, prefix="/swmm", tags=["不规则断面"])
application.include_router(timeseriesRouter, prefix="/swmm", tags=["时间序列"])
application.include_router(raingageRouter, prefix="/swmm", tags=["雨量计"])
application.include_router(calculateRouter, prefix="/swmm", tags=["计算"])
application.include_router(subcatchment, prefix="/swmm", tags=["子汇水区域"])

application.include_router(showRouter, prefix="/swmm", tags=["首页滚动展示数据"])
# agent相关路由
application.include_router(chatRouter, prefix="/agent", tags=["agent聊天"])

if __name__ == "__main__":
    uvicorn.run(
        "app:application",
        host=SystemConfig.HOST,
        port=SystemConfig.PORT,
        reload=SystemConfig.APP_DEBUG,  # 根据配置决定是否热启动
        access_log=False,  # 禁用uvicorn的访问日志,使用我们的中间件
    )
