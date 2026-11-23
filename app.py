
import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.express as px
from datetime import date, timedelta
from io import BytesIO

# =====================================================
# PAGE CONFIGURATION
# =====================================================
st.set_page_config(
    page_title="ExpenseIQ | Personal Finance",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB = "expenses.db"

CATEGORIES = [
    "Food & Dining", "Groceries", "Transport", "Shopping",
    "Bills & Utilities", "Entertainment", "Healthcare",
    "Education", "Travel", "Rent", "Other"
]

PAYMENTS = ["UPI", "Cash", "Debit Card", "Credit Card", "Net Banking"]

# =====================================================
# PROFESSIONAL RED THEME
# =====================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: #F5F6FA;
}

[data-testid="stSidebar"] {
    background: #171923;
}

[data-testid="stSidebar"] * {
    color: #FFFFFF !important;
}

[data-testid="stMetric"] {
    background: white;
    padding: 19px;
    border-radius: 13px;
    border: 1px solid #E9E9EF;
    box-shadow: 0 3px 12px rgba(0,0,0,0.035);
}

[data-testid="stMetricLabel"] {
    color: #737789 !important;
    font-weight: 600;
}

[data-testid="stMetricValue"] {
    color: #202331 !important;
    font-weight: 800;
}

h1, h2, h3 {
    color: #202331;
    font-weight: 750;
}

.stButton > button {
    background: #D92332;
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    padding: 9px 18px;
}

.stButton > button:hover {
    background: #B91827;
    color: white;
    border: none;
}

div[data-testid="stForm"] {
    background: white;
    padding: 20px;
    border-radius: 12px;
    border: 1px solid #E9E9EF;
}

div[data-testid="stDataFrame"] {
    border-radius: 10px;
}

hr {
    border-color: #E7E7ED;
}

.hero {
    background: linear-gradient(120deg, #991B2B, #E52D3D);
    padding: 27px 30px;
    border-radius: 15px;
    color: white;
    margin-bottom: 23px;
}

.hero h1 {
    color: white;
    margin: 0;
    font-size: 30px;
}

.hero p {
    color: #FFE5E8;
    margin: 7px 0 0 0;
}

.section-note {
    color: #777B89;
    font-size: 13px;
}

</style>
""", unsafe_allow_html=True)

# =====================================================
# DATABASE
# =====================================================
def get_connection():
    return sqlite3.connect(DB, check_same_thread=False)

def init_database():
    with get_connection() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tx_date TEXT NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT,
                payment_method TEXT,
                type TEXT DEFAULT 'Expense'
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month TEXT NOT NULL,
                category TEXT NOT NULL,
                limit_amount REAL NOT NULL,
                UNIQUE(month, category)
            )
        """)

        count = con.execute(
            "SELECT COUNT(*) FROM transactions"
        ).fetchone()[0]

        if count == 0:
            create_sample_data(con)

def create_sample_data(con):
    """Generate realistic demo transactions."""

    rng = np.random.default_rng(42)

    merchants = {
        "Food & Dining": [
            "Swiggy Order", "Zomato Restaurant", "Cafe Coffee",
            "Restaurant Dinner"
        ],
        "Groceries": [
            "DMart Shopping", "Reliance Fresh", "Grocery Store"
        ],
        "Transport": [
            "Uber Ride", "Ola Cab", "Petrol", "Metro Travel"
        ],
        "Shopping": [
            "Amazon Purchase", "Myntra Shopping", "Clothing Store"
        ],
        "Bills & Utilities": [
            "Electricity Bill", "Mobile Recharge", "Internet Bill"
        ],
        "Entertainment": [
            "Netflix Subscription", "Movie Tickets", "Spotify"
        ],
        "Healthcare": [
            "Pharmacy", "Medical Checkup", "Hospital Visit"
        ],
        "Education": [
            "Online Course", "Books Purchase", "Course Fee"
        ],
        "Travel": [
            "Hotel Booking", "Travel Tickets", "Trip Expenses"
        ],
        "Rent": ["Monthly House Rent"],
        "Other": ["Personal Expense", "Miscellaneous"]
    }

    rows = []

    for i in range(180):
        category = rng.choice(list(merchants.keys()))
        description = rng.choice(merchants[category])
        amount = round(float(rng.integers(100, 3500)), 2)
        tx_date = date.today() - timedelta(days=int(rng.integers(0, 180)))
        payment = rng.choice(PAYMENTS)

        rows.append((
            str(tx_date),
            description,
            amount,
            category,
            payment,
            "Expense"
        ))

    # Add monthly income records
    for i in range(6):
        income_date = date.today() - timedelta(days=i * 30 + 2)
        rows.append((
            str(income_date),
            "Monthly Salary",
            35000.0,
            "Income",
            "Net Banking",
            "Income"
        ))

    con.executemany("""
        INSERT INTO transactions
        (tx_date, description, amount, category, payment_method, type)
        VALUES (?, ?, ?, ?, ?, ?)
    """, rows)

