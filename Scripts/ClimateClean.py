
"""
This script cleans and processes two climate datasets from 1980-2000 and 2000-2022. 
It concatenates the datasets, converts dates, and replaces missing data marked as -9999 with NaN. 
Three pivot tables for maximum temperature (TMAX), minimum temperature (TMIN), and precipitation (PRCP) are created.

Two functions, climateInterpolate and climateClean, handle missing data. 
They use linear regression to estimate missing TMAX and TMIN values based on the most strongly correlated column.

climateInterpolate drops columns with >90% missing data and fills missing values using a regression model.

climateClean applies climateInterpolate twice, drops columns with >99% missing data, 
and fills remaining missing data using linear interpolation.

The cleaned TMAX, TMIN, and processed PRCP (dropping columns with >10% missing data and filling remaining with zero)
are written to CSV files.
"""
#%%
import pandas as pd
from datetime import datetime
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
import numpy as np

df = pd.read_csv('../Data/Climate/1980_2000.csv')
df2 = pd.read_csv('../Data/Climate/2000_2022.csv')

Climate = pd.concat([df, df2], ignore_index=True)


Climate['DATE'] = pd.to_datetime(Climate['DATE'].astype(str), format='%Y%m%d')

# Replace all -9999 values with NaN
Climate = Climate.replace(-9999, np.nan)


# Create pivot table STATION_NAME as columns, date as index, TMAX as values
ClimateTMAX = Climate.pivot_table(index='DATE', columns='STATION_NAME', values='TMAX')
ClimateTMIN = Climate.pivot_table(index='DATE', columns='STATION_NAME', values='TMIN')
ClimatePRCP = Climate.pivot_table(index='DATE', columns='STATION_NAME', values='PRCP')

def climateInterpolate(climateVal):
    climateVal = climateVal.loc[:datetime(2019, 1, 1)]

    # Drop all columns with more than 90% NaN values
    climateVal = climateVal.dropna(thresh=climateVal.shape[0]*0.1, axis=1)

    # For each column, fill nan values using regression method
    for col in climateVal.columns:
        r2Max = 0
        colMax = ''

        for col2 in climateVal.columns:
            df = climateVal[[col, col2]].dropna()
            if (len(df)==0) | (col == col2):
                continue
            X = df[col2].values.reshape(-1, 1)
            y = df[col].values.reshape(-1, 1)
            r2 = r2_score(y, X)

            if r2 > r2Max:
                r2Max = r2
                colMax = col2

        df = climateVal[[col, colMax]].dropna()
        X = df[colMax].values.reshape(-1, 1)
        y = df[col].values.reshape(-1, 1)
        model = LinearRegression().fit(X, y)


        mask = climateVal[col].isna() & climateVal[colMax].notna()

        if len(climateVal[mask])==0:
            continue

        # Replace missing values with regression
        climateVal.loc[mask, col] = model.predict(climateVal.loc[mask, colMax].values.reshape(-1, 1)).flatten()
        
    return climateVal

def climateClean(climateVal):
    climateVal = climateInterpolate(climateVal)
    climateVal = climateInterpolate(climateVal)

    # Drop all columns with more than 99% NaN values
    climateVal = climateVal.dropna(thresh=climateVal.shape[0]*0.99, axis=1)
    climateVal = climateVal.interpolate(method='linear', axis=0).ffill().bfill()

    return climateVal

ClimateTMAX = climateClean(ClimateTMAX)
ClimateTMIN = climateClean(ClimateTMIN)

# Drop all columns with more than 10% NaN values
ClimatePRCP = ClimatePRCP.dropna(thresh=ClimatePRCP.shape[0]*0.9, axis=1).fillna(0)

ClimateTMAX.to_csv('../Outputs/Climate/ClimateTMAX.csv')
ClimateTMIN.to_csv('../Outputs/Climate/ClimateTMIN.csv')
ClimatePRCP.to_csv('../Outputs/Climate/ClimatePRCP.csv')

# %%
