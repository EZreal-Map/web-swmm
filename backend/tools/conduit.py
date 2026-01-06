from langchain_core.tools import tool
from typing import List, Dict, Any, Optional
from pydantic import Field
from schemas.conduit import ConduitRequestModel
from utils.logger import tools_logger
from langgraph.prebuilt import InjectedState
from langgraph.types import interrupt
from typing_extensions import Annotated
from langgraph.errors import GraphInterrupt
from utils.agent.websocket_manager import ChatMessageSendHandler
from schemas.result import Result
from utils.utils import with_result_exception_handler
from fastapi import HTTPException
from pydantic.fields import FieldInfo

from apis.conduit import (
    get_conduits,
    update_conduit,
    create_conduit,
    delete_conduit,
    batch_get_conduits_by_ids,
)


@tool
@with_result_exception_handler
async def get_conduits_tool() -> str:
    """渠道信息批量获取工具,可用作多个渠道信息查询。
    一次性获取SWMM模型中所有渠道(Conduit)的详细信息,包括地理与水力参数。

    **功能特性**:
        - 获取所有渠道的基础属性和水力参数
        - 支持批量查询,适合地图渲染、表格展示等场景
        - 返回结构化数据,便于前端直接消费

    **使用场景**:
        - 查询渠道总个数
        - 查询多个渠道的信息时

    **返回值**:
        Result.success_result(
            data=conduits, message=f"成功获取所有渠道数据({len(conduits)}个)"
        )
        其中 data(conduits)为 ConduitResponseModel 列表,每个渠道结构如下:
        [
            {
                "name": str,              # 渠道名称
                "from_node": str,        # 起点节点
                "to_node": str,          # 终点节点
                "length": float,         # 渠道长度
                "roughness": float,      # 渠道糙率
                "transect": str|None,    # 断面引用(仅IRREGULAR时有)
                "shape": str,            # 断面形状
                "height": float|None,    # 断面高度
                "parameter_2": float|None, # 断面底宽
                "parameter_3": float|None, # 左侧边坡
                "parameter_4": float|None, # 右侧边坡
            },
            ...
        ]
    """
    result = await get_conduits()
    tools_logger.info(
        f"获取所有渠道信息: {len(result.data)}个渠道,其中类似于: {result.data[0]}"
        if result.data
        else "无渠道信息"
    )
    return result.model_dump()


@tool
@with_result_exception_handler
async def batch_get_conduits_by_ids_tool(
    ids: List[str] = Field(description="渠道ID列表，如 ['C1', 'C2', 'C3']"),
):
    """
    渠道配置，属性信息批量查询工具,通过渠道ID列表批量查询渠道的详细信息。

    **功能特性**:
        - 支持通过渠道ID列表查询多个渠道的详细信息
        - 返回渠道的地理与水力参数,便于前端直接消费

    **使用场景**：
        - 批量查询多个渠道信息
        - 表格展示多个渠道数据

    **参数**:
        - ids (List[str]): 渠道ID列表(**可以一次性查询多个，不必多次调用**),比如 ["C1", "C2", "C3"]

    **返回值**:
        Result.success_result(
            data=conduits, message=f"成功获取指定渠道数据({len(conduits)}个)"
        )
        其中 data(conduits)为 ConduitResponseModel 列表,每个渠道结构如下:
        [
            {
                "name": str,              # 渠道名称
                "from_node": str,        # 起点节点
                "to_node": str,          # 终点节点
                "length": float,         # 渠道长度
                "roughness": float,      # 渠道糙率
                "transect": str|None,    # 断面引用(仅IRREGULAR时有)
                "shape": str,            # 断面形状
                "height": float|None,    # 断面高度
                "parameter_2": float|None, # 断面底宽
                "parameter_3": float|None, # 左侧边坡
                "parameter_4": float|None, # 右侧边坡
            },
            ...
        ]
    """
    result = await batch_get_conduits_by_ids(ids)
    if not result.data:
        return Result.error(message=f"未找到渠道 `{ids}` 数据").model_dump()
    return result.model_dump()


