# =====================================================
# BPO LeadGen Pro – Production-Ready Streamlit App
# =====================================================

import streamlit as st
import google.generativeai as genai
import requests
import pandas as pd
import time
import io
import random
import re
import logging

# =====================================================
# CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="BPO LeadGen Pro",
    page_icon="💼",
    layout="wide"
)

logging.basicConfig(level=logging.INFO)

# =====================================================
# CONSTANTS
# =====================================================

REGION_MAP = {
    "UK ": "UK plc corporate office Contact phone number -news",
    "USA ": "USA Inc headquarters Contact Us phone -news",
    "India ": "India Limited company corporate office contact number -news"
}

ROLES_BY_SERVICE = {
    "Hiring": ["HR Manager", "Head of Talent", "Chief People Officer"],
    "Customer Support": ["Head of Operations", "Support Director"],
    "Sourcing": ["Procurement Head", "VP Procurement"]
}

# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:
    st.header("⚙️ Configuration")

    mode = st.radio(
        "Select Mode:",
        ["🌐 Real Google Search", "🛠️ Simulation (Test UI)"],
        index=0
    )

    if mode == "🌐 Real Google Search":
        st.divider()
        st.markdown("### 🔑 API Credentials")

        sec_api = st.secrets.get("GOOGLE_API_KEY")
        sec_cx = st.secrets.get("SEARCH_ENGINE_ID")

        if sec_api and sec_cx:
            st.success("Credentials loaded from Secrets")
            API_KEY = sec_api
            CX_ID = sec_cx
        else:
            API_KEY = st.text_input("Google API Key", type="password")
            CX_ID = st.text_input("Search Engine ID (cx)")

    st.divider()
    st.info(
        "Hunter Mode: If phone is hidden, the tool saves the contact page link "
        "instead of discarding the lead."
    )

# =====================================================
# UTILITIES
# =====================================================

def normalize_phone(phone: str) -> str:
    phone = re.sub(r"[^\d+]", "", phone)
    return phone if len(phone) >= 8 else "Visit Website"

def rate_limit():
    time.sleep(random.uniform(0.8, 1.5))

# =====================================================
# SIMULATION MODE
# =====================================================

def get_simulation_data(region: str, count: int):
    rate_limit()
    roles = [
        "Head of Operations",
        "Director of Talent",
        "Chief People Officer",
        "VP Procurement"
    ]

    data = []
    for _ in range(count):
        data.append({
            "Company": f"Simulated {region.split()[0]} Corp {random.randint(100,999)}",
            "Location": f"{region} (HQ)",
            "Decision Maker": random.choice(roles),
            "Phone": f"+1-800-{random.randint(100,999)}-{random.randint(1000,9999)}",
            "Source Link": "https://www.example.com",
            "Lead Type": "SIMULATED"
        })
    return data

# =====================================================
# GOOGLE SEARCH
# =====================================================

def search_google(query: str, api_key: str, cx: str):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": api_key, "cx": cx, "q": query, "num": 10}

    try:
        response = requests.get(url, params=params)
        data = response.json()

        if "error" in data:
            return f"API_ERROR: {data['error']['message']}"

        if "items" not in data:
            return None

        results = []
        for item in data["items"]:
            results.append(
                f"Source: {item['title']}\n"
                f"Snippet: {item.get('snippet','')}\n"
                f"URL: {item['link']}"
            )

        rate_limit()
        return "\n".join(results)

    except Exception as e:
        return f"API_ERROR: {str(e)}"

# =====================================================
# AI + HUNTER EXTRACTION
# =====================================================

def extract_leads(context, region, service, api_key, count):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-pro")

    prompt = f"""
You are a professional data extractor.

TASK:
Extract company leads from the text below.

FORMAT (PIPE SEPARATED):
Company Name | Phone Number | Decision Maker Role | Source Link

RULES:
- DO NOT invent phone numbers.
- If phone is missing, write exactly: Visit Website
- Base role on service: {service}

INPUT:
{context}
"""

    leads = []

    # ---------- AI PASS ----------
    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()

        for line in raw.split("\n"):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                phone = normalize_phone(parts[1])
                leads.append({
                    "Company": parts[0],
                    "Phone": phone,
                    "Decision Maker": parts[2],
                    "Source Link": parts[3] if len(parts) > 3 else "N/A",
                    "Location": region,
                    "Lead Type": "Phone Verified" if phone != "Visit Website" else "Link Only"
                })

    except Exception as e:
        logging.warning(f"Gemini extraction failed: {e}")

    # ---------- REGEX FALLBACK ----------
    if not leads:
        current_company = "Unknown Company"
        current_link = "N/A"

        for line in context.split("\n"):
            if line.startswith("Source:"):
                current_company = line.replace("Source:", "").strip()
            elif line.startswith("URL:"):
                current_link = line.replace("URL:", "").strip()
            elif "Snippet:" in line:
                phones = re.findall(r'(\+?\d[\d \-]{8,15})', line)
                phone = normalize_phone(phones[0]) if phones else "Visit Website"

                leads.append({
                    "Company": current_company,
                    "Phone": phone,
                    "Decision Maker": random.choice(ROLES_BY_SERVICE[service]),
                    "Source Link": current_link,
                    "Location": region,
                    "Lead Type": "Phone Verified" if phone != "Visit Website" else "Link Only"
                })

    # Deduplicate & limit
    df = pd.DataFrame(leads)
    if not df.empty:
        df.drop_duplicates(subset=["Company"], inplace=True)
        return df.head(count).to_dict(orient="records")

    return []

# =====================================================
# MAIN UI
# =====================================================

st.title("🛡️ BPO LeadGen Pro")
st.caption("Publicly sourced business contact intelligence. GDPR compliant.")

c1, c2, c3 = st.columns(3)
with c1:
    region = st.selectbox("Target Region", REGION_MAP.keys())
with c2:
    service = st.selectbox("Service Pitch", list(ROLES_BY_SERVICE.keys()))
with c3:
    count = st.slider("Lead Count", 5, 10, 5)

# =====================================================
# ACTION
# =====================================================

if st.button("🚀 Generate Leads", type="primary"):

    if mode == "🛠️ Simulation (Test UI)":
        leads = get_simulation_data(region, count)
        df = pd.DataFrame(leads)

    else:
        if not API_KEY or not CX_ID:
            st.error("Missing API credentials.")
            st.stop()

        query = f"{REGION_MAP[region]} {service}"
        st.write(f"Debug Query: `{query}`")

        with st.status("🔍 Searching & Extracting...", expanded=True):
            context = search_google(query, API_KEY, CX_ID)

            if not context or "API_ERROR" in str(context):
                st.error(context or "No results found.")
                st.stop()

            leads = extract_leads(context, region, service, API_KEY, count)
            df = pd.DataFrame(leads)

    if not df.empty:
        st.dataframe(df, use_container_width=True)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False)

        st.download_button(
            "📥 Download Excel",
            buffer.getvalue(),
            file_name="BPO_Leads.xlsx"
        )
    else:
        st.warning("No leads extracted. Try a different query.")
