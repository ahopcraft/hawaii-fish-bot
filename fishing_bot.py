import streamlit as st
import xarray as xr
import numpy as np
import pandas as pd
import folium
from streamlit_folium import st_folium
import matplotlib.cm as cm
import matplotlib.colors as mcolors

# --- 1. TITLE & SETUP ---
st.set_page_config(layout="wide") # Make the app wide so the map is big!
st.title("🐟 Da Fish Spy 3000: Zoom Edition")
st.write("Fetching the latest satellite data... wait wunst!")

# Define the Hawaii Box (Slightly wider for zooming)
lat_min, lat_max = 18.0, 23.0 
lon_min, lon_max = -161.0, -154.0

# --- 2. DATA SOURCES ---
sst_url = 'https://coastwatch.noaa.gov/erddap/griddap/noaacrwsstDaily'

# --- 3. HELPER: SMART SLICE (Keeps data straight) ---
def get_smart_slice(ds, var_name, lats, lons):
    # Check if lat is flipped
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

# --- 4. LOADER ---
@st.cache_data
def load_data():
    ds_sst = xr.open_dataset(sst_url)
    sst = get_smart_slice(ds_sst, 'analysed_sst', (lat_min, lat_max), (lon_min, lon_max))
    latest_date = ds_sst['time'].values[-1]
    return sst, latest_date

# --- 5. COLORIZER HELPER (Turns data into an image overlay) ---
def make_image_overlay(data, vmin=24, vmax=28, cmap_name='jet'):
    """
    Folium can't read raw numbers, so we turn the temperature data 
    into a colored picture (PNG style) with transparency.
    """
    # 1. Normalize data (squish numbers between 0 and 1)
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    
    # 2. Apply colormap (turn 0-1 into Red-Blue colors)
    cmap = cm.get_cmap(cmap_name)
    colored_data = cmap(norm(data.values)) # This makes RGBA array
    
    # 3. Handle "Empty" pixels (Clouds/Land) - Make them transparent
    # Any NaN (Not a Number) becomes see-through
    mask = np.isnan(data.values)
    colored_data[mask, 3] = 0  # Set Alpha (transparency) to 0
    
    return colored_data

# --- 6. MAIN APP LOGIC ---
try:
    sst_hawaii, latest_date = load_data()
    
    st.success(f"Latest Intel: {pd.to_datetime(latest_date).date()}")

    # --- BUILD THE MAP ---
    # Center on Maui
    m = folium.Map(location=[20.8, -156.6], zoom_start=7)

    # Convert SST data to an image for the map
    sst_img = make_image_overlay(sst_hawaii, vmin=24, vmax=28)

    # Add the Image Overlay to the map
    # We need the bounds: [[lat_min, lon_min], [lat_max, lon_max]]
    # Note: Xarray lats might be upside down, so we force the correct bounds
    image_bounds = [[lat_min, lon_min], [lat_max, lon_max]]
    
    folium.raster_layers.ImageOverlay(
        image=sst_img,
        bounds=image_bounds,
        opacity=0.6,
        name="Sea Surface Temp"
    ).add_to(m)

    # Add a Layer Control so you can toggle it on/off
    folium.LayerControl().add_to(m)

    # Display the interactive map
    st_folium(m, width=700, height=500)

except Exception as e:
    st.error(f"Auwe! Something broke: {e}")
