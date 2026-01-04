import streamlit as st
import xarray as xr
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# --- 1. TITLE & SETUP ---
st.title("🐟 Da Fish Spy 3000: Hawaii Edition")
st.write("Fetching the latest satellite data... wait wunst!")

# Define the Hawaii Box
lat_min, lat_max = 18.5, 22.5 
lon_min, lon_max = -160.0, -154.0

# --- 2. THE DATA SOURCES ---
sst_url = 'https://coastwatch.noaa.gov/erddap/griddap/noaacrwsstDaily'
chl_url = 'https://coastwatch.noaa.gov/erddap/griddap/noaacwN20VIIRSchlaDaily'

# --- 3. HELPER FUNCTION: SMART SLICE ---
def get_smart_slice(ds, var_name, lats, lons):
    """
    This function checks if the satellite reads North-to-South or South-to-North
    and slices it correctly so we don't get empty data.
    """
    # Check Latitude Order
    if ds.latitude[0] > ds.latitude[-1]:
        # Dataset is High-to-Low (Descending)
        lat_slice = slice(lats[1], lats[0]) 
    else:
        # Dataset is Low-to-High (Ascending)
        lat_slice = slice(lats[0], lats[1])
        
    # Grab the data
    data = ds[var_name].sel(
        time=ds['time'].values[-1], # Latest time
        latitude=lat_slice,
        longitude=slice(lons[0], lons[1])
    ).squeeze()
    
    return data

# --- 4. THE MAIN LOADER ---
@st.cache_data
def load_data():
    # Load SST
    ds_sst = xr.open_dataset(sst_url)
    sst = get_smart_slice(ds_sst, 'analysed_sst', (lat_min, lat_max), (lon_min, lon_max))
    
    # Load Chlorophyll
    ds_chl = xr.open_dataset(chl_url)
    chl = get_smart_slice(ds_chl, 'chlor_a', (lat_min, lat_max), (lon_min, lon_max))
    
    latest_date = ds_sst['time'].values[-1]
    return sst, chl, latest_date

# --- 5. RUN THE LOGIC ---
try:
    sst_hawaii, chl_hawaii, latest_date = load_data()
    
    # Check if data is truly empty
    if sst_hawaii.size == 0 or chl_hawaii.size == 0:
        st.error(f"Auwe! One of the datasets is empty. SST Size: {sst_hawaii.size}, Chl Size: {chl_hawaii.size}")
    else:
        st.success(f"Data loaded for {pd.to_datetime(latest_date).date()}! Cheehuu!")

        # --- MAKE THE MAP ---
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Plot SST
        sst_plot = sst_hawaii.plot(ax=ax, cmap='jet', vmin=23, vmax=28, add_colorbar=False)
        
        # Plot Chlorophyll Contours (Safety Check for NaNs)
        # We replace NaNs with 0 just for the contour logic so it doesn't crash
        chl_clean = chl_hawaii.fillna(0)
        chl_levels = np.linspace(0.1, 0.4, 3)
        
        ax.contour(chl_hawaii['longitude'], chl_hawaii['latitude'], chl_clean, 
                   levels=chl_levels, colors='white', alpha=0.6, linewidths=1)

        cbar = plt.colorbar(sst_plot, ax=ax, label="Temp (°C)")
        
        ax.set_title("Hawaii Fish Intel: Temp (Color) + Bait (White Lines)")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.grid(True, linestyle='--', alpha=0.5)

        st.pyplot(fig)

except Exception as e:
    st.error(f"Auwe! Something broke: {e}")