@tool
@with_result_exception_handler
async def update_conduit_tool(
    conduit_id: str = Field(description="要更新的渠道ID，如 'C1'"),
    name: Optional[str] = Field(default=None, description="渠道名称，不更新时传 None"),
    from_node: Optional[str] = Field(
        default=None, description="起点节点，不更新时传 None"
    ),
    to_node: Optional[str] = Field(
        default=None, description="终点节点，不更新时传 None"
    ),
    length: Optional[float] = Field(
        default=None, description="渠道长度，不更新时传 None"
    ),
    roughness: Optional[float] = Field(
        default=None, description="渠道糙率，不更新时传 None"
    ),
    transect: Optional[str] = Field(
        default=None, description="断面引用，不更新时传 None"
    ),
    shape: Optional[str] = Field(default=None, description="断面形状，不更新时传 None"),
    height: Optional[float] = Field(
        default=None, description="断面高度，不更新时传 None"
    ),
    parameter_2: Optional[float] = Field(
        default=None, description="断面底宽，不更新时传 None"
    ),
    parameter_3: Optional[float] = Field(
        default=None, description="左侧边坡，不更新时传 None"
    ),
    parameter_4: Optional[float] = Field(
        default=None, description="右侧边坡，不更新时传 None"
    ),
) -> Dict[str, Any]:
    """
    渠道信息更新工具,通过渠道ID更新指定渠道的部分或全部信息。

    **功能特性**:
        - 支持更新渠道的地理与水力参数
        - 可更新渠道的断面信息
        - 仅更新传入的参数,未传入的参数保持原值不变

    **参数**:
        - conduit_id (str): 要更新的渠道ID
        - name (Optional[str]): 渠道名称,不更新时传 None
        - from_node (Optional[str]): 起点节点,不更新时传 None
        - to_node (Optional[str]): 终点节点,不更新时传 None
        - length (Optional[float]): 渠道长度,不更新时传 None
        - roughness (Optional[float]): 渠道糙率,不更新时传 None
        - transect (Optional[str]): 断面引用,不更新时传 None
        - shape (Optional[str]): 断面形状,不更新时传 None
        - height (Optional[float]): 断面高度,不更新时传 None
        - parameter_2 (Optional[float]): 断面底宽,不更新时传 None
        - parameter_3 (Optional[float]): 左侧边坡,不更新时传 None
        - parameter_4 (Optional[float]): 右侧边坡,不更新时传 None

    **返回值**:
        Dict[str, Any]: 更新结果字典,包含更新后的渠道信息。

    **提示**:
        - 如果某个字段不需要更新,请传 None。
        - 只需更新部分字段时,仅传递需要变更的参数。
    """
    # 合并参数
    updates_args = {
        "name": name,
        "from_node": from_node,
        "to_node": to_node,
        "length": length,
        "roughness": roughness,
        "transect": transect,
        "shape": shape,
        "height": height,
        "parameter_2": parameter_2,
        "parameter_3": parameter_3,
        "parameter_4": parameter_4,
    }
    updates_args = {
        k: (v.default if isinstance(v, FieldInfo) else v)
        for k, v in updates_args.items()
        if (
            (not isinstance(v, FieldInfo) and v is not None)
            or (isinstance(v, FieldInfo) and v.default is not None)
        )
    }
    if not updates_args:
        return Result.error(
            message="更新参数不能为空,请提供至少一个需要更新的字段"
        ).model_dump()

    # 获取当前渠道信息
    current_data_result = await batch_get_conduits_by_ids([conduit_id])
    if not current_data_result or not current_data_result.data:
        return Result.not_found(f"渠道 {conduit_id} 不存在,无法更新").model_dump()

    # 从 Result 里面取出 JunctionModel 再变成字典
    current_data = current_data_result.data[0].model_dump()
    updated_data = {**current_data, **updates_args}
    conduit_update = ConduitRequestModel(**updated_data)
    result = await update_conduit(conduit_id, conduit_update)

    return Result.success_result(
        message=result.get("message"), data={"updated_args": updates_args}
    ).model_dump()


