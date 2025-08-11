from fastapi import APIRouter, HTTPException
from swmm_api import SwmmInput
from swmm_api.input_file.sections.others import Transect
from swmm_api.input_file.sections.link_component import CrossSection
from schemas.transect import TransectModel
from schemas.result import Result
from utils.swmm_constant import (
    SWMM_FILE_INP_PATH,
    ENCODING,
)
from utils.utils import with_exception_handler


transectsRouter = APIRouter()


# 获取所有不规则断面信息的name集合
@transectsRouter.get(
    "/transects/name",
    summary="获取所有不规则断面的名称列表",
    description="获取所有不规则断面的名称列表（不包含数据）",
)
@with_exception_handler(default_message="获取失败，文件有误，发生未知错误")
async def get_transect_names():
    INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    inp_transects = INP.check_for_section(Transect)
    transect_names = list(inp_transects.keys())
    return Result.success(
        message=f"成功获取所有断面名称，共({len(transect_names)}个)",
        data=transect_names,
    )


# 通过断面名称获取不规则断面信息
@transectsRouter.get(
    "/transect/{transect_id:path}",
    summary="获取指定不规则断面信息",
    description="""
通过指定规则断面名称，获取该不规则断面的所有相关信息，包括：

- `name`：断面名称
- `roughness_left`：左岸糙率（float，默认 0.1）
- `roughness_right`：右岸糙率（float，默认 0.1）
- `roughness_channel`：主槽糙率（float，默认 0.1）
- `bank_station_left`：左岸编号（float，默认 0）
- `bank_station_right`：右岸编号（float，默认 0）
- `station_elevations`：断面坐标高程点列表，每个元素为 `[Y, X]` 坐标点（单位为米），用于绘制断面图，自动按 X 升序排序

注意：
- `station_elevations` 中的坐标点必须为二维数组，点的坐标值必须为非负数，格式为 `[[y1, x1], [y2, x2], ...]`
- 所有糙率和编号必须为非负数值，否则将返回格式化的错误提示
""",
)
@with_exception_handler(default_message="获取失败，文件有误，发生未知错误")
async def get_transect(transect_id: str):
    INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    inp_transects = INP.check_for_section(Transect)
    transect = inp_transects.get(transect_id)
    if not transect:
        raise HTTPException(status_code=404, detail=f"断面 [ {transect_id} ] 不存在")
    transect_model = TransectModel(
        name=transect.name,
        roughness_left=transect.roughness_left,
        roughness_right=transect.roughness_right,
        roughness_channel=transect.roughness_channel,
        bank_station_left=transect.bank_station_left,
        bank_station_right=transect.bank_station_right,
        station_elevations=transect.station_elevations,
    )
    return Result.success(message="成功获取断面信息", data=transect_model)


@transectsRouter.get(
    "/transects",
    summary="获取所有不规则断面信息",
    description="获取所有不规则断面信息",
    deprecated=True,
)
@with_exception_handler(default_message="获取失败，文件有误，发生未知错误")
async def get_transects():
    INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    inp_transects = INP.check_for_section(Transect)
    transects = {}
    for transect in inp_transects.values():
        transect_model = TransectModel(
            name=transect.name,
            roughness_left=transect.roughness_left,
            roughness_right=transect.roughness_right,
            roughness_channel=transect.roughness_channel,
            bank_station_left=transect.bank_station_left,
            bank_station_right=transect.bank_station_right,
            station_elevations=transect.station_elevations,
        )
        transects[transect.name] = transect_model
    return transects


@transectsRouter.put(
    "/transect/{transect_id:path}",
    summary="更新指定断面的相关信息",
    description="通过指定断面ID，更新断面的相关信息",
)
@with_exception_handler(default_message="更新失败，文件有误，发生未知错误")
async def update_transect(transect_id: str, transect: TransectModel):
    INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    inp_transects = INP.check_for_section(Transect)
    inp_xsections = INP.check_for_section(CrossSection)
    if transect_id not in inp_transects:
        raise HTTPException(status_code=404, detail="修改失败，断面不存在")
    if transect.name in inp_transects and transect.name != transect_id:
        raise HTTPException(status_code=400, detail="修改失败，断面名称已存在")

    transect.station_elevations
    # 更新断面信息
    del inp_transects[transect_id]
    transect_model = Transect(
        name=transect.name,
        station_elevations=transect.station_elevations,
        bank_station_left=transect.bank_station_left,
        bank_station_right=transect.bank_station_right,
        roughness_left=transect.roughness_left,
        roughness_right=transect.roughness_right,
        roughness_channel=transect.roughness_channel,
    )
    inp_transects[transect.name] = transect_model

    # 如果断面名字修改以后，还需要修改渠道引用的断面名字信息
    related_xsections = []
    if transect_id != transect.name:
        for xsection in inp_xsections.values():
            if xsection.transect == transect_id:
                xsection.transect = transect.name
                related_xsections.append(xsection.link)
    # 构建响应信息
    message = f"断面更新成功"
    if len(related_xsections) > 0:
        message += f"，同时更新了 {len(related_xsections)} 条引用"

    # 保存更新后的文件
    INP.write_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    return Result.success(
        message=message,
        data={"id": transect.name, "related_xsections": related_xsections},
    )


@transectsRouter.post(
    "/transect",
    summary="创建新的不规则断面",
    description="创建新的不规则断面",
)
@with_exception_handler(default_message="创建失败，文件有误，发生未知错误")
async def create_transect(transect: TransectModel):
    INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    inp_transects = INP.check_for_section(Transect)

    # 检查断面名称是否已存在
    if transect.name in inp_transects:
        raise HTTPException(
            status_code=400,
            detail=f"创建失败，断面名称 [ {transect.name} ] 已存在，请使用不同的断面名称",
        )

    # 创建新的不规则断面
    transect_model = Transect(
        name=transect.name,
        station_elevations=transect.station_elevations,
        bank_station_left=transect.bank_station_left,
        bank_station_right=transect.bank_station_right,
        roughness_left=transect.roughness_left,
        roughness_right=transect.roughness_right,
        roughness_channel=transect.roughness_channel,
    )
    inp_transects[transect.name] = transect_model

    # 保存更新后的文件
    INP.write_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    return Result.success(message="创建成功", data=transect)


@transectsRouter.delete(
    "/transect/{transect_id:path}",
    summary="删除指定断面",
    description="通过断面ID删除断面",
)
@with_exception_handler(default_message="删除失败，文件有误，发生未知错误")
async def delete_transect(transect_id: str):
    INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    inp_transects = INP.check_for_section(Transect)
    inp_xsections = INP.check_for_section(CrossSection)
    # 检查断面是否存在
    if transect_id not in inp_transects:
        raise HTTPException(status_code=404, detail="删除失败，断面不存在")
    # 检查是否有渠道引用该断面
    related_xsections = [
        xsection.link
        for xsection in inp_xsections.values()
        if xsection.transect == transect_id
    ]
    if related_xsections:
        raise HTTPException(
            status_code=400,
            detail=f"删除失败，断面 [ {transect_id} ] 被 {len(related_xsections)} 条渠道引用，请先取消引用再删除，渠道名称为：{related_xsections}",
        )
    del inp_transects[transect_id]
    INP.write_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    return Result.success(message="删除成功", data={"id": transect_id})
