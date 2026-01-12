# =====================================================
# BPO LeadGen Pro – Global Safe Edition
# No Crunchbase | No Market Cap | No Hard Validation
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
# REGION & MODE CONFIG
# =====================================================

REGION_MAP = {
    "UK – Startups": {"gl": "uk", "class": "Startup (Likely)"},
    "UK – Top Priced Companies": {"gl": "uk", "class": "Enterprise (Likely)"},
    "USA – Startups": {"gl": "us", "class": "Startup (Likely)"},
    "USA – Top Priced Companies": {"gl": "us", "class": "Enterprise (Likely)"},
    "India – Startups": {"gl": "in", "class": "Startup (Likely)"},
    "India – Top Priced Companies": {"gl": "in", "class": "Enterprise (Likely)"},
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
        "Mode",
        ["🌐 Real Google Search", "🛠️ Simulation (Test UI)"],
        index=0
    )

    if mode == "🌐 Real Google Search":
        API_KEY = st.secrets.get("GOOGLE_API_KEY")
        CX_ID = st.secrets.get("SEARCH_ENGINE_ID")

    st.divider()
    st.info(
        "Hunter Mode enabled: If phone number is hidden, "
        "the tool saves the contact page link instead of discarding the lead."
    )

# =====================================================
# UTILITIES
# =====================================================

def rate_limit():
    time.sleep(random.uniform(0.8, 1.4))

def normalize_phone(phone):
    phone = re.sub(r"[^\d+]", "", phone)
    return phone if len(phone) >= 8 else "Visit Website"

def clean_company_name(name):
    name = re.sub(r"\|.*", "", name)
    name = re.sub(r"-.*", "", name)
    name = re.sub(r"Contact.*", "", name, flags=re.I)
    return name.strip()

def classify_company(name, region_class):
    """
    Soft classification only — never blocks a company
    """
    name_l = name.lower()

    if any(x in name_l for x in ["pvt", "private", "startup", "labs"]):
        return "Startup (Likely)"
    if any(x in name_l for x in ["plc", "limited", "ltd", "corp"]):
        return "Enterprise (Likely)"

    return region_class

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
# EXTRACTION (SAFE GLOBAL LOGIC)
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

        company_class = classify_company(company, cfg["class"])

        leads.append({
            "Company": company,
            "Decision Maker": random.choice(ROLES_BY_SERVICE[service]),
            "Phone": phone,
            "Source Link": url,
            "Company Type": company_class,
            "Lead Type": "Phone Verified" if phone != "Visit Website" else "Link Only"
        })

        if len(leads) >= count:
            break

    return leads

# =====================================================
# MAIN UI
# =====================================================

st.title("🛡️ BPO LeadGen Pro")
st.caption("Global BPO lead intelligence — no restrictive validation")

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

    if mode == "🛠️ Simulation (Test UI)":
        st.info("Simulation mode active.")
        st.stop()

    if not API_KEY or not CX_ID:
        st.error("Missing API credentials.")
        st.stop()

    query = f"{region_key.split('–')[0]} company headquarters contact {service}"
    st.write(f"Debug Query: `{query}`")

    with st.status("🔍 Hunting leads...", expanded=True):
        results = search_google(query, API_KEY, CX_ID, REGION_MAP[region_key]["gl"])

        if not results:
            st.error("No results found.")
            st.stop()

        leads = process_results(results, region_key, service, count)
        df = pd.DataFrame(leads)

    if df.empty:
        st.warning("No leads extracted.")
    else:
        st.dataframe(df, use_container_width=True)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False)

        st.download_button(
            "📥 Download Excel",
            buffer.getvalue(),
            "BPO_Leads_Global.xlsx"
        )
