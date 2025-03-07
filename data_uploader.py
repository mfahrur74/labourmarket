import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import re
from io import BytesIO

# Streamlit UI
st.title("📊 Emerging Jobs Vacancy Analysis")

# File uploader
uploaded_file = st.file_uploader("Upload file", type=['csv'])

if uploaded_file:
    df = pd.read_csv(uploaded_file, low_memory=False, dtype={'mvf_job_desc': str}, on_bad_lines='skip')
    st.success("✅ File uploaded successfully!")
    st.dataframe(df)  # Display uploaded data
else:
    st.warning("Please upload a CSV file.")
