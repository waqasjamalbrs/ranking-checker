import streamlit as st
import requests
import pandas as pd
import json
import os
import time
import io  # Excel file memory mai banane ke liye zaroori hai

# --- Page Config ---
st.set_page_config(page_title="Serper Rank Tracker", page_icon="📈", layout="wide")

st.title("📈 Bulk Google Rank Checker (Excel Output)")
st.markdown("Check your website rankings accurately using **Serper.dev API** with specific city targeting.")

# --- Helper Function: Load Locations ---
@st.cache_data
def get_locations():
    if os.path.exists('locations.json'):
        with open('locations.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        st.warning("⚠️ 'locations.json' file nahi mili. Please ensure you uploaded it to GitHub.")
        return ["New York, NY, United States", "London, United Kingdom"]

all_locations = get_locations()

# --- Sidebar: Settings ---
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Serper API Key", type="password", help="Serper.dev se API key lein")
    
    target_location = st.selectbox(
        "📍 Select Location (City)",
        options=all_locations,
        index=0,
        placeholder="Type city name...",
        help="City ka naam likhen, list auto-filter ho jayegi."
    )
    
    st.success(f"Selected: **{target_location}**")

# --- Main Inputs ---
col1, col2 = st.columns([1, 2])

with col1:
    website_url = st.text_input("🌐 Website URL", placeholder="example.com")
    st.caption("Example: qualityrestorationservicesinc.com")

with col2:
    keywords_text = st.text_area("🔑 Keywords (Har line mai ek keyword)", height=150, placeholder="water damage restoration\nmold remediation\nkitchen remodeling")

# --- Logic: Check Rankings ---
if st.button("🚀 Check Rankings"):
    if not api_key:
        st.error("❌ Please enter Serper API Key.")
    elif not website_url:
        st.error("❌ Please enter Website URL.")
    elif not keywords_text.strip():
        st.error("❌ Please enter at least one keyword.")
    else:
        keywords_list = [k.strip() for k in keywords_text.split('\n') if k.strip()]
        total_keywords = len(keywords_list)
        results = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        st.write("---")
        
        for i, keyword in enumerate(keywords_list):
            status_text.text(f"Checking {i+1}/{total_keywords}: '{keyword}'...")
            
            payload = json.dumps({
                "q": keyword,
                "location": target_location,
                "gl": "us",
                "hl": "en",
                "num": 100
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
                    if 'organic' in data:
                        for item in data['organic']:
                            clean_target = website_url.replace("https://", "").replace("http://", "").replace("www.", "").split('/')[0]
                            if clean_target.lower() in item['link'].lower():
                                rank = item['position']
                                found_url = item['link']
                                break
                else:
                    rank = f"API Error: {response.status_code}"

            except Exception as e:
                rank = "Error"
                found_url = str(e)
            
            results.append({
                "Keyword": keyword,
                "Location": target_location,
                "Rank": rank,
                "Found URL": found_url
            })
            
            progress_bar.progress((i + 1) / total_keywords)
            time.sleep(0.1)

        status_text.success("✅ Analysis Complete!")
        
        # --- Display Results ---
        df = pd.DataFrame(results)
        
        # Table Styling
        def highlight_rank(val):
            if isinstance(val, int):
                if val <= 3: return 'background-color: #d4edda; color: green'
                elif val <= 10: return 'background-color: #fff3cd; color: orange'
            elif val == "Not in Top 100": return 'color: red'
            return ''

        st.dataframe(df.style.applymap(highlight_rank, subset=['Rank']), use_container_width=True)
        
        # --- EXCEL DOWNLOAD LOGIC ---
        # Buffer create kar rahe hain (Memory mai file)
        buffer = io.BytesIO()
        
        # Pandas ko use kar ke Excel write kar rahe hain
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Rankings')
            
        # File ka pointer start par la rahe hain taake download ho sake
        buffer.seek(0)
        
        # File name banana
        safe_city = target_location.split(',')[0].replace(" ", "_")
        
        st.download_button(
            label="📥 Download Report (.xlsx)",
            data=buffer,
            file_name=f"Rankings_{safe_city}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
