from langchain_core.tools import tool
from typing import List, Dict, Any
from schemas.junction import JunctionModel
from schemas.result import Result
import asyncio
from utils.logger import tools_logger


from apis.junction import (
    get_junctions,
    update_junction,
    create_junction,
    delete_junction,
)


@tool
def get_junctions_tool() -> str:
    """节点信息批量获取工具，可用作多个节点信息查询。
    一次性获取SWMM模型中所有节点（Junction）的详细信息，包括地理与水力参数。

    **功能特性**：
        - 获取所有节点的基础属性和水力参数
        - 支持批量查询，适合地图渲染、表格展示等场景
        - 返回结构化数据，便于前端直接消费

    **使用场景**：
        - 查询节点总个数
        - 查询多个节点的信息时

    **返回值**：
        Result.success(
            data=junctions, message=f"成功获取所有节点数据({len(junctions)}个)"
        )
        其中 data（junctions）为 JunctionModel 列表，每个节点结构如下：
        [
            {
                "name": str,              # 节点名称
                "lon": float,             # 节点经度
                "lat": float,             # 节点纬度
                "elevation": float,       # 节点高程（米）
                "depth_init": float,      # 初始水深（米）
                "depth_max": float,       # 最大水深（米）
                "depth_surcharge": float, # 超载水深（米）
                "area_ponded": float,     # 积水面积（平方米）
                "has_inflow": bool,       # 是否有入流
                "timeseries_name": str    # 入流时间序列名称（无则为空字符串）
            },
            ...
        ]
    """
    result = asyncio.run(get_junctions())
    tools_logger.info(
        f"获取所有节点信息: {len(result.data)}个节点,其中类似于: {result.data[0]}"
        if result.data
        else "无节点信息"
    )
    return result


@tool
def update_junction_tool(
    junction_id: str,
    name: str,
    lon: float,
    lat: float,
    elevation: float = 0.0,
    depth_init: float = 0.0,
    depth_max: float = 9999.0,
    depth_surcharge: float = 9999.0,
    area_ponded: float = 0.0,
    has_inflow: bool = False,
    timeseries_name: str = "",
) -> Dict[str, Any]:
    """通过节点名称，更新指定节点的所有信息.

    通过节点名称，更新指定节点的所有信息，包括名称、经纬度、高程、最大水深、初始水深、超载水深、积水面积、是否有入流及入流时间序列名称。

    Args:
        junction_id: 要更新的节点ID
        name: 节点名称
        lon: 经度
        lat: 纬度
        elevation: 高程
        depth_init: 初始水深
        depth_max: 最大水深
        depth_surcharge: 超载水深
        area_ponded: 积水面积
        has_inflow: 是否有入流
        timeseries_name: 入流时间序列名称

    Returns:
        Dict[str, Any]: 更新结果字典
    """
    junction_update = JunctionModel(
        name=name,
        lon=lon,
        lat=lat,
        elevation=elevation,
        depth_init=depth_init,
        depth_max=depth_max,
        depth_surcharge=depth_surcharge,
        area_ponded=area_ponded,
        has_inflow=has_inflow,
        timeseries_name=timeseries_name,
    )

    result = update_junction(junction_id, junction_update)
    return result


@tool
def create_junction_tool(
    name: str,
    lon: float,
    lat: float,
    elevation: float = 0.0,
    depth_init: float = 0.0,
    depth_max: float = 9999.0,
    depth_surcharge: float = 9999.0,
    area_ponded: float = 0.0,
    has_inflow: bool = False,
    timeseries_name: str = "",
) -> Dict[str, Any]:
    """
    创建一个新的节点（Junction）。
    用于在 SWMM 水力模型中添加一个新的节点（Junction），并写入相关的地理与水力参数

    必须参数:
        - name: 节点名称 （需要从问题中提取，不能由大模型生成，如果问题中没有，发送回复提醒用户提供）
        - lon: 节点经度 （需要从问题中提取，不能由大模型生成，如果问题中没有，发送回复提醒用户提供）
        - lat: 节点纬度 （需要从问题中提取，不能由大模型生成，如果问题中没有，发送回复提醒用户提供）
    可选参数:
        - elevation: 节点高程，单位为米，默认 0.0
        - depth_init: 初始水深，单位为米，默认 0.0
        - depth_max: 最大水深，单位为米，默认 9999.0
        - depth_surcharge: 超载水深，单位为米，默认 9999.0
        - area_ponded: 积水面积，单位为平方米，默认 0.0
        - has_inflow: 是否有入流。True 表示有，False 表示 无，默认 False
        - timeseries_name: 入流时间序列名称，默认空字符串

    返回:
        Result.success(
            message=f"节点创建成功",
            data={"junction_id": junction_data.name},
        )
    """
    junction_data = JunctionModel(
        name=name,
        lon=lon,
        lat=lat,
        elevation=elevation,
        depth_init=depth_init,
        depth_max=depth_max,
        depth_surcharge=depth_surcharge,
        area_ponded=area_ponded,
        has_inflow=has_inflow,
        timeseries_name=timeseries_name,
    )

    result = asyncio.run(create_junction(junction_data))
    tools_logger.info(f"创建节点: {result} ")
    return result


@tool
def delete_junction_tool(junction_id: str) -> Dict[str, Any]:
    """删除指定节点.

    通过节点ID删除节点，并清理关联的渠道和坐标数据。

    Args:
        junction_id: 要删除的节点ID

    Returns:
        Dict[str, Any]: 删除结果字典
    """
    result = delete_junction(junction_id)
    return result


if __name__ == "__main__":
    # 测试获取所有节点信息
    import asyncio

    async def test_get_junctions():
        result = await get_junctions_tool()
        print(result)

    asyncio.run(test_get_junctions())