@tool
@with_result_exception_handler
async def create_conduit_tool(
    name: str = Field(
        description="渠道名称，必填，(需要从问题中提取,**不能由大模型生成默认值**,**如果问题中没有,表示信息不全,无法创建,发送回复提醒用户提供**)"
    ),
    from_node: str = Field(
        description="起点节点，必填，(需要从问题中提取,**不能由大模型生成默认值**,**如果问题中没有,表示信息不全,无法创建,发送回复提醒用户提供**)"
    ),
    to_node: str = Field(
        description="终点节点，必填，(需要从问题中提取,**不能由大模型生成默认值**,**如果问题中没有,表示信息不全,无法创建,发送回复提醒用户提供**)"
    ),
    length: float = Field(default=100, description="渠道长度，默认100，可选参数"),
    roughness: float = Field(default=0.01, description="渠道糙率，默认0.01，可选参数"),
    transect: Optional[str] = Field(
        default=None, description="断面引用，仅IRREGULAR时有意义，可选参数"
    ),
    shape: str = Field(
        default="TRAPEZOIDAL", description="断面形状，默认TRAPEZOIDAL，可选参数"
    ),
    height: float = Field(default=10, description="断面高度，默认10，可选参数"),
    parameter_2: float = Field(default=20, description="断面底宽，默认20，可选参数"),
    parameter_3: float = Field(default=0.5, description="左侧边坡，默认0.5，可选参数"),
    parameter_4: float = Field(default=0.5, description="右侧边坡，默认0.5，可选参数"),
) -> Dict[str, Any]:
    """
    创建一个新的渠道(Conduit)。
    用于在 SWMM 水力模型中添加一个新的渠道(Conduit),并写入相关的地理与水力参数

    必须参数:
        - name: 渠道名称 (需要从问题中提取,不能由大模型生成默认值,**如果问题中没有,表示信息不全,无法创建,发送回复提醒用户提供**)
        - from_node: 起点节点 (需要从问题中提取,不能由大模型生成默认值,**如果问题中没有,表示信息不全,无法创建,发送回复提醒用户提供**)
        - to_node: 终点节点 (需要从问题中提取,不能由大模型生成默认值,**如果问题中没有,表示信息不全,无法创建,发送回复提醒用户提供**)
    可选参数（可选参数不必须传入）:
        - length: 渠道长度,默认100
        - roughness: 渠道糙率,默认0.01
        - transect: 断面引用,仅IRREGULAR时有意义
        - shape: 断面形状,默认TRAPEZOIDAL
        - height: 断面高度,默认10
        - parameter_2: 断面底宽,默认20
        - parameter_3: 左侧边坡,默认0.5
        - parameter_4: 右侧边坡,默认0.5

    返回:
        Result.success_result(
            message=f"渠道创建成功",
            data={"conduit_id": conduit_data.name},
        )
    """
    conduit_data = ConduitRequestModel(
        name=name,
        from_node=from_node,
        to_node=to_node,
        length=length,
        roughness=roughness,
        transect=transect,
        shape=shape,
        height=height,
        parameter_2=parameter_2,
        parameter_3=parameter_3,
        parameter_4=parameter_4,
    )
    result = await create_conduit(conduit_data)
    return result.model_dump()


@tool
async def delete_conduit_tool(
    conduit_id: str = Field(description="要删除的渠道ID，如 'C1'"),
    confirm_question: str = Field(description="确认删除的提示问题，需带渠道名称"),
    state: Annotated[Any, InjectedState] = Field(description="自动注入的状态对象"),
) -> Dict[str, Any]:
    """删除指定渠道.
    通过渠道ID删除渠道,并清理关联的断面数据。
    Args:
        conduit_id: 要删除的渠道ID,比如 "C1"
        confirm_question: 确认删除的提示问题,比如 "您确定要删除 C1 渠道吗？",一定要带上具体的渠道名称(conduit_id)
    Returns:
        Dict[str, Any]: 删除结果字典
    """
    try:
        # 触发前端弹窗确认
        frontend_feedback = interrupt(
            {
                "function_name": "showConfirmBoxUITool",
                "args": {"confirm_question": confirm_question},
            }
        )
        if frontend_feedback.get("success", False):
            result = await delete_conduit(conduit_id)
            tools_logger.info(f"删除渠道: {result} ")
            return result.model_dump()
        else:
            return frontend_feedback
    except GraphInterrupt:
        # 第一次 interrupt 时会进入这里,通知前端弹窗
        await ChatMessageSendHandler.send_function_call(
            client_id=state.get("client_id"),
            function_name="showConfirmBoxUITool",
            args={"confirm_question": confirm_question},
            is_direct_feedback=False,
            mode=state.get("mode"),
        )

        raise
    except HTTPException as e:
        return Result.error(message=str(e.detail)).model_dump()
    except Exception as e:
        return Result.error(message=str(e)).model_dump()


if __name__ == "__main__":
    # 测试获取所有渠道信息
    import asyncio

    async def test_get_conduits():
        result = await get_conduits_tool()
        print(result)

    asyncio.run(test_get_conduits())
