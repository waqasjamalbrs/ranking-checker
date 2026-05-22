import streamlit as st
import requests
import pandas as pd
import json
import os
import time
import io

# --- Page Config ---
st.set_page_config(page_title="Serper Rank Tracker", page_icon="📈", layout="wide")

st.title("📈 Advanced Google Rank Checker (Global)")
st.markdown("Check **Google Maps** and **Organic** rankings for ANY country accurately.")

# --- Helper Function: Load Locations ---
@st.cache_data
def get_locations():
    if os.path.exists('locations.json'):
        with open('locations.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return []

all_locations = get_locations()

# --- Helper Function: Generate Sample Excel ---
def generate_sample_excel():
    df_sample = pd.DataFrame({
        "Keyword": ["water damage restoration", "commercial property management", "kitchen remodeling"],
        "City": ["Sarasota", "Everett", "London"],
        "State": ["FL", "WA", ""]
    })
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_sample.to_excel(writer, index=False)
    return buffer.getvalue()

# --- REFINED MATCHING LOGIC ---
def find_precise_location(city, state, all_locs):
    city = str(city).strip()
    candidates = [loc for loc in all_locs if loc.lower().startswith(city.lower())]
    
    if state and pd.notna(state) and str(state).strip() != "":
        state_str = str(state).strip().lower()
        filtered_candidates = [c for c in candidates if state_str in c.lower()]
        if filtered_candidates:
            return filtered_candidates[0]
            
    if candidates:
        return candidates[0]
    return None

# --- API Logic (With Dynamic GL/Country Code) ---
def check_ranking(keyword, location, website_url, api_key, gl_code):
    payload = json.dumps({
        "q": keyword, 
        "location": location, 
        "gl": gl_code,  # YAHAN DYNAMIC COUNTRY AYEGA AB
        "hl": "en", 
        "num": 100
    })
    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
    
    try:
        response = requests.post("https://google.serper.dev/search", headers=headers, data=payload)
        if response.status_code == 200:
            data = response.json()
            
            organic_rank = "Not in Top 100"
            maps_rank = "Not in Map Pack"
            found_url = "-"
            
            clean_target = website_url.replace("https://", "").replace("http://", "").replace("www.", "").split('/')[0].lower()
            
            # 1. CHECK LOCAL PACK (Google Maps)
            if 'places' in data:
                for i, place in enumerate(data['places']):
                    place_url = place.get('website', place.get('link', '')).lower()
                    if clean_target in place_url:
                        maps_rank = i + 1
                        found_url = place.get('website', '')
                        break
                        
            # 2. CHECK ORGANIC RESULTS
            if 'organic' in data:
                for item in data['organic']:
                    if clean_target in item.get('link', '').lower():
                        organic_rank = item['position']
                        if found_url == "-":
                            found_url = item.get('link', '')
                        break
                        
            return organic_rank, maps_rank, found_url
        else:
            return f"Error {response.status_code}", "Error", "-"
    except Exception as e:
        return "Error", str(e), "-"

# --- Main App Logic & Processing Function ---
def process_data(df_input, website_url, api_key, gl_code):
    results = []
    progress = st.progress(0)
    status = st.empty()
    
    df_input = df_input.fillna("")
    total = len(df_input)
    
    for index, row in df_input.iterrows():
        kw = str(row['Keyword']).strip()
        city = str(row['City']).strip()
        state = str(row['State']).strip() if 'State' in row else ""
        
        matched_location = find_precise_location(city, state, all_locations)
        if not matched_location:
            matched_location = f"{city}, {state}".strip(", ")
            note = " (⚠️ Not in DB)"
        else:
            note = ""
        
        status.text(f"Processing {index+1}/{total}: '{kw}' in {matched_location}...")
        
        # Pass GL code to API
        org_rank, map_rank, url = check_ranking(kw, matched_location, website_url, api_key, gl_code)
        
        results.append({
            "Keyword": kw,
            "City": city,
            "Targeted Location": matched_location + note,
            "Organic Rank": org_rank,
            "Maps Rank": map_rank,
            "Found URL": url
        })
        
        progress.progress((index + 1) / total)
        time.sleep(0.1)
    
    status.success("✅ Analysis Complete!")
    return pd.DataFrame(results)

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Serper API Key", type="password")
    website_url = st.text_input("🌐 Website URL", placeholder="example.com")
    
    # NAYA OPTION: Country Selection
    st.divider()
    st.subheader("🌍 Google Region")
    gl_options = {
        "United States (US)": "us",
        "United Kingdom (UK)": "uk",
        "Canada (CA)": "ca",
        "Australia (AU)": "au",
        "United Arab Emirates (AE)": "ae",
        "Pakistan (PK)": "pk",
        "India (IN)": "in"
    }
    selected_country = st.selectbox("Search Country Database:", options=list(gl_options.keys()))
    current_gl = gl_options[selected_country]
    
    st.divider()
    mode = st.radio("Select Mode:", ["📂 Bulk Upload (Excel)", "📝 Manual Entry (UI Table)"])

# ==========================================
# MODE 1: BULK UPLOAD (EXCEL)
# ==========================================
if mode == "📂 Bulk Upload (Excel)":
    st.subheader("📂 Bulk Check via Excel Upload")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.info(f"**Current Search Engine:** Google {current_gl.upper()}")
    with col2:
        st.download_button("⬇️ Download Sample Excel", data=generate_sample_excel(), file_name="Template_RankChecker.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
    uploaded_file = st.file_uploader("Upload Your Filled Excel File (.xlsx)", type=['xlsx'])
    
    if uploaded_file and website_url and api_key:
        df_upload = pd.read_excel(uploaded_file)
        df_upload.columns = [str(c).strip().title() for c in df_upload.columns]
        
        if not all(col in df_upload.columns for col in ['Keyword', 'City', 'State']):
            st.error("❌ Error: Columns must be named: Keyword, City, State")
        else:
            if st.button("🚀 Start Bulk Checking"):
                df_results = process_data(df_upload, website_url, api_key, current_gl)
                st.dataframe(df_results, use_container_width=True)
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_results.to_excel(writer, index=False)
                st.download_button("📥 Download Final Report", buffer.getvalue(), "Rankings_Report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ==========================================
# MODE 2: MANUAL ENTRY (UI TABLE)
# ==========================================
elif mode == "📝 Manual Entry (UI Table)":
    st.subheader("📝 Direct Manual Entry")
    st.info(f"**Current Search Engine:** Google {current_gl.upper()}")
    
    default_data = pd.DataFrame([
        {"Keyword": "water damage restoration", "City": "Cape Coral", "State": "FL"},
        {"Keyword": "", "City": "", "State": ""}
    ])
    
    edited_df = st.data_editor(default_data, num_rows="dynamic", use_container_width=True)
    
    if st.button("🚀 Check Rankings (Manual Data)"):
        if not api_key or not website_url:
            st.error("❌ Please enter Serper API Key and Website URL in the sidebar.")
        else:
            edited_df = edited_df.fillna("")
            valid_df = edited_df[edited_df['Keyword'].str.strip() != ""]
            
            if valid_df.empty:
                st.warning("⚠️ Please enter at least one Keyword and City.")
            else:
                df_results = process_data(valid_df, website_url, api_key, current_gl)
                st.dataframe(df_results, use_container_width=True)
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_results.to_excel(writer, index=False)
                st.download_button("📥 Download Final Report", buffer.getvalue(), "Manual_Rankings_Report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
