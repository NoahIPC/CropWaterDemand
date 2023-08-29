"""
This script processes climate and river diversion data to generate predictive
models for each river reach. It imports datasets of daily maximum and minimum
temperatures, and precipitation, as well as a list of river reaches and
diversions.

For each reach, it sums up the diversions, subtracts any recharge present, and
removes leap days and negative values. It then finds the best fit climate
station for each reach by iterating through all stations and evaluating a
Gradient Boosting Regressor model's performance.

The script then generates predictions for the entire period, and saves the best
model results and the diversion predictions for each reach into CSV files.

Libraries used include pandas for data handling, datetime for time-series
manipulations, sklearn for modeling and metrics, and the QuantileTransformer
for normalization of the target variable.
"""
# %%

import pandas as pd
from datetime import datetime
from sklearn.metrics import r2_score

from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import r2_score
from sklearn.preprocessing import QuantileTransformer

import plotly.graph_objects as go

import os


# Update this to the name of the basin
BasinName = "PAY"

# From USBR RiverWare Report
Reaches = pd.read_csv("../Data/RiverWareReaches.csv")

# Load weather data
ClimateTMAX = pd.read_csv(f"../Outputs/{BasinName}/Climate/ClimateTMAX.csv", 
                          index_col=0, parse_dates=True)
ClimateTMIN = pd.read_csv(f"../Outputs/{BasinName}/Climate/ClimateTMIN.csv",
                          index_col=0, parse_dates=True)
ClimatePRCP = pd.read_csv(f"../Outputs/{BasinName}/Climate/ClimatePRCP.csv", 
                          index_col=0, parse_dates=True)

# Only use reaches the end with BasinName
Reaches = Reaches[Reaches["RiverWare Reach"].str.contains(f"_{BasinName}")]


# Create a dataframe to store observed diversions for each reach
ObservedDiversions = pd.DataFrame(index=ClimateTMAX.index, 
                                  columns=Reaches["RiverWare Reach"].unique()).fillna(0)

# Sum up all diversions for each reach
for Reach in Reaches["RiverWare Reach"].unique():
    Diversions = pd.Series(index=ClimateTMAX.index, dtype=float).fillna(0)

    # Sum up all diversions for the given reach
    for div in Reaches.loc[Reaches["RiverWare Reach"] == Reach, "IDWR Site Code"]:
        try:
            div_val = pd.read_csv(f"../Data/Diversions/{Reach}/{div}.csv", engine="python")
            div_val.index = pd.to_datetime(div_val["HSTDate"])
            div_val = div_val[~div_val.index.duplicated()]
            div_val = div_val["Flow (CFS)"].reindex(ClimateTMAX.index).clip(lower=0).fillna(0)
            Diversions += div_val.values

        except FileNotFoundError:
            print(f"No diversion data for {Reach} {div}")
            continue

    # Subtract out recharge if present
    try:
        rech = pd.read_csv(
            f"../Data/Diversions/{Reach}/Recharge.csv", index_col=0, parse_dates=True
        )
        Diversions -= rech.reindex(Diversions.index).fillna(0).values.flatten()
    except FileNotFoundError:
        pass

    # Set values outside irrigation season to 0
    Diversions[(Diversions.index.dayofyear < 74) | (Diversions.index.dayofyear > 319)] = 0

    # Reindex to 1980 - 2018
    Diversions = Diversions.reindex(pd.date_range(datetime(1980, 1, 1), datetime(2018, 12, 31)))

    # Remove leap days and negative values
    Diversions = Diversions.clip(lower=0).fillna(0)
    Diversions = Diversions[~((Diversions.index.month == 2) & (Diversions.index.day == 29))]

    ObservedDiversions[Reach] += Diversions

#%%

# Find all columns with data for ClimateTMAX, ClimateTMIN, ClimatePRCP
cols = list(set(ClimateTMAX.columns)
    .intersection(ClimateTMIN.columns)
    .intersection(ClimatePRCP.columns))


DiversionTotal = pd.DataFrame(index=ClimateTMAX.index)

ModelResults = []

