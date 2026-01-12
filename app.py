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
    
    # SECURITY: Check for API Key in Streamlit Secrets
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("✅ API Key loaded securely")
    else:
        # Fallback: Allow manual entry if secrets file is missing
        api_key = st.text_input("Enter Gemini API Key", type="password")
        st.warning("⚠️ No secrets.toml found. Using manual input.")

    st.divider()
    st.info("💡 **Tip:** This tool extracts data from live search results using AI. Verify all phone numbers before calling.")

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
        ["End-to-End Hiring / Staffing", "Customer Support (Voice/Chat)", "Physical Goods Sourcing", "Data Entry / Back Office"]
    )

with col3:
    num_leads = st.slider("Number of Companies to Fetch", min_value=5, max_value=20, value=5)

# --- BACKEND LOGIC ---

def search_web(query):
    """Searches DuckDuckGo for live data."""
    try:
        results = DDGS().text(query, max_results=10)
        return "\n".join([f"- {r['title']}: {r['body']} (Link: {r['href']})" for r in results])
    except Exception as e:
        st.error(f"Search Error: {e}")
        return None

def extract_leads_with_ai(context, region, service, count):
    """Uses Gemini to structure the data into JSON."""
    if not api_key:
        st.error("❌ Missing API Key. Please add it to .streamlit/secrets.toml")
        return []
    
    # Configure API with the secure key
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are a BPO Sales Lead Researcher.
    Analyze the search results below and extract exactly {count} companies in {region} that would likely need {service}.
    
    CRITERIA:
    1. **Phone Number is the MOST IMPORTANT field.** Look for Corporate HQ lines.
    2. Decision Maker should be relevant to {service} (e.g., Head of Talent for Hiring, Ops Director for Sourcing).
    
    OUTPUT FORMAT:
    Return ONLY a raw JSON list of objects. No markdown formatting.
    [
        {{"Company": "Name", "Location": "City", "Decision_Maker": "Role", "Phone": "+1-555...", "Email_Or_Link": "url"}}
    ]
    
    Search Context:
    {context}
    """
    
    try:
        response = model.generate_content(prompt)
        # Cleaning the response to ensure valid JSON
        cleaned_json = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(cleaned_json)
    except Exception as e:
        st.error(f"AI Extraction Error: {e}")
        return []

# --- EXECUTION BUTTON ---
if st.button("🚀 Generate Leads", type="primary"):
    if not api_key:
        st.error("🛑 Please configure your API key first.")
    else:
        with st.spinner(f"Searching verified sources for {target_region}..."):
            # 1. Construct Query
            search_query = f"List of companies {target_region} contact details headquarters phone number for {service_focus}"
            
            # 2. Perform Search
            context_data = search_web(search_query)
            
            if context_data:
                # 3. AI Extraction
                leads_data = extract_leads_with_ai(context_data, target_region, service_focus, num_leads)
                
                if leads_data:
                    # 4. Display Results
                    df = pd.DataFrame(leads_data)
                    st.success(f"Successfully found {len(leads_data)} leads!")
                    st.dataframe(df, use_container_width=True)
                    
                    # 5. Excel Download Logic
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False, sheet_name='Leads')
                    
                    st.download_button(
                        label="📥 Download as Excel",
                        data=buffer.getvalue(),
                        file_name=f"BPO_Leads_{time.strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.ms-excel"
                    )
                else:
                    st.warning("AI found search results but couldn't structure the data. Try reducing the number of leads.")
            else:
                st.error("Search engine returned no results. Try a different region.")
