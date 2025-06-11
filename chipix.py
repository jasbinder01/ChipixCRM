import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from PIL import Image
import re
import csv
from io import StringIO

# ────────────────────────────────────────────────────────────────────────────────
# 1. FIREBASE SETUP
# ────────────────────────────────────────────────────────────────────────────────
if not firebase_admin._apps:
    cred = credentials.Certificate("chipix.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()
customers_ref = db.collection("chipix_customers")

# ────────────────────────────────────────────────────────────────────────────────
# 2. ADMIN LOGIN
# ────────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Chipix CRM", layout="wide")
st.markdown("<h1 style='font-family: Arial; color: #1363DF;'>Chipix CRM - Customer, Sales & Service Management</h1>", unsafe_allow_html=True)

admin_username = st.text_input("Admin Username")
admin_password = st.text_input("Admin Password", type="password")

if admin_username != "admin" or admin_password != "Chipix@babaji1":
    st.warning("🚫 Unauthorized. Enter correct credentials to proceed.")
    st.stop()

# ────────────────────────────────────────────────────────────────────────────────
# 3. ADD NEW ENTRY (Purchase or Service)
# ────────────────────────────────────────────────────────────────────────────────
with st.expander("➕ Add New Entry"):
    name = st.text_input("Customer Name")
    phone = st.text_input("Phone Number")
    entry_type = st.radio("Entry Type", ["Purchase", "Service"])

    def validate_inputs():
        if not name.replace(" ", "").isalpha():
            st.error("❌ Name must contain only letters.")
            return False
        if not phone.isdigit() or len(phone) != 10:
            st.error("❌ Phone number must be exactly 10 digits.")
            return False
        return True

    details = {}
    if entry_type == "Purchase":
        details['product'] = st.text_input("Product Name")
        details['price'] = st.number_input("Amount Paid (₹)", min_value=0.0, format="%.2f")
        warranty_duration = st.selectbox("Warranty Period", ["1 Month", "3 Months", "6 Months", "1 Year", "2 Years"])
        details['warranty'] = warranty_duration
    else:
        details['item'] = st.text_input("Electronic Item")
        details['issue'] = st.text_area("Issue Description")
        details['status'] = st.selectbox("Initial Status", ["Pending", "In Progress", "Completed"])

    if st.button("Submit Entry"):
        if validate_inputs() and all(details.values()):
            entry = {
                "name": name,
                "phone": phone,
                "entry_type": entry_type,
                "timestamp": datetime.now(),
                **details
            }
            customers_ref.add(entry)
            st.success(f"✅ {entry_type} entry for {name} recorded.")
        else:
            st.error("❌ Please fill all required fields.")

# ────────────────────────────────────────────────────────────────────────────────
# 4. FETCH RECORDS
# ────────────────────────────────────────────────────────────────────────────────
def fetch_customers():
    return [
        {**doc.to_dict(), "id": doc.id}
        for doc in customers_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).stream()
    ]

# ────────────────────────────────────────────────────────────────────────────────
# 5. SEARCH RECORDS & UPDATE STATUS
# ────────────────────────────────────────────────────────────────────────────────
with st.expander("🔍 Search & Manage Customer"):
    query = st.text_input("Search by Name or Phone")
    data = fetch_customers()
    if query:
        filtered = [e for e in data if query.lower() in e.get("name", "").lower() or query in e.get("phone", "")]
        if filtered:
            st.write(f"📄 Found {len(filtered)} matching records:")
            for r in filtered:
                if r.get('entry_type') == 'Purchase':
                    st.success(f"🛒 **{r['name']}** | {r['phone']} | {r['product']} | ₹{r['price']} | {r['warranty']}")
                else:
                    st.info(f"🛠️ **{r['name']}** | {r['phone']} | {r['item']} | {r['issue']} | Status: {r['status']}")
                    cols = st.columns([3, 3, 3])
                    cols[0].markdown(f"**{r['name']}** | {r['item']}")
                    new_status = cols[1].selectbox("Update Status", ["Pending", "In Progress", "Completed"],
                                                   index=["Pending", "In Progress", "Completed"].index(r["status"]),
                                                   key=r["id"])
                    if new_status != r["status"]:
                        customers_ref.document(r["id"]).update({"status": new_status})
                        st.success(f"✅ Status updated for {r['name']}")
        else:
            st.warning("No matching records found.")

# ────────────────────────────────────────────────────────────────────────────────
# 6. EXPORT TO CSV
# ────────────────────────────────────────────────────────────────────────────────
with st.expander("📤 Export Data"):
    export_data = fetch_customers()
    if st.button("Download CSV"):
        csv_buffer = StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=export_data[0].keys())
        writer.writeheader()
        writer.writerows(export_data)
        st.download_button("📥 Click to Download CSV", csv_buffer.getvalue(), "chipix_data.csv", "text/csv")
