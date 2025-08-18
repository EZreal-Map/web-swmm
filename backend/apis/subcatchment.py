from fastapi import APIRouter, HTTPException, Query
from swmm_api import SwmmInput
from swmm_api.input_file.sections import (
    SubCatchment,
    SubArea,
    Infiltration,
    InfiltrationHorton,
    Polygon,
    RainGage,
)
from swmm_api.input_file.sections import Junction, Outfall
from utils.swmm_constant import (
    SWMM_FILE_INP_PATH,
    ENCODING,
)
from schemas.result import Result
from utils.coordinate_converter import polygon_wgs84_to_utm, polygon_utm_to_wgs84
from schemas.subcatchment import (
    SubCatchmentModel,
    SubAreaModel,
    InfiltrationModel,
    PolygonModel,
)
from utils.utils import with_exception_handler

subcatchment = APIRouter()


# 获取子汇水(产流)模型参数 和 子汇水边界
@subcatchment.get(
    "/subcatchments",
    summary="获取子汇水(产流)模型参数",
    description="获取子汇水的产流模型参数,包括名称、雨量计、出水口、面积、不透水率、宽度和坡度,还有子汇水边界",
)
@with_exception_handler(default_message="获取失败,文件有误,发生未知错误")
async def get_subcatchments():
    INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    inp_subcatchments = INP.check_for_section(SubCatchment)
    inp_polygons = INP.check_for_section(Polygon)
    data = []
    for subcatchment in inp_subcatchments.values():
        temp_dict = {}
        # 获取子汇水边界
        name = subcatchment.name
        polygon = inp_polygons.get(name, [])
        if polygon:
            polygon = polygon_utm_to_wgs84(polygon.polygon)
        temp_dict["name"] = name
        temp_dict["rain_gage"] = subcatchment.rain_gage
        temp_dict["outlet"] = subcatchment.outlet
        temp_dict["area"] = subcatchment.area
        temp_dict["imperviousness"] = subcatchment.imperviousness
        temp_dict["width"] = subcatchment.width
        temp_dict["slope"] = subcatchment.slope
        temp_dict["polygon"] = polygon
        data.append(temp_dict)
    return Result.success_result(
        message=f"成功获取子汇水(产流)模型参数和边界数据,共({len(data)}个)",
        data=data,
    )


# 批量获取指定子汇水区的信息
@subcatchment.post(
    "/subcatchments/batch",
    summary="批量获取指定子汇水区的信息",
    description="通过子汇水区名称列表批量获取子汇水区的基本信息,包括名称、雨量计、出水口、面积、不透水率、宽度、坡度和边界。",
)
@with_exception_handler(default_message="获取失败,文件有误,发生未知错误")
async def batch_get_subcatchments_by_names(names: list[str]):
    """通过子汇水区名称列表批量获取子汇水区信息"""
    INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    inp_subcatchments = INP.check_for_section(SubCatchment)
    inp_polygons = INP.check_for_section(Polygon)

    data = []
    found_names = []
    for name in names:
        subcatchment = inp_subcatchments.get(name)
        if not subcatchment:
            continue
        temp_dict = {}
        polygon = inp_polygons.get(name, [])
        if polygon:
            polygon = polygon_utm_to_wgs84(polygon.polygon)
        temp_dict["name"] = name
        temp_dict["rain_gage"] = subcatchment.rain_gage
        temp_dict["outlet"] = subcatchment.outlet
        temp_dict["area"] = subcatchment.area
        temp_dict["imperviousness"] = subcatchment.imperviousness
        temp_dict["width"] = subcatchment.width
        temp_dict["slope"] = subcatchment.slope
        temp_dict["polygon"] = polygon
        data.append(temp_dict)
        found_names.append(name)
    return Result.success_result(
        data=data, message=f"成功获取 {found_names} 子汇水区数据"
    )


