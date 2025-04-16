from fastapi import APIRouter, HTTPException
from swmm_api import SwmmInput, swmm5_run
from swmm_api.input_file.sections import OptionSection
from datetime import datetime, timezone, timedelta
from pathlib import Path
import re
from schemas.calculate import CalculateModel
from schemas.result import Result
from swmm_api import SwmmOutput
from utils.swmm_constant import (
    NODE_RESULT_VARIABLE_SELECT,
    LINK_RESULT_VARIABLE_SELECT,
    SWMM_FILE_INP_PATH,
    SWMM_FILE_OUT_PATH,
    ENCODING,
)


calculateRouter = APIRouter()


# 获取计算选项（参数）
@calculateRouter.get(
    "/calculate/options",
    summary="获取计算选项",
    description="获取计算选项",
)
async def get_calculate_options():
    try:
        INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
        inp_options = INP.check_for_section(OptionSection)
        flow_units = inp_options.get("FLOW_UNITS")
        report_step = inp_options.get("REPORT_STEP")
        flow_routing = inp_options.get("FLOW_ROUTING")
        start_date = inp_options.get("START_DATE")
        start_time = inp_options.get("START_TIME")
        end_date = inp_options.get("END_DATE")
        end_time = inp_options.get("END_TIME")
        # 拼接为 datetime
        start_datetime = datetime.combine(start_date, start_time)
        end_datetime = datetime.combine(end_date, end_time)
        # 设置为东八区时间（UTC+8）
        start_datetime = start_datetime.replace(tzinfo=timezone(timedelta(hours=8)))
        end_datetime = end_datetime.replace(tzinfo=timezone(timedelta(hours=8)))

        calculate_model = CalculateModel(
            flow_units=flow_units,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            report_step=report_step,
            flow_routing=flow_routing,
        )
        return Result.success(
            message="成功获取计算选项",
            data=calculate_model,
        )
    except Exception as e:
        # 捕获异常并返回错误信息
        raise HTTPException(
            status_code=e.status_code if hasattr(e, "status_code") else 500,
            detail=f"{str(e.detail) if hasattr(e, 'detail') else '获取失败，文件有误，发生未知错误'}",
        )


# 保存更新计算选项（参数）
@calculateRouter.put(
    "/calculate/options",
    summary="保存更新计算选项",
    description="保存更新计算选项",
)
async def update_calculate_options(calculate_model: CalculateModel):
    try:
        INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
        inp_options = INP.check_for_section(OptionSection)

        # 更新选项
        inp_options.update(
            {
                "FLOW_UNITS": calculate_model.flow_units,
                "REPORT_STEP": calculate_model.report_step,
                "FLOW_ROUTING": calculate_model.flow_routing,
                "START_DATE": calculate_model.start_datetime.date(),
                "START_TIME": calculate_model.start_datetime.time(),
                "END_DATE": calculate_model.end_datetime.date(),
                "END_TIME": calculate_model.end_datetime.time(),
                # 把 开始报告时间 默认处理为 开始计算时间
                "REPORT_START_DATE": calculate_model.start_datetime.date(),
                "REPORT_START_TIME": calculate_model.start_datetime.time(),
            }
        )
        # 保存文件
        INP.write_file(SWMM_FILE_INP_PATH, encoding=ENCODING)

        return Result.success(message="成功更新计算选项")
    except Exception as e:
        # 捕获异常并返回错误信息
        raise HTTPException(
            status_code=e.status_code if hasattr(e, "status_code") else 500,
            detail=f"{str(e.detail) if hasattr(e, 'detail') else '更新失败，文件有误，发生未知错误'}",
        )


