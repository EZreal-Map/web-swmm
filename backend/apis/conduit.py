from fastapi import APIRouter, HTTPException
from swmm_api import SwmmInput
from schemas.conduit import ConduitModel
from schemas.result import Result


conduitRouter = APIRouter()


@conduitRouter.get(
    "/conduits",
    response_model=list[ConduitModel],
    summary="获取所有管道信息",
    description="获取所有管道信息",
)
async def get_conduits():
    """
    获取坐标
    """
    inp = SwmmInput.read_file("./swmm/swmm_test.inp", encoding="GB2312")
    conduits = []
    for conduit in inp.CONDUITS.values():
        conduits.append(
            {
                "name": conduit.name,
                "from_node": conduit.from_node,
                "to_node": conduit.to_node,
                "length": conduit.length,
                "roughness": conduit.roughness,
            }
        )
    return conduits


@conduitRouter.put(
    "/conduit/{conduit_id}",
    response_model=Result,
    summary="更新指定管道的相关信息",
    description="通过指定管道ID，更新管道的相关信息",
)
async def update_conduit(conduit_id: str, conduit_update: ConduitModel):
    """
    更新管道信息
    """
    inp = SwmmInput.read_file("./swmm/swmm_test.inp", encoding="GB2312")
    conduits_data = inp.CONDUITS
    coordinates_data = inp.COORDINATES

    # 检查管道ID是否存在
    if conduit_id not in conduits_data:
        raise HTTPException(
            status_code=404,
            detail=f"修改失败，需要修改的渠道名称({conduit_id}) 不存在，请检查渠道名称是否正确",
        )

    # 检查新的管道ID是否已存在，如果新的ID与现有ID冲突，则抛出异常
    if conduit_update.name in conduits_data and conduit_update.name != conduit_id:
        raise HTTPException(
            status_code=400,
            detail=f"修改失败，管道名称 ({conduit_update.name}) 已存在，请使用不同的管道名称",
        )

    # 检查管道的起点和终点是否一样
    if conduit_update.from_node == conduit_update.to_node:
        raise HTTPException(
            status_code=400,
            detail="修改失败，管道的起点和终点不能相同",
        )

    # 检查管道的起点和终点是否存在
    if conduit_update.from_node not in coordinates_data:
        raise HTTPException(
            status_code=404,
            detail=f"修改失败，起点节点 ({conduit_update.from_node}) 不存在，请检查节点名称是否正确",
        )
    if conduit_update.to_node not in coordinates_data:
        raise HTTPException(
            status_code=404,
            detail=f"修改失败，终点节点 ({conduit_update.to_node}) 不存在，请检查节点名称是否正确",
        )
    try:
        conduit = conduits_data.pop(conduit_id)
        conduits_data[conduit_update.name] = conduit
        conduit.name = conduit_update.name
        conduit.from_node = conduit_update.from_node
        conduit.to_node = conduit_update.to_node
        conduit.length = conduit_update.length
        conduit.roughness = conduit_update.roughness

        inp.write_file("./swmm/swmm_test.inp", encoding="GB2312")
        return Result.success(message=f"渠道({conduit_id})信息更新成功")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"修改失败，发生未知错误: {str(e)}",
        )
