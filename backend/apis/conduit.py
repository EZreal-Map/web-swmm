from fastapi import APIRouter
from swmm_api import SwmmInput


conduitRouter = APIRouter()


@conduitRouter.get(
    "/conduits",
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
