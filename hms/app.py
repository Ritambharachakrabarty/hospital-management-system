import os
import sqlite3
import hashlib
from datetime import datetime, date
import pandas as pd
import streamlit as st

# CONFIGURATION & CONSTANTS
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hms.db")

st.set_page_config(
    page_title="Hospital Management System",
    page_icon="+",
    layout="wide",
    initial_sidebar_state="expanded"
)
# Custom CSS 
CUSTOM_CSS = """
<style>
    /* Global & Typography */
    .main {
        background-color: #f8fafc;
    }
    h1, h2, h3 {
        color: #1e3a8a;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Metric Cards */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #ffffff 0%, #f0fdf4 100%);
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 14px 18px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    div[data-testid="metric-container"] label {
        color: #64748b !important;
        font-weight: 600;
        font-size: 0.85rem;
    }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #0f766e !important;
        font-size: 1.8rem;
        font-weight: 700;
    }

    /* Cards */
    .hms-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }
    .hms-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    .badge-active { background-color: #dcfce7; color: #166534; }
    .badge-discharged { background-color: #fee2e2; color: #991b1b; }
    .badge-cardio { background-color: #ede9fe; color: #5b21b6; }
    .badge-ward { background-color: #e0f2fe; color: #0369a1; }

    /* Button styling */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# DATABASE UTILITIES
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def caesar_cipher(text: str, shift: int = 3) -> str:
    shift %= 26
    result = []
    for char in text:
        if "a" <= char <= "z":
            result.append(chr((ord(char) - ord("a") + shift) % 26 + ord("a")))
        elif "A" <= char <= "Z":
            result.append(chr((ord(char) - ord("A") + shift) % 26 + ord("A")))
        else:
            result.append(char)
    return "".join(result)


def legacy_hash_password(password: str) -> str:
    salt = "hms_secure_salt_2026"
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. usr_pwd table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usr_pwd (
            USERNAME TEXT PRIMARY KEY,
            PASSWORD TEXT NOT NULL
        );
    """)

    # 2. doc table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS doc (
            DID TEXT PRIMARY KEY,
            DFNAME TEXT NOT NULL,
            DMNAME TEXT,
            DLNAME TEXT NOT NULL,
            FIELD TEXT NOT NULL,
            DOJ TEXT NOT NULL
        );
    """)

    # 3. dtime table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dtime (
            DID TEXT PRIMARY KEY,
            MON TEXT,
            TUE TEXT,
            WED TEXT,
            THU TEXT,
            FRI TEXT,
            SAT TEXT,
            SUN TEXT,
            FOREIGN KEY (DID) REFERENCES doc (DID) ON DELETE CASCADE
        );
    """)

    # 4. nurse table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nurse (
            NID TEXT PRIMARY KEY,
            NFNAME TEXT NOT NULL,
            NMNAME TEXT,
            NLNAME TEXT NOT NULL,
            WARD TEXT NOT NULL,
            DOJ TEXT NOT NULL
        );
    """)

    # 5. Patient table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Patient (
            PNUM INTEGER PRIMARY KEY AUTOINCREMENT,
            FNAME TEXT NOT NULL,
            MNAME TEXT,
            LNAME TEXT NOT NULL,
            DID TEXT NOT NULL,
            GENDER TEXT NOT NULL,
            DOB TEXT NOT NULL,
            DOA TEXT NOT NULL,
            DOD TEXT,
            WARD TEXT NOT NULL,
            REASON TEXT NOT NULL,
            FOREIGN KEY (DID) REFERENCES doc (DID)
        );
    """)
    conn.commit()

    conn.close()


def calculate_age(dob_str):
    if not dob_str:
        return "N/A"

    dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
    today = date.today()
    age = today.year - dob.year

    if (today.month, today.day) < (dob.month, dob.day):
        age -= 1

    if age < 0:
        return "N/A"

    return str(age) + " yrs"

conn = get_db_connection()


def validate_doctor_id(did: str) -> bool:
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM doc WHERE DID = ?;", (did.strip().upper(),))
    row = cursor.fetchone()
    cursor.close()
    return row is not None


def get_all_doctor_options():
    cursor = conn.cursor()
    cursor.execute("SELECT DID, DFNAME, DLNAME, FIELD FROM doc ORDER BY DID ASC;")
    rows = cursor.fetchall()
    cursor.close()
    return [{"DID": r["DID"], "Label": f"{r['DID']} - Dr. {r['DFNAME']} {r['DLNAME']} ({r['FIELD']})"} for r in rows]


def get_nurses_by_ward(ward: str):
    cursor = conn.cursor()
    cursor.execute("SELECT NID, NFNAME || ' ' || NLNAME as NurseName FROM nurse WHERE WARD = ? ORDER BY NID ASC;", (ward,))
    rows = cursor.fetchall()
    cursor.close()
    return [f"{r['NID']} ({r['NurseName']})" for r in rows]


init_database()


