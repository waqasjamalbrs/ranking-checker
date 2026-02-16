import streamlit as st
import requests
import pandas as pd
import json
import os
import time
import io

# --- Page Config ---
st.set_page_config(page_title="Serper Rank Tracker", page_icon="📈", layout="wide")

st.title("📈 Google Rank Checker (Keyword, City, State)")
st.markdown("Use the **Bulk Upload** feature for maximum accuracy.")

# --- Helper Function: Load Locations ---
@st.cache_data
def get_locations():
    if os.path.exists('locations.json'):
        with open('locations.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return []

all_locations = get_locations()

# --- REFINED MATCHING LOGIC (City + State) ---
def find_precise_location(city, state, all_locs):
    city = str(city).strip()
    
    # Step 1: Filter by City Name
    # E.g., "Sarasota" matches "Sarasota, Florida, US"
    candidates = [loc for loc in all_locs if loc.lower().startswith(city.lower())]
    
    # Step 2: If State is provided, filter by State
    if state and pd.notna(state) and str(state).strip() != "":
        state_str = str(state).strip().lower()
        
        # Check if state string exists in the location
        # Handles "FL" vs "Florida" by checking if "fl" is inside the full string
        filtered_candidates = [c for c in candidates if state_str in c.lower()]
        
        if filtered_candidates:
            return filtered_candidates[0]
        
        # Agar exact state match na mile, to pehla city match return karo
        if candidates:
            return candidates[0]
            
    # Step 3: If no State provided, return best City match
    if candidates:
        return candidates[0]
        
    return None

# --- API Logic ---
def check_ranking(keyword, location, website_url, api_key):
    payload = json.dumps({
        "q": keyword,
        "location": location,
        "gl": "us",
        "hl": "en",
        "num": 100
    })
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post("https://google.serper.dev/search", headers=headers, data=payload)
        if response.status_code == 200:
            data = response.json()
            rank = "Not in Top 100"
            found_url = "-"
            
            if 'organic' in data:
                for item in data['organic']:
                    # Domain Matching Logic
                    clean_target = website_url.replace("https://", "").replace("http://", "").replace("www.", "").split('/')[0]
                    if clean_target.lower() in item['link'].lower():
                        rank = item['position']
                        found_url = item['link']
                        break
            return rank, found_url
        else:
            return f"Error {response.status_code}", "-"
    except Exception as e:
        return "Error", str(e)

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Serper API Key", type="password")
    st.divider()
    mode = st.radio("Select Mode:", ["Bulk Upload (Keyword, City, State)", "Single City Check"])

# ==========================================
# MODE 1: BULK UPLOAD (Keyword, City, State)
# ==========================================
if mode == "Bulk Upload (Keyword, City, State)":
    st.subheader("📂 Bulk Check (Excel Upload)")
    
    st.info("""
    **Excel File Columns must be exactly:**
    1. **Keyword** (e.g., water damage)
    2. **City** (e.g., Sarasota)
    3. **State** (e.g., FL or Florida)
    """)
    
    website_url = st.text_input("Website URL", placeholder="example.com")
    uploaded_file = st.file_uploader("Upload Excel File (.xlsx)", type=['xlsx'])
    
    if uploaded_file and website_url and api_key:
        df_upload = pd.read_excel(uploaded_file)
        
        # Rename columns to standardized format if they differ slightly
        # This helps if user writes "Keywords" instead of "Keyword"
        df_upload.columns = [c.strip().title() for c in df_upload.columns]
        
        required_cols = ['Keyword', 'City', 'State']
        
        # Validation
        if not all(col in df_upload.columns for col in required_cols):
            st.error(f"❌ Error: Excel columns must be named: {required_cols}")
            st.write("Current columns found:", df_upload.columns.tolist())
        else:
            st.write(f"Loaded {len(df_upload)} rows.")
            
            if st.button("🚀 Start Bulk Processing"):
                results = []
                progress = st.progress(0)
                status = st.empty()
                total = len(df_upload)
                
                for index, row in df_upload.iterrows():
                    kw = row['Keyword']
                    city = row['City']
                    state = row['State']
                    
                    # Logic to find exact location string
                    matched_location = find_precise_location(city, state, all_locations)
                    
                    if not matched_location:
                        matched_location = f"{city}, {state}" # Fallback
                        note = " (⚠️ Not in Database)"
                    else:
                        note = ""
                    
                    status.text(f"Processing {index+1}/{total}: '{kw}' in {city}...")
                    
                    # API Call
                    rank, url = check_ranking(kw, matched_location, website_url, api_key)
                    
                    results.append({
                        "Keyword": kw,
                        "Input City": city,
                        "Input State": state,
                        "Used Location": matched_location + note,
                        "Rank": rank,
                        "Found URL": url
                    })
                    
                    progress.progress((index + 1) / total)
                    time.sleep(0.1) # Small delay for safety
                
                status.success("✅ Analysis Complete!")
                df_results = pd.DataFrame(results)
                st.dataframe(df_results, use_container_width=True)
                
                # Excel Download
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_results.to_excel(writer, index=False)
                st.download_button("📥 Download Final Report", buffer.getvalue(), "Rankings_Report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ==========================================
# MODE 2: SINGLE CITY CHECK
# ==========================================
elif mode == "Single City Check":
    st.subheader("📍 Quick Single Check")
    col1, col2 = st.columns([1, 2])
    with col1:
        target_location = st.selectbox("Select Location", all_locations if all_locations else ["New York, NY, United States"])
        website_url = st.text_input("Website URL", placeholder="example.com")
    with col2:
        keywords_text = st.text_area("Keywords (1 per line)", height=150)

    if st.button("🚀 Check Rankings"):
        if not api_key or not website_url:
            st.error("Missing fields")
        else:
            keywords_list = [k.strip() for k in keywords_text.split('\n') if k.strip()]
            results = []
            progress = st.progress(0)
            
            for i, kw in enumerate(keywords_list):
                rank, url = check_ranking(kw, target_location, website_url, api_key)
                results.append({"Keyword": kw, "Location": target_location, "Rank": rank, "Found URL": url})
                progress.progress((i + 1) / len(keywords_list))
            
            df = pd.DataFrame(results)
            st.dataframe(df)
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            st.download_button("📥 Download Report", buffer.getvalue(), "Single_Report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
