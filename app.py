# =====================================================
# BPO LeadGen Pro – Country & Company-Class Enforced
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
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="BPO LeadGen Pro",
    page_icon="💼",
    layout="wide"
)

logging.basicConfig(level=logging.INFO)

# =====================================================
# REGION + COMPANY CLASS MAP (CRITICAL CHANGE)
# =====================================================

REGION_MAP = {
    "UK – Startups": {
        "query": "UK startup company headquarters contact",
        "gl": "uk",
        "signals": ["startup", "limited", "ltd", "ventures"],
        "class": "Startup"
    },
    "UK – Top Priced Companies": {
        "query": "FTSE 100 plc headquarters contact",
        "gl": "uk",
        "signals": ["plc", "FTSE"],
        "class": "Listed Enterprise"
    },
    "USA – Startups": {
        "query": "US startup company headquarters contact",
        "gl": "us",
        "signals": ["startup", "inc", "ventures"],
        "class": "Startup"
    },
    "USA – Top Priced Companies": {
        "query": "S&P 500 company headquarters contact",
        "gl": "us",
        "signals": ["NYSE", "NASDAQ", "Corp"],
        "class": "Listed Enterprise"
    },
    "India – Startups": {
        "query": "Indian startup private limited company contact",
        "gl": "in",
        "signals": ["startup", "pvt", "private"],
        "class": "Startup"
    },
    "India – Top Priced Companies": {
        "query": "NIFTY 50 listed company corporate office contact",
        "gl": "in",
        "signals": ["limited", "ltd", "NSE", "BSE"],
        "class": "Listed Enterprise"
    }
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
        "Hunter Mode enabled: If phone number is hidden, "
        "the tool saves the contact page link instead of discarding the lead."
    )

# =====================================================
# UTILITIES
# =====================================================

def rate_limit():
    time.sleep(random.uniform(0.8, 1.5))

def normalize_phone(phone):
    phone = re.sub(r"[^\d+]", "", phone)
    return phone if len(phone) >= 8 else "Visit Website"

def company_matches_target(company_name, signals):
    name = company_name.lower()
    return any(sig.lower() in name for sig in signals)

# =====================================================
# SIMULATION MODE
# =====================================================

def get_simulation_data(region_key, count):
    rate_limit()
    cfg = REGION_MAP[region_key]

    data = []
    for _ in range(count):
        data.append({
            "Company": f"Simulated {region_key.split()[0]} Corp {random.randint(100,999)}",
            "Location": cfg["gl"].upper(),
            "Decision Maker": random.choice(sum(ROLES_BY_SERVICE.values(), [])),
            "Phone": "+1-800-555-1234",
            "Source Link": "https://www.example.com",
            "Company Class": cfg["class"],
            "Lead Type": "SIMULATED"
        })
    return data

# =====================================================
# GOOGLE SEARCH (COUNTRY ENFORCED)
# =====================================================

def search_google(query, api_key, cx, gl):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cx,
        "q": query,
        "num": 10,
        "gl": gl,
        "hl": "en"
    }

    try:
        res = requests.get(url, params=params)
        data = res.json()

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

def extract_leads(context, region_key, service, api_key, count):
    cfg = REGION_MAP[region_key]

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-pro")

    prompt = f"""
You are a professional data extractor.

OUTPUT FORMAT:
Company Name | Phone Number | Decision Maker Role | Source Link

RULES:
- Do NOT invent phone numbers.
- If missing, write exactly: Visit Website
- Target ONLY {cfg["class"]} companies in {cfg["gl"].upper()}.
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
                if not company_matches_target(parts[0], cfg["signals"]):
                    continue

                phone = normalize_phone(parts[1])

                leads.append({
                    "Company": parts[0],
                    "Phone": phone,
                    "Decision Maker": parts[2],
                    "Source Link": parts[3] if len(parts) > 3 else "N/A",
                    "Location": cfg["gl"].upper(),
                    "Company Class": cfg["class"],
                    "Lead Type": "Phone Verified" if phone != "Visit Website" else "Link Only"
                })

    except Exception as e:
        logging.warning(f"AI extraction failed: {e}")

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
                if not company_matches_target(current_company, cfg["signals"]):
                    continue

                phones = re.findall(r'(\+?\d[\d \-]{8,15})', line)
                phone = normalize_phone(phones[0]) if phones else "Visit Website"

                leads.append({
                    "Company": current_company,
                    "Phone": phone,
                    "Decision Maker": random.choice(ROLES_BY_SERVICE[service]),
                    "Source Link": current_link,
                    "Location": cfg["gl"].upper(),
                    "Company Class": cfg["class"],
                    "Lead Type": "Phone Verified" if phone != "Visit Website" else "Link Only"
                })

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
    region_key = st.selectbox(
        "Target Market (Country + Company Type)",
        REGION_MAP.keys()
    )
with c2:
    service = st.selectbox("Service Pitch", ROLES_BY_SERVICE.keys())
with c3:
    count = st.slider("Lead Count", 5, 10, 5)

# =====================================================
# ACTION
# =====================================================

if st.button("🚀 Generate Leads", type="primary"):

    if mode == "🛠️ Simulation (Test UI)":
        leads = get_simulation_data(region_key, count)
        df = pd.DataFrame(leads)

    else:
        if not API_KEY or not CX_ID:
            st.error("Missing API credentials.")
            st.stop()

        cfg = REGION_MAP[region_key]
        query = f"{cfg['query']} {service}"
        st.write(f"Debug Query: `{query}`")

        with st.status("🔍 Hunting qualified leads...", expanded=True):
            context = search_google(query, API_KEY, CX_ID, cfg["gl"])

            if not context or "API_ERROR" in str(context):
                st.error(context or "No results found.")
                st.stop()

            leads = extract_leads(context, region_key, service, API_KEY, count)
            df = pd.DataFrame(leads)

    if not df.empty:
        st.dataframe(df, use_container_width=True)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False)

        st.download_button(
            "📥 Download Excel",
            buffer.getvalue(),
            file_name="BPO_Qualified_Leads.xlsx"
        )
    else:
        st.warning("No qualified companies matched the target criteria.")
