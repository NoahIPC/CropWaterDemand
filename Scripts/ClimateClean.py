
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
import os

from urllib.error import HTTPError
import os


def get_stations(bbox):
    columns = ['Station', 'Latitude', 'Longitude', 'Elevation', 'Name']
    Stations = pd.read_csv('https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/doc/ghcnd-stations.txt',
                    sep='\s+', names=columns, usecols=[0, 1, 2, 3, 4], engine='python')

    # Get stations within bounding box
    Stations = Stations[(Stations['Longitude'] >= bbox[0][0]) & (Stations['Longitude'] <= bbox[0][1]) &
                        (Stations['Latitude'] >= bbox[1][0]) & (Stations['Latitude'] <= bbox[1][1])]

    return Stations


def download_stations(Stations, file_dir):
    access = 'https://www.ncei.noaa.gov/data/global-historical-climatology-network-daily/access/'

    for i, station in enumerate(Stations['Station']):
        print(f'{i+1}/{len(Stations)}')

        station += '.csv'

        if os.path.exists(os.path.join(file_dir, station)):
            continue

        try:
            df = pd.read_csv(f'{access}{station}', low_memory=False)
        except HTTPError:
            continue

        if 'TMAX' not in df.columns:
            continue
        
        df.to_csv(os.path.join(file_dir, station))
    


def climate_pivot(file_dir):
    Files = os.listdir(file_dir)

    Climate = []

    for file in Files:
        df = pd.read_csv(os.path.join(file_dir, file), low_memory=False)
        Climate.append(df)

    Climate = pd.concat(Climate, ignore_index=True)

    Climate = Climate[['NAME', 'DATE', 'TMAX', 'TMIN', 'PRCP']]
    Climate['DATE'] = pd.to_datetime(Climate['DATE'])

    # Precipitation is in tenths of mm, convert to inches
    Climate['PRCP'] = Climate['PRCP'] / 254

    # Temperature is in tenths of degrees C, convert to F
    Climate['TMAX'] = Climate['TMAX'] / 10 * 9/5 + 32
    Climate['TMIN'] = Climate['TMIN'] / 10 * 9/5 + 32

    # Replace all -9999 values with NaN
    Climate = Climate.replace(-9999, np.nan)

    # Get all post 1980 data
    Climate = Climate[Climate['DATE'] >= datetime(1980, 1, 1)]

    # Create pivot table NAME as columns, date as index, TMAX as values
    ClimateTMAX = Climate.pivot_table(index='DATE', columns='NAME', values='TMAX')
    ClimateTMIN = Climate.pivot_table(index='DATE', columns='NAME', values='TMIN')
    ClimatePRCP = Climate.pivot_table(index='DATE', columns='NAME', values='PRCP')

    return ClimateTMAX, ClimateTMIN, ClimatePRCP


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

def climate_fill(climateVal):
    climateVal = climateInterpolate(climateVal)
    climateVal = climateInterpolate(climateVal)

    # Drop all columns with more than 1% NaN values
    climateVal = climateVal.dropna(thresh=climateVal.shape[0]*0.99, axis=1)
    climateVal = climateVal.interpolate(method='linear', axis=0).ffill().bfill()

    return climateVal



def climateClean(BasinName, bbox, file_dir, download=True):

    if download:
        # Get all stations within bounding box
        Stations = get_stations(bbox)

        # Download all station data
        download_stations(Stations, file_dir)

    # Create pivot tables for TMAX, TMIN, and PRCP for all stations
    ClimateTMAX, ClimateTMIN, ClimatePRCP = climate_pivot(file_dir)


    ClimateTMAX = climate_fill(ClimateTMAX)
    ClimateTMIN = climate_fill(ClimateTMIN)

    # Drop all columns with more than 10% NaN values
    ClimatePRCP = ClimatePRCP.dropna(thresh=ClimatePRCP.shape[0]*0.9, axis=1).fillna(0)

    ClimateTMAX.to_csv(f'../Outputs/{BasinName}/Climate/ClimateTMAX.csv')
    ClimateTMIN.to_csv(f'../Outputs/{BasinName}/Climate/ClimateTMIN.csv')
    ClimatePRCP.to_csv(f'../Outputs/{BasinName}/Climate/ClimatePRCP.csv')

#%%

# Lat lon bounding box for each basin
BoundingBox = {'SNK':[[-114.8, -109.8], [42, 44.7]],
                'PAY':[[-117, -115], [43.8, 45.2]],
                'BOI':[[-117.1, -115.7], [43.4, 43.9]]}


for BasinName in BoundingBox.keys():
    climateClean(BasinName, BoundingBox[BasinName], f'../Data/Climate/{BasinName}')

# %%
