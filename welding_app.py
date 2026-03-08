import streamlit as st
import pandas as pd
import sqlite3
import io
from datetime import datetime

# --- DATABASE SETUP ---
conn = sqlite3.connect('welding_data.db', check_same_thread=False)
c = conn.cursor()

c.executescript('''
CREATE TABLE IF NOT EXISTS wps_master (wps_no TEXT PRIMARY KEY, process TEXT);
CREATE TABLE IF NOT EXISTS welders (welder_id TEXT PRIMARY KEY, name TEXT, qualified_wps TEXT);
CREATE TABLE IF NOT EXISTS joints (
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    area_name TEXT, 
    line_no TEXT,
    drawing_no TEXT, 
    joint_dia REAL, 
    sch_thickness REAL, 
    wps_no TEXT, 
    welder_id TEXT, 
    fitup_date DATE, 
    weld_date DATE, 
    visual_report TEXT, 
    nde_type TEXT, 
    nde_report_no TEXT,
    nde_result TEXT, 
    status TEXT
);
''')
conn.commit()

st.set_page_config(layout="wide", page_title="WeldQMS Pro")

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("WeldQMS Control Tower")
menu = st.sidebar.selectbox("Go to:", [
    "Area & Line Management", 
    "WPS & Welder Registry", 
    "Reports & Analytics"
])

# --- 1. AREA & LINE MANAGEMENT ---
if menu == "Area & Line Management":
    st.header("📂 Area & Line Selection")
    
    # Get unique areas
    areas = [row[0] for row in c.execute("SELECT DISTINCT area_name FROM joints").fetchall()]
    selected_area = st.selectbox("Select Area (Project)", ["+ Create New Area"] + areas)
    
    if selected_area == "+ Create New Area":
        new_area = st.text_input("Enter New Area Name")
        if st.button("Initialize Area"):
            selected_area = new_area
    
    if selected_area and selected_area != "+ Create New Area":
        # Get unique lines within that area
        lines = [row[0] for row in c.execute("SELECT DISTINCT line_no FROM joints WHERE area_name=?", (selected_area,)).fetchall()]
        selected_line = st.selectbox("Select Line Item", ["+ Add New Line"] + lines)
        
        if selected_line == "+ Add New Line":
            with st.expander("Line Item Details"):
                l_no = st.text_input("Line Number")
                drw = st.text_input("Drawing Number")
                dia = st.number_input("Joint Dia", min_value=0.1)
                sch = st.number_input("Thickness", min_value=0.1)
                wps_list = [row[0] for row in c.execute("SELECT wps_no FROM wps_master").fetchall()]
                wps = st.selectbox("Select WPS", wps_list)
                if st.button("Save Line Item"):
                    c.execute("INSERT INTO joints (area_name, line_no, drawing_no, joint_dia, sch_thickness, wps_no, status) VALUES (?,?,?,?,?,?,?)",
                              (selected_area, l_no, drw, dia, sch, wps, "Pending"))
                    conn.commit()
                    st.rerun()
        else:
            # DISPLAY JOINTS FOR SELECTED LINE
            st.subheader(f"Joints in {selected_area} / {selected_line}")
            df = pd.read_sql_query("SELECT * FROM joints WHERE area_name=? AND line_no=?", conn, params=(selected_area, selected_line))
            st.dataframe(df)
            
            # UPDATE JOINT LOGIC
            with st.expander("Update Weld Data"):
                target_id = st.selectbox("Select Joint ID", df['id'].tolist())
                current_wps = df[df['id'] == target_id]['wps_no'].values[0]
                
                # Filter qualified welders
                all_welders = c.execute("SELECT welder_id, qualified_wps FROM welders").fetchall()
                qual_welders = [w[0] for w in all_welders if current_wps in w[1].split(',')]
                
                col1, col2 = st.columns(2)
                f_date = col1.date_input("Fitup Date")
                w_date = col2.date_input("Weld Date")
                w_id = st.selectbox("Welder ID", qual_welders)
                
                v_res = st.selectbox("Visual", ["Pending", "Accepted", "Rejected"])
                nde_t = st.selectbox("NDE Type", ["None", "RT", "PT", "MPI", "UT"])
                nde_r_no = st.text_input("NDE Report Number")
                nde_res = st.selectbox("NDE Result", ["N/A", "Pass", "Fail"])
                
                if st.button("Update Record"):
                    status = "Closed" if (v_res == "Accepted" and (nde_t == "None" or nde_res == "Pass")) else "Open"
                    c.execute("""UPDATE joints SET fitup_date=?, weld_date=?, welder_id=?, 
                                 visual_report=?, nde_type=?, nde_report_no=?, nde_result=?, status=? WHERE id=?""",
                              (f_date, w_date, w_id, v_res, nde_t, nde_r_no, nde_res, status, target_id))
                    conn.commit()
                    st.success("Record Updated")
                    st.rerun()

# --- 2. WPS & WELDER REGISTRY (Same as before) ---
elif menu == "WPS & Welder Registry":
    st.header("⚙️ Master Registry")
    # ... [Keep your previous WPS and Welder registration code here] ...

