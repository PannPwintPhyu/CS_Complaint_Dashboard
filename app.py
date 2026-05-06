import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import timedelta

st.set_page_config(page_title="YKKO CS Complaint Dashboard", layout="wide", page_icon="📊")

# ─────────────────────────────────────────────────────────────
# 📁 CLOUD-SAFE DATA LOADER
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Load Complaint Data
    comp_path = os.path.join(base_dir, "CS Complaint Raw.xlsx")
    df_comp = pd.read_excel(comp_path, sheet_name="Sheet1")
    df_comp["Date"] = pd.to_datetime(df_comp["Date"])
    df_comp["Hour"] = df_comp["Timestamp"].apply(lambda x: x.hour if pd.notna(x) else None)
    df_comp["Is_Multi"] = df_comp.apply(
        lambda row: any(pd.notna(row[c]) for c in df_comp.columns if "Main Complaint Category" in c or "Sub Complaint Category" in c) > 1,
        axis=1
    )
    df_comp["Is_High"] = df_comp["Severity"].str.upper() == "HIGH"
    
    # Load Promotion Data
    promo_path = os.path.join(base_dir, "Promotion Set Sales Qty & Amt For YKKO Company Ownership Stores (April-2026).xlsx")
    df_promo = pd.read_excel(promo_path, sheet_name="Summary")
    
    # Load KO Sales Data
    ko_path = os.path.join(base_dir, "KO_KOSi.xlsx")
    df_ko = pd.read_excel(ko_path, sheet_name="Sheet1")
    
    return df_comp, df_promo, df_ko

df_comp, df_promo, df_ko = load_data()

# ─────────────────────────────────────────────────────────────
# 🔍 SIDEBAR FILTERS
# ─────────────────────────────────────────────────────────────
st.sidebar.header("🔍 Filters")
min_d, max_d = df_comp["Date"].min().date(), df_comp["Date"].max().date()
date_range = st.sidebar.date_input("Filter Period", (min_d, max_d), min_value=min_d, max_value=max_d)

region = st.sidebar.selectbox("Region", ["All"] + sorted(df_comp["Region"].dropna().unique()))
shop = st.sidebar.selectbox("Shop", ["All"] + sorted(df_comp["Store Name"].dropna().unique()))
channel = st.sidebar.selectbox("Channel", ["All"] + sorted(df_comp["Channel"].dropna().unique()))
source = st.sidebar.selectbox("Source", ["All"] + sorted(df_comp["Source"].dropna().unique()))

df = df_comp[
    (df_comp["Date"].dt.date >= date_range[0]) & (df_comp["Date"].dt.date <= date_range[1]) &
    (df_comp["Region"] == region if region != "All" else True) &
    (df_comp["Store Name"] == shop if shop != "All" else True) &
    (df_comp["Channel"] == channel if channel != "All" else True) &
    (df_comp["Source"] == source if source != "All" else True)
]

# ─────────────────────────────────────────────────────────────
# 📊 KPIs & SHOP CARDS
# ─────────────────────────────────────────────────────────────
st.title("📊 YKKO Customer Complaint Dashboard")

max_date = df["Date"].max()
today = max_date.normalize()
yesterday = today - timedelta(days=1)
this_week = today - pd.Timedelta(days=today.weekday())
last_week = this_week - pd.Timedelta(weeks=1)
this_month = today.replace(day=1)
last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)

def count_range(start, end):
    return len(df[(df["Date"] >= start) & (df["Date"] < end)])

kpi_cols = st.columns(5)
kpi_cols[0].metric("Today vs Yesterday", f"{count_range(today, today+timedelta(1))} | {count_range(yesterday, yesterday+timedelta(1))}")
kpi_cols[1].metric("Current Week vs Last", f"{count_range(this_week, this_week+timedelta(7))} | {count_range(last_week, last_week+timedelta(7))}")
kpi_cols[2].metric("Current Month vs Last", f"{count_range(this_month, today)} | {count_range(last_month, last_month+timedelta(30))}")
kpi_cols[3].metric("Total Complaints", len(df))
kpi_cols[4].metric("High Severity", int(df["Is_High"].sum()), f"{df['Is_High'].mean():.1%}")