# 传入一个查询实体名称，判断是node/link 还是都不属于，都不属于则返回错误
@calculateRouter.get(
    "/calculate/result/kind",
    summary="判断查询实体名称是否属于节点或链接",
    description="传入一个查询实体名称，判断是node/link 还是都不属于，都不属于则返回错误",
)
async def query_entity_kind_select(name: str):
    try:
        OUT = SwmmOutput(SWMM_FILE_OUT_PATH, encoding=ENCODING)
        df = OUT.to_frame()
        # 获取节点列名
        columns_for_node = (
            df.columns[df.columns.get_level_values(0) == "node"]
            .get_level_values(1)
            .unique()
            .tolist()
        )
        if name in columns_for_node:
            data = {"kind": "node", "select": NODE_RESULT_VARIABLE_SELECT}
            return Result.success(message="查询实体成功", data=data)
        # 获取链接列名
        columns_for_link = (
            df.columns[df.columns.get_level_values(0) == "link"]
            .get_level_values(1)
            .unique()
            .tolist()
        )
        if name in columns_for_link:
            data = {"kind": "link", "select": LINK_RESULT_VARIABLE_SELECT}
            return Result.success(message="查询实体成功", data=data)
        # 如果都不属于，则返回提示信息
        return Result.error(
            message="查询实体名称不属于节点或链接，请检查输入的名称是否正确",
            data=[],
        )
    except Exception as e:
        # 捕获异常并返回错误信息
        raise HTTPException(
            status_code=e.status_code if hasattr(e, "status_code") else 500,
            detail=f"{str(e.detail) if hasattr(e, 'detail') else '查询失败，没有计算结果，请先计算'}",
        )


# 计算结果查询，通过传入 kind name variable
# kind: node or link
# name: 节点或链接名称
# variable: 查询变量名称
@calculateRouter.get(
    "/calculate/result",
    summary="计算结果查询",
    description="计算结果查询，通过传入 kind name variable",
)
async def query_calculate_result(kind: str, name: str, variable: str):
    try:
        OUT = SwmmOutput(SWMM_FILE_OUT_PATH, encoding=ENCODING)
        data = OUT.get_part(kind, name, variable)
        if data.empty:
            return Result.error(
                message="查询结果为空，请检查输入的名称是否正确",
                data=[],
            )
        # 格式化 data 输出
        # 1.index 是 naive datetime（无时区信息），先设为 UTC 再转为东八区
        data.index = data.index.tz_localize("UTC").tz_convert("Asia/Shanghai")
        # 2.将数据转换为list [[], []]，方便前端 echarts 使用，并且值保留两位小数
        data = data.round(2)
        data_list = [[index, value] for index, value in data.items()]
        return Result.success(
            message="结果查询成功",
            data=data_list,
        )
    except Exception as e:
        # 捕获异常并返回错误信息
        raise HTTPException(
            status_code=e.status_code if hasattr(e, "status_code") else 500,
            detail=f"{str(e.detail) if hasattr(e, 'detail') else '查询失败，文件有误，发生未知错误'}",
        )


# 进行计算
@calculateRouter.post(
    "/calculate/run",
    summary="进行计算",
    description="进行计算",
)
async def run_calculation():
    try:
        # 运行 SWMM 模型
        INP_ABSOLUTE_PATH = Path(SWMM_FILE_INP_PATH).resolve()
        swmm5_run(INP_ABSOLUTE_PATH)
        return Result.success(message="计算成功")
    except Exception as e:
        error_msg = extract_errors(str(e))
        print(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


def extract_errors(log_text):
    # 把错误解读的字符串转成 utf-8 字节，再用 GB2312 解码回来
    log_text = fix_garbled_text(log_text)
    # 将日志文本按行拆分
    lines = log_text.splitlines()
    # 用于存储提取的错误信息
    errors = []
    # 设一个标志位，标记是否已遇到 .inp 行
    found_inp = False
    # 遍历每一行
    for line in lines:
        # 如果找到 .inp 后缀的行，开始记录所有后续的行
        if ".inp" in line:
            found_inp = True
        # 如果找到 ERROR 相关的行，且已经找到 .inp 行，保留这行及之后的所有行
        if found_inp and line.startswith("ERROR"):
            # 使用正则表达式提取单引号之间的内容
            matches = re.findall(r"'(.*?)'", line)
            errors.extend(matches)  # 将找到的错误信息添加到列表中

    error_msg = "运行 SWMM 时发生错误:\n"
    for index, error in enumerate(errors):  # 确保 index 在前面
        error_msg += f"{index+1}、{error}\n"  # 添加换行符以便每个错误独占一行
    return error_msg


def fix_garbled_text(text: str) -> str:
    """
    修复可能因编码错误导致的乱码字符串
    原始中文 → 用 gb2312 编码 → 被错误地当成 utf-8 解码 → 出现乱码
    然后我们想办法通过 latin1 编码 → gb2312 解码 来“复原”。
    """
    try:
        return text.encode("latin1").decode("gb2312")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text  # 如果失败就原样返回 (一般是utf-8编码，解析也是utf-8)
