# =====================================================
# BPO LeadGen Pro – Intelligence Edition
# Market Cap + Startup Verification
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

st.set_page_config(page_title="BPO LeadGen Pro", page_icon="💼", layout="wide")
logging.basicConfig(level=logging.INFO)

# =====================================================
# TARGET CONFIG
# =====================================================

MIN_MARKET_CAP = 1_000_000_000  # $1B minimum for listed companies

REGION_MAP = {
    "UK – Startups": {"gl": "uk", "class": "Startup"},
    "UK – Top Priced Companies": {"gl": "uk", "class": "Listed Enterprise"},
    "USA – Startups": {"gl": "us", "class": "Startup"},
    "USA – Top Priced Companies": {"gl": "us", "class": "Listed Enterprise"},
    "India – Startups": {"gl": "in", "class": "Startup"},
    "India – Top Priced Companies": {"gl": "in", "class": "Listed Enterprise"},
}

STARTUP_KEYWORDS = [
    "startup", "venture", "seed", "series", "early stage",
    "privately held", "bootstrapped"
]

ROLES_BY_SERVICE = {
    "Hiring": ["HR Manager", "Head of Talent"],
    "Customer Support": ["Head of Operations"],
    "Sourcing": ["Procurement Head"]
}

# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:
    st.header("⚙️ Configuration")
    mode = st.radio("Mode", ["🌐 Real Google Search", "🛠️ Simulation"], index=0)

    if mode == "🌐 Real Google Search":
        API_KEY = st.secrets.get("GOOGLE_API_KEY")
        CX_ID = st.secrets.get("SEARCH_ENGINE_ID")

# =====================================================
# UTILITIES
# =====================================================

def rate_limit():
    time.sleep(random.uniform(0.8, 1.5))

def normalize_phone(phone):
    phone = re.sub(r"[^\d+]", "", phone)
    return phone if len(phone) >= 8 else "Visit Website"

# =====================================================
# MARKET CAP VALIDATION (YAHOO FINANCE)
# =====================================================

def get_market_cap(company):
    try:
        url = "https://query1.finance.yahoo.com/v1/finance/search"
        params = {"q": company, "quotesCount": 1, "newsCount": 0}
        res = requests.get(url, params=params, timeout=5)
        data = res.json()

        if not data.get("quotes"):
            return None

        quote = data["quotes"][0]
        market_cap = quote.get("marketCap")
        symbol = quote.get("symbol")

        return market_cap, symbol
    except Exception:
        return None

# =====================================================
# STARTUP VERIFICATION (CRUNCHBASE-STYLE)
# =====================================================

def is_startup(company_name, snippet):
    name = company_name.lower()
    text = snippet.lower()

    if any(k in text for k in STARTUP_KEYWORDS):
        return True

    if any(s in name for s in ["pvt", "private", "llp"]):
        return True

    return False

# =====================================================
# GOOGLE SEARCH
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

    res = requests.get(url, params=params)
    data = res.json()

    if "items" not in data:
        return None

    blocks = []
    for item in data["items"]:
        blocks.append(
            f"Company: {item['title']}\n"
            f"Snippet: {item.get('snippet','')}\n"
            f"URL: {item['link']}"
        )

    rate_limit()
    return blocks

# =====================================================
# EXTRACTION + VALIDATION
# =====================================================

def process_results(results, region_key, service, count):
    cfg = REGION_MAP[region_key]
    leads = []

    for block in results:
        lines = block.split("\n")
        company = lines[0].replace("Company:", "").strip()
        snippet = lines[1]
        url = lines[2].replace("URL:", "").strip()

        phone_matches = re.findall(r'(\+?\d[\d \-]{8,15})', block)
        phone = normalize_phone(phone_matches[0]) if phone_matches else "Visit Website"

        # ---------- STARTUP MODE ----------
        if cfg["class"] == "Startup":
            if not is_startup(company, snippet):
                continue

            leads.append({
                "Company": company,
                "Phone": phone,
                "Decision Maker": random.choice(ROLES_BY_SERVICE[service]),
                "Source Link": url,
                "Company Stage": "Startup",
                "Market Cap (USD)": "Private",
                "Validation Source": "Heuristic",
                "Lead Confidence": "High" if phone != "Visit Website" else "Medium"
            })

        # ---------- LISTED MODE ----------
        else:
            market_data = get_market_cap(company)
            if not market_data:
                continue

            market_cap, symbol = market_data
            if not market_cap or market_cap < MIN_MARKET_CAP:
                continue

            leads.append({
                "Company": company,
                "Phone": phone,
                "Decision Maker": random.choice(ROLES_BY_SERVICE[service]),
                "Source Link": url,
                "Company Stage": "Listed Enterprise",
                "Market Cap (USD)": market_cap,
                "Validation Source": f"Yahoo Finance ({symbol})",
                "Lead Confidence": "High" if phone != "Visit Website" else "Medium"
            })

        if len(leads) >= count:
            break

    return leads

# =====================================================
# UI
# =====================================================

st.title("🛡️ BPO LeadGen Pro – Intelligence Edition")
st.caption("Startup & Market-Cap validated business leads")

c1, c2, c3 = st.columns(3)
with c1:
    region_key = st.selectbox("Target Market", REGION_MAP.keys())
with c2:
    service = st.selectbox("Service Pitch", ROLES_BY_SERVICE.keys())
with c3:
    count = st.slider("Lead Count", 5, 10, 5)

# =====================================================
# RUN
# =====================================================

if st.button("🚀 Generate Leads", type="primary"):

    if mode == "🛠️ Simulation":
        st.info("Simulation mode active.")
        st.stop()

    if not API_KEY or not CX_ID:
        st.error("Missing API credentials.")
        st.stop()

    query = f"{region_key.split('–')[0]} company headquarters contact {service}"
    st.write(f"Debug Query: `{query}`")

    with st.status("🔍 Validating company intelligence...", expanded=True):
        results = search_google(query, API_KEY, CX_ID, REGION_MAP[region_key]["gl"])

        if not results:
            st.error("No results found.")
            st.stop()

        leads = process_results(results, region_key, service, count)
        df = pd.DataFrame(leads)

    if df.empty:
        st.warning("No companies passed validation.")
    else:
        st.dataframe(df, use_container_width=True)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False)

        st.download_button("📥 Download Excel", buffer.getvalue(), "Validated_BPO_Leads.xlsx")
