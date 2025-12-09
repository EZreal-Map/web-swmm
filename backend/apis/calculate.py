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
from utils.utils import with_exception_handler
from utils.logger import get_logger

# 获取日志记录器
logger = get_logger("calculate")


calculateRouter = APIRouter()


# 获取计算选项(参数)
@calculateRouter.get(
    "/calculate/options",
    summary="获取计算选项",
    description="""
获取模拟计算的参数配置,包括:
- `flow_units`:流量单位(默认 `"CMS"`,可选:CFS、GPM、MGD、CMS、LPS、MLD)
- `start_datetime`:模拟开始时间(格式:YYYY-MM-DDTHH:MM:SS)
- `end_datetime`:模拟结束时间
- `report_step`:输出时间步长(格式:HH:MM:SS,默认 00:15:00)
- `flow_routing`:流量计算方法(默认 `"KINWAVE"`,可选:STEADY、KINWAVE、DYNWAVE)
""",
)
@with_exception_handler(default_message="获取失败,文件有误,发生未知错误")
async def get_calculate_options():
    INP = SwmmInput.read_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    inp_options = INP.check_for_section(OptionSection)
    flow_units = inp_options.get("FLOW_UNITS")
    report_step = inp_options.get("REPORT_STEP")
    flow_routing = inp_options.get("FLOW_ROUTING")
    start_date = inp_options.get("START_DATE")
    start_time = inp_options.get("START_TIME")
    end_date = inp_options.get("END_DATE")
    end_time = inp_options.get("END_TIME")
    report_start_date = inp_options.get("REPORT_START_DATE")
    report_start_time = inp_options.get("REPORT_START_TIME")
    # 拼接为 datetime
    start_datetime = datetime.combine(start_date, start_time)
    end_datetime = datetime.combine(end_date, end_time)
    start_report_datetime = datetime.combine(report_start_date, report_start_time)

    calculate_model = CalculateModel(
        flow_units=flow_units,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        report_step=report_step,
        flow_routing=flow_routing,
        start_report_datetime=start_report_datetime,
    )
    return Result.success_result(
        message="成功获取计算选项",
        data=calculate_model,
    )


# 保存更新计算选项(参数)
@calculateRouter.put(
    "/calculate/options",
    summary="保存更新计算选项",
    description="保存更新计算选项",
)
@with_exception_handler(default_message="更新失败,文件有误,发生未知错误")
async def update_calculate_options(calculate_model: CalculateModel):
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
            "REPORT_START_DATE": calculate_model.start_report_datetime.date(),
            "REPORT_START_TIME": calculate_model.start_report_datetime.time(),
        }
    )
    # 保存文件
    INP.write_file(SWMM_FILE_INP_PATH, encoding=ENCODING)
    return Result.success_result(message="成功更新计算选项")


# 传入一个查询实体名称,判断是node/link 还是都不属于,都不属于则返回错误
@calculateRouter.get(
    "/calculate/result/kind",
    summary="判断查询实体名称是否属于节点或链接",
    description="传入一个查询实体名称,判断是 node / link 还是都不属于,都不属于则返回错误,大概率是没找到这个查询实体名称",
)
@with_exception_handler(default_message="查询失败,没有计算结果,请先计算")
async def query_entity_kind_select(name: str):
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
        return Result.success_result(message="查询实体成功", data=data)
    # 获取链接列名
    columns_for_link = (
        df.columns[df.columns.get_level_values(0) == "link"]
        .get_level_values(1)
        .unique()
        .tolist()
    )
    if name in columns_for_link:
        data = {"kind": "link", "select": LINK_RESULT_VARIABLE_SELECT}
        return Result.success_result(message="查询实体成功", data=data)
    # 如果都不属于,则返回提示信息
    return Result.error(
        message="查询实体名称不属于节点或链接,请检查输入的名称是否正确",
        data=[],
    )


# 计算结果查询,通过传入 kind name variable
# kind: node or link
# name: 节点或链接名称
# variable: 查询变量名称
@calculateRouter.get(
    "/calculate/result",
    summary="计算结果查询",
    description="""
查询指定对象的模拟计算结果。

参数说明:
- `kind`:对象类型,支持的值有:
  - `"node"`:节点
  - `"link"`:链路

- `name`:对象名称,例如节点名或管道名。

- `variable`:查询变量名称,依据 `kind` 类型的不同,`variable` 变量的选项有所不同(传入的是英文):
  - 对于 `kind="node"`(节点),可选值包括:
    - `"depth"`:深度
    - `"head"`:水头
    - `"volume"`:容积
    - `"lateral_inflow"`:侧边进流量
    - `"total_inflow"`:总进流量
    - `"flooding"`:积水
  - 对于 `kind="link"`(链路),可选值包括:
    - `"flow"`:流量
    - `"depth"`:深度
    - `"velocity"`:流速
    - `"volume"`:容积
    - `"capacity"`:能力

通过传入上述参数,返回对应对象在整个模拟时间范围内的时序计算结果。
实例:kind=node name=J1 variable=depth
""",
)
@with_exception_handler(default_message="查询失败,文件有误,发生未知错误")
async def query_calculate_result(kind: str, name: str, variable: str):
    OUT = SwmmOutput(SWMM_FILE_OUT_PATH, encoding=ENCODING)
    data = OUT.get_part(kind, name, variable)
    if data.empty:
        return Result.error(
            message="查询结果为空,请检查输入的名称是否正确",
            data=[],
        )
    # 格式化 data 输出
    # 1.将数据转换为list [[], []],方便前端 echarts 使用,并且值保留两位小数
    data = data.round(2)
    data_list = [[index, value] for index, value in data.items()]
    logger.info(
        f"查询结果: kind={kind}, name={name}, variable={variable}, data={data_list}"
    )
    return Result.success_result(
        message="结果查询成功",
        data=data_list,
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
        return Result.success_result(message="计算成功")
    except Exception as e:
        error_msg = extract_errors(str(e))
        logger.error(f"SWMM 计算失败: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)


def extract_errors(log_text):
    # 把错误解读的字符串转成 utf-8 字节,再用 GB2312 解码回来
    log_text = fix_garbled_text(log_text)
    # 将日志文本按行拆分
    lines = log_text.splitlines()
    # 用于存储提取的错误信息
    errors = []
    # 设一个标志位,标记是否已遇到 .inp 行
    found_inp = False
    # 遍历每一行
    for line in lines:
        # 如果找到 .inp 后缀的行,开始记录所有后续的行
        if ".inp" in line:
            found_inp = True
        # 如果找到 ERROR 相关的行,且已经找到 .inp 行,保留这行及之后的所有行
        if found_inp and line.startswith("ERROR"):
            # 使用正则表达式提取单引号之间的内容
            matches = re.findall(r"'(.*?)'", line)
            errors.extend(matches)  # 将找到的错误信息添加到列表中

    error_msg = "计算时发生错误:\n"
    for index, error in enumerate(errors):  # 确保 index 在前面
        error_msg += f"{index+1}、{error}\n"  # 添加换行符以便每个错误独占一行
    return error_msg.strip()  # 去除首尾空白字符


def fix_garbled_text(text: str) -> str:
    """
    修复可能因编码错误导致的乱码字符串
    原始中文 → 用 gb2312 编码 → 被错误地当成 utf-8 解码 → 出现乱码
    然后我们想办法通过 latin1 编码 → gb2312 解码 来"复原"。
    """
    try:
        return text.encode("latin1").decode("gb2312")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text  # 如果失败就原样返回 (一般是utf-8编码,解析也是utf-8)
