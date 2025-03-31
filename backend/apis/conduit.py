from fastapi import APIRouter, HTTPException
from swmm_api import SwmmInput
from swmm_api.input_file.sections.node_component import Coordinate
from swmm_api.input_file.sections.link import Conduit
from swmm_api.input_file.sections.link_component import CrossSection
from schemas.conduit import ConduitResponseModel, ConduitRequestModel
from schemas.result import Result

# TODO 修改post 和 put 中的创建和更新的逻辑（使用Conduit类和CrossSection类）

conduitRouter = APIRouter()
SWMM_FILE_PATH = "./swmm/swmm_test.inp"


@conduitRouter.get(
    "/conduits",
    summary="获取所有管道信息",
    description="获取所有管道信息",
)
async def get_conduits():
    """
    获取坐标
    """
    INP = SwmmInput.read_file(SWMM_FILE_PATH, encoding="GB2312")
    inp_conduits = INP.check_for_section(Conduit)
    inp_xsections = INP.check_for_section(CrossSection)
    conduits = []
    for conduit in inp_conduits.values():
        xsection = inp_xsections.get(conduit.name)
        print(f"xsection: {xsection.shape}")
        conduit_model = ConduitResponseModel(
            name=conduit.name,
            from_node=conduit.from_node,
            to_node=conduit.to_node,
            length=conduit.length,
            roughness=conduit.roughness,
            transect=xsection.transect,
            shape=xsection.shape,
            height=xsection.height,
            parameter_2=xsection.parameter_2,
            parameter_3=xsection.parameter_3,
            parameter_4=xsection.parameter_4,
        )
        print(f"conduit_model: {conduit_model}")
        conduits.append(conduit_model)
    return conduits