# AUTHENTICATION 
def render_auth_page():
    col_left, col_center, col_right = st.columns([1, 2, 1])

    with col_center:
        st.markdown(
            """
            <div style="text-align: center; margin-top: 30px; margin-bottom: 25px;">
                <h1 style="margin-bottom: 5px;">Hospital Management System</h1>
                <p style="color: #64748b; font-size: 1.05rem;">Integrated Clinical, Staff & Patient Records Portal</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        auth_tab = st.tabs(["Sign In", "User Registration", "Forgot Password"])

        # LOGIN
        with auth_tab[0]:
            st.markdown("### Staff Sign In")
            st.caption("Please enter your registered credentials to access the portal.")
            with st.form("login_form"):
                login_user = st.text_input("Username", placeholder="e.g. admin")
                login_pass = st.text_input("Password", type="password", placeholder="Enter password")
                login_submit = st.form_submit_button("Sign In", use_container_width=True)

            if login_submit:
                if not login_user or not login_pass:
                    st.error("Please enter both username and password.")
                else:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT USERNAME, PASSWORD FROM usr_pwd WHERE USERNAME = ?",
                        (login_user.strip(),)
                    )
                    user_record = cursor.fetchone()
                    authenticated = bool(
                        user_record
                        and user_record["PASSWORD"] == caesar_cipher(login_pass)
                    )
                    if (
                        user_record
                        and not authenticated
                        and user_record["PASSWORD"] == legacy_hash_password(login_pass)
                    ):
                        cursor.execute(
                            "UPDATE usr_pwd SET PASSWORD = ? WHERE USERNAME = ?;",
                            (caesar_cipher(login_pass), user_record["USERNAME"])
                        )
                        conn.commit()
                        authenticated = True
                    conn.close()

                    if authenticated:
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = user_record["USERNAME"]
                        st.success(f"Welcome back, {user_record['USERNAME']}!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

            st.info("**Preloaded Demo Credentials**: Username: `admin` | Password: `admin123`")

        # REGISTER
        with auth_tab[1]:
            st.markdown("### User Registration")
            st.caption("Register a new staff account.")
            with st.form("register_form", clear_on_submit=True):
                reg_user = st.text_input("Username *", placeholder="e.g. nurse_smith")
                reg_pass = st.text_input("Password *", type="password")
                reg_pass_confirm = st.text_input("Confirm Password *", type="password")
                reg_submit = st.form_submit_button("Register Account", use_container_width=True)

            if reg_submit:
                if not reg_user or not reg_pass or not reg_pass_confirm:
                    st.error("All fields are mandatory.")
                elif len(reg_pass) < 4:
                    st.warning("Password should be at least 4 characters.")
                elif reg_pass != reg_pass_confirm:
                    st.error("Passwords do not match.")
                else:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1 FROM usr_pwd WHERE USERNAME = ?;", (reg_user.strip(),))
                    if cursor.fetchone():
                        st.error(f"Username '{reg_user}' is already registered.")
                    else:
                        cursor.execute(
                            "INSERT INTO usr_pwd (USERNAME, PASSWORD) VALUES (?, ?);",
                            (reg_user.strip(), caesar_cipher(reg_pass))
                        )
                        conn.commit()
                        st.success(f"Account '{reg_user}' registered successfully!")
                    conn.close()

        # FORGOT PASSWORD
        with auth_tab[2]:
            st.markdown("### Password Reset (Forgot Password)")
            st.caption("Reset the password for an existing registered username.")
            
            with st.form("forgot_password_form", clear_on_submit=True):
                reset_user = st.text_input("Enter Registered Username *", placeholder="e.g. admin")
                new_pass = st.text_input("New Password *", type="password")
                new_pass_confirm = st.text_input("Confirm New Password *", type="password")
                reset_btn = st.form_submit_button("Reset Password", use_container_width=True)

            if reset_btn:
                if not reset_user or not new_pass or not new_pass_confirm:
                    st.error("Please fill in all fields.")
                elif len(new_pass) < 4:
                    st.warning("Password must be at least 4 characters.")
                elif new_pass != new_pass_confirm:
                    st.error("New passwords do not match.")
                else:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1 FROM usr_pwd WHERE USERNAME = ?;", (reset_user.strip(),))
                    if not cursor.fetchone():
                        st.error(f"Username '{reset_user}' does not exist.")
                    else:
                        cursor.execute(
                            "UPDATE usr_pwd SET PASSWORD = ? WHERE USERNAME = ?;",
                            (caesar_cipher(new_pass), reset_user.strip())
                        )
                        conn.commit()
                        st.success(f"Password for '{reset_user}' reset successfully!")
                    conn.close()


# PATIENT MANAGEMENT
def render_patient_management():
    st.title("Patient Management")
    st.markdown("Comprehensive Patient Records System conforming to the `Patient` table schema.")

    p_tabs = st.tabs(["View Patients", "Add Patient", "Modify Patient", "Discharge & Delete"])

    # TAB 1: VIEW & SEARCH PATIENTS
    with p_tabs[0]:
        st.subheader("Patient Records Directory")

        conn = get_db_connection()
        query = """
            SELECT p.PNUM, p.FNAME, p.MNAME, p.LNAME, p.GENDER, p.DOB, p.DOA, p.DOD, p.WARD, p.REASON,
                   p.DID, d.DFNAME, d.DLNAME, d.FIELD
            FROM Patient p
            LEFT JOIN doc d ON p.DID = d.DID
            ORDER BY p.PNUM DESC;
        """
        df_patients = pd.read_sql_query(query, conn)
        conn.close()

        if df_patients.empty:
            st.info("No patient records found in the database.")
            st.caption("Create a doctor in Doctor Management first, then use the Add Patient tab to enter the first patient.")
        else:
            df_patients["Full Name"] = (
                df_patients["FNAME"] + " " +
                df_patients["MNAME"].fillna("") + " " +
                df_patients["LNAME"]
            ).str.replace(r"\s+", " ", regex=True).str.strip()
            df_patients["Age"] = df_patients["DOB"].apply(calculate_age)
            df_patients["Doctor Assignment"] = (
                "Dr. " + df_patients["DFNAME"] + " " +
                df_patients["DLNAME"] + " (" +
                df_patients["FIELD"] + ") [" +
                df_patients["DID"].astype(str) + "]"
            )
            df_patients.loc[df_patients["DID"].isna(), "Doctor Assignment"] = "Unassigned"
            df_patients["Status"] = df_patients["DOD"].apply(
                lambda d: "Discharged" if pd.notna(d) else "Admitted (Active)"
            )

            # Search and Filter Controls
            col_search, col_status_filter, col_ward_filter = st.columns([2, 1, 1])
            with col_search:
                search_term = st.text_input("Search Patient ID or Name", placeholder="Enter PNUM or Name")
            with col_status_filter:
                status_filter = st.selectbox("Filter Status", ["All", "Admitted (Active)", "Discharged"])
            with col_ward_filter:
                ward_filter = st.selectbox(
                    "Filter Ward",
                    ["All"] + sorted(df_patients["WARD"].dropna().unique().tolist())
                )

            filtered_df = df_patients.copy()

            if search_term:
                term = search_term.strip().lower()
                filtered_df = filtered_df[
                    filtered_df["PNUM"].astype(str).str.contains(term, case=False, na=False) |
                    filtered_df["FNAME"].str.lower().str.contains(term, na=False) |
                    filtered_df["LNAME"].str.lower().str.contains(term, na=False) |
                    filtered_df["Full Name"].str.lower().str.contains(term, na=False)
                ]

            if status_filter != "All":
                filtered_df = filtered_df[filtered_df["Status"] == status_filter]

            if ward_filter != "All":
                filtered_df = filtered_df[filtered_df["WARD"] == ward_filter]

            st.markdown(f"**Showing {len(filtered_df)} of {len(df_patients)} total patient records**")

            # Display Table
            display_cols = [
                "PNUM", "Full Name", "GENDER", "Age", "DOB", "DOA", "DOD", "WARD",
                "Doctor Assignment", "REASON", "Status"
            ]
            rename_map = {
                "PNUM": "PNUM (ID)",
                "GENDER": "Gender",
                "DOB": "Date of Birth",
                "DOA": "Date of Admission",
                "DOD": "Date of Discharge",
                "WARD": "Ward Number",
                "REASON": "Reason for Admission"
            }
            st.dataframe(
                filtered_df[display_cols].rename(columns=rename_map),
                use_container_width=True,
                hide_index=True
            )

            # Nurses associated with Patient through WARD
            with st.expander("View Associated Ward Staff (Nurse - Patient Relationship via WARD)"):
                st.caption("As defined in the ER specifications: Nurses are associated with patients through the assigned WARD.")
                selected_patient_id = st.selectbox(
                    "Inspect Ward Staff for Patient",
                    options=filtered_df["PNUM"].tolist(),
                    format_func=lambda x: f"Patient #{x} ({next(r['Full Name'] + ' - ' + r['WARD'] for _, r in filtered_df.iterrows() if r['PNUM'] == x)})"
                )
                patient_ward = filtered_df[filtered_df["PNUM"] == selected_patient_id]["WARD"].iloc[0]
                nurses_in_ward = get_nurses_by_ward(patient_ward)
                if nurses_in_ward:
                    st.success(f"Nurses on duty for **{patient_ward}**: {', '.join(nurses_in_ward)}")
                else:
                    st.warning(f"No nurses currently assigned specifically to {patient_ward}.")

    # TAB 2: REGISTER NEW PATIENT (CREATE)
    with p_tabs[1]:
        st.subheader("Add New Patient Record")
        st.caption("Auto-generated unique Patient ID (PNUM) with Doctor ID validation and automated Age calculation.")

        doc_options = get_all_doctor_options()
        if not doc_options:
            st.error("No doctors found in the database. Add a doctor from Doctor Management before registering a patient.")
        else:
            with st.form("add_patient_form", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    fname = st.text_input("First Name (FNAME) *", placeholder="e.g. John")
                with c2:
                    mname = st.text_input("Middle Name (MNAME)", placeholder="e.g. Edward (Nullable)")
                with c3:
                    lname = st.text_input("Last Name (LNAME) *", placeholder="e.g. Doe")

                c4, c5, c6 = st.columns(3)
                with c4:
                    gender_choice = st.selectbox("Gender (GENDER) *", ["M (Male)", "F (Female)", "O (Other)"])
                    gender_val = gender_choice[0]  # Store 'M', 'F', or 'O' as per schema
                with c5:
                    dob = st.date_input("Date of Birth (DOB) *", min_value=date(1920, 1, 1), max_value=date.today())
                with c6:
                    calc_age_display = calculate_age(dob.strftime("%Y-%m-%d"))
                    st.metric("Computed Age from DOB", calc_age_display)

                c7, c8, c9 = st.columns(3)
                with c7:
                    # Doctor ID validation
                    selected_doc = st.selectbox(
                        "Assigned Doctor (DID) *",
                        options=[d["DID"] for d in doc_options],
                        format_func=lambda did: next((d["Label"] for d in doc_options if d["DID"] == did), did)
                    )
                with c8:
                    doa = st.date_input("Date of Admission (DOA) *", value=date.today())
                with c9:
                    ward = st.selectbox(
                        "Ward Number (WARD) *",
                        ["Ward 101", "Ward 102", "Ward 201", "ICU", "Cardiology Ward", "Pediatric Ward", "Emergency", "Orthopedic Ward"]
                    )

                c10, c11 = st.columns([1, 2])
                with c10:
                    status_choice = st.radio("Admission State", ["Active Admission (DOD is Null)", "Already Discharged"])
                    dod_val = None
                    if status_choice == "Already Discharged":
                        dod_val = st.date_input("Date of Discharge (DOD)", value=date.today())
                with c11:
                    reason = st.text_area("Reason for Admission (REASON) *", placeholder="Enter clinical condition, diagnosis, symptoms...")

                submit_patient = st.form_submit_button("Add Patient Record", use_container_width=True)

                if submit_patient:
                    if not fname.strip() or not lname.strip() or not reason.strip():
                        st.error("Please fill in all required fields (marked *).")
                    elif not validate_doctor_id(selected_doc):
                        st.error(f"Doctor ID '{selected_doc}' does not exist in the doc table.")
                    else:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        dod_str = dod_val.strftime("%Y-%m-%d") if dod_val else None
                        cursor.execute("""
                            INSERT INTO Patient (FNAME, MNAME, LNAME, DID, GENDER, DOB, DOA, DOD, WARD, REASON)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """, (
                            fname.strip(),
                            mname.strip() if mname else None,
                            lname.strip(),
                            selected_doc.strip(),
                            gender_val,
                            dob.strftime("%Y-%m-%d"),
                            doa.strftime("%Y-%m-%d"),
                            dod_str,
                            ward,
                            reason.strip()
                        ))
                        new_pnum = cursor.lastrowid
                        conn.commit()
                        conn.close()

                        st.success(f" Patient '{fname} {lname}' registered successfully with auto-generated Patient ID (PNUM): #{new_pnum}")

    # TAB 3: EDIT PATIENT DETAILS 
    with p_tabs[2]:
        st.subheader("Modify Patient Details")
        st.caption("Update Name, Doctor assignment, Gender, DOB / DOA / DOD, Ward, or Reason.")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT PNUM, FNAME, LNAME, DOB, WARD FROM Patient ORDER BY PNUM ASC;")
        patient_list = cursor.fetchall()
        conn.close()

        if not patient_list:
            st.info("No patients available to edit.")
        else:
            patient_choices = {r["PNUM"]: f"#{r['PNUM']} - {r['FNAME']} {r['LNAME']} (DOB: {r['DOB']} | Ward: {r['WARD']})" for r in patient_list}
            selected_pnum = st.selectbox(
                "Select Patient to Modify",
                options=list(patient_choices.keys()),
                format_func=lambda x: patient_choices[x]
            )

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Patient WHERE PNUM = ?;", (selected_pnum,))
            p_data = cursor.fetchone()
            conn.close()

            if p_data:
                doc_options = get_all_doctor_options()
                with st.form("edit_patient_form"):
                    st.markdown(f"#### Editing Record for Patient #{p_data['PNUM']}")
                    e_c1, e_c2, e_c3 = st.columns(3)
                    with e_c1:
                        e_fname = st.text_input("First Name (FNAME) *", value=p_data["FNAME"])
                    with e_c2:
                        e_mname = st.text_input("Middle Name (MNAME)", value=p_data["MNAME"] or "")
                    with e_c3:
                        e_lname = st.text_input("Last Name (LNAME) *", value=p_data["LNAME"])

                    e_c4, e_c5, e_c6 = st.columns(3)
                    with e_c4:
                        curr_g = str(p_data["GENDER"]).strip().upper()
                        gender_map = {"M": 0, "F": 1, "O": 2}
                        g_idx = gender_map.get(curr_g, 0)
                        e_gender_choice = st.selectbox("Gender (GENDER) *", ["M (Male)", "F (Female)", "O (Other)"], index=g_idx)
                        e_gender_val = e_gender_choice[0]
                    with e_c5:
                        curr_dob = datetime.strptime(p_data["DOB"], "%Y-%m-%d").date()
                        e_dob = st.date_input("Date of Birth (DOB) *", value=curr_dob)
                    with e_c6:
                        st.metric("Computed Age", calculate_age(e_dob.strftime("%Y-%m-%d")))

                    e_c7, e_c8, e_c9 = st.columns(3)
                    with e_c7:
                        all_dids = [d["DID"] for d in doc_options]
                        curr_did_idx = all_dids.index(p_data["DID"]) if p_data["DID"] in all_dids else 0
                        e_did = st.selectbox(
                            "Doctor Assignment (Validated against doc table) *",
                            options=all_dids,
                            index=curr_did_idx,
                            format_func=lambda did: next((d["Label"] for d in doc_options if d["DID"] == did), did)
                        )
                    with e_c8:
                        curr_doa = datetime.strptime(p_data["DOA"], "%Y-%m-%d").date()
                        e_doa = st.date_input("Date of Admission (DOA) *", value=curr_doa)
                    with e_c9:
                        ward_options = ["Ward 101", "Ward 102", "Ward 201", "ICU", "Cardiology Ward", "Pediatric Ward", "Emergency", "Orthopedic Ward"]
                        curr_ward = p_data["WARD"]
                        if curr_ward not in ward_options:
                            ward_options.append(curr_ward)
                        curr_ward_idx = ward_options.index(curr_ward)
                        e_ward = st.selectbox("Ward Number (WARD) *", ward_options, index=curr_ward_idx)

                    e_c10, e_c11 = st.columns([1, 2])
                    with e_c10:
                        is_discharged = bool(p_data["DOD"] and str(p_data["DOD"]).strip().upper() not in ["NONE", "", "NAN", "NULL"])
                        e_status = st.radio("Status", ["Admitted (Active - DOD Null)", "Discharged (Has DOD)"], index=1 if is_discharged else 0)
                        e_dod_val = None
                        if e_status.startswith("Discharged"):
                            default_dod = datetime.strptime(p_data["DOD"], "%Y-%m-%d").date()
                            e_dod_val = st.date_input("Date of Discharge (DOD)", value=default_dod)
                    with e_c11:
                        e_reason = st.text_area("Reason for Admission (REASON) *", value=p_data["REASON"])

                    save_changes = st.form_submit_button("Save Changes", use_container_width=True)

                    if save_changes:
                        if not e_fname.strip() or not e_lname.strip() or not e_reason.strip():
                            st.error("Please fill in all required fields.")
                        elif not validate_doctor_id(e_did):
                            st.error(f"Doctor ID '{e_did}' is invalid or does not exist in the doc table.")
                        else:
                            e_dod_str = e_dod_val.strftime("%Y-%m-%d") if e_dod_val else None
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE Patient
                                SET FNAME = ?, MNAME = ?, LNAME = ?, DID = ?, GENDER = ?,
                                    DOB = ?, DOA = ?, DOD = ?, WARD = ?, REASON = ?
                                WHERE PNUM = ?;
                            """, (
                                e_fname.strip(),
                                e_mname.strip() if e_mname else None,
                                e_lname.strip(),
                                e_did.strip(),
                                e_gender_val,
                                e_dob.strftime("%Y-%m-%d"),
                                e_doa.strftime("%Y-%m-%d"),
                                e_dod_str,
                                e_ward,
                                e_reason.strip(),
                                selected_pnum
                            ))
                            conn.commit()
                            conn.close()
                            st.success(f"Patient record #{selected_pnum} updated successfully!")
                            st.rerun()

    # TAB 4: DISCHARGE & RECORD ACTIONS (DELETE / DISCHARGE)
    with p_tabs[3]:
        st.subheader("Discharge & Record Deletion")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT PNUM, FNAME, LNAME, DOA, DOD, WARD FROM Patient ORDER BY PNUM DESC;")
        patients_to_action = cursor.fetchall()
        conn.close()

        if not patients_to_action:
            st.info("No records found.")
        else:
            action_pnum = st.selectbox(
                "Select Patient Record",
                options=[r["PNUM"] for r in patients_to_action],
                format_func=lambda x: f"Patient #{x} - {next(r['FNAME'] + ' ' + r['LNAME'] + ' (' + r['WARD'] + ', Status: ' + ('Discharged ' + str(r['DOD']) if r['DOD'] else 'Active') + ')' for r in patients_to_action if r['PNUM'] == x)}"
            )

            act_col1, act_col2 = st.columns(2)
            with act_col1:
                st.markdown("#### Quick Discharge")
                st.write("Mark patient as discharged today (sets Date of Discharge `DOD`).")
                if st.button("Mark as Discharged Today", use_container_width=True):
                    today_str = date.today().strftime("%Y-%m-%d")
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("UPDATE Patient SET DOD = ? WHERE PNUM = ?;", (today_str, action_pnum))
                    conn.commit()
                    conn.close()
                    st.success(f"Patient #{action_pnum} has been discharged as of {today_str}.")
                    st.rerun()

            with act_col2:
                st.markdown("#### Delete Patient Record")
                st.write("Permanently remove this patient file from the database.")
                confirm_delete = st.checkbox("I confirm I want to permanently delete this record.", key="del_chk")
                if st.button("Delete Record", type="primary", use_container_width=True, disabled=not confirm_delete):
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM Patient WHERE PNUM = ?;", (action_pnum,))
                    conn.commit()
                    conn.close()
                    st.warning(f"Patient record #{action_pnum} was permanently removed.")
                    st.rerun()


