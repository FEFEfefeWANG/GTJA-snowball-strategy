# -*- coding: utf-8 -*-

"""
Created on Tue Dec 15 15:42:07 2020
Revised on Wed Oct 18 10:57:30 2023

@author: liuguixu 
Revised by: Fan Chen
Revised by: Junyi Wang

"""

"""多种雪球结构类"""


from dateutil.relativedelta import relativedelta
from datetime import datetime
import pandas as pd
from tools import *


class SnowballOption:
    @staticmethod
    def create_snowball(snowball_type, *args, **kwargs):
        if snowball_type == "经典雪球":
            return ClassicSnowball(*args, **kwargs)
        elif snowball_type == "降敲型雪球":
            return StepdownSnowball(*args, **kwargs)
        elif snowball_type == "限亏型雪球":
            return LimitedLossSnowball(*args, **kwargs)
        elif snowball_type == "限亏止盈型雪球":
            return LimitedLossAndProfitSnowball(*args, **kwargs)
        elif snowball_type == "早利型雪球":
            return EarlyYieldSnowball(*args, **kwargs)
        else:
            raise ValueError(f"Unknown snowball_type: {snowball_type}")


class BaseSnowball(object):
    def __init__(
        self,
        snowball_type,
        underlying,
        time_fixed_param,
        knockin_param,
        knockout_param,
        coupon_param,
        profit_param,
    ):
        self.underlying = underlying  # 标的代码
        self.snowball_type = snowball_type  # 雪球类型
        self.time_fixed_param = time_fixed_param  # 时间固定参数：包括敲入条件
        self.knockin_param = knockin_param  # 敲入参数：包括敲入条件
        self.knockout_param = knockout_param  # 敲出参数：包括首个敲出观察日，敲出条件，敲出观察频率，每月下调比例
        self.coupon_param = coupon_param  # 票息参数：包括敲出票息与红利票息
        self.profit_param = profit_param  # 不可追保则最大损失1 (即全部保证金)

        self.knockin_price = None  # 标的敲入价格
        self.knockout_price = None  # 标的敲出价格
        self.knockin_date = None  # 标的敲入日期
        self.knockout_date = None  # 标的敲出日期
        self.terminal_month = None  # 合约终止月份
        self.status = None  # 敲入敲出状态
        self.maturity_sign = None  # 合约是否完结

    def set_time_param(self, time_dynamic_param):
        self.time_dynamic_param = time_dynamic_param  # 时间可变参数：包括合约起始日期,合约长度与合约到期日

    def is_maturity(self):
        """判断截止上一个交易日，雪球产品是否到期"""
        yesterday = last_trading_day(datetime.now().date())
        if self.time_dynamic_param["end_date"] > yesterday:
            self.maturity_sign = False
        else:
            self.maturity_sign = True

    def reset_state(self):
        """重设状态"""
        self.knockin_price = None
        self.knockout_price = None
        self.knockin_date = None
        self.knockout_date = None
        self.terminal_month = None
        self.status = None
        self.maturity_sign = None

    def process_backtest(self, index_data_all):
        """回测"""
        index_data_selected = self.get_index_data_selected(
            index_data_all
        )  # 该雪球产品回测用到的数据
        self.fetch_start_end_prices(index_data_selected)
        self.determine_knock_status(index_data_selected)
        self.calculate_return()
        return None

    def get_index_data_selected(self, index_data_all):
        """选取回测区间内的标的数据"""
        yesterday = last_trading_day(datetime.now().date())
        date_range = [
            i
            for i in index_data_all.index
            if i >= self.time_dynamic_param["start_date"]
            and i <= min(yesterday, self.time_dynamic_param["end_date"])
        ]
        index_data_selected = index_data_all.loc[date_range]
        return index_data_selected

    def fetch_start_end_prices(self, index_data_selected):
        """获取对应起始/结束日期的标的价格"""
        self.is_maturity()
        start_date = self.time_dynamic_param["start_date"]
        end_date = self.time_dynamic_param["end_date"]
        self.start_price = index_data_selected.loc[start_date, "close"]  # 起始日标的价格
        if self.maturity_sign:
            self.end_price = index_data_selected.loc[end_date, "close"]  # 结束日标的价格
        else:
            self.end_price = -1  # 结束日在未来，标的价格未知
        return None

    def determine_knock_status(self, index_data_selected):
        """判断敲入敲出情况"""
        knockin_dates = self.get_knockin_dates(index_data_selected)
        knockout_dates = self.get_knockout_dates(index_data_selected)
        self.determine_status(knockin_dates, knockout_dates, index_data_selected)
        return None

    def get_knockin_dates(self, index_data_selected):
        """获取所有符合敲入条件的日期"""
        start_date = self.time_dynamic_param["start_date"]
        price_threshold = round(
            self.start_price * self.knockin_param["knockin_barrier"], 2
        )

        knockin_dates = list(
            index_data_selected[index_data_selected["close"] <= price_threshold].index
        )
        if start_date in knockin_dates:
            knockin_dates.remove(start_date)  # 敲入判断从第二天开始
        knockin_dates.sort()
        return knockin_dates

    def get_knockout_dates(self, index_data_selected):
        """获取所有符合敲出条件的日期"""
        knockout_dates = []
        for current_month in range(
            self.knockout_param["observation_start_month"],
            self.time_fixed_param["option_expire_month"] + 1,
        ):
            self.update_knockout_param(current_month)
            knockout_date = self.process_knockout_by_month(
                current_month, index_data_selected
            )
            if knockout_date is not None:
                knockout_dates.append(knockout_date)
            knockout_dates.sort()
        return knockout_dates

    def update_knockout_param(self, current_month):
        pass

    def process_knockout_by_month(self, current_month, index_data_selected):
        """判断给定月份是否满足敲出条件"""
        current_date = self.time_dynamic_param["start_date"] + relativedelta(
            months=current_month * self.knockout_param["knockout_freq_month"]
        )
        current_date = ensure_trading_day(current_date)
        yesterday = last_trading_day(datetime.now().date())
        if current_date <= min(yesterday, self.time_dynamic_param["end_date"]):
            current_price = index_data_selected.loc[current_date, "close"]  # 当前标的价格
            price_threshold = round(
                self.start_price * self.knockout_param["knockout_barrier"], 2
            )  # 敲出的价格上限

            if current_price >= price_threshold:
                return current_date
        return None

    def determine_status(self, knockin_dates, knockout_dates, index_data_selected):
        """根据符合条件的敲入敲出日期列表, 判断雪球的敲入敲出状态"""
        if len(knockin_dates) == 0 and len(knockout_dates) == 0:
            self.status = "未敲入，未敲出"
            self.knockin_date = pd.to_datetime("19000101").date()
            self.knockin_price = -1
            self.knockout_date = pd.to_datetime("19000101").date()
            self.knockout_price = -1
            self.terminal_month = self.time_fixed_param["option_expire_month"]
        elif len(knockin_dates) == 0 and len(knockout_dates) != 0:
            self.status = "未敲入，敲出"
            self.knockin_date = pd.to_datetime("19000101").date()
            self.knockin_price = -1
            self.knockout_date = min(knockout_dates)
            self.knockout_price = index_data_selected.loc[self.knockout_date, "close"]
            self.terminal_month = months_between_dates(
                self.knockout_date, self.time_dynamic_param["start_date"]
            )
        elif len(knockin_dates) != 0 and len(knockout_dates) == 0:
            self.status = "敲入，未敲出"
            self.knockin_date = min(knockin_dates)
            self.knockin_price = index_data_selected.loc[self.knockin_date, "close"]
            self.knockout_date = pd.to_datetime("19000101").date()
            self.knockout_price = -1
            self.terminal_month = self.time_fixed_param["option_expire_month"]
        else:
            if min(knockin_dates) < min(knockout_dates):
                self.status = "敲入，敲出"
                self.knockin_date = min(knockin_dates)
                self.knockin_price = index_data_selected.loc[self.knockin_date, "close"]
                self.knockout_date = min(knockout_dates)
                self.knockout_price = index_data_selected.loc[
                    self.knockout_date, "close"
                ]
                self.terminal_month = months_between_dates(
                    self.knockout_date, self.time_dynamic_param["start_date"]
                )
            else:
                self.status = "未敲入，敲出"  # 在敲入前已经完成敲出
                self.knockin_date = pd.to_datetime("19000101").date()
                self.knockin_price = -1
                self.knockout_date = min(knockout_dates)
                self.knockout_price = index_data_selected.loc[
                    self.knockout_date, "close"
                ]
                self.terminal_month = months_between_dates(
                    self.knockout_date, self.time_dynamic_param["start_date"]
                )
        return None

    def calculate_return(self):
        """计算不同敲入敲出情况下的收益"""
        self.update_coupon_param()
        if self.maturity_sign == True:  # 若合约已完结
            if self.status == "未敲入，未敲出":
                self.case_no_event()
            elif self.status == "敲入，未敲出":
                self.case_knockin_only()
            elif self.status == "未敲入，敲出":
                self.case_knockout_only()
            elif self.status == "敲入，敲出":
                self.case_knockin_and_knockout()
        else:  # 若合约未完结
            if self.status == "未敲入，未敲出":
                self.case_contract_ongoing()
            elif self.status == "敲入，未敲出":
                self.case_contract_ongoing()
            elif self.status == "未敲入，敲出":
                self.case_knockout_only()
            elif self.status == "敲入，敲出":
                self.case_knockin_and_knockout()

    def update_coupon_param(self):
        pass

    def case_contract_ongoing(self):
        """若合约未完结，则不计算收益"""
        self.abs_return = -1
        self.annual_return = -1
        self.terminal_month = -1
        return None

    def case_no_event(self):
        """未敲入，未敲出情况下的收益"""
        regular_coupon = self.coupon_param["regular_coupon"]
        start_date = self.time_dynamic_param["start_date"]
        end_date = self.time_dynamic_param["end_date"]
        self.abs_return = (
            regular_coupon * days_between_dates(start_date, end_date) / 365
        )
        self.annual_return = regular_coupon
        return None

    def case_knockout_only(self):
        """未敲入，敲出情况下的收益"""
        kickout_coupon = self.coupon_param["kickout_coupon"]
        start_date = self.time_dynamic_param["start_date"]
        end_date = self.knockout_date
        self.abs_return = (
            kickout_coupon * days_between_dates(start_date, end_date) / 365
        )
        self.annual_return = kickout_coupon
        return None

    def case_knockin_only(self):
        """敲入，未敲出情况下的收益"""
        start_price = self.start_price
        end_price = self.end_price
        start_date = self.time_dynamic_param["start_date"]
        end_date = self.time_dynamic_param["end_date"]
        self.abs_return = max(end_price / start_price - 1, -1)
        self.annual_return = (
            self.abs_return * 365 / days_between_dates(start_date, end_date)
        )
        return None

    def case_knockin_and_knockout(self):
        """敲入，敲出情况下的收益"""
        kickout_coupon = self.coupon_param["kickout_coupon"]
        start_date = self.time_dynamic_param["start_date"]
        end_date = self.knockout_date
        self.abs_return = (
            kickout_coupon * days_between_dates(start_date, end_date) / 365
        )
        self.annual_return = kickout_coupon
        return None


