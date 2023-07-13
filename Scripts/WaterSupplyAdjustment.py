"""
Diversion Analysis & Piecewise Linear Fit Modeling
This script performs a detailed analysis of river diversions, unregulated inflows
and reservoir storage to determine the best piecewise linear fit for each reach.

Key steps and operations:
Data Importing: Imports historical and modeled diversions, unregulated
inflows from the South Fork and Henry's Fork, and reservoir storage data.

Data Processing: For each year, computes the cumulative sum of inflows
and subtracts it from the total sum. It then adds the reservoir storage.

Flow Calculation: For each reach and month, calculates the gap between
historical and modeled diversions.

Piecewise Linear Fit: Computes a piecewise linear fit of the river
diversion as a function of water supply. It calculates separate slopes
before and after the breakpoint.

Data Export: Saves the slopes and break values for each reach and month
into CSV files.

This script uses libraries such as pandas, datetime, pwlf, statsmodels, and
matplotlib.
"""
# %%
import pwlf
import statsmodels.api as sm
import numpy as np
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import re
from scipy.optimize import curve_fit
from sklearn.metrics import r2_score


def piecewise_linear(x, m, b, y2):
    return np.piecewise(x, [x < b, x >= b], [lambda x: m * (x - b) + y2, y2])


# Update this to the name of the basin
BasinName = "SNK"

HistoricalDiversions = pd.read_csv(
    f"../Outputs/{BasinName}/ObservedDiversions.csv", index_col=0, parse_dates=True
)
ModeledDiversions = pd.read_csv(
    f"../Outputs/{BasinName}/ReachDiversions.csv", index_col=0, parse_dates=True
)

# Calculate the unregulated inflows from the South Fork and Henry's Fork in acre-feet
HEII = pd.read_csv("../Data/Flows/HEII.csv", index_col=0, parse_dates=True)["heii_qu"]
HEII *= 1.9835
ISLI = pd.read_csv("../Data/Flows/HEII.csv", index_col=0, parse_dates=True)["isli_qu"]
ISLI *= 1.9835

HEII.loc[(HEII.index.month < 4) | (HEII.index.month > 11)] = 0
ISLI.loc[(ISLI.index.month < 4) | (ISLI.index.month > 11)] = 0


# Add the reservoir storage to the inflows
Reservoir = pd.read_csv(
    "../Data/Reservoirs/SnakeReservoirs.csv", index_col=0, parse_dates=True
)
Reservoir = Reservoir.reindex(HEII.index)

Reservoir.loc[(Reservoir.index.month != 3) | (Reservoir.index.day != 31)] = 0


HEII = HEII + Reservoir[["jck_af", "pal_af"]].sum(axis=1)

HEN = ISLI + Reservoir[["isl_af", "grs_af", "hen_af"]].sum(axis=1)

RIR = Reservoir[["rir_af"]].sum(axis=1)

AMF = Reservoir[["amf_af"]].sum(axis=1)

SWSITotal = pd.concat((HEII, RIR, HEN, HEII + HEN + HEN, HEII + HEN + AMF), axis=1)
SWSITotal.columns = ["HEII", "RIR", "HEN", "HEII+HEN", "HEII+HEN+AMF"]

SWSITotal = SWSITotal.resample("1Y").sum()

ReachWaterSupply = pd.read_csv("../Data/ReachSWSI.csv", index_col=0)


# Only use months during the irrigation season
months = [4, 5, 6, 7, 8, 9, 10, 11]
monthsLength = [30, 31, 30, 31, 31, 30, 31, 30]

Outputs = pd.DataFrame(index=ReachWaterSupply.index, columns=["Slope", "y2", "Break"])

