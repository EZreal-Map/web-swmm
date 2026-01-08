from swmm_api.input_file.sections import RainGage, Symbol, SubCatchment
from utils.swmm_constant import RAINGAGE_DEFAULT_INTERVAL
from utils.utils import remove_timeseries_prefix


def create_raingage(
    INP,
    timeseries_name: str,
    interval: str = RAINGAGE_DEFAULT_INTERVAL,  # 默认时间间隔为 1 小时
    x: float = 0.0,
    y: float = 0.0,
    form: str = "INTENSITY",
    SCF: float = 1.0,
):
    """
    创建绑定 timeseries 的 RainGage 对象以及对应的 Symbol 坐标。

    Args:
        name (str): 雨量计名称。
        interval (str): 时间间隔(如 '0:15' 表示每15分钟)。
        timeseries_name (str): 时间序列名称,需在 [TIMESERIES] 段中定义。
        x (float): 雨量计 X 坐标(默认 0.0)。
        y (float): 雨量计 Y 坐标(默认 0.0)。
        form (str): 降雨格式(默认为 'INTENSITY')。
        SCF (float): 雪修正因子(默认 1.0)。

    Returns:
        Tuple[RainGage, Symbol]: 一个绑定好的雨量计对象和其地图符号对象。
    """
    inp_rain_gages = INP.check_for_section(RainGage)
    inp_symbols = INP.check_for_section(Symbol)
    # 把 timeseries_name 转换为 raingage 的 name
    name = remove_timeseries_prefix(timeseries_name)
    # 检查雨量计名称是否已存在
    if name in inp_rain_gages:
        raise ValueError(f"雨量计名称 '{name}' 已存在,请使用不同的名称。")
    # 添加新的雨量计到 INP
    inp_rain_gages[name] = RainGage(
        name=name,
        form=form,
        interval=interval,
        SCF=SCF,
        source="TIMESERIES",
        timeseries=timeseries_name,
    )
    # 添加对应的符号(位置)到 INP
    inp_symbols[name] = Symbol(gage=name, x=x, y=y)
    return True


def delete_raingage(INP, timeseries_name: str):
    """
    删除指定名称的 RainGage 和对应的 Symbol。

    Args:
        INP: swmm_api 读入的 INP 对象。
        timeseries_name (str): 雨量计名称。

    Returns:
        bool: 删除成功返回 True,若未找到该名称则抛出异常。
    """
    inp_rain_gages = INP.check_for_section(RainGage)
    inp_symbols = INP.check_for_section(Symbol)

    # 把 timeseries_name 转换为 raingage 的 name
    name = remove_timeseries_prefix(timeseries_name)
    # 检查并删除 RainGage
    if name in inp_rain_gages:
        del inp_rain_gages[name]

    # 检查并删除 Symbol
    if name in inp_symbols:
        del inp_symbols[name]

    # 更新(删除)关联的子汇水区雨量计名称
    inp_subcatchments = INP.check_for_section(SubCatchment)
    for subcatchment in inp_subcatchments.values():
        if subcatchment.rain_gage == name:
            subcatchment.rain_gage = "*"  # 清空雨量计名称

    return True


def update_raingage(
    INP,
    timeseries_name: str,
    new_timeseries_name: str,
    interval: str = None,
):
    """
    更新指定名称的 RainGage 的 name、interval 和 timeseries。

    如果 new_name 和 name 不同,则执行删除旧的 RainGage 和 Symbol,
    并用新名称重新创建(保留原来的其他属性)。

    Args:
        INP: swmm_api 读入的 INP 对象。
        name (str): 当前雨量计名称。
        new_name (str): 新雨量计名称。
        interval (str, optional): 新的时间间隔(如 '0:15'),不传则保持原值。间隔时间通过 timeseriers 获取

    Returns:
        bool: 更新成功返回 True,若未找到该名称则抛出异常。
    """
    inp_rain_gages = INP.check_for_section(RainGage)
    inp_symbols = INP.check_for_section(Symbol)
    related_entity_ids = []  # 用于记录更新了哪些子汇水区的雨量计名称 (也是返回值)

    # 把 timeseries_name 转换为 raingage 的 name
    # timeseries_name 和 new_timeseries_name 带有前缀, 而 raingage 的 name 不带前缀, 并且 子汇水区引用的也是raingage的 name
    name = remove_timeseries_prefix(timeseries_name)
    new_name = remove_timeseries_prefix(new_timeseries_name)

    if name not in inp_rain_gages:
        raise ValueError(f"RainGage '{name}' 不存在,无法更新。")

    # 1.名称不变,直接修改属性
    if new_name == name:
        raingage = inp_rain_gages[name]
        if interval is not None:
            raingage.interval = interval
    # 2.名称变更,先检查新名称是否存在,避免冲突
    else:
        if new_name in inp_rain_gages:
            raise ValueError(f"新雨量计名称 '{new_name}' 已存在,请使用不同的名称。")
        # 2.1 取出原雨量计对象和符号
        raingage_old = inp_rain_gages[name]
        symbol_old = inp_symbols.get(name)

        # 2.2 删除旧的 raingage和 symbol
        del inp_rain_gages[name]
        del inp_symbols[name]

        # 2.3 创建新的,保留旧对象的属性,更新可选属性和新名称
        raingage_new = RainGage(
            name=new_name,
            form=raingage_old.form,
            interval=interval if interval is not None else raingage_old.interval,
            SCF=raingage_old.SCF,
            source=raingage_old.source,
            timeseries=new_timeseries_name,
        )
        inp_rain_gages[new_name] = raingage_new

        # 同步更新 Symbol 坐标的名称
        inp_symbols[new_name] = Symbol(gage=new_name, x=symbol_old.x, y=symbol_old.y)

        # 3.更新子汇水区的雨量计名称

        inp_subcatchments = INP.check_for_section(SubCatchment)
        for subcatchment in inp_subcatchments.values():
            if subcatchment.rain_gage == name:
                subcatchment.rain_gage = new_name
                related_entity_ids.append(subcatchment.name)

    return related_entity_ids