single = int((~df["Is_Multi"]).sum())
multi = int(df["Is_Multi"].sum())
st.markdown(f"🟢 Single Complaints: **{single}** | 🟡 Multi-Complaints: **{multi}**")

shop_counts = df.groupby("Store Name").size().sort_values(ascending=False)
this_month_shops = df[df["Date"].dt.month == today.month].groupby("Store Name").size().sort_values(ascending=False)

shop_cols = st.columns(2)
shop_cols[0].markdown(f"🏪 **Most Complaint Shop This Month**<br>👉 `{this_month_shops.index[0] if len(this_month_shops)>0 else 'N/A'}`<br>📉 `{this_month_shops.iloc[0] if len(this_month_shops)>0 else 0} complaints`", unsafe_allow_html=True)
shop_cols[1].markdown(f"🏆 **All-Time Most Complaint Shop**<br>👉 `{shop_counts.index[0] if len(shop_counts)>0 else 'N/A'}`<br>📉 `{shop_counts.iloc[0] if len(shop_counts)>0 else 0} total complaints`", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# 📈 CHARTS
# ─────────────────────────────────────────────────────────────
st.header("📈 Trend & Volume Analysis")
chart_cols = st.columns(2)

period = chart_cols[0].radio("Time Period", ["Daily", "Weekly", "Monthly"], horizontal=True)
freq = {"Daily": "D", "Weekly": "W", "Monthly": "M"}[period]
trend_df = df.resample(freq, on="Date").size().reset_index(name="Count")
chart_cols[0].plotly_chart(px.line(trend_df, x="Date", y="Count", markers=True), use_container_width=True)

hour_df = df.dropna(subset=["Hour"]).groupby("Hour").size().reset_index(name="Count")
chart_cols[1].plotly_chart(px.bar(hour_df, x="Hour", y="Count", color="Hour", color_continuous_scale=["#1b5e20"]), use_container_width=True)

st.header("📊 Distribution Analysis")
dist_cols = st.columns(3)
dist_cols[0].plotly_chart(px.pie(df["Severity"].value_counts(), hole=0.6, color_discrete_map={"HIGH":"#d32f2f","MED":"#f9a825","LOW":"#4caf50"}), use_container_width=True)
dist_cols[1].plotly_chart(px.bar(df["Channel"].value_counts(), orientation="h", color="index", color_discrete_sequence=["#1b5e20","#f9a825","#7b1fa2"])), use_container_width=True)
dist_cols[2].plotly_chart(px.bar(df["Source"].value_counts().head(10), orientation="h")), use_container_width=True)

st.header("🎯 Category Analysis")
cat_cols = st.columns(2)
cat_cols[0].plotly_chart(px.bar(df["Main Complaint Category"].value_counts().head(10), orientation="h", color="index", color_discrete_sequence=["#1b5e20","#f9a825"])), use_container_width=True)
cat_cols[1].plotly_chart(px.bar(df["Main Complaint Category"].value_counts().head(6), orientation="h", text="value")), use_container_width=True)

st.header("🐛 Foreign Object Analysis")
fo_df = df[df["Main Complaint Category"] == "ForeignObject"]
fo_break = fo_df.groupby("Sub Complaint Category").agg(
    Count=("Sub Complaint Category","count"),
    Stores=("Store Name", lambda x: ", ".join(x.dropna().unique()))
).reset_index()
st.dataframe(fo_break.style.set_properties(**{"text-align":"left"}), use_container_width=True)

st.subheader("📋 Foreign Object Complete List")
st.dataframe(fo_df[["Date","Store Name","Sub Complaint Category","Severity","Customer Feedback"]].dropna(subset=["Sub Complaint Category"]).sort_values("Date", ascending=False), use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────────────────────
# 💡 PROMOTION & KO INSIGHTS (Optional Tabs)
# ─────────────────────────────────────────────────────────────
st.header("📈 Sales & Promotion Insights")
tab1, tab2 = st.tabs(["🎁 Promotion Performance", "🍜 KO Product Rankings"])
with tab1:
    st.dataframe(df_promo, use_container_width=True)
with tab2:
    st.dataframe(df_ko.sort_values("2026 Jan ~ 20-Apr-2026", ascending=False), use_container_width=True)