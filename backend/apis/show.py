from fastapi import APIRouter, HTTPException
from schemas.result import Result
from utils.swmm_constant import SWMM_FILE_OUT_PATH, SWMM_FILE_INP_PATH, ENCODING
from swmm_api import SwmmOutput, SwmmInput
from swmm_api.input_file.sections import Junction
from swmm_api.input_file.sections.link import Conduit
from swmm_api.input_file.sections.node_component import Coordinate
from swmm_api.input_file.sections import Outfall
from utils.coordinate_converter import utm_to_wgs84

showRouter = APIRouter()


@showRouter.get("/show", summary="计算结果滚动展示")
async def show_calculate_result():
    try:
        OUT = SwmmOutput(SWMM_FILE_OUT_PATH, encoding=ENCODING)
        INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
        inp_junctions = INP.check_for_section(Junction)
        inp_coordinates = INP.check_for_section(Coordinate)
        inp_conduits = INP.check_for_section(Conduit)
        inp_outfalls = INP.check_for_section(Outfall)
        df = OUT.to_frame()
        columns_for_node = df.columns[df.columns.get_level_values(0) == "link"]
        conduit_names = columns_for_node.get_level_values(1).unique().tolist()
        variables = ["flow", "depth", "velocity"]
        # 0.1 变量极值
        variables_extremes = get_link_variable_extremes(df, variables=variables)
        data = {}
        data["variables_extremes"] = variables_extremes
        # 0.2 计算时间列表
        # 获取时间索引
        time_index = df.index.tolist()
        # 转换为字符串格式
        time_list = [time.strftime("%Y-%m-%d %H:%M") for time in time_index]
        data["time"] = time_list
        result_data = []
        for name in conduit_names:
            temp_data = {}
            # 1.基础数据
            temp_data["name"] = name
            temp_data["type"] = "conduit"
            # temp_data["time"] = df.index.tolist()

            # 2.拓扑属性
            from_node = get_from_node_info(
                name,
                "from_node",
                inp_conduits,
                inp_coordinates,
                inp_junctions,
                inp_outfalls,
            )
            to_node = get_from_node_info(
                name,
                "to_node",
                inp_conduits,
                inp_coordinates,
                inp_junctions,
                inp_outfalls,
            )
            temp_data["from_node"] = from_node
            temp_data["to_node"] = to_node

            # 3.拼接计算数据 变量在variables中
            columns = df.columns[
                (df.columns.get_level_values(0) == "link")
                & (df.columns.get_level_values(1) == name)
                & (df.columns.get_level_values(2).isin(variables))
            ]
            for i, variable in enumerate(variables):
                temp_data[variable] = df[columns[i]].tolist()

            result_data.append(temp_data)
        data["calculate_result"] = result_data
        return Result.success(
            data=data,
            message="计算结果列表",
        )
    except Exception as e:
        # 捕获异常并返回错误信息
        raise HTTPException(
            status_code=e.status_code if hasattr(e, "status_code") else 500,
            detail=f"{str(e.detail) if hasattr(e, 'detail') else '获取失败，文件有误，发生未知错误'}",
        )


def get_from_node_info(
    conduit_name, dict_name, inp_conduits, inp_coordinates, inp_junctions, inp_outfalls
):
    """
    获取指定 conduit 的起点节点信息，包括类型、名称、经纬度坐标。

    参数：
        conduit_name: 管道名称
        dict_name: "from_node" / "to_node"
        inp_conduits: 管道信息字典
        inp_coordinates: 坐标信息字典
        inp_junctions: 交叉口信息字典

    返回：
        from_node: 字典，包含 'type'、'name'、'lon'、'lat'；如果未找到，返回 None
    """
    node_info = inp_conduits.get(conduit_name)
    if not node_info:
        return None

    from_node_name = node_info.get(dict_name)
    if not from_node_name:
        return None

    from_node_coords = inp_coordinates.get(from_node_name)
    if not from_node_coords:
        return None

    try:
        lon, lat = utm_to_wgs84(from_node_coords.x, from_node_coords.y)
    except Exception:
        return None

    if inp_junctions.get(from_node_name):
        node_type = "junction"
    elif inp_outfalls.get(from_node_name):
        node_type = "outfall"
    else:
        node_type = None

    return {"type": node_type, "name": from_node_name, "lon": lon, "lat": lat}


def get_link_variable_extremes(df, variables=["flow", "depth", "velocity"]):
    """
    获取 df 中 link 类型的 flow / depth / velocity 三个变量的最大值和最小值

    返回结构：
    {
        "flow": {"max": ..., "min": ...},
        "depth": {"max": ..., "min": ...},
        "velocity": {"max": ..., "min": ...},
    }
    """
    result = {}

    for var in variables:
        # 获取所有满足 (link, *, var) 的列
        cols = df.columns[
            (df.columns.get_level_values(0) == "link")
            & (df.columns.get_level_values(2) == var)
        ]

        if not cols.empty:
            data = df[cols]
            result[var] = {
                "max": data.max().max(),  # 所有列的最大值，再取最大
                "min": data.min().min(),  # 所有列的最小值，再取最小
            }
        else:
            result[var] = {"max": None, "min": None}

    return result
