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
                    model = genai.GenerativeModel('gemini-pro')
                    response = model.generate_content("Hello")
                    st.success(f"Connected to gemini-pro!")
                except Exception as e:
                    st.error(f"Connection Failed: {e}")
        else:
            st.warning("No secrets found. Enter manually:")
            api_key = st.text_input("Google API Key", type="password")
            search_engine_id = st.text_input("Search Engine ID (cx)")
            
    st.divider()
    st.info("💡 **Directory Hack:** This version searches Bloomberg/Reuters profiles which often show the phone number in the snippet!")

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
    """Hybrid Extraction: Tries AI, falls back to manual Regex if AI fails."""
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
    
    prompt = f"""
    Analyze the text below. It contains business directory profiles.
    Extract the Company Name and Phone Number from each snippet.
    
    Format each line strictly like this (Pipe Separated):
    Company Name | Phone Number | Decision Maker Role | Source Link
    
    RULES:
    1. Phone numbers usually look like "+1...", "+44...", "020...". Extract them exactly.
    2. If Phone is missing, write "Link in Excel".
    3. Decision Maker: Guess the role based on "{service}" (e.g. "HR Director" or "Ops Manager").
    
    INPUT TEXT:
    {context}
    """
    
    extracted_leads = []
    
    # 2. TRY AI EXTRACTION
    try:
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        
        for line in raw_text.split('\n'):
            parts = line.split('|')
            if len(parts) >= 3:
                extracted_leads.append({
                    "Company": parts[0].strip(),
                    "Phone": parts[1].strip(),
                    "Decision_Maker": parts[2].strip(),
                    "Source_URL": parts[3].strip() if len(parts) > 3 else "N/A",
                    "Location": region 
                })
    except Exception as ai_error:
        print(f"AI Failed: {ai_error}") 
        
    # 3. REGEX BACKUP (If AI returned nothing)
    if not extracted_leads:
        lines = context.split('\n')
        current_company = "Unknown"
        for line in lines:
            if "Source:" in line:
                current_company = line.replace("Source:", "").replace("Profile", "").strip()
            elif "Snippet:" in line or "Text:" in line:
                # Regex for Intl formats (UK, US, India)
                phones = re.findall(r'(\+?\d[\d \-\(\)]{8,16})', line)
                if phones:
                    # Filter out short dates/years that look like phones
                    valid_phones = [p for p in phones if len(re.sub(r'\D', '', p)) > 8]
                    if valid_phones:
                        extracted_leads.append({
                            "Company": current_company,
                            "Phone": valid_phones[0],
                            "Decision_Maker": "N/A",
                            "Source_URL": "See Search Results",
                            "Location": region
                        })

    return extracted_leads

# --- MAIN APP ---
st.title("🛡️ BPO LeadGen Pro (Directory Mode)")

# --- NEW STRATEGY: TARGET BLOOMBERG/REUTERS ---
# This forces Google to look at profiles that LIST phone numbers in plain text.
REGION_MAP = {
    "UK FTSE 100": "site:bloomberg.com/profile 'United Kingdom' 'Phone' OR 'Tel' -news",
    "USA Startups": "site:bloomberg.com/profile 'United States' 'Phone' OR 'Tel' -news",
    "India NIFTY 50": "site:moneycontrol.com OR site:bloomberg.com/profile 'India' 'Phone' -news"
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
            with st.status("🔍 Searching Business Directories...", expanded=True) as status:
                
                # We specifically hunt for the "Phone" keyword in the profile snippet
                query = f"{search_term} {service}"
                context = search_google_real(query, api_key, search_engine_id)
                
                if context and "API_ERROR" in context:
                    status.update(label="❌ API Error", state="error")
                    st.error(context)
                
                elif context:
                    with st.expander("👀 View Raw Google Results", expanded=False):
                        st.text(context)
                    
                    status.update(label="🧠 Analyzing with AI...", state="running")
                    
                    leads = extract_with_bulletproof_ai(context, region_select, service, count, api_key)
                    
                    if leads:
                        status.update(label="✅ Success!", state="complete")
                        df = pd.DataFrame(leads)
                        
                        # Filter bad rows
                        df = df[df['Company'].str.len() < 50] 
                        
                        st.dataframe(df, use_container_width=True)
                        
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            df.to_excel(writer, index=False)
                        st.download_button("📥 Download Verified Data", buffer.getvalue(), "Real_Leads.xlsx")
                    else:
                        status.update(label="⚠️ Extraction Failed.", state="error")
                        st.error("Could not find phone numbers. Directories might be blocking the snippets.")
                else:
                    status.update(label="❌ No results found", state="error")