class ClassicSnowball(BaseSnowball):
    """经典雪球"""

    def __init__(
        self,
        underlying,
        time_fixed_param,
        knockin_param,
        knockout_param,
        coupon_param,
        profit_param,
    ):
        super().__init__(
            "经典雪球",
            underlying,
            time_fixed_param,
            knockin_param,
            knockout_param,
            coupon_param,
            profit_param,
        )


class StepdownSnowball(BaseSnowball):
    """降敲型雪球"""

    def __init__(
        self,
        underlying,
        time_fixed_param,
        knockin_param,
        knockout_param,
        coupon_param,
        profit_param,
    ):
        """初始化"""
        super().__init__(
            "降敲型雪球",
            underlying,
            time_fixed_param,
            knockin_param,
            knockout_param,
            coupon_param,
            profit_param,
        )
        self.stepdown_ratio = float(
            input("请输入该降敲型雪球敲出条件每月下调比例:")
        )  # e.g. 输入 0.005 即代表每月下调 0.5%
        self.original_knockout_barrier = self.knockout_param["knockout_barrier"]

    def update_knockout_param(self, current_month):
        """每月更新敲出条件"""
        observation_start_month = self.knockout_param["observation_start_month"]
        if current_month >= observation_start_month:
            self.knockout_param["knockout_barrier"] = (
                self.original_knockout_barrier
                - (current_month - observation_start_month) * self.stepdown_ratio
            )
        return None


