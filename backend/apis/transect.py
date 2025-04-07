from fastapi import APIRouter, HTTPException
from swmm_api import SwmmInput
from swmm_api.input_file.sections.others import Transect
from swmm_api.input_file.sections.link_component import CrossSection
from schemas.transect import TransectModel
from schemas.result import Result


transectsRouter = APIRouter()

SWMM_FILE_PATH = "./swmm/swmm_test.inp"


# 获取所有不规则断面信息的name集合
@transectsRouter.get(
    "/transects/name",
    summary="获取所有不规则断面的名称",
    description="获取所有不规则断面的名称",
)
async def get_transect_names():
    INP = SwmmInput.read_file(SWMM_FILE_PATH, encoding="GB2312")
    inp_transects = INP.check_for_section(Transect)
    transect_names = list(inp_transects.keys())
    return Result.success(message="成功获取所有断面名称", data=transect_names)


# 通过断面名称获取不规则断面信息
@transectsRouter.get(
    "/transect/{transect_id}",
    summary="获取指定断面信息",
    description="通过指定断面ID，获取断面的相关信息",
)
async def get_transect(transect_id: str):
    INP = SwmmInput.read_file(SWMM_FILE_PATH, encoding="GB2312")
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
async def get_transects():
    INP = SwmmInput.read_file(SWMM_FILE_PATH, encoding="GB2312")
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
    "/transect/{transect_id}",
    summary="更新指定断面的相关信息",
    description="通过指定断面ID，更新断面的相关信息",
)
async def update_transect(transect_id: str, transect: TransectModel):
    try:
        INP = SwmmInput.read_file(SWMM_FILE_PATH, encoding="GB2312")
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
            message += (
                f"，同时更新了 {len(related_xsections)} 条引用该断面的渠道的断面名称"
            )

        # 保存更新后的文件
        INP.write_file(SWMM_FILE_PATH, encoding="GB2312")
        return Result.success(
            message=message,
            data={"id": transect.name, "related_xsections": related_xsections},
        )
    except Exception as e:
        raise HTTPException(
            status_code=e.status_code if hasattr(e, "status_code") else 500,
            detail=f"{str(e.detail) if hasattr(e, 'detail') else '保存失败，发生未知错误'}",
        )


@transectsRouter.post(
    "/transect",
    summary="创建新的不规则断面",
    description="创建新的不规则断面",
)
async def create_transect(transect: TransectModel):
    try:
        INP = SwmmInput.read_file(SWMM_FILE_PATH, encoding="GB2312")
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
        INP.write_file(SWMM_FILE_PATH, encoding="GB2312")
        return Result.success(message="创建成功", data=transect)
    except Exception as e:
        raise HTTPException(
            status_code=e.status_code if hasattr(e, "status_code") else 500,
            detail=f"{str(e.detail) if hasattr(e, 'detail') else '创建失败，发生未知错误'}",
        )


@transectsRouter.delete(
    "/transect/{transect_id}",
    summary="删除指定断面",
    description="通过断面ID删除断面",
)
async def delete_transect(transect_id: str):
    try:
        INP = SwmmInput.read_file(SWMM_FILE_PATH, encoding="GB2312")
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
        INP.write_file(SWMM_FILE_PATH, encoding="GB2312")
        return Result.success(message="删除成功", data={"id": transect_id})
    except Exception as e:
        raise HTTPException(
            status_code=e.status_code if hasattr(e, "status_code") else 500,
            detail=f"{str(e.detail) if hasattr(e, 'detail') else '删除失败，发生未知错误'}",
        )
