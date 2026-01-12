import streamlit as st
import google.generativeai as genai
import requests
import pandas as pd
import json
import time
import io
import random

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="BPO LeadGen Pro", page_icon="💼", layout="wide")

# --- SIDEBAR: CONFIGURATION ---
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # 1. MODE SELECTION
    mode = st.radio("Select Mode:", ["🛠️ Simulation (Test UI)", "🌐 Real Google Search"], index=0)
    
    # 2. CREDENTIALS (Only needed for Real Mode)
    if mode == "🌐 Real Google Search":
        st.divider()
        st.markdown("### 🔑 API Credentials")
        
        # Try to load from secrets first
        sec_api = st.secrets.get("GOOGLE_API_KEY")
        sec_cx = st.secrets.get("SEARCH_ENGINE_ID")
        
        if sec_api and sec_cx:
            st.success("Credentials loaded from Secrets!")
            api_key = sec_api
            search_engine_id = sec_cx
        else:
            st.warning("No secrets found. Enter manually:")
            api_key = st.text_input("Google API Key", type="password")
            search_engine_id = st.text_input("Search Engine ID (cx)")
            
    st.divider()
    st.info("💡 **Simulation:** Generates realistic dummy data to test Excel export.\n\n🌐 **Real Search:** Uses your Google API to find actual companies.")

# --- FUNCTIONS ---

def get_simulation_data(region, count):
    """Generates fake verified leads for testing."""
    time.sleep(1.5) # Fake loading
    data = []
    roles = ["Head of Operations", "Director of Talent", "Chief People Officer", "VP Procurement"]
    
    for i in range(count):
        comp_name = f"{region.split()[0]} {random.choice(['Logistics', 'Health', 'Tech', 'Retail'])} {random.randint(100,999)}"
        data.append({
            "Company": comp_name,
            "Location": f"{region} (HQ)",
            "Decision_Maker": random.choice(roles),
            "Phone": f"+1 (800) {random.randint(100,999)}-{random.randint(1000,9999)}",
            "Contact_Link": f"https://www.{comp_name.lower().replace(' ', '')}.com/contact"
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
        return "\n".join([f"Title: {r['title']}\nSnippet: {r.get('snippet','')}\nLink: {r['link']}" for r in data['items']])
    except Exception as e:
        return f"API_ERROR: {str(e)}"

def extract_with_ai(context, region, service, count, api_key):
    """Uses Gemini to parse the search results."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
    
    prompt = f"""
    Extract exactly {count} BPO leads from the text below for {region} needing {service}.
    RETURN RAW JSON LIST ONLY. No markdown.
    [
        {{"Company": "Name", "Location": "City", "Decision_Maker": "Role", "Phone": "Phone Number", "Contact_Link": "URL"}}
    ]
    Context: {context}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except:
        return []

# --- MAIN APP ---
st.title("💼 BPO LeadGen Pro")

c1, c2, c3 = st.columns(3)
with c1: region = st.selectbox("Target Region", ["UK FTSE 100", "USA Startups", "India NIFTY 50"])
with c2: service = st.selectbox("Service Pitch", ["Hiring", "Customer Support", "Sourcing"])
with c3: count = st.slider("Lead Count", 5, 10, 5)

if st.button("🚀 Generate Leads", type="primary"):
    
    # PATH A: SIMULATION
    if mode == "🛠️ Simulation (Test UI)":
        with st.spinner("Generating simulated leads..."):
            leads = get_simulation_data(region, count)
            df = pd.DataFrame(leads)
            st.success(f"Generated {len(leads)} simulated leads!")
            st.dataframe(df, use_container_width=True)
            
            # Export
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            st.download_button("📥 Download Excel", buffer.getvalue(), "Simulation_Leads.xlsx")

    # PATH B: REAL API
    else:
        if not api_key or not search_engine_id:
            st.error("❌ Missing Credentials in Sidebar/Secrets.")
        else:
            with st.status("🔍 Searching Google Live...", expanded=True) as status:
                query = f"List of {region} companies {service} corporate headquarters phone number"
                
                # 1. Search
                context = search_google_real(query, api_key, search_engine_id)
                
                if context and "API_ERROR" in context:
                    status.update(label="❌ API Error", state="error")
                    st.error(context)
                    st.info("Check 'API Restrictions' in Google Cloud Console Credentials.")
                
                elif context:
                    status.update(label="🧠 Analyzing with AI...", state="running")
                    # 2. AI Extract
                    leads = extract_with_ai(context, region, service, count, api_key)
                    
                    if leads:
                        status.update(label="✅ Success!", state="complete")
                        df = pd.DataFrame(leads)
                        st.dataframe(df, use_container_width=True)
                        
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            df.to_excel(writer, index=False)
                        st.download_button("📥 Download Real Data", buffer.getvalue(), "Real_Leads.xlsx")
                    else:
                        status.update(label="⚠️ AI could not format data", state="error")
                else:
                    status.update(label="❌ No results found", state="error")
