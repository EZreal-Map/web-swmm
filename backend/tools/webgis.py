from langchain_core.tools import tool
from langgraph.types import interrupt
from langgraph.prebuilt import InjectedState
from typing_extensions import Annotated
from langgraph.errors import GraphInterrupt
from utils.agent.websocket_manager import ChatMessageSendHandler
import asyncio

# 在 LangGraph 的 interrupt 机制下，节点被 resume 时会重新执行整个节点函数，所以 print("human_in_lood 之前") 也会被执行两次（一次是第一次中断时，一次是 resume 时）。这是 LangGraph 的设计：resume 后节点会完整重跑。
# 只让 print 运行一次的原理与方法
# 原理：
# interrupt 第一次调用时会 raise GraphInterrupt，节点退出，print 执行。
# resume 时节点重跑，print 又执行一次。
# 解决思路：
# 你可以通过检测当前是“resume”状态，来决定是否执行 print。resume 时，interrupt 会返回 resume 的值，而不是 raise 异常。
# 在 LangGraph 的 interrupt 机制下，节点被 resume 时会重新执行整个节点函数
# LangGraph 的 interrupt 机制原理

# 第一次调用 interrupt
# 当节点第一次执行到 interrupt(...) 时，LangGraph 会抛出一个特殊的异常（GraphInterrupt）。
# 这个异常会被你的 try/except 捕获，所以 except 里的 print("human_in_lood 之前") 会被执行，然后异常被重新抛出，节点中断，等待外部 resume。
# resume 后再次执行节点


# 当你用 Command(resume=...) 恢复节点时，LangGraph 会重新执行整个节点函数，但这时 interrupt(...) 不会再抛异常，
# 而是直接返回你 resume 时传入的值（即 resume_value）。
# 所以这次不会进入 except，print 也不会再执行，直接 return。
@tool
def fly_to_entity_by_name_tool(
    entity_name: str, client_id: Annotated[str, InjectedState("client_id")]
) -> dict:
    """
    地图实体跳转或点击工具（**只能用于单实体，禁止批量或多次调用！**），**多实体信息查询禁止使用此工具**

    通过实体名称在前端WebGIS地图中定位并高亮显示指定实体，同时弹出实体详细信息窗口。

    **⚠️ 严格约束：**
    - 本函数**每次大模型function_call请求只能调用一次**，**禁止在同一请求或同一function_call中多次调用tools**！
    - **禁止for循环、禁止传入多个实体、禁止批量调用！**
    - 如果用户请求多个实体（如“查看J1、J2、J3”），**只能选择其中一个最相关的实体进行跳转**，不要多次调用本函数！
    - 违反此约束会导致前端异常或用户体验混乱。

    **正例（推荐）：**
        - 用户请求“查看J1节点”，只运行调用一次本函数，参数为J1。
        - 用户请求“定位到C1管道”，只运行调用一次本函数，参数为C1。

    **反例（禁止）：**
        - 用户请求“查看J1、J2、J3节点信息”，**不要**多次调用本函数！
        - 用户请求“查看J1-J3节点信息”，**不要**多次调用本函数！
        - 不要传入列表或多个实体名！

    **功能特性**：
        - 自动定位到指定实体的地理位置
        - 高亮显示目标实体
        - 弹出实体详细信息窗口
        - 支持SWMM模型中的所有实体类型（节点、管道、子汇水区等）

    **使用场景**：
        - 单个实体信息查询和可视化
        - 用户请求查看特定实体位置时
        - 需要在地图上突出显示某个实体时

    **参数说明**:
        entity_name (str): 目标实体的唯一标识名称
            - 支持节点名称、管道名称、子汇水区名称
            - 名称需与SWMM模型中的实际名称完全匹配（区分大小写）

    **返回值**:
        dict: 前端执行结果，包含成功确认信息
            格式: {"function_name": "flyToEntityByNameTool", "args": {"entity_name": entity_name}}
    """
    frontend_feedback = None
    print("**************进入前端跳转TOOL**************")
    try:
        # 直接调用前端的 interrupt 函数，传递跳转指令
        # interrupt括号里面的信息会被放进 AIMessage 的 tool calls的 args 里面
        frontend_feedback = interrupt(
            {
                "function_name": "flyToEntityByNameTool",
                "args": {"entity_name": entity_name},
            }
        )
        return frontend_feedback
    except GraphInterrupt:
        print("**************执行前端跳转TOOLL**************")
        # 只执行一次，当第一次interrupt时，Command(resume=...) 恢复节点时 不会再执行下面的代码，但是上面代码每次都会执行
        asyncio.run(
            ChatMessageSendHandler.send_function_call(
                client_id=client_id,
                function_name="flyToEntityByNameTool",
                args={"entity_name": entity_name},
                is_direct_feedback=True,
                # 预定义成功消息，当前端执行成功以后，再被返回给后端，后端可以放进Command里去，Command里的信息最终会被封装到ToolMessage里
                success_message=f"前端界面已跳转到实体: {entity_name}，并高亮显示实体和实体信息弹窗。具体命令格式为: {{'function_name': 'flyToEntityByNameTool', 'args': {{'entity_name': '{entity_name}'}}}}",
            )
        )
        # 一定要raise异常，否则会导致节点不会中断
        # 一定不要带参数 会把刚刚捕获到的 GraphInterrupt 原样抛出，LangGraph 能正确识别和恢复
        raise


@tool
def init_entities_tool(client_id: Annotated[str, InjectedState("client_id")]) -> dict:
    """
    WebGIS实体初始化/刷新工具（用于实体有增删改时，通知前端刷新所有实体）

    **功能描述**：
        通知前端WebGIS刷新并重新加载所有实体（如节点、管道、子汇水区等），以保证前端展示的实体状态与后端一致。

    **使用场景**：
        - 后端实体有新增、删除、更新时
        - 需要前端重新拉取并渲染所有实体时

    **⚠️ 严格约束**：
        - **最先执行约束**，该工具会导致前端重新加载所有实体，需要**保证**在**所有前端工具调用之前执行**。

    **参数说明**:
        不需要参数

    **返回值**:
        dict: 前端执行结果，包含成功确认信息
            格式: {"function_name": "initEntitiesTool", "args": {}}
    """
    frontend_feedback = None
    print("**************进入前端初始化TOOL**************")
    try:
        frontend_feedback = interrupt(
            {
                "function_name": "initEntitiesTool",
                "args": {},
            }
        )
        return frontend_feedback
    except GraphInterrupt:
        print("**************执行前端初始化TOOL**************")
        asyncio.run(
            ChatMessageSendHandler.send_function_call(
                client_id=client_id,
                function_name="initEntitiesTool",
                args={},
                is_direct_feedback=True,
                success_message="前端已刷新所有实体，展示为最新状态。",
            )
        )
        raise
