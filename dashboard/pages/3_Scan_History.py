import pandas as pd
import streamlit as st

from api_client import APIError, get, post

st.set_page_config(page_title="Scan history · Screener", page_icon="🕒", layout="wide")
st.title("🕒 Scan history")

if st.button("Run a scan now", type="primary"):
    try:
        post("/api/scans/run")
        st.success("Scan accepted. Refresh shortly to see its results.")
    except APIError as exc:
        st.warning(str(exc))

try:
    scans = get("/api/scans", limit=500)
except APIError as exc:
    st.error(str(exc))
    st.stop()

if not scans:
    st.info("No scans have run yet.")
else:
    frame = pd.DataFrame(scans)
    st.dataframe(
        frame[
            [
                "started_at",
                "finished_at",
                "status",
                "discovered_count",
                "processed_count",
                "qualified_count",
                "alerted_count",
                "error",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )

