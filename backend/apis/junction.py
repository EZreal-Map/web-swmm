from fastapi import APIRouter, HTTPException
from swmm_api import SwmmInput

from utils.coordinate_converter import utm_to_wgs84, wgs84_to_utm
from schemas.junction import JunctionModel
from schemas.result import Result

junctionsRouter = APIRouter()

# 全局变量，存储节点数据和坐标数据
# 方便在不同的API中共享数据
junctions_data = {}
coordinates_data = {}


@junctionsRouter.get(
    "/junctions",
    response_model=list[JunctionModel],
    summary="获取所有节点的坐标",
    description="获取所有节点的坐标",
)
async def get_junctions():
    SWMM_FILE_PATH = "./swmm/swmm_test.inp"
    inp = SwmmInput.read_file(SWMM_FILE_PATH, encoding="GB2312")
    junctions_data = inp.JUNCTIONS
    coordinates_data = inp.COORDINATES

    # 用列表推导式，提高效率
    junctions = [
        JunctionModel(
            name=junction.name,
            lon=lon,
            lat=lat,
            elevation=junction.elevation,
            depth_max=junction.depth_max,
            depth_init=junction.depth_init,
            depth_surcharge=junction.depth_surcharge,
            area_ponded=junction.area_ponded,
        )
        for junction in junctions_data.values()
        if (coord := coordinates_data.get(junction.name))
        and (lon_lat := utm_to_wgs84(coord.x, coord.y))
        and (lon := lon_lat[0])
        and (lat := lon_lat[1])
    ]

    return junctions


@junctionsRouter.put(
    "/junction/{junction_id}",
    summary="更新指定节点的坐标",
    description="通过指定节点id，更新节点的相关信息",
)
async def update_junction(junction_id: str, junction_update: JunctionModel):
    SWMM_FILE_PATH = "./swmm/swmm_test.inp"
    inp = SwmmInput.read_file(SWMM_FILE_PATH, encoding="GB2312")
    junctions_data = inp.JUNCTIONS
    coordinates_data = inp.COORDINATES

    # 检查节点ID是否存在
    if junction_id not in junctions_data:
        raise HTTPException(
            status_code=404,
            detail=f"修改失败，需要修改的节点名称({junction_id})不存在，请检查节点名称是否正确",
        )

    # 检查新名称是否已存在，如果新名称与现有节点名称冲突，则抛出异常
    if junction_update.name in junctions_data and junction_update.name != junction_id:
        raise HTTPException(
            status_code=400,
            detail=f"修改失败，节点名称 '{junction_update.name}' 已存在，请使用不同的节点名称",
        )
    if junction_update.name in coordinates_data and junction_update.name != junction_id:
        raise HTTPException(
            status_code=400,
            detail=f"修改失败，坐标名称 '{junction_update.name}' 已存在，请使用不同的节点名称",
        )
    try:
        # 1.更新JUNCTIONS数据
        junction = junctions_data.pop(junction_id)
        junctions_data[junction_update.name] = junction
        junction.name = junction_update.name
        junction.elevation = junction_update.elevation
        junction.depth_max = junction_update.depth_max
        junction.depth_init = junction_update.depth_init
        junction.depth_surcharge = junction_update.depth_surcharge
        junction.area_ponded = junction_update.area_ponded

        # 2.更新COORDINATES数据
        coordinate = coordinates_data.pop(junction_id)
        coordinates_data[junction_update.name] = coordinate
        coordinate.node = junction_update.name
        coordinate.x, coordinate.y = wgs84_to_utm(
            junction_update.lon, junction_update.lat
        )

        # 3.更新CONDUITS的起点和终点的名称
        # 如果节点名称发生变化，则需要更新所有与该节点相关的管道的起点和终点名称
        if junction_id != junction_update.name:
            for conduit in inp.CONDUITS.values():
                if conduit.from_node == junction_id:
                    conduit.from_node = junction_update.name
                elif conduit.to_node == junction_id:
                    conduit.to_node = junction_update.name

        # 4.保存数据到文件
        inp.write_file(
            SWMM_FILE_PATH,
            encoding="GB2312",
        )
        return Result.success(message=f"节点({junction_id})信息更新成功")
    except Exception as e:
        return Result.error(message=f"更新失败，发生未知错误: {str(e)}")