# 更新子汇水(产流)模型参数
@subcatchment.put(
    "/subcatchment/{subcatchment_id:path}",
    summary="更新子汇水(产流)模型参数",
    description="通过指定子汇水ID,更新子汇水的产流模型参数",
)
@with_exception_handler(default_message="更新失败,文件有误,发生未知错误")
async def update_subcatchment(
    subcatchment_id: str, subcatchment_update: SubCatchmentModel
):
    INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    inp_subcatchments = INP.check_for_section(SubCatchment)
    inp_junctions = INP.check_for_section(Junction)
    inp_outfalls = INP.check_for_section(Outfall)
    inp_raingages = INP.check_for_section(RainGage)

    # 1.检查子汇水是否存在,如果不存在,则抛出异常
    if subcatchment_id not in inp_subcatchments:
        raise HTTPException(
            status_code=404,
            detail=f"保存失败,需要修改的子汇水名称 [ {subcatchment_id} ] 不存在,请检查子汇水名称是否正确",
        )

    # 2.检查新名称是否已存在,如果新名称与现有子汇水名称冲突,则抛出异常
    if (
        subcatchment_update.name in inp_subcatchments
        and subcatchment_update.name != subcatchment_id
    ):
        raise HTTPException(
            status_code=400,
            detail=f"保存失败,子汇水名称 [ {subcatchment_update.name} ] 已存在,请使用其他名称",
        )

    # 3. 检查出水口的名称是否在节点或出口存在
    # 仅当 outlet 不为 "*" 时才进行校验
    if subcatchment_update.outlet != "*":
        if (
            subcatchment_update.outlet not in inp_junctions
            and subcatchment_update.outlet not in inp_outfalls
        ):
            raise HTTPException(
                status_code=404,
                detail=f"保存失败,出水口名称 [ {subcatchment_update.outlet} ] 不存在,请检查出水口名称是否正确",
            )
    # 4.检查雨量计名称是否存在
    # 仅当 rain_gage 不为 "*" 时才进行校验
    if subcatchment_update.rain_gage != "*":
        if subcatchment_update.rain_gage not in inp_raingages:
            raise HTTPException(
                status_code=404,
                detail=f"保存失败,雨量计名称 [ {subcatchment_update.rain_gage} ] 不存在,请检查雨量计名称是否正确",
            )
    # 5.更新子汇水参数
    del inp_subcatchments[subcatchment_id]
    inp_subcatchments[subcatchment_update.name] = SubCatchment(
        name=subcatchment_update.name,
        rain_gage=subcatchment_update.rain_gage,
        outlet=subcatchment_update.outlet,
        area=subcatchment_update.area,
        imperviousness=subcatchment_update.imperviousness,
        width=subcatchment_update.width,
        slope=subcatchment_update.slope,
    )

    # 6.如果子汇水名称发生变化,同时更新 汇流、下渗、多边形的名字
    if subcatchment_update.name != subcatchment_id:
        # 6.1 更新汇流的名字
        inp_subareas = INP.check_for_section(SubArea)
        temp_subarea = inp_subareas.pop(subcatchment_id)
        temp_subarea.subcatchment = subcatchment_update.name
        inp_subareas[subcatchment_update.name] = temp_subarea
        # 6.2 更新下渗的名字
        inp_infiltrations = INP.check_for_section(Infiltration)
        temp_infiltration = inp_infiltrations.pop(subcatchment_id)
        temp_infiltration.subcatchment = subcatchment_update.name
        inp_infiltrations[subcatchment_update.name] = temp_infiltration
        # 6.3 更新多边形的名字
        inp_polygons = INP.check_for_section(Polygon)
        temp_polygon = inp_polygons.pop(subcatchment_id)
        temp_polygon.subcatchment = subcatchment_update.name
        inp_polygons[subcatchment_update.name] = temp_polygon

    # 保存更新后的输入文件
    INP.write_file(SWMM_FILE_INP_PATH, encoding=ENCODING)

    return Result.success_result(
        message=f"成功更新子汇水区 [{subcatchment_update.name}] 的产流模型参数",
        data={"id": subcatchment_update.name, "type": "subcatchment"},
    )


# 新建一个子汇水区,并设置默认的产流、汇流、下渗模型参数
@subcatchment.post(
    "/subcatchment",
    summary="新建一个子汇水区",
    description="新建一个子汇水区,并设置默认的产流、汇流、下渗模型参数",
)
@with_exception_handler(default_message="新建失败,文件有误,发生未知错误")
async def create_subcatchment(polygon_data: PolygonModel):
    INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    inp_subcatchments = INP.check_for_section(SubCatchment)
    inp_subareas = INP.check_for_section(SubArea)
    inp_infiltrations = INP.check_for_section(Infiltration)
    inp_polygons = INP.check_for_section(Polygon)

    # 检查子汇水名称是否已存在
    if polygon_data.subcatchment in inp_subcatchments:
        raise HTTPException(
            status_code=400,
            detail=f"新建失败,子汇水名称 [ {polygon_data.subcatchment} ] 已存在,请使用其他名称",
        )

    # 1.创建新的子汇水区
    subcatchmentModel = SubCatchmentModel(name=polygon_data.subcatchment)
    inp_subcatchments[polygon_data.subcatchment] = SubCatchment(
        **subcatchmentModel.model_dump()
    )

    # 2.创建默认的产流模型参数
    model = SubAreaModel(subcatchment=polygon_data.subcatchment)
    inp_subareas[polygon_data.subcatchment] = SubArea(**model.model_dump())

    # 3.创建默认的下渗模型参数
    model = InfiltrationModel(subcatchment=polygon_data.subcatchment)
    inp_infiltrations[polygon_data.subcatchment] = InfiltrationHorton(
        **model.model_dump()
    )

    # 4.创建默认的子汇水边界
    polygon_utm = polygon_wgs84_to_utm(polygon_data.polygon)
    inp_polygons[polygon_data.subcatchment] = Polygon(
        subcatchment=polygon_data.subcatchment, polygon=polygon_utm
    )

    # 保存更新后的输入文件
    INP.write_file(SWMM_FILE_INP_PATH, encoding=ENCODING)

    return Result.success_result(
        message=f"成功新建子汇水区 [{polygon_data.subcatchment}]",
        data=subcatchmentModel,
    )


