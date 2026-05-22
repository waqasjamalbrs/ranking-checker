import streamlit as st
import requests
import pandas as pd
import json
import os
import time
import io

# --- Page Config ---
st.set_page_config(page_title="Serper Rank Tracker", page_icon="📈", layout="wide")

st.title("📈 Advanced Google Rank Checker")
st.markdown("Easily check keyword rankings with **Excel Upload** or **Direct Manual Entry**.")

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
        "Keyword": ["water damage restoration", "kitchen remodeling", "property management"],
        "City": ["Sarasota", "Venice", "Everett"],
        "State": ["FL", "FL", "WA"]
    })
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_sample.to_excel(writer, index=False)
    return buffer.getvalue()

# --- REFINED MATCHING LOGIC (City + State) ---
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
            
    if candidates:
        return candidates[0]
    return None

# --- API Logic ---
def check_ranking(keyword, location, website_url, api_key):
    payload = json.dumps({
        "q": keyword, "location": location, "gl": "us", "hl": "en", "num": 100
    })
    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
    
    try:
        response = requests.post("https://google.serper.dev/search", headers=headers, data=payload)
        if response.status_code == 200:
            data = response.json()
            rank = "Not in Top 100"
            found_url = "-"
            
            if 'organic' in data:
                for item in data['organic']:
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

# --- Main App Logic & Processing Function ---
def process_data(df_input, website_url, api_key):
    results = []
    progress = st.progress(0)
    status = st.empty()
    total = len(df_input)
    
    for index, row in df_input.iterrows():
        kw = str(row['Keyword']).strip()
        city = str(row['City']).strip()
        state = str(row['State']).strip() if 'State' in row else ""
        
        # Auto-City Fill / Match
        matched_location = find_precise_location(city, state, all_locations)
        if not matched_location:
            matched_location = f"{city}, {state}".strip(", ")
            note = " (⚠️ Exact Match Not Found)"
        else:
            note = ""
        
        status.text(f"Processing {index+1}/{total}: '{kw}' in {matched_location}...")
        
        # API Call
        rank, url = check_ranking(kw, matched_location, website_url, api_key)
        
        results.append({
            "Keyword": kw,
            "Input City": city,
            "Input State": state,
            "Auto-Matched Location": matched_location + note,
            "Rank": rank,
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
    st.divider()
    mode = st.radio("Select Mode:", ["📂 Bulk Upload (Excel)", "📝 Manual Entry (UI Table)"])

# ==========================================
# MODE 1: BULK UPLOAD (EXCEL)
# ==========================================
if mode == "📂 Bulk Upload (Excel)":
    st.subheader("📂 Bulk Check via Excel Upload")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.info("**Instructions:** Upload an Excel file with exactly 3 columns: `Keyword`, `City`, `State`.")
    with col2:
        # 1. SAMPLE FILE DOWNLOAD BUTTON
        st.download_button(
            label="⬇️ Download Sample Excel",
            data=generate_sample_excel(),
            file_name="Template_RankChecker.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    uploaded_file = st.file_uploader("Upload Your Filled Excel File (.xlsx)", type=['xlsx'])
    
    if uploaded_file and website_url and api_key:
        df_upload = pd.read_excel(uploaded_file)
        df_upload.columns = [str(c).strip().title() for c in df_upload.columns] # Auto-format headers
        
        if not all(col in df_upload.columns for col in ['Keyword', 'City', 'State']):
            st.error("❌ Error: Excel columns must be named: Keyword, City, State")
        else:
            st.write(f"Loaded {len(df_upload)} keywords ready for check.")
            
            if st.button("🚀 Start Bulk Checking"):
                df_results = process_data(df_upload, website_url, api_key)
                st.dataframe(df_results, use_container_width=True)
                
                # Excel Download
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_results.to_excel(writer, index=False)
                st.download_button("📥 Download Final Report", buffer.getvalue(), "Rankings_Report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ==========================================
# MODE 2: MANUAL ENTRY (UI TABLE)
# ==========================================
elif mode == "📝 Manual Entry (UI Table)":
    st.subheader("📝 Direct Manual Entry")
    st.write("Aap niche table mein direct data type kar sakte hain. Nayi row add karne ke liye table ke neeche click karen.")
    
    # Pre-fill with a blank structure so user knows what to do
    default_data = pd.DataFrame([
        {"Keyword": "water damage restoration", "City": "Cape Coral", "State": "FL"},
        {"Keyword": "", "City": "", "State": ""}
    ])
    
    # 2. STREAMLIT DATA EDITOR (Mini Excel in Web)
    edited_df = st.data_editor(
        default_data, 
        num_rows="dynamic", # Allow user to add/delete rows
        use_container_width=True
    )
    
    if st.button("🚀 Check Rankings (Manual Data)"):
        if not api_key or not website_url:
            st.error("❌ Please enter Serper API Key and Website URL in the sidebar.")
        else:
            # Remove empty rows before processing
            valid_df = edited_df[edited_df['Keyword'].str.strip() != ""]
            
            if valid_df.empty:
                st.warning("⚠️ Please enter at least one Keyword and City.")
            else:
                st.write(f"Processing {len(valid_df)} entries...")
                
                # Use the exact same processing and auto-city logic
                df_results = process_data(valid_df, website_url, api_key)
                
                st.dataframe(df_results, use_container_width=True)
                
                # Excel Download
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_results.to_excel(writer, index=False)
                st.download_button("📥 Download Final Report", buffer.getvalue(), "Manual_Rankings_Report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