@conduitRouter.put(
    "/conduit/{conduit_id}",
    response_model=Result,
    summary="更新指定管道的相关信息",
    description="通过指定管道ID，更新管道的相关信息",
)
async def update_conduit(conduit_id: str, conduit_update: ConduitRequestModel):
    """
    更新管道信息
    """
    INP = SwmmInput.read_file(SWMM_FILE_PATH, encoding="GB2312")
    inp_conduits = INP.check_for_section(Conduit)
    inp_coordinates = INP.check_for_section(Coordinate)
    inp_xsections = INP.check_for_section(CrossSection)

    # 检查管道ID是否存在
    if conduit_id not in inp_conduits:
        raise HTTPException(
            status_code=404,
            detail=f"修改失败，需要修改的渠道名称 [ {conduit_id} ] 不存在，请检查渠道名称是否正确",
        )

    # 检查新的管道ID是否已存在，如果新的ID与现有ID冲突，则抛出异常
    if conduit_update.name in inp_conduits and conduit_update.name != conduit_id:
        raise HTTPException(
            status_code=400,
            detail=f"保存失败，管道名称 [ {conduit_update.name} ] 已存在，请使用不同的管道名称",
        )

    # 检查管道的起点和终点是否一样
    if conduit_update.from_node == conduit_update.to_node:
        raise HTTPException(
            status_code=400,
            detail="保存失败，管道的起点和终点不能相同",
        )

    # 检查管道的起点和终点是否存在
    if conduit_update.from_node not in inp_coordinates:
        raise HTTPException(
            status_code=404,
            detail=f"保存失败，起点节点 [ {conduit_update.from_node} ] 不存在，请检查节点名称是否正确",
        )
    if conduit_update.to_node not in inp_coordinates:
        raise HTTPException(
            status_code=404,
            detail=f"保存失败，终点节点 [ {conduit_update.to_node} ] 不存在，请检查节点名称是否正确",
        )
    try:
        conduit = inp_conduits.pop(conduit_id)
        inp_conduits[conduit_update.name] = conduit
        conduit.name = conduit_update.name
        conduit.from_node = conduit_update.from_node
        conduit.to_node = conduit_update.to_node
        conduit.length = conduit_update.length
        conduit.roughness = conduit_update.roughness

        # 更新断面数据
        xsection = inp_xsections.pop(conduit_id)
        inp_xsections[conduit_update.name] = xsection
        xsection.link = conduit_update.name
        xsection.transect = conduit_update.transect
        xsection.shape = conduit_update.shape
        xsection.height = conduit_update.height
        xsection.parameter_2 = conduit_update.parameter_2
        xsection.parameter_3 = conduit_update.parameter_3
        xsection.parameter_4 = conduit_update.parameter_4
        print(f"conduit: {conduit}")
        print(f"xsection: {xsection}")
        print(f"xsection.height: {xsection.height}")
        print(f"xsection.parameter_2: {xsection.parameter_2}")
        print(f"xsection.parameter_3: {xsection.parameter_3}")
        print(f"xsection.parameter_4: {xsection.parameter_4}")
        INP.write_file(SWMM_FILE_PATH, encoding="GB2312")
        return Result.success(
            message=f"渠道 [ {conduit_update.name} ] 信息更新成功",
            data={"id": conduit_update.name, type: "conduit"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"保存失败，发生未知错误: {str(e)}",
        )


@conduitRouter.post(
    "/conduit",
    response_model=Result,
    summary="添加新的管道",
    description="创建一个新的管道，并写入 SWMM 文件",
)
async def create_conduit(conduit_data: ConduitRequestModel):
    """
    添加管道信息
    """
    INP = SwmmInput.read_file(SWMM_FILE_PATH, encoding="GB2312")
    inp_conduits = INP.check_for_section(Conduit)
    inp_coordinates = INP.check_for_section(Coordinate)
    inp_xsections = INP.check_for_section(CrossSection)

    # 检查管道名称是否已存在
    if conduit_data.name in inp_conduits:
        raise HTTPException(
            status_code=400,
            detail=f"创建失败，管道名称 [ {conduit_data.name} ] 已存在，请使用不同的管道名称",
        )

    # 检查管道的起点和终点是否相同
    if conduit_data.from_node == conduit_data.to_node:
        raise HTTPException(
            status_code=400,
            detail="创建失败，管道的起点和终点不能相同",
        )

    # 检查起点和终点是否存在
    if conduit_data.from_node not in inp_coordinates:
        raise HTTPException(
            status_code=404,
            detail=f"创建失败，起点节点 [ {conduit_data.from_node} ] 不存在，请检查节点名称是否正确",
        )
    if conduit_data.to_node not in inp_coordinates:
        raise HTTPException(
            status_code=404,
            detail=f"创建失败，终点节点 [ {conduit_data.to_node} ] 不存在，请检查节点名称是否正确",
        )

    # 检查管道是否已存在，起点和终点完全一样
    for conduit in inp_conduits.values():
        if (
            conduit.from_node == conduit_data.from_node
            and conduit.to_node == conduit_data.to_node
            or conduit.from_node == conduit_data.to_node
            and conduit.to_node == conduit_data.from_node
        ):
            raise HTTPException(
                status_code=400,
                detail=f"创建失败，启点和终点已存在管道，请检查节点名称是否正确",
            )

    try:
        # 创建新管道对象
        new_conduit = Conduit(
            name=conduit_data.name,
            from_node=conduit_data.from_node,
            to_node=conduit_data.to_node,
            length=conduit_data.length,
            roughness=conduit_data.roughness,
        )
        inp_conduits[conduit_data.name] = new_conduit

        # 创建新的断面信息
        new_xsection = CrossSection(
            link=conduit_data.name,
            transect=conduit_data.transect,
            shape=conduit_data.shape,
            height=conduit_data.height,
            parameter_2=conduit_data.parameter_2,
            parameter_3=conduit_data.parameter_3,
            parameter_4=conduit_data.parameter_4,
        )
        inp_xsections[conduit_data.name] = new_xsection

        # 写入 SWMM 文件
        INP.write_file(SWMM_FILE_PATH, encoding="GB2312")
        return Result.success(
            message=f"管道创建成功", data={"conduit_id": conduit_data.name}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"创建失败，发生未知错误: {str(e)}",
        )


@conduitRouter.delete(
    "/conduit/{conduit_id}",
    response_model=Result,
    summary="删除指定管道",
    description="通过指定管道ID，删除管道信息",
)
async def delete_conduit(conduit_id: str):
    """
    删除管道信息
    """
    # 读取 SWMM 文件
    INP = SwmmInput.read_file(SWMM_FILE_PATH, encoding="GB2312")
    inp_conduits = INP.check_for_section(Conduit)
    inp_xsections = INP.check_for_section(CrossSection)

    # 检查管道是否存在
    if conduit_id not in inp_conduits:
        raise HTTPException(
            status_code=404,
            detail=f"删除失败，管道 [ {conduit_id} ] 不存在，请检查管道名称是否正确",
        )

    try:
        # 删除管道
        del inp_conduits[conduit_id]

        # 删除断面信息（如果存在）
        if conduit_id in inp_xsections:
            del inp_xsections[conduit_id]

        # 写入 SWMM 文件
        INP.write_file(SWMM_FILE_PATH, encoding="GB2312")

        return Result.success(message=f"管道 [ {conduit_id} ] 删除成功")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"删除失败，发生未知错误: {str(e)}",
        )
