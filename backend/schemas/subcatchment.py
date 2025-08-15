from pydantic import BaseModel, Field, field_validator
from typing import Literal
from fastapi import HTTPException


class SubCatchmentModel(BaseModel):
    """子汇水(产流) 模型参数"""

    name: str = Field(..., description="子汇水区的名称")
    rain_gage: str = Field(
        "*",  # 默认值为 "*"
        description="分配给该子汇水区的雨量计名称(对应SWMM输入文件中的[RAINGAGES]部分)",
    )
    outlet: str = Field("*", description="接收该子汇水区径流的节点或子汇水区名称")
    area: float = Field(5.0, description="子汇水区面积(单位:英亩或公顷)")
    imperviousness: float = Field(25.0, description="子汇水区的不透水率百分比")
    width: float = Field(500.0, description="子汇水区的特征宽度(单位:英尺或米)")
    slope: float = Field(0.5, description="子汇水区坡度(百分比)")

    @field_validator("rain_gage", "outlet", mode="before")
    def validate_non_empty(cls, v, info):
        # field_name 的别名
        if info.field_name == "rain_gage":
            field_name_alias = "雨量计"
        elif info.field_name == "outlet":
            field_name_alias = "出水口"
        else:
            field_name_alias = info.field_name
        # 检查是否为空
        if v is None or str(v).strip() == "":
            raise HTTPException(
                status_code=400,
                detail=f"保存失败,字段 '{field_name_alias}' 不能为空",
            )
        return v

    @field_validator("area", "imperviousness", "width", "slope", mode="before")
    def validate_non_empty_and_non_negative(cls, v, info):
        # field_name 的别名
        if info.field_name == "area":
            field_name_alias = "面积"
        elif info.field_name == "imperviousness":
            field_name_alias = "不透水率"
        elif info.field_name == "width":
            field_name_alias = "宽度"
        elif info.field_name == "slope":
            field_name_alias = "坡度"
        else:
            field_name_alias = info.field_name
        # 检查数值类型和正数
        if v is None or str(v).strip() == "":
            raise HTTPException(
                status_code=400,
                detail=f"保存失败,字段 '{field_name_alias}' 不能为空",
            )
        try:
            value = float(v)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"保存失败,字段 '{field_name_alias}' 必须为数字",
            )
        if value < 0:
            raise HTTPException(
                status_code=400,
                detail=f"保存失败,字段 '{field_name_alias}' 不能为负数",
            )
        return value


class SubAreaModel(BaseModel):
    """子汇水(汇流)模型参数"""

    subcatchment: str = Field(..., description="子汇水区名称")
    n_imperv: float = Field(0.01, description="不透水子区的曼宁粗糙系数 (s*m^(-1/3))")
    n_perv: float = Field(0.1, description="渗透子区的曼宁粗糙系数 (s*m^(-1/3))")
    storage_imperv: float = Field(1, description="不透水子区的凹陷储存量(毫米)")
    storage_perv: float = Field(1, description="渗透子区的凹陷储存量(毫米)")
    pct_zero: float = Field(25.0, description="无凹陷储存的不透水面积百分比")
    route_to: Literal["IMPERVIOUS", "PERVIOUS", "OUTLET"] = "OUTLET"
    pct_routed: float = Field(
        100.0, description="从一种子区径流流向另一种子区的百分比 (演算百分比)"
    )

    @field_validator("pct_zero", "pct_routed", mode="before")
    def validate_percentage(cls, v):
        if not (0 <= v <= 100):
            raise HTTPException(
                status_code=400,
                detail="保存失败,百分比必须在0到100之间",
            )
        return v

    @field_validator(
        "n_imperv", "n_perv", "storage_imperv", "storage_perv", mode="before"
    )
    def validate_non_empty_and_non_negative(cls, v, info):
        # field_name 的别名
        if info.field_name == "n_imperv":
            field_name_alias = "不透水子区的曼宁粗糙系数"
        elif info.field_name == "n_perv":
            field_name_alias = "渗透子区的曼宁粗糙系数"
        elif info.field_name == "storage_imperv":
            field_name_alias = "不透水子区的凹陷储存量"
        elif info.field_name == "storage_perv":
            field_name_alias = "渗透子区的凹陷储存量"
        else:
            field_name_alias = info.field_name
        # 检查数值类型和正数
        if v is None or str(v).strip() == "":
            raise HTTPException(
                status_code=400,
                detail=f"保存失败,字段 '{field_name_alias}' 不能为空",
            )
        try:
            value = float(v)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"保存失败,字段 '{field_name_alias}' 必须为数字",
            )
        if value < 0:
            raise HTTPException(
                status_code=400,
                detail=f"保存失败,字段 '{field_name_alias}' 不能为负数",
            )
        return value


class InfiltrationModel(BaseModel):
    """霍顿下渗模型"""

    subcatchment: str = Field(..., description="子汇水区名称")
    rate_max: float = Field(3.0, description="霍顿曲线最大入渗速率(mm/hr)")
    rate_min: float = Field(0.5, description="霍顿曲线最小入渗速率(mm/hr)")
    decay: float = Field(4.0, description="霍顿曲线衰减常数(1/hr)")
    time_dry: float = Field(7.0, description="土壤完全饱和后干燥时间(天)")
    volume_max: float = Field(0.0, description="最大入渗体积(单位mm,若无则为0)")

    @field_validator(
        "rate_max", "rate_min", "decay", "time_dry", "volume_max", mode="before"
    )
    def validate_non_empty_and_non_negative(cls, v, info):
        # field_name 的别名
        if info.field_name == "rate_max":
            field_name_alias = "霍顿曲线最大入渗速率"
        elif info.field_name == "rate_min":
            field_name_alias = "霍顿曲线最小入渗速率"
        elif info.field_name == "decay":
            field_name_alias = "霍顿曲线衰减常数"
        elif info.field_name == "time_dry":
            field_name_alias = "土壤完全饱和后干燥时间"
        elif info.field_name == "volume_max":
            field_name_alias = "最大入渗体积"
        else:
            field_name_alias = info.field_name
        # 检查数值类型和正数
        if v is None or str(v).strip() == "":
            raise HTTPException(
                status_code=400,
                detail=f"保存失败,字段 '{field_name_alias}' 不能为空",
            )
        try:
            value = float(v)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"保存失败,字段 '{field_name_alias}' 必须为数字",
            )
        if value < 0:
            raise HTTPException(
                status_code=400,
                detail=f"保存失败,字段 '{field_name_alias}' 不能为负数",
            )
        return value


class PolygonModel(BaseModel):
    """子汇水多边形数据"""

    subcatchment: str = Field(..., description="子汇水名称")
    polygon: list[tuple[float, float]] = Field(
        ..., description="多边形顶点坐标列表,点格式为(x, y),浮点数"
    )
