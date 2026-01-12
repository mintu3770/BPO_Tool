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
    
    # 1. Load API Key securely
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("✅ API Key loaded securely")
    else:
        api_key = st.text_input("Enter Gemini API Key", type="password")
        if not api_key:
            st.warning("⚠️ Please enter your API Key to proceed.")

    st.divider()
    st.info("💡 **Tip:** This tool extracts data from live search results. Always verify phone numbers before calling.")

# --- FUNCTIONS ---

def search_web(query):
    """Searches using 'html' backend to avoid Cloud blocks."""
    try:
        # UX: Show a status spinner that updates
        with st.status(f"🔍 Searching: {query}...", expanded=True) as status:
            
            # ATTEMPT 1: HTML Backend (Most reliable for Cloud)
            results = DDGS().text(query, max_results=10, backend="html")
            
            # ATTEMPT 2: Lite Backend (Fallback)
            if not results:
                time.sleep(1)
                results = DDGS().text(query, max_results=10, backend="lite")
            
            if not results:
                status.update(label="❌ Search engine blocked or found no results.", state="error")
                return None
            
            # Format results for the AI
            context = "\n".join([f"Title: {r['title']}\nSnippet: {r['body']}\nLink: {r['href']}" for r in results])
            status.update(label="✅ Search complete! Data found.", state="complete")
            return context

    except Exception as e:
        st.error(f"Search Engine Error: {e}")
        return None

def extract_leads_with_retry(context, region, service, count, retries=3):
    """Uses Gemini to structure data, with retry logic for rate limits."""
    if not api_key:
        st.error("❌ Missing API Key.")
        return []
    
    genai.configure(api_key=api_key)
    
    # FIX: Switched to 'gemini-pro' which is universally available on v1beta
    model = genai.GenerativeModel('gemini-pro')
    
    prompt = f"""
    You are a BPO Sales Lead Researcher.
    Analyze the search results below and extract exactly {count} companies in {region} that would likely need {service}.
    
    CRITERIA:
    1. Phone Number is the MOST IMPORTANT field. Look for Corporate HQ lines.
    2. Decision Maker should be relevant to {service}.
    3. If a field is missing, write "N/A".
    
    OUTPUT FORMAT:
    Return ONLY a raw JSON list of objects. Do not use Markdown blocks (no ```json).
    [
        {{"Company": "Name", "Location": "City", "Decision_Maker": "Role", "Phone": "+1-555...", "Email_Or_Link": "url"}}
    ]
    
    Search Context:
    {context}
    """
    
    for attempt in range(retries):
        try:
            response = model.generate_content(prompt)
            
            # Clean response
            cleaned_json = response.text.strip().replace('```json', '').replace('```', '')
            
            # Parse JSON
            return json.loads(cleaned_json)
            
        except Exception as e:
            if "429" in str(e):
                wait_time = (attempt + 1) * 5
                st.warning(f"⚠️ API Busy (Quota Limit). Retrying in {wait_time}s...")
                time.sleep(wait_time)
            elif "404" in str(e):
                st.error("❌ Model Error: The API key cannot access the model. Try creating a new API key.")
                return []
            else:
                st.error(f"AI Extraction Error: {e}")
                return []
    
    st.error("❌ Failed after multiple retries. Try a new API key or reduce the lead count.")
    return []

# --- MAIN INTERFACE ---
st.title("💼 BPO Lead Generation Dashboard")
st.markdown("Generate verified company leads with **Decision Makers** & **Phone Numbers** for outsourcing services.")

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
    num_leads = st.slider("Number of Companies to Fetch", min_value=5, max_value=15, value=5)

# --- EXECUTION BUTTON ---
if st.button("🚀 Generate Leads", type="primary"):
    if not api_key:
        st.error("🛑 Please configure your API key in the sidebar.")
    else:
        # 1. Search
        search_query = f"List of companies {target_region} corporate headquarters phone number contact details for {service_focus}"
        context_data = search_web(search_query)
        
        if context_data:
            # 2. Extract with AI
            with st.spinner("🤖 AI is analyzing search results..."):
                leads_data = extract_leads_with_retry(context_data, target_region, service_focus, num_leads)
            
            if leads_data:
                # 3. Display Results
                df = pd.DataFrame(leads_data)
                st.success(f"Successfully found {len(leads_data)} leads!")
                st.dataframe(df, use_container_width=True)
                
                # 4. Excel Download
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Leads')
                
                st.download_button(
                    label="📥 Download Results as Excel",
                    data=buffer.getvalue(),
                    file_name=f"BPO_Leads_{time.strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.ms-excel"
                )
            else:
                st.warning("The AI found search results but couldn't format them. Try searching for a different region.")
