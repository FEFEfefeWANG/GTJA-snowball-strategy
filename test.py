from data_local import df
from new_pde import *
from scipy.optimize import brentq as bq
import pandas as pd



# ---------------------------- 回测参数设置 ------------------------------#
Ob_date = dt.datetime(2018,7,2).date()
end_date = dt.datetime(2020,7 ,2).date()
S_0, r, q, vol, T, ko_dict, ki_dict, datelist, daysdict = genParams(Ob_date)
r = 0.025 ## 3m cbond yield on 230426
qdct = dict()
mark_1y = Ob_date+rd.relativedelta(years=1)
for x in datelist:
#     qdct[x] = 0.053 if x < mark_1y else 0.053 - 0.01*(x-mark_1y).days/365.0
#     qdct[x] = 0.053 if x < mark_1y else 0.043
#     qdct[x] = 0.053 - 0.01*(x-Ob_date).days/(len(datelist)-1)
    qdct[x] = 0.045
vol = 0.20   # modified by the official
# -----------------------------------# -----------------------#

date_df = df.loc[Ob_date:end_date].copy()

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
    # Create an empty DataFrame with the index
    res = pd.DataFrame(index=list(str(round(x * 100.0, 2)) + '%' for x in allS))

    # Initialize k and now
    k = 0
    now = Ob_date

    # Create a list to store the Series that will be concatenated
    data_to_concat = []

    while now <= datelist[-1]:
        tmpdelta = []
        for i in range(len(allS)):
            S = allS[i] * S_0
            tmpdelta.append(str(round(gridval(delta_grid_new, S, k,ko_dict)*100.0,2))+'%')

        # Create a Series with the current data and append it to the list
        data_to_concat.append(pd.Series(tmpdelta, index=res.index, name=now))

        now += rd.relativedelta(days=1)
        k += 1
        while now not in alldates:
            now += rd.relativedelta(days=1)
            k += 1

    # Concatenate all the Series in the list along the columns axis
    res = pd.concat(data_to_concat, axis=1)

    print(res)







































