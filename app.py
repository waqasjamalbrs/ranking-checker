import streamlit as st
import requests
import pandas as pd
import json
import os
import time
import io

# --- Page Config ---
st.set_page_config(page_title="Ultimate Rank Tracker", page_icon="📈", layout="wide")

st.title("📈 Google Rank Checker")
st.markdown("Universal Location Lock, National vs Local Switch & State Translation Active.")
st.markdown("**Note:** Getting Top 100 results uses pagination (up to 10 API calls per keyword) due to Google's deprecation of `num=100`.")

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

# --- SMART LOCATION MATCHER ---
def find_precise_location(city, state, all_locs, country_name):
    city = str(city).strip() if city and str(city).lower() != "none" else ""
    state_input = str(state).strip().lower() if state and str(state).lower() != "none" else ""
    
    if not city and not state_input:
        return None
    
    if state_input in US_STATES:
        full_state_name = US_STATES[state_input].title()
    else:
        full_state_name = str(state).strip().title() if state else ""
        
    if city:
        candidates = [loc for loc in all_locs if loc.lower().startswith(city.lower())]
        
        if full_state_name:
            filtered = [c for c in candidates if full_state_name.lower() in c.lower()]
            if filtered:
                return filtered[0]
                
        if candidates:
            return candidates[0]
            
        if full_state_name:
            return f"{city}, {full_state_name}, {country_name}"
            
        return f"{city}, {country_name}"
    else:
        return f"{full_state_name}, {country_name}"

# --- CORE API ENGINE WITH PAGINATION ---
def check_ranking(keyword, location, website_url, api_key, gl_code, check_depth, is_local_mode):
    gl_code = str(gl_code).strip().lower()
    
    organic_rank = "Not in Top 100" if "100" in check_depth else "Not in Top 10"
    maps_rank = "Not in Map Pack" if is_local_mode else "N/A (National)"
    found_url = "-"
    
    clean_target = website_url.replace("https://", "").replace("http://", "").replace("www.", "").split('/')[0].lower()
    
    max_pages = 10 if "100" in check_depth else 1
    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
    
    current_global_position = 0

    for page_num in range(1, max_pages + 1):
        payload_dict = {
            "q": keyword, 
            "gl": gl_code, 
            "hl": "en",
            "page": page_num
        }
        if location:
            payload_dict["location"] = location
        
        try:
            response = requests.post("https://google.serper.dev/search", headers=headers, json=payload_dict)
            if response.status_code == 200:
                data = response.json()
                
                # 1. MAPS/PLACES SCAN (Sirf Local mode mein page 1 par)
                if is_local_mode and page_num == 1 and 'places' in data and maps_rank == "Not in Map Pack":
                    for i, place in enumerate(data['places']):
                        place_url = place.get('website', place.get('link', '')).lower()
                        if clean_target in place_url:
                            maps_rank = f"#{i + 1} (Maps)"
                            if found_url == "-":
                                found_url = place.get('website', '')
                            break
                            
                # 2. ORGANIC LINKS SCAN
                if 'organic' in data:
                    for item in data['organic']:
                        current_global_position += 1
                        
                        if clean_target in item.get('link', '').lower():
                            organic_rank = current_global_position
                            
                            if found_url == "-":
                                found_url = item.get('link', '')
                                
                            return organic_rank, maps_rank, found_url
                            
                    if len(data['organic']) < 5: 
                        break
                else:
                    break
            else:
                if page_num == 1:
                    return f"API Error {response.status_code}", "Error", "-"
                else:
                    break
                    
        except Exception as e:
            if page_num == 1:
                return "Error", str(e), "-"
            else:
                break
                
    return organic_rank, maps_rank, found_url

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Serper API Key", type="password")
    website_url = st.text_input("🌐 Website URL", placeholder="aurastyled.com")
    
    st.divider()
    st.subheader("🎯 Tracking Scope")
    
    # Switch / Dropdown for National vs Local
    tracking_scope = st.radio(
        "Rank Target Type:",
        ["🌐 National / Country-Level (Only Keywords)", "📍 Local / City-Level (Keywords + City + State)"],
        index=0
    )
    is_local_mode = "Local" in tracking_scope
    
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
        ["Top 10 (1 API Credit)", "Top 100 Organic (Up to 10 API Credits)"]
    )
    
    st.divider()
    mode = st.radio("Select Input Mode:", ["📝 Manual Entry (UI Table)", "📂 Bulk Upload (Excel)"])

