import streamlit as st
import google.generativeai as genai
from duckduckgo_search import DDGS
import pandas as pd
import json
import time
import io

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="BPO LeadGen Pro", page_icon="💼", layout="wide")

# --- SIDEBAR: CONFIGURATION ---
with st.sidebar:
    st.header("⚙️ Configuration")
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("✅ API Key loaded securely")
    else:
        api_key = st.text_input("Enter Gemini API Key", type="password")
        st.warning("⚠️ No secrets.toml found. Using manual input.")

# --- BACKEND LOGIC ---
def search_web(query):
    """Searches DuckDuckGo for live data."""
    try:
        results = DDGS().text(query, max_results=10)
        return "\n".join([f"- {r['title']}: {r['body']} (Link: {r['href']})" for r in results])
    except Exception as e:
        st.error(f"Search Error: {e}")
        return None

def extract_leads_with_retry(context, region, service, count, retries=3):
    """Uses Gemini to structure data with Retry Logic for 429 Errors."""
    if not api_key:
        st.error("❌ Missing API Key.")
        return []
    
    genai.configure(api_key=api_key)
    # Using 'gemini-1.5-flash' as it is the fastest/cheapest
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are a BPO Sales Lead Researcher.
    Analyze the search results below and extract exactly {count} companies in {region} that would likely need {service}.
    
    CRITERIA:
    1. Phone Number is the MOST IMPORTANT field. Look for Corporate HQ lines.
    2. Decision Maker should be relevant to {service}.
    
    OUTPUT FORMAT:
    Return ONLY a raw JSON list of objects. No markdown.
    [
        {{"Company": "Name", "Location": "City", "Decision_Maker": "Role", "Phone": "+1-555...", "Email_Or_Link": "url"}}
    ]
    
    Search Context:
    {context}
    """
    
    for attempt in range(retries):
        try:
            response = model.generate_content(prompt)
            cleaned_json = response.text.strip().replace('```json', '').replace('```', '')
            return json.loads(cleaned_json)
        except Exception as e:
            if "429" in str(e):
                wait_time = (attempt + 1) * 5  # Wait 5s, then 10s, then 15s
                st.warning(f"⚠️ API Busy (429). Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                st.error(f"AI Extraction Error: {e}")
                return []
    
    st.error("❌ Failed after multiple retries. Try reducing the number of leads.")
    return []

# --- MAIN INTERFACE ---
st.title("💼 BPO Lead Generation Dashboard")

col1, col2, col3 = st.columns(3)
with col1:
    target_region = st.selectbox("Target Geography", ["USA", "UK", "India"])
with col2:
    service_focus = st.selectbox("Service Pitch", ["Hiring", "Customer Support", "Sourcing"])
with col3:
    num_leads = st.slider("Leads count", 5, 20, 5)

if st.button("🚀 Generate Leads", type="primary"):
    if not api_key:
        st.error("🛑 Please configure your API key.")
    else:
        with st.spinner(f"Searching verified sources for {target_region}..."):
            search_query = f"List of companies {target_region} contact details headquarters phone number for {service_focus}"
            context_data = search_web(search_query)
            
            if context_data:
                leads_data = extract_leads_with_retry(context_data, target_region, service_focus, num_leads)
                
                if leads_data:
                    df = pd.DataFrame(leads_data)
                    st.success(f"Successfully found {len(leads_data)} leads!")
                    st.dataframe(df, use_container_width=True)
                    
                    # Excel Download
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False, sheet_name='Leads')
                    
                    st.download_button(
                        label="📥 Download Excel",
                        data=buffer.getvalue(),
                        file_name=f"Leads.xlsx",
                        mime="application/vnd.ms-excel"
                    )
