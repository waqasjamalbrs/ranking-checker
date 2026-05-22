import streamlit as st
import requests
import pandas as pd
import json
import os
import time
import io

# --- Page Config ---
st.set_page_config(page_title="Ultimate Rank Tracker", page_icon="📈", layout="wide")

st.title("📈 Google Rank Checker (Bulletproof Local & Organic)")
st.markdown("Universal Location Lock, Index-Mismatch Fixed & State Translation Active.")

# --- Comprehensive US States Dictionary for Exact Canonical Match ---
US_STATES = {
    "al": "alabama", "ak": "alaska", "az": "arizona", "ar": "arkansas", "ca": "california",
    "co": "colorado", "ct": "connecticut", "de": "delaware", "fl": "florida", "ga": "georgia",
    "hi": "hawaii", "id": "idaho", "il": "illinois", "in": "indiana", "ia": "iowa",
    "ks": "kansas", "ky": "kentucky", "la": "louisiana", "me": "maine", "md": "maryland",
    "ma": "massachusetts", "mi": "michigan", "mn": "minnesota", "ms": "mississippi",
    "mo": "missouri", "mt": "montana", "ne": "nebraska", "nv": "nevada", "nh": "new hampshire",
    "nj": "new jersey", "nm": "new mexico", "ny": "new york", "nc": "north carolina",
    "nd": "north dakota", "oh": "ohio", "ok": "oklahoma", "or": "oregon", "pa": "pennsylvania",
    "ri": "rhode island", "sc": "south carolina", "sd": "south dakota", "tn": "tennessee",
    "tx": "texas", "ut": "utah", "vt": "vermont", "va": "virginia", "wa": "washington",
    "wv": "west virginia", "wi": "wisconsin", "wy": "wyoming"
}

