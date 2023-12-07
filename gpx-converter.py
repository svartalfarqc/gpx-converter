import os
import gpxpy.gpx
import pandas as pd
import numpy as np
from gpx_converter import Converter
from geopy import distance
import matplotlib.pyplot as plt
import plotly.express as px
import tkinter as tk
from tkinter import filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

def read_gpx_file(file_path):
    with open(file_path, 'r') as gpx_file:
        gpx_data = gpxpy.parse(gpx_file)
    return gpx_data.tracks, gpx_data.tracks[0].segments, gpx_data.tracks[0].segments[0].points

def calculate_distance_deltas(gpx_points):
    dist_great_circle = [0]
    dist_geodesic = [0]

    for idx in range(1, len(gpx_points)):
        start = gpx_points[idx-1]
        stop = gpx_points[idx]
        temp_delta_great_circle = distance.great_circle((start.latitude, start.longitude),
                                                        (stop.latitude, stop.longitude)).m
        temp_delta_geodesic = distance.distance((start.latitude, start.longitude),
                                                (stop.latitude, stop.longitude)).m
        dist_great_circle.append(temp_delta_great_circle)
        dist_geodesic.append(temp_delta_geodesic)

    return dist_great_circle, dist_geodesic

def calculate_total_altitude(gpx_df):
    altitude_total_up = gpx_df['altitude_delta_meters'][gpx_df['altitude_delta_meters'] > 0].sum()
    altitude_total_down = gpx_df['altitude_delta_meters'][gpx_df['altitude_delta_meters'] < 0].sum()
    return altitude_total_up, altitude_total_down

def process_gpx_file(file_path, debug = False):
    gpx_tracks, gpx_segments, gpx_points = read_gpx_file(file_path)

    # Convert data into a dataframe
    gpx_df = Converter(input_file=file_path).gpx_to_dataframe()

    # Calculate delta
    gpx_df['time_delta'] = gpx_df['time'].shift(-1) - gpx_df['time']
    gpx_df['time_delta_seconds'] = ((gpx_df['time_delta']
                                     .fillna(pd.Timedelta(seconds=0))
                                     .view('int64')/1000000000))
    gpx_df['altitude_delta_meters'] = gpx_df['altitude'].shift(-1) - gpx_df['altitude']
    dist_great_circle, dist_geodesic = calculate_distance_deltas(gpx_points)
    gpx_df['distance_delta_great-circle_meters'] = dist_great_circle
    gpx_df['distance_delta_geodesic_meters'] = dist_geodesic

    # Calculate sums
    altitude_total_up, altitude_total_down = calculate_total_altitude(gpx_df)
    gpx_df['distance_total_geodesic_meters'] = np.cumsum(dist_geodesic)
    gpx_df['distance_total_geodesic_kilometers'] = round(gpx_df['distance_delta_geodesic_meters'].cumsum() / 1000, 3)
    gpx_df['speed_meters_per_second'] = round(gpx_df['distance_delta_geodesic_meters'] / gpx_df['time_delta_seconds'], 3)
    gpx_df['speed_meters_per_second'].replace(np.inf, 0, inplace=True)
    gpx_df['speed_kilometers_per_hour'] = round(gpx_df['speed_meters_per_second'] * 3.6, 3)

    if debug:
        # Print the results
        print('SessionStart:', gpx_df.iloc[0, 0])
        print('SessionStop:', gpx_df.iloc[-1, 0])
        print('SessionDuration (hh:mm:ss):', gpx_df['time'].max() - gpx_df['time'].min())
        print('SessionDistanceTotal:', round((gpx_df['distance_delta_geodesic_meters'].sum() / 1000), 3), 'km')
        print('SessionWayUp:', altitude_total_up, 'm')
        print('SessionWayDown:', altitude_total_down, 'm')
        print('---')
        print('MaxSpeed:', gpx_df['speed_kilometers_per_hour'].max(), 'km/h')
        print('MinSpeed:', gpx_df['speed_kilometers_per_hour'].min(), 'km/h')
        print('RoundedAvgSpeed:', round(gpx_df['speed_kilometers_per_hour'].mean(), 3), 'km/h')
        print('---')
        print('TimeDeltaMax:', gpx_df['time_delta_seconds'].max())
        print('TimeDeltaMin:', gpx_df['time_delta_seconds'].min())
        print('TimeDeltaMean:', gpx_df['time_delta_seconds'].mean())

    # # Plot with plotly.express
    # fig_2 = px.line(gpx_df, x='time', y=['speed_kilometers_per_hour',
    #                                       'distance_total_geodesic_kilometers',
    #                                       'altitude'],
    #                 template='plotly_dark')
    # fig_2.show()

    return gpx_df

def process_folder():
    folder_path = filedialog.askdirectory(title="Select Folder with GPX Files")

    if folder_path:
        # Get a list of all GPX files in the selected folder
        gpx_files = [f for f in os.listdir(folder_path) if f.endswith('.gpx')]

        # Create an empty list to store DataFrames
        all_results = []

        for gpx_file in gpx_files:
            # Construct the full path to the GPX file
            file_path = os.path.join(folder_path, gpx_file)

            # Process the current GPX file
            gpx_df = process_gpx_file(file_path)

            # Add a source_file column to the DataFrame
            gpx_df['source_file'] = gpx_file

            # Append the DataFrame to the list
            all_results.append(gpx_df)

        # Concatenate all DataFrames into one
        combined_results = pd.concat(all_results, ignore_index=True)

        # Save the combined results to a CSV file
        output_csv = filedialog.asksaveasfilename(defaultextension=".csv",
                                                   filetypes=[("CSV files", "*.csv")],
                                                   title="Save CSV File")

        if output_csv:
            combined_results.to_csv(output_csv, index=False)
            print(f"Results saved to {output_csv}")

        
# Create the main application window
app = tk.Tk()
app.title("GPX Processor")

# Create a button to trigger file selection, processing, and plotting
process_button = tk.Button(app, text="Select folder to process GPX files in", command=process_folder)
process_button.pack(pady=20)

# Run the GUI application
app.mainloop()