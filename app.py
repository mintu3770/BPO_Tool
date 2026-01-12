import streamlit as st
import google.generativeai as genai
from duckduckgo_search import DDGS
import pandas as pd
import json
import time
import io

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="BPO LeadGen Pro (Debug Mode)", page_icon="🐞", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuration")
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("✅ API Key loaded")
    else:
        api_key = st.text_input("Enter Gemini API Key", type="password")

# --- FUNCTIONS ---
def search_web(query):
    """Searches with debug output."""
    try:
        # Use the 'news' backend for fresher results, or default to text
        with st.status(f"🔍 Searching: {query}...", expanded=True) as status:
            results = DDGS().text(query, max_results=10)
            
            if not results:
                status.update(label="❌ No search results found!", state="error")
                return None
            
            # Formulate context
            context = "\n".join([f"Title: {r['title']}\nSnippet: {r['body']}\nLink: {r['href']}" for r in results])
            status.update(label="✅ Search complete!", state="complete")
            
            # DEBUG: Show what the search engine actually found
            with st.expander("👀 View Raw Search Results (Debug)"):
                st.text(context)
                
            return context
    except Exception as e:
        st.error(f"Search Engine Error: {e}")
        return None

def extract_leads(context, count):
    """Extracts leads with strict JSON formatting."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are a data extraction bot. 
    Extract exactly {count} companies from the text below.
    
    RETURN ONLY RAW JSON. NO MARKDOWN. NO TEXT.
    Structure: [{{ "Company": "...", "Location": "...", "Decision_Maker": "...", "Phone": "...", "Link": "..." }}]
    
    If no phone is found, write "General HQ Line".
    
    Text to analyze:
    {context}
    """
    
    try:
        response = model.generate_content(prompt)
        
        # DEBUG: Show what the AI actually replied
        with st.expander("🤖 View Raw AI Response (Debug)"):
            st.code(response.text)
            
        # Clean the response to remove ```json or ```
        cleaned = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(cleaned)
        
    except Exception as e:
        st.error(f"AI Parsing Error: {e}")
        return []

# --- MAIN UI ---
st.title("🐞 BPO LeadGen (Debug Mode)")
st.warning("This mode shows raw data to help fix the 'No Leads' error.")

region = st.selectbox("Region", ["USA Startups", "UK FTSE 100", "India NIFTY 50"])
service = st.selectbox("Service", ["Hiring", "Support", "Sourcing"])

if st.button("🚀 Run Debug Search"):
    if not api_key:
        st.error("Missing API Key")
    else:
        # 1. Broaden the query to ensure we get hits
        query = f"List of {region} companies with corporate headquarters phone number contact details"
        
        context = search_web(query)
        
        if context:
            st.info("Sending data to AI...")
            leads = extract_leads(context, 5)
            
            if leads:
                st.success("✅ Extraction Successful!")
                df = pd.DataFrame(leads)
                st.dataframe(df)
            else:
                st.error("❌ AI returned empty list or invalid JSON.")
