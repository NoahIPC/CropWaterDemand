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
import os

# Update this to the name of the basin
BasinName = "SNK"

DiversionTotal = pd.read_csv(
    f"../Outputs/{BasinName}/ReachDiversions.csv", index_col=0, parse_dates=True
)
Reaches = pd.read_csv("../Data/RiverWareReaches.csv")
HistoricalDiversions = pd.read_csv(
    f"../Outputs/{BasinName}/ObservedDiversions.csv", index_col=0, parse_dates=True
)
SlopeThreshold = pd.read_csv(f"../Outputs/{BasinName}/SlopeThreshold.csv", index_col=0)

f = open(f"../Outputs/{BasinName}/RiverWareInputs/FullDiversions.DMI", "w")

PathName = os.path.dirname(os.getcwd()).replace("\\", "/")

for reach in DiversionTotal.columns:
    div = DiversionTotal[reach].loc[datetime(1980, 9, 30) :]
    div = div.resample("1D").ffill()
    div.to_csv(
        f"../Outputs/{BasinName}/RiverWareInputs/FullDiversions/{reach}.txt",
        header=False,
        index=False,
        sep="\t",
    )

    f.write(
        f"FullDiversionReach_{BasinName}.{reach}: file={PathName}/Outputs/{BasinName}/RiverWareInputs/FullDiversions/{reach}.txt import=resize\n"
    )

f.close()

# %%

# Calculate the percentage of the diversions for each reach
Perc = []

for Reach in DiversionTotal.columns:
    if "SNK" not in Reach:
        continue

    for i, row in Reaches.loc[Reaches["RiverWare Reach"] == Reach].iterrows():
        SiteCode = row["IDWR Site Code"]
        try:
            Diversions = pd.read_csv(
                f"../Data/Diversions/{Reach}/{SiteCode}.csv",
                index_col=4,
                parse_dates=True,
                engine="python",
            )
        except FileNotFoundError:
            Perc.append([row["RiverWare Reach"], row["Diversion name"], 0])
            continue

        p = (
            Diversions.loc[
                datetime(2010, 1, 1) : datetime(2018, 1, 1), "Flow (CFS)"
            ].sum()
            / HistoricalDiversions.loc[
                datetime(2010, 1, 1) : datetime(2018, 1, 1), Reach
            ].sum()
        )

        Perc.append(
            [
                row["RiverWare Reach"],
                row["Diversion name"],
                SlopeThreshold.loc[Reach, "Slope"],
                SlopeThreshold.loc[Reach, "Break"],
                SlopeThreshold.loc[Reach, "y2"],
                p,
            ]
        )


Perc = pd.DataFrame(
    Perc, columns=["Diversion", "Name", "Slope", "Break", "Offset", "Percentage"]
)
Perc.fillna(0, inplace=True)
# This feeds into RiverWare
Perc.to_csv(f"../Outputs/{BasinName}/RiverWareInputs/DiversionWeight.csv")


# %%
import uuid

header = f"""# RiverWare_Object 9.0.4 Patch
# Created 13:38 July 3, 2023
# CADSWES, University of Colorado at Boulder, http://cadswes.colorado.edu/
# objects:  1
# clusters: 0
# 
DST 0
FlagEncoding 3
# Section: Objects
set obj {{AdjustmentExport}}
set o "$ws.AdjustmentExport"
$ws SimObj $obj {{DataObj}} 2515 2054 {{}} 2833 50 357 50
"$o" webMapCoords 3050 2907
"$o" geospatialCoords 0 0 357 50
"$o" UUID {{{uuid.uuid4()}}}
"$o" objOrd wsList 6690
"$o" objSlotOrderType ListOrder_DEFAULT 0 Ascend
"$o" {{TableSlot}} {{DiversionWeight_{BasinName}}}
set s "$o.DiversionWeight_{BasinName}"
"$s" order 500 
"$s" UUID {{{uuid.uuid4()}}}
"$s" resize {len(Perc)} 3
"$s" setRowLabels """
for i, row in Perc.iterrows():
    header += "{" + row["Diversion"] + "__" + row["Name"] + "} "

header += """
"$s" setColumnLabels {Slope} {Threshold} {Percent} 
"$s" setMaximums NaN NaN NaN 
"$s" setMinimums NaN NaN NaN 
"$s" setUnitTypes {NONE} {Volume} {NONE} 
"$s" setScales 1 1 1 
"$s" setUsrUnits {NONE} {m3} {NONE} 
"$s" setUsrFormat {%f} {%f} {%f} 
"$s" setUsrPrecision {2} {2} {2} 
"""
unit = 0.000810713193789912

for i, row in Perc.iterrows():
    header += f'"$s" row {i} {row["Slope"]} {row["Break"]/unit} {row["Percentage"]} \n'

header += """"$o" hideSlots 0 hideOff hideEmptyOff
# Section: Snapshot Object Relationships
# Section: Links
"""

print(header)
f = open(f"../Outputs/{BasinName}/RiverWareInputs/DivAdjPopulate.bak", "w")
f.write(header)
f.close()
# %%