# =====================================================
# CATEGORY DETECTION
# =====================================================
def auto_category(description):
    text = str(description).lower()

    rules = {
        "Food & Dining": ["swiggy", "zomato", "restaurant", "cafe", "food"],
        "Groceries": ["grocery", "dmart", "reliance fresh", "supermarket"],
        "Transport": ["uber", "ola", "petrol", "metro", "bus", "fuel"],
        "Shopping": ["amazon", "flipkart", "myntra", "shopping"],
        "Bills & Utilities": ["electricity", "recharge", "internet", "wifi", "bill"],
        "Entertainment": ["netflix", "spotify", "movie", "cinema"],
        "Healthcare": ["medical", "hospital", "pharmacy", "doctor"],
        "Education": ["course", "books", "education", "tuition"],
        "Travel": ["hotel", "travel", "flight", "train", "trip"],
        "Rent": ["rent"]
    }

    for category, keywords in rules.items():
        if any(word in text for word in keywords):
            return category

    return "Other"

# =====================================================
# DATA FUNCTIONS
# =====================================================
def load_data():
    with get_connection() as con:
        df = pd.read_sql_query(
            "SELECT * FROM transactions ORDER BY tx_date DESC",
            con
        )

    if not df.empty:
        df["tx_date"] = pd.to_datetime(df["tx_date"])
        df["month"] = df["tx_date"].dt.strftime("%Y-%m")
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

    return df

def add_transaction(tx_date, description, amount, category, payment, tx_type):
    if category == "Auto Detect":
        category = "Income" if tx_type == "Income" else auto_category(description)

    with get_connection() as con:
        con.execute("""
            INSERT INTO transactions
            (tx_date, description, amount, category, payment_method, type)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            str(tx_date), description.strip(), abs(float(amount)),
            category, payment, tx_type
        ))

def delete_transaction(tx_id):
    with get_connection() as con:
        con.execute("DELETE FROM transactions WHERE id=?", (tx_id,))

def update_transaction(tx_id, tx_date, description, amount, category, payment, tx_type):
    with get_connection() as con:
        con.execute("""
            UPDATE transactions
            SET tx_date=?, description=?, amount=?, category=?,
                payment_method=?, type=?
            WHERE id=?
        """, (
            str(tx_date), description, abs(float(amount)),
            category, payment, tx_type, tx_id
        ))

def save_budget(month, category, amount):
    with get_connection() as con:
        con.execute("""
            INSERT INTO budgets (month, category, limit_amount)
            VALUES (?, ?, ?)
            ON CONFLICT(month, category)
            DO UPDATE SET limit_amount=excluded.limit_amount
        """, (month, category, float(amount)))

def load_budgets(month):
    with get_connection() as con:
        return pd.read_sql_query(
            "SELECT * FROM budgets WHERE month=?",
            con,
            params=(month,)
        )

# =====================================================
# CSV IMPORT
# =====================================================
def import_csv(uploaded_file):
    df = pd.read_csv(uploaded_file)
    df.columns = [str(c).strip().lower().replace("_", " ") for c in df.columns]

    aliases = {
        "date": ["date", "tx date", "transaction date"],
        "description": ["description", "narration", "merchant", "details"],
        "amount": ["amount", "value", "transaction amount"],
        "category": ["category", "expense category"],
        "payment": ["payment method", "payment", "mode", "account"],
        "type": ["type", "transaction type"]
    }

    mapped = {}

    for field, options in aliases.items():
        for option in options:
            if option in df.columns:
                mapped[field] = option
                break

    if "date" not in mapped or "amount" not in mapped:
        raise ValueError("CSV must contain at least Date and Amount columns.")

    if "description" not in mapped:
        df["description"] = "Imported Transaction"
        mapped["description"] = "description"

    imported = 0

    with get_connection() as con:
        for _, row in df.iterrows():
            try:
                tx_date = pd.to_datetime(row[mapped["date"]], errors="raise").date()
                amount = abs(float(str(row[mapped["amount"]]).replace(",", "").replace("₹", "").strip()))

                if amount <= 0:
                    continue

                description = str(row[mapped["description"]])
                tx_type = str(row[mapped["type"]]).strip().title() if "type" in mapped else "Expense"

                if tx_type not in ["Income", "Expense"]:
                    tx_type = "Expense"

                category = (
                    str(row[mapped["category"]])
                    if "category" in mapped and pd.notna(row[mapped["category"]])
                    else ("Income" if tx_type == "Income" else auto_category(description))
                )

                payment = (
                    str(row[mapped["payment"]])
                    if "payment" in mapped and pd.notna(row[mapped["payment"]])
                    else "Other"
                )

                con.execute("""
                    INSERT INTO transactions
                    (tx_date, description, amount, category, payment_method, type)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (str(tx_date), description, amount, category, payment, tx_type))

                imported += 1

            except (ValueError, TypeError):
                continue

    return imported

