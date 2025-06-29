import pandas as pd
import polars as pl
import matplotlib.pyplot as plt
import streamlit as st

# ==============================
# Streamlit Inputs
# ==============================

st.title("Retirement & Savings Projection")

# Loan & Savings Inputs
loan_balance = st.number_input("Student Loan Balance", value=20000)
loan_payment = st.number_input("Monthly Loan Payment", value=500)
savings_rate = st.slider("Savings Rate (%)", 0, 100, 20) / 100
years = st.slider("Years to Simulate", 5, 40, 20)
retirement_year = st.number_input(
    "Retirement Year (Income stops)",
    min_value=1,
    max_value=years,
    value=min(30, years)  # Make sure default doesn't exceed max
)
# Inheritance Inputs
st.subheader("Optional One-Time Inheritances")
num_inheritances = st.slider("Number of Inheritances", 0, 3, 1)

inheritances = []
for i in range(num_inheritances):
    st.markdown(f"**Inheritance #{i+1}**")
    year = st.number_input(f"Inheritance Year #{i+1}", min_value=1, max_value=years, value=10, key=f"inh_year_{i}")
    amount = st.number_input(f"Inheritance Amount #{i+1}", min_value=0, step=1000, value=50000, key=f"inh_amt_{i}")
    inheritances.append({"month": year * 12, "amount": amount})

# Income Schedule UI
st.subheader("Define Your Income Schedule")
num_periods = st.slider("Number of Income Periods", min_value=1, max_value=5, value=3)

income_schedule = []
for i in range(num_periods):
    st.markdown(f"**Income Period {i+1}**")
    start = st.number_input(f"Start Year (Period {i+1})", min_value=1, max_value=100, value=1, key=f"start_{i}")
    end = st.number_input(f"End Year (Period {i+1})", min_value=start, max_value=100, value=start+2, key=f"end_{i}")
    income = st.number_input(f"Monthly Income (Period {i+1})", min_value=0, step=100, value=4000, key=f"income_{i}")
    income_schedule.append({"start_year": start, "end_year": end, "monthly_income": income})

# ==============================
# Model Parameters
# ==============================

loan_interest_annual = 0.05
investment_return_annual = 0.07
loan_interest_monthly = loan_interest_annual / 12
investment_return_monthly = investment_return_annual / 12
months = years * 12
retirement_month = retirement_year * 12

# ==============================
# Income Mapping by Month
# ==============================

income_by_month = {}
for period in income_schedule:
    start_month = (period["start_year"] - 1) * 12 + 1
    end_month = period["end_year"] * 12
    for month in range(start_month, end_month + 1):
        if month <= retirement_month:
            income_by_month[month] = period["monthly_income"]

# ==============================
# Simulation Loop
# ==============================

loan = loan_balance
invested = 0.0
rows = []
loan_paid_off_month = None

for month in range(1, months + 1):
    year = (month - 1) // 12 + 1
    current_income = income_by_month.get(month, 0)

    # Loan interest accrues
    loan += loan * loan_interest_monthly

    # Loan payment
    loan_payment_actual = min(loan, loan_payment)
    loan -= loan_payment_actual

    # Record when loan is fully paid
    if loan <= 0 and loan_paid_off_month is None:
        loan_paid_off_month = month

    # Disposable income
    leftover = current_income - loan_payment_actual

    # Savings contribution (only after loan is gone)
    savings_contrib = leftover * savings_rate if loan <= 0 else 0.0

    # Inheritance if applicable
    inheritance_this_month = sum(inh["amount"] for inh in inheritances if inh["month"] == month)

    # Update investments
    invested = invested * (1 + investment_return_monthly) + savings_contrib + inheritance_this_month

    rows.append({
        "Year": year,
        "Month": month,
        "Income": current_income,
        "LoanBalance": round(max(loan, 0), 2),
        "LoanPayment": round(loan_payment_actual, 2),
        "RemainingIncome": round(leftover, 2),
        "SavedThisMonth": round(savings_contrib, 2),
        "TotalInvested": round(invested, 2),
        "Inheritance": inheritance_this_month
    })

df_projection = pl.DataFrame(rows)

# ==============================
# Progress Bars
# ==============================

st.subheader("Progress Overview")

final_loan_balance = df_projection["LoanBalance"][-1]
loan_paid = loan_balance - final_loan_balance
loan_progress = loan_paid / loan_balance if loan_balance > 0 else 1

st.progress(loan_progress, text=f"Loan Paid: ${loan_paid:,.0f} / ${loan_balance:,.0f}")

final_investment = df_projection["TotalInvested"][-1]
st.metric("Total Invested at End", f"${final_investment:,.0f}")

if loan_paid_off_month:
    st.success(f"🎉 Loan fully paid off in Month {loan_paid_off_month} (Year {loan_paid_off_month // 12})")

# ==============================
# Visualization
# ==============================

st.subheader("Projection Chart")

fig, ax = plt.subplots(figsize=(10, 5))
ax.fill_between(df_projection["Month"].to_list(), df_projection["LoanBalance"].to_list(), label="Loan Balance", alpha=0.4, color="tomato")
ax.fill_between(df_projection["Month"].to_list(), df_projection["TotalInvested"].to_list(), label="Total Invested", alpha=0.4, color="green")
ax.set_xlabel("Month")
ax.set_ylabel("Amount ($)")
ax.set_title("Loan Balance vs Investment Growth")
ax.legend()
st.pyplot(fig)

# ==============================
# Download CSV
# ==============================

st.download_button(
    "Download Data as CSV",
    data=df_projection.write_csv(),
    file_name="projection.csv",
    mime="text/csv"
)