# --- SAFE DATAFRAME PROCESSOR ---
def process_clean_dataframe(df_input, is_local):
    results = []
    progress = st.progress(0)
    status = st.empty()
    
    df_input = df_input.fillna("")
    total = len(df_input)
    
    for i in range(total):
        row = df_input.iloc[i]
        kw = str(row.get('Keyword', '')).strip()
        
        if not kw or kw.lower() == "none":
            continue
            
        matched_location = None
        target_display = f"National ({clean_country_name})"
        city = ""
        state = ""
        
        if is_local:
            city = str(row.get('City', '')).strip()
            state = str(row.get('State', '')).strip() if 'State' in df_input.columns else ""
            matched_location = find_precise_location(city, state, all_locations, clean_country_name)
            
            note = ""
            if matched_location:
                target_display = matched_location
                if state.strip():
                    state_val = US_STATES.get(state.lower().strip(), state.title().strip())
                    expected_fallback = f"{city}, {state_val.title()}, {clean_country_name}"
                else:
                    expected_fallback = f"{city}, {clean_country_name}"
                    
                if matched_location == expected_fallback:
                    note = " (⚠️ Auto-Format)"
                target_display += note
            else:
                target_display = f"National ({clean_country_name})"
        
        log_txt = f"{kw} ({city})" if (is_local and city) else kw
        status.text(f"Processing {i+1}/{total}: '{log_txt}'...")
        
        org_rank, map_rank, url = check_ranking(
            kw, matched_location, website_url, api_key, current_gl, check_depth, is_local
        )
        
        row_dict = {
            "Keyword": kw,
            "Targeted Country": clean_country_name,
        }
        if is_local:
            row_dict["City"] = city if city and city.lower() != "none" else "-"
            row_dict["State"] = state if state and state.lower() != "none" else "-"
            
        row_dict["Targeted Location"] = target_display
        row_dict["Organic Rank"] = org_rank
        
        if is_local:
            row_dict["Maps Rank"] = map_rank
            
        row_dict["Found URL"] = url
        results.append(row_dict)
        
        progress.progress((i + 1) / total)
        time.sleep(0.1)
        
    status.success("✅ Process Completed Successfully!")
    return pd.DataFrame(results)

# ==========================================
# MODE 1: MANUAL ENTRY (UI TABLE)
# ==========================================
if mode == "📝 Manual Entry (UI Table)":
    st.subheader(f"📝 Manual Entry — {'📍 Local Mode (City + State)' if is_local_mode else '🌐 National Mode (Keywords Only)'}")
    
    # Local aur National ke mutabiq table ka default data adjust hoga
    if is_local_mode:
        if 'manual_df_local' not in st.session_state:
            st.session_state.manual_df_local = pd.DataFrame([
                {"Keyword": "water damage restoration", "City": "Cape Coral", "State": "FL"},
                {"Keyword": "kitchen remodeling", "City": "Venice", "State": "FL"}
            ])
        current_table = st.session_state.manual_df_local
    else:
        if 'manual_df_national' not in st.session_state:
            st.session_state.manual_df_national = pd.DataFrame([
                {"Keyword": "best bangs for thick hair"},
                {"Keyword": "heavy curtain bangs"},
                {"Keyword": "thick curtain bangs"},
                {"Keyword": "ponytail with thin hair"}
            ])
        current_table = st.session_state.manual_df_national

    edited_df = st.data_editor(current_table, num_rows="dynamic", use_container_width=True)
    
    if st.button("🚀 Check Rankings"):
        if not api_key or not website_url:
            st.error("❌ Please enter API Key and Website URL in sidebar.")
        else:
            cleaned_df = edited_df.dropna(subset=['Keyword'])
            cleaned_df = cleaned_df[cleaned_df['Keyword'].astype(str).str.strip() != ""]
            
            if cleaned_df.empty:
                st.warning("⚠️ Table is empty. Please enter keywords.")
            else:
                df_results = process_clean_dataframe(cleaned_df, is_local_mode)
                st.dataframe(df_results, use_container_width=True)
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_results.to_excel(writer, index=False)
                st.download_button("📥 Download Report", buffer.getvalue(), "Rankings_Report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ==========================================
# MODE 2: BULK UPLOAD (EXCEL)
# ==========================================
elif mode == "📂 Bulk Upload (Excel)":
    st.subheader(f"📂 Bulk Upload — {'📍 Local Mode' if is_local_mode else '🌐 National Mode'}")
    
    if not is_local_mode:
        st.info("ℹ️ National Mode: Excel file mein sirf **Keyword** ka column hona zaroori hai. City ya State ki zaroorat nahi hai.")
    else:
        st.info("ℹ️ Local Mode: Excel file mein **Keyword**, **City**, aur **State** (optional) columns honge.")
        
    uploaded_file = st.file_uploader("Upload Excel (.xlsx)", type=['xlsx'])
    
    if uploaded_file and website_url and api_key:
        df_upload = pd.read_excel(uploaded_file)
        df_upload.columns = [str(c).strip().title() for c in df_upload.columns]
        
        if 'Keyword' not in df_upload.columns:
            st.error("❌ Excel file must contain a 'Keyword' column.")
        else:
            if st.button("🚀 Start Bulk Checking"):
                df_results = process_clean_dataframe(df_upload, is_local_mode)
                st.dataframe(df_results, use_container_width=True)
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_results.to_excel(writer, index=False)
                st.download_button("📥 Download Final Report", buffer.getvalue(), "Bulk_Rankings.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
