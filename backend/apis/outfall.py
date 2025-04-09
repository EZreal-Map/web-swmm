from fastapi import APIRouter, HTTPException
from swmm_api import SwmmInput
from swmm_api.input_file.sections import Outfall
from swmm_api.input_file.sections.node_component import Coordinate
from swmm_api.input_file.sections import Junction
from swmm_api.input_file.sections.link import Conduit
from swmm_api.input_file.sections.link_component import CrossSection

from utils.coordinate_converter import utm_to_wgs84, wgs84_to_utm
from schemas.outfall import OutfallModel
from schemas.result import Result

import numpy as np

outfallRouter = APIRouter()

SWMM_FILE_PATH = "./swmm/swmm_test.inp"


@outfallRouter.get(
    "/outfalls",
    response_model=list[OutfallModel],
    summary="获取所有出口的坐标",
    description="获取所有出口的坐标",
)
async def get_outfalls():
    try:
        INP = SwmmInput.read_file(SWMM_FILE_PATH, encoding="GB2312")
        inp_outfalls = INP.check_for_section(Outfall)
        inp_coordinates = INP.check_for_section(Coordinate)
        outfalls = [
            OutfallModel(
                name=outfall.name,
                lon=lon,
                lat=lat,
                elevation=outfall.elevation,
                kind=outfall.kind,
                data=outfall.data if outfall.kind == "FIXED" else None,
            )
            for outfall in inp_outfalls.values()
            if (coord := inp_coordinates.get(outfall.name))
            and (lon_lat := utm_to_wgs84(coord.x, coord.y))
            and (lon := lon_lat[0])
            and (lat := lon_lat[1])
        ]
        return outfalls
    except Exception as e:
        # 捕获异常并返回错误信息
        raise HTTPException(
            status_code=e.status_code if hasattr(e, "status_code") else 500,
            detail=f"{str(e.detail) if hasattr(e, 'detail') else '获取失败，文件有误，发生未知错误'}",
        )


