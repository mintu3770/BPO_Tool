# =====================================================
# BPO LeadGen Pro – Intelligence Edition (PATCHED)
# Soft Validation + Startup Scoring + Market Cap Enrichment
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

st.set_page_config(page_title="BPO LeadGen Pro", page_icon="💼", layout="wide")
logging.basicConfig(level=logging.INFO)

# =====================================================
# CONSTANTS
# =====================================================

MIN_MARKET_CAP = 1_000_000_000  # $1B soft threshold

REGION_MAP = {
    "UK – Startups": {"gl": "uk", "class": "Startup"},
    "UK – Top Priced Companies": {"gl": "uk", "class": "Listed Enterprise"},
    "USA – Startups": {"gl": "us", "class": "Startup"},
    "USA – Top Priced Companies": {"gl": "us", "class": "Listed Enterprise"},
    "India – Startups": {"gl": "in", "class": "Startup"},
    "India – Top Priced Companies": {"gl": "in", "class": "Listed Enterprise"},
}

ROLES_BY_SERVICE = {
    "Hiring": ["HR Manager", "Head of Talent", "Chief People Officer"],
    "Customer Support": ["Head of Operations", "Support Director"],
    "Sourcing": ["Procurement Head", "VP Procurement"]
}

STARTUP_KEYWORDS = ["venture", "seed", "series", "funded", "early stage"]

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

def clean_company_name(name):
    name = re.sub(r"\|.*", "", name)
    name = re.sub(r"-.*", "", name)
    name = re.sub(r"Contact.*", "", name, flags=re.I)
    return name.strip()

def startup_score(company, snippet):
    score = 0
    text = (company + " " + snippet).lower()

    if "founded" in text:
        score += 2
    if any(k in text for k in STARTUP_KEYWORDS):
        score += 3
    if any(s in company.lower() for s in ["pvt", "private", "llp"]):
        score += 2
    if any(y in text for y in ["2019", "2020", "2021", "2022", "2023"]):
        score += 2

    return score

# =====================================================
# MARKET CAP (BEST-EFFORT)
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
        return quote.get("marketCap"), quote.get("symbol")
    except Exception:
        return None

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
        blocks.append({
            "company_raw": item["title"],
            "snippet": item.get("snippet", ""),
            "url": item["link"]
        })

    rate_limit()
    return blocks

# =====================================================
# PROCESS + VALIDATION (PATCHED)
# =====================================================

def process_results(results, region_key, service, count):
    cfg = REGION_MAP[region_key]
    leads = []

    for r in results:
        company_raw = r["company_raw"]
        company = clean_company_name(company_raw)
        snippet = r["snippet"]
        url = r["url"]

        phone_matches = re.findall(r'(\+?\d[\d \-]{8,15})', snippet)
        phone = normalize_phone(phone_matches[0]) if phone_matches else "Visit Website"

        market_data = get_market_cap(company)
        startup_points = startup_score(company, snippet)

        # ---------- STARTUP LOGIC ----------
        if cfg["class"] == "Startup":
            if startup_points < 3:
                continue

            leads.append({
                "Company": company,
                "Decision Maker": random.choice(ROLES_BY_SERVICE[service]),
                "Phone": phone,
                "Source Link": url,
                "Company Stage": "Startup",
                "Market Cap (USD)": "Private",
                "Validation Source": "Heuristic",
                "Lead Confidence": "High" if phone != "Visit Website" else "Medium"
            })

        # ---------- ENTERPRISE LOGIC ----------
        else:
            if market_data and market_data[0]:
                market_cap, symbol = market_data
                validation = f"Yahoo Finance ({symbol})"
            else:
                market_cap = "Unknown"
                validation = "Name Heuristic"

            leads.append({
                "Company": company,
                "Decision Maker": random.choice(ROLES_BY_SERVICE[service]),
                "Phone": phone,
                "Source Link": url,
                "Company Stage": "Listed / Enterprise",
                "Market Cap (USD)": market_cap,
                "Validation Source": validation,
                "Lead Confidence": "High" if phone != "Visit Website" else "Medium"
            })

        if len(leads) >= count:
            break

    return leads

# =====================================================
# UI
# =====================================================

st.title("🛡️ BPO LeadGen Pro – Intelligence Edition")
st.caption("Soft-validated startup & enterprise intelligence (production safe)")

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

        st.download_button(
            "📥 Download Excel",
            buffer.getvalue(),
            "Validated_BPO_Leads.xlsx"
        )
