from schemas.agent.state import State
from utils.agent.websocket_manager import ChatMessageSendHandler
from langchain_core.messages import HumanMessage
from utils.logger import agent_logger
from utils.agent.llm_manager import create_openai_llm

llm = create_openai_llm()
intent_llm = llm


async def intent_classifier_node(state: State) -> dict:
    await ChatMessageSendHandler.send_step(
        state.get("client_id", ""), "[意图识别] 正在进行AI意图识别..."
    )
    """意图识别节点:分析问题并标记需要后端/前端工具"""
    # 提取用户查询
    user_query = state.get("query")
    agent_logger.info(
        f"{state.get('client_id')} - 进入意图识别节点: user_query: {user_query}"
    )
    # 使用提示词进行意图识别(可能包含多种需求)
    # 新增:将state上下文也加入prompt
    intent_prompt = f"""
请阅读用户的问题:<<** {user_query} **>>,并根据需求判断需要调用哪些处理工具(可以同时需要多种)。  

处理工具说明:  
1. backend_tools  
- 用于 **SWMM 模型数据操作**(例如:节点/管道/子汇水区等数据的查询、创建、更新、删除)。  
- 如果问题涉及数据的增删改查,或者需要从数据库读取模型信息,都应选择该工具。  

2. frontend_tools  
- 用于 **前端界面交互**(例如:地图跳转、实体高亮、界面刷新等)。  
- 如果问题需要让用户在界面上看到变化(如定位到某个节点、在地图上显示结果等),则需要该工具。  
- 注意:如果只是查询数据并将结果直接返回给用户(不要求地图或界面变化),则**不需要** frontend_tools。
- 但凡涉及到数据的**更新,删除,增加**操作,都需要 frontend_tools,因为前端界面也要响应的变化更新。

3.如果用户的问题仅仅是日常闲聊或寒暄，不涉及任何 SWMM 模型、数据查询或前端界面操作，
则不需要调用任何工具，请在说明中明确写出“本次对话仅为闲聊，不需要任何工具”。
如果用户的问题超出上述工具能力范围、无法通过这两个工具解决，也请将两个工具都标记为 false，并在说明中写明“不需要任何工具，并简要说明原因”。
---

### 输出要求  
只按以下格式回答(不要多余内容):  

- backend_tools: [true/false]  
- frontend_tools: [true/false]  
- 说明: [简短说明需要这些工具的原因]  

---

### 示例  

##### 1 查询多个问题
用户问题:帮我查询所有节点的信息  
回答:  
- backend_tools: true  
- frontend_tools: false  
- 说明: 查询节点信息只需调用 backend_tools 获取数据表,数据太多无法在前端上一一显示,所以不需要 frontend_tools。

##### 2 查询一个问题
用户问题:帮我查询一个节点的信息,节点ID为J1  
回答:  
- backend_tools: true  
- frontend_tools: true
- 说明: 查询节点信息需调用 backend_tools 获取数据信息,因为数据只有1个,所以可以很方便的在前端界面显示,所以需要 frontend_tools。

#### 3 创建问题
用户问题:帮我创建一个节点,节点信息如下名字为J1,纬度为110,纬度为30  
回答:  
- backend_tools: true
- frontend_tools: true  
- 说明: 创建节点需要调用 backend_tools 保存数据,因为数据只有1个,所以可以很方便的在前端界面显示,所以需要 frontend_tools。

#### 4 删除问题
用户问题:帮我删除一个节点,节点ID为J1  
回答:  
- backend_tools: true
- frontend_tools: true  
- 说明: 删除节点需调用 backend_tools 删除数据,同时需要 frontend_tools 在界面显示更新后的节点信息。  

##### 5 更新问题
用户问题:帮我把节点J1的名字设置为J1_new  
回答:  
- backend_tools: true
- frontend_tools: true  
- 说明: 更新节点需要调用 backend_tools 保存数据,同时需要 frontend_tools 在界面显示更新后的节点信息。

##### 6 前端问题
用户问题:跳转到J1
回答:
- backend_tools: false
- frontend_tools: true
- 说明: 跳转到J1不需要查询后端数据,所有不需要backend_tools,前端工具可以直接处理跳转。
"""
    # 将历史消息与意图prompt结合
    intent_messages = [HumanMessage(content=intent_prompt)]
    # 获取意图识别结果
    intent_response = await intent_llm.ainvoke(intent_messages)
    response_content = intent_response.content.strip()
    # 解析回答
    need_backend = "backend_tools: true" in response_content
    need_frontend = "frontend_tools: true" in response_content
    agent_logger.info(
        f"{state.get('client_id')} - 意图识别节点LLM响应: {response_content}"
    )

    return {
        "need_backend": need_backend,
        "need_frontend": need_frontend,
    }