# 删除子汇水区及其相关模型参数
@subcatchment.delete(
    "/subcatchment/{subcatchment_id:path}",
    summary="删除子汇水区",
    description="通过指定子汇水ID,删除子汇水区及其相关模型参数",
)
@with_exception_handler(default_message="删除失败,文件有误,发生未知错误")
async def delete_subcatchment(subcatchment_id: str):
    INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    inp_subcatchments = INP.check_for_section(SubCatchment)
    inp_subareas = INP.check_for_section(SubArea)
    inp_infiltrations = INP.check_for_section(Infiltration)
    inp_polygons = INP.check_for_section(Polygon)

    # 检查子汇水是否存在
    if subcatchment_id not in inp_subcatchments:
        raise HTTPException(
            status_code=404,
            detail=f"删除失败,子汇水名称 [ {subcatchment_id} ] 不存在",
        )

    # 删除子汇水区及其相关模型参数
    del inp_subcatchments[subcatchment_id]
    del inp_subareas[subcatchment_id]
    del inp_infiltrations[subcatchment_id]
    del inp_polygons[subcatchment_id]

    # 保存更新后的输入文件
    INP.write_file(SWMM_FILE_INP_PATH, encoding=ENCODING)

    return Result.success_result(
        message=f"成功删除子汇水区 [{subcatchment_id}] 的相关模型参数"
    )


# 通过子汇水名称获取边界信息
@subcatchment.get(
    "/subcatchment/polygon",
    summary="获取子汇水边界",
    description="获取子汇水的边界数据",
)
@with_exception_handler(default_message="获取失败,文件有误,发生未知错误")
async def get_polygon(name: str = Query(..., description="子汇水名称")):
    INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    inp_polygons = INP.check_for_section(Polygon)

    if name not in inp_polygons:
        raise HTTPException(
            status_code=404,
            detail=f"子汇水 {name} 的边界数据未找到",
        )

    polygon = inp_polygons[name].polygon
    polygon = polygon_utm_to_wgs84(polygon)
    return Result.success_result(
        message=f"成功获取子汇水 {name} 的边界数据",
        data=polygon,
    )


@subcatchment.post(
    "/subcatchment/polygon",
    summary="保存子汇水边界",
    description="保存子汇水的边界数据",
)
@with_exception_handler(default_message="保存失败,文件有误,发生未知错误")
async def save_polygon(data: PolygonModel):
    INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    inp_polygons = INP.check_for_section(Polygon)

    if data.subcatchment not in inp_polygons:
        raise HTTPException(
            status_code=404,
            detail=f"子汇水 {data.subcatchment} 不存在,无法保存边界",
        )

    # WGS84转UTM投影
    polygon_utm = polygon_wgs84_to_utm(data.polygon)

    # 更新内存中的边界数据
    inp_polygons[data.subcatchment].polygon = polygon_utm

    # 保存回文件(假设SwmmInput支持写文件)
    INP.write_file(SWMM_FILE_INP_PATH, encoding=ENCODING)

    return Result.success_result(
        message=f"成功编辑并且保存子汇水区 [{data.subcatchment}] 的边界数据",
    )


