# River Data Analysis Pipeline

This repository contains a pipeline of scripts designed for processing and analyzing river diversion and climate data, generating predictive models, and applying these models to adjust diversions. The scripts are meant to be executed in the following order:

## 1. DiversionsDownload.py
Downloads water diversion data identified by IDWR Site Codes from the Idaho Department of Water Resources (IDWR) website. The script handles missing data and exports cleaned dataframes for each site into separate CSV files.

## 2. ClimateClean.py
Processes two climate datasets from 1980-2022. The script merges the datasets, cleans and formats the data, and handles missing data using regression and linear interpolation. Outputs include cleaned datasets for maximum and minimum temperatures, and processed precipitation data.

## 3. ClimateDemand.py
Processes the cleaned climate data and river diversion data to generate predictive models for each river reach. The script finds the best fit climate station for each reach and generates predictions for the entire period. Outputs include the best model results and the diversion predictions for each reach.

## 4. WaterSupplyAdjustment.py
Performs a detailed analysis of river diversions, unregulated inflows, and reservoir storage to determine the best piecewise linear fit for each reach. The script calculates the gap between historical and modeled diversions, and computes a piecewise linear fit of the river diversion as a function of water supply. Outputs include the slopes and break values for each reach and month.

## 5. RiverWareFormat.py
Computes and applies diversion adjustments on the basis of historical data. The script then generates a DMI script to populate data in a RiverWare model. The outputs include adjusted diversion data, interpolated slope and breakpoint values, and a .DMI file for data population in RiverWare.

For each script, more detailed explanations of the procedures, input and output files, and involved libraries are provided in the script comments. Ensure you have all necessary Python packages installed and the required input data files are in the appropriate directories before running each script.
