from langchain_core.tools import tool
from typing import List, Dict, Any, Optional
from schemas.junction import JunctionModel
import asyncio
from utils.logger import tools_logger
from langgraph.prebuilt import InjectedState
from utils.agent.websocket_manager import ChatMessageSendHandler
from langgraph.types import interrupt
from typing_extensions import Annotated
from langgraph.errors import GraphInterrupt


from apis.junction import (
    get_junctions,
    batch_get_junctions_by_ids,
    update_junction,
    create_junction,
    delete_junction,
)


@tool
async def get_junctions_tool() -> str:
    """节点信息批量获取工具,可用作多个节点信息查询。
    一次性获取SWMM模型中所有节点(Junction)的详细信息,包括地理与水力参数。

    **功能特性**：
        - 获取所有节点的基础属性和水力参数
        - 支持批量查询,适合地图渲染、表格展示等场景
        - 返回结构化数据,便于前端直接消费

    **使用场景**：
        - 查询节点总个数
        - 查询多个节点的信息时

    **返回值**：
        Result.success(
            data=junctions, message=f"成功获取所有节点数据({len(junctions)}个)"
        )
        其中 data(junctions)为 JunctionModel 列表,每个节点结构如下：
        [
            {
                "name": str,              # 节点名称
                "lon": float,             # 节点经度
                "lat": float,             # 节点纬度
                "elevation": float,       # 节点高程(米)
                "depth_init": float,      # 初始水深(米)
                "depth_max": float,       # 最大水深(米)
                "depth_surcharge": float, # 超载水深(米)
                "area_ponded": float,     # 积水面积(平方米)
                "has_inflow": bool,       # 是否有入流
                "timeseries_name": str    # 入流时间序列名称(无则为空字符串)
            },
            ...
        ]
    """
    result = await get_junctions()
    tools_logger.info(
        f"获取所有节点信息: {len(result.data)}个节点,其中类似于: {result.data[0]}"
        if result.data
        else "无节点信息"
    )
    return result


@tool
async def batch_get_junctions_by_ids_tool(ids: List[str]):
    """
    节点信息批量获取工具,通过节点ID列表批量获取节点的详细信息。

    **功能特性**：
        - 支持通过节点ID列表查询多个节点的详细信息
        - 返回节点的地理与水力参数,便于前端直接消费

    **使用场景**：
        - 批量查询节点信息
        - 地图渲染或表格展示多个节点数据

    **参数**：
        - ids (List[str]): 节点ID列表,比如["J1", "J2", "J3"]

    **返回值**：
        Result.success(
            data=junctions, message=f"成功获取指定节点数据({len(junctions)}个)"
        )
        其中 data(junctions)为 JunctionModel 列表,每个节点结构如下：
        [
            {
                "name": str,              # 节点名称
                "lon": float,             # 节点经度
                "lat": float,             # 节点纬度
                "elevation": float,       # 节点高程(米)
                "depth_init": float,      # 初始水深(米)
                "depth_max": float,       # 最大水深(米)
                "depth_surcharge": float, # 超载水深(米)
                "area_ponded": float,     # 积水面积(平方米)
                "has_inflow": bool,       # 是否有入流
                "timeseries_name": str    # 入流时间序列名称(无则为空字符串)
            },
            ...
        ]
    """
    result = await batch_get_junctions_by_ids(ids)
    # TODO：修改logger方式,找一个更高效的处理logger方式(模式)
    tools_logger.info(f"{result.message}" if result.message else "无节点信息")
    return result


