import streamlit as st
import xarray as xr
import numpy as np
import pandas as pd
import folium
from streamlit_folium import st_folium
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import random

# --- 1. TITLE & SETUP ---
st.set_page_config(layout="wide") 
st.title("🐟 Da Fish Spy 3000: The Works")
st.write("Fetching SST, Bait, and Boat data... wait wunst!")

# Define the Hawaii Box
lat_min, lat_max = 18.0, 23.0 
lon_min, lon_max = -161.0, -154.0

# --- 2. DATA SOURCES ---
sst_url = 'https://coastwatch.noaa.gov/erddap/griddap/noaacrwsstDaily'
chl_url = 'https://coastwatch.noaa.gov/erddap/griddap/noaacwN20VIIRSchlaDaily'

# --- 3. HELPER: SMART SLICE ---
def get_smart_slice(ds, var_name, lats, lons):
    """Checks if satellite is reading North-to-South or South-to-North"""
    if ds.latitude[0] > ds.latitude[-1]:
        lat_slice = slice(lats[1], lats[0]) 
    else:
        lat_slice = slice(lats[0], lats[1])
        
    data = ds[var_name].sel(
        time=ds['time'].values[-1],
        latitude=lat_slice,
        longitude=slice(lons[0], lons[1])
    ).squeeze()
    return data

# --- 4. HELPER: MAKE IMAGE OVERLAY ---
def make_image_overlay(data, vmin, vmax, cmap_name):
    """Turns raw data numbers into a colored picture for the map"""
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    cmap = cm.get_cmap(cmap_name)
    colored_data = cmap(norm(data.values)) 
    
    # Make clouds/empty pixels transparent
    mask = np.isnan(data.values)
    colored_data[mask, 3] = 0  
    return colored_data

# --- 5. HELPER: GHOST BOATS ---
def get_ghost_boats(n_boats=10):
    """Simulates other fishermen (since we don't have a paid API)"""
    boats = []
    for _ in range(n_boats):
        # Random spots near the islands
        lat = random.uniform(20.5, 21.5)
        lon = random.uniform(-157.5, -156.0)
        boats.append((lat, lon))
    return boats

# --- 6. MAIN LOADER ---
@st.cache_data
def load_all_data():
    # Load SST
    ds_sst = xr.open_dataset(sst_url)
    sst = get_smart_slice(ds_sst, 'analysed_sst', (lat_min, lat_max), (lon_min, lon_max))
    
    # Load Chlorophyll
    ds_chl = xr.open_dataset(chl_url)
    chl = get_smart_slice(ds_chl, 'chlor_a', (lat_min, lat_max), (lon_min, lon_max))
    
    latest_date = ds_sst['time'].values[-1]
    return sst, chl, latest_date

# --- 7. APP LOGIC ---
try:
    sst_hawaii, chl_hawaii, latest_date = load_all_data()
    
    st.success(f"All Intel Loaded for {pd.to_datetime(latest_date).date()}!")

    # --- BUILD THE MAP ---
    m = folium.Map(location=[20.8, -156.6], zoom_start=7)

    # LAYER A: TEMPERATURE (Red/Blue)
    # We use 'jet' colors.
    sst_img = make_image_overlay(sst_hawaii, vmin=24, vmax=28, cmap_name='jet')
    folium.raster_layers.ImageOverlay(
        image=sst_img,
        bounds=[[lat_min, lon_min], [lat_max, lon_max]],
        opacity=0.6,
        name="Sea Surface Temp (SST)"
    ).add_to(m)

    # LAYER B: CHLOROPHYLL (Green)
    # We use 'viridis' (Greens/Yellows) for bait. 
    # vmin 0.05 to 0.3 is usually good for finding plankton blooms.
    chl_img = make_image_overlay(chl_hawaii, vmin=0.05, vmax=0.3, cmap_name='viridis')
    folium.raster_layers.ImageOverlay(
        image=chl_img,
        bounds=[[lat_min, lon_min], [lat_max, lon_max]],
        opacity=0.5,
        name="Chlorophyll (Bait)",
        show=False # Start with this HIDDEN so it doesn't look messy
    ).add_to(m)

    # LAYER C: BOATS
    boats = get_ghost_boats()
    for b_lat, b_lon in boats:
        folium.Marker(
            [b_lat, b_lon],
            popup="Fishing Vessel (Simulated)",
            icon=folium.Icon(color="black", icon="ship", prefix="fa")
        ).add_to(m)

    # Add the Layer Control (The Menu button to toggle layers)
    folium.LayerControl().add_to(m)

    # Show the map
    st_folium(m, width=800, height=600)

except Exception as e:
    st.error(f"Auwe! Something broke: {e}")