# --- Helper Function: Load Locations ---
@st.cache_data
def get_locations():
    if os.path.exists('locations.json'):
        with open('locations.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

all_locations = get_locations()

# --- SMART & CLEAN LOCATION MATCHER (State Bug Fixed) ---
def find_precise_location(city, state, all_locs, country_name):
    city = str(city).strip()
    state_input = str(state).strip().lower()
    
    # 1. State abbreviation ko full name mai convert karo (e.g., 'fl' -> 'Florida')
    if state_input in US_STATES:
        full_state_name = US_STATES[state_input].title()
    else:
        full_state_name = str(state).strip().title()
        
    candidates = [loc for loc in all_locs if loc.lower().startswith(city.lower())]
    
    # 2. Match with full state name
    if full_state_name:
        filtered = [c for c in candidates if full_state_name.lower() in c.lower()]
        if filtered:
            return filtered[0]
            
    if candidates:
        return candidates[0]
        
    # 3. BULLETPROOF FALLBACK: Google Ads Canonical Format
    if full_state_name:
        return f"{city}, {full_state_name}, {country_name}"
        
    return f"{city}, {country_name}"

# --- CORE API ENGINE ---
def check_ranking(keyword, location, website_url, api_key, gl_code, check_depth):
    gl_code = str(gl_code).strip().lower()
    
    payload_dict = {
        "q": keyword, 
        "location": location, 
        "gl": gl_code, 
        "hl": "en"
    }
    
    if "100" in check_depth:
        payload_dict["num"] = 100
        
    payload = json.dumps(payload_dict)
    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
    
    try:
        response = requests.post("https://google.serper.dev/search", headers=headers, data=payload)
        if response.status_code == 200:
            data = response.json()
            
            organic_rank = "Not in Top 100" if "100" in check_depth else "Not in Top 10"
            maps_rank = "Not in Map Pack"
            found_url = "-"
            
            clean_target = website_url.replace("https://", "").replace("http://", "").replace("www.", "").split('/')[0].lower()
            
            # 1. MAPS/PLACES SCAN
            if 'places' in data:
                for i, place in enumerate(data['places']):
                    place_url = place.get('website', place.get('link', '')).lower()
                    if clean_target in place_url:
                        maps_rank = f"#{i + 1} (Maps)"
                        found_url = place.get('website', '')
                        break
                        
            # 2. ORGANIC LINKS SCAN
            if 'organic' in data:
                for item in data['organic']:
                    if clean_target in item.get('link', '').lower():
                        organic_rank = item['position']
                        if found_url == "-":
                            found_url = item.get('link', '')
                        break
                        
            return organic_rank, maps_rank, found_url
        else:
            return f"API Error {response.status_code}", "Error", "-"
    except Exception as e:
        return "Error", str(e), "-"

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Serper API Key", type="password")
    website_url = st.text_input("🌐 Website URL", placeholder="example.com")
    
    st.divider()
    st.subheader("🌍 Regional Settings")
    gl_options = {
        "United States (US)": "us",
        "United Kingdom (UK)": "uk",
        "Canada (CA)": "ca",
        "Australia (AU)": "au",
        "United Arab Emirates (AE)": "ae",
        "Pakistan (PK)": "pk"
    }
    selected_country_name = st.selectbox("Google Country Engine:", options=list(gl_options.keys()))
    current_gl = gl_options[selected_country_name]
    clean_country_name = selected_country_name.split(" (")[0]
    
    check_depth = st.radio(
        "Search Strategy:", 
        ["Top 10 + Map Pack (Best for Local)", "Top 100 Organic (Hides Map Pack)"]
    )
    
    st.divider()
    mode = st.radio("Select Mode:", ["📝 Manual Entry (UI Table)", "📂 Bulk Upload (Excel)"])

# --- SAFE DATAFRAME PROCESSOR (Guarantees Perfect Row Alignment) ---
def process_clean_dataframe(df_input):
    results = []
    progress = st.progress(0)
    status = st.empty()
    
    df_input = df_input.fillna("")
    total = len(df_input)
    
    for i in range(total):
        row = df_input.iloc[i]
        kw = str(row.get('Keyword', '')).strip()
        city = str(row.get('City', '')).strip()
        state = str(row.get('State', '')) if 'State' in df_input.columns else ""
        
        if not kw or not city:
            continue
            
        matched_location = find_precise_location(city, state, all_locations, clean_country_name)
        
        # Helper logic for visual confirmation of fallback usage
        note = ""
        expected_fallback = ""
        if state.strip():
            state_val = US_STATES.get(state.lower().strip(), state.title().strip())
            expected_fallback = f"{city}, {state_val.title()}, {clean_country_name}"
        else:
            expected_fallback = f"{city}, {clean_country_name}"
            
        if matched_location == expected_fallback:
             note = " (⚠️ Auto-Format)"
        
        status.text(f"Processing {i+1}/{total}: '{kw}' in {city}...")
        
        org_rank, map_rank, url = check_ranking(kw, matched_location, website_url, api_key, current_gl, check_depth)
        
        results.append({
            "Keyword": kw,
            "City": city,
            "State": state,
            "Targeted Location": matched_location + note,
            "Organic Rank": org_rank,
            "Maps Rank": map_rank,
            "Found URL": url
        })
        
        progress.progress((i + 1) / total)
        time.sleep(0.1)
        
    status.success("✅ Process Completed Successfully!")
    return pd.DataFrame(results)

# ==========================================
# MODE 1: MANUAL ENTRY (UI TABLE)
# ==========================================
if mode == "📝 Manual Entry (UI Table)":
    st.subheader("📝 Direct Manual Entry")
    
    if 'manual_df' not in st.session_state:
        st.session_state.manual_df = pd.DataFrame([
            {"Keyword": "water damage restoration", "City": "Cape Coral", "State": "FL"},
            {"Keyword": "kitchen remodeling", "City": "Venice", "State": "FL"},
            {"Keyword": "mold remediation", "City": "Sarasota", "State": "FL"}
        ])
        
    edited_df = st.data_editor(st.session_state.manual_df, num_rows="dynamic", use_container_width=True)
    
    if st.button("🚀 Check Rankings"):
        if not api_key or not website_url:
            st.error("❌ Please enter API Key and Website URL in sidebar.")
        else:
            cleaned_df = edited_df.dropna(subset=['Keyword', 'City'])
            cleaned_df = cleaned_df[cleaned_df['Keyword'].str.strip() != ""]
            
            if cleaned_df.empty:
                st.warning("⚠️ Table is empty. Please enter data.")
            else:
                df_results = process_clean_dataframe(cleaned_df)
                st.dataframe(df_results, use_container_width=True)
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_results.to_excel(writer, index=False)
                st.download_button("📥 Download Report", buffer.getvalue(), "Manual_Rankings.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ==========================================
# MODE 2: BULK UPLOAD (EXCEL)
# ==========================================
elif mode == "📂 Bulk Upload (Excel)":
    st.subheader("📂 Bulk Check via Excel Upload")
    
    uploaded_file = st.file_uploader("Upload Excel (.xlsx)", type=['xlsx'])
    
    if uploaded_file and website_url and api_key:
        df_upload = pd.read_excel(uploaded_file)
        df_upload.columns = [str(c).strip().title() for c in df_upload.columns]
        
        if not all(col in df_upload.columns for col in ['Keyword', 'City']):
            st.error("❌ Excel must have columns: Keyword, City")
        else:
            if st.button("🚀 Start Bulk Checking"):
                df_results = process_clean_dataframe(df_upload)
                st.dataframe(df_results, use_container_width=True)
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_results.to_excel(writer, index=False)
                st.download_button("📥 Download Final Report", buffer.getvalue(), "Bulk_Rankings.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