@subcatchment.get(
    "/subcatchments/infiltration",
    summary="获取子汇水区霍顿下渗模型参数",
    description="根据子汇水区名称,获取对应的霍顿下渗模型参数",
)
@with_exception_handler(default_message="获取失败,文件有误,发生未知错误")
async def get_infiltration(subcatchment_name=Query(..., description="子汇水区名称")):
    INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    inp_infiltration = INP.check_for_section(Infiltration)

    # 查找对应子汇水区名称的参数
    infiltration = inp_infiltration.get(subcatchment_name)
    if infiltration is None:
        raise HTTPException(
            status_code=404, detail=f"未找到子汇水区'{subcatchment_name}'的下渗参数"
        )

    # 假设返回值结构和 InfiltrationModel 字段对应
    data = InfiltrationModel(
        subcatchment=subcatchment_name,
        rate_max=infiltration.rate_max,
        rate_min=infiltration.rate_min,
        decay=infiltration.decay,
        time_dry=infiltration.time_dry,
        volume_max=infiltration.volume_max,
    )
    return Result.success_result(
        message=f"成功获取子汇水区 [{subcatchment_name}] 的下渗模型参数",
        data=data,
    )


@subcatchment.put(
    "/subcatchments/infiltration",
    summary="修改子汇水区霍顿下渗模型参数",
    description="根据子汇水区名称,修改对应的霍顿下渗模型参数",
)
@with_exception_handler(default_message="更新失败,文件有误,发生未知错误")
async def update_infiltration(
    infiltration_update: InfiltrationModel,
):
    # 读取已有配置
    INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    inp_infiltration = INP.check_for_section(Infiltration)

    # 查找是否存在此子汇水区
    if infiltration_update.subcatchment not in inp_infiltration:
        raise HTTPException(
            status_code=404,
            detail=f"更新失败,未能找到子汇水区'{infiltration_update.subcatchment}'的下渗参数",
        )

    # 修改参数
    infiltration = inp_infiltration[infiltration_update.subcatchment]
    infiltration.rate_max = infiltration_update.rate_max
    infiltration.rate_min = infiltration_update.rate_min
    infiltration.decay = infiltration_update.decay
    infiltration.time_dry = infiltration_update.time_dry
    infiltration.volume_max = infiltration_update.volume_max

    # 保存回文件
    INP.write_file(SWMM_FILE_INP_PATH, encoding=ENCODING)

    return Result.success_result(
        message=f"成功修改子汇水区 [{infiltration_update.subcatchment}] 的下渗模型参数"
    )


@subcatchment.get(
    "/subcatchments/subarea",
    summary="获取子汇水区汇流模型参数",
    description="根据子汇水区名称,获取对应的子汇水区汇流模型参数",
)
@with_exception_handler(default_message="获取失败,文件有误,发生未知错误")
async def get_subarea(subcatchment_name=Query(..., description="子汇水区名称")):
    INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    inp_subareas = INP.check_for_section(SubArea)

    # 查找对应子汇水区名称的参数
    subarea = inp_subareas.get(subcatchment_name)
    if subarea is None:
        raise HTTPException(
            status_code=404, detail=f"未找到子汇水区'{subcatchment_name}'的汇流参数"
        )

    # 转换为 Pydantic 模型
    data = SubAreaModel(
        subcatchment=subcatchment_name,
        n_imperv=subarea.n_imperv,
        n_perv=subarea.n_perv,
        storage_imperv=subarea.storage_imperv,
        storage_perv=subarea.storage_perv,
        pct_zero=subarea.pct_zero,
        route_to=subarea.route_to,
        pct_routed=subarea.pct_routed,
    )

    return Result.success_result(
        message=f"成功获取子汇水区 [{subcatchment_name}] 的汇流模型参数",
        data=data,
    )


@subcatchment.put(
    "/subcatchments/subarea",
    summary="修改子汇水区汇流模型参数",
    description="根据子汇水区名称,修改对应的子汇水区汇流模型参数",
)
@with_exception_handler(default_message="更新失败,文件有误,发生未知错误")
async def update_subarea(
    subarea_update: SubAreaModel,
):
    # 读取已有配置
    INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    inp_subareas = INP.check_for_section(SubArea)

    # 检查子汇水区是否存在
    if subarea_update.subcatchment not in inp_subareas:
        raise HTTPException(
            status_code=404,
            detail=f"更新失败,未能找到子汇水区'{subarea_update.subcatchment}'的汇流参数",
        )

    # 修改参数
    subarea = inp_subareas[subarea_update.subcatchment]
    subarea.n_imperv = subarea_update.n_imperv
    subarea.n_perv = subarea_update.n_perv
    subarea.storage_imperv = subarea_update.storage_imperv
    subarea.storage_perv = subarea_update.storage_perv
    subarea.pct_zero = subarea_update.pct_zero
    subarea.route_to = subarea_update.route_to
    subarea.pct_routed = subarea_update.pct_routed

    # 保存回文件
    INP.write_file(SWMM_FILE_INP_PATH, encoding=ENCODING)

    return Result.success_result(
        message=f"成功修改子汇水区 [{subarea_update.subcatchment}] 的汇流模型参数"
    )
