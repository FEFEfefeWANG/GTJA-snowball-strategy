from datetime import datetime
import pandas as pd

# 挂钩标的信息 {名称：代码}
underlying_dict = {
    "上证50": "000016.SH",
    "沪深300": "000300.SH",
    "中证500": "000905.SH",
    "中证1000": "000852.SH",
    "中证1000-ETF": "512100.SH"
}


def get_underlying_data(underlying,
                        data_fields,
                        start_date,
                        end_date,
                        data_source="wind"):
    """ 获取挂钩标的的特征数据
    Args:
        underlying (str): 挂钩标的名称
        data_fields (list) : 数据特征，例: ["close", "PE_TTM"]
        start_date (datetime): 开始日期
        end_date (datetime): 结束日期
        data_source (str, optional): 挂钩标的数据源 (默认"wind")
    Returns:
        dataframe: 挂钩标的的特征数据
    Example:
                    close      pe_ttm
        2021-01-04  3643.3592  14.2053
        2021-01-05  3683.3634  14.2828
    """

    # 数据源：wind
    if data_source == "wind":
        import WindPy
        WindPy.w.start()

        data_fields = [i.lower() for i in data_fields]
        index_data = WindPy.w.wsd(
            underlying_dict[underlying],
            data_fields,
            start_date.strftime("%Y%m%d"),
            end_date.strftime("%Y%m%d"),
            "Fill=Previous",
            usedf=True,
            PriceAdj="F")[1].dropna()
        index_data.columns = data_fields
        return index_data

    # 数据源：ifind
    elif data_source == "ifind":
        from iFinDPy import THS_iFinDLogin, THS_HQ
        THS_iFinDLogin("gjzg035", "af252e")

        data_fields = [i.lower() for i in data_fields]
        data_fields_input = [
            item.lower() + "_index" if item == "pe_ttm" else item
            for item in data_fields
        ]
        data_fields_input = ",".join(data_fields_input)
        THSData = THS_HQ(underlying_dict[underlying],
                         data_fields_input,
                         'CPS:5',
                         begintime=start_date.strftime("%Y%m%d"),
                         endtime=end_date.strftime("%Y%m%d"))
        index_data = pd.DataFrame(THSData.data).drop("thscode", axis=1)
        index_data = index_data.set_index("time")
        index_data.index = index_data.index.map(lambda x: pd.to_datetime(x).date())
        index_data.columns = data_fields
        return index_data

    # 数据源：efinance
    elif data_source == "efinance":
        if data_fields != ['close']:
            print("ERROR: efinance数据源仅可用于获取收盘价")
            return None

        import efinance as ef
        index_data = ef.stock.get_quote_history(
            stock_codes=underlying,
            beg=start_date.strftime("%Y%m%d"),
            end=end_date.strftime("%Y%m%d"),
        )
        index_data = index_data.loc[:, ["日期", "收盘"]]
        index_data.columns = ["date", "close"]
        index_data = index_data.set_index("date", drop=True)
        index_data.index = index_data.index.map(
            lambda x: datetime.strptime(x, "%Y-%m-%d").date())
        return index_data
