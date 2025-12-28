import streamlit as st
import pandas as pd
from io import BytesIO

# =====================================================
# Utility: Create downloadable INPUT TEMPLATE
# =====================================================
def get_input_template():
    df = pd.DataFrame({
        "Clinikk ID": ["C0001", "C0002", "C0003"],
        "Amount": [5000, 3500, 4200],
        "Status": ["Active", "Inactive", "Affiliate"]
    })

    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Input")
    return output.getvalue()

# =====================================================
# Utility: Convert result DF to Excel
# =====================================================
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Assignments")
    return output.getvalue()

# =====================================================
# Greedy load balancer (amount based)
# =====================================================
def GreedyFriendsAlgorithm(amounts, k):
    amounts = sorted(amounts, reverse=True)
    totals = [0] * k
    assignments = [[] for _ in range(k)]

    for amt in amounts:
        idx = totals.index(min(totals))
        totals[idx] += amt
        assignments[idx].append(amt)

    return assignments

# =====================================================
# Assign Clinikk IDs safely (no reuse)
# =====================================================
def AssigningClinikkIds(row):
    amt = row["AssignedAmount"]
    status = row["Status"]

    match = data[
        (data["Amount"] == amt) &
        (data["Status"] == status) &
        ~(data["Clinikk ID"].isin(used_ids))
    ]

    if not match.empty:
        cid = match.iloc[0]["Clinikk ID"]
        used_ids.append(cid)
        return cid
    return None

# =====================================================
# STREAMLIT UI
# =====================================================
st.header("🔁 Renewal Distributor (Amount + Status Balanced)")

st.markdown("""
This tool distributes renewals across persons such that:
- 💰 **Total amount is evenly balanced**
- 🧩 **Active / Inactive / Affiliate are evenly distributed**
- 🔒 **Clinikk IDs are never reused**
""")

# -------------------------------
# INPUT TEMPLATE DOWNLOAD
# -------------------------------
st.subheader("📥 Input File Format")

st.markdown("""
**Required columns (do not rename):**
- `Clinikk ID`
- `Amount`
- `Status` → allowed values:
  - `Active`
  - `Inactive`
  - `Affiliate`
""")

template_file = get_input_template()

st.download_button(
    label="⬇️ Download Input Template (Excel)",
    data=template_file,
    file_name="Renewal_Input_Template.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.divider()

# -------------------------------
# USER INPUTS
# -------------------------------
n = st.number_input(
    "Enter number of persons for renewals:",
    min_value=1,
    step=1
)

persons = [f"Person{i+1}" for i in range(n)]
used_ids = []

uploaded_file = st.file_uploader(
    "Upload filled input file (CSV / Excel)",
    type=["csv", "xlsx", "xls"]
)

# =====================================================
# MAIN LOGIC
# =====================================================
if uploaded_file and n > 0:

    # Read file
    if uploaded_file.name.endswith(".csv"):
        data = pd.read_csv(uploaded_file)
    else:
        data = pd.read_excel(uploaded_file, engine="openpyxl")

    # -------------------------------
    # VALIDATIONS
    # -------------------------------
    required_cols = {"Clinikk ID", "Amount", "Status"}
    if not required_cols.issubset(data.columns):
        st.error("❌ Missing required columns in input file.")
        st.stop()

    allowed_statuses = {"Active", "Inactive", "Affiliate"}
    invalid_statuses = set(data["Status"].unique()) - allowed_statuses
    if invalid_statuses:
        st.error(f"❌ Invalid Status values found: {invalid_statuses}")
        st.stop()

    if data["Clinikk ID"].duplicated().any():
        st.error("❌ Duplicate Clinikk IDs found in input.")
        st.stop()

    # -------------------------------
    # STATUS-WISE SPLIT
    # -------------------------------
    statuses = ["Active", "Inactive", "Affiliate"]

    status_data = {
        status: data[data["Status"] == status]
        for status in statuses
    }

    # -------------------------------
    # GREEDY ASSIGNMENT PER STATUS
    # -------------------------------
    status_assignments = {}

    for status in statuses:
        amounts = status_data[status]["Amount"].tolist()
        status_assignments[status] = GreedyFriendsAlgorithm(amounts, n)

    # -------------------------------
    # BUILD FINAL RESULT
    # -------------------------------
    all_frames = []

    for i in range(n):
        for status in statuses:
            assigned_amounts = status_assignments[status][i]

            if assigned_amounts:
                df = pd.DataFrame(
                    assigned_amounts,
                    columns=["AssignedAmount"]
                )
                df["Status"] = status
                df["Person"] = persons[i]
                all_frames.append(df)

    result_df = pd.concat(all_frames, ignore_index=True)

    # Assign Clinikk IDs
    result_df["Clinikk ID"] = result_df.apply(
        AssigningClinikkIds, axis=1
    )

    # -------------------------------
    # SUMMARY TABLE (IMPORTANT)
    # -------------------------------
    st.subheader("📊 Distribution Summary")

    summary = (
        result_df
        .groupby(["Person", "Status"])
        .agg(
            Count=("AssignedAmount", "count"),
            TotalAmount=("AssignedAmount", "sum")
        )
        .reset_index()
    )

    st.dataframe(summary, use_container_width=True)

    # -------------------------------
    # OUTPUT DOWNLOAD
    # -------------------------------
    output_excel = to_excel(result_df)

    st.download_button(
        label="⬇️ Download Assignment Output (Excel)",
        data=output_excel,
        file_name="Renewal_Distribution_Output.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
