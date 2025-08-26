from langchain_core.tools import tool
from typing import List, Dict, Any, Optional
from pydantic import Field
from schemas.subcatchment import SubCatchmentModel, PolygonModel
import asyncio
from utils.logger import tools_logger
from schemas.result import Result
from langgraph.prebuilt import InjectedState
from langgraph.types import interrupt
from typing_extensions import Annotated
from langgraph.errors import GraphInterrupt
from fastapi import HTTPException
from utils.agent.websocket_manager import ChatMessageSendHandler
from utils.utils import with_result_exception_handler
from pydantic.fields import FieldInfo

from apis.subcatchment import (
    get_subcatchments,
    batch_get_subcatchments_by_names,
    update_subcatchment,
    create_subcatchment,
    delete_subcatchment,
)


@tool
@with_result_exception_handler
async def get_subcatchments_tool() -> str:
    """
    子汇水区信息批量获取工具,一次性获取所有子汇水区的详细信息,包括地理与水文参数。

    **功能特性**：
            - 获取所有子汇水区的基础属性和边界
            - 支持批量查询,适合地图渲染、表格展示等场景
            - 返回结构化数据,便于前端直接消费

    **返回值**：
            Result.success_result(
                    data=subcatchments, message=f"成功获取所有子汇水区数据({len(subcatchments)}个)"
            )
            其中 data(subcatchments)为子汇水区列表,每个结构如下：
            [
                    {
                            "name": str,              # 子汇水区名称
                            "rain_gage": str,         # 雨量计
                            "outlet": str,            # 出水口
                            "area": float,            # 面积
                            "imperviousness": float,  # 不透水率
                            "width": float,           # 特征宽度
                            "slope": float,           # 坡度
                            "polygon": list           # 边界坐标
                    },
                    ...
            ]
    """
    result = await get_subcatchments()
    tools_logger.debug(
        f"获取所有子汇水区信息: {len(result.data)}个,示例: {result.data[0] if result.data else None}"
    )
    return result.model_dump()


@tool
@with_result_exception_handler
async def batch_get_subcatchments_by_names_tool(
    names: List[str] = Field(description="子汇水区名称列表，如 ['S1', 'S2']"),
):
    """
    子汇水区信息批量获取工具,通过名称列表批量获取子汇水区的详细信息。

    **参数**：
            - names (List[str]): 子汇水区名称列表,如 ["S1", "S2"]

    **返回值**：
            Result.success_result(
                    data=subcatchments, message=f"成功获取 {names} 子汇水区数据"
            )
    """
    result = await batch_get_subcatchments_by_names(names)
    if not result.data:
        return Result.error(message=f"未找到子汇水区 {names} 数据").model_dump()
    return result.model_dump()


@tool
@with_result_exception_handler
async def update_subcatchment_tool(
    subcatchment_id: str = Field(description="要更新的子汇水区ID，如 'S1'"),
    name: Optional[str] = Field(
        default=None, description="子汇水区名称，不更新时传 None"
    ),
    rain_gage: Optional[str] = Field(
        default=None, description="雨量计，不更新时传 None"
    ),
    outlet: Optional[str] = Field(default=None, description="出水口，不更新时传 None"),
    area: Optional[float] = Field(default=None, description="面积，不更新时传 None"),
    imperviousness: Optional[float] = Field(
        default=None, description="不透水率，不更新时传 None"
    ),
    width: Optional[float] = Field(
        default=None, description="特征宽度，不更新时传 None"
    ),
    slope: Optional[float] = Field(default=None, description="坡度，不更新时传 None"),
) -> Dict[str, Any]:
    """
    子汇水区信息更新工具,通过ID更新指定子汇水区的部分或全部信息。

    **参数**：
            - subcatchment_id (str): 要更新的子汇水区ID
            - 其他参数: 仅更新传入的参数,未传入的参数保持原值不变
                "name": str,              # 子汇水区名称
                "rain_gage": str,         # 雨量计
                "outlet": str,            # 出水口
                "area": float,            # 面积
                "imperviousness": float,  # 不透水率
                "width": float,           # 特征宽度
                "slope": float,           # 坡度
                "polygon": list           # 边界坐标

    **返回值**：
            Result.success_result(message, data={...})
    """
    # 收集所有非 None 的参数
    updates_args = {
        "name": name,
        "rain_gage": rain_gage,
        "outlet": outlet,
        "area": area,
        "imperviousness": imperviousness,
        "width": width,
        "slope": slope,
    }
    # updates = {k: v for k, v in updates.items() if v is not None}
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

    # 获取当前子汇水区信息
    current_data_result = await batch_get_subcatchments_by_names([subcatchment_id])
    if not current_data_result or not current_data_result.data:
        return Result.error(
            message=f"子汇水区 {subcatchment_id} 不存在,无法更新"
        ).model_dump()
    current_data = current_data_result.data[0]
    updated_data = {**current_data, **updates_args}
    subcatchment_update = SubCatchmentModel(**updated_data)
    result = await update_subcatchment(subcatchment_id, subcatchment_update)
    return Result.success_result(
        message=result.get("message"),
        data={"updated_args": updates_args},
    ).model_dump()


