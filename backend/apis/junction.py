from fastapi import APIRouter, HTTPException
from swmm_api import SwmmInput
from swmm_api.input_file.sections import Junction
from swmm_api.input_file.sections.node_component import Coordinate
from swmm_api.input_file.sections.link import Conduit
from swmm_api.input_file.sections.link_component import CrossSection
from swmm_api.input_file.sections import Outfall


from utils.coordinate_converter import utm_to_wgs84, wgs84_to_utm
from schemas.junction import JunctionModel
from schemas.result import Result

junctionsRouter = APIRouter()

SWMM_FILE_PATH = "./swmm/swmm_test.inp"


@junctionsRouter.get(
    "/junctions",
    response_model=list[JunctionModel],
    summary="获取所有节点的坐标",
    description="获取所有节点的坐标",
)
async def get_junctions():
    try:
        INP = SwmmInput.read_file(SWMM_FILE_PATH, encoding="GB2312")
        inp_junctions = INP.check_for_section(Junction)
        inp_coordinates = INP.check_for_section(Coordinate)

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
            for junction in inp_junctions.values()
            if (coord := inp_coordinates.get(junction.name))
            and (lon_lat := utm_to_wgs84(coord.x, coord.y))
            and (lon := lon_lat[0])
            and (lat := lon_lat[1])
        ]

        return junctions
    except Exception as e:
        # 捕获异常并返回错误信息
        raise HTTPException(
            status_code=e.status_code if hasattr(e, "status_code") else 500,
            detail=f"{str(e.detail) if hasattr(e, 'detail') else '获取失败，发生未知错误'}",
        )


