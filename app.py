import streamlit as st
import google.generativeai as genai
import requests
import pandas as pd
import json
import time
import io

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="BPO LeadGen Pro (Official API)", page_icon="💼", layout="wide")

# --- SIDEBAR: CONFIGURATION ---
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Check for Keys
    api_key = st.secrets.get("GOOGLE_API_KEY")
    search_engine_id = st.secrets.get("SEARCH_ENGINE_ID")

    if api_key and search_engine_id:
        st.success("✅ Credentials Loaded")
    else:
        st.error("❌ Missing Credentials")
        st.info("Add GOOGLE_API_KEY and SEARCH_ENGINE_ID to secrets.")
        api_key = st.text_input("Manual API Key", type="password")
        search_engine_id = st.text_input("Manual Search Engine ID")

    st.divider()
    st.markdown("Uses **Google Custom Search API** (Reliable & Block-Free).")

# --- FUNCTIONS ---

def search_google(query, api_key, cx):
    """Searches using Google's Official JSON API."""
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cx,
        "q": query,
        "num": 10  # Max allowed per request
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        # Check for errors in the API response
        if "error" in data:
            st.error(f"Google Search API Error: {data['error']['message']}")
            return None
            
        if "items" not in data:
            return None
            
        # Format results for Gemini
        results = data["items"]
        context = "\n".join([f"Title: {r['title']}\nSnippet: {r.get('snippet', '')}\nLink: {r['link']}" for r in results])
        return context

    except Exception as e:
        st.error(f"Request Failed: {e}")
        return None

def extract_leads_with_ai(context, region, service, count):
    """Uses Gemini to structure data."""
    if not api_key:
        return []
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
    
    prompt = f"""
    You are a BPO Sales Lead Researcher.
    Analyze the search results below and extract exactly {count} companies in {region} that would likely need {service}.
    
    CRITERIA:
    1. Phone Number is the MOST IMPORTANT field. Look for Corporate HQ lines.
    2. Decision Maker should be relevant to {service}.
    3. If a field is missing, write "N/A".
    
    OUTPUT FORMAT:
    Return ONLY a raw JSON list of objects. No markdown blocks.
    [
        {{"Company": "Name", "Location": "City", "Decision_Maker": "Role", "Phone": "+1-555...", "Email_Or_Link": "url"}}
    ]
    
    Search Context:
    {context}
    """
    
    try:
        response = model.generate_content(prompt)
        cleaned_json = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(cleaned_json)
    except Exception as e:
        st.error(f"AI Extraction Error: {e}")
        return []

# --- MAIN INTERFACE ---
st.title("💼 BPO Lead Generation Dashboard")
st.caption("Powered by Google Custom Search & Gemini Pro")

# Input Columns
col1, col2, col3 = st.columns(3)

with col1:
    target_region = st.selectbox(
        "Target Geography",
        ["USA (Recently Funded Startups)", "UK (FTSE 100 / AIM)", "India (NIFTY 50 / Next 50)"]
    )

with col2:
    service_focus = st.selectbox(
        "Priority Service Pitch",
        ["End-to-End Hiring / Staffing", "Customer Support (Voice/Chat)", "Physical Goods Sourcing"]
    )

with col3:
    num_leads = st.slider("Number of Companies", 5, 10, 5)

# --- EXECUTION ---
if st.button("🚀 Generate Leads", type="primary"):
    if not api_key or not search_engine_id:
        st.error("🛑 Please configure your secrets.toml with API Key and Search Engine ID.")
    else:
        with st.status("🔍 Searching Google...", expanded=True) as status:
            # 1. Search
            search_query = f"List of companies {target_region} corporate headquarters phone number contact details for {service_focus}"
            context_data = search_google(search_query, api_key, search_engine_id)
            
            if context_data:
                status.update(label="✅ Search Complete! Analyzing...", state="running")
                
                # 2. AI Extraction
                leads_data = extract_leads_with_ai(context_data, target_region, service_focus, num_leads)
                
                if leads_data:
                    status.update(label="✅ Leads Generated!", state="complete")
                    
                    # 3. Display & Export
                    df = pd.DataFrame(leads_data)
                    st.success(f"Found {len(leads_data)} verified leads.")
                    st.dataframe(df, use_container_width=True)
                    
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False, sheet_name='Leads')
                    
                    st.download_button(
                        label="📥 Download Excel",
                        data=buffer.getvalue(),
                        file_name=f"BPO_Leads_{time.strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.ms-excel"
                    )
                else:
                    status.update(label="⚠️ AI could not format data.", state="error")
            else:
                status.update(label="❌ No results found via Google API.", state="error")
