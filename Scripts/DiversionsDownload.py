
"""
This script reads a CSV file containing water diversion data identified by IDWR Site Codes. For each Site Code,
the script generates a URL to access the corresponding historical data (from 1980 to 2020) in CSV format from
the Idaho Department of Water Resources (IDWR) website.

In case there's no data available for a specific Site Code, an EmptyDataError exception is raised, caught, and a
message is printed indicating the Site Code for which data is missing.

For each Site Code with data, the script cleans the DataFrame by removing unnamed columns. It then retrieves the
corresponding 'RiverWare Reach' value from the original CSV file, and checks if a directory with the Reach's name
exists under the 'Diversions' directory in the 'Data' directory. If not, it creates one.

Finally, the script writes the cleaned DataFrame to a CSV file in the corresponding Reach's directory. The filename
is the IDWR Site Code. The index column of the DataFrame is not included in the output file.

"""

#%%
import pandas as pd
from pandas.errors import EmptyDataError
import numpy as np
import os

# Read in the diversion data
Reaches = pd.read_csv('../Data/RiverWareReaches.csv')

for site in Reaches['IDWR Site Code']:

    year_list = np.arange(1980, 2021, 1)

    year_list = ','.join([str(x) for x in year_list])

    url = f'https://research.idwr.idaho.gov/apps/Shared/WaterServices/Accounting/History?sitelist={site}&yearlist={year_list}&yeartype=IY&f=csv'

    try:
        df = pd.read_csv(url)
    except EmptyDataError:
        print(f'No data for {site}')
        continue

    # Drop any unnamed columns
    df = df.loc[:, ~df.columns.str.contains('Unnamed')]

    Reach = Reaches.loc[Reaches['IDWR Site Code'] == site, 'RiverWare Reach'].values[0]

    # Check if folder exists, if not create it
    if not os.path.exists(f'../Data/Diversions/{Reach}'):
        os.makedirs(f'../Data/Diversions/{Reach}')

    df.to_csv(f'../Data/Diversions/{Reach}/{site}.csv', index=False)

# %%

# Calculate diversions to Lake Lowell
import pandas as pd
import matplotlib.pyplot as plt


Lowell = pd.read_html("https://www.usbr.gov/pn-bin/daily.pl?station=low&format=html&year=1980&month=9&day=30&year=2023&month=8&day=31&pcode=af", 
                                index_col=0, parse_dates=True)[0]

Div = Lowell.rolling(14, center=True).mean().diff().clip(0)

Div.to_csv("../Data/Diversions/Reach7Diversions_BOI/NonIrr.csv")

# Plot 1983
plt.plot(Div.loc["1983-01-01":"1983-12-31"])