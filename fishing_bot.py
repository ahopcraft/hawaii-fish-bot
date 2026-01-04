import streamlit as st
import xarray as xr
import numpy as np
import pandas as pd
import folium
from streamlit_folium import st_folium
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import asyncio
import json
import websockets
from datetime import datetime
import random

# --- 1. SETUP ---
st.set_page_config(layout="wide") 
st.title("🐟 Da Fish Spy: Auto-Detection Mode")

# !!! OPTION A: REAL LIVE BOATS (Needs Key) !!!
AIS_API_KEY = "YOUR_API_KEY_HERE" 

# Hawaii Box
lat_min, lat_max = 18.0, 23.0 
lon_min, lon_max = -161.0, -154.0

# --- 2. DATA SOURCES ---
sst_url = 'https://coastwatch.noaa.gov/erddap/griddap/noaacrwsstDaily'
chl_url = 'https://coastwatch.noaa.gov/erddap/griddap/noaacwN20VIIRSchlaDaily'

# --- 3. HELPER: SMART SLICE ---
def get_smart_slice(ds, var_name, lats, lons):
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

# --- 4. HELPER: COLORIZER ---
def make_image_overlay(data, vmin, vmax, cmap_name):
    if data is None: return None
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    cmap = cm.get_cmap(cmap_name)
    colored_data = cmap(norm(data.values)) 
    mask = np.isnan(data.values)
    colored_data[mask, 3] = 0  
    return colored_data

# --- 5. THE NEW "FISH ALGORITHM" ---
def find_fish_spots(sst, chl):
    """
    Scans the ocean for the 'Sweet Spot':
    Temp: 25.5 - 27.5 (Comfort)
    Bait: > 0.15 (Food)
    """
    fish_spots = []
    
    # We step through the grid (skip every 5th point to save speed)
    # This is a simple scan.
    lats = sst.latitude.values
    lons = sst.longitude.values
    
    # Create masks for good conditions
    good_temp = (sst.values > 25.5) & (sst.values < 27.5)
    good_food = (chl.values > 0.15) & (chl.values < 0.4)
    
    # Find overlap (The Jackpot)
    jackpot = good_temp & good_food
    
    # Get coordinates of jackpot spots
    # We limit to 10 spots so the map isn't crowded
    y_idxs, x_idxs = np.where(jackpot)
    
    # Pick a few random successful spots to mark
    if len(y_idxs) > 0:
        indices = np.linspace(0, len(y_idxs)-1, 10, dtype=int)
        for i in indices:
            lat = lats[y_idxs[i]]
            lon = lons[x_idxs[i]]
            fish_spots.append((lat, lon))
            
    return fish_spots

# --- 6. DATA LOADER ---
@st.cache_data
def load_ocean_data():
    try:
        ds_sst = xr.open_dataset(sst_url)
        sst = get_smart_slice(ds_sst, 'analysed_sst', (lat_min, lat_max), (lon_min, lon_max))
        
        ds_chl = xr.open_dataset(chl_url)
        chl = get_smart_slice(ds_chl, 'chlor_a', (lat_min, lat_max), (lon_min, lon_max))
        
        # We need to interpolate Chl to match SST grid size for the math to work
        chl_interp = chl.interp_like(sst, method='nearest')
        
        latest_date = ds_sst['time'].values[-1]
        return sst, chl_interp, latest_date
    except Exception as e:
        return None, None, None

# --- 7. LIVE BOATS (OR GHOSTS) ---
async def fetch_live_boats():
    # ... (Same AIS code as before) ...
    # IF NO KEY, RETURN FAKE BOATS
    if AIS_API_KEY == a3f776e1f103c6deac3a456373a64b7b1feadcc0:
        return get_ghost_boats()
        
    boats = []
    # ... Real AIS logic would go here ...
    return boats

def get_ghost_boats():
    """Backup: Fake boats for demo"""
    return [
        {"name": "Kolohe Kai", "lat": 20.9, "lon": -156.4},
        {"name": "Da Kine II", "lat": 21.2, "lon": -157.1},
        {"name": "Lawai'a Boy", "lat": 19.8, "lon": -156.1},
    ]

# --- 8. MAIN APP ---
st.write("🤖 Bot is calculating probability... wait wunst...")

sst_data, chl_data, date_val = load_ocean_data()

if sst_data is not None and chl_data is not None:
    st.success(f"Ocean Data Loaded! ({pd.to_datetime(date_val).date()})")
    
    # --- RUN THE FISH ALGO ---
    potential_fish = find_fish_spots(sst_data, chl_data)
    st.info(f"The bot found {len(potential_fish)} High-Probability Fishing Zones!")

    # --- BUILD MAP ---
    m = folium.Map(location=[20.8, -156.6], zoom_start=7)

    # 1. SST Layer
    sst_img = make_image_overlay(sst_data, vmin=24, vmax=28, cmap_name='jet')
    folium.raster_layers.ImageOverlay(
        image=sst_img, bounds=[[lat_min, lon_min], [lat_max, lon_max]],
        opacity=0.6, name="Sea Temp"
    ).add_to(m)

    # 2. Chlorophyll Layer (Hidden by default)
    chl_img = make_image_overlay(chl_data, vmin=0.05, vmax=0.3, cmap_name='viridis')
    folium.raster_layers.ImageOverlay(
        image=chl_img, bounds=[[lat_min, lon_min], [lat_max, lon_max]],
        opacity=0.5, name="Bait (Chl)", show=False
    ).add_to(m)

    # 3. FISH MARKERS (The New Stuff)
    for f_lat, f_lon in potential_fish:
        folium.Marker(
            [f_lat, f_lon],
            popup="Target Species: Ahi/Mahi",
            icon=folium.Icon(color="green", icon="info-sign") # Use simple icon
        ).add_to(m)

    # 4. BOAT MARKERS
    # (Simple version for now - uses Ghost boats if key is missing)
    if st.checkbox("Show Boats"):
        boats = get_ghost_boats() # Using ghost for reliability
        for boat in boats:
            folium.Marker(
                [boat['lat'], boat['lon']],
                popup=f"{boat['name']}",
                icon=folium.Icon(color="black", icon="ship", prefix="fa")
            ).add_to(m)

    folium.LayerControl().add_to(m)
    st_folium(m, width=800, height=600)
    
else:
    st.error("Auwe! Could not load satellite data.")
