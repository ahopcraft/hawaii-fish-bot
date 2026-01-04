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

# --- 1. SETUP ---
st.set_page_config(layout="wide") 
st.title("🐟 Da Fish Spy: LIVE + BAIT Edition")

# !!! PUT YOUR KEY HERE !!!
AIS_API_KEY = "YOUR_API_KEY_HERE" 

# Hawaii Box
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

# --- 4. HELPER: COLORIZER ---
def make_image_overlay(data, vmin, vmax, cmap_name):
    """Turns data into a colored picture"""
    if data is None: return None
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    cmap = cm.get_cmap(cmap_name)
    colored_data = cmap(norm(data.values)) 
    
    # Make clouds/empty pixels transparent
    mask = np.isnan(data.values)
    colored_data[mask, 3] = 0  
    return colored_data

# --- 5. DATA LOADER (SST + CHLOROPHYLL) ---
@st.cache_data
def load_ocean_data():
    try:
        # Load SST
        ds_sst = xr.open_dataset(sst_url)
        sst = get_smart_slice(ds_sst, 'analysed_sst', (lat_min, lat_max), (lon_min, lon_max))
        
        # Load Chlorophyll
        ds_chl = xr.open_dataset(chl_url)
        chl = get_smart_slice(ds_chl, 'chlor_a', (lat_min, lat_max), (lon_min, lon_max))
        
        latest_date = ds_sst['time'].values[-1]
        return sst, chl, latest_date
    except Exception as e:
        return None, None, None

# --- 6. LIVE BOAT FETCHING (AIS) ---
async def fetch_live_boats():
    boats = []
    bbox = [[[lat_min, lon_min], [lat_max, lon_max]]]
    subscribe_message = {
        "APIKey": AIS_API_KEY,
        "BoundingBoxes": bbox,
        "FiltersShipMMSI": [],
        "FilterMessageTypes": ["PositionReport"]
    }
    uri = "wss://stream.aisstream.io/v0/stream"

    try:
        async with websockets.connect(uri) as websocket:
            await websocket.send(json.dumps(subscribe_message))
            start_time = datetime.now()
            # Listen for 3 seconds
            while (datetime.now() - start_time).seconds < 3:
                try:
                    message_json = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    message = json.loads(message_json)
                    if "PositionReport" in message["Message"]:
                        report = message["Message"]["PositionReport"]
                        lat = report["Latitude"]
                        lon = report["Longitude"]
                        name = message["MetaData"]["ShipName"]
                        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                            boats.append({"name": name.strip(), "lat": lat, "lon": lon})
                except asyncio.TimeoutError:
                    break 
                except Exception:
                    break
    except Exception as e:
        st.error(f"Could not connect to live AIS: {e}")
    return boats

# --- 7. MAIN APP EXECUTION ---
st.write("Fetching Satellite Intel & Scanning Radio Frequencies...")

# A. Load Satellite Data
sst_data, chl_data, date_val = load_ocean_data()

if date_val:
    st.info(f"Satellite Data Date: {pd.to_datetime(date_val).date()}")

# B. Load Live Boats (On Button Click)
if st.button("🔄 Scan for Live Boats"):
    if AIS_API_KEY == a3f776e1f103c6deac3a456373a64b7b1feadcc0:
        st.error("Auwe! You forgot to put your API Key in the code, brah!")
        live_boats = []
    else:
        live_boats = asyncio.run(fetch_live_boats())
        st.success(f"Caught {len(live_boats)} live signals!")
else:
    live_boats = []

# C. Build the Map
m = folium.Map(location=[20.8, -156.6], zoom_start=7)

# Layer 1: SST (Temp) - Red/Blue
if sst_data is not None:
    sst_img = make_image_overlay(sst_data, vmin=24, vmax=28, cmap_name='jet')
    folium.raster_layers.ImageOverlay(
        image=sst_img,
        bounds=[[lat_min, lon_min], [lat_max, lon_max]],
        opacity=0.6,
        name="Sea Temp (SST)"
    ).add_to(m)

# Layer 2: Chlorophyll (Bait) - Green
if chl_data is not None:
    chl_img = make_image_overlay(chl_data, vmin=0.05, vmax=0.3, cmap_name='viridis')
    folium.raster_layers.ImageOverlay(
        image=chl_img,
        bounds=[[lat_min, lon_min], [lat_max, lon_max]],
        opacity=0.5,
        name="Chlorophyll (Bait)",
        show=False # Hidden by default, toggle it on in menu
    ).add_to(m)

# Layer 3: Boats
for boat in live_boats:
    folium.Marker(
        [boat['lat'], boat['lon']],
        popup=f"{boat['name']} (LIVE)",
        icon=folium.Icon(color="red", icon="ship", prefix="fa")
    ).add_to(m)

# Add Menu
folium.LayerControl().add_to(m)

# Show Map
st_folium(m, width=900, height=600)
