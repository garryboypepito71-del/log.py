import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- Theme Configuration & Injected Premium Glassmorphism Background Style ---
st.set_page_config(page_title="Ailyn House Premium Planner", page_icon="🏗️", layout="wide")

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

    /* Custom Header Container */
    .glass-header {
        text-align: center;
        margin-bottom: 30px;
        padding-bottom: 10px;
    }
    
    .glass-header h1 {
        color: #22c55e !important;
        font-size: 2.3rem !important;
        font-weight: 700 !important;
        letter-spacing: 1.5px;
        margin: 0;
        text-transform: uppercase;
    }
    
    .glass-header p {
        color: #a7f3d0 !important;
        font-weight: 500;
        margin-top: 8px;
        font-size: 0.9rem;
    }

    h2, h3, label, .stWidgetLabel p, .stSubheader {
        color: #22c55e !important;
        font-weight: 600 !important;
    }

    /* Metrics display structural cards */
    .stat-card-container {
        display: flex;
        gap: 20px;
        margin-bottom: 25px;
    }

    .stat-card {
        flex: 1;
        background: rgba(4, 28, 20, 0.7);
        border: 1px solid rgba(34, 197, 94, 0.25);
        padding: 24px;
        border-radius: 14px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
    }

    .stat-card .label {
        font-size: 0.8rem;
        color: #22c55e;
        text-transform: uppercase;
        font-weight: 700;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }

    .stat-card .value {
        font-size: 2rem;
        font-weight: 800;
        color: #ffffff;
    }

    .form-box {
        background: rgba(6, 20, 15, 0.4);
        border: 1px solid rgba(255,255,255,0.05);
        padding: 25px;
        border-radius: 12px;
        margin-bottom: 20px;
    }

    /* Calendar Grid System */
    .calendar-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 20px;
        margin-bottom: 10px;
        width: 100%;
    }

    .calendar-event-card {
        background: rgba(4, 28, 20, 0.75);
        border: 1px solid rgba(34, 197, 94, 0.3);
        border-radius: 14px 14px 0 0;
        overflow: hidden;
    }

    .calendar-event-header {
        background: rgba(34, 197, 94, 0.2);
        padding: 12px 15px;
        border-bottom: 1px solid rgba(34, 197, 94, 0.3);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .calendar-event-date {
        font-weight: 700;
        color: #22c55e;
        font-size: 1rem;
    }

    .calendar-event-daybadge {
        background: #22c55e;
        color: #041c14;
        font-size: 0.75rem;
        font-weight: 800;
        padding: 3px 8px;
        border-radius: 6px;
        text-transform: uppercase;
    }

    .calendar-event-body {
        padding: 15px;
        font-size: 0.95rem;
        line-height: 1.5;
        color: #e5e7eb;
        min-height: 100px;
        white-space: pre-line;
    }

    .week-divider-title {
        background: rgba(255, 255, 255, 0.05);
        border-left: 4px solid #22c55e;
        padding: 8px 15px;
        font-weight: 700;
        color: #a7f3d0;
        margin-top: 25px;
        margin-bottom: 15px;
        border-radius: 0 6px 6px 0;
        font-size: 1.05rem;
    }

    /* Elements Framework Injections */
    div[data-baseweb="input"], div[data-baseweb="select"], div[data-baseweb="textarea"] {
        background-color: rgba(8, 30, 22, 0.75) !important;
        border: 1px solid rgba(34, 197, 94, 0.3) !important;
        border-radius: 8px !important;
    }
    
    input, textarea, div[data-baseweb="select"] {
        color: #ffffff !important;
    }

    div.stButton > button {
        background-color: rgba(8, 40, 28, 0.8) !important;
        color: #22c55e !important;
        border: 1px solid rgba(34, 197, 94, 0.4) !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        letter-spacing: 0.5px;
        padding: 14px 28px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    div.stButton > button:hover {
        background-color: #047857 !important;
        color: white !important;
        box-shadow: 0 0 20px rgba(34, 197, 94, 0.5) !important;
    }
    
    /* Styled delete button container match */
    .delete-btn-box div.stButton > button {
        background-color: rgba(239, 68, 68, 0.15) !important;
        color: #f87171 !important;
        border: 1px solid rgba(239, 68, 68, 0.3) !important;
        border-top: none !important;
        border-radius: 0 0 14px 14px !important;
        padding: 6px !important;
        font-size: 0.8rem !important;
    }
    .delete-btn-box div.stButton > button:hover {
        background-color: #ef4444 !important;
        color: white !important;
        box-shadow: 0 0 15px rgba(239, 68, 68, 0.4) !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- CSV Local Storage Synchronization Handlers ---
DB_FILE = "ailyn_house_data.csv"

def load_data():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            # Ensure proper string padding for structural layouts
            df['Date'] = df['Date'].astype(str).str.zfill(2)
            return df
        except Exception:
            pass
    return pd.DataFrame(columns=["Date", "Month", "Year", "Day of Week", "Week Number", "Description of Work"])

def save_data(df):
    df.to_csv(DB_FILE, index=False)

# Initialize data structures from disk file instead of standard session volatile memory
if "tasks_df" not in st.session_state:
    st.session_state.tasks_df = load_data()
if "current_page" not in st.session_state:
    st.session_state.current_page = "dashboard"

# --- Title Header Layout ---
st.markdown("""
    <div class="glass-header">
        <h1>🏗️ AILYN HOUSE PROJECT PLANNER</h1>
        <p>Combined System | Mobile Operating Engine v30000</p>
    </div>
""", unsafe_allow_html=True)

# --- Top Navigation Bar ---
col_nav1, col_nav2 = st.columns(2)
with col_nav1:
    if st.button("📊 ACCESS ENGINE INPUT DASHBOARD", use_container_width=True):
        st.session_state.current_page = "dashboard"
with col_nav2:
    if st.button("📑 VIEW ORGANISED PROJECT LEDGER", use_container_width=True):
        st.session_state.current_page = "ledger"

st.markdown("<br>", unsafe_allow_html=True)

month_list = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

# ----------------- PAGE 1: INPUT DASHBOARD -----------------
if st.session_state.current_page == "dashboard":
    st.subheader("📋 Structural Operations Registry")
    
    with st.form("construction_form", clear_on_submit=True):
        st.markdown('<div class="form-box">', unsafe_allow_html=True)
        
        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            day_options = list(range(1, 32))
            current_day_idx = datetime.now().day - 1
            day = st.selectbox("I Target Day Option", options=day_options, index=current_day_idx)
        with col_d2:
            current_month_idx = datetime.now().month - 1
            month_input = st.selectbox("📅 Planning Month Group", options=month_list, index=current_month_idx)
        with col_d3:
            year_options = list(range(2020, 2036))
            current_year_idx = year_options.index(datetime.now().year) if datetime.now().year in year_options else 6
            year = st.selectbox("📁 Fiscal Management Year", options=year_options, index=current_year_idx)
            
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        desc = st.text_area("✍️ Task Execution & Structural Log Details", height=150, placeholder="Document structural parameters, concrete formulations, deployment schedules...")
        st.markdown("<br>", unsafe_allow_html=True)
        submit_btn = st.form_submit_button("Secure Activity to Ledger Database", use_container_width=True)
        
        if submit_btn:
            if desc.strip() == "":
                st.error("Registry transaction aborted. Description layout parameter must contain text inputs.")
            else:
                try:
                    month_num = month_list.index(month_input) + 1
                    date_obj = datetime(year, month_num, day)
                    day_name = date_obj.strftime("%A")
                    formatted_date = f"{day:02d}"
                    week_num = f"Week {date_obj.strftime('%U')} ({year})"
                    
                    new_row = {
                        "Date": formatted_date,
                        "Month": month_input,
                        "Year": str(year),
                        "Day of Week": day_name,
                        "Week Number": week_num,
                        "Description of Work": desc
                    }
                    
                    st.session_state.tasks_df = pd.concat([st.session_state.tasks_df, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(st.session_state.tasks_df)
                    st.success("Activity logged and stored inside local persistent database storage configuration.")
                except ValueError:
                    st.error("❌ Chronological matrix mismatch error. Selected configuration framework is invalid.")

# ----------------- PAGE 2: LEDGER OF WORK & HTML BUILDER -----------------
elif st.session_state.current_page == "ledger":
    st.subheader("📑 Materials Ledger & Operations Preview")
    
    st.markdown(f"""
        <div class="stat-card-container">
            <div class="stat-card">
                <div class="label">Total Secure Log Records (Persistent Archive)</div>
                <div class="value">📑 {len(st.session_state.tasks_df)} Active Entries</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.tasks_df.empty:
        st.info("Log database empty. Utilize the primary registry frame console to record items.")
    else:
        # --- Advanced UI Search Bar & Month Filter Matrix ---
        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            search_query = st.text_input("🔍 Search Logs Content Description", placeholder="Type keywords to filter calendar layout...")
        with col_f2:
            filter_month = st.selectbox("📅 Filter by Month Matrix", options=["All Months"] + month_list)
            
        display_df = st.session_state.tasks_df.copy()
        display_df['Month_Num'] = display_df['Month'].map(lambda m: month_list.index(m)+1 if m in month_list else 1)
        display_df = display_df.sort_values(by=['Year', 'Month_Num', 'Date'])
        
        # Apply Live Queries Filters
        if search_query:
            display_df = display_df[display_df['Description of Work'].str.contains(search_query, case=False, na=False)]
        if filter_month != "All Months":
            display_df = display_df[display_df['Month'] == filter_month]
            
        # Render the logged entries as an interactive Calendar Grid System with custom structural deletion
        grouped = display_df.groupby("Week Number", sort=False)
        for week, group in grouped:
            st.markdown(f'<div class="week-divider-title">📅 {week}</div>', unsafe_allow_html=True)
            
            # Use dynamic layout column blocks to house structural components 
            cols = st.columns(3)
            for idx, (_, row) in enumerate(group.iterrows()):
                target_col = cols[idx % 3]
                with target_col:
                    grid_html = f'<div class="calendar-event-card"><div class="calendar-event-header"><span class="calendar-event-date">{row["Month"]} {row["Date"]}, {row["Year"]}</span><span class="calendar-event-daybadge">{row["Day of Week"][:3]}</span></div><div class="calendar-event-body">{row["Description of Work"]}</div></div>'
                    st.markdown(grid_html, unsafe_allow_html=True)
                    
                    # Custom programmatic inline delete layout key mapping mechanics
                    st.markdown('<div class="delete-btn-box">', unsafe_allow_html=True)
                    # Find exact match location in core dataframe array
                    match_indices = st.session_state.tasks_df[
                        (st.session_state.tasks_df['Date'] == row['Date']) & 
                        (st.session_state.tasks_df['Month'] == row['Month']) & 
                        (st.session_state.tasks_df['Year'] == row['Year']) & 
                        (st.session_state.tasks_df['Description of Work'] == row['Description of Work'])
                    ].index
                    
                    if not match_indices.empty:
                        if st.button(f"🗑️ Delete Entry Row", key=f"del_{match_indices[0]}_{idx}", use_container_width=True):
                            st.session_state.tasks_df = st.session_state.tasks_df.drop(match_indices[0]).reset_index(drop=True)
                            save_data(st.session_state.tasks_df)
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)

        # --- Native Programmatic HTML Exporter Document Framework ---
        def generate_html(dataframe):
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Organised Project Planner Ledger</title>
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
                    .week-section {{ margin-bottom: 35px; }}
                    .week-title {{ background: rgba(34, 197, 94, 0.2); border-left: 4px solid #22c55e; color: #22c55e; padding: 10px 15px; font-size: 16px; font-weight: bold; border-radius: 0 6px 6px 0; margin-bottom: 12px; }}
                    .calendar-grid-html {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px; margin-bottom: 15px; }}
                    .card-html {{ background: rgba(10, 35, 25, 0.6); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 10px; overflow: hidden; }}
                    .card-h-head {{ background: rgba(34, 197, 94, 0.15); padding: 10px; display: flex; justify-content: space-between; font-weight: bold; color: #22c55e; font-size: 14px; border-bottom: 1px solid rgba(34, 197, 94, 0.2); }}
                    .card-h-body {{ padding: 12px; color: #e5e7eb; font-size: 13px; line-height: 1.4; white-space: pre-line; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>AILYN HOUSE PROJECT LEDGER</h1>
                        <p>Weekly Organised Construction Execution Records</p>
                    </div>
            """
            grouped_html = dataframe.groupby("Week Number", sort=False)
            for week, group in grouped_html:
                html_content += f"""
                <div class="week-section">
                    <div class="week-title">📅 {week}</div>
                    <div class="calendar-grid-html">
                """
                for _, row in group.iterrows():
                    html_content += f"""
                        <div class="card-html">
                            <div class="card-h-head">
                                <span>{row['Month']} {row['Date']}, {row['Year']}</span>
                                <span style="background:#22c55e; color:#062319; padding:1px 5px; border-radius:4px; font-size:11px;">{row['Day of Week'][:3].upper()}</span>
                            </div>
                            <div class="card-h-body">{row['Description of Work']}</div>
                        </div>
                    """
                html_content += "</div></div>"
            html_content += "</div></body></html>"
            return html_content

        html_string = generate_html(display_df)
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            label="📥 Export Organised Visual Calendar Ledger as HTML",
            data=html_string,
            file_name=f"calendar_planner_ledger_{datetime.now().strftime('%Y%m%d')}.html",
            mime="text/html",
            use_container_width=True
        )