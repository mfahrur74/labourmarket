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
uploaded_file = st.file_uploader("Upload CSV File", type=['csv'])

if uploaded_file:
    df = pd.read_csv(uploaded_file, low_memory=False, dtype={'mvf_job_desc': str}, on_bad_lines='skip')
    st.success("✅ File uploaded successfully!")
    st.dataframe(df)  # Display uploaded data
else:
    st.warning("Please upload a CSV file.")

# Load data from Excel
@st.cache_data
def load_excel():
    return pd.read_excel("emerging_jobs.xlsx")

dt = load_excel()

# Convert DataFrame to Excel
@st.cache_data
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Emerging Jobs')
    return output.getvalue()

# Download button
st.download_button(
    "📥 Download Emerging Jobs",
    to_excel(dt),
    "emerging_jobs.xlsx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# Dropdown for Job Role Selection
role = st.selectbox("Select Job Role", dt['Job Role'].unique())

# Display Corresponding Keywords & Job Description
filtered_data = dt[dt['Job Role'] == role]
keywords = filtered_data['Relevant Keywords'].values[0]

# User inputs
keywords = st.text_area("Enter Keywords (comma-separated)", keywords)
st.write(f"**Job Description:** {filtered_data['Job Description'].values[0]} \n")

# Date selection
start_date = st.date_input("Select Start Date (Last 2 Years)", date.today().replace(day=1) - relativedelta(years=2))
end_date = st.date_input("Select End Date (Last Month)", date.today().replace(day=1) - relativedelta(days=1))
st.write(f"Filtering data from {start_date} to {end_date}")

# Function to clean and process data
def process_data(df, role, keywords, start_date, end_date):
    if df is None:
        st.error("No data available. Please upload a file.")
        return None

    keywords_list = [keyword.strip() for keyword in keywords.split(",")]
    pattern = " | ".join(keywords_list)

    # Data preprocessing
    df = df.fillna('')
    df = df[['mvf_start_dt', 'mvf_position_title', 'mvf_job_desc', 'mvf_occp_name', 'mvf_esco',
             'mvf_position_open_qty', 'mvf_msic1d_name', 'mvf_msic1d_cd', 'mvf_vac_city', 'mvf_vac_state']]
    
    df = df.map(lambda x: x.lower() if isinstance(x, str) else x)
    df = df.drop_duplicates(subset=['mvf_job_desc', 'mvf_esco'])
    df['major'] = df['mvf_esco'].astype(str).str[0:1]
    df['mvf_start_dt'] = pd.to_datetime(df['mvf_start_dt'], errors='coerce')
    df['year_month'] = df['mvf_start_dt'].dt.strftime("%Y-%m")

    df = df.loc[(df['mvf_start_dt'] >= pd.to_datetime(start_date)) & (df['mvf_start_dt'] <= pd.to_datetime(end_date))]

    # Filter by keywords
    df = df.loc[df['mvf_job_desc'].str.contains(pattern, flags=re.IGNORECASE, regex=True)]
    df['keyword'] = ', '.join(keywords_list)
    df['job_role'] = role

    # Pivot table
    pt = df.pivot_table(index=['year_month', 'job_role', 'mvf_position_title', 'mvf_esco', 'mvf_occp_name',
                               'mvf_job_desc', 'major', 'mvf_msic1d_name', 'mvf_msic1d_cd', 'mvf_vac_city',
                               'mvf_vac_state', 'keyword'],
                        values='mvf_position_open_qty',
                        aggfunc='sum').reset_index()

    pt['date'] = pd.to_datetime(pt['year_month'], format='%Y-%m')
    pt['mvf_position_open_qty'] = pd.to_numeric(pt['mvf_position_open_qty'], errors='coerce').fillna(0)

    return pt

# Process button
if st.button("🔍 Analyze Data"):
    if uploaded_file:
        with st.spinner("Processing data..."):
            processed_data = process_data(df, role, keywords, start_date, end_date)
            if processed_data is not None:
                st.success("✅ Data processing complete!")

                # Download button
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    processed_data.to_excel(writer, index=False, sheet_name='Analysis')
                st.download_button("📥 Download Excel", output.getvalue(), "emerging_job_analysis.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

                # Display total vacancies
                total_vacancies = processed_data['mvf_position_open_qty'].sum()
                st.metric(label="📌 Total Job Vacancies", value=f"{int(total_vacancies):,}")

                # Line chart
                st.subheader("📈 Job Vacancy Trend Over Time")
                pt1 = processed_data.pivot_table(index='date', values='mvf_position_open_qty', aggfunc='sum').reset_index()

                fig, ax = plt.subplots(figsize=(12, 6))
                ax.plot(pt1['date'], pt1['mvf_position_open_qty'], marker='o', color='#007ACC', linewidth=2, linestyle='-')
                ax.set_facecolor("#F5F5F5")
                ax.grid(color='gray', linestyle='dotted', linewidth=0.7)
                ax.set_xlabel("Date", fontsize=12, fontweight='bold')
                ax.set_ylabel("Job Vacancies", fontsize=12, fontweight='bold')
                ax.set_title("Job Vacancy Trend Over Time\n", fontsize=14, fontweight='bold')
                plt.xticks(rotation=45, ha='right')
                st.pyplot(fig)

                # Top occupations
                st.subheader("🏆 Top 20 Occupations by Vacancies")
                pt2 = processed_data.pivot_table(index=['mvf_occp_name', 'major'], values='mvf_position_open_qty', aggfunc='sum').sort_values(by='mvf_position_open_qty', ascending=False)[:20].reset_index()
                pt2.columns = ['Occupation', 'Group', 'Open Positions']
                st.dataframe(pt2)

                # Top locations
                st.subheader("🌍 Top 20 Locations by Vacancies")
                pt3 = processed_data.pivot_table(index=['mvf_vac_state', 'mvf_vac_city'], values='mvf_position_open_qty', aggfunc='sum').sort_values(by='mvf_position_open_qty', ascending=False)[:20].reset_index()
                pt3.columns = ['State', 'City', 'Open Positions']
                st.dataframe(pt3)

                # Top Industries table
                st.subheader("\n🏭 Top 20 Industries by Vacancies")
                pt4 = processed_data.pivot_table(index=['mvf_msic1d_cd','mvf_msic1d_name'],
                                     values='mvf_position_open_qty',
                                     aggfunc='sum').sort_values(by='mvf_position_open_qty', ascending=False)[:20].reset_index()
                pt4.columns = ['MSIC Code','MSIC Name','Open Positions']
                pt4[['MSIC Code', 'MSIC Name']] = pt4[['MSIC Code', 'MSIC Name']].apply(lambda x: x.str.title())
                st.dataframe(pt4)

    else:
        st.error("⚠ Please upload a CSV file first.")