# =====================================================
# START APPLICATION
# =====================================================
init_database()
df = load_data()

# =====================================================
# SIDEBAR
# =====================================================
with st.sidebar:
    st.markdown("## 🔴 ExpenseIQ")
    st.caption("PERSONAL FINANCE ANALYTICS")
    st.divider()

    page = st.radio(
        "MAIN MENU",
        ["Dashboard", "Transactions", "Budgets", "Reports"],
        label_visibility="visible"
    )

    st.divider()
    st.markdown("### 💡 Quick Insight")

    if not df.empty:
        total_expense = df.loc[df["type"] == "Expense", "amount"].sum()
        st.metric("All-time Expenses", f"₹{total_expense:,.0f}")

    st.caption("Manage your money smarter.")

# =====================================================
# MONTH SELECTION
# =====================================================
months = sorted(df["month"].unique().tolist(), reverse=True) if not df.empty else []

if not months:
    months = [date.today().strftime("%Y-%m")]

default_month = date.today().strftime("%Y-%m")
if default_month not in months:
    default_month = months[0]

# =====================================================
# DASHBOARD
# =====================================================
if page == "Dashboard":

    st.markdown("""
    <div class="hero">
        <h1>Personal Finance Dashboard</h1>
        <p>Track your money. Understand your habits. Make smarter decisions.</p>
    </div>
    """, unsafe_allow_html=True)

    selected_month = st.selectbox(
        "Select Reporting Month",
        months,
        index=months.index(default_month)
    )

    month_df = df[df["month"] == selected_month].copy()
    expenses = month_df[month_df["type"] == "Expense"]
    income_df = month_df[month_df["type"] == "Income"]

    total_expense = expenses["amount"].sum()
    total_income = income_df["amount"].sum()
    savings = total_income - total_expense
    savings_rate = (savings / total_income * 100) if total_income > 0 else 0
    transaction_count = len(month_df)
    avg_daily = total_expense / max(
        month_df["tx_date"].dt.date.nunique(), 1
    )

    st.markdown("### Financial Overview")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Expenses", f"₹{total_expense:,.0f}")
    c2.metric("Total Income", f"₹{total_income:,.0f}")
    c3.metric("Net Savings", f"₹{savings:,.0f}")
    c4.metric("Transactions", f"{transaction_count:,}")

    st.markdown("### Spending Insights")

    c1, c2, c3 = st.columns(3)
    c1.metric("Average Daily Spending", f"₹{avg_daily:,.0f}")
    c2.metric("Savings Rate", f"{savings_rate:.1f}%")
    top_category = (
        expenses.groupby("category")["amount"].sum().idxmax()
        if not expenses.empty else "N/A"
    )
    c3.metric("Highest Spending Category", top_category)

    st.divider()

    left, right = st.columns(2)

    with left:
        st.markdown("#### Category-wise Expenses")
        if not expenses.empty:
            category_data = (
                expenses.groupby("category", as_index=False)["amount"]
                .sum().sort_values("amount", ascending=False)
            )

            fig = px.bar(
                category_data,
                x="category",
                y="amount",
                color="amount",
                color_continuous_scale=["#F9A5AC", "#D92332"],
                text_auto=".2s"
            )
            fig.update_layout(
                showlegend=False,
                coloraxis_showscale=False,
                xaxis_title="Category",
                yaxis_title="Amount (₹)",
                plot_bgcolor="white",
                paper_bgcolor="white",
                margin=dict(t=15, b=15)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No expense data for this month.")

    with right:
        st.markdown("#### Payment Method Distribution")
        if not expenses.empty:
            payment_data = (
                expenses.groupby("payment_method", as_index=False)["amount"]
                .sum()
            )
            fig = px.pie(
                payment_data,
                names="payment_method",
                values="amount",
                hole=0.58,
                color_discrete_sequence=[
                    "#D92332", "#EF7D87", "#F5B6BC",
                    "#A91F2D", "#F3D0D3", "#777B89"
                ]
            )
            fig.update_layout(
                margin=dict(t=15, b=15),
                paper_bgcolor="white"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No payment data available.")

    st.divider()

    st.markdown("#### Monthly Spending Trend")

    all_expenses = df[df["type"] == "Expense"]

    if not all_expenses.empty:
        trend = (
            all_expenses.groupby("month", as_index=False)["amount"]
            .sum().sort_values("month")
        )

        fig = px.line(
            trend,
            x="month",
            y="amount",
            markers=True,
            line_shape="spline",
            color_discrete_sequence=["#D92332"]
        )
        fig.update_layout(
            xaxis_title="Month",
            yaxis_title="Expenses (₹)",
            plot_bgcolor="white",
            paper_bgcolor="white"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Daily Spending Trend")

    if not expenses.empty:
        daily = (
            expenses.groupby(expenses["tx_date"].dt.date)["amount"]
            .sum().reset_index()
        )
        daily.columns = ["Date", "Amount"]

        fig = px.area(
            daily,
            x="Date",
            y="Amount",
            color_discrete_sequence=["#E34A57"]
        )
        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Recent Transactions")

    if not month_df.empty:
        st.dataframe(
            month_df[[
                "tx_date", "description", "category",
                "amount", "payment_method", "type"
            ]].head(8),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No transactions available.")

    # Budget warning on dashboard
    budget_df = load_budgets(selected_month)

    if not budget_df.empty:
        st.markdown("#### Budget Alerts")

        for _, budget in budget_df.iterrows():
            actual = expenses[
                expenses["category"] == budget["category"]
            ]["amount"].sum()

            limit = budget["limit_amount"]
            percentage = actual / limit if limit > 0 else 0

            st.write(
                f"**{budget['category']}** — "
                f"₹{actual:,.0f} / ₹{limit:,.0f}"
            )
            st.progress(min(float(percentage), 1.0))

            if actual > limit:
                st.error(f"Budget exceeded by ₹{actual-limit:,.0f}")
            elif percentage >= 0.8:
                st.warning("You are close to your budget limit.")

# =====================================================
# TRANSACTIONS PAGE
# =====================================================
elif page == "Transactions":

    st.title("💳 Transaction Management")
    st.caption("Add, import, edit and manage your financial records.")

    tab1, tab2, tab3 = st.tabs([
        "➕ Add Transaction",
        "📂 Import CSV",
        "📋 Manage Transactions"
    ])

    with tab1:
        st.subheader("Add New Transaction")

        with st.form("add_transaction_form"):
            col1, col2 = st.columns(2)

            with col1:
                tx_date = st.date_input("Transaction Date", value=date.today())
                description = st.text_input("Description", placeholder="e.g. Swiggy Order")
                amount = st.number_input("Amount (₹)", min_value=1.0, value=500.0, step=50.0)

            with col2:
                tx_type = st.selectbox("Transaction Type", ["Expense", "Income"])
                category = st.selectbox(
                    "Category",
                    ["Auto Detect"] + CATEGORIES + ["Income"]
                )
                payment = st.selectbox("Payment Method", PAYMENTS + ["Other"])

            submitted = st.form_submit_button("Save Transaction", use_container_width=True)

            if submitted:
                if not description.strip():
                    st.error("Please enter a description.")
                else:
                    add_transaction(
                        tx_date, description, amount,
                        category, payment, tx_type
                    )
                    st.success("Transaction saved successfully!")
                    st.rerun()

    with tab2:
        st.subheader("Upload Expense CSV")
        st.write(
            "Upload a CSV containing Date and Amount. "
            "Description, Category, Payment Method and Type are optional."
        )

        uploaded_file = st.file_uploader(
            "Choose CSV file",
            type=["csv"],
            key="expense_csv"
        )

        st.caption(
            "Supported column examples: Date, Description, Amount, "
            "Category, Payment Method, Type."
        )

        if uploaded_file and st.button("Import Transactions"):
            try:
                count = import_csv(uploaded_file)
                st.success(f"Successfully imported {count} transactions.")
                st.rerun()
            except Exception as e:
                st.error(f"Import failed: {e}")

    with tab3:
        st.subheader("Manage Existing Transactions")

        if not df.empty:
            search = st.text_input("Search by description or category")

            display_df = df.copy()

            if search:
                display_df = display_df[
                    display_df["description"].str.contains(search, case=False, na=False)
                    | display_df["category"].str.contains(search, case=False, na=False)
                ]

            st.dataframe(
                display_df[[
                    "id", "tx_date", "description", "amount",
                    "category", "payment_method", "type"
                ]],
                use_container_width=True,
                hide_index=True
            )

            st.divider()
            st.markdown("#### Edit or Delete a Transaction")

            ids = display_df["id"].tolist()

            if ids:
                selected_id = st.selectbox(
                    "Select Transaction ID",
                    ids
                )

                selected_row = df[df["id"] == selected_id].iloc[0]

                with st.form("edit_transaction_form"):
                    e1, e2 = st.columns(2)

                    with e1:
                        edit_date = st.date_input(
                            "Date",
                            value=selected_row["tx_date"].date()
                        )
                        edit_description = st.text_input(
                            "Description",
                            value=selected_row["description"]
                        )
                        edit_amount = st.number_input(
                            "Amount",
                            min_value=1.0,
                            value=float(selected_row["amount"])
                        )

                    with e2:
                        current_cat = selected_row["category"]
                        category_options = CATEGORIES + ["Income", "Other"]
                        cat_index = (
                            category_options.index(current_cat)
                            if current_cat in category_options else 0
                        )
                        edit_category = st.selectbox(
                            "Category",
                            category_options,
                            index=cat_index
                        )

                        current_payment = selected_row["payment_method"]
                        payment_options = PAYMENTS + ["Other"]
                        payment_index = (
                            payment_options.index(current_payment)
                            if current_payment in payment_options else 0
                        )
                        edit_payment = st.selectbox(
                            "Payment Method",
                            payment_options,
                            index=payment_index
                        )

                        edit_type = st.selectbox(
                            "Type",
                            ["Expense", "Income"],
                            index=0 if selected_row["type"] == "Expense" else 1
                        )

                    update = st.form_submit_button("Update Transaction")

                    if update:
                        update_transaction(
                            selected_id, edit_date, edit_description,
                            edit_amount, edit_category, edit_payment, edit_type
                        )
                        st.success("Transaction updated.")
                        st.rerun()

                if st.button("🗑️ Delete Selected Transaction"):
                    delete_transaction(selected_id)
                    st.success("Transaction deleted.")
                    st.rerun()

        else:
            st.info("No transactions found.")

# =====================================================
# BUDGET PAGE
# =====================================================
elif page == "Budgets":

    st.title("🎯 Budget Management")
    st.caption("Set spending limits and monitor your monthly expenses.")

    selected_month = st.selectbox(
        "Choose Month",
        months,
        index=months.index(default_month),
        key="budget_month"
    )

    with st.form("budget_form"):
        st.subheader("Set Monthly Category Budget")

        b1, b2 = st.columns(2)

        with b1:
            budget_category = st.selectbox("Expense Category", CATEGORIES)

        with b2:
            budget_amount = st.number_input(
                "Budget Limit (₹)",
                min_value=100.0,
                value=5000.0,
                step=500.0
            )

        save = st.form_submit_button("Save Budget", use_container_width=True)

        if save:
            save_budget(selected_month, budget_category, budget_amount)
            st.success("Budget saved successfully.")
            st.rerun()

    st.divider()
    st.subheader("Monthly Budget Performance")

    budgets = load_budgets(selected_month)
    month_expenses = df[
        (df["month"] == selected_month) &
        (df["type"] == "Expense")
    ]

    if not budgets.empty:
        total_budget = budgets["limit_amount"].sum()

        total_actual = sum(
            month_expenses[
                month_expenses["category"] == row["category"]
            ]["amount"].sum()
            for _, row in budgets.iterrows()
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Budget", f"₹{total_budget:,.0f}")
        c2.metric("Actual Spending", f"₹{total_actual:,.0f}")
        c3.metric("Remaining", f"₹{total_budget-total_actual:,.0f}")

        for _, row in budgets.iterrows():
            actual = month_expenses[
                month_expenses["category"] == row["category"]
            ]["amount"].sum()

            limit = row["limit_amount"]
            percent = actual / limit if limit > 0 else 0

            st.markdown(f"**{row['category']}**")
            st.progress(min(float(percent), 1.0))

            st.write(
                f"Spent: ₹{actual:,.0f} | "
                f"Budget: ₹{limit:,.0f} | "
                f"Used: {percent*100:.1f}%"
            )

            if actual > limit:
                st.error(f"Overspending: ₹{actual-limit:,.0f}")
            elif percent >= 0.8:
                st.warning("Approaching your budget limit.")
            else:
                st.success("Within budget.")

        st.divider()

        st.markdown("#### Delete a Budget")

        budget_categories = budgets["category"].tolist()
        delete_category = st.selectbox(
            "Select budget to delete",
            budget_categories
        )

        if st.button("Delete Budget"):
            with get_connection() as con:
                con.execute(
                    "DELETE FROM budgets WHERE month=? AND category=?",
                    (selected_month, delete_category)
                )
            st.success("Budget deleted.")
            st.rerun()

    else:
        st.info("No budgets set for this month. Add your first budget above.")

# =====================================================
# REPORTS PAGE
# =====================================================
elif page == "Reports":

    st.title("📊 Financial Reports")
    st.caption("Analyze and export your financial records.")

    selected_month = st.selectbox(
        "Select Report Month",
        months,
        index=months.index(default_month),
        key="report_month"
    )

    report_df = df[df["month"] == selected_month].copy()

    if not report_df.empty:

        expense_report = report_df[
            report_df["type"] == "Expense"
        ]

        income_report = report_df[
            report_df["type"] == "Income"
        ]

        total_expense = expense_report["amount"].sum()
        total_income = income_report["amount"].sum()

        st.subheader("Monthly Financial Summary")

        c1, c2, c3 = st.columns(3)
        c1.metric("Expenses", f"₹{total_expense:,.2f}")
        c2.metric("Income", f"₹{total_income:,.2f}")
        c3.metric("Net Savings", f"₹{total_income-total_expense:,.2f}")

        st.divider()

        st.subheader("Category Summary")

        category_report = (
            expense_report.groupby("category", as_index=False)["amount"]
            .sum().sort_values("amount", ascending=False)
        )

        st.dataframe(
            category_report,
            use_container_width=True,
            hide_index=True
        )

        # CSV export
        csv_data = report_df.drop(columns=["month"], errors="ignore").to_csv(
            index=False
        )

        st.download_button(
            "⬇️ Download Monthly CSV Report",
            data=csv_data,
            file_name=f"expense_report_{selected_month}.csv",
            mime="text/csv",
            use_container_width=True
        )

        # Excel export
        excel_buffer = BytesIO()

        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            report_df.drop(columns=["month"], errors="ignore").to_excel(
                writer, sheet_name="Transactions", index=False
            )
            category_report.to_excel(
                writer, sheet_name="Category Summary", index=False
            )

            summary = pd.DataFrame({
                "Metric": ["Total Income", "Total Expenses", "Net Savings"],
                "Amount": [
                    total_income,
                    total_expense,
                    total_income - total_expense
                ]
            })

            summary.to_excel(
                writer, sheet_name="Financial Summary", index=False
            )

        st.download_button(
            "⬇️ Download Excel Financial Report",
            data=excel_buffer.getvalue(),
            file_name=f"expense_report_{selected_month}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

        st.divider()
        st.subheader("All Transactions in Selected Month")

        st.dataframe(
            report_df.drop(columns=["month"], errors="ignore"),
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No transactions available for this month.")

# =====================================================
# FOOTER
# =====================================================
st.divider()

st.markdown(
    "<p style='text-align:center;color:#9295A2;font-size:12px;'>"
    "ExpenseIQ | Personal Expense Tracker & Analytics "
    "| Built with Python and Streamlit</p>",
    unsafe_allow_html=True
)
