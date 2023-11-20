import pandas as pd
import WindPy

WindPy.w.start()

trading_datelist = WindPy.w.tdays("20100101", "20301231").Data[0]
trading_datelist = [i.date() for i in trading_datelist]

# from iFinDPy import THS_iFinDLogin, THS_DateQuery
# import pandas as pd

# THS_iFinDLogin("gjzg035", "Asdfg123")

# dd = THS_DateQuery("SSE", "dateType:0,period:D,dateFormat:0", "20100101", "20290101")
# trading_datelist = dd["tables"]["time"]
# trading_datelist = [pd.to_datetime(i).date() for i in trading_datelist]


def ensure_trading_day(current_date):
    """确保当前日期为交易日，否则返回下一个交易日
    Args:
        current_date (datetime/str): 输入的日期
    Returns:
        datetime: 当前交易日或下一个交易日
    """
    if type(current_date) == str:
        current_date = pd.to_datetime(current_date).date()

    if current_date in trading_datelist:
        return current_date
    else:
        next_date = next(date for date in trading_datelist if date > current_date)
        return next_date


def days_between_dates(date1, date2):
    """获取两个自然日之间的日期天数
    Args:
        date1 (datetime): 第一个自然日
        date2 (datetime): 第二个自然日
    Returns:
        int: 两个自然日之间的日期天数
    """
    if date2 > date1:
        delta = date2 - date1
    else:
        delta = date1 - date2
    days_between = delta.days
    return days_between


def months_between_dates(date1, date2):
    """获取两个自然日相距的月份
    Args:
        date1 (datetime): 第一个自然日
        date2 (datetime): 第二个自然日
    Returns:
        int: 两个自然日相距的月份
    """
    start_date = min(date1, date2)
    end_date = max(date1, date2)

    month_diff = (end_date.year - start_date.year) * 12 + (
        end_date.month - start_date.month
    )
    # 注意：
    # 2023-01-07 至 2023-03-01 记作 2个月
    # 2023-01-20 至 2023-03-01 记作 1个月
    if start_date.day > end_date.day + 15:
        month_diff = month_diff - 1
    return month_diff


def last_trading_day(current_date):
    """获取当前日期之前的最后一个交易日
    Args:
        current_date (datetime): 任意日期
    Returns:
        datetime: 该日期之前的最后一个交易日
    """
    if current_date in trading_datelist:
        return trading_datelist[trading_datelist.index(current_date) - 1]
    else:
        return_date = [i for i in trading_datelist if i < current_date][-1]
        return return_date


def get_trading_days_between(date1, date2):
    """获取两个日期之间的全部交易日
    Args:
        date1 (datetime): 开始日期
        date2 (datetime): 结束日期
    Returns:
        list: 两个日期之间的全部交易日列表（包含两端）
    """
    return_list = [i for i in trading_datelist if i >= date1 and i <= date2]
    return return_list


def next_trading_day(current_date):
    """获取当前日期的下一个交易日
    Args:
        current_date (datetime): 任意日期
    Returns:
        datetime: 该日期之前的最后一个交易日
    """
    if current_date in trading_datelist:
        return trading_datelist[trading_datelist.index(current_date) + 1]
    else:
        return_date = [i for i in trading_datelist if i > current_date][0]
        return return_date
