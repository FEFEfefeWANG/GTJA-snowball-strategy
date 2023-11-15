import numpy as np
import pandas as pd
import os
import datetime as dt
from dateutil import relativedelta as rd
from scipy import stats as spstat
from matplotlib import pyplot as plt
from numpy import random as rdm
from math import ceil, floor
from data_local import alldates, Sdict, voldict,df

def update_in_grid(grid,date_df,ki_dict):
    Ob_date = date_df.index[0]
    for d in ki_dict.keys():
        # insprct if knock in
        if d not in df.index:
            break
        date_df.loc[d, "ki"] = (date_df.loc[d, "close"] <= ki_dict[d]).copy()
        if date_df.loc[d, "ki"]:
            delta = (d - Ob_date).days
            grid[:,delta:] = 0
            print(f"敲入日为：{d}")
            break
    return grid

def update_out_grid(grid,date_df,ko_dict):
    Ob_date = date_df.index[0]
    for d in ko_dict.keys():
        # inspect if knock out
        if d not in df.index:
            break
        date_df.loc[d,"ko"] = (date_df.loc[d,"close"] >= ko_dict[d]).copy()
        if date_df.loc[d,"ko"]:
            delta = (d - Ob_date).days
            grid[:, delta:] = 0
            print(f"敲出日为：{d}")
            break
    return grid


def gridval(grid, S, k,ko_dict ): ## extracting grid value for S at time k
    m = 800
    S_max = 4.0*max(ko_dict.values())
    S_min = 0.0
    delta_S = 1.0*(S_max-S_min)/m
    i_S0 = int((S-S_min)/delta_S)
#     if i_S0*delta_S+S_min < S:
#         alpha = (S - i_S0*delta_S-S_min)/delta_S
#         return alpha*grid[i_S0+1][k]+(1.0-alpha)*grid[i_S0][k]
#     elif i_S0*delta_S+S_min > S:
#         alpha = (i_S0*delta_S+S_min - S)/delta_S
#         return alpha*grid[i_S0-1][k]+(1.0-alpha)*grid[i_S0][k]
#     else:
#         return grid[i_S0][k]
    return grid[i_S0][k]

## change key params for autocallables in this function
def genParams(Ob_date,N_mth = 24, N_lock = 3, ko_down = 0.0, ko = 1.00, ki = 0.75, S_0=np.nan):

    ko_oblist = list()
    ki_oblist = list()
    for i in range(N_lock, N_mth + 1):
        tmp = Ob_date + rd.relativedelta(months=i)
        while tmp not in alldates:  #alldates are trading days list
            tmp += rd.relativedelta(days=1)
        ko_oblist.append(tmp)
    for x in alldates:
        if x >= ko_oblist[0] and x <= ko_oblist[-1]:
            ki_oblist.append(x)
    if np.isnan(S_0):
        S_0 = Sdict[Ob_date]
    try:
        vol = voldict[Ob_date]

    except:
        vol = 0.2
    #     r = rdct[dt.datetime.strptime(str(Ob_date), '%Y-%m-%d')] ## temporarily abandoned
    #     q = qdct[dt.datetime.strptime(str(Ob_date), '%Y-%m-%d')] ## temporarily abandoned
    r = np.nan  ## to be specified outside
    q = np.nan  ## to be specified outside
    ko_dict = dict()
    ki_dict = dict()
    daysdict = dict()
    for x in ko_oblist:
        ko_dict[x] = ko * S_0
        ko -= ko_down
    for x in ki_oblist:
        ki_dict[x] = ki * S_0
    datearr = np.array(alldates)
    #     datelist = list()
    datelist = [Ob_date + dt.timedelta(days=x) for x in range((ko_oblist[-1] - Ob_date).days + 1)]
    #     for x in range((ko_oblist[-1] - Ob_date).days + 1):
    #         tmp = Ob_date + dt.timedelta(days=x)
    #         if tmp in vacation or tmp.isoweekday() >= 6:
    #             continue
    #         datelist.append(tmp)
    for x in datelist:
        daysdict[x] = 1.0 * (x - Ob_date).days / 365.0
    T = max(daysdict.values())

    return S_0, r, q, vol, T, ko_dict, ki_dict, datelist, daysdict
    # 返回初始价格，（无风险利率，分红率，波动率(这三个外部确定)，周期，敲入敲出字典（key:日期， value：价格），日期列表，日期字典（key：日期， value：日期距离初始日期的年份差）

