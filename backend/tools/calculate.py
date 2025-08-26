from langchain_core.tools import tool
from pydantic import Field
from apis.calculate import query_entity_kind_select, query_calculate_result
from utils.utils import with_result_exception_handler
import asyncio
from langgraph.types import interrupt
from langgraph.errors import GraphInterrupt
from schemas.result import Result
from fastapi import HTTPException
from utils.agent.websocket_manager import ChatMessageSendHandler
from langgraph.prebuilt import InjectedState
from typing_extensions import Annotated


# @tool
# @with_result_exception_handler
# async def query_entity_kind_select_tool(name: str):
#     """
#     查询实体类型判断工具。
#     传入一个实体名称，判断其属于 SWMM 计算结果中的节点(node)还是链接(link)，或都不属于。

#     **功能特性**：
#         - 支持根据名称自动判断实体类型（节点/链接）
#         - 返回实体类型(kind)及可选变量(select)列表，便于后续查询
#         - 若名称无效或未找到，返回错误信息

#     **使用场景**：
#         - 用户输入一个名称，需判断其是节点还是管道
#         - 需要根据实体类型动态展示可选查询变量
#         - 前端表单、下拉选择、自动补全等场景

#     **参数**：
#         - name (str): 实体名称（如节点名、管道名等），区分 node/link

#     **返回值**：
#     - 对于 kind="node"，可选值包括：
#                     - "depth"（深度）、"head"（水头）、"volume"（容积）、"lateral_inflow"（侧边进流量）、"total_inflow"（总进流量）、"flooding"（积水）
#                 - 对于 kind="link"，可选值包括：
#                     - "flow"（流量）、"depth"（深度）、"velocity"（流速）、"volume"（容积）、"capacity"（能力）

#             - 若为节点，select 为 NODE_RESULT_VARIABLE_SELECT
#             - 若为链接，select 为 LINK_RESULT_VARIABLE_SELECT
#             - 若名称无效，Result.error(message="查询实体名称不属于节点或链接...", data=[])

#     **示例**：
#         输入: name="J1"
#         返回: {"kind": "node", "select": [...]}
#         输入: name="C1"
#         返回: {"kind": "link", "select": [...]}
#         输入: name="不存在"
#         返回: Result.error(...)
#     """
#     return await query_entity_kind_select(name)


@tool
def query_calculate_result_tool(
    name: str = Field(description="对象名称（如节点名、管道名），必填"),
    variable_label: str = Field(description="查询变量名称(中文)，必填"),
    client_id: Annotated[str, InjectedState("client_id")] = Field(
        description="前端客户端ID，自动注入"
    ),
):
    """
    计算结果查询工具。
    查询指定对象（节点/链接）的模拟计算时序结果，支持多种变量类型。

    **功能特性**：
        - 支持节点(node)和链接(link)两类对象的结果查询
        - 可查询多种变量（如水深、流量、容积等），返回时序数据
        - 结果格式适配前端可视化（如 ECharts）
        - 自动处理无结果、名称错误等异常情况

    **使用场景**：
        - 用户想查看某节点或管道的模拟结果曲线
        - 前端图表、报表、数据分析等
        - 需要获取指定对象的历史时序数据

    **参数**：
        - name (str): 对象名称（如节点名、管道名） (需要从问题中提取,不能由大模型生成默认值,**如果问题中没有,表示信息不全,无法查询,发送回复提醒用户提供**)
        - variable_label (str): 查询变量名称(中文) (需要从问题中提取,不能由大模型生成默认值,**如果问题中没有,表示信息不全,无法查询,发送回复提醒用户提供**)
            - 对于 节点或者出口，可选值包括：
                - 深度、水头、容积、侧边进流量、总进流量、积水
            - 对于 渠道，可选值包括：
                - 流量、深度、流速、容积、能力

    **返回值**：
        Result.success_result(
            message="结果查询成功",
            data=[ [时间索引, 数值], ... ]  # 时序数据，数值保留两位小数
        )
        - 若无结果，Result.error(message="查询结果为空...", data=[])

    **示例**：
        输入: name="J1", variable="depth"
        返回: [[时间1, 1.23], [时间2, 1.45], ...]
        输入: name="C1", variable="flow"
        返回: [[时间1, 0.56], [时间2, 0.78], ...]
        输入: name="不存在", variable="depth"
        返回: Result.error(...)
    """
    try:
        kind_result = asyncio.run(query_entity_kind_select(name))
        if not kind_result.data:
            return kind_result.model_dump()
        kind = kind_result.data.get("kind")
        select = kind_result.data.get("select")
        success_message = ""
        for var in select:
            if var.get("label") == variable_label:
                success_message = f"已成功获取 {name} 的 {variable_label} 计算结果,并且数据已经在前端图表组件展示"
                variable = var.get("value")
                break
            else:
                success_message = f"未找到 {name} 的 {variable_label} 计算结果，是 {name} 没有 {variable_label} 计算属性，以用 {select[0].get('label')} 替代,数据已经在前端图表组件展示"
                variable = select[0].get("value")  # 默认取第一个变量
        # 触发前端图组件
        frontend_feedback = interrupt(
            {
                "function_name": "showEchartsUITool",
                "args": {
                    "name": name,
                    "kind": kind,
                    "variable": variable,
                },
            }
        )
        return frontend_feedback

    except GraphInterrupt:
        # 第一次 interrupt 时会进入这里,通知前端弹窗
        asyncio.run(
            ChatMessageSendHandler.send_function_call(
                client_id=client_id,
                function_name="showEchartsUITool",
                args={
                    "name": name,
                    "kind": kind,
                    "variable": variable,
                },
                is_direct_feedback=True,
                success_message=success_message,
            )
        )
        raise
    except HTTPException as e:
        return Result.error(message=str(e.detail)).model_dump()
    except Exception as e:
        return Result.error(message=str(e)).model_dump()
