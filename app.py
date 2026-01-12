import streamlit as st
import google.generativeai as genai
import requests
import pandas as pd
import json
import time
import io
import random
import re

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="BPO LeadGen Pro", page_icon="💼", layout="wide")

# --- SIDEBAR: CONFIGURATION ---
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # 1. MODE SELECTION
    mode = st.radio("Select Mode:", ["🌐 Real Google Search", "🛠️ Simulation (Test UI)"], index=0)
    
    # 2. CREDENTIALS
    if mode == "🌐 Real Google Search":
        st.divider()
        st.markdown("### 🔑 API Credentials")
        
        sec_api = st.secrets.get("GOOGLE_API_KEY")
        sec_cx = st.secrets.get("SEARCH_ENGINE_ID")
        
        if sec_api and sec_cx:
            st.success("Credentials loaded from Secrets!")
            api_key = sec_api
            search_engine_id = sec_cx
            
            if st.button("Test API Connection"):
                try:
                    genai.configure(api_key=api_key)
                    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    st.success(f"Connected! Available models: {len(models)}")
                except Exception as e:
                    st.error(f"Connection Failed: {e}")
        else:
            st.warning("No secrets found. Enter manually:")
            api_key = st.text_input("Google API Key", type="password")
            search_engine_id = st.text_input("Search Engine ID (cx)")
            
    st.divider()
    st.info("💡 **Tip:** This version is 'Permissive'. It saves companies even if the phone number is missing (marked as 'See Link').")

# --- FUNCTIONS ---

def get_simulation_data(region, count):
    """Generates fake verified leads for testing."""
    time.sleep(1.5) 
    data = []
    roles = ["Head of Operations", "Director of Talent", "Chief People Officer", "VP Procurement"]
    for i in range(count):
        comp_name = f"Simulated {region.split()[0]} Corp {random.randint(100,999)}"
        data.append({
            "Company": comp_name,
            "Location": f"{region} (HQ)",
            "Decision_Maker": random.choice(roles),
            "Phone": f"+1 (800) {random.randint(100,999)}-{random.randint(1000,9999)}",
            "Source_URL": "https://www.example.com",
            "Verification": "SIMULATED DATA"
        })
    return data

def search_google_real(query, api_key, cx):
    """Real API Call to Google Custom Search."""
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": api_key, "cx": cx, "q": query, "num": 10}
    try:
        res = requests.get(url, params=params)
        data = res.json()
        if "error" in data:
            return f"API_ERROR: {data['error']['message']}"
        if "items" not in data:
            return None
        return "\n".join([f"Source: {r['title']}\nSnippet: {r.get('snippet','')}\nURL: {r['link']}" for r in data['items']])
    except Exception as e:
        return f"API_ERROR: {str(e)}"

def extract_with_permissive_ai(context, region, service, count, api_key):
    """Uses Gemini 1.5 Flash with PERMISSIVE instructions."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are a Data Scraper. Extract every company mentioned in the text below.
    
    GOAL: List {count} companies in {region}.
    
    RULES:
    1. **Company Name:** Extract the name of the company (e.g., Unilever, Aberdeen).
    2. **Phone Numbers:** If you see digits (e.g., +44, 020, 1-800), extract them.
    3. **MISSING PHONE:** If there is NO phone number, write "See Link" in the Phone field. DO NOT SKIP THE COMPANY.
    4. **Decision Maker:** Guess the relevant role for {service} (e.g., "HR Director", "Ops Lead").
    
    INPUT CONTEXT:
    {context}
    
    OUTPUT FORMAT (Return strictly a JSON list):
    [
        {{"Company": "Name", "Location": "Address found or Region", "Decision_Maker": "Role", "Phone": "Number or 'See Link'", "Source_URL": "Link"}}
    ]
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        # Attempt to parse
        return json.loads(text)
    except Exception as e:
        return f"AI_ERROR: {str(e)}"

# --- MAIN APP ---
st.title("🛡️ BPO LeadGen Pro (Permissive Mode)")

# --- FIXED MAPPING: FORCE "TELEPHONE" IN SEARCH ---
REGION_MAP = {
    # We add "Telephone" OR "Tel" to force digits into the snippet
    "UK FTSE 100": "UK plc 'Contact Us' (Telephone OR Tel) -news -jobs",
    "USA Startups": "USA Inc 'Contact Us' (Phone OR Call) -news -jobs",
    "India NIFTY 50": "India Limited 'Contact Us' (Tel OR Phone) -news -jobs"
}

c1, c2, c3 = st.columns(3)
with c1: 
    region_select = st.selectbox("Target Region", list(REGION_MAP.keys()))
    search_term = REGION_MAP[region_select] 
with c2: 
    service = st.selectbox("Service Pitch", ["Hiring", "Customer Support", "Sourcing"])
with c3: 
    count = st.slider("Lead Count", 5, 10, 5)

if st.button("🚀 Generate Leads", type="primary"):
    
    if mode == "🛠️ Simulation (Test UI)":
        leads = get_simulation_data(region_select, count)
        df = pd.DataFrame(leads)
        st.success("Generated Simulated Data")
        st.dataframe(df)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        st.download_button("📥 Download Excel", buffer.getvalue(), "Sim_Leads.xlsx")

    else:
        # REAL MODE
        if not api_key or not search_engine_id:
            st.error("❌ Missing Credentials")
        else:
            with st.status("🔍 Searching Google Live...", expanded=True) as status:
                
                # Query includes "Telephone" to force digits
                query = f"{search_term} {service}"
                
                context = search_google_real(query, api_key, search_engine_id)
                
                if context and "API_ERROR" in context:
                    status.update(label="❌ API Error", state="error")
                    st.error(context)
                
                elif context:
                    with st.expander("👀 View Raw Google Results", expanded=False):
                        st.text(context)
                    
                    status.update(label="🧠 Analyzing with AI...", state="running")
                    leads = extract_with_permissive_ai(context, region_select, service, count, api_key)
                    
                    if isinstance(leads, list) and leads:
                        status.update(label="✅ Success!", state="complete")
                        df = pd.DataFrame(leads)
                        
                        # Filter out obviously bad rows
                        df = df[df['Company'] != "N/A"]
                        
                        st.dataframe(df, use_container_width=True)
                        
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            df.to_excel(writer, index=False)
                        st.download_button("📥 Download Verified Data", buffer.getvalue(), "Real_Leads.xlsx")
                    else:
                        status.update(label="⚠️ AI Parsing Error.", state="error")
                        st.error("AI could not extract lists. This usually happens if the search results were too messy.")
                else:
                    status.update(label="❌ No results found", state="error")