@junctionsRouter.put(
    "/junction/{junction_id}",
    summary="更新指定节点的坐标",
    description="通过指定节点id，更新节点的相关信息",
)
async def update_junction(junction_id: str, junction_update: JunctionModel):

    try:

        INP = SwmmInput.read_file(SWMM_FILE_PATH, encoding="GB2312")
        inp_junctions = INP.check_for_section(Junction)
        inp_coordinates = INP.check_for_section(Coordinate)
        inp_conduits = INP.check_for_section(Conduit)
        inp_outfalls = INP.check_for_section(Outfall)

        # 检查节点ID是否存在
        if junction_id not in inp_junctions:
            raise HTTPException(
                status_code=404,
                detail=f"保存失败，需要修改的节点名称 [ {junction_id} ] 不存在，请检查节点名称是否正确",
            )

        # 检查新名称是否已存在，如果新名称与现有节点名称冲突，则抛出异常
        if (
            junction_update.name in inp_junctions
            and junction_update.name != junction_id
        ):
            raise HTTPException(
                status_code=400,
                detail=f"修改失败，节点名称 [ {junction_update.name} ] 已存在，请使用不同的节点名称",
            )
        if junction_update.name in inp_outfalls:
            raise HTTPException(
                status_code=400,
                detail=f"保存失败，节点名称与出口名称不能重复，请使用其他名称",
            )
        if (
            junction_update.name in inp_coordinates
            and junction_update.name != junction_id
        ):
            raise HTTPException(
                status_code=400,
                detail=f"保存失败，坐标名称 [ {junction_update.name} ] 已存在，请使用不同的节点名称",
            )

        # 1.更新JUNCTIONS数据
        del inp_junctions[junction_id]
        inp_junctions[junction_update.name] = Junction(
            name=junction_update.name,
            elevation=junction_update.elevation,
            depth_max=junction_update.depth_max,
            depth_init=junction_update.depth_init,
            depth_surcharge=junction_update.depth_surcharge,
            area_ponded=junction_update.area_ponded,
        )

        # 2.更新COORDINATES数据
        del inp_coordinates[junction_id]
        utm_x, utm_y = wgs84_to_utm(junction_update.lon, junction_update.lat)
        inp_coordinates[junction_update.name] = Coordinate(
            node=junction_update.name, x=utm_x, y=utm_y
        )

        # 3.更新CONDUITS的起点和终点的名称
        # 如果节点名称发生变化，则需要更新所有与该节点相关的管道的起点和终点名称
        if junction_id != junction_update.name:
            for conduit in inp_conduits.values():
                if conduit.from_node == junction_id:
                    conduit.from_node = junction_update.name
                elif conduit.to_node == junction_id:
                    conduit.to_node = junction_update.name

        # 4.保存数据到文件
        INP.write_file(
            SWMM_FILE_PATH,
            encoding="GB2312",
        )
        return Result.success(
            message=f"节点 [ {junction_update.name} ] 信息更新成功",
            data={"id": junction_update.name, "type": "junction"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=e.status_code if hasattr(e, "status_code") else 500,
            detail=f"{str(e.detail) if hasattr(e, 'detail') else '修改失败，发生未知错误'}",
        )


@junctionsRouter.post(
    "/junction",
    summary="创建新的 Junction 节点",
    description="在 SWMM 模型中创建一个新的 Junction，并更新坐标数据",
)
async def create_junction(junction_data: JunctionModel):
    try:
        # 读取 SWMM 输入文件
        INP = SwmmInput.read_file(SWMM_FILE_PATH, encoding="GB2312")
        inp_junctions = INP.check_for_section(Junction)
        inp_coordinates = INP.check_for_section(Coordinate)
        inp_outfalls = INP.check_for_section(Outfall)

        # 检查节点是否已存在
        if junction_data.name in inp_junctions or junction_data.name in inp_coordinates:
            raise HTTPException(
                status_code=400,
                detail=f"创建失败，节点名称 [ {junction_data.name} ] 已存在，请使用不同的名称",
            )
        if junction_data.name in inp_outfalls:
            raise HTTPException(
                status_code=400,
                detail=f"保存失败，节点名称与出口名称不能重复，请使用其他名称",
            )

        # 1. 创建新的 Junction 并添加到 JUNCTIONS
        inp_junctions[junction_data.name] = Junction(
            name=junction_data.name,
            elevation=junction_data.elevation,
            depth_max=junction_data.depth_max,
            depth_init=junction_data.depth_init,
            depth_surcharge=junction_data.depth_surcharge,
            area_ponded=junction_data.area_ponded,
        )

        # 2. 计算 UTM 坐标并创建 Coordinate
        utm_x, utm_y = wgs84_to_utm(junction_data.lon, junction_data.lat)
        new_coordinate = Coordinate(
            node=junction_data.name,
            x=utm_x,
            y=utm_y,
        )
        inp_coordinates[junction_data.name] = new_coordinate

        # 3. 写回 SWMM 输入文件
        INP.write_file(SWMM_FILE_PATH, encoding="GB2312")

        return Result.success(
            message=f"节点创建成功",
            data={"junction_id": junction_data.name},
        )
    except Exception as e:
        raise HTTPException(
            status_code=e.status_code if hasattr(e, "status_code") else 500,
            detail=f"{str(e.detail) if hasattr(e, 'detail') else '创建失败，发生未知错误'}",
        )


@junctionsRouter.delete(
    "/junction/{junction_id}",
    summary="删除指定节点",
    description="通过节点ID删除节点，并清理关联的管道和坐标数据",
    response_model=Result,
)
async def delete_junction(junction_id: str):
    try:
        INP = SwmmInput.read_file(SWMM_FILE_PATH, encoding="GB2312")
        inp_junctions = INP.check_for_section(Junction)
        inp_coordinates = INP.check_for_section(Coordinate)
        inp_conduits = INP.check_for_section(Conduit)
        inp_xsections = INP.check_for_section(CrossSection)

        # 检查节点是否存在
        if junction_id not in inp_junctions:
            raise HTTPException(
                status_code=404, detail=f"删除失败，节点 [ {junction_id} ] 不存在"
            )

        # 1. 检查关联管道并记录
        related_conduits = [
            conduit.name
            for conduit in inp_conduits.values()
            if conduit.from_node == junction_id or conduit.to_node == junction_id
        ]

        # 2. 删除关联管道（强制级联删除）
        for conduit_id in related_conduits:
            del inp_conduits[conduit_id]
            # 删除断面信息（如果存在）
            if conduit_id in inp_xsections:
                del inp_xsections[conduit_id]

        # 3. 删除节点数据
        del inp_junctions[junction_id]

        # 4. 删除坐标数据
        if junction_id in inp_coordinates:
            del inp_coordinates[junction_id]

        # 保存修改
        INP.write_file(SWMM_FILE_PATH, encoding="GB2312")

        # 构建响应信息
        message = f"节点 [ {junction_id} ] 删除成功"
        if related_conduits:
            message += f"，同时删除 {len(related_conduits)} 条关联管道"
        return Result.success(message=message)
    except Exception as e:
        raise HTTPException(
            status_code=e.status_code if hasattr(e, "status_code") else 500,
            detail=f"{str(e.detail) if hasattr(e, 'detail') else '删除失败，发生未知错误'}",
        )
