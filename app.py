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
    st.info("💡 **Hunter Mode:** Scans for 'Contact Us' pages. If no phone number is found in the preview, it provides the direct link.")

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

def extract_with_hunter_ai(context, region, service, count, api_key):
    """Hybrid Extraction: Matches Companies + Phones, with fallbacks."""
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
    
    prompt = f"""
    You are a Data Scraper. Analyze the search results below.
    
    GOAL: Create a list of companies found in the text.
    
    OUTPUT FORMAT (Pipe Separated):
    Company Name | Phone Number | Decision Maker Role | Source Link
    
    RULES:
    1. **Company Name:** Extract the name (e.g. AstraZeneca, Barclays).
    2. **Phone:** Look for digits. If NONE found, write "Visit Website".
    3. **Role:** Guess the role based on "{service}" (e.g. "HR Manager" or "Head of Ops").
    
    INPUT TEXT:
    {context}
    """
    
    extracted_leads = []
    
    # 1. TRY AI EXTRACTION
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
        
    # 2. FAILSAFE: If AI found nothing, manually parse the text lines
    if not extracted_leads:
        lines = context.split('\n')
        current_company = "Unknown Company"
        current_link = "N/A"
        
        for line in lines:
            if "Source:" in line:
                current_company = line.replace("Source:", "").replace("Contact", "").strip()
            elif "URL:" in line:
                current_link = line.replace("URL:", "").strip()
            elif "Snippet:" in line:
                # Basic Regex for phones
                phones = re.findall(r'(\+?\d[\d \-]{8,15})', line)
                phone_val = phones[0] if phones else "Visit Website"
                
                # Add to list
                extracted_leads.append({
                    "Company": current_company,
                    "Phone": phone_val,
                    "Decision_Maker": "N/A",
                    "Source_URL": current_link,
                    "Location": region
                })

    return extracted_leads

# --- MAIN APP ---
st.title("🛡️ BPO LeadGen Pro (Hunter Mode)")

# --- FIXED MAPPING: BROAD BUT SPECIFIC ---
REGION_MAP = {
    # We remove "site:" restrictions to ensure RESULTS appear.
    # We add "Contact" and "Phone" to prioritize snippets with numbers.
    "UK FTSE 100": "UK plc corporate office 'Contact' phone number -news",
    "USA Startups": "USA Inc headquarters 'Contact Us' phone -news",
    "India NIFTY 50": "India Limited company corporate office contact number -news"
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
            with st.status("🔍 Hunting for Leads...", expanded=True) as status:
                
                query = f"{search_term} {service}"
                
                # DEBUG: Show query so we know what's happening
                st.write(f"**Debug Query:** `{query}`")
                
                context = search_google_real(query, api_key, search_engine_id)
                
                if context and "API_ERROR" in context:
                    status.update(label="❌ API Error", state="error")
                    st.error(context)
                
                elif context:
                    with st.expander("👀 View Raw Google Results", expanded=False):
                        st.text(context)
                    
                    status.update(label="🧠 Extracting Data...", state="running")
                    
                    leads = extract_with_hunter_ai(context, region_select, service, count, api_key)
                    
                    if leads:
                        status.update(label="✅ Success!", state="complete")
                        df = pd.DataFrame(leads)
                        
                        # Filter out bad header rows
                        df = df[df['Company'] != "Company Name"]
                        
                        st.dataframe(df, use_container_width=True)
                        
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            df.to_excel(writer, index=False)
                        st.download_button("📥 Download Verified Data", buffer.getvalue(), "Real_Leads.xlsx")
                    else:
                        status.update(label="⚠️ Extraction Failed.", state="error")
                        st.error("Google found data, but the extractor missed it. Check the 'Raw Results' above.")
                else:
                    status.update(label="❌ No results found", state="error")
                    st.error("Google returned 0 results. Try a different Region.")