# --- 3. REPORTS SECTION ---
elif menu == "Reports & Analytics":
    st.header("📊 Reports Center")
    report_type = st.selectbox("Select Report Type", ["Weld History", "Welder Continuity", "Repair Rate Analysis"])
    
    df_all = pd.read_sql_query("SELECT * FROM joints", conn)
    
    if report_type == "Weld History":
        st.subheader("Full Weld History Log")
        st.dataframe(df_all)
        
    elif report_type == "Welder Continuity":
        st.subheader("Welder Continuity (Last Weld Date per WPS)")
        continuity = df_all.groupby(['welder_id', 'wps_no'])['weld_date'].max().reset_index()
        st.table(continuity)
        
    elif report_type == "Repair Rate Analysis":
        st.subheader("Welder Repair Rates")
        perf = df_all.groupby('welder_id').agg(
            Total_Joints=('id', 'count'),
            Total_Inch_Dia=('joint_dia', 'sum'),
            Repairs=('nde_result', lambda x: (x == 'Fail').sum())
        )
        perf['Repair_Rate_%'] = (perf['Repairs'] / perf['Total_Joints']) * 100
        st.table(perf)

    # Universal Export to Excel
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_all.to_excel(writer, index=False, sheet_name='Report')
    st.download_button("📥 Download Report as Excel", buffer, "weld_report.xlsx", "application/vnd.ms-excel")
    import streamlit as st
import pandas as pd
import sqlite3
import io

# Database setup
conn = sqlite3.connect('welding_management.db', check_same_thread=False)
c = conn.cursor()

# --- HELPER: GET DATA ---
def get_data(query):
    return pd.read_sql_query(query, conn)

# --- APP LAYOUT ---
st.set_page_config(page_title="WeldQMS Pro", layout="wide")
st.sidebar.title("WeldQMS Navigation")
nav = st.sidebar.radio("Go to:", ["Project Explorer", "Welder Registry", "Reports"])

# --- 1. PROJECT EXPLORER ---
if nav == "Project Explorer":
    st.header("Area & Line Management")
    
    # Select Area (Project)
    projects = get_data("SELECT DISTINCT project_name FROM joints")
    selected_project = st.selectbox("Select Area (Project)", projects['project_name'].tolist())
    
    if selected_project:
        st.subheader(f"Lines in {selected_project}")
        # View lines for this area
        df = get_data(f"SELECT * FROM joints WHERE project_name = '{selected_project}'")
        st.dataframe(df)
        
        # Select Line for Update
        line_id = st.selectbox("Select Line Item ID to Update", df['id'].tolist())
        if line_id:
            with st.form("update_form"):
                f_date = st.date_input("Fitup Date")
                w_date = st.date_input("Weld Date")
                # Dropdown for qualified welders only
                wps = df[df['id'] == line_id]['wps_no'].values[0]
                qualified = [w[0] for w in c.execute("SELECT welder_id FROM welders WHERE qualified_wps LIKE ?", (f'%{wps}%',)).fetchall()]
                welder = st.selectbox("Assign Welder", qualified)
                
                if st.form_submit_button("Update Joint"):
                    c.execute("UPDATE joints SET fitup_date=?, weld_date=?, welder_id=? WHERE id=?", (f_date, w_date, welder, line_id))
                    conn.commit()
                    st.success("Updated!")

# --- 2. WELDER REGISTRY ---
elif nav == "Welder Registry":
    st.header("Manage Welders & Qualifications")
    # (Simplified: Add logic here to insert into 'welders' table)
    st.info("Use this section to update welder qualifications against specific WPS.")

# --- 3. REPORTING HUB ---
elif nav == "Reports":
    st.header("Quality Control Reports")
    tab1, tab2, tab3 = st.tabs(["Weld History", "Welder Continuity", "Repair Rate Analysis"])
    
    with tab1: # Weld History
        st.subheader("Full Project Weld History")
        hist = get_data("SELECT * FROM joints WHERE status = 'Closed'")
        st.dataframe(hist)
    
    with tab2: # Welder Continuity
        st.subheader("Welder Continuity Report")
        w_id = st.selectbox("Select Welder ID", get_data("SELECT welder_id FROM welders")['welder_id'].tolist())
        continuity_df = get_data(f"SELECT * FROM joints WHERE welder_id = '{w_id}'")
        st.dataframe(continuity_df[['drawing_no', 'weld_date', 'nde_type', 'nde_result']])
        
    with tab3: # Repair Rate
        st.subheader("Repair Rate Performance")
        query = """
        SELECT welder_id, 
        COUNT(*) as Total_Joints,
        SUM(CASE WHEN nde_result = 'Fail' THEN 1 ELSE 0 END) as Failures,
        (CAST(SUM(CASE WHEN nde_result = 'Fail' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*)) * 100 as Repair_Rate
        FROM joints WHERE nde_result IS NOT NULL GROUP BY welder_id
        """
        st.table(get_data(query))
