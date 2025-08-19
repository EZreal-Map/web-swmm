import os
from langgraph.store.postgres.aio import AsyncPostgresStore, PoolConfig

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from utils.logger import app_logger


DB_URI = f"postgresql://{os.getenv('DB_USER', 'postgres')}:{os.getenv('DB_PASSWORD', 'postgres')}@{os.getenv('DB_HOST', 'postgres')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'postgres')}?connect_timeout=2"


# 线程池配置(连接池)
POOL_CONFIG = PoolConfig(min_size=5, max_size=20)


# 手动调用 aenter(),并把返回值赋给 cls.store,最后在 close 时手动 aexit()。
# 本质上和 async with 是一样的,只是你自己管理生命周期,容易出错(比如忘记 close、异常时没释放)
# 优点是: 可以更灵活地控制资源的生命周期,不用频繁的初始化,创建连接
class AsyncStoreManager:
    store: AsyncPostgresStore = None
    checkpointer: AsyncPostgresSaver = None
    _initialized: bool = False

    @classmethod
    async def init(cls):
        if cls._initialized:
            app_logger.info("AsyncStoreManager 已初始化,跳过重复初始化。")
            return
        app_logger.info("AsyncStoreManager 开始初始化全局 store/checkpointer...")
        try:
            store_cm = AsyncPostgresStore.from_conn_string(
                DB_URI, pool_config=POOL_CONFIG
            )
            cls.store = await store_cm.__aenter__()
            # checkpointer 只支持单连接(不支持 pool_config),因为 checkpoint 写入通常是串行的,且更安全。
            checkpointer_cm = AsyncPostgresSaver.from_conn_string(DB_URI)
            cls.checkpointer = await checkpointer_cm.__aenter__()
            await cls.store.setup()
            await cls.checkpointer.setup()
            cls._initialized = True
            cls._store_cm = store_cm
            cls._checkpointer_cm = checkpointer_cm
            app_logger.info("AsyncStoreManager 初始化完成！")
        except Exception as e:
            app_logger.error(f"AsyncStoreManager 初始化失败: {e}")
            raise

    @classmethod
    async def close(cls):
        app_logger.info("AsyncStoreManager 开始关闭全局 store/checkpointer...")
        try:
            if hasattr(cls, "_store_cm") and cls.store:
                await cls._store_cm.__aexit__(None, None, None)
                cls.store = None
            if hasattr(cls, "_checkpointer_cm") and cls.checkpointer:
                await cls._checkpointer_cm.__aexit__(None, None, None)
                cls.checkpointer = None
            cls._initialized = False
            app_logger.info("AsyncStoreManager 关闭完成！")
        except Exception as e:
            app_logger.error(f"AsyncStoreManager 关闭失败: {e}")
            raise


# 一、手动 aenter/aexit 的优缺点 优点:

# 生命周期灵活:你可以在全局/单例场景下只初始化一次,整个应用期间都复用同一个连接池/资源,避免频繁创建和销毁(比如 FastAPI lifespan、全局 manager)。
# 适合需要"全局持久资源"的场景,比如数据库连接池、缓存等,减少初始化开销。
# 可以手动控制何时初始化、何时关闭,适合和应用生命周期(如 FastAPI 的 startup/shutdown)绑定。
# 缺点:

# 容易出错:如果忘记调用 close(aexit),或者异常时没有释放资源,会导致连接泄漏、资源未释放。
# 代码复杂度高:需要自己保证异常安全和资源释放,容易遗漏。
# 不适合局部/短生命周期场景:比如只在一个函数/请求内用一次,手动管理反而繁琐。
# 二、async with 的优缺点 优点:

# 自动管理资源:进入 async with 自动 aenter,退出自动 aexit,即使抛异常也能保证资源释放。
# 代码简洁、安全,异常安全性高。
# 适合"用完即释放"的场景,比如临时用一个连接、文件、锁等。
# 缺点:

# 生命周期短:出了 with 块资源就被释放,不适合全局/单例场景。
# 如果频繁创建/销毁,可能有性能损耗(比如频繁新建连接池)。
# 三、总结

# 你的用法(手动 aenter/aexit)适合全局单例、长生命周期资源,优点是只初始化一次,性能好,灵活。
# async with 适合局部、短生命周期,优点是安全、简洁、异常友好。
# 只要你能保证异常时也能正确 close,手动管理是合理且常见的做法(比如 FastAPI lifespan、Django AppConfig 等场景)。
# 建议:全局资源用手动管理,局部用 async with,始终注意异常安全和资源释放。
