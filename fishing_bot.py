import streamlit as st
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import numpy as np
import pandas as pd

# --- CONFIG & STYLE ---
st.set_page_config(page_title="Da Fish Spy 3000: Winter Edition", layout="wide")

st.title("🎣 Da Fish Spy 3000: Winter Season")
st.markdown("### Select your target. Winter time means the Nairagi stay biting!")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("Configuration")
st.sidebar.info("Current Season: **Winter (Hoʻoilo)**")

# THE BIG LIST
target_fish = st.sidebar.radio(
    "What you chasing today?",
    (
        "Ahi (Yellowfin)", 
        "Ono (Wahoo)", 
        "Mahi (Dorado)", 
        "Nairagi (Striped Marlin)", 
        "Hebi (Shortbill Spearfish)", 
        "Aku (Skipjack)", 
        "Bigeye Ahi (Deep Ahi)",
        "Kajiki (Blue Marlin)"
    )
)

# --- FISH LOGIC (The Brains) ---
# Updated Logic for Winter 2026 Seasonality
if target_fish == "Ahi (Yellowfin)":
    temp_min, temp_max = 24.5, 28.0
    chl_min, chl_max = 0.08, 0.35
    desc = "Standard Ahi logic. They like that perfect 76-82°F water. Look for clean edges."

elif target_fish == "Ono (Wahoo)":
    temp_min, temp_max = 25.0, 28.5
    chl_min, chl_max = 0.05, 0.25
    desc = "Ono are speed demons. They hug the ledges. Look for sharp temp breaks!"

elif target_fish == "Mahi (Dorado)":
    temp_min, temp_max = 25.5, 29.5
    chl_min, chl_max = 0.1, 0.5
    desc = "Mahi love the 'rubbish' water. High bait, warm temp. If it's green, check it unseen."

elif target_fish == "Nairagi (Striped Marlin)":
    # Winter Favorite! They like cooler water than Blues.
    temp_min, temp_max = 20.0, 25.0 
    chl_min, chl_max = 0.05, 0.2
    desc = "**WINTER SPECIAL:** Nairagi love the cooler water (68-77°F). This is the best time for them!"

elif target_fish == "Hebi (Shortbill Spearfish)":
    # Another Winter/Spring fish.
    temp_min, temp_max = 21.0, 25.5
    chl_min, chl_max = 0.05, 0.25
    desc = "Hebi are aggressive right now. They like the transition zones, slightly cooler than Ahi."

elif target_fish == "Aku (Skipjack)":
    # The staple. Broad range.
    temp_min, temp_max = 23.0, 28.0
    chl_min, chl_max = 0.15, 0.6
    desc = "Aku are hungry year-round. They like the high-chlorophyll bait balls. Look for the birds!"

elif target_fish == "Bigeye Ahi (Deep Ahi)":
    # They live deep, but we look for surface indicators.
    # They like cooler water than Yellowfin.
    temp_min, temp_max = 22.0, 26.0
    chl_min, chl_max = 0.05, 0.3
    desc = "Bigeye stay deep (cold), but come up at night or low light. We looking for cooler surface patches."

elif target_fish == "Kajiki (Blue Marlin)":
    # Summer is better, but they still around.
    temp_min, temp_max = 26.0, 29.0
    chl_min, chl_max = 0.02, 0.15
    desc = "Big Momma. She likes the warmest, cleanest blue water you can find. Don't go in the green stuff."

# DISPLAY THE SETTINGS
st.info(f"**Targeting: {target_fish}**\n\n{desc}")
col1, col2 = st.columns(2)
col1.metric("Target Temp", f"{temp_min}-{temp_max}°C")
col2.metric("Target Chlorophyll", f"{chl_min}-{chl_max} mg/m³")

# --- THE DATA FETCH ---
@st.cache_data(ttl=3600)
def get_data():
    lat_min, lat_max = 18.5, 22.5
    lon_min, lon_max = -161.0, -155.0
    
    # FETCH SST
    sst_url = 'https://coastwatch.noaa.gov/erddap/griddap/noaacrwsstDaily'
    try:
        ds_sst = xr.open_dataset(sst_url)
        latest_time = ds_sst['time'].values[-1]
        sst = ds_sst['analysed_sst'].sel(
            time=latest_time, latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max)
        )
    except:
        return None, None

    # FETCH CHLOROPHYLL
    chl_url = 'https://coastwatch.noaa.gov/erddap/griddap/noaa_snpp_chla_daily'
    try:
        ds_chl = xr.open_dataset(chl_url)
        latest_chl = ds_chl['time'].values[-1]
        chl = ds_chl['chlor_a'].sel(
            time=latest_chl, latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max)
        )
    except:
        return None, None
        
    return sst, chl

# --- MAP MAKER ---
if st.button("Scout the Ocean (Load Map)"):
    with st.spinner("Wait wunst, checking the satellites..."):
        sst, chl = get_data()
        
        if sst is None or chl is None:
            st.error("Auwe! NOAA server is acting lolo. Try again in 5 minutes.")
        else:
            # Interpolate Chlorophyll to match SST grid
            chl_interp = chl.interp_like(sst, method='linear')
            
            # THE FORMULA
            temp_mask = (sst >= temp_min) & (sst <= temp_max)
            food_mask = (chl_interp >= chl_min) & (chl_interp <= chl_max)
            sweet_spot = sst.where(temp_mask & food_mask)

            # PLOT
            fig = plt.figure(figsize=(14, 10))
            ax = plt.axes(projection=ccrs.PlateCarree())
            ax.add_feature(cfeature.LAND, edgecolor='black', facecolor='lightgray', zorder=100)
            ax.coastlines(resolution='10m')
            ax.gridlines(draw_labels=True, linestyle='--', alpha=0.5)
            
            # 1. Base Layer (SST)
            sst.plot(ax=ax, transform=ccrs.PlateCarree(), cmap='jet', vmin=23, vmax=29, 
                     cbar_kwargs={'label': 'Temp (°C)', 'shrink': 0.7})
            
            # 2. Sweet Spot Layer (White Contours)
            if sweet_spot.count() > 0:
                plt.contour(sst.longitude, sst.latitude, sweet_spot, 
                            colors='white', linewidths=2, transform=ccrs.PlateCarree())
                st.success(f"Shoots! Found prime {target_fish} water! Check the white circles.")
            else:
                st.warning(f"No perfect {target_fish} water found today. Conditions might be too rough or servers sleeping.")

            plt.title(f"Hawaii Fishing Intel: {target_fish} Zones")
            st.pyplot(fig)