class LimitedLossSnowball(BaseSnowball):
    """限亏型雪球"""

    def __init__(
        self,
        underlying,
        time_fixed_param,
        knockin_param,
        knockout_param,
        coupon_param,
        profit_param,
    ):
        """初始化"""
        super().__init__(
            "限亏型雪球",
            underlying,
            time_fixed_param,
            knockin_param,
            knockout_param,
            coupon_param,
            profit_param,
        )
        self.protect_ratio = float(input("请输入该限亏型雪球保护比例:"))  # e.g. 输入 0.8 即保护比例为 80%

    def case_knockin_only(self):
        """敲入，未敲出情况的收益需要结合保护比例单独考虑"""
        self.status = "敲入，未敲出"

        start_price = self.start_price
        end_price = self.end_price
        start_date = self.time_dynamic_param["start_date"]
        end_date = self.time_dynamic_param["end_date"]

        self.abs_return = max(end_price / start_price - 1, -(1 - self.protect_ratio))
        self.annual_return = (
            self.abs_return * 365 / days_between_dates(start_date, end_date)
        )
        return None


class LimitedLossAndProfitSnowball(BaseSnowball):
    """限亏止盈型雪球"""

    def __init__(
        self,
        underlying,
        time_fixed_param,
        knockin_param,
        knockout_param,
        coupon_param,
        profit_param,
    ):
        """初始化"""
        super().__init__(
            "限亏止盈型雪球",
            underlying,
            time_fixed_param,
            knockin_param,
            knockout_param,
            coupon_param,
            profit_param,
        )
        self.protect_ratio = float(input("请输入该限亏止盈型雪球保护比例:"))  # e.g. 输入 0.8 即保护比例为 80%
        self.coupon_param["regular_coupon"] = 0  # 红利票息为0

    def determine_knock_status(self, index_data_selected):
        """限亏止盈型雪球，不存在敲入"""
        knockout_dates = self.get_knockout_dates(index_data_selected)
        self.determine_status(knockout_dates, index_data_selected)
        return None

    def determine_status(self, knockout_dates, index_data_selected):
        """根据符合条件的敲入敲出日期列表, 判断雪球的敲入敲出状态"""
        if len(knockout_dates) == 0:
            self.status = "未敲入，未敲出"
            self.knockin_date = pd.to_datetime("19000101").date()
            self.knockin_price = -1
            self.knockout_date = pd.to_datetime("19000101").date()
            self.knockout_price = -1
            self.terminal_month = self.time_fixed_param["option_expire_month"]
        elif len(knockout_dates) != 0:
            self.status = "未敲入，敲出"
            self.knockin_date = pd.to_datetime("19000101").date()
            self.knockin_price = -1
            self.knockout_date = min(knockout_dates)
            self.knockout_price = index_data_selected.loc[self.knockout_date, "close"]
            self.terminal_month = months_between_dates(
                self.knockout_date, self.time_dynamic_param["start_date"]
            )
        return None

    def case_no_event(self):
        """未敲出情况的收益需要重新考虑"""
        start_date = self.time_dynamic_param["start_date"]
        end_date = self.time_dynamic_param["end_date"]
        self.abs_return = max(
            self.end_price / self.start_price - 1, -(1 - self.protect_ratio)
        )
        self.annual_return = (
            self.abs_return * 365 / days_between_dates(start_date, end_date)
        )
        return None


class EarlyYieldSnowball(BaseSnowball):
    """早利型雪球"""

    def __init__(
        self,
        underlying,
        time_fixed_param,
        knockin_param,
        knockout_param,
        coupon_param,
        profit_param,
    ):
        super().__init__(
            "早利型雪球",
            underlying,
            time_fixed_param,
            knockin_param,
            knockout_param,
            coupon_param,
            profit_param,
        )
        self.drop_freq = float(input("请输入该早利型雪球敲出票息的下调周期(月):"))
        self.periodic_return_drop = float(input("请输入该早利型雪球敲出票息的周期下调利率:"))
        self.original_kickout_coupon = self.coupon_param["kickout_coupon"]

    def update_coupon_param(self):
        """早利型雪球的票息参数需要定期更新"""
        knockout_month = self.terminal_month
        option_expire_month = self.time_fixed_param["option_expire_month"]
        self.coupon_param["kickout_coupon"] = (
            self.original_kickout_coupon
            - knockout_month // self.drop_freq * self.periodic_return_drop
        )
        self.coupon_param["regular_coupon"] = (
            self.original_kickout_coupon
            - option_expire_month // self.drop_freq * self.periodic_return_drop
        )
        return None
