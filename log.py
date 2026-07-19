import streamlit as st
import pandas as pd
from datetime import datetime

# --- Theme Configuration & Injected Premium Glassmorphism Background Style ---
st.set_page_config(
    page_title="AILYN HOUSE - Construction & Payroll Planner | Project Management",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'About': "🏗️ AILYN HOUSE Advanced Project & Payroll Planner v30000 - Professional Construction Management"
    }
)

# SEO Meta Tags for Search Engines
st.markdown("""
    <meta name="description" content="Advanced construction project management and payroll planning system with receipt tracking, financial dashboard, and organized ledger views.">
    <meta name="keywords" content="construction management, project planning, receipt tracking, payroll, financial dashboard, building planner, project ledger">
    <meta name="author" content="Ailyn House Development Team">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta property="og:title" content="AILYN HOUSE - Construction & Payroll Planner">
    <meta property="og:description" content="Professional construction project management platform with advanced receipt tracking and financial analytics.">
    <meta property="og:type" content="website">
    <meta property="og:image" content="https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=80">
    <meta name="theme-color" content="#22c55e">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="https://ailyn-house-planner.streamlit.app">
""", unsafe_allow_html=True)

# Custom UI CSS to replicate the screenshot background, blur filter, and container layout
st.markdown("""
    <style>
    /* Global Background Image with Dark Overlay and Blur */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background: linear-gradient(rgba(10, 25, 20, 0.75), rgba(10, 25, 20, 0.75)), 
                    url('https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1920&q=80') no-repeat center center fixed;
        background-size: cover;
        font-family: 'Inter', sans-serif;
        color: #ffffff;
    }

    /* Target the main view block wrapper */
    [data-testid="stMainBlockContainer"] {
        background: rgba(6, 35, 25, 0.4);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        padding: 40px !important;
        border-radius: 20px;
        margin-top: 20px;
        margin-bottom: 20px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }

    /* Custom Header Container from your Image */
    .glass-header {
        text-align: center;
        margin-bottom: 40px;
        padding-bottom: 10px;
    }
    
    .glass-header h1 {
        color: #22c55e !important; /* Vibrant Emerald Green Title */
        font-size: 2.3rem !important;
        font-weight: 700 !important;
        letter-spacing: 1.5px;
        margin: 0;
        text-transform: uppercase;
    }
    
    .glass-header p {
        color: #a7f3d0 !important; /* Soft Sage text */
        font-weight: 500;
        margin-top: 8px;
        font-size: 0.9rem;
    }

    /* Text elements inside forms, tabs and widgets */
    h2, h3, label, .stWidgetLabel p, .stSubheader {
        color: #22c55e !important;
        font-weight: 600 !important;
    }

    /* Quick Stats Receipt Cards styling exactly like the screenshot */
    .stat-card-container {
        display: flex;
        gap: 20px;
        margin-bottom: 25px;
    }

    .stat-card {
        flex: 1;
        background: rgba(6, 25, 18, 0.6);
        border: 1px solid rgba(34, 197, 94, 0.2);
        padding: 20px;
        border-radius: 12px;
    }

    .stat-card .label {
        font-size: 0.75rem;
        color: #22c55e;
        text-transform: uppercase;
        font-weight: bold;
        letter-spacing: 0.5px;
        margin-bottom: 5px;
    }

    .stat-card .value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #ffffff;
    }

    /* Input Fields Custom Dark Translucent Styling */
    div[data-baseweb="input"], div[data-baseweb="select"], div[data-baseweb="textarea"] {
        background-color: rgba(10, 35, 25, 0.6) !important;
        border: 1px solid rgba(34, 197, 94, 0.3) !important;
        border-radius: 8px !important;
    }
    
    input, textarea, div[data-baseweb="select"] {
        color: #ffffff !important;
    }

    /* Navigation Menu Buttons override */
    div.stButton > button {
        background-color: rgba(10, 45, 30, 0.7) !important;
        color: #22c55e !important;
        border: 1px solid rgba(34, 197, 94, 0.4) !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 12px 24px !important;
        transition: all 0.3s ease !important;
    }
    div.stButton > button:hover {
        background-color: #047857 !important;
        color: white !important;
        box-shadow: 0 0 15px rgba(34, 197, 94, 0.4) !important;
    }

    /* Cleaned Dataframe Styles for dark theme balance */
    .stDataFrame {
        background-color: rgba(6, 25, 18, 0.6) !important;
        border-radius: 12px;
        padding: 10px;
        border: 1px solid rgba(255,255,255,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# --- Session State Data Container Initialisation ---
if "tasks_df" not in st.session_state:
    st.session_state.tasks_df = pd.DataFrame(
        columns=["Date", "Month", "Year", "Day of Week", "Week Number", "Receipt No", "Vendor", "Amount", "Description of Work"]
    )
if "current_page" not in st.session_state:
    st.session_state.current_page = "dashboard"

# --- Dynamic Title Header matching screenshot structural accents ---
st.markdown("""
    <div class="glass-header">
        <h1>🏗️ AILYN HOUSE PROJECT & PAYROLL PLANNER</h1>
        <p>Combined System | Mobile Operating Engine v30000</p>
    </div>
""", unsafe_allow_html=True)

# --- Two-Button Page Navigation Menu ---
col_nav1, col_nav2 = st.columns(2)
with col_nav1:
    if st.button("📊 INPUT DASHBOARD", use_container_width=True):
        st.session_state.current_page = "dashboard"
with col_nav2:
    if st.button("📑 ORGANISED PROJECT LEDGER", use_container_width=True):
        st.session_state.current_page = "ledger"

st.markdown("<br>", unsafe_allow_html=True)

# ----------------- PAGE 1: INPUT DASHBOARD -----------------
if st.session_state.current_page == "dashboard":
    st.subheader("📋 Advanced Activity & Receipt Entry")
    
    with st.form("construction_form", clear_on_submit=True):
        # 1. Date Inputs Stacked
        day = st.number_input("Day", min_value=1, max_value=31, value=datetime.now().day)
        
        month_list = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        current_month_idx = datetime.now().month - 1
        month = st.selectbox("Month", options=month_list, index=current_month_idx)
        
        year = st.number_input("Year", min_value=2020, max_value=2035, value=datetime.now().year)
        
        st.markdown("<hr style='border: 0.5px solid rgba(34, 197, 94, 0.2)'>", unsafe_allow_html=True)
        st.write("🧾 Receipt Tracking Details (Optional)")
        
        # 2. Receipt Tracker Upgrades
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            receipt_no = st.text_input("Receipt / Invoice Number", placeholder="e.g. OR-10234")
        with col_r2:
            vendor = st.text_input("Vendor / Store Name", placeholder="e.g. Citi Hardware")
        with col_r3:
            amount = st.number_input("Total Receipt Amount (PHP)", min_value=0.0, step=50.0, value=0.0)
            
        st.markdown("<hr style='border: 0.5px solid rgba(34, 197, 94, 0.2)'>", unsafe_allow_html=True)
        
        # 3. Description Field Below
        desc = st.text_area("Description of Structural/Material Work", placeholder="Specify masonry details, item descriptions, quantities...")
        
        submit_btn = st.form_submit_button("Secure Log Into Ledger")
        
        if submit_btn:
            if desc.strip() == "":
                st.error("Submission blocked. Please input execution details.")
            else:
                try:
                    month_num = month_list.index(month) + 1
                    date_obj = datetime(year, month_num, day)
                    day_name = date_obj.strftime("%A")
                    formatted_date = f"{day:02d}"
                    week_num = f"Week {date_obj.strftime('%U')} ({year})"
                    
                    new_row = {
                        "Date": formatted_date,
                        "Month": month,
                        "Year": str(year),
                        "Day of Week": day_name,
                        "Week Number": week_num,
                        "Receipt No": receipt_no if receipt_no else "N/A",
                        "Vendor": vendor if vendor else "N/A",
                        "Amount": float(amount),
                        "Description of Work": desc
                    }
                    
                    st.session_state.tasks_df = pd.concat([st.session_state.tasks_df, pd.DataFrame([new_row])], ignore_index=True)
                    st.success("Activity and structural financial assets secured inside transaction ledger log.")
                except ValueError:
                    st.error("❌ Chronological processing error. Verify your Day/Month configuration framework.")

# ----------------- PAGE 2: LEDGER OF WORK & HTML BUILDER -----------------
elif st.session_state.current_page == "ledger":
    st.subheader("📊 Quick Stats & Materials Ledger Preview")
    
    # Dynamic Financial Dashboard Cards Cloned From Your Layout
    total_spent = 0.0 if st.session_state.tasks_df.empty else st.session_state.tasks_df['Amount'].sum()
    
    st.markdown(f"""
        <div class="stat-card-container">
            <div class="stat-card">
                <div class="label">Total Logs Count</div>
                <div class="value">{len(st.session_state.tasks_df)} Entries</div>
            </div>
            <div class="stat-card">
                <div class="label">Total Materials Spent</div>
                <div class="value">PHP {total_spent:,.2f}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.tasks_df.empty:
        st.info("No records available yet. Access input dashboard framework to generate dynamic transactions.")
    else:
        month_map = {"January":1, "February":2, "March":3, "April":4, "May":5, "June":6, "July":7, "August":8, "September":9, "October":10, "November":11, "December":12}
        display_df = st.session_state.tasks_df.copy()
        display_df['Month_Num'] = display_df['Month'].map(lambda m: month_list.index(m)+1 if m in month_list else 1)
        display_df = display_df.sort_values(by=['Year', 'Month_Num', 'Date']).drop(columns=['Month_Num'])
        
        # Display advanced tabular tracking matrix
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # --- Native Programmatic HTML Exporter Document Framework ---
        def generate_html(dataframe):
            sorted_df = dataframe.copy()
            sorted_df['Month_Num'] = sorted_df['Month'].map(lambda m: month_list.index(m)+1 if m in month_list else 1)
            sorted_df = sorted_df.sort_values(by=['Year', 'Month_Num', 'Date'])
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Advanced Project & Receipt Ledger</title>
                <style>
                    body {{ 
                        font-family: 'Segoe UI', Arial, sans-serif; 
                        background: linear-gradient(rgba(10, 25, 20, 0.85), rgba(10, 25, 20, 0.85)), url('https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1920&q=80') no-repeat center center fixed;
                        background-size: cover;
                        color: #ffffff; margin: 0; padding: 40px; 
                    }}
                    .container {{ max-width: 1000px; margin: 0 auto; background: rgba(6, 35, 25, 0.7); backdrop-filter: blur(10px); padding: 30px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.05); }}
                    .header {{ text-align: center; border-bottom: 2px solid #22c55e; padding-bottom: 20px; margin-bottom: 30px; }}
                    .header h1 {{ color: #22c55e; margin: 0; font-size: 28px; text-transform: uppercase; letter-spacing: 1px; }}
                    .header p {{ color: #a7f3d0; font-weight: 500; margin: 5px 0 0 0; font-size: 13px; }}
                    .summary-title {{ font-size: 20px; color: #22c55e; font-weight: bold; margin-bottom: 15px; }}
                    .week-section {{ margin-bottom: 35px; }}
                    .week-title {{ background: rgba(34, 197, 94, 0.2); border-left: 4px solid #22c55e; color: #22c55e; padding: 10px 15px; font-size: 16px; font-weight: bold; border-radius: 0 6px 6px 0; margin-bottom: 12px; }}
                    table {{ width: 100%; border-collapse: collapse; margin-bottom: 10px; table-layout: fixed; }}
                    th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.05); vertical-align: top; word-wrap: break-word; }}
                    th {{ background-color: rgba(10, 35, 25, 0.5); color: #22c55e; font-weight: bold; font-size: 13px; text-transform: uppercase; }}
                    td.date-cell {{ color: #a7f3d0; width: 25%; font-weight: 600; }}
                    td.receipt-cell {{ color: #cbd5e1; width: 25%; font-size: 13px; }}
                    td.desc-cell {{ color: #e5e7eb; width: 50%; line-height: 1.5; white-space: pre-line; }}
                    tr:nth-child(even) td {{ background-color: rgba(255,255,255,0.02); }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>AILYN HOUSE PROJECT LEDGER</h1>
                        <p>Total Material Expenditures Accounted: PHP {total_spent:,.2f}</p>
                    </div>
            """
            
            grouped = sorted_df.groupby("Week Number")
            for week, group in grouped:
                html_content += f"""
                <div class="week-section">
                    <div class="week-title">📅 {week}</div>
                    <table>
                        <thead>
                            <tr>
                                <th style="width: 25%;">Date / Day</th>
                                <th style="width: 25%;">Receipt & Vendor Details</th>
                                <th style="width: 50%;">Description of Structural Execution</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                for _, row in group.iterrows():
                    html_content += f"""
                            <tr>
                                <td class="date-cell">{row['Month']} {row['Date']}, {row['Year']}<br><span style='font-size:12px; color:#94a3b8;'>{row['Day of Week']}</span></td>
                                <td class="receipt-cell">
                                    <b>No:</b> {row['Receipt No']}<br>
                                    <b>Store:</b> {row['Vendor']}<br>
                                    <span style='color:#22c55e; font-weight:bold;'>PHP {row['Amount']:,.2f}</span>
                                </td>
                                <td class="desc-cell">{row['Description of Work']}</td>
                            </tr>
                    """
                html_content += """
                        </tbody>
                    </table>
                </div>
                """
                
            html_content += """
                </div>
            </body>
            </html>
            """
            return html_content

        html_string = generate_html(display_df)
        
        st.download_button(
            label="📥 Export Organised Weekly Receipts Ledger as HTML",
            data=html_string,
            file_name=f"advanced_receipt_ledger_{datetime.now().strftime('%Y%m%d')}.html",
            mime="text/html",
            use_container_width=True
        )
