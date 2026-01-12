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
    st.info("💡 **Tip:** This version uses a Regex Safety Net to capture phone numbers even if the AI misses them.")

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

def extract_with_bulletproof_ai(context, region, service, count, api_key):
    """Uses Gemini 1.5 Flash with Simple Formatting + Regex Backup."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # SIMPLER PROMPT: Ask for pipe-separated text, not complex JSON
    prompt = f"""
    Analyze the text below and list companies found.
    Format each line strictly like this:
    Company Name | Phone Number | Decision Maker Role | Source Link
    
    RULES:
    1. If Phone is missing, write "Link in Excel".
    2. If Role is missing, write "N/A".
    3. Do not add bolding or markdown. Just the text.
    
    INPUT TEXT:
    {context}
    """
    try:
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        
        # Parse the pipe-separated lines manually
        leads = []
        for line in raw_text.split('\n'):
            parts = line.split('|')
            if len(parts) >= 3:
                leads.append({
                    "Company": parts[0].strip(),
                    "Phone": parts[1].strip(),
                    "Decision_Maker": parts[2].strip(),
                    "Source_URL": parts[3].strip() if len(parts) > 3 else "N/A",
                    "Location": region # Default location
                })
        return leads
    except Exception as e:
        return f"AI_ERROR: {str(e)}"

# --- MAIN APP ---
st.title("🛡️ BPO LeadGen Pro (Bulletproof Mode)")

# --- FIXED MAPPING: FORCE "TELEPHONE" IN SEARCH ---
REGION_MAP = {
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
                
                query = f"{search_term} {service}"
                context = search_google_real(query, api_key, search_engine_id)
                
                if context and "API_ERROR" in context:
                    status.update(label="❌ API Error", state="error")
                    st.error(context)
                
                elif context:
                    with st.expander("👀 View Raw Google Results", expanded=False):
                        st.text(context)
                    
                    status.update(label="🧠 Analyzing with AI...", state="running")
                    
                    # 1. Try AI Extraction
                    leads = extract_with_bulletproof_ai(context, region_select, service, count, api_key)
                    
                    # 2. Safety Check: If AI failed completely, return an error
                    if isinstance(leads, str) and "AI_ERROR" in leads:
                        status.update(label="⚠️ AI Error", state="error")
                        st.error(leads)
                    elif isinstance(leads, list) and leads:
                        status.update(label="✅ Success!", state="complete")
                        df = pd.DataFrame(leads)
                        
                        # Filter bad rows
                        df = df[df['Company'] != "Company Name"] 
                        
                        st.dataframe(df, use_container_width=True)
                        
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            df.to_excel(writer, index=False)
                        st.download_button("📥 Download Verified Data", buffer.getvalue(), "Real_Leads.xlsx")
                    else:
                        status.update(label="⚠️ Parsing Failed.", state="error")
                        st.error("The AI read the data but couldn't format it. Try searching a different region.")
                else:
                    status.update(label="❌ No results found", state="error")