@tool
async def update_junction_tool(
    junction_id: str,
    name: Optional[str] = None,
    lon: Optional[float] = None,
    lat: Optional[float] = None,
    elevation: Optional[float] = None,
    depth_init: Optional[float] = None,
    depth_max: Optional[float] = None,
    depth_surcharge: Optional[float] = None,
    area_ponded: Optional[float] = None,
    has_inflow: Optional[bool] = None,
    timeseries_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    节点信息更新(更改)工具,通过节点ID更新指定节点的部分或全部信息。

    **功能特性**：
        - 支持更新节点的地理与水力参数
        - 可更新节点的入流信息及时间序列名称
        - 仅更新传入的参数,未传入的参数保持原值不变

    **使用场景**：
        - 修改节点的部分属性,例如只更新高程 (elevation)
        - 更新节点的地理坐标或水力参数
        - 设置或取消节点的入流信息

    **参数**：
        - junction_id (str): 要更新的节点ID
        - name (Optional[str]): 节点名称,不更新时传 None
        - lon (Optional[float]): 节点经度,不更新时传 None
        - lat (Optional[float]): 节点纬度,不更新时传 None
        - elevation (Optional[float]): 节点高程,单位为米,不更新时传 None
        - depth_init (Optional[float]): 初始水深,单位为米,不更新时传 None
        - depth_max (Optional[float]): 最大水深,单位为米,不更新时传 None
        - depth_surcharge (Optional[float]): 超载水深,单位为米,不更新时传 None
        - area_ponded (Optional[float]): 积水面积,单位为平方米,不更新时传 None
        - has_inflow (Optional[bool]): 是否有入流,不更新时传 None
        - timeseries_name (Optional[str]): 入流时间序列名称,不更新时传 None

    **返回值**：
        Dict[str, Any]: 更新结果字典,包含更新后的节点信息。


    **提示**：
        - 如果某个字段不需要更新,请传 None。
        - 如果只需要更新单个字段,例如高程 (elevation),可以直接传入：
          {
              "elevation": 120
          }
        - 如果需要更新多个字段,可以传入：
          {
              "name": "new_junction_name",
              "lon": 120.123,
              "lat": 30.456,
              "elevation": 120,
              "depth_max": 10.0,
          }
    """
    # 收集所有非 None 的参数
    updates_args = {
        "name": name,
        "lon": lon,
        "lat": lat,
        "elevation": elevation,
        "depth_init": depth_init,
        "depth_max": depth_max,
        "depth_surcharge": depth_surcharge,
        "area_ponded": area_ponded,
        "has_inflow": has_inflow,
        "timeseries_name": timeseries_name,
    }
    updates_args = {k: v for k, v in updates_args.items() if v is not None}

    if not updates_args:
        raise ValueError("更新参数不能为空,请提供至少一个需要更新的字段")

    # 获取当前节点信息
    current_data_result = await batch_get_junctions_by_ids([junction_id])
    if not current_data_result or not current_data_result.data:
        return {"success": False, "message": f"节点 {junction_id} 不存在,无法更新"}

    # 从 Result 里面取出 JunctionModel 再变成字典
    current_data = current_data_result.data[0].dict()

    # 合并更新参数
    updated_data = {**current_data, **updates_args}

    # 构造 JunctionModel 对象
    junction_update = JunctionModel(
        name=updated_data["name"],
        lon=updated_data["lon"],
        lat=updated_data["lat"],
        elevation=updated_data["elevation"],
        depth_init=updated_data["depth_init"],
        depth_max=updated_data["depth_max"],
        depth_surcharge=updated_data["depth_surcharge"],
        area_ponded=updated_data["area_ponded"],
        has_inflow=updated_data["has_inflow"],
        timeseries_name=updated_data["timeseries_name"],
    )

    # 调用更新函数
    result = await update_junction(junction_id, junction_update)
    result_message = {
        "message": result.get("message", "更新节点失败"),
        "updated_args": updates_args,
    }
    return result_message


@tool
async def create_junction_tool(
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
    创建一个新的节点(Junction)。
    用于在 SWMM 水力模型中添加一个新的节点(Junction),并写入相关的地理与水力参数

    必须参数:
        - name: 节点名称 (需要从问题中提取,不能由大模型生成,如果问题中没有,发送回复提醒用户提供)
        - lon: 节点经度 (需要从问题中提取,不能由大模型生成,如果问题中没有,发送回复提醒用户提供)
        - lat: 节点纬度 (需要从问题中提取,不能由大模型生成,如果问题中没有,发送回复提醒用户提供)
    可选参数:
        - elevation: 节点高程,单位为米,默认 0.0
        - depth_init: 初始水深,单位为米,默认 0.0
        - depth_max: 最大水深,单位为米,默认 9999.0
        - depth_surcharge: 超载水深,单位为米,默认 9999.0
        - area_ponded: 积水面积,单位为平方米,默认 0.0
        - has_inflow: 是否有入流。True 表示有,False 表示 无,默认 False
        - timeseries_name: 入流时间序列名称,默认空字符串

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

    result = await create_junction(junction_data)
    tools_logger.info(f"创建节点: {result} ")
    return result


@tool
def delete_junction_tool(
    junction_id: str,
    confirm_question: str,
    client_id: Annotated[str, InjectedState("client_id")],
) -> Dict[str, Any]:
    """删除指定节点.

    通过节点ID删除节点,并清理关联的渠道和坐标数据。

    Args:
        junction_id: 要删除的节点ID,比如 "J1"
        confirm_question: 确认删除的提示问题,比如 "您确定要删除 "J1" 节点吗？",一定要带上具体的节点名称(junction_id)

    Returns:
        Dict[str, Any]: 删除结果字典
    """
    frontend_feedback = None
    try:
        # 触发前端弹窗确认
        frontend_feedback = interrupt(
            {
                "function_name": "showConfirmInChat",
                "args": {"confirm_question": confirm_question},
            }
        )
        if frontend_feedback.get("keep_going", False):
            # keep_going 为 True,表示用户确认删除
            result = asyncio.run(delete_junction(junction_id))
            tools_logger.info(f"删除节点: {result} ")
            return result
        else:
            # keep_going 为 False,表示用户取消删除
            return frontend_feedback
    except GraphInterrupt:
        # 第一次 interrupt 时会进入这里,通知前端弹窗
        asyncio.run(
            ChatMessageSendHandler.send_function_call(
                client_id=client_id,
                function_name="showConfirmInChat",
                args={"confirm_question": confirm_question},
                is_direct_feedback=False,
            )
        )
        raise
    except Exception as e:
        tools_logger.error(f"删除节点失败: {e}")
        return {"success": False, "message": str(e)}


if __name__ == "__main__":
    # 测试获取所有节点信息
    import asyncio

    async def test_get_junctions():
        result = await get_junctions_tool()
        print(result)

    asyncio.run(test_get_junctions())
