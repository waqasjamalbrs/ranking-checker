import streamlit as st
import requests
import pandas as pd
import json
import os
import time

# --- Page Config ---
st.set_page_config(page_title="Serper Rank Tracker", page_icon="📈", layout="wide")

st.title("📈 Bulk Keyword Rank Checker")
st.markdown("Check your website rankings accurately using **Serper.dev API** with specific city targeting.")

# --- Helper Function: Load Locations ---
@st.cache_data
def get_locations():
    # JSON file load karne ki koshish
    if os.path.exists('locations.json'):
        with open('locations.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # Fallback agar user ne convert script run nahi ki
        st.warning("⚠️ 'locations.json' file nahi mili. Auto-complete cities limited hain. Please 'convert_locations.py' run karen.")
        return [
            "New York, NY, United States", 
            "London, United Kingdom", 
            "Dubai, United Arab Emirates",
            "Karachi, Pakistan"
        ]

# Load locations into memory
all_locations = get_locations()

# --- Sidebar: Settings ---
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # API Key
    api_key = st.text_input("Serper API Key", type="password", help="Get key from serper.dev")
    
    # City Selection (Auto-Fetch Logic)
    # Selectbox acts as a search bar for the list
    target_location = st.selectbox(
        "📍 Select City (Type to search)",
        options=all_locations,
        index=0,
        placeholder="e.g. Sarasota...",
        help="Type city name, and it will auto-suggest from the database."
    )
    
    st.info(f"Targeting: **{target_location}**")

# --- Main Inputs ---
col1, col2 = st.columns([1, 2])

with col1:
    website_url = st.text_input("🌐 Website URL", placeholder="example.com")
    st.caption("Example: qualityrestorationservicesinc.com")

with col2:
    keywords_text = st.text_area("🔑 Keywords (1 per line)", height=150, placeholder="water damage restoration\nmold remediation\nkitchen remodeling")

# --- Logic: Check Rankings ---
if st.button("🚀 Check Rankings"):
    # Validation
    if not api_key:
        st.error("❌ Please enter Serper API Key.")
    elif not website_url:
        st.error("❌ Please enter Website URL.")
    elif not keywords_text.strip():
        st.error("❌ Please enter at least one keyword.")
    else:
        # Prepare Data
        keywords_list = [k.strip() for k in keywords_text.split('\n') if k.strip()]
        total_keywords = len(keywords_list)
        results = []
        
        # UI Elements for Progress
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        st.write("---")
        
        # Loop through keywords
        for i, keyword in enumerate(keywords_list):
            status_text.text(f"⏳ Checking {i+1}/{total_keywords}: '{keyword}' in {target_location}...")
            
            # API Payload
            payload = json.dumps({
                "q": keyword,
                "location": target_location,
                "gl": "us", # Standard Google Locale
                "hl": "en", # Language
                "num": 100  # Check top 100 results
            })
            
            headers = {
                'X-API-KEY': api_key,
                'Content-Type': 'application/json'
            }
            
            rank = "Not in Top 100"
            found_url = "-"
            
            try:
                response = requests.post("https://google.serper.dev/search", headers=headers, data=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Search for domain in organic results
                    if 'organic' in data:
                        for item in data['organic']:
                            # Case insensitive check
                            if website_url.lower().replace("https://", "").replace("http://", "").replace("www.", "").split('/')[0] in item['link'].lower():
                                rank = item['position']
                                found_url = item['link']
                                break
                else:
                    rank = f"API Error: {response.status_code}"

            except Exception as e:
                rank = "Error"
                found_url = str(e)
            
            # Save Result
            results.append({
                "Keyword": keyword,
                "Location": target_location,
                "Rank": rank,
                "Found URL": found_url
            })
            
            # Update Progress
            progress_bar.progress((i + 1) / total_keywords)
            time.sleep(0.1) # Thora pause taake API limit hit na ho

        status_text.success("✅ Analysis Complete!")
        
        # --- Display Results ---
        df = pd.DataFrame(results)
        
        # Color formatting function for Rank column
        def highlight_rank(val):
            color = ''
            if isinstance(val, int):
                if val <= 3: color = 'background-color: #d4edda; color: green' # Top 3
                elif val <= 10: color = 'background-color: #fff3cd; color: orange' # Top 10
            elif val == "Not in Top 100": color = 'color: red'
            return color

        # Show Table
        st.dataframe(df.style.applymap(highlight_rank, subset=['Rank']), use_container_width=True)
        
        # --- CSV Download ---
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Report (Excel/CSV)",
            data=csv_data,
            file_name=f"Rankings_{target_location.split(',')[0]}_{website_url}.csv",
            mime="text/csv"
        )
