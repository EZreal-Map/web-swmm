from fastapi import FastAPI
from config import Config
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 路由
from apis.coordinate import coordinatesRouter
from apis.conduit import conduitRouter

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
application.include_router(coordinatesRouter, prefix="/swmm", tags=["节点"])
application.include_router(conduitRouter, prefix="/swmm", tags=["管道"])


if __name__ == "__main__":
    uvicorn.run("app:application", host="127.0.0.1", port=8080, reload=True)
