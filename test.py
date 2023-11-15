from data_local import df
from new_pde import *
from scipy.optimize import brentq as bq


# ---------------------------- 回测参数设置 ------------------------------#
Ob_date = dt.datetime(2015,10,23).date()
end_date = dt.datetime(2017,10 ,23).date()
S_0, r, q, vol, T, ko_dict, ki_dict, datelist, daysdict = genParams(Ob_date)
r = 0.025 ## 3m cbond yield on 230426
qdct = dict()
mark_1y = Ob_date+rd.relativedelta(years=1)
for x in datelist:
#     qdct[x] = 0.053 if x < mark_1y else 0.053 - 0.01*(x-mark_1y).days/365.0
#     qdct[x] = 0.053 if x < mark_1y else 0.043
#     qdct[x] = 0.053 - 0.01*(x-Ob_date).days/(len(datelist)-1)
    qdct[x] = 0.045
vol = 0.50   # modified by the official
# -----------------------------------# -----------------------#

date_df = df.loc[Ob_date:end_date]

if __name__ == "__main__":
    def coupon2snowball(c):
        return pdeSnowball(S_0, r, qdct, vol, T, c, Ob_date, ko_dict, ki_dict, datelist, daysdict, return_type='price')*1e5
    c = bq(coupon2snowball, 0.0, 0.4)
    print(f"q = {qdct[datelist[-1]]}")
    print(f"r={r}")
    print(f"vol={vol}")
    print(f"理论年化票息是：{c}%")

    OTU_delta_grid, DNT_delta_grid, DKOP_delta_grid, UOP_delta_grid, delta_grid = pdeSnowball(S_0,
                r, qdct, vol, T, c, Ob_date, ko_dict, ki_dict, datelist, daysdict, return_type='alldelta')

    # Here to modify the delta_grid according to the specific path! 敲入会导致delta跃变
    DKOP_delta_grid = update_in_grid(DKOP_delta_grid,date_df,ki_dict)
    DNT_delta_grid = update_in_grid(DNT_delta_grid,date_df,ki_dict)

    delta_grid_new = OTU_delta_grid + DNT_delta_grid + (DKOP_delta_grid - UOP_delta_grid)
    delta_grid_new = update_out_grid(delta_grid_new,date_df,ko_dict)

    allS = np.linspace(0.70, 1.10, 81)#*S_0
    # allS = np.linspace(0.50, 1.10, 25)
    res = pd.DataFrame(index = list(str(round(x*100.0, 2))+'%' for x in allS))
    k = 0
    now = Ob_date
    while now <= end_date:
        for i in range(len(allS)):
            index = str(round(allS[i]*100.0, 2))+'%'
            S = allS[i]*S_0
            res.loc[index, now] = str(round(gridval(delta_grid_new, S, k,ko_dict)*100.0,2))+'%'


        now += rd.relativedelta(days=1)
        k += 1
        while now not in alldates:
            now += rd.relativedelta(days=1)
            k += 1

    print(res)


    #  export the res to excel and name
    res.to_excel(f"./data/case5_new_r{r}_q{qdct[datelist[-1]]}_vol{vol}_理论年化票息{round(c*100,2)}%.xlsx")







































