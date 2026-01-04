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

# --- 3. THE FUNCTION TO GET DATA ---
@st.cache_data
def load_data():
    # --- Load SST ---
    ds_sst = xr.open_dataset(sst_url)
    latest_time_sst = ds_sst['time'].values[-1]
    
    # FIX: We use slice(lat_max, lat_min) because the data is stored North-to-South!
    sst = ds_sst['analysed_sst'].sel(
        time=latest_time_sst,
        latitude=slice(lat_max, lat_min),  # <--- FLIPPED THIS
        longitude=slice(lon_min, lon_max)
    ).squeeze()
    
    # --- Load Chlorophyll ---
    ds_chl = xr.open_dataset(chl_url)
    latest_time_chl = ds_chl['time'].values[-1]
    
    # FIX: Same flip here
    chl = ds_chl['chlor_a'].sel(
        time=latest_time_chl,
        latitude=slice(lat_max, lat_min),  # <--- FLIPPED THIS
        longitude=slice(lon_min, lon_max)
    ).squeeze()
    
    return sst, chl, latest_time_sst

# --- 4. RUN THE LOGIC ---
try:
    sst_hawaii, chl_hawaii, latest_date = load_data()
    
    # Double check we actually got data (no empty arrays)
    if sst_hawaii.size == 0 or chl_hawaii.size == 0:
        st.error("Auwe! The data came back empty. NOAA might be updating the grid.")
    else:
        st.success(f"Data loaded for {pd.to_datetime(latest_date).date()}! Cheehuu!")

        # --- 5. MAKE THE MAP ---
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Plot SST (Temp)
        sst_plot = sst_hawaii.plot(ax=ax, cmap='jet', vmin=23, vmax=28, add_colorbar=False)
        
        # Add contours for Chlorophyll (Food)
        # We assume 0.1 to 0.4 is the good range for plankton
        chl_levels = np.linspace(0.1, 0.4, 3)
        
        ax.contour(chl_hawaii['longitude'], chl_hawaii['latitude'], chl_hawaii, 
                   levels=chl_levels, colors='white', alpha=0.6, linewidths=1)

        # Add a colorbar manually
        cbar = plt.colorbar(sst_plot, ax=ax, label="Temp (°C)")
        
        ax.set_title("Hawaii Fish Intel: Temp (Color) + Bait (White Lines)")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.grid(True, linestyle='--', alpha=0.5)

        # Show it in Streamlit
        st.pyplot(fig)

except Exception as e:
    st.error(f"Auwe! Something broke: {e}")
