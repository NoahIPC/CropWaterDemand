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

# Update this to the name of the basin
BasinName = 'SNK'

DiversionTotal = pd.read_csv(f'../Outputs/{BasinName}/ReachDiversions.csv')
Reaches = pd.read_csv('../Data/RiverWareReaches.csv')
HistoricalDiversions = pd.read_csv(f'../Outputs/{BasinName}/ObservedDiversions.csv', index_col=0, parse_dates=True)


# Calculate the percentage of the diversions for each reach
Perc = []

for Reach in DiversionTotal.columns:

    if 'SNK' not in Reach:
        continue

    for i, row in Reaches.loc[Reaches['RiverWare Reach']==Reach].iterrows():

        SiteCode = row['IDWR Site Code']
        try:
            Diversions = pd.read_csv(f'../Data/Diversions/{Reach}/{SiteCode}.csv', 
                            index_col=4, parse_dates=True, engine='python')
        except FileNotFoundError:
            Perc.append([row['RiverWare Reach'], row['Diversion name'], 0])
            continue

        Perc.append([row['RiverWare Reach'], row['Diversion name'], Diversions.loc[datetime(2010,1,1):datetime(2018,1,1), 'Flow (CFS)'].sum()/HistoricalDiversions.loc[datetime(2010,1,1):datetime(2018,1,1), Reach].sum()])


Perc = pd.DataFrame(Perc, columns=['Diversion', 'Name', 'Percent'])
# This feeds into RiverWare
Perc.to_csv(f'../Outputs/{BasinName}/RiverWareInputs/DiversionWeight.csv')

# %%
import os
f = open(f'../Outputs/{BasinName}/RiverWareInputs/DivAdjPopulate.DMI', 'w')

PathName = os.path.dirname(os.getcwd()).replace('\\', '/')

for reach in Reaches['RiverWare Reach'].unique():

    if 'SNK' not in reach:
        continue

    f.write(f'FullDiversionReach_{BasinName}.{reach}: file={PathName}/Outputs/{BasinName}/Reach3Diversions_SNK__Breaks import=resize\n')
    

# %%
