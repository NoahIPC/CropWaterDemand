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
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import re
from scipy.optimize import curve_fit
from sklearn.metrics import r2_score
import os


def piecewise_linear(x, m, b, y2):
    return np.piecewise(x, [x < b, x >= b], [lambda x: m * (x - b) + y2, y2])


# Update this to the name of the basin
BasinName = "BOI"

# Dictionary of water supply sources for each reach
WaterSupplyDict = {'SNK': {'HEII': {'Inflow': ['HEII'], 'Reservoirs': ['jck_af', 'pal_af']},
                           'HEN': {'Inflow': ['ISLI'], 'Reservoirs': ['isl_af', 'grs_af', 'hen_af']},
                           'HEII+HEN' : {'Inflow': ['HEII', 'ISLI'], 'Reservoirs': ['jck_af', 'pal_af', 'isl_af', 'grs_af', 'hen_af']}, 
                           'HEII+HEN+AMF': {'Inflow': ['ISLI', 'HEII'], 'Reservoirs': ['jck_af', 'pal_af', 'isl_af', 'grs_af', 'hen_af', 'amf_af']},
                            'RIR': {'Inflow': [], 'Reservoirs': ['rir_af']}},
                    'BOI': {'BOI': {'Inflow': ['LUC'], 'Reservoirs': ['LUC', 'ARK', 'AND']}},
                    'PAY': {'PAY': {'Inflow': ['HRSI'], 'Reservoirs': ['CSC', 'DED']}}}

SWSITotal = pd.DataFrame(index=pd.date_range('1980-01-01', '2018-12-31', freq='D'), columns=WaterSupplyDict[BasinName].keys()).fillna(0)

WaterSupply = WaterSupplyDict[BasinName]

for reach in WaterSupply.keys():

    for flow in WaterSupply[reach]['Inflow']:
        df = pd.read_html(f"https://www.usbr.gov/pn-bin/daily.pl?station={flow}&format=html&year=1980&month=1&day=1&year=2018&month=12&day=31&pcode=qu", 
                                        index_col=0, parse_dates=True)[0]
        df *= 1.9835
        df.loc[(df.index.month < 4) | (df.index.month > 10)] = 0
        SWSITotal[reach] += df.values.flatten()

    for reservoir in WaterSupply[reach]['Reservoirs']:
        df = pd.read_html(f"https://www.usbr.gov/pn-bin/daily.pl?station={reservoir}&format=html&year=1980&month=1&day=1&year=2018&month=12&day=31&pcode=af", 
                                        index_col=0, parse_dates=True)[0]
        df.loc[(df.index.month != 3) | (df.index.day != 31)] = 0
        SWSITotal[reach] += df.values.flatten()

SWSITotal = SWSITotal.resample("1Y").sum()



HistoricalDiversions = pd.read_csv(f"../Outputs/{BasinName}/ObservedDiversions.csv",
                                    index_col=0, parse_dates=True).dropna()
ModeledDiversions = pd.read_csv(f"../Outputs/{BasinName}/ReachDiversions.csv", 
                                index_col=0, parse_dates=True).dropna()

# Only use reaches the end with BasinName
ReachWaterSupply = pd.read_csv("../Data/ReachSWSI.csv", index_col=0)
ReachWaterSupply = ReachWaterSupply[ReachWaterSupply.index.str.contains(f"_{BasinName}")]

Outputs = pd.DataFrame(index=ReachWaterSupply.index, columns=["Slope", "y2", "Break"])

for reach in HistoricalDiversions.columns:
    print(reach)


    def fit_water_supply(Flow, reach, OutputFolder):
        # Get the avaiable water supply for the reach
        WaterSupplyName = ReachWaterSupply.loc[reach, "Water Supply"]
        WaterSupply = SWSITotal[WaterSupplyName]
        WaterSupply = WaterSupply.reindex(Flow.index)

        # Set the bounds for the piecewise linear fit to be the 5th smallest and 5th largest water supply values
        bounds = [
            [WaterSupply.nsmallest(5).iloc[4], WaterSupply.nlargest(5).iloc[4]],
            [0, 1],
        ]


        # Fit the piecewise linear function
        p, e = curve_fit(
            piecewise_linear,
            WaterSupply.values,
            Flow.values,
            p0=[0.01, WaterSupply.mean(), 0],
        )

        m = p[0]
        b = p[1]
        y2 = p[2]

        # Save the slope, breakpoint, and y2 value
        Outputs.loc[reach, "Slope"] = m
        Outputs.loc[reach, "Break"] = b
        Outputs.loc[reach, "y2"] = y2

        # Plot the flow vs the WaterSupply
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.scatter(WaterSupply, Flow, label="Historical Diversions")

        # add labels for each year
        for i, txt in enumerate(Flow.index.year):
            ax.annotate(
                txt,
                (WaterSupply.values[i], Flow.values[i]),
                xytext=(5, 5),
                textcoords="offset points",
            )


        # Plot the piecewise linear fit
        xHat = np.linspace(WaterSupply.min(), WaterSupply.max(), 100)
        yHat = piecewise_linear(xHat, m, b, y2)
        ax.plot(xHat, yHat, label="Piecewise Linear Fit")

        # Calculate the R2 value
        r2 = r2_score(Flow, piecewise_linear(WaterSupply.values, m, b, y2))

        # Add the legend and title
        params = f"m={m:.2e}\n b={b:.2e}\n y2={y2:.2f}\n R2={r2:.2f}"
        plt.plot([], [], " ", label=params)

        plt.legend()
        plt.title(f"{reach}")
        plt.xlabel(f"{WaterSupplyName} (AF)")
        plt.ylabel("Total Diversion (CFS)")


        # If the folder doesn't exist, create it
        if not os.path.exists(f"../Outputs/{BasinName}/Figures/{OutputFolder}"):
            os.makedirs(f"../Outputs/{BasinName}/Figures/{OutputFolder}")

        # Save the figure
        fig.savefig(f"../Outputs/{BasinName}/Figures/{OutputFolder}/{reach}.png", dpi=300)
        plt.close()


    # Get the gap between the historical diversions and the previously calculated full water supply diversions
    Flow = (HistoricalDiversions - ModeledDiversions.reindex(HistoricalDiversions.index))[reach]

    # Calculate the cumulative sum of the gap for July and August
    Flow = Flow.resample("1Y").mean().fillna(0)
    Flow = Flow.loc[Flow.index.year >= 2000]

    # Fit the piecewise linear function
    fit_water_supply(Flow, reach, "WaterSupplyFull")
    
    # Get the gap between the historical diversions and the previously calculated full water supply diversions
    Flow = (HistoricalDiversions - ModeledDiversions.reindex(HistoricalDiversions.index))[reach]

    # Calculate the cumulative sum of the gap for July and August
    Flow = Flow.loc[(HistoricalDiversions.index.month >= 7) & (HistoricalDiversions.index.month <= 9)].resample("1Y").mean().fillna(0)
    Flow = Flow.loc[Flow.index.year >= 2000]

    # Fit the piecewise linear function
    fit_water_supply(Flow, reach, "WaterSupplyJulyAugust")





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