@outfallRouter.put(
    "/outfall/{outfall_id:path}",
    summary="更新指定出口的坐标",
    description="通过指定出口ID，更新出口的相关信息",
)
async def update_outfall(outfall_id: str, outfall_update: OutfallModel):
    try:
        INP = SwmmInput.read_file(SWMM_FILE_PATH, encoding="GB2312")
        inp_outfalls = INP.check_for_section(Outfall)
        inp_coordinates = INP.check_for_section(Coordinate)
        inp_junctions = INP.check_for_section(Junction)
        inp_conduits = INP.check_for_section(Conduit)

        # 检查出口是否存在，如果不存在，则抛出异常
        if outfall_id not in inp_outfalls:
            raise HTTPException(
                status_code=404,
                detail=f"保存失败，需要修改的出口名称 [ {outfall_id} ] 不存在，请检查出口名称是否正确",
            )
        # 检查新名称是否已存在，如果新名称与现有节点名称冲突，则抛出异常
        if outfall_update.name in inp_outfalls and outfall_update.name != outfall_id:
            raise HTTPException(
                status_code=400,
                detail=f"保存失败，出口名称 [ {outfall_update.name} ] 已存在，请使用其他名称",
            )
        if outfall_update.name in inp_junctions:
            raise HTTPException(
                status_code=400,
                detail=f"保存失败，出口名称与节点名称不能重复，请使用其他名称",
            )
        if outfall_update.name in inp_coordinates and outfall_update.name != outfall_id:
            raise HTTPException(
                status_code=400,
                detail=f"保存失败，坐标名称 [ {outfall_update.name} ] 已存在，请使用其他名称",
            )

        # 1.更新OUTFALLS数据
        del inp_outfalls[outfall_id]

        inp_outfalls[outfall_update.name] = Outfall(
            name=outfall_update.name,
            elevation=outfall_update.elevation,
            kind=outfall_update.kind,
            data=outfall_update.data if outfall_update.kind == "FIXED" else np.nan,
        )

        # 2.更新坐标数据
        del inp_coordinates[outfall_id]
        utm_x, utm_y = wgs84_to_utm(outfall_update.lon, outfall_update.lat)
        inp_coordinates[outfall_update.name] = Coordinate(
            node=outfall_update.name, x=utm_x, y=utm_y
        )

        # 3.更新CONDUITS的起点和终点的名称
        # 如果出口名称发生变化，则需要更新所有与该节点相关的渠道的出口和终点名称
        if outfall_id != outfall_update.name:
            for conduit in inp_conduits.values():
                if conduit.from_node == outfall_id:
                    conduit.from_node = outfall_update.name
                elif conduit.to_node == outfall_id:
                    conduit.to_node = outfall_update.name

        INP.write_file(SWMM_FILE_PATH, encoding="GB2312")
        return Result.success(
            message=f"出口 [ {outfall_update.name} ] 更新成功",
            data={"id": outfall_update.name, "type": "outfall"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=e.status_code if hasattr(e, "status_code") else 500,
            detail=f"{str(e.detail) if hasattr(e, 'detail') else '修改失败，发生未知错误'}",
        )


@outfallRouter.post(
    "/outfall",
    summary="创建新的出口节点",
    description="在 SWMM 模型中创建一个新的 Outfall，并更新坐标数据",
)
async def create_outfall(outfall_data: OutfallModel):
    try:
        INP = SwmmInput.read_file(SWMM_FILE_PATH, encoding="GB2312")
        inp_outfalls = INP.check_for_section(Outfall)
        inp_coordinates = INP.check_for_section(Coordinate)
        inp_junctions = INP.check_for_section(Junction)

        # 检查出口是否已存在
        if outfall_data.name in inp_outfalls or outfall_data.name in inp_coordinates:
            raise HTTPException(
                status_code=400,
                detail=f"出口 [ {outfall_data.name} ] 已存在",
            )
        # 检查出口名是否与现有节点名称冲突
        if outfall_data.name in inp_junctions:
            raise HTTPException(
                status_code=400,
                detail=f"保存失败，出口名称与节点名称不能重复，请使用其他名称",
            )

        # 1. 创建新的 Outfall 并添加到 OUTFALLS
        inp_outfalls[outfall_data.name] = Outfall(
            name=outfall_data.name,
            elevation=outfall_data.elevation,
            kind=outfall_data.kind,
            data=outfall_data.data if outfall_data.kind == "FIXED" else np.nan,
        )

        # 2. 计算 UTM 坐标并创建 Coordinate
        utm_x, utm_y = wgs84_to_utm(outfall_data.lon, outfall_data.lat)
        inp_coordinates[outfall_data.name] = Coordinate(
            node=outfall_data.name, x=utm_x, y=utm_y
        )

        INP.write_file(SWMM_FILE_PATH, encoding="GB2312")
        return Result.success(
            message="出口创建成功", data={"outfall_id": outfall_data.name}
        )
    except Exception as e:
        raise HTTPException(
            status_code=e.status_code if hasattr(e, "status_code") else 500,
            detail=f"{str(e.detail) if hasattr(e, 'detail') else '删除失败，发生未知错误'}",
        )


@outfallRouter.delete(
    "/outfall/{outfall_id:path}",
    summary="删除指定出口",
    description="通过出口ID删除出口，并清理关联的坐标数据",
    response_model=Result,
)
async def delete_outfall(outfall_id: str):
    try:
        INP = SwmmInput.read_file(SWMM_FILE_PATH, encoding="GB2312")
        inp_outfalls = INP.check_for_section(Outfall)
        inp_coordinates = INP.check_for_section(Coordinate)
        inp_conduits = INP.check_for_section(Conduit)
        inp_xsections = INP.check_for_section(CrossSection)

        # 检查出口是否存在，如果不存在，则抛出异常
        if outfall_id not in inp_outfalls:
            raise HTTPException(
                status_code=404,
                detail=f"删除失败，出口 [ {outfall_id} ] 不存在",
            )

        # 1. 检查关联渠道并记录
        related_conduits = [
            conduit.name
            for conduit in inp_conduits.values()
            if conduit.from_node == outfall_id or conduit.to_node == outfall_id
        ]

        # 2. 删除关联渠道（强制级联删除）
        for conduit_id in related_conduits:
            del inp_conduits[conduit_id]
            # 删除断面信息（如果存在）
            if conduit_id in inp_xsections:
                del inp_xsections[conduit_id]

        # 3. 删除节点数据
        del inp_outfalls[outfall_id]

        # 4. 删除坐标数据
        if outfall_id in inp_coordinates:
            del inp_coordinates[outfall_id]

        INP.write_file(SWMM_FILE_PATH, encoding="GB2312")

        # 构建响应信息
        message = f"节点 [ {outfall_id} ] 删除成功"
        if related_conduits:
            message += f"，同时删除 {len(related_conduits)} 条关联渠道"

        return Result.success(message=message)
    except Exception as e:
        raise HTTPException(
            status_code=e.status_code if hasattr(e, "status_code") else 500,
            detail=f"{str(e.detail) if hasattr(e, 'detail') else '删除失败，发生未知错误'}",
        )
