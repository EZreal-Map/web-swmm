from fastapi import FastAPI
from config import Config
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 路由
from apis.conduit import conduitRouter
from apis.junction import junctionsRouter
from apis.outfall import outfallRouter
from apis.transect import transectsRouter
from apis.timeseries import timeseriesRouter
from apis.calculate import calculateRouter
from apis.show import showRouter

from apis.mj import mjRouter  # 岷江项目,与此项目无关

application = FastAPI(
    debug=Config.APP_DEBUG,
    description=Config.DESCRIPTION,
    version=Config.VERSION,
    title=Config.PROJECT_NAME,
)

application.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS,
    allow_credentials=Config.CORS_ALLOW_CREDENTIALS,
    allow_methods=Config.CORS_ALLOW_METHODS,
    allow_headers=Config.CORS_ALLOW_HEADERS,
)


# 路由
application.include_router(junctionsRouter, prefix="/swmm", tags=["节点"])
application.include_router(conduitRouter, prefix="/swmm", tags=["渠道"])
application.include_router(outfallRouter, prefix="/swmm", tags=["出口"])
application.include_router(transectsRouter, prefix="/swmm", tags=["不规则断面"])
application.include_router(timeseriesRouter, prefix="/swmm", tags=["时间序列"])
application.include_router(calculateRouter, prefix="/swmm", tags=["计算"])
application.include_router(showRouter, prefix="/swmm", tags=["首页滚动展示数据"])

application.include_router(mjRouter, prefix="/mj", tags=["岷江项目,与此项目无关"])


if __name__ == "__main__":
    uvicorn.run("app:application", host="0.0.0.0", port=8080, reload=True)
