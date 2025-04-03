from pydantic import BaseModel

# TODO：校验问题，可以前端加入校验（使用表达rules），也可以后端加入校验（已校验，但是错误信息不友好） 这里包括除渠道弹窗以外的（节点，出口，不规则断面）
# TODO：理解一下 swmm 计算逻辑，一些节点参数的选择（比如：节点的最大深度，初始深度，溢流深度，蓄水面积），还有没有涉及的功能，是否需要添加此次任务（河道径流模拟）中
# TODO: 完成 提取断面功能，前端界面点击2个点，获取2个点之间的断面高程过程线


class JunctionModel(BaseModel):
    type: str = "junction"
    name: str
    lon: float
    lat: float
    elevation: float = 0.0
    depth_max: float = 0.0
    depth_init: float = 0.0
    depth_surcharge: float = 0.0
    area_ponded: float = 0.0
