"""

Diversion Adjustment and Data Population Script
This script computes and applies diversion adjustments on the basis of historical
data. It then generates a DMI script to populate data in a RiverWare model.

Key steps and operations:
Data Importing: Loads total diversions, historical diversions, and reach
information.

Diversions Percentage Calculation: Calculates the percentage of
diversions for each reach and exports the results to a CSV file.

Modeled Diversions Adjustment: Adjusts each modeled diversion according
to the calculated percentage and exports the results.

Slope and Breakpoints Processing: Loads and restructures slope and
breakpoint data, interpolating these values across all dates.

DMI Script Generation: Writes a .DMI file which populates data in a
RiverWare model with the interpolated values.

This script uses pandas, datetime, and python file I/O operations.

"""

# %%
import pandas as pd
from datetime import datetime


DiversionTotal = pd.read_csv(f'../Outputs/ReachDiversions.csv')
Reaches = pd.read_csv('../Data/Diversions/ModelDiversions.csv')
HistoricalDiversions = pd.read_csv('../Outputs/ObservedDiversions.csv', index_col=0, parse_dates=True)


# Calculate the percentage of the diversions for each reach
Perc = []

for div in DiversionTotal.columns:
    
    Reach = div.split('/')[0]

    if 'SNK' not in div:
        continue

    Diversions = pd.read_csv(f'../Data/Diversions/{Reach}/{div.split("/")[1]}.csv', 
                    index_col=0, parse_dates=True, engine='python')

    divName = Reaches.loc[Reaches['IDWR Site Code']==int(div.split('/')[1]), 'Diversion name'].iloc[0]

    Perc.append([div, divName, Diversions.loc[datetime(2010,1,1):datetime(2018,1,1), 'Flow (CFS)'].sum()/HistoricalDiversions.loc[datetime(2010,1,1):datetime(2018,1,1), Reach].sum()])


Perc = pd.DataFrame(Perc, columns=['Diversion', 'Name', 'Percent'])
# This feeds into RiverWare
Perc.to_csv('../Outputs/RiverWareInputs/DiversionPercent.csv')

# %%

# Adjust each modeled diversion by the percentage of the historical diversion
ModeledDiversions = pd.read_csv('../Outputs/ReachDiversions.csv', index_col=0, parse_dates=True)
Perc = pd.read_csv('../Outputs/DiversionPercent.csv', index_col=0)
DiversionSWSI = pd.read_csv('../Outputs/DiversionSWSI.csv', index_col=0)


ModeledDiversions = ModeledDiversions.reindex(pd.date_range(datetime(1980, 9, 30), datetime(2018, 9, 30), freq='1D')).fillna(0)


for i, div in Perc.iterrows():

    AdjustmentName = div['Diversion'].split('/')[0]+'__'+div['Name']
    reach = div['Diversion'].split('/')[0]

    adj = ModeledDiversions[reach]*div['Percent']

    adj.to_csv(f'../Outputs/Diversions/RiverWareInputs/{AdjustmentName}', index=False, header=False)


# %%

Breaks = pd.read_csv('../Outputs/DiversionSWSIBreaks.csv', index_col=0).T
Slopes1 = pd.read_csv('../Outputs/DiversionSWSISlopes1.csv', index_col=0).T
Slopes2 = pd.read_csv('../Outputs/DiversionSWSISlopes2.csv', index_col=0).T

Breaks.index = Breaks.index.astype(int)
Slopes1.index = Slopes1.index.astype(int)
Slopes2.index = Slopes2.index.astype(int)

BreaksInt = pd.DataFrame(index=pd.date_range(datetime(1980, 9, 30), datetime(2018, 9, 30)), columns=Breaks.columns).fillna(0)
Slopes1Int = pd.DataFrame(index=pd.date_range(datetime(1980, 9, 30), datetime(2018, 9, 30)), columns=Slopes1.columns).fillna(0)
Slopes2Int = pd.DataFrame(index=pd.date_range(datetime(1980, 9, 30), datetime(2018, 9, 30)), columns=Slopes2.columns).fillna(0)

for month in Breaks.index:
    for reach in Breaks.columns:
        BreaksInt.loc[BreaksInt.index.month==month, reach] = Breaks.loc[month, reach]
        Slopes1Int.loc[Slopes1Int.index.month==month, reach] = Slopes1.loc[month, reach]
        Slopes2Int.loc[Slopes2Int.index.month==month, reach] = Slopes2.loc[month, reach]

BreaksInt.to_csv('../Outputs/DiversionSWSIBreaksInt.csv')
Slopes1Int.to_csv('../Outputs/DiversionSWSISlopes1Int.csv')
Slopes2Int.to_csv('../Outputs/DiversionSWSISlopes2Int.csv')

for col in BreaksInt.columns:
    BreaksInt[col].to_csv(f'../Outputs/Diversions/Monthly/{col}__Breaks', index=False, header=False)
    Slopes1Int[col].to_csv(f'../Outputs/Diversions/Monthly/{col}__Slopes1', index=False, header=False)
    Slopes2Int[col].to_csv(f'../Outputs/Diversions/Monthly/{col}__Slopes2', index=False, header=False)
# %%
import os
f = open('../Outputs/RiverWareInputs/DivAdjPopulate.DMI', 'w')

PathName = os.path.dirname(os.getcwd()).replace('\\', '/')

for col in BreaksInt.columns:
    f.write(f'AdjRetry.{col}__Breaks: file={PathName}/Outputs/Diversions/Monthly/{col}__Breaks import=resize\n')
    f.write(f'AdjRetry.{col}__Slopes1: {PathName}/Outputs/Diversions/Monthly/{col}__Slopes1 import=resize\n')
    f.write(f'AdjRetry.{col}__Slopes2: {PathName}/Outputs/Diversions/Monthly/{col}__Slopes2 import=resize\n')

f.close()

# %%
