"""
BNPL Pricing Strategy Simulator
Interactive tool for modeling and visualizing BNPL product profitability
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from pricing_engine import (
    calculate_effective_yield,
    calculate_required_apr,
    estimate_interest_free_cap,
    generate_sensitivity_data,
    compare_interest_models
)


# Page configuration
st.set_page_config(
    page_title="BNPL Pricing Simulator",
    page_icon="💰",
    layout="wide"
)

# Header
st.title("BNPL Pricing Strategy Simulator")
st.markdown("Model and visualize the profitability and yield of BNPL products under different pricing scenarios")

# Sidebar inputs
st.sidebar.header("Configuration")

# Loan plan type
plan_type = st.sidebar.radio(
    "Loan Plan Type",
    options=["Interest-bearing", "Interest-free"],
    help="Choose between interest-bearing loans (with APR) or interest-free installment plans"
)

st.sidebar.markdown("---")
st.sidebar.subheader("Loan Parameters")

# Average loan parameters
avg_principal = st.sidebar.number_input(
    "Average Loan Principal ($)",
    min_value=20.0,
    max_value=10000.0,
    value=100.0,
    step=10.0,
    help="Average loan amount"
)

avg_installments = st.sidebar.slider(
    "Average Installment Count",
    min_value=1,
    max_value=36,
    value=7,
    help="Number of installments"
)

# Installment frequency
installment_frequency = st.sidebar.radio(
    "Installment Frequency",
    options=["Biweekly", "Monthly"],
    help="Choose payment frequency: Monthly (30 days) or Biweekly (14 days)"
)
installment_frequency_days = 30 if installment_frequency == "Monthly" else 14

# Interest rate (only for interest-bearing)
if plan_type == "Interest-bearing":
    interest_apr = st.sidebar.slider(
        "Interest Rate (APR %)",
        min_value=0.0,
        max_value=500.0,
        value=250.0,
        step=5.0,
        help="Annual Percentage Rate for interest-bearing loans"
    ) / 100.0
else:
    interest_apr = 0.0

# Fixed loan fee
fixed_fee_pct = st.sidebar.slider(
    "Fixed Loan Fee (%)",
    min_value=0.0,
    max_value=100.0,
    value=0.0,
    step=1.0,
    help="Fixed fee as % of principal (protects against early repayment)"
) / 100.0

# Late fee parameters
st.sidebar.markdown("---")
st.sidebar.subheader("Late Fee Parameters")

late_fee_amount = st.sidebar.number_input(
    "Late Fee Amount ($)",
    min_value=0.0,
    max_value=20.0,
    value=3.0,
    step=0.50,
    help="Fee charged per late installment payment"
)

late_installment_pct = st.sidebar.slider(
    "% of Installments Paid Late",
    min_value=0.0,
    max_value=100.0,
    value=20.0,
    step=1.0,
    help="Percentage of installments that incur late fees"
) / 100.0

st.sidebar.markdown("---")
st.sidebar.subheader("Business Parameters")

# Merchant parameters
merchant_commission = st.sidebar.slider(
    "Merchant Commission (%)",
    min_value=0.0,
    max_value=10.0,
    value=1.0,
    step=0.1,
    help="Fee charged to merchants"
) / 100.0

settlement_delay = st.sidebar.slider(
    "Settlement Delay (days)",
    min_value=0,
    max_value=60,
    value=1,
    help="Days until merchant is paid"
)

# Risk parameters
default_rate = st.sidebar.slider(
    "Default Rate (%)",
    min_value=0.0,
    max_value=30.0,
    value=15.0,
    step=0.5,
    help="Expected portfolio default rate"
) / 100.0

recovery_rate = st.sidebar.slider(
    "Credit Loss Recovery Rate (%)",
    min_value=0.0,
    max_value=100.0,
    value=10.0,
    step=5.0,
    help="% recovered from defaulted loans"
) / 100.0

# Target yield
target_yield = st.sidebar.slider(
    "Target Annualized Yield (%)",
    min_value=10.0,
    max_value=100.0,
    value=60.0,
    step=1.0,
    help="Desired portfolio-level return"
) / 100.0

# Funding cost (optional, defaulted to 0)
funding_cost = st.sidebar.slider(
    "Funding Cost (APR %)",
    min_value=0.0,
    max_value=20.0,
    value=8.0,
    step=0.5,
    help="Cost of capital (optional)"
) / 100.0

# Main dashboard
st.markdown("---")

# Calculate current metrics
current_yield_result = calculate_effective_yield(
    principal=avg_principal,
    apr=interest_apr,
    installments=avg_installments,
    merchant_commission_pct=merchant_commission,
    settlement_delay_days=settlement_delay,
    default_rate=default_rate,
    recovery_rate=recovery_rate,
    fixed_fee_pct=fixed_fee_pct,
    funding_cost_apr=funding_cost,
    installment_frequency_days=installment_frequency_days,
    late_fee_amount=late_fee_amount,
    late_installment_pct=late_installment_pct
)

# Calculate required APR (if interest-bearing)
if plan_type == "Interest-bearing":
    required_apr = calculate_required_apr(
        target_yield=target_yield,
        principal=avg_principal,
        installments=avg_installments,
        merchant_commission_pct=merchant_commission,
        settlement_delay_days=settlement_delay,
        default_rate=default_rate,
        recovery_rate=recovery_rate,
        fixed_fee_pct=fixed_fee_pct,
        funding_cost_apr=funding_cost,
        installment_frequency_days=installment_frequency_days,
        late_fee_amount=late_fee_amount,
        late_installment_pct=late_installment_pct
    )
else:
    required_apr = None

# Calculate interest-free installment cap
interest_free_cap = estimate_interest_free_cap(
    target_yield=target_yield,
    principal=avg_principal,
    merchant_commission_pct=merchant_commission,
    settlement_delay_days=settlement_delay,
    default_rate=default_rate,
    recovery_rate=recovery_rate,
    fixed_fee_pct=fixed_fee_pct,
    funding_cost_apr=funding_cost,
    installment_frequency_days=installment_frequency_days,
    late_fee_amount=late_fee_amount,
    late_installment_pct=late_installment_pct,
    max_installments=12
)

# Summary metrics - Compact view
st.header("Key Metrics")
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric(
        "Effective Yield",
        f"{current_yield_result['effective_yield'] * 100:.1f}%",
        delta=f"{(current_yield_result['effective_yield'] - target_yield) * 100:.1f}%"
    )

with col2:
    if plan_type == "Interest-bearing" and required_apr is not None:
        st.metric(
            "Required APR",
            f"{required_apr * 100:.1f}%",
            delta=f"{(required_apr - interest_apr) * 100:.1f}%"
        )
    else:
        st.metric(
            "Current APR",
            f"{interest_apr * 100:.1f}%"
        )

with col3:
    st.metric(
        "Profit Margin",
        f"{current_yield_result['profit_margin'] * 100:.1f}%"
    )

with col4:
    st.metric(
        "Loan Duration",
        f"{current_yield_result['loan_duration_days']}d"
    )

with col5:
    st.metric(
        "Capital Deploy",
        f"{current_yield_result['capital_deployment_days']:.0f}d"
    )

with col6:
    st.metric(
        "Settle Benefit",
        f"+{current_yield_result['settlement_delay_benefit'] * 100:.1f}%"
    )

# Float scenario warning - compact
if current_yield_result['is_float_scenario']:
    st.warning(
        f"⚠️ **FLOAT SCENARIO**: Settlement ({settlement_delay}d) ≥ Loan ({current_yield_result['loan_duration_days']}d) — "
        f"Customers pay BEFORE merchant. Float: {settlement_delay - current_yield_result['loan_duration_days']}d. Actual yield: INFINITE.",
        icon="⚠️"
    )

# Revenue breakdown - in expander to save space
with st.expander("💰 Revenue & Cost Breakdown", expanded=False):
    col1, col2 = st.columns(2)

    with col1:
        # Revenue components
        revenue_data = {
            'Component': ['Interest Income', 'Fixed Fee', 'Merchant Commission', 'Late Fees'],
            'Amount ($)': [
                current_yield_result['interest_income'],
                current_yield_result['fixed_fee_income'],
                current_yield_result['merchant_commission'],
                current_yield_result['late_fee_income']
            ]
        }
        revenue_df = pd.DataFrame(revenue_data)
        revenue_df['Percentage'] = (revenue_df['Amount ($)'] / revenue_df['Amount ($)'].sum() * 100).round(2)

        st.write("**Revenue Sources**")
        st.dataframe(revenue_df, hide_index=True, use_container_width=True)

        st.metric("Total Revenue", f"${current_yield_result['total_revenue']:.2f}")

    with col2:
        # Cost/loss components
        cost_data = {
            'Component': ['Funding Cost', 'Expected Loss'],
            'Amount ($)': [
                current_yield_result['funding_cost'],
                current_yield_result['expected_loss']
            ]
        }
        cost_df = pd.DataFrame(cost_data)

        st.write("**Costs & Losses**")
        st.dataframe(cost_df, hide_index=True, use_container_width=True)

        st.metric("Net Profit", f"${current_yield_result['net_profit']:.2f}")

# Visualizations
st.subheader("📊 Sensitivity Analysis")

# Prepare base parameters for sensitivity analysis
base_params = {
    'principal': avg_principal,
    'installments': avg_installments,
    'merchant_commission_pct': merchant_commission,
    'settlement_delay_days': settlement_delay,
    'default_rate': default_rate,
    'recovery_rate': recovery_rate,
    'fixed_fee_pct': fixed_fee_pct,
    'funding_cost_apr': funding_cost,
    'installment_frequency_days': installment_frequency_days,
    'late_fee_amount': late_fee_amount,
    'late_installment_pct': late_installment_pct
}

# Chart 1: Yield vs Default Rate
default_range = np.linspace(0, 0.30, 30)
base_params_for_default = base_params.copy()
base_params_for_default['apr'] = interest_apr

_, yields_by_default = generate_sensitivity_data(
    'default_rate',
    default_range,
    base_params_for_default,
    'effective_yield'
)

fig1 = go.Figure()
fig1.add_trace(go.Scatter(
    x=default_range * 100,
    y=yields_by_default * 100,
    mode='lines+markers',
    name='Effective Yield',
    line=dict(color='blue', width=2)
))
fig1.add_hline(
    y=target_yield * 100,
    line_dash="dash",
    line_color="red",
    annotation_text="Target Yield"
)
fig1.update_layout(
    title="Effective Yield vs Default Rate",
    xaxis_title="Default Rate (%)",
    yaxis_title="Effective Yield (%)",
    hovermode='x unified',
    height=300
)

# Chart 2: Yield vs Installment Count
installment_range = np.arange(2, 25, 1)
yields_by_installments = []

for inst in installment_range:
    params = base_params.copy()
    params['apr'] = interest_apr
    params['installments'] = int(inst)
    result = calculate_effective_yield(**params)
    yields_by_installments.append(result['effective_yield'])

fig2 = go.Figure()
fig2.add_trace(go.Scatter(
    x=installment_range,
    y=np.array(yields_by_installments) * 100,
    mode='lines+markers',
    name='Effective Yield',
    line=dict(color='green', width=2)
))
fig2.add_hline(
    y=target_yield * 100,
    line_dash="dash",
    line_color="red",
    annotation_text="Target Yield"
)
fig2.update_layout(
    title="Effective Yield vs Installment Count",
    xaxis_title="Number of Installments",
    yaxis_title="Effective Yield (%)",
    hovermode='x unified',
    height=300
)

# Chart 3: Required APR vs Merchant Commission
commission_range = np.linspace(0.01, 0.10, 20)
required_aprs = []

for comm in commission_range:
    params = base_params.copy()
    params['merchant_commission_pct'] = comm
    params['target_yield'] = target_yield
    apr = calculate_required_apr(**params)
    required_aprs.append(apr)

fig3 = go.Figure()
fig3.add_trace(go.Scatter(
    x=commission_range * 100,
    y=np.array(required_aprs) * 100,
    mode='lines+markers',
    name='Required APR',
    line=dict(color='purple', width=2)
))
if plan_type == "Interest-bearing":
    fig3.add_hline(
        y=interest_apr * 100,
        line_dash="dash",
        line_color="orange",
        annotation_text="Current APR"
    )
fig3.update_layout(
    title="Required APR vs Merchant Commission",
    xaxis_title="Merchant Commission (%)",
    yaxis_title="Required APR (%)",
    hovermode='x unified',
    height=300
)

# Chart 4: Yield vs Settlement Delay (NEW - shows settlement delay impact)
settlement_delay_range = np.arange(0, 61, 5)  # 0 to 60 days
yields_by_settlement = []

for delay in settlement_delay_range:
    params = base_params.copy()
    params['apr'] = interest_apr
    params['settlement_delay_days'] = int(delay)
    result = calculate_effective_yield(**params)
    yields_by_settlement.append(result['effective_yield'])

fig4 = go.Figure()
fig4.add_trace(go.Scatter(
    x=settlement_delay_range,
    y=np.array(yields_by_settlement) * 100,
    mode='lines+markers',
    name='Effective Yield',
    line=dict(color='orange', width=2)
))
fig4.add_hline(
    y=target_yield * 100,
    line_dash="dash",
    line_color="red",
    annotation_text="Target Yield"
)
fig4.add_vline(
    x=settlement_delay,
    line_dash="dot",
    line_color="gray",
    annotation_text="Current Delay"
)
fig4.update_layout(
    title="Yield vs Settlement Delay",
    xaxis_title="Settlement Delay (days)",
    yaxis_title="Effective Yield (%)",
    hovermode='x unified',
    height=300
)

# Display charts
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(fig1, use_container_width=True)
with col2:
    st.plotly_chart(fig2, use_container_width=True)

col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(fig3, use_container_width=True)
with col2:
    st.plotly_chart(fig4, use_container_width=True)

# Comparison table: Interest-bearing vs Interest-free - in expander
with st.expander("🔄 Interest-Bearing vs Interest-Free Comparison", expanded=False):
    comparison = compare_interest_models(
        principal=avg_principal,
        installments=avg_installments,
        merchant_commission_pct=merchant_commission,
        settlement_delay_days=settlement_delay,
        default_rate=default_rate,
        recovery_rate=recovery_rate,
        fixed_fee_pct=fixed_fee_pct,
        interest_bearing_apr=interest_apr if plan_type == "Interest-bearing" else required_apr if required_apr else 0.30,
        funding_cost_apr=funding_cost,
        installment_frequency_days=installment_frequency_days,
        late_fee_amount=late_fee_amount,
        late_installment_pct=late_installment_pct
    )

    # Create comparison dataframe
    comparison_df = pd.DataFrame({
        'Metric': [
            'APR',
            'Effective Yield',
            'Total Revenue',
            'Net Profit',
            'Profit Margin'
        ],
        'Interest-Bearing': [
            f"{comparison['interest_bearing']['apr'] * 100:.2f}%",
            f"{comparison['interest_bearing']['effective_yield'] * 100:.2f}%",
            f"${comparison['interest_bearing']['total_revenue']:.2f}",
            f"${comparison['interest_bearing']['net_profit']:.2f}",
            f"{comparison['interest_bearing']['profit_margin'] * 100:.2f}%"
        ],
        'Interest-Free': [
            f"{comparison['interest_free']['apr'] * 100:.2f}%",
            f"{comparison['interest_free']['effective_yield'] * 100:.2f}%",
            f"${comparison['interest_free']['total_revenue']:.2f}",
            f"${comparison['interest_free']['net_profit']:.2f}",
            f"{comparison['interest_free']['profit_margin'] * 100:.2f}%"
        ]
    })

    st.dataframe(comparison_df, hide_index=True, use_container_width=True)

# Key insights - in expander
with st.expander("💡 Key Insights", expanded=False):
    insights = []

    # Insight 1: Target yield achievability
    if current_yield_result['effective_yield'] >= target_yield:
        insights.append(f"✅ Current configuration **exceeds** target yield by {(current_yield_result['effective_yield'] - target_yield) * 100:.2f}%")
    else:
        insights.append(f"⚠️ Current configuration **falls short** of target yield by {(target_yield - current_yield_result['effective_yield']) * 100:.2f}%")

    # Insight 2: Required APR vs current
    if plan_type == "Interest-bearing" and required_apr:
        if required_apr > interest_apr:
            insights.append(f"📈 To hit target yield, APR should be increased to **{required_apr * 100:.2f}%** (currently {interest_apr * 100:.2f}%)")
        else:
            insights.append(f"💡 Current APR of **{interest_apr * 100:.2f}%** is sufficient to exceed target yield")

    # Insight 3: Interest-free viability
    if interest_free_cap > 0:
        insights.append(f"🎯 Interest-free plans are viable up to **{interest_free_cap} installments** to maintain target yield")
    else:
        insights.append(f"❌ Interest-free plans cannot achieve target yield under current parameters")

    # Insight 4: Default impact
    if default_rate > 0.10:
        insights.append(f"⚠️ High default rate ({default_rate * 100:.1f}%) significantly impacts profitability. Consider tighter credit requirements.")

    # Insight 5: Revenue composition
    interest_pct = (current_yield_result['interest_income'] / current_yield_result['total_revenue'] * 100) if current_yield_result['total_revenue'] > 0 else 0
    merchant_pct = (current_yield_result['merchant_commission'] / current_yield_result['total_revenue'] * 100) if current_yield_result['total_revenue'] > 0 else 0

    if merchant_pct > interest_pct and plan_type == "Interest-bearing":
        insights.append(f"💰 Merchant commission ({merchant_pct:.1f}%) generates more revenue than interest ({interest_pct:.1f}%)")

    for insight in insights:
        st.markdown(f"- {insight}")

# Footer
st.caption("BNPL Pricing Strategy Simulator v1.4 | Built with Streamlit")
