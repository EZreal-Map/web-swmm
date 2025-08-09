from langchain_core.tools import tool
from typing import List, Dict, Any, Optional
from schemas.outfall import OutfallModel
from schemas.result import Result
import asyncio
from utils.logger import tools_logger


from apis.outfall import (
    get_outfalls,
    update_outfall,
    create_outfall,
    delete_outfall,
)


@tool
def get_outfalls_tool() -> str:
    """出口信息批量获取工具，可用作多个出口信息查询。
    一次性获取SWMM模型中所有出口（Outfall）的详细信息，包括地理与水力参数。

    **功能特性**：
        - 获取所有出口的基础属性和水力参数
        - 支持批量查询，适合地图渲染、表格展示等场景
        - 返回结构化数据，便于前端直接消费

    **使用场景**：
        - 查询出口总个数
        - 查询多个出口的信息时

    **返回值**：
        Result.success(
            data=outfalls, message=f"成功获取所有出口数据({len(outfalls)}个)"
        )
        其中 data（outfalls）为 OutfallModel 列表，每个出口结构如下：
        [
            {
                "name": str,              # 出口名称
                "lon": float,             # 出口经度
                "lat": float,             # 出口纬度
                "elevation": float,       # 出口高程（米）
                "kind": str,              # 出流类型，FREE=自由出流(最常见)，NORMAL=正常水位出流，FIXED=固定水位出流
                # kind 说明：
                #   FREE   —— 自由出流（最常见，出口直接排放到自由水面）
                #   NORMAL —— 正常水位出流（出口水位受下游水位影响）
                #   FIXED  —— 固定水位出流（出口水位为固定值，需指定data）
                "data": float | None      # 固定水位值（仅当kind为FIXED时有值）
            },
            ...
        ]
    """
    result = asyncio.run(get_outfalls())
    tools_logger.info(
        f"获取所有出口信息: {len(result.data)}个出口,其中类似于: {result.data[0]}"
        if result.data
        else "无出口信息"
    )
    return result


@tool
def update_outfall_tool(
    outfall_id: str,
    name: Optional[str] = None,
    lon: Optional[float] = None,
    lat: Optional[float] = None,
    elevation: Optional[float] = None,
    kind: Optional[str] = None,
    data: Optional[float] = None,
) -> Dict[str, Any]:
    """
    出口信息更新(更改)工具，通过出口ID更新指定出口的部分或全部信息。

    **功能特性**：
        - 支持更新出口的地理与水力参数
        - 可更新出口的出流类型及固定水位值
        - 仅更新传入的参数，未传入的参数保持原值不变

    **使用场景**：
        - 修改出口的部分属性，例如只更新高程 (elevation)
        - 更新出口的地理坐标或水力参数
        - 设置或修改出口的出流类型

    **参数**：
        - outfall_id (str): 要更新的出口ID
        - name (Optional[str]): 出口名称，不更新时传 None
        - lon (Optional[float]): 出口经度，不更新时传 None
        - lat (Optional[float]): 出口纬度，不更新时传 None
        - elevation (Optional[float]): 出口高程，单位为米，不更新时传 None
        - kind (Optional[str]): 出流类型（FREE、NORMAL、FIXED），不更新时传 None
        - data (Optional[float]): 固定水位值，仅当kind为FIXED时有效，不更新时传 None

    **返回值**：
        Dict[str, Any]: 更新结果字典，包含更新后的出口信息。

    **完整的参数示例**：
        {
            "outfall_id": "outfall_1", # 出口ID
            "name": "outfall_1", # 更新之后的出口名称
            "lon": 120.123, # 更新之后的出口经度，约束 >=0
            "lat": 30.456, # 更新之后的出口纬度, 约束 >=0
            "elevation": 100.0, # 更新之后的出口高程, 约束 >=0
            "kind": "FIXED", # 更新之后的出流类型（FREE、NORMAL、FIXED）
            "data": 50.0, # 更新之后的固定水位值（仅当kind为FIXED时有效）
        }

    **提示**：
        - 如果某个字段不需要更新，请传 None。
        - 如果只需要更新单个字段，例如高程 (elevation)，可以直接传入：
          {
              "elevation": 120
          }
        - 如果需要更新多个字段，可以传入：
          {
              "name": "new_outfall_name",
              "lon": 120.123,
              "lat": 30.456,
              "elevation": 120,
              "kind": "FIXED",
              "data": 50.0
          }
        - 当kind为FIXED时，data字段为必填项；当kind为FREE或NORMAL时，data字段会被忽略
    """
    # 收集所有非 None 的参数
    updates = {
        "name": name,
        "lon": lon,
        "lat": lat,
        "elevation": elevation,
        "kind": kind,
        "data": data,
    }
    updates = {k: v for k, v in updates.items() if v is not None}

    if not updates:
        raise ValueError("更新参数不能为空，请提供至少一个需要更新的字段")

    # 获取当前出口信息（通过调用get_outfalls获取所有出口，然后筛选）
    current_outfalls_result = asyncio.run(get_outfalls())
    if not current_outfalls_result or not current_outfalls_result.data:
        return {"success": False, "message": "获取出口信息失败"}

    # 查找指定的出口
    current_outfall = None
    for outfall in current_outfalls_result.data:
        if outfall.name == outfall_id:
            current_outfall = outfall
            break

    if not current_outfall:
        return {"success": False, "message": f"出口 {outfall_id} 不存在，无法更新"}

    # 从 OutfallModel 变成字典
    current_data = current_outfall.dict()

    # 合并更新参数
    updated_data = {**current_data, **updates}

    # 构造 OutfallModel 对象
    outfall_update = OutfallModel(
        name=updated_data["name"],
        lon=updated_data["lon"],
        lat=updated_data["lat"],
        elevation=updated_data["elevation"],
        kind=updated_data["kind"],
        data=updated_data["data"],
    )

    # 调用更新函数
    result = asyncio.run(update_outfall(outfall_id, outfall_update))
    result_message = {
        "message": result.get("message", "更新出口失败"),
        "updated_args": updated_data,
    }
    return result_message


