from fastapi import APIRouter, HTTPException
from swmm_api import SwmmInput
from swmm_api.input_file.sections import RainGage, Symbol
from schemas.result import Result
from utils.swmm_constant import SWMM_FILE_INP_PATH, ENCODING
from utils.utils import with_exception_handler, remove_timeseries_prefix
from apis.raingage import create_raingage, delete_raingage, update_raingage
from utils.logger import get_logger
from pydantic import BaseModel
from typing import Optional

# 获取日志记录器
logger = get_logger("raingage")

raingageRouter = APIRouter()


class RaingageModel(BaseModel):
    """雨量计数据模型"""

    name: str
    form: str = "INTENSITY"
    interval: str
    SCF: float = 1.0
    source: str = "TIMESERIES"
    timeseries: str
    x: float = 0.0
    y: float = 0.0


class RaingageUpdateModel(BaseModel):
    """雨量计更新数据模型"""

    timeseries_name: Optional[str] = None
    interval: Optional[str] = None


# 获取所有雨量计名称列表
@raingageRouter.get(
    "/raingage/name",
    summary="获取所有雨量计的名称列表",
    description="获取所有雨量计的名称列表",
)
@with_exception_handler(default_message="获取失败,文件有误,发生未知错误")
async def get_raingage_names():
    INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    inp_rain_gages = INP.check_for_section(RainGage)
    raingage_names = list(inp_rain_gages.keys())

    return Result.success_result(
        message=f"成功获取所有雨量计名称,共({len(raingage_names)}个)",
        data=raingage_names,
    )


# 通过雨量计名称获取雨量计信息
@raingageRouter.get(
    "/raingage/{raingage_id:path}",
    summary="获取指定雨量计信息",
    description="通过指定雨量计名称,获取该雨量计的相关信息",
)
@with_exception_handler(default_message="获取失败,文件有误,发生未知错误")
async def get_raingage_by_id(raingage_id: str):
    INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    inp_rain_gages = INP.check_for_section(RainGage)
    inp_symbols = INP.check_for_section(Symbol)

    raingage = inp_rain_gages.get(raingage_id)
    if not raingage:
        raise HTTPException(status_code=404, detail=f"雨量计 [ {raingage_id} ] 不存在")

    symbol = inp_symbols.get(raingage_id)

    raingage_model = RaingageModel(
        name=raingage.name,
        form=raingage.form,
        interval=raingage.interval,
        SCF=raingage.SCF,
        source=raingage.source,
        timeseries=raingage.timeseries,
        x=symbol.x if symbol else 0.0,
        y=symbol.y if symbol else 0.0,
    )

    return Result.success_result(message="成功获取雨量计信息", data=raingage_model)


# 通过雨量计id更新雨量计信息
@raingageRouter.put(
    "/raingage/{raingage_id:path}",
    summary="更新指定雨量计信息",
    description="通过指定雨量计ID,更新雨量计的相关信息",
)
@with_exception_handler(default_message="更新失败,文件有误,发生未知错误")
async def update_raingage_by_id(raingage_id: str, raingage_update: RaingageUpdateModel):
    INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    inp_rain_gages = INP.check_for_section(RainGage)

    # 检查雨量计ID是否存在
    if raingage_id not in inp_rain_gages:
        raise HTTPException(
            status_code=404,
            detail=f"保存失败,需要修改的雨量计 [ {raingage_id} ] 不存在,请检查雨量计名称是否正确",
        )

    # 构建时间序列名称
    old_timeseries_name = inp_rain_gages[raingage_id].timeseries
    new_timeseries_name = (
        raingage_update.timeseries_name
        if raingage_update.timeseries_name
        else old_timeseries_name
    )

    # 更新雨量计信息
    related_entity_ids = update_raingage(
        INP,
        timeseries_name=old_timeseries_name,
        new_timeseries_name=new_timeseries_name,
        interval=raingage_update.interval,
    )

    # 构建响应信息
    message = f"雨量计更新成功"
    if len(related_entity_ids) > 0:
        message += f",同时更新了 {len(related_entity_ids)} 条引用"

    INP.write_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    return Result.success_result(
        message=message,
        data={"id": raingage_id, "related_entity_ids": related_entity_ids},
    )


# 新建雨量计
@raingageRouter.post(
    "/raingage",
    summary="创建新的雨量计",
    description="创建一个新的雨量计,并写入 SWMM 文件",
)
@with_exception_handler(default_message="创建失败,文件有误,发生未知错误")
async def create_raingage_endpoint(raingage_data: RaingageModel):
    """
    创建雨量计信息
    """
    INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    inp_rain_gages = INP.check_for_section(RainGage)

    # 检查雨量计名称是否已存在
    name = remove_timeseries_prefix(raingage_data.timeseries)
    if name in inp_rain_gages:
        raise HTTPException(
            status_code=400,
            detail=f"创建失败,雨量计名称 [ {name} ] 已存在,请使用不同的雨量计名称",
        )

    # 创建新的雨量计
    create_raingage(
        INP,
        timeseries_name=raingage_data.timeseries,
        interval=raingage_data.interval,
        x=raingage_data.x,
        y=raingage_data.y,
        form=raingage_data.form,
        SCF=raingage_data.SCF,
    )

    INP.write_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    return Result.success_result(message="雨量计创建成功", data={"name": name})


# 通过 raingage_id 删除雨量计
@raingageRouter.delete(
    "/raingage/{raingage_id:path}",
    summary="删除指定雨量计",
    description="通过雨量计ID删除雨量计,并清理关联的数据",
)
async def delete_raingage_endpoint(raingage_id: str):
    INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    inp_rain_gages = INP.check_for_section(RainGage)

    # 检查雨量计是否存在
    if raingage_id not in inp_rain_gages:
        raise HTTPException(
            status_code=404,
            detail=f"删除失败,雨量计 [ {raingage_id} ] 不存在",
        )

    # 删除雨量计
    delete_raingage(INP, timeseries_name=raingage_id)

    # 保存修改
    INP.write_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    return Result.success_result(message="雨量计删除成功", data={"id": raingage_id})
