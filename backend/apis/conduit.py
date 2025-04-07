from fastapi import APIRouter, HTTPException
from swmm_api import SwmmInput
from swmm_api.input_file.sections.node_component import Coordinate
from swmm_api.input_file.sections.link import Conduit
from swmm_api.input_file.sections.link_component import CrossSection
from swmm_api.input_file.sections.others import Transect
from schemas.conduit import ConduitResponseModel, ConduitRequestModel
from schemas.result import Result


conduitRouter = APIRouter()
SWMM_FILE_PATH = "./swmm/swmm_test.inp"


@conduitRouter.get(
    "/conduits",
    summary="获取所有渠道信息",
    description="获取所有渠道信息",
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
        conduits.append(conduit_model)
    return conduits


@conduitRouter.put(
    "/conduit/{conduit_id}",
    response_model=Result,
    summary="更新指定渠道的相关信息",
    description="通过指定渠道ID，更新渠道的相关信息",
)
async def update_conduit(conduit_id: str, conduit_update: ConduitRequestModel):
    """
    更新渠道信息
    """
    INP = SwmmInput.read_file(SWMM_FILE_PATH, encoding="GB2312")
    inp_conduits = INP.check_for_section(Conduit)
    inp_coordinates = INP.check_for_section(Coordinate)
    inp_xsections = INP.check_for_section(CrossSection)
    inp_transects = INP.check_for_section(Transect)

    # 检查渠道ID是否存在
    if conduit_id not in inp_conduits:
        raise HTTPException(
            status_code=404,
            detail=f"修改失败，需要修改的渠道名称 [ {conduit_id} ] 不存在，请检查渠道名称是否正确",
        )

    # 检查新的渠道ID是否已存在，如果新的ID与现有ID冲突，则抛出异常
    if conduit_update.name in inp_conduits and conduit_update.name != conduit_id:
        raise HTTPException(
            status_code=400,
            detail=f"保存失败，渠道名称 [ {conduit_update.name} ] 已存在，请使用不同的渠道名称",
        )

    # 检查渠道的起点和终点是否一样
    if conduit_update.from_node == conduit_update.to_node:
        raise HTTPException(
            status_code=400,
            detail="保存失败，渠道的起点和终点不能相同",
        )

    # 检查渠道的起点和终点是否存在
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

    # 如果是不规则断面，检查断面是否存在
    if conduit_update.shape == "IRREGULAR":
        if conduit_update.transect not in inp_transects:
            raise HTTPException(
                status_code=404,
                detail=f"保存失败，断面 [ {conduit_update.transect} ] 不存在，请检查断面名称是否正确",
            )

    try:
        conduit = inp_conduits.pop(conduit_id)
        inp_conduits[conduit_update.name] = conduit
        conduit.name = conduit_update.name
        conduit.from_node = conduit_update.from_node
        conduit.to_node = conduit_update.to_node
        conduit.length = conduit_update.length
        conduit.roughness = conduit_update.roughness

        del inp_xsections[conduit_id]
        xsection = CrossSection(
            link=conduit_update.name,
            transect=conduit_update.transect,
            shape=conduit_update.shape,
            height=conduit_update.height,
            parameter_2=conduit_update.parameter_2,
            parameter_3=conduit_update.parameter_3,
            parameter_4=conduit_update.parameter_4,
        )
        inp_xsections[conduit_update.name] = xsection
        INP.write_file(SWMM_FILE_PATH, encoding="GB2312")
        return Result.success(
            message=f"渠道 [ {conduit_update.name} ] 信息更新成功",
            data={
                "id": conduit_update.name,
                "type": "conduit",
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"保存失败，发生未知错误: {str(e)}",
        )


@conduitRouter.post(
    "/conduit",
    response_model=Result,
    summary="添加新的渠道",
    description="创建一个新的渠道，并写入 SWMM 文件",
)
async def create_conduit(conduit_data: ConduitRequestModel):
    """
    添加渠道信息
    """
    INP = SwmmInput.read_file(SWMM_FILE_PATH, encoding="GB2312")
    inp_conduits = INP.check_for_section(Conduit)
    inp_coordinates = INP.check_for_section(Coordinate)
    inp_xsections = INP.check_for_section(CrossSection)

    # 检查渠道名称是否已存在
    if conduit_data.name in inp_conduits:
        raise HTTPException(
            status_code=400,
            detail=f"创建失败，渠道名称 [ {conduit_data.name} ] 已存在，请使用不同的渠道名称",
        )

    # 检查渠道的起点和终点是否相同
    if conduit_data.from_node == conduit_data.to_node:
        raise HTTPException(
            status_code=400,
            detail="创建失败，渠道的起点和终点不能相同",
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

    # 检查渠道是否已存在，起点和终点完全一样
    for conduit in inp_conduits.values():
        if (
            conduit.from_node == conduit_data.from_node
            and conduit.to_node == conduit_data.to_node
            or conduit.from_node == conduit_data.to_node
            and conduit.to_node == conduit_data.from_node
        ):
            raise HTTPException(
                status_code=400,
                detail=f"创建失败，启点和终点已存在渠道，请检查节点名称是否正确",
            )

    try:
        # 创建新渠道对象
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
            message=f"渠道创建成功", data={"conduit_id": conduit_data.name}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"创建失败，发生未知错误: {str(e)}",
        )


@conduitRouter.delete(
    "/conduit/{conduit_id}",
    response_model=Result,
    summary="删除指定渠道",
    description="通过指定渠道ID，删除渠道信息",
)
async def delete_conduit(conduit_id: str):
    """
    删除渠道信息
    """
    # 读取 SWMM 文件
    INP = SwmmInput.read_file(SWMM_FILE_PATH, encoding="GB2312")
    inp_conduits = INP.check_for_section(Conduit)
    inp_xsections = INP.check_for_section(CrossSection)

    # 检查渠道是否存在
    if conduit_id not in inp_conduits:
        raise HTTPException(
            status_code=404,
            detail=f"删除失败，渠道 [ {conduit_id} ] 不存在，请检查渠道名称是否正确",
        )

    try:
        # 删除渠道
        del inp_conduits[conduit_id]

        # 删除断面信息（如果存在）
        if conduit_id in inp_xsections:
            del inp_xsections[conduit_id]

        # 写入 SWMM 文件
        INP.write_file(SWMM_FILE_PATH, encoding="GB2312")

        return Result.success(message=f"渠道 [ {conduit_id} ] 删除成功")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"删除失败，发生未知错误: {str(e)}",
        )