def pdeSnowball(S_0, r, qdct, sigma, T, c, today, ko_dict, ki_dict, datelist, daysdict,
                return_type='price'):  ## different returning values with different usage: price/delta position
    ## datelist is all business days after today until maturity
    ## daysdict is for calculating the day gap til today by day/365 ratio, should satisfy daysdict[x] <= T for any x
    m = 800  ## grid on stock prices, a denser grid (m=1000) doesn't affect much under current calculations
    n = len(datelist) - 1  ## grid on dates
    S_max = 4.0 * max(ko_dict.values())
    S_min = 0.0
    delta_S = 1.0 * (S_max - S_min) / m  # grid step on stock prices, it isn't normalized by S_0
    Sarr = np.linspace(S_min, S_max, m + 1)  # stock price grid
    Tarr = np.array(datelist)  # date grid
    ki = max(ki_dict.values()) / S_0  #敲入价

    ## grid initialization
    ## loss is limited by margin ratio - (1-ki) by default
    init_grid_otu = np.full((m + 1, n + 1), np.nan)  # 上涨生效障碍期权
    #     init_grid_dot = np.full((m+1, n+1), np.nan)   #
    init_grid_dnt = np.full((m + 1, n + 1), np.nan)  # 双边触碰失效期权
    init_grid_dkop = np.full((m + 1, n + 1), np.nan)  # 双边失效看跌
    init_grid_uop = np.full((m + 1, n + 1), np.nan)  # 上涨失效看跌
    #  init_grid_put = np.full((m + 1, n + 1), np.nan)  # 带保证金看跌
    #  five parts of the snowball

    for i in range(m + 1):
        # right bound at t=T

        init_grid_otu[i][n] = 0.0

        init_grid_dnt[i][n] = c * T  # coupon payment

        init_grid_dkop[i][n] = max((S_0 - Sarr[i]), 0.0) / S_0  ## 归一化
        init_grid_uop[i][n] = max((S_0 - Sarr[i]), 0.0) / S_0  ##
        #  init_grid_put[i][n] = max(ki * S_0 - Sarr[i], 0.0) / S_0  ##
        for j in range(1, n + 1):
            x = daysdict[Tarr[j]]
            if Tarr[j] in ko_dict.keys() and Sarr[i] >= ko_dict[Tarr[j]]:  ## grid above S=ko*S0
                init_grid_otu[i][j] = c * x
                #                 init_grid_dot[i][j] = c*T*np.exp(-r*(T-x))
                init_grid_dnt[i][j] = 0.0  ##
                init_grid_dkop[i][j] = 0.0
                init_grid_uop[i][j] = 0.0
            if Tarr[j] in ki_dict.keys() and Sarr[i] <= ki_dict[Tarr[j]]:  ## grid below S=ki*S0
                #                 init_grid_dot[i][j] = c*T*np.exp(-r*(T-x))
                init_grid_dnt[i][j] = 0.0  ##
                init_grid_dkop[i][j] = 0.0
    for j in range(1, n + 1):  ## lower bound at S=0
        x = daysdict[Tarr[j]]
        init_grid_otu[0][j] = 0.0
        #         init_grid_uop[0][j] = S_0*np.exp(-r*(T-x))/S_0*(1.0-ki) ##
        init_grid_uop[0][j] = S_0 * np.exp(-r * (T - x)) / S_0
        #  init_grid_put[0][j] = ki * S_0 * np.exp(-r * (T - x)) / S_0
    #  for j in range(1, n + 1):  ## upper bound at S=+inf
        #  init_grid_put[m][j] = 0.0  ##

    ## grid calculations
    def newgridcalc(grid):
        #         delta_t = 1.0/365.0 ## may have further improvements
        m = grid.shape[0] - 1
        n = grid.shape[1] - 1

        #         delta_t = T/n
        def genM(mtype='left'):
            if mtype == 'left':
                mfactor = -1.0
            elif mtype == 'right':
                mfactor = 1.0
            M = np.zeros((m - 1, m - 1))
            for i in range(1, m - 1):
                M[i][i - 1] = mfactor * alpha(i + 1)
            for i in range(m - 1):
                M[i][i] = 1 + mfactor * beta(i + 1)
            for i in range(m - 2):
                M[i][i + 1] = mfactor * gamma(i + 1)
            return M

        for j in range(n - 1, -1, -1):
            q = qdct[Tarr[j]]  ##
            delta_t = (Tarr[j + 1] - Tarr[j]).days / 365.0  ##
            alpha = lambda j: delta_t / 4.0 * (sigma * sigma * j * j - r * j + q * j)
            beta = lambda j: -delta_t / 2.0 * (sigma * sigma * j * j + r)
            gamma = lambda j: delta_t / 4.0 * (sigma * sigma * j * j + r * j - q * j)
            M1 = genM('left')
            M2 = genM('right')
            if np.isnan(grid[m][j]):  ## upper bound has discretized initial value
                grid[m][j] = grid[m][j + 1] * np.exp(-r * delta_t)
            if np.isnan(grid[0][j]):  ## lower bound has discretized initial value
                grid[0][j] = grid[0][j + 1] * np.exp(-r * delta_t)
            b = np.zeros((m - 1, 1))
            b[0] = alpha(1) * (grid[0][j] + grid[0][j + 1])
            b[m - 2] = gamma(m - 1) * (grid[m][j] + grid[m][j + 1])
            tmp = np.linalg.solve(M1, M2 @ grid[1:m, j + 1].reshape(-1, 1) + b)
            for i in range(1, m):
                if np.isnan(grid[i][j]):  ## value is initialized
                    grid[i][j] = tmp[i - 1][0]
        return grid

    ## OTU
    OTUgrid = newgridcalc(init_grid_otu)
    ## DNT
    #     xmatrix = np.full((m+1, n+1), list(T-daysdict[date] for date in datelist)) ## check
    #     print(xmatrix)
    #     DNTgrid = c*T*np.exp(-r*xmatrix) - newgridcalc(init_grid_dot)
    DNTgrid = newgridcalc(init_grid_dnt)  ## for DNT, direct calculations turned out to be more precise
    ## DKOP



    DKOPgrid = newgridcalc(init_grid_dkop)
    ## UOP
    UOPgrid = newgridcalc(init_grid_uop)
    ## put
    #  PUTgrid = newgridcalc(init_grid_put)
    snowball_grid = OTUgrid + DNTgrid + (DKOPgrid - UOPgrid) #  + PUTgrid
    #     snowball_grid = OTUgrid+DNTgrid+(DKOPgrid-UOPgrid)

    OTU_delta_grid = (OTUgrid[1:, :] - OTUgrid[:-1, :]) / delta_S * S_0
    DNT_delta_grid = (DNTgrid[1:, :] - DNTgrid[:-1, :]) / delta_S * S_0
    DKOP_delta_grid = (DKOPgrid[1:, :] - DKOPgrid[:-1, :]) / delta_S * S_0
    UOP_delta_grid = (UOPgrid[1:, :] - UOPgrid[:-1, :]) / delta_S * S_0
    delta_grid = OTU_delta_grid + DNT_delta_grid + (DKOP_delta_grid - UOP_delta_grid) #  + PUT_delta_grid



    def gridval(grid, S_0):  ## extracting grid value for S_0 at time 0
        i_S0 = int((S_0 - S_min) / delta_S)
        if i_S0 * delta_S + S_min < S_0:
            alpha = (S_0 - i_S0 * delta_S - S_min) / delta_S
            return alpha * grid[i_S0 + 1][0] + (1.0 - alpha) * grid[i_S0][0]
        elif i_S0 * delta_S + S_min > S_0:
            alpha = (i_S0 * delta_S + S_min - S_0) / delta_S
            return alpha * grid[i_S0 - 1][0] + (1.0 - alpha) * grid[i_S0][0]
        else:
            return grid[i_S0][0]

    ## supports 4 types of return value
    if return_type == 'price':  ## for the actual price at time 0
        return gridval(snowball_grid, S_0)
    elif return_type == 'delta':  ## for the actual delta at time 0
        return gridval(delta_grid, S_0)
    elif return_type == 'pricegrid':  ## for the entire pricing grid
        return snowball_grid
    elif return_type == 'deltagrid':  ## for the entire delta grid
        return delta_grid
    elif return_type == 'allprices':  ## for testing
        return gridval(OTUgrid, S_0), gridval(DNTgrid, S_0), gridval(DKOPgrid, S_0), gridval(UOPgrid, S_0), gridval(
            snowball_grid, S_0)
#     return gridval(snowball_grid, S_0) ## use for finding zero priced coupon values
#     return gridval(delta_grid, S_0)*S_0 ## use for finding delta position at time 0
    elif return_type == "alldelta":
        return OTU_delta_grid, DNT_delta_grid, DKOP_delta_grid, UOP_delta_grid, delta_grid