@tool
@with_result_exception_handler
async def create_subcatchment_tool(
    subcatchment: str = Field(
        description="子汇水区名称，必填，，(需要从问题中提取,**不能由大模型生成默认值**,**如果问题中没有,表示信息不全,无法创建,发送回复提醒用户提供**)"
    ),
    polygon: list = Field(
        description="边界坐标，必填，格式为[(x1, y1), (x2, y2), ...]，，(需要从问题中提取,**不能由大模型生成默认值**,**如果问题中没有,表示信息不全,无法创建,发送回复提醒用户提供**)"
    ),
) -> Dict[str, Any]:
    """
    创建一个新的子汇水区。
    必须参数:
        - subcatchment: 子汇水区名称 (必须由用户提供)
        - polygon: 边界坐标 (必须由用户提供)
            例如:
                [
                    (103.6282, 29.7554),
                    (103.6042, 29.7162),
                    (103.6849, 29.7018),
                    (103.6811, 29.7378)
                ]
            其中每个点为(x, y)浮点数元组，建议首尾点相同闭合多边形。
    """
    polygon_data = PolygonModel(subcatchment=subcatchment, polygon=polygon)
    result = await create_subcatchment(polygon_data)
    return result.model_dump()


@tool
def delete_subcatchment_tool(
    subcatchment_id: str = Field(description="要删除的子汇水区ID，如 'S1'"),
    confirm_question: str = Field(description="确认删除的提示问题，需带子汇水区名称"),
    client_id: Annotated[str, InjectedState("client_id")] = Field(
        description="前端客户端ID，自动注入"
    ),
) -> Dict[str, Any]:
    """
    删除指定子汇水区。
    通过子汇水区ID删除子汇水区及其相关模型参数。

    Args:
        subcatchment_id: 要删除的子汇水区ID,比如 "S1"
        confirm_question: 确认删除的提示问题,比如 "您确定要删除 S1 子汇水区吗？"
        client_id: 前端会话ID,用于消息推送

    Returns:
        Dict[str, Any]: 删除结果字典
    """
    try:
        frontend_feedback = interrupt(
            {
                "function_name": "showConfirmBoxUITool",
                "args": {"confirm_question": confirm_question},
            }
        )
        if frontend_feedback.get("success", False):
            # 用户确认删除
            result = asyncio.run(delete_subcatchment(subcatchment_id))
            tools_logger.info(f"删除子汇水区: {result}")
            return result.model_dump()
        else:
            # 用户取消删除
            return frontend_feedback
    except GraphInterrupt:
        asyncio.run(
            ChatMessageSendHandler.send_function_call(
                client_id=client_id,
                function_name="showConfirmBoxUITool",
                args={"confirm_question": confirm_question},
                is_direct_feedback=False,
            )
        )
        raise
    except HTTPException as e:
        return Result.error(message=str(e.detail)).model_dump()
    except Exception as e:
        return Result.error(message=str(e)).model_dump()
