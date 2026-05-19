import streamlit as st
import pandas as pd
import pdfplumber
import io
from parser import parse_statement
from frequency import frequency_count_avg, frequency_count

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Budget Dashboard", layout="wide")

# ── Session state defaults ─────────────────────────────────────────────────────
for key, default in {
    "monthly_income": 0,
    "goal_percent": 20,
    "df_all": None,          # combined raw transactions DataFrame
    "df_avg": None,          # frequency_count_avg result
    "df_total": None,        # frequency_count result
    "num_months": 0,
    "chat_history": [],      # list of {role, content} dicts for Ask AI page
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ── Helper: PDF bytes → plain text ────────────────────────────────────────────
def pdf_bytes_to_text(data: bytes) -> str:
    text = ""
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    return text


# ── Helper: reprocess all uploaded statements ──────────────────────────────────
def reprocess(uploaded_files):
    dfs = []
    for f in uploaded_files:
        raw = f.read()
        text = pdf_bytes_to_text(raw)
        df = parse_statement(text)
        if not df.empty:
            dfs.append(df)

    if not dfs:
        return

    combined = pd.concat(dfs, ignore_index=True)
    num_months = len(uploaded_files)

    st.session_state.df_all = combined
    st.session_state.df_avg = frequency_count_avg(combined, num_months)
    st.session_state.df_total = frequency_count(combined)
    st.session_state.num_months = num_months


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("💰 Budget Dashboard")
    st.markdown("---")

    page = st.radio("Navigate", ["Home", "Past Spendings", "Budgeting Goals", "Future Predictions", "Ask AI"])

    st.markdown("---")
    st.subheader("📂 Upload Statements")
    st.caption("Upload one PDF per month. Everything runs automatically.")

    uploaded_files = st.file_uploader(
        "Bank statement PDFs",
        type=["pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    if uploaded_files:
        if st.button("▶ Process statements", use_container_width=True):
            with st.spinner("Parsing your statements..."):
                reprocess(uploaded_files)
            st.success(f"✅ Processed {len(uploaded_files)} statement(s)")

    if st.session_state.num_months > 0:
        st.caption(f"Loaded: {st.session_state.num_months} month(s) of data")


# ══════════════════════════════════════════════════════════════════════════════
# HOME
# ══════════════════════════════════════════════════════════════════════════════
if page == "Home":
    st.title("Home")

    if st.session_state.df_all is None:
        st.info("👈 Upload your bank statement PDFs in the sidebar and click **Process statements** to get started.")
    else:
        df_total = st.session_state.df_total
        total_row = df_total[df_total["Store"] == "TOTAL"]
        total_spent = total_row["Total Spent ($)"].values[0] if not total_row.empty else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Months loaded", st.session_state.num_months)
        col2.metric("Total transactions", int(df_total[df_total["Store"] != "TOTAL"]["Count"].sum()))
        col3.metric("Total spent", f"${total_spent:,.2f}")

    st.markdown("---")
    st.subheader("Income & savings goal")

    monthly_income = st.number_input("Monthly income ($)", min_value=0, step=100,
                                     value=st.session_state.monthly_income)
    goal_percent = st.slider("% of income to save", 0, 100,
                             value=st.session_state.goal_percent)

    if monthly_income > 0:
        st.session_state.monthly_income = monthly_income
        st.session_state.goal_percent = goal_percent

        allowed = monthly_income * (1 - goal_percent / 100)
        save_amt = monthly_income * goal_percent / 100

        c1, c2, c3 = st.columns(3)
        c1.metric("Monthly income", f"${monthly_income:,}")
        c2.metric("Saved per month", f"${save_amt:,.0f}")
        c3.metric("Spend budget", f"${allowed:,.0f}")


# ══════════════════════════════════════════════════════════════════════════════
# PAST SPENDINGS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Past Spendings":
    st.title("Past Spendings")

    if st.session_state.df_total is None:
        st.warning("No data yet — upload statements on the sidebar first.")
    else:
        view = st.radio("View", ["Total (all months)", "Monthly averages"], horizontal=True)

        if view == "Total (all months)":
            df = st.session_state.df_total.copy()
            df = df[df["Store"] != "TOTAL"]
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.bar_chart(df.set_index("Store")["Total Spent ($)"])
        else:
            df = st.session_state.df_avg.copy()
            df = df[df["Store"] != "TOTAL"]
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.bar_chart(df.set_index("Store")["Avg Spent ($)"])


# ══════════════════════════════════════════════════════════════════════════════
# BUDGETING GOALS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Budgeting Goals":
    st.title("Budgeting Goals")

    if st.session_state.monthly_income == 0:
        st.warning("Set your income on the Home page first.")
    elif st.session_state.df_avg is None:
        st.warning("No data yet — upload statements on the sidebar first.")
    else:
        df = st.session_state.df_avg.copy()
        df = df[df["Store"] != "TOTAL"]

        # Group rare stores (avg < 1 visit/month) into Outliers
        outliers = df[df["Count (avg/month)"] == 1]
        main_df = df[df["Count (avg/month)"] > 1].copy()

        if not outliers.empty:
            main_df = pd.concat([main_df, pd.DataFrame({
                "Store": ["Outliers"],
                "Count (avg/month)": [len(outliers)],
                "Avg Spent ($)": [outliers["Avg Spent ($)"].sum()]
            })], ignore_index=True)

        allowed_spend = st.session_state.monthly_income * (1 - st.session_state.goal_percent / 100)
        total_avg = main_df["Avg Spent ($)"].sum()

        main_df["Recommended ($)"] = (main_df["Avg Spent ($)"] / total_avg * allowed_spend).round(2)
        main_df["Difference ($)"] = (main_df["Recommended ($)"] - main_df["Avg Spent ($)"]).round(2)

        st.write(
            f"Saving **{st.session_state.goal_percent}%** means your monthly spend budget is "
            f"**${allowed_spend:,.2f}**. Here's how your current habits map to that:"
        )

        # Colour the difference column
        def colour_diff(val):
            color = "green" if val >= 0 else "red"
            return f"color: {color}"

        styled = main_df[["Store", "Avg Spent ($)", "Recommended ($)", "Difference ($)"]]\
            .style.map(colour_diff, subset=["Difference ($)"])

        st.dataframe(styled, use_container_width=True, hide_index=True)
        st.bar_chart(main_df.set_index("Store")[["Avg Spent ($)", "Recommended ($)"]])


# ══════════════════════════════════════════════════════════════════════════════
# FUTURE PREDICTIONS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Future Predictions":
    st.title("Future Predictions")

    if st.session_state.df_all is None:
        st.warning("No data yet — upload statements on the sidebar first.")
    else:
        df_all = st.session_state.df_all.copy()

        if "Date" not in df_all.columns:
            st.error("Date column missing — check parser output.")
        else:
            df_all["Month"] = df_all["Date"].dt.to_period("M").astype(str)

            monthly = df_all.groupby("Month")["Spending"].sum().reset_index()
            monthly.columns = ["Month", "Total Spent ($)"]
            monthly = monthly.sort_values("Month")

            st.subheader("Monthly spend over time")
            st.line_chart(monthly.set_index("Month")["Total Spent ($)"])

            # Simple 3-month rolling average as a naive forecast
            monthly["3-month avg"] = monthly["Total Spent ($)"].rolling(3, min_periods=1).mean().round(2)

            st.subheader("Rolling 3-month average")
            st.line_chart(monthly.set_index("Month")[["Total Spent ($)", "3-month avg"]])

            st.caption(
                "Forecast is a simple rolling average. The more months of data you upload, "
                "the more accurate it becomes."
            )


# ══════════════════════════════════════════════════════════════════════════════
# ASK AI
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Ask AI":
    import anthropic
    import json

    st.title("Ask AI")

    if st.session_state.df_all is None:
        st.warning("No data yet — upload statements on the sidebar first.")
    else:
        # ── Build a spending summary to inject as context ──────────────────────
        df_total = st.session_state.df_total.copy()
        df_avg   = st.session_state.df_avg.copy()

        total_row   = df_total[df_total["Store"] == "TOTAL"]
        total_spent = total_row["Total Spent ($)"].values[0] if not total_row.empty else 0
        top_stores  = df_total[df_total["Store"] != "TOTAL"].head(10).to_dict(orient="records")
        avg_stores  = df_avg[df_avg["Store"] != "TOTAL"].head(10).to_dict(orient="records")

        income       = st.session_state.monthly_income
        goal_pct     = st.session_state.goal_percent
        allowed      = income * (1 - goal_pct / 100) if income > 0 else None
        num_months   = st.session_state.num_months

        system_prompt = f"""You are a personal finance assistant. The user has uploaded {num_months} month(s) of bank statements.
Here is a summary of their spending data:

Total spent across all months: ${total_spent:,.2f}

Top stores by total spend:
{json.dumps(top_stores, indent=2)}

Monthly averages by store:
{json.dumps(avg_stores, indent=2)}

Monthly income: {"$" + f"{income:,}" if income > 0 else "not set"}
Savings goal: {goal_pct}%
Monthly spend budget: {"$" + f"{allowed:,.2f}" if allowed is not None else "not set"}

Answer questions about their spending honestly and concisely. Give specific numbers from their data wherever possible.
If they ask something you don't have data for, say so clearly."""

        # ── Render chat history ────────────────────────────────────────────────
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        # ── Chat input ─────────────────────────────────────────────────────────
        if prompt := st.chat_input("Ask anything about your spending..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    client = anthropic.Anthropic()
                    response = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=1000,
                        system=system_prompt,
                        messages=st.session_state.chat_history
                    )
                    reply = response.content[0].text

                st.write(reply)
                st.session_state.chat_history.append({"role": "assistant", "content": reply})

        if st.session_state.chat_history:
            if st.button("Clear chat"):
                st.session_state.chat_history = []
                st.rerun()
