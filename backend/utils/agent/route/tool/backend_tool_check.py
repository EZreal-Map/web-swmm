from schemas.agent.state import ToolModeSate
from typing import Literal


# 2.4 后端检查点路由
async def backend_tool_check_route(
    state: ToolModeSate,
) -> Literal["backend_tools", "frontend_tools", "summary_response"]:
    """后端检查点路由:根据后端工具检查结果决定下一步流程"""
    next_step = state.get("next_step", "summary_response")
    if next_step not in [
        "backend_tools",
        "frontend_tools",
        "summary_response",
    ]:
        return "summary_response"
    else:
        return next_step