for reach in HistoricalDiversions.columns:
    print(reach)

    # Get the gap between the historical diversions and the previously calculated full water supply diversions
    Flow = (
        (HistoricalDiversions - ModeledDiversions.reindex(HistoricalDiversions.index))[
            reach
        ]
        .resample("1Y")
        .mean()
        .fillna(0)
    )

    Flow = Flow.loc[Flow.index.year >= 2000]

    # Get the avaiable water supply for the reach
    WaterSupplyName = ReachWaterSupply.loc[reach, "Water Supply"]
    WaterSupply = SWSITotal[WaterSupplyName]
    WaterSupply = WaterSupply.reindex(Flow.index)

    # Set the bounds for the piecewise linear fit to be the 5th smallest and 5th largest water supply values
    bounds = [
        [WaterSupply.nsmallest(5).iloc[4], WaterSupply.nlargest(5).iloc[4]],
        [0, 1],
    ]

    p, e = curve_fit(
        piecewise_linear,
        WaterSupply.values,
        Flow.values,
        p0=[0.01, WaterSupply.mean(), 0],
    )

    m = p[0]
    b = p[1]
    y2 = p[2]

    slope1 = False
    Outputs.loc[reach, "Break"] = b
    Outputs.loc[reach, "Slope"] = m
    Outputs.loc[reach, "y2"] = y2

    # Plot the flow vs the WaterSupply
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.scatter(WaterSupply, Flow, label="Historical Diversions")

    xHat = np.linspace(WaterSupply.min(), WaterSupply.max(), 100)
    yHat = piecewise_linear(xHat, m, b, y2)
    ax.plot(xHat, yHat, label="Piecewise Linear Fit")

    r2 = r2_score(Flow, piecewise_linear(WaterSupply.values, m, b, y2))

    params = f"m={m:.2e}\n b={b:.2e}\n y2={y2:.2f}\n R2={r2:.2f}"
    plt.plot([], [], " ", label=params)

    plt.legend()
    plt.title(f"{reach}")
    plt.xlabel(f"{WaterSupplyName} (AF)")
    plt.ylabel("Total Diversion (CFS)")
    fig.savefig(f"../Outputs/{BasinName}/Figures/{reach}.png", dpi=300)

    plt.close()

WaterSupplyRiverWare = pd.DataFrame(
    index=ReachWaterSupply.index, columns=["HEII", "HEN", "AMF", "RIR"]
).fillna(0)
# Format ReachSWSI for RiverWare
for reach in ReachWaterSupply.index:
    if "HEII" in ReachWaterSupply.loc[reach, "Water Supply"]:
        WaterSupplyRiverWare.loc[reach, "HEII"] = 1
    if "HEN" in ReachWaterSupply.loc[reach, "Water Supply"]:
        WaterSupplyRiverWare.loc[reach, "HEN"] = 1
    if "AMF" in ReachWaterSupply.loc[reach, "Water Supply"]:
        WaterSupplyRiverWare.loc[reach, "AMF"] = 1
    if "RIR" in ReachWaterSupply.loc[reach, "Water Supply"]:
        WaterSupplyRiverWare.loc[reach, "RIR"] = 1

WaterSupplyRiverWare.to_csv(f"../Outputs/{BasinName}/RiverWareInputs/WaterSupply.csv")

Outputs.to_csv(f"../Outputs/{BasinName}/SlopeThreshold.csv")

# %%

ReachGap = pd.DataFrame(index=range(366), columns=HistoricalDiversions.columns)

for reach in HistoricalDiversions.columns:
    gap = (
        HistoricalDiversions - ModeledDiversions.reindex(HistoricalDiversions.index)
    ).loc[
        (HistoricalDiversions.index.year > 2000)
        * (HistoricalDiversions.index.year < 2020),
        reach,
    ]
    gap = gap.groupby(gap.index.dayofyear).mean()
    gap.loc[gap.index < 170] = 0

    # Set the mean to 1

    gap = gap.rolling(30).mean().fillna(0)

    ReachGap[reach] = gap


# We need to create a key for sorting that extracts the numeric part of the column header and converts it to int
def sorting_key(column_name):
    match = re.search(r"\d+", column_name)
    if match:
        return int(match.group())
    else:
        return 0


ReachGap.fillna(0, inplace=True)

# Set each column to have a mean of 1
ReachGap = ReachGap / ReachGap.mean()

ReachGap = ReachGap.reindex(sorted(ReachGap.columns, key=sorting_key), axis=1)

ReachGap.to_csv(f"../Outputs/{BasinName}/RiverWareInputs/ReachGap.csv")

# %%
