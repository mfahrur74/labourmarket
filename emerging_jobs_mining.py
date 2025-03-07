import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import re
from PIL import Image



# File uploader
uploaded_file = st.file_uploader(r"/Users/pksstaff/Desktop/SQL Backup/dm_vacancy.csv", type=['csv'])

if uploaded_file:
    file_path = "/mnt/data/dm_vacancy.csv"  # Save file in Streamlit Cloud
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.success(f"File successfully uploaded to {file_path}")

    # Load CSV
    df = pd.read_csv(file_path)
    st.dataframe(df)
else:
    st.warning("Please upload a CSV file.")

# Set CSV file path
csv_file = st.secrets["DATA_PATH"]

# Function to clean and process data
def process_data(role, keywords):
    # Read the CSV file
    dv = pd.read_csv(csv_file, low_memory=False, dtype={'mvf_job_desc': str}, on_bad_lines='skip')

    # Prepare keywords
    keywords_list = [keyword.strip() for keyword in keywords.split(",")]
    pattern = " | ".join(keywords_list)

    # Data preprocessing
    df = dv.fillna('')
    df = df[['mvf_start_dt', 'mvf_position_title', 'mvf_job_desc', 'mvf_occp_name', 'mvf_esco',
             'mvf_position_open_qty', 'mvf_msic1d_name', 'mvf_msic1d_cd', 'mvf_vac_city', 'mvf_vac_state']]
    df = df.map(lambda x: x.lower() if isinstance(x, str) else x)
    df = df.drop_duplicates(subset=['mvf_job_desc', 'mvf_esco'])
    df['major'] = df['mvf_esco'].astype(str).str[0:1]
    df['mvf_start_dt'] = pd.to_datetime(df['mvf_start_dt'], errors='coerce')
    df['year_month'] = df['mvf_start_dt'].dt.strftime("%Y-%m")
    
    df = df.loc[(df['mvf_start_dt']>=pd.to_datetime(start_date)) & (df['mvf_start_dt']<=pd.to_datetime(end_date))]

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

    # Clean data
    pt['date'] = pd.to_datetime(pt['year_month'], format='%Y-%m')
    pt['mvf_position_open_qty'] = pd.to_numeric(pt['mvf_position_open_qty'], errors='coerce').fillna(0)
    #pt['major'] = pd.to_numeric(pt['major'], errors='coerce')
    #pt['major'] = pt.loc[(pt['major']!=8) | (pt['major']!=9)]

    return pt


# Load the JPK logo
#logo_path = r'/Users/pksstaff/Desktop/jpk_analysis.png'  # Update with correct path if needed
logo_path = 'jpk_analysis.png'

st.image(logo_path, width=400)  # Adjust width as needed

# Streamlit UI
st.title("📊 Emerging Jobs Vacancy Analysis")

from io import BytesIO

# Load data
dt = pd.read_excel('emerging_jobs.xlsx')

# Convert to Excel
@st.cache_data
def to_excel(df):
    output = BytesIO()
    df.to_excel(output, index=False, sheet_name='Emerging Jobs', engine='xlsxwriter')
    return output.getvalue()

