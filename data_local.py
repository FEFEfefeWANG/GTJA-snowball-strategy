import pandas as pd
import datetime as dt
import numpy as np
from scipy.optimize import brentq as bq

df = pd.read_excel("./data/000852_SH.xlsx")
df = df.set_index("date")

#  set the index from int to be datetime.date
df.index = df.index.map(lambda x: dt.datetime.strptime(str(x), "%Y%m%d").date())
Ssrs = df

#  get the trading date list
alldates = df.index.tolist()

#  append the future trading date list
alldates = alldates + [alldates[-1] + dt.timedelta(days=i) for i in range(1, 365 * 5)
                       if (alldates[-1] + dt.timedelta(days=i)).weekday() < 5]


#  get the underlying price dict
Sdict = df["close"].to_dict()

#  get the underlying vol dict
voldict = (df["close"].pct_change(1).rolling(252).std().dropna() * np.sqrt(252.0)).to_dict()