# DOCTOR MANAGEMENT
def render_doctor_management():
    st.title("Doctor Management")
    st.markdown("Physician directory, specializations, and weekly schedules (Mon–Sun) via `doc` & `dtime` tables.")

    added_message = st.session_state.pop("doctor_added_message", None)
    if added_message:
        st.success(added_message)

    conn = get_db_connection()
    query_docs = """
        SELECT d.DID, d.DFNAME, d.DMNAME, d.DLNAME, d.FIELD, d.DOJ,
               s.MON, s.TUE, s.WED, s.THU, s.FRI, s.SAT, s.SUN,
               (SELECT COUNT(*) FROM Patient p WHERE p.DID = d.DID) as PatientCount
        FROM doc d
        LEFT JOIN dtime s ON d.DID = s.DID
        ORDER BY d.DID ASC;
    """
    df_docs = pd.read_sql_query(query_docs, conn)
    conn.close()

    add_label = "Register First Doctor" if df_docs.empty else "Add Doctor"
    if st.button(add_label, key="open_doctor_registration"):
        st.session_state["show_doctor_registration"] = not st.session_state.get("show_doctor_registration", False)

    if st.session_state.get("show_doctor_registration", False):
        st.subheader("Register Doctor")
        with st.form("add_doctor_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                did = st.text_input("Doctor ID (DID) *", placeholder="e.g. DOC101")
            with c2:
                dfname = st.text_input("First Name *")
            with c3:
                dlname = st.text_input("Last Name *")

            c4, c5, c6 = st.columns(3)
            with c4:
                dmname = st.text_input("Middle Name")
            with c5:
                field = st.text_input("Specialization *", placeholder="e.g. Cardiology")
            with c6:
                doj = st.date_input("Date of Joining *", value=date.today())

            submit_doctor = st.form_submit_button("Save Doctor", use_container_width=True)

        if submit_doctor:
            if not did.strip() or not dfname.strip() or not dlname.strip() or not field.strip():
                st.error("Please fill in the required doctor fields.")
            else:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM doc WHERE DID = ?;", (did.strip().upper(),))
                if cursor.fetchone():
                    st.error(f"Doctor ID '{did.strip().upper()}' is already registered.")
                else:
                    cursor.execute(
                        """INSERT INTO doc (DID, DFNAME, DMNAME, DLNAME, FIELD, DOJ)
                           VALUES (?, ?, ?, ?, ?, ?);""",
                        (
                            did.strip().upper(),
                            dfname.strip(),
                            dmname.strip() or None,
                            dlname.strip(),
                            field.strip(),
                            doj.strftime("%Y-%m-%d")
                        )
                    )
                    conn.commit()
                    conn.close()
                    st.session_state["doctor_added_message"] = f"Dr. {dfname.strip()} {dlname.strip()} registered successfully."
                    st.session_state["show_doctor_registration"] = False
                    st.rerun()
                conn.close()

    if df_docs.empty:
        st.warning("No doctors registered in the system.")
        return

    # Add Doctor Name
    df_docs["Doctor Name"] = df_docs.apply(
        lambda r: f"Dr. {r['DFNAME']} {r['DMNAME'] + ' ' if (pd.notna(r['DMNAME']) and r['DMNAME']) else ''}{r['DLNAME']}".strip(),
        axis=1
    )

    doc_tabs = st.tabs(["Doctor Directory", "Weekly Schedules (Mon-Sun)", "Doctor Profile"])

    # DOCTOR DIRECTORY
    with doc_tabs[0]:
        st.subheader("Registered Physicians & Specialists")
        
        c_search, c_field = st.columns([2, 1])
        with c_search:
            doc_search = st.text_input("Search Doctor by ID or Name", placeholder="e.g. DOC101, Chen, Robert...")
        with c_field:
            field_options = ["All Fields"] + sorted(list(df_docs["FIELD"].dropna().unique()))
            selected_field = st.selectbox("Specialization Filter", field_options)

        filtered_docs = df_docs.copy()
        if doc_search:
            s = doc_search.strip().lower()
            filtered_docs = filtered_docs[
                filtered_docs["DID"].str.lower().str.contains(s, na=False) |
                filtered_docs["Doctor Name"].str.lower().str.contains(s, na=False)
            ]
        if selected_field != "All Fields":
            filtered_docs = filtered_docs[filtered_docs["FIELD"] == selected_field]

        st.markdown(f"**Found {len(filtered_docs)} doctor(s)**")

        # Visual Cards
        cols = st.columns(3)
        for i, (_, row) in enumerate(filtered_docs.iterrows()):
            with cols[i % 3]:
                st.markdown(
                    f"""
                    <div class="hms-card">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <span class="hms-badge badge-cardio">{row['FIELD']}</span>
                            <span style="font-weight: 700; color: #475569; font-size: 0.85rem;">{row['DID']}</span>
                        </div>
                        <h3 style="margin: 0; font-size: 1.25rem;">{row['Doctor Name']}</h3>
                        <p style="color: #64748b; font-size: 0.9rem; margin-top: 4px; margin-bottom: 12px;">Date of Joining: {row['DOJ']}</p>
                        <div style="background-color: #f8fafc; border-radius: 8px; padding: 8px 12px; display: flex; justify-content: space-between;">
                            <span style="font-size: 0.85rem; color: #64748b;">Assigned Patients:</span>
                            <span style="font-weight: 700; color: #0f766e;">{row['PatientCount']}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # Tabular View
        st.markdown("#### Doctor Directory Table")
        st.dataframe(
            filtered_docs[["DID", "Doctor Name", "FIELD", "DOJ", "PatientCount"]].rename(columns={
                "DID": "Doctor ID",
                "FIELD": "Medical Specialization",
                "DOJ": "Date of Joining",
                "PatientCount": "Treated Patients"
            }),
            use_container_width=True,
            hide_index=True
        )

    # WEEKLY SCHEDULES
    with doc_tabs[1]:
        st.subheader("Weekly Duty Schedules (Monday – Sunday)")
        st.caption("Daily shifts from the dtime table.")

        schedule_cols = ["DID", "Doctor Name", "FIELD", "MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        sched_df = df_docs[schedule_cols].rename(columns={
            "DID": "Doctor ID",
            "FIELD": "Specialization",
            "MON": "Monday",
            "TUE": "Tuesday",
            "WED": "Wednesday",
            "THU": "Thursday",
            "FRI": "Friday",
            "SAT": "Saturday",
            "SUN": "Sunday"
        })
        st.dataframe(sched_df, use_container_width=True, hide_index=True)

    # DETAILED PROFILE
    with doc_tabs[2]:
        st.subheader("Doctor Profile & Schedule")
        profile_did = st.selectbox(
            "Select Doctor",
            options=df_docs["DID"].tolist(),
            format_func=lambda x: f"{x} - {next(r['Doctor Name'] + ' (' + r['FIELD'] + ')' for _, r in df_docs.iterrows() if r['DID'] == x)}"
        )

        doc_row = df_docs[df_docs["DID"] == profile_did].iloc[0]

        p_col1, p_col2 = st.columns([1, 2])
        with p_col1:
            st.markdown(
                f"""
                <div class="hms-card">
                    <h2 style="text-align: center; margin-bottom: 2px;">{doc_row['Doctor Name']}</h2>
                    <p style="text-align: center; color: #0f766e; font-weight: 600; margin-bottom: 15px;">{doc_row['FIELD']}</p>
                    <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 15px 0;">
                    <p><strong>Doctor ID (DID):</strong> <code>{doc_row['DID']}</code></p>
                    <p><strong>Date of Joining (DOJ):</strong> {doc_row['DOJ']}</p>
                    <p><strong>Active Patients Treated:</strong> {doc_row['PatientCount']}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

        with p_col2:
            st.markdown("### Weekly Schedule (Mon–Sun)")
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            day_keys = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
            schedule_data = [{"Day": d, "Schedule": doc_row[k] or "OFF"} for d, k in zip(days, day_keys)]
            st.table(pd.DataFrame(schedule_data))

            st.markdown("### Assigned Patients (Relationship: doc Treats Patient via DID)")
            conn = get_db_connection()
            query_assigned = """
                SELECT PNUM, FNAME || ' ' || LNAME as PatientName, GENDER, DOB, DOA, DOD, WARD, REASON
                FROM Patient
                WHERE DID = ?;
            """
            assigned_df = pd.read_sql_query(query_assigned, conn, params=(profile_did,))
            conn.close()

            if assigned_df.empty:
                st.info("No patients currently assigned to this doctor.")
            else:
                assigned_df["Age"] = assigned_df["DOB"].apply(calculate_age)
                assigned_df["Status"] = assigned_df["DOD"].apply(
                    lambda d: "Discharged" if (pd.notna(d) and str(d).strip() and str(d).strip().upper() not in ["NONE", "NAN"]) else "Admitted (Active)"
                )
                st.dataframe(
                    assigned_df[["PNUM", "PatientName", "Age", "GENDER", "DOA", "WARD", "REASON", "Status"]].rename(columns={
                        "PNUM": "Patient ID",
                        "PatientName": "Name",
                        "GENDER": "Gender",
                        "DOA": "Admission Date",
                        "WARD": "Ward",
                        "REASON": "Reason"
                    }),
                    use_container_width=True,
                    hide_index=True
                )


# NURSE MANAGEMENT MODULE
def render_nurse_management():
    st.title(" Nurse Management")
    st.markdown("Nursing staff directory, ward assignments, and ward-patient correlations.")

    added_message = st.session_state.pop("nurse_added_message", None)
    if added_message:
        st.success(added_message)

    conn = get_db_connection()
    query_nurses = """
        SELECT NID, NFNAME, NMNAME, NLNAME, WARD, DOJ
        FROM nurse
        ORDER BY NID ASC;
    """
    df_nurses = pd.read_sql_query(query_nurses, conn)
    conn.close()

    add_label = "Register First Nurse" if df_nurses.empty else "Add Nurse"
    if st.button(add_label, key="open_nurse_registration"):
        st.session_state["show_nurse_registration"] = not st.session_state.get("show_nurse_registration", False)

    if st.session_state.get("show_nurse_registration", False):
        st.subheader("Register Nurse")
        with st.form("add_nurse_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                nid = st.text_input("Nurse ID (NID) *", placeholder="e.g. NUR201")
            with c2:
                nfname = st.text_input("First Name *")
            with c3:
                nlname = st.text_input("Last Name *")

            c4, c5, c6 = st.columns(3)
            with c4:
                nmname = st.text_input("Middle Name")
            with c5:
                ward = st.selectbox(
                    "Assigned Ward *",
                    ["Ward 101", "Ward 102", "Ward 201", "ICU", "Cardiology Ward", "Pediatric Ward", "Emergency", "Orthopedic Ward"]
                )
            with c6:
                doj = st.date_input("Date of Joining *", value=date.today())

            submit_nurse = st.form_submit_button("Save Nurse", use_container_width=True)

        if submit_nurse:
            if not nid.strip() or not nfname.strip() or not nlname.strip():
                st.error("Please fill in the required nurse fields.")
            else:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM nurse WHERE NID = ?;", (nid.strip().upper(),))
                if cursor.fetchone():
                    st.error(f"Nurse ID '{nid.strip().upper()}' is already registered.")
                else:
                    cursor.execute(
                        """INSERT INTO nurse (NID, NFNAME, NMNAME, NLNAME, WARD, DOJ)
                           VALUES (?, ?, ?, ?, ?, ?);""",
                        (
                            nid.strip().upper(),
                            nfname.strip(),
                            nmname.strip() or None,
                            nlname.strip(),
                            ward,
                            doj.strftime("%Y-%m-%d")
                        )
                    )
                    conn.commit()
                    conn.close()
                    st.session_state["nurse_added_message"] = f"{nfname.strip()} {nlname.strip()} registered successfully."
                    st.session_state["show_nurse_registration"] = False
                    st.rerun()
                conn.close()

    if df_nurses.empty:
        st.warning("No nurse records found in the database.")
        return

    df_nurses["Nurse Name"] = df_nurses.apply(
        lambda r: f"{r['NFNAME']} {r['NMNAME'] + ' ' if (pd.notna(r['NMNAME']) and r['NMNAME']) else ''}{r['NLNAME']}".strip(),
        axis=1
    )

    def calc_service(doj_str):
        try:
            doj = datetime.strptime(str(doj_str).strip(), "%Y-%m-%d").date()
            years = (date.today() - doj).days / 365.25
            return f"{years:.1f} yrs"
        except Exception:
            return "N/A"

    df_nurses["Tenure"] = df_nurses["DOJ"].apply(calc_service)

    # Top metrics
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Total Nursing Staff", len(df_nurses))
    with m2:
        st.metric("Wards Covered", df_nurses["WARD"].nunique())
    with m3:
        st.metric("Largest Ward Team", f"{df_nurses['WARD'].value_counts().index[0]} ({df_nurses['WARD'].value_counts().iloc[0]})")

    # Search & Filtering
    col_search, col_ward = st.columns([2, 1])
    with col_search:
        nurse_search = st.text_input(" Search Nurse by ID or Name", placeholder="e.g. NUR201, Emily, Watson...")
    with col_ward:
        all_wards = ["All Wards"] + sorted(list(df_nurses["WARD"].dropna().unique()))
        selected_ward = st.selectbox(" Filter Nurses by Ward", all_wards)

    filtered_nurses = df_nurses.copy()

    if nurse_search:
        term = nurse_search.strip().lower()
        filtered_nurses = filtered_nurses[
            filtered_nurses["NID"].str.lower().str.contains(term, na=False) |
            filtered_nurses["Nurse Name"].str.lower().str.contains(term, na=False)
        ]

    if selected_ward != "All Wards":
        filtered_nurses = filtered_nurses[filtered_nurses["WARD"] == selected_ward]

    st.markdown(f"**Displaying {len(filtered_nurses)} of {len(df_nurses)} nursing staff members**")

    # Table
    st.dataframe(
        filtered_nurses[["NID", "Nurse Name", "WARD", "DOJ", "Tenure"]].rename(columns={
            "NID": "Nurse ID",
            "WARD": "Assigned Ward",
            "DOJ": "Date of Joining",
            "Tenure": "Service Tenure"
        }),
        use_container_width=True,
        hide_index=True
    )
    # Patients associated with nurse's ward
    st.markdown("---")
    st.subheader(" Patients in Nurse's Ward (Relationship: nurse associated with Patient via WARD)")
    
    inspect_nid = st.selectbox(
        "Select Nurse to View Ward Patients",
        options=df_nurses["NID"].tolist(),
        format_func=lambda nid: f"{nid} - {next(r['Nurse Name'] + ' (Assigned to ' + r['WARD'] + ')' for _, r in df_nurses.iterrows() if r['NID'] == nid)}"
    )
    nurse_selected_ward = df_nurses[df_nurses["NID"] == inspect_nid]["WARD"].iloc[0]

    conn = get_db_connection()
    ward_pts_query = """
        SELECT p.PNUM, p.FNAME || ' ' || p.LNAME as PatientName, p.GENDER, p.DOB, p.DOA, p.DOD, p.REASON,
               'Dr. ' || d.DFNAME || ' ' || d.DLNAME as AttendingDoc
        FROM Patient p
        LEFT JOIN doc d ON p.DID = d.DID
        WHERE p.WARD = ?;
    """
    ward_pts_df = pd.read_sql_query(ward_pts_query, conn, params=(nurse_selected_ward,))
    conn.close()

    if ward_pts_df.empty:
        st.info(f"No patients currently admitted to {nurse_selected_ward}.")
    else:
        ward_pts_df["Age"] = ward_pts_df["DOB"].apply(calculate_age)
        ward_pts_df["Status"] = ward_pts_df["DOD"].apply(
            lambda d: "Discharged" if (pd.notna(d) and str(d).strip() and str(d).strip().upper() not in ["NONE", "NAN"]) else "Admitted (Active)"
        )
        st.dataframe(
            ward_pts_df[["PNUM", "PatientName", "Age", "GENDER", "DOA", "AttendingDoc", "REASON", "Status"]].rename(columns={
                "PNUM": "Patient ID",
                "PatientName": "Patient Name",
                "GENDER": "Gender",
                "DOA": "Admission Date",
                "AttendingDoc": "Doctor",
                "REASON": "Clinical Reason"
            }),
            use_container_width=True,
            hide_index=True
        )
# DASHBOARD OVERVIEW 
def render_dashboard():
    st.title("Hospital Operations Dashboard")
    st.write(f"Welcome, **{st.session_state.get('username', 'Staff Member')}**! Live status of clinical operations.")

    # Fetch dashboard statistics
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM Patient")
    total_patients = c.fetchone()[0]

    c.execute("""
        SELECT COUNT(*) FROM Patient
        WHERE DOD IS NULL OR TRIM(DOD) = ''
        OR UPPER(TRIM(DOD)) IN ('ACTIVE', 'NONE')
    """)
    active_patients = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM doc")
    total_docs = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM nurse")
    total_nurses = c.fetchone()[0]
    conn.close()

    # Display statistics
    m1, m2, m3, m4 = st.columns(4)

    m1.metric("Admitted Patients", active_patients, delta="Active in Wards")
    m2.metric("Total Patient Files", total_patients)
    m3.metric("Attending Doctors", total_docs)
    m4.metric("Nursing Staff", total_nurses)

    st.divider()

    col_recent, col_quick = st.columns([2, 1])

    # Recent admissions
    with col_recent:
        st.subheader("Recent Admissions")

        conn = get_db_connection()

        query = """
            SELECT p.PNUM, p.FNAME || ' ' || p.LNAME AS PatientName,
                   p.GENDER, p.DOB, p.DOA, p.WARD,
                   'Dr. ' || d.DFNAME || ' ' || d.DLNAME AS Doctor
            FROM Patient p
            LEFT JOIN doc d ON p.DID = d.DID
            ORDER BY p.PNUM DESC
            LIMIT 5
        """

        recent_df = pd.read_sql_query(query, conn)
        conn.close()

        if recent_df.empty:
            st.info("No recent patients found.")
        else:
            recent_df["Age"] = recent_df["DOB"].apply(calculate_age)

            recent_df = recent_df[
                ["PNUM", "PatientName", "Age", "GENDER", "DOA", "WARD", "Doctor"]
            ]

            recent_df = recent_df.rename(columns={
                "PNUM": "ID",
                "PatientName": "Patient",
                "GENDER": "Gender",
                "DOA": "Admitted",
                "WARD": "Ward"
            })

            st.dataframe(recent_df, use_container_width=True, hide_index=True)

    # System information
    with col_quick:
        st.subheader("System Info & Status")

        st.write("**Database:** `hms.db` (SQLite3)")
        st.write(f"**System Date:** {date.today().strftime('%B %d, %Y')}")
        st.write(f"**Logged in as:** `{st.session_state.get('username')}`")
        st.write("**Database Status:** 🟢 Online")

        st.divider()

        st.caption(
            "Use the sidebar to manage patients, review doctor duty rosters, "
            "and manage nursing allocations by ward."
        )


# MAIN 
def main():
    # Set default login details
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if "username" not in st.session_state:
        st.session_state["username"] = None

    # Show login page if user is not logged in
    if not st.session_state["authenticated"]:
        render_auth_page()
        return

    # Display sidebar
    with st.sidebar:
        st.title("Hospital Portal")
        st.caption("Healthcare Operations Roster")

        st.write(f"Staff User: {st.session_state['username']}")

        # Logout
        if st.button("Logout"):
            st.session_state["authenticated"] = False
            st.session_state["username"] = None
            st.rerun()

        # Navigation menu
        nav = st.radio(
            "Navigation Menu",
            ["Operations Dashboard", "Patient Management",
             "Doctor Management", "Nurse Management"]
        )

    # Display selected page
    if nav == "Operations Dashboard":
        render_dashboard()
    elif nav == "Patient Management":
        render_patient_management()
    elif nav == "Doctor Management":
        render_doctor_management()
    else:
        render_nurse_management()


if __name__ == "__main__":
    main()