@tool
def create_outfall_tool(
    name: str,
    lon: float,
    lat: float,
    elevation: float = 0.0,
    kind: str = "FREE",
    data: Optional[float] = None,
) -> Dict[str, Any]:
    """
    创建一个新的出口（Outfall）。
    用于在 SWMM 水力模型中添加一个新的出口（Outfall），并写入相关的地理与水力参数

    必须参数:
        - name: 出口名称 （需要从问题中提取，不能由大模型生成，如果问题中没有，发送回复提醒用户提供）
        - lon: 出口经度 （需要从问题中提取，不能由大模型生成，如果问题中没有，发送回复提醒用户提供）
        - lat: 出口纬度 （需要从问题中提取，不能由大模型生成，如果问题中没有，发送回复提醒用户提供）
    可选参数:
        - elevation: 出口高程，单位为米，默认 0.0
        - kind: 出流类型，可选值为 FREE、NORMAL、FIXED，默认 FREE
        - data: 固定水位值，仅当kind为FIXED时有效，默认 None

    返回:
        Result.success(
            message=f"出口创建成功",
            data={"outfall_id": outfall_data.name},
        )
    """
    outfall_data = OutfallModel(
        name=name,
        lon=lon,
        lat=lat,
        elevation=elevation,
        kind=kind,
        data=data,
    )

    result = asyncio.run(create_outfall(outfall_data))
    tools_logger.info(f"创建出口: {result} ")
    return result


@tool
def delete_outfall_tool(outfall_id: str) -> Dict[str, Any]:
    """删除指定出口.

    通过出口ID删除出口，并清理关联的渠道和坐标数据。

    Args:
        outfall_id: 要删除的出口ID

    Returns:
        Dict[str, Any]: 删除结果字典
    """
    result = asyncio.run(delete_outfall(outfall_id))
    tools_logger.info(f"删除出口: {result} ")
    return result


if __name__ == "__main__":
    # 测试获取所有出口信息
    import asyncio

    async def test_get_outfalls():
        result = await get_outfalls_tool()
        print(result)

    asyncio.run(test_get_outfalls())
