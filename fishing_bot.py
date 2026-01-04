import streamlit as st
import xarray as xr
import numpy as np
import pandas as pd
import folium
from streamlit_folium import st_folium
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import random

# --- 1. PAGE SETUP ---
st.set_page_config(layout="wide", page_title="Da Fish Spy: Species Edition") 

# --- SIDEBAR CONTROLS ---
st.sidebar.title("🎣 Tackle Box")
target_fish = st.sidebar.radio(
    "What you chasing today?",
    ("Ahi (Yellowfin)", "Mahi (Dolphinfish)", "Ono (Wahoo)", "Aku (Skipjack)")
)

show_boats = st.sidebar.checkbox("Show Boat Traffic", value=True)
show_bait = st.sidebar.checkbox("Show Chlorophyll Layer", value=False)

# Main Title changes based on selection
st.title(f"🐟 Da Fish Spy: Hunting for {target_fish}")

# Hawaii Box
lat_min, lat_max = 18.0, 23.0 
lon_min, lon_max = -161.0, -154.0
sst_url = 'https://coastwatch.noaa.gov/erddap/griddap/noaacrwsstDaily'
chl_url = 'https://coastwatch.noaa.gov/erddap/griddap/noaacwN20VIIRSchlaDaily'

# --- 2. DATA FUNCTIONS ---
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

def make_image_overlay(data, vmin, vmax, cmap_name):
    if data is None: return None
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    cmap = cm.get_cmap(cmap_name)
    colored_data = cmap(norm(data.values)) 
    mask = np.isnan(data.values)
    colored_data[mask, 3] = 0  
    return colored_data

@st.cache_data
def load_ocean_data():
    try:
        ds_sst = xr.open_dataset(sst_url)
        sst = get_smart_slice(ds_sst, 'analysed_sst', (lat_min, lat_max), (lon_min, lon_max))
        ds_chl = xr.open_dataset(chl_url)
        chl = get_smart_slice(ds_chl, 'chlor_a', (lat_min, lat_max), (lon_min, lon_max))
        chl_interp = chl.interp_like(sst, method='nearest') # Match grids
        latest_date = ds_sst['time'].values[-1]
        return sst, chl_interp, latest_date
    except:
        return None, None, None

# --- 3. THE "FISH BRAIN" (Species Logic) ---
def find_specific_fish(sst, chl, fish_type):
    spots = []
    
    # Define the "Perfect Conditions" for each fish
    if "Ahi" in fish_type:
        # Ahi like warm water and clean bait edges
        temp_min, temp_max = 26.0, 28.5
        bait_min = 0.1
        color = "red"
    elif "Mahi" in fish_type:
        # Mahi like structure and slightly cooler breaks
        temp_min, temp_max = 24.5, 26.5
        bait_min = 0.2
        color = "green"
    elif "Ono" in fish_type:
        # Ono are fast, like transition zones
        temp_min, temp_max = 25.0, 27.0
        bait_min = 0.15
        color = "orange"
    else: # Aku
        # Aku aren't picky, they just want food
        temp_min, temp_max = 24.0, 28.0
        bait_min = 0.25
        color = "blue"

    # The Math
    lats = sst.latitude.values
    lons = sst.longitude.values
    
    # Create the "Jackpot" mask
    good_temp = (sst.values >= temp_min) & (sst.values <= temp_max)
    good_food = (chl.values >= bait_min) & (chl.values < 0.5)
    jackpot = good_temp & good_food
    
    y_idxs, x_idxs = np.where(jackpot)
    
    # Pick top 15 spots so map isn't crowded
    if len(y_idxs) > 0:
        # Shuffle logic to random pick spots in the zone
        indices = np.linspace(0, len(y_idxs)-1, 15, dtype=int)
        for i in indices:
            lat = lats[y_idxs[i]]
            lon = lons[x_idxs[i]]
            spots.append((lat, lon, color))
            
    return spots, color, temp_min, temp_max

# --- 4. GHOST BOATS (Demo Mode) ---
def get_ghost_boats():
    return [
        {"name": "Kolohe Kai", "lat": 20.9, "lon": -156.4},
        {"name": "Da Kine II", "lat": 21.2, "lon": -157.1},
        {"name": "Lawai'a Boy", "lat": 19.8, "lon": -156.1},
        {"name": "Hana Pa'a", "lat": 20.5, "lon": -156.8},
    ]

# --- 5. MAIN APP ---
st.write("Checking satellite feeds...")
sst_data, chl_data, date_val = load_ocean_data()

if sst_data is not None:
    st.success(f"Data Source: NOAA | Date: {pd.to_datetime(date_val).date()}")
    
    # Get the spots for the SELECTED fish
    fish_spots, marker_color, t_min, t_max = find_specific_fish(sst_data, chl_data, target_fish)
    
    # --- DISPLAY KEY / LEGEND ---
    st.markdown(f"""
    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; border: 1px solid #ccc;">
        <strong>📋 Captain's Log ({target_fish}):</strong><br>
        • 🌡️ <strong>Ideal Temp:</strong> {t_min}°C - {t_max}°C<br>
        • 📍 <strong>Markers:</strong> Look for the <b>{marker_color.upper()}</b> pins.<br>
        • 🧠 <strong>Logic:</strong> We found {len(fish_spots)} high-probability zones.
    </div>
    <br>
    """, unsafe_allow_html=True)

    # --- BUILD MAP ---
    m = folium.Map(location=[20.8, -156.6], zoom_start=7)

    # SST Layer
    sst_img = make_image_overlay(sst_data, vmin=24, vmax=28, cmap_name='jet')
    folium.raster_layers.ImageOverlay(
        image=sst_img, bounds=[[lat_min, lon_min], [lat_max, lon_max]],
        opacity=0.6, name="Sea Temp"
    ).add_to(m)

    # Chlorophyll Layer (Controlled by Sidebar)
    if show_bait:
        chl_img = make_image_overlay(chl_data, vmin=0.05, vmax=0.3, cmap_name='viridis')
        folium.raster_layers.ImageOverlay(
            image=chl_img, bounds=[[lat_min, lon_min], [lat_max, lon_max]],
            opacity=0.5, name="Bait (Chl)"
        ).add_to(m)

    # FISH MARKERS
    for f_lat, f_lon, color in fish_spots:
        folium.Marker(
            [f_lat, f_lon],
            popup=f"Probable {target_fish.split()[0]} Zone",
            icon=folium.Icon(color=color, icon="star")
        ).add_to(m)

    # BOATS (Controlled by Sidebar)
    if show_boats:
        boats = get_ghost_boats()
        for boat in boats:
            folium.Marker(
                [boat['lat'], boat['lon']],
                popup=f"{boat['name']}",
                icon=folium.Icon(color="black", icon="ship", prefix="fa")
            ).add_to(m)

    folium.LayerControl().add_to(m)
    st_folium(m, width=900, height=600)

else:
    st.error("Auwe! Satellite data is sleeping. Try again later.")
