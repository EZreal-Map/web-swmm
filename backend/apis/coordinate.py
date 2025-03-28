from fastapi import APIRouter
from swmm_api import SwmmInput

from utils.coordinate_converter import utm_to_wgs84

from schemas.coordinate import CoordinateModel

coordinatesRouter = APIRouter()


@coordinatesRouter.get(
    "/coordinates",
    response_model=list[CoordinateModel],
    summary="获取所有节点的坐标",
    description="获取所有节点的坐标",
)
async def get_coordinates():
    """
    获取坐标
    """
    inp = SwmmInput.read_file("./swmm/swmm_test.inp", encoding="GB2312")
    coordinates = []
    for coordinate in inp.COORDINATES.values():
        x, y = utm_to_wgs84(coordinate.x, coordinate.y)
        coordinates.append(
            {
                "node": coordinate.node,
                "x": x,
                "y": y,
            }
        )
    return coordinates