for Reach in ObservedDiversions.columns:

    Diversions = ObservedDiversions[Reach].copy()

    if Diversions.mean()<1:
        MedianDiv = ObservedDiversions.loc[ObservedDiversions[Reach]>0, Reach]
        MedianDiv = MedianDiv.groupby(MedianDiv.index.dayofyear).median()
        for i in MedianDiv.index:
            DiversionTotal.loc[DiversionTotal.index.dayofyear == i, Reach] = MedianDiv.loc[i]
        DiversionTotal[Reach] = DiversionTotal[Reach].fillna(0)
        DiversionTotal = DiversionTotal.copy()
        continue

    rMax = 0
    colMax = ""
    rfFit = None

    # Iterate through all climate stations to find best fit
    for Station in cols:

        def ClimateStation(Station):
            Climate = pd.concat((ClimateTMAX[Station], ClimateTMIN[Station], ClimatePRCP[Station]), axis=1)
            Climate.columns = ["TMAX", "TMIN", "PRCP"]
            Climate["DayOfYear"] = Climate.index.dayofyear

            Climate["PRCP"] = Climate["PRCP"].rolling(7).mean()

            return Climate

        Climate = ClimateStation(Station)
    
        # Years that have have a full water supply
        if BasinName == "SNK":
            Years = [2010, 2012, 2014, 2017, 2018]
        elif BasinName == "BOI":
            Years = [2010, 2011, 2012, 2014, 2016, 2017, 2018]

        ClimateYear = Climate[[year in Years for year in Climate.index.year]]

        ClimateYear = ClimateYear.interpolate(limit=10).dropna()

        DiversionsYear = Diversions.reindex(ClimateYear.index).fillna(0)
        qt = QuantileTransformer(n_quantiles=10)
        DiversionsYear = qt.fit_transform(DiversionsYear.values.reshape(-1, 1)).flatten()

        (TrainClimate, 
         TestClimate, 
         TrainDiv, 
         TestDiv) = train_test_split(ClimateYear, 
                                     DiversionsYear, test_size=0.3, shuffle=False)

        rf = GradientBoostingRegressor(n_estimators=100, max_depth=3)
        rf.fit(TrainClimate, TrainDiv)

        TestPred = rf.predict(TestClimate)
        TestPred = qt.inverse_transform(TestPred.reshape(-1, 1)).flatten()
        TestPred = pd.Series(data=TestPred, index=TestClimate.index).fillna(0)

        TestDiv = qt.inverse_transform(TestDiv.reshape(-1, 1)).flatten()
        TestDiv = pd.Series(data=TestDiv, index=TestClimate.index)

        if (r2_score(TestDiv, TestPred.bfill().ffill())> rMax):
            rMax = r2_score(TestDiv, TestPred)
            colMax = Station
            rfFit = rf

    print(f"Reach: {Reach}")
    print(f"Max R2: {rMax}")
    print(f"Column: {colMax}")
    Climate = ClimateStation(colMax)
    MissPred = rfFit.predict(Climate.dropna())
    MissPred = qt.inverse_transform(MissPred.reshape(-1, 1)).flatten()
    MissPred = pd.Series(data=MissPred, index=Climate.dropna().index).fillna(0)
    MissPred = MissPred.reindex(DiversionTotal.index).fillna(0)

    # if folder doesn't exist, create it
    if not os.path.exists(f"../Outputs/{BasinName}/Figures/ModeledDiversions"):
        os.makedirs(f"../Outputs/{BasinName}/Figures/ModeledDiversions")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=MissPred.index, y=MissPred, name="Modeled Full Water Supply Demand"))
    fig.add_trace(go.Scatter(x=ObservedDiversions.index, y=ObservedDiversions[Reach], name="Observed Demand"))
    fig.update_layout(title=f"{Reach} Modeled vs Observed Diversions", xaxis_title="Date", yaxis_title="Diversions (cfs)")
    fig.write_html(f"../Outputs/{BasinName}/Figures/ModeledDiversions/{Reach}ModeledDiversions.html")

    DiversionSum = Diversions.resample("1Y").sum().mean() * 1.9835
    ModelResults.append([Reach, colMax, rMax, DiversionSum])

    DiversionTotal[Reach] = MissPred
    DiversionTotal = DiversionTotal.copy()

ModelResults = pd.DataFrame(
    ModelResults,
    columns=["Reach", "Climate Station", "R2 Test", "Annual Diversion (AF)"],
)
ModelResults.to_csv(f"../Outputs/{BasinName}/ClimateRegressionResults.csv")
DiversionTotal.to_csv(f"../Outputs/{BasinName}/ReachDiversions.csv")
ObservedDiversions.to_csv(f"../Outputs/{BasinName}/ObservedDiversions.csv")

