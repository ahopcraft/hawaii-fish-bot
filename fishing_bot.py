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
st.title("🐟 Da Fish Spy: LIVE Real-Time Edition")

# !!! YOUR KEY IS IN HERE NOW !!!
AIS_API_KEY = "a3f776e1f103c6deac3a456373a64b7b1feadcc0"

# Hawaii Box
lat_min, lat_max = 18.0, 23.0 
lon_min, lon_max = -161.0, -154.0

# --- 2. SATELLITE DATA FUNCTIONS ---
sst_url = 'https://coastwatch.noaa.gov/erddap/griddap/noaacrwsstDaily'

@st.cache_data
def load_sst_data():
    try:
        ds = xr.open_dataset(sst_url)
        # Smart slice logic (checks if satellite reads North-to-South)
        if ds.latitude[0] > ds.latitude[-1]:
            lat_slice = slice(lat_max, lat_min)
        else:
            lat_slice = slice(lat_min, lat_max)
            
        sst = ds['analysed_sst'].sel(
            time=ds['time'].values[-1],
            latitude=lat_slice,
            longitude=slice(lon_min, lon_max)
        ).squeeze()
        return sst
    except Exception as e:
        return None

def make_image_overlay(data):
    if data is None: return None
    # Normalize temp for Hawaii waters (24C to 28C)
    norm = mcolors.Normalize(vmin=24, vmax=28)
    cmap = cm.get_cmap('jet')
    colored_data = cmap(norm(data.values)) 
    # Make clouds/empty pixels transparent
    mask = np.isnan(data.values)
    colored_data[mask, 3] = 0  
    return colored_data

# --- 3. LIVE BOAT FETCHING (Async Logic) ---
async def fetch_live_boats():
    """
    Connects to AISStream.io and listens for 3 seconds to catch boats in Hawaii.
    """
    boats = []
    
    # Bounding Box for Hawaii
    bbox = [[
        [lat_min, lon_min], 
        [lat_max, lon_max]
    ]]
    
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
            
            # Listen for 3 seconds only (Quick Snapshot)
            start_time = datetime.now()
            status_container = st.empty()
            status_container.write("📡 Tuning into radio frequencies...")
            
            while (datetime.now() - start_time).seconds < 3:
                try:
                    # Wait 1 second for a message
                    message_json = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    message = json.loads(message_json)
                    
                    if "PositionReport" in message["Message"]:
                        report = message["Message"]["PositionReport"]
                        lat = report["Latitude"]
                        lon = report["Longitude"]
                        name = message["MetaData"]["ShipName"]
                        
                        # Double check it's in our box
                        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                            # Avoid duplicates
                            if not any(b['name'] == name.strip() for b in boats):
                                boats.append({"name": name.strip(), "lat": lat, "lon": lon})
                            
                except asyncio.TimeoutError:
                    pass # Keep listening
                except Exception:
                    break
            
            status_container.empty()
                    
    except Exception as e:
        st.error(f"Could not connect to live AIS: {e}")
        
    return boats

# --- 4. MAIN APP ---
st.write("Current Fishing Intel:")

# Load Static Data (Map)
sst_data = load_sst_data()

# Load Live Data (Boats)
# Using a button prevents the app from freezing up or spamming the server
if st.button("🔄 SCAN FOR LIVE BOATS"):
    live_boats = asyncio.run(fetch_live_boats())
    if live_boats:
        st.success(f"Cheehuu! Caught {len(live_boats)} live signals!")
    else:
        st.warning("No signals caught in the last 3 seconds. Radio is quiet. Try again.")
else:
    live_boats = []
    st.info("Click the button to open the radio stream.")

# --- BUILD MAP ---
# Start centered near Maui
m = folium.Map(location=[20.8, -156.6], zoom_start=7)

# Add SST Layer
if sst_data is not None:
    sst_img = make_image_overlay(sst_data)
    # Handle the image bounds carefully
    folium.raster_layers.ImageOverlay(
        image=sst_img,
        bounds=[[lat_min, lon_min], [lat_max, lon_max]],
        opacity=0.6,
        name="Sea Temp"
    ).add_to(m)

# Add Live Boats
for boat in live_boats:
    folium.Marker(
        [boat['lat'], boat['lon']],
        popup=f"🚢 {boat['name']} (LIVE)",
        icon=folium.Icon(color="red", icon="ship", prefix="fa")
    ).add_to(m)

folium.LayerControl().add_to(m)
st_folium(m, width=800, height=600)