# Download button
st.download_button("📥 Download Emerging Jobs", to_excel(dt), "emerging_jobs.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# Dropdown for Job Role Selection
role = st.selectbox("Select Job Role", dt['Job Role'].unique())

# Display Corresponding Keywords & Job Description
filtered_data = dt[dt['Job Role'] == role]
keywords = filtered_data['Relevant Keywords'].values[0]

#st.write(f"**Keywords:** {filtered_data['Relevant Keywords'].values[0]}")


# User inputs
#role = st.text_input("Enter Job Role", role)
keywords = st.text_area("Enter Keywords (comma-separated)", keywords)
st.write(f"**Job Description:** {filtered_data['Job Description'].values[0]} \n")

# Date input for start and end date
start_date = st.date_input("Select Start Date (from last two years)", date.today().replace(day=1) - relativedelta(years=2))
end_date = st.date_input("Select End Date (to last day of last month)", date.today().replace(day=1) - relativedelta(days=1))

st.write(f"Filtering data from {start_date} to {end_date}")

# Process button
if st.button("🔍 Analyze Data"):
    with st.spinner("Processing data..."):
        processed_data = process_data(role, keywords)
        
        # Display data
        st.success("✅ Data processing complete!")

        # Download button
        excel_file = "emerging_job_analysis.xlsx"
        processed_data.to_excel(excel_file, index=False)
        with open(excel_file, "rb") as f:
            st.download_button("📥 Download Excel", f, file_name=excel_file)
            
        # Display total vacancies
        total_vacancies = processed_data['mvf_position_open_qty'].sum()
        st.metric(label="📌 Total Job Vacancies", value=f"{int(total_vacancies):,}")

        # Line chart
        st.subheader("📈 Job Vacancy Trend Over Time \n")

        # Aggregate vacancies by date
        pt1 = processed_data.pivot_table(index='date', values='mvf_position_open_qty', aggfunc='sum').reset_index()

        # Create figure and axis
        fig, ax = plt.subplots(figsize=(12, 6))
        fig.patch.set_facecolor('white')  # White background outside plot

        # Plot line chart using Matplotlib
        ax.plot(pt1['date'], pt1['mvf_position_open_qty'], marker='o', color='#007ACC', linewidth=2, linestyle='-')

        # Light gray background
        ax.set_facecolor("#F5F5F5")

        # Add data labels
        for i, row in pt1.iterrows():
            ax.text(row['date'], row['mvf_position_open_qty'] + 10, f"{int(row['mvf_position_open_qty']):,}",
                    color='black', fontsize=10, ha='center')

        # Dotted gridlines
        ax.grid(color='gray', linestyle='dotted', linewidth=0.7)

        # Labels and title
        ax.set_xlabel("Date", fontsize=12, fontweight='bold')
        ax.set_ylabel("Job Vacancies", fontsize=12, fontweight='bold')
        ax.set_title("Job Vacancy Trend Over Time\n", fontsize=14, fontweight='bold')

        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45, ha='right')

        # Show plot in Streamlit
        st.pyplot(fig)

        # Top occupations table
        st.subheader("\n\n🏆 Top 20 Occupations by Vacancies")
        pt2 = processed_data.pivot_table(index=['mvf_occp_name', 'major'],
                                         values='mvf_position_open_qty',
                                         aggfunc='sum').sort_values(by='mvf_position_open_qty', ascending=False)[:20].reset_index()
        pt2.columns = ['Occupation','Group','Open Positions']
        pt2[['Occupation', 'Group']] = pt2[['Occupation', 'Group']].apply(lambda x: x.str.title())
        st.dataframe(pt2)

        # Top locations table
        st.subheader("\n🌍 Top 20 Locations by Vacancies")
        pt3 = processed_data.pivot_table(index=['mvf_vac_state', 'mvf_vac_city'],
                                         values='mvf_position_open_qty',
                                         aggfunc='sum').sort_values(by='mvf_position_open_qty', ascending=False)[:20].reset_index()
        pt3.columns = ['State','City','Open Positions']
        pt3[['State', 'City']] = pt3[['State', 'City']].apply(lambda x: x.str.title())
        st.dataframe(pt3)
        
        # Top Industries table
        st.subheader("\n🏭 Top 20 Industries by Vacancies")
        pt4 = processed_data.pivot_table(index=['mvf_msic1d_cd','mvf_msic1d_name'],
                             values='mvf_position_open_qty',
                             aggfunc='sum').sort_values(by='mvf_position_open_qty', ascending=False)[:20].reset_index()
        pt4.columns = ['MSIC Code','MSIC Name','Open Positions']
        pt4[['MSIC Code', 'MSIC Name']] = pt4[['MSIC Code', 'MSIC Name']].apply(lambda x: x.str.title())
        st.dataframe(pt4)
