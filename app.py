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
    st.info("💡 **Tip:** This version captures 'Click Link' leads if the phone number is hidden in the website.")

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

def extract_with_lenient_ai(context, region, service, count, api_key):
    """Uses Gemini 1.5 Flash with LENIENT instructions to capture more leads."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are a Lead Generation Specialist. Analyze the Google Search Results below.
    
    GOAL: List {count} companies in {region} needing {service}.
    
    RULES:
    1. **Phone Numbers:** Extract any phone number digits found in the snippet.
    2. **Fallback:** If the snippet matches a company but has NO phone number, write "Link in Excel" in the Phone field. DO NOT discard the lead.
    3. **Cleanup:** Remove text like "Give a missed call on" and just keep the digits if possible.
    
    INPUT CONTEXT:
    {context}
    
    OUTPUT FORMAT (Return strictly a JSON list):
    [
        {{"Company": "Name", "Location": "City/Region", "Decision_Maker": "Department/Role", "Phone": "Number or 'Link in Excel'", "Source_URL": "Link"}}
    ]
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except Exception as e:
        return f"AI_ERROR: {str(e)}"

# --- MAIN APP ---
st.title("🛡️ BPO LeadGen Pro (Lenient Mode)")

# --- FIXED MAPPING: OPTIMIZED FOR CONTACT PAGES ---
REGION_MAP = {
    "UK FTSE 100": "UK FTSE 100 'Head Office' contact number",
    "USA Startups": "USA tech startup 'Corporate Headquarters' phone number",
    "India NIFTY 50": "India NIFTY 50 'Customer Care' contact number"
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
                
                # Broad query to catch both "Phone" and "Contact" pages
                query = f"{search_term} {service} -news -jobs"
                
                context = search_google_real(query, api_key, search_engine_id)
                
                if context and "API_ERROR" in context:
                    status.update(label="❌ API Error", state="error")
                    st.error(context)
                
                elif context:
                    with st.expander("👀 View Raw Google Results", expanded=False):
                        st.text(context)
                    
                    status.update(label="🧠 Analyzing with AI...", state="running")
                    leads = extract_with_lenient_ai(context, region_select, service, count, api_key)
                    
                    if isinstance(leads, list) and leads:
                        status.update(label="✅ Success!", state="complete")
                        df = pd.DataFrame(leads)
                        
                        # Filter out empty rows
                        df = df[df['Company'] != "N/A"]
                        
                        st.dataframe(df, use_container_width=True)
                        
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            df.to_excel(writer, index=False)
                        st.download_button("📥 Download Verified Data", buffer.getvalue(), "Real_Leads.xlsx")
                    else:
                        status.update(label="⚠️ No structured data found.", state="error")
                        st.warning("Google found results, but AI couldn't parse them. Try 'Simulation Mode'.")
                else:
                    status.update(label="❌ No results found", state="error")
