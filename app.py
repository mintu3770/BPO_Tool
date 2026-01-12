import streamlit as st
import google.generativeai as genai
import requests
import pandas as pd
import json
import time
import io
import random

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="BPO LeadGen Pro (Strict Mode)", page_icon="🛡️", layout="wide")

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
            
            # CONNECTION CHECKER
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
    st.info("🛡️ **Strict Mode:** This version will output 'N/A' instead of fake numbers if Google doesn't provide the data.")

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
            "Contact_Link": "https://www.example.com",
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
        return "\n".join([f"Source: {r['title']}\nText: {r.get('snippet','')}\nURL: {r['link']}" for r in data['items']])
    except Exception as e:
        return f"API_ERROR: {str(e)}"

def extract_with_strict_ai(context, region, service, count, api_key):
    """Uses Gemini 1.5 Flash with STRICT instructions to avoid hallucination."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are a strict Data Analyst. Analyze the text below to find BPO leads for {region} needing {service}.
    
    STRICT RULES:
    1. **DO NOT INVENT DATA.** If a phone number or name is not explicitly written in the "Text" provided below, write "N/A".
    2. Do not make up company names that are not in the text.
    3. Extract exactly {count} companies if possible.
    
    INPUT TEXT FROM GOOGLE:
    {context}
    
    OUTPUT FORMAT (Raw JSON only):
    [
        {{"Company": "Exact Name from text", "Location": "City/Country from text", "Decision_Maker": "Role found or N/A", "Phone": "Number found or N/A", "Source_URL": "URL from text"}}
    ]
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except Exception as e:
        return f"AI_ERROR: {str(e)}"

# --- MAIN APP ---
st.title("🛡️ BPO LeadGen Pro (Strict Mode)")

c1, c2, c3 = st.columns(3)
with c1: region = st.selectbox("Target Region", ["UK FTSE 100", "USA Startups", "India NIFTY 50"])
with c2: service = st.selectbox("Service Pitch", ["Hiring", "Customer Support", "Sourcing"])
with c3: count = st.slider("Lead Count", 5, 10, 5)

if st.button("🚀 Generate Leads", type="primary"):
    
    if mode == "🛠️ Simulation (Test UI)":
        # ... Simulation Logic (Same as before) ...
        leads = get_simulation_data(region, count)
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
                # Optimized Query for specific details
                query = f"site:linkedin.com OR site:bloomberg.com {region} {service} 'headquarters' 'phone'"
                
                context = search_google_real(query, api_key, search_engine_id)
                
                if context and "API_ERROR" in context:
                    status.update(label="❌ API Error", state="error")
                    st.error(context)
                
                elif context:
                    # SHOW THE RAW DATA (Source of Truth)
                    with st.expander("👀 View Raw Google Search Results (Check this if data seems fake)", expanded=False):
                        st.text(context)
                    
                    status.update(label="🧠 Analyzing with Strict AI...", state="running")
                    leads = extract_with_strict_ai(context, region, service, count, api_key)
                    
                    if isinstance(leads, list) and leads:
                        status.update(label="✅ Success!", state="complete")
                        df = pd.DataFrame(leads)
                        
                        # Highlight N/A values
                        st.warning("⚠️ Note: If you see 'N/A', it means the data was not found in the search snippets. This is good! It means the AI is not lying.")
                        st.dataframe(df, use_container_width=True)
                        
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            df.to_excel(writer, index=False)
                        st.download_button("📥 Download Verified Data", buffer.getvalue(), "Real_Leads.xlsx")
                    else:
                        status.update(label="⚠️ AI Error or No Data", state="error")
                else:
                    status.update(label="❌ No results found", state="error")
