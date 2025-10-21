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

# Initialize session state for comparison scenario (matches Scenario A defaults)
if 'comp_principal' not in st.session_state:
    st.session_state.comp_principal = 100.0
    st.session_state.comp_installments = 7
    st.session_state.comp_frequency = "Biweekly"  # Different from Scenario A (Monthly)
    st.session_state.comp_first_upfront = False
    st.session_state.comp_early_rate = 0.0
    st.session_state.comp_early_inst = 3
    st.session_state.comp_apr = 250.0  # Matches sidebar default (250% APR)
    st.session_state.comp_fixed_fee = 0.0
    st.session_state.comp_late_fee = 3.0
    st.session_state.comp_late_pct = 20.0
    st.session_state.comp_merchant_comm = 1.0
    st.session_state.comp_settlement = 1
    st.session_state.comp_default = 15.0
    st.session_state.comp_recovery = 10.0
    st.session_state.comp_funding = 8.0

# Sidebar inputs
st.sidebar.header("Configuration")

with st.sidebar.expander("**Loan Parameters**", expanded=False):
    # Average loan parameters
    avg_principal = st.number_input(
        "Average Loan Principal ($)",
        min_value=20.0,
        max_value=10000.0,
        value=100.0,
        step=10.0,
        help="Average loan amount"
    )

    avg_installments = st.slider(
        "Average Installment Count",
        min_value=1,
        max_value=36,
        value=7,
        help="Number of installments"
    )

    # Installment frequency
    installment_frequency = st.radio(
        "Installment Frequency",
        options=["Biweekly", "Monthly"],
        help="Choose payment frequency: Monthly (30 days) or Biweekly (14 days)"
    )
    installment_frequency_days = 30 if installment_frequency == "Monthly" else 14

    # First installment upfront
    first_installment_upfront = st.checkbox(
        "Charge First Installment Upfront",
        value=False,
        help="Customer pays first installment at purchase. Reduces capital deployed and loan duration. Merchant still charged on full transaction value."
    )

with st.sidebar.expander("**Early Repayment**", expanded=False):
    early_repayment_rate = st.slider(
        "Early Repayment Rate (%)",
        min_value=0.0,
        max_value=50.0,
        value=0.0,
        step=1.0,
        help="Percentage of loans repaid early. Early repayers are assumed to be higher quality (no defaults) but generate less interest income."
    ) / 100.0

    # Only show avg repayment installment if early repayment is enabled
    avg_repayment_installment = None
    if early_repayment_rate > 0:
        avg_repayment_installment = st.slider(
            "Avg Early Repayment Installment",
            min_value=1,
            max_value=max(1, avg_installments - 1),
            value=max(1, avg_installments // 2),
            help="Average installment number at which early repayment occurs (e.g., installment 3 out of 6)"
        )

with st.sidebar.expander("**Pricing**", expanded=False):
    # Interest rate
    interest_apr = st.slider(
        "Interest Rate (APR %)",
        min_value=0.0,
        max_value=500.0,
        value=250.0,
        step=5.0,
        help="Annual Percentage Rate (set to 0% for interest-free plans)"
    ) / 100.0

    # Fixed loan fee
    fixed_fee_pct = st.slider(
        "Fixed Loan Fee (%)",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=1.0,
        help="Fixed fee as % of principal (protects against early repayment)"
    ) / 100.0

with st.sidebar.expander("**Late Fees**", expanded=False):
    late_fee_amount = st.number_input(
        "Late Fee Amount ($)",
        min_value=0.0,
        max_value=20.0,
        value=3.0,
        step=0.50,
        help="Fee charged per late installment payment"
    )

    late_installment_pct = st.slider(
        "% of Installments Paid Late",
        min_value=0.0,
        max_value=100.0,
        value=20.0,
        step=1.0,
        help="Percentage of installments that incur late fees"
    ) / 100.0

with st.sidebar.expander("**Business & Risk**", expanded=False):
    # Merchant parameters
    merchant_commission = st.slider(
        "Merchant Commission (%)",
        min_value=0.0,
        max_value=10.0,
        value=1.0,
        step=0.1,
        help="Fee charged to merchants"
    ) / 100.0

    settlement_delay = st.slider(
        "Settlement Delay (days)",
        min_value=0,
        max_value=60,
        value=1,
        help="Days until merchant is paid"
    )

    # Risk parameters
    default_rate = st.slider(
        "Default Rate (%)",
        min_value=0.0,
        max_value=30.0,
        value=15.0,
        step=0.5,
        help="Expected portfolio default rate"
    ) / 100.0

    recovery_rate = st.slider(
        "Credit Loss Recovery Rate (%)",
        min_value=0.0,
        max_value=100.0,
        value=10.0,
        step=5.0,
        help="% recovered from defaulted loans"
    ) / 100.0

    # Funding cost (optional, defaulted to 0)
    funding_cost = st.slider(
        "Funding Cost (APR %)",
        min_value=0.0,
        max_value=20.0,
        value=8.0,
        step=0.5,
        help="Cost of capital (optional)"
    ) / 100.0

with st.sidebar.expander("**Target Yield**", expanded=False):
    # Target yield
    target_yield = st.slider(
        "Target Annualized Yield (%)",
        min_value=10.0,
        max_value=100.0,
        value=60.0,
        step=1.0,
        help="Desired portfolio-level return"
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
    late_installment_pct=late_installment_pct,
    first_installment_upfront=first_installment_upfront,
    early_repayment_rate=early_repayment_rate,
    avg_repayment_installment=avg_repayment_installment
)

# Calculate required APR
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
    late_installment_pct=late_installment_pct,
    first_installment_upfront=first_installment_upfront,
    early_repayment_rate=early_repayment_rate,
    avg_repayment_installment=avg_repayment_installment
)

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
    first_installment_upfront=first_installment_upfront,
    early_repayment_rate=early_repayment_rate,
    avg_repayment_installment=avg_repayment_installment,
    max_installments=12
)

# Summary metrics - Compact view
st.header("Key Metrics")

# Add helpful explanations in an info box
with st.expander("ℹ️ What do these metrics mean?", expanded=False):
    st.markdown("""
    **Effective Yield**: The annualized return on capital after accounting for all revenues, costs, defaults, and time value of money. This is your actual portfolio-level profitability. Delta shows difference from target yield.

    **Required APR**: The interest rate needed to achieve your target yield given current parameters. Delta shows how much you'd need to adjust your current APR.

    **Profit Margin**: Net profit as a percentage of principal (Net Profit / Principal). Shows profitability per loan before annualizing.

    **Loan Duration**: Total time from loan origination to final payment in days (installments × frequency).

    **Capital Deploy**: Average days capital is deployed, accounting for when merchant is paid. Lower is better - capital locked up for less time.

    **Settle Benefit**: The yield boost from settlement delay. When you pay the merchant later, you earn extra yield on the float.
    """)

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric(
        "Effective Yield",
        f"{current_yield_result['effective_yield'] * 100:.1f}%",
        delta=f"{(current_yield_result['effective_yield'] - target_yield) * 100:.1f}%",
        help="Annualized return on capital after all revenues, costs, and defaults"
    )

with col2:
    st.metric(
        "Required APR",
        f"{required_apr * 100:.1f}%",
        delta=f"{(required_apr - interest_apr) * 100:.1f}%",
        help="Interest rate needed to hit target yield with current settings"
    )

with col3:
    st.metric(
        "Profit Margin",
        f"{current_yield_result['profit_margin'] * 100:.1f}%",
        help="Net profit as % of principal (before annualizing)"
    )

with col4:
    st.metric(
        "Loan Duration",
        f"{current_yield_result['loan_duration_days']}d",
        help="Total time from origination to final payment"
    )

with col5:
    st.metric(
        "Capital Deploy",
        f"{current_yield_result['capital_deployment_days']:.0f}d",
        help="Average days capital is deployed (accounting for settlement)"
    )

with col6:
    st.metric(
        "Settle Benefit",
        f"+{current_yield_result['settlement_delay_benefit'] * 100:.1f}%",
        help="Yield boost from settlement delay float"
    )

# First installment upfront info - compact
if first_installment_upfront:
    installment_amt = current_yield_result['installment_amount']
    capital_deployed = current_yield_result['capital_to_deploy']
    loan_days = current_yield_result['loan_duration_days']
    msg = f"First installment collected upfront ({installment_amt:.2f} USD) — Capital at risk: {capital_deployed:.2f} USD over {loan_days} days"
    st.info(msg, icon="💰")

# Early repayment info - compact
if current_yield_result['has_early_repayment']:
    early_pct = current_yield_result['early_repayment_rate'] * 100
    early_inst = current_yield_result['avg_repayment_installment']
    msg = f"Portfolio blending enabled: {early_pct:.0f}% of loans repay early at installment {early_inst} (zero defaults, reduced interest income)"
    st.info(msg, icon="⚡")

# Float scenario warning - compact
if current_yield_result['is_float_scenario']:
    st.warning(
        f"⚠️ **FLOAT SCENARIO**: Settlement ({settlement_delay}d) ≥ Loan ({current_yield_result['loan_duration_days']}d) — "
        f"Customers pay BEFORE merchant. Float: {settlement_delay - current_yield_result['loan_duration_days']}d. Actual yield: INFINITE.",
        icon="⚠️"
    )

# Revenue breakdown - in expander to save space
with st.expander("💰 Revenue & Cost Breakdown", expanded=False):
    # Build waterfall chart dynamically, excluding zero values
    waterfall_x = []
    waterfall_y = []
    waterfall_text = []
    waterfall_measure = []

    # Revenue components (in order: Merchant Commission, Fixed Fee, Interest, Late Fees)
    revenue_components = [
        ("Merchant<br>Commission", current_yield_result['merchant_commission']),
        ("Fixed<br>Fee", current_yield_result['fixed_fee_income']),
        ("Interest<br>Income", current_yield_result['interest_income']),
        ("Late<br>Fees", current_yield_result['late_fee_income'])
    ]

    # Add non-zero revenue components
    for label, value in revenue_components:
        if value > 0:
            waterfall_x.append(label)
            waterfall_y.append(value)
            waterfall_text.append(f"${value:.2f}")
            waterfall_measure.append("relative")

    # Add Total Revenue
    waterfall_x.append("Total<br>Revenue")
    waterfall_y.append(None)
    waterfall_text.append(f"${current_yield_result['total_revenue']:.2f}")
    waterfall_measure.append("total")

    # Cost components
    cost_components = [
        ("Expected<br>Loss", current_yield_result['expected_loss']),
        ("Funding<br>Cost", current_yield_result['funding_cost'])
    ]

    # Add non-zero cost components
    for label, value in cost_components:
        if value > 0:
            waterfall_x.append(label)
            waterfall_y.append(-value)
            waterfall_text.append(f"-${value:.2f}")
            waterfall_measure.append("relative")

    # Add Net Profit
    waterfall_x.append("Net<br>Profit")
    waterfall_y.append(None)
    waterfall_text.append(f"${current_yield_result['net_profit']:.2f}")
    waterfall_measure.append("total")

    # Create waterfall chart
    waterfall_fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=waterfall_measure,
        x=waterfall_x,
        y=waterfall_y,
        text=waterfall_text,
        textposition="outside",
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "#2ecc71"}},  # Green for revenue
        decreasing={"marker": {"color": "#e74c3c"}},  # Red for costs
        totals={"marker": {"color": "#3498db"}}  # Blue for totals
    ))

    # Calculate y-axis range - extend above total revenue for better label visibility
    max_value = current_yield_result['total_revenue']
    min_value = current_yield_result['net_profit']
    y_top_padding = max_value * 0.25  # 25% padding at top only

    # Start at 0 or minimum value if negative
    y_axis_min = min(0, min_value)
    y_axis_max = max_value + y_top_padding

    waterfall_fig.update_layout(
        title="Profitability Waterfall: Revenue Sources → Net Profit",
        showlegend=False,
        height=450,
        margin=dict(t=100, b=50, l=50, r=50),  # Extra top margin for labels
        xaxis_title="",
        yaxis_title="Amount ($)",
        yaxis_range=[y_axis_min, y_axis_max],
        hovermode='x'
    )

    st.plotly_chart(waterfall_fig, config={'displayModeBar': False})

    st.markdown("---")

    # Detailed breakdown tables
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
        st.dataframe(revenue_df, hide_index=True, width='stretch')

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
        st.dataframe(cost_df, hide_index=True, width='stretch')

        st.metric("Net Profit", f"${current_yield_result['net_profit']:.2f}")

# Visualizations - in expander to save space
with st.expander("📊 Sensitivity Analysis", expanded=False):
    st.markdown("""
    These charts show how changing each variable impacts your **Effective Yield** while keeping all other parameters constant.
    Use these to understand which levers have the most impact on profitability and identify optimization opportunities.
    The red dashed line represents your target yield.
    """)
    st.markdown("---")

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
        'late_installment_pct': late_installment_pct,
        'first_installment_upfront': first_installment_upfront,
        'early_repayment_rate': early_repayment_rate,
        'avg_repayment_installment': avg_repayment_installment
    }

    # Chart 1: Yield vs Default Rate
    default_range = np.linspace(0, 0.5, 30)
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
        yaxis_range=[-25, 150],
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
        yaxis_range=[-25, 150],
        hovermode='x unified',
        height=300
    )

    # Chart 3: Yield vs Merchant Commission
    commission_range = np.linspace(0.01, 0.10, 20)
    yields_by_commission = []

    for comm in commission_range:
        params = base_params.copy()
        params['apr'] = interest_apr
        params['merchant_commission_pct'] = comm
        result = calculate_effective_yield(**params)
        yields_by_commission.append(result['effective_yield'])

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=commission_range * 100,
        y=np.array(yields_by_commission) * 100,
        mode='lines+markers',
        name='Effective Yield',
        line=dict(color='purple', width=2)
    ))
    fig3.add_hline(
        y=target_yield * 100,
        line_dash="dash",
        line_color="red",
        annotation_text="Target Yield"
    )
    fig3.update_layout(
        title="Effective Yield vs Merchant Commission",
        xaxis_title="Merchant Commission (%)",
        yaxis_title="Effective Yield (%)",
        yaxis_range=[-25, 150],
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
        yaxis_range=[-25, 150],
        hovermode='x unified',
        height=300
    )

    # Chart 5: Yield vs APR
    apr_range = np.linspace(0, 5.0, 30)  # 0% to 500%
    yields_by_apr = []

    for apr in apr_range:
        params = base_params.copy()
        params['apr'] = apr
        result = calculate_effective_yield(**params)
        yields_by_apr.append(result['effective_yield'])

    fig5 = go.Figure()
    fig5.add_trace(go.Scatter(
        x=apr_range * 100,
        y=np.array(yields_by_apr) * 100,
        mode='lines+markers',
        name='Effective Yield',
        line=dict(color='red', width=2)
    ))
    fig5.add_hline(
        y=target_yield * 100,
        line_dash="dash",
        line_color="red",
        annotation_text="Target Yield"
    )
    fig5.add_vline(
        x=interest_apr * 100,
        line_dash="dot",
        line_color="gray",
        annotation_text="Current APR"
    )
    fig5.update_layout(
        title="Effective Yield vs APR",
        xaxis_title="APR (%)",
        yaxis_title="Effective Yield (%)",
        yaxis_range=[-25, 150],
        hovermode='x unified',
        height=300
    )

    # Chart 6: Yield vs Fixed Fee
    fixed_fee_range = np.linspace(0, 0.20, 20)  # 0% to 20%
    yields_by_fixed_fee = []

    for fee in fixed_fee_range:
        params = base_params.copy()
        params['apr'] = interest_apr
        params['fixed_fee_pct'] = fee
        result = calculate_effective_yield(**params)
        yields_by_fixed_fee.append(result['effective_yield'])

    fig6 = go.Figure()
    fig6.add_trace(go.Scatter(
        x=fixed_fee_range * 100,
        y=np.array(yields_by_fixed_fee) * 100,
        mode='lines+markers',
        name='Effective Yield',
        line=dict(color='teal', width=2)
    ))
    fig6.add_hline(
        y=target_yield * 100,
        line_dash="dash",
        line_color="red",
        annotation_text="Target Yield"
    )
    fig6.update_layout(
        title="Effective Yield vs Fixed Fee",
        xaxis_title="Fixed Fee (%)",
        yaxis_title="Effective Yield (%)",
        yaxis_range=[-25, 150],
        hovermode='x unified',
        height=300
    )

    # Chart 7: Yield vs Late Fee Amount
    late_fee_range = np.linspace(0, 10, 20)  # $0 to $10
    yields_by_late_fee = []

    for fee in late_fee_range:
        params = base_params.copy()
        params['apr'] = interest_apr
        params['late_fee_amount'] = fee
        result = calculate_effective_yield(**params)
        yields_by_late_fee.append(result['effective_yield'])

    fig7 = go.Figure()
    fig7.add_trace(go.Scatter(
        x=late_fee_range,
        y=np.array(yields_by_late_fee) * 100,
        mode='lines+markers',
        name='Effective Yield',
        line=dict(color='brown', width=2)
    ))
    fig7.add_hline(
        y=target_yield * 100,
        line_dash="dash",
        line_color="red",
        annotation_text="Target Yield"
    )
    fig7.update_layout(
        title="Effective Yield vs Late Fee Amount",
        xaxis_title="Late Fee Amount ($)",
        yaxis_title="Effective Yield (%)",
        yaxis_range=[-25, 150],
        hovermode='x unified',
        height=300
    )

    # Chart 8: Yield vs Recovery Rate
    recovery_range = np.linspace(0, 1.0, 20)  # 0% to 100%
    yields_by_recovery = []

    for recovery in recovery_range:
        params = base_params.copy()
        params['apr'] = interest_apr
        params['recovery_rate'] = recovery
        result = calculate_effective_yield(**params)
        yields_by_recovery.append(result['effective_yield'])

    fig8 = go.Figure()
    fig8.add_trace(go.Scatter(
        x=recovery_range * 100,
        y=np.array(yields_by_recovery) * 100,
        mode='lines+markers',
        name='Effective Yield',
        line=dict(color='pink', width=2)
    ))
    fig8.add_hline(
        y=target_yield * 100,
        line_dash="dash",
        line_color="red",
        annotation_text="Target Yield"
    )
    fig8.update_layout(
        title="Effective Yield vs Recovery Rate",
        xaxis_title="Recovery Rate (%)",
        yaxis_title="Effective Yield (%)",
        yaxis_range=[-25, 150],
        hovermode='x unified',
        height=300
    )

    # Chart 9: Yield vs Funding Cost
    funding_cost_range = np.linspace(0, 0.20, 20)  # 0% to 20%
    yields_by_funding = []

    for funding in funding_cost_range:
        params = base_params.copy()
        params['apr'] = interest_apr
        params['funding_cost_apr'] = funding
        result = calculate_effective_yield(**params)
        yields_by_funding.append(result['effective_yield'])

    fig9 = go.Figure()
    fig9.add_trace(go.Scatter(
        x=funding_cost_range * 100,
        y=np.array(yields_by_funding) * 100,
        mode='lines+markers',
        name='Effective Yield',
        line=dict(color='navy', width=2)
    ))
    fig9.add_hline(
        y=target_yield * 100,
        line_dash="dash",
        line_color="red",
        annotation_text="Target Yield"
    )
    fig9.update_layout(
        title="Effective Yield vs Funding Cost",
        xaxis_title="Funding Cost APR (%)",
        yaxis_title="Effective Yield (%)",
        yaxis_range=[-25, 150],
        hovermode='x unified',
        height=300
    )

    # Display charts with explanations
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig1, config={'displayModeBar': False})
        st.caption("📉 **Default Rate Impact**: Shows how credit quality affects profitability. Higher defaults directly reduce yield through expected losses. Critical for risk-based pricing decisions.")
    with col2:
        st.plotly_chart(fig2, config={'displayModeBar': False})
        st.caption("📅 **Installment Count Impact**: Longer loan terms generally reduce annualized yield because capital is deployed longer. However, more installments = more late fee opportunities.")

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig3, config={'displayModeBar': False})
        st.caption("💳 **Merchant Commission Impact**: Higher commissions increase revenue and boost yield. This is often the most controllable lever for profitability since it's negotiated upfront.")
    with col2:
        st.plotly_chart(fig4, config={'displayModeBar': False})
        st.caption("⏱️ **Settlement Delay Impact**: Delaying merchant payment increases yield by keeping more capital working longer. Major profitability lever with minimal risk if managed properly.")

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig5, config={'displayModeBar': False})
        st.caption("💰 **APR Impact**: Interest rate is the most direct yield driver. Linear relationship - each percentage point increase in APR translates to higher effective yield. Set to 0% for interest-free plans.")
    with col2:
        st.plotly_chart(fig6, config={'displayModeBar': False})
        st.caption("🛡️ **Fixed Fee Impact**: Fixed fees boost yield and protect against early repayment risk. Unlike interest, they're earned upfront regardless of loan duration.")

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig7, config={'displayModeBar': False})
        st.caption("⚠️ **Late Fee Impact**: Late fees provide incremental revenue but impact is modest unless late payment rates are high. Balance profitability with customer experience.")
    with col2:
        st.plotly_chart(fig8, config={'displayModeBar': False})
        st.caption("♻️ **Recovery Rate Impact**: Higher recovery on defaulted loans reduces net losses and improves yield. Invest in collections infrastructure to move this needle.")

    # Chart 10: Yield vs Early Repayment Rate
    early_repayment_range = np.linspace(0, 0.50, 20)  # 0% to 50%
    yields_by_early_repayment = []

    for early_rate in early_repayment_range:
        params = base_params.copy()
        params['apr'] = interest_apr
        params['early_repayment_rate'] = early_rate
        # Use middle of installment range as avg repayment point
        params['avg_repayment_installment'] = max(1, avg_installments // 2) if early_rate > 0 else None
        result = calculate_effective_yield(**params)
        yields_by_early_repayment.append(result['effective_yield'])

    fig10 = go.Figure()
    fig10.add_trace(go.Scatter(
        x=early_repayment_range * 100,
        y=np.array(yields_by_early_repayment) * 100,
        mode='lines+markers',
        name='Effective Yield',
        line=dict(color='magenta', width=2)
    ))
    fig10.add_hline(
        y=target_yield * 100,
        line_dash="dash",
        line_color="red",
        annotation_text="Target Yield"
    )
    fig10.update_layout(
        title="Effective Yield vs Early Repayment Rate",
        xaxis_title="Early Repayment Rate (%)",
        yaxis_title="Effective Yield (%)",
        yaxis_range=[-25, 150],
        hovermode='x unified',
        height=300
    )

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig9, config={'displayModeBar': False})
        st.caption("💸 **Funding Cost Impact**: Your cost of capital directly reduces net yield. Lower funding costs = higher profitability. Critical for debt-financed BNPL models.")
    with col2:
        st.plotly_chart(fig10, config={'displayModeBar': False})
        st.caption("⚡ **Early Repayment Impact**: Early repayments reduce interest income (shorter loan duration) but improve portfolio quality (zero defaults on early repayers). Net impact depends on APR level and default rates.")

# Scenario Comparison
with st.expander("🔄 Scenario Comparison", expanded=False):
    st.markdown("""
    Compare your current scenario (Scenario A) against an alternative configuration (Scenario B).
    Adjust the parameters below to model different pricing strategies and see side-by-side comparisons of key metrics, profitability, and revenue breakdown.
    """)

    # Copy current scenario button
    if st.button("📋 Copy Current Scenario to Comparison"):
        st.session_state.comp_principal = avg_principal
        st.session_state.comp_installments = avg_installments
        st.session_state.comp_frequency = installment_frequency
        st.session_state.comp_first_upfront = first_installment_upfront
        st.session_state.comp_early_rate = early_repayment_rate * 100
        st.session_state.comp_early_inst = avg_repayment_installment if avg_repayment_installment else max(1, avg_installments // 2)
        st.session_state.comp_apr = interest_apr * 100
        st.session_state.comp_fixed_fee = fixed_fee_pct * 100
        st.session_state.comp_late_fee = late_fee_amount
        st.session_state.comp_late_pct = late_installment_pct * 100
        st.session_state.comp_merchant_comm = merchant_commission * 100
        st.session_state.comp_settlement = settlement_delay
        st.session_state.comp_default = default_rate * 100
        st.session_state.comp_recovery = recovery_rate * 100
        st.session_state.comp_funding = funding_cost * 100
        st.rerun()

    st.markdown("---")

    with st.expander("⚙️ Scenario B Configuration", expanded=False):
        # Input controls organized in columns
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**Loan Parameters**")
            comp_principal = st.number_input(
                "Principal ($)",
                min_value=20.0,
                max_value=10000.0,
                value=st.session_state.comp_principal,
                step=10.0,
                key="comp_principal_input"
            )
            comp_installments = st.slider(
                "Installments",
                min_value=1,
                max_value=36,
                value=st.session_state.comp_installments,
                key="comp_installments_input"
            )
            comp_frequency = st.radio(
                "Frequency",
                options=["Biweekly", "Monthly"],
                index=0 if st.session_state.comp_frequency == "Biweekly" else 1,
                key="comp_frequency_input"
            )
            comp_first_upfront = st.checkbox(
                "First Installment Upfront",
                value=st.session_state.comp_first_upfront,
                key="comp_first_upfront_input"
            )

            st.markdown("**Early Repayment**")
            comp_early_rate = st.slider(
                "Early Repayment Rate (%)",
                min_value=0.0,
                max_value=50.0,
                value=st.session_state.comp_early_rate,
                step=1.0,
                key="comp_early_rate_input"
            )
            comp_early_inst = None
            if comp_early_rate > 0:
                comp_early_inst = st.slider(
                    "Avg Early Installment",
                    min_value=1,
                    max_value=max(1, comp_installments - 1),
                    value=min(st.session_state.comp_early_inst, max(1, comp_installments - 1)),
                    key="comp_early_inst_input"
                )

        with col2:
            st.markdown("**Pricing**")
            comp_apr = st.slider(
                "APR (%)",
                min_value=0.0,
                max_value=500.0,
                value=st.session_state.comp_apr,
                step=5.0,
                key="comp_apr_input"
            )
            comp_fixed_fee = st.slider(
                "Fixed Fee (%)",
                min_value=0.0,
                max_value=100.0,
                value=st.session_state.comp_fixed_fee,
                step=1.0,
                key="comp_fixed_fee_input"
            )

            st.markdown("**Late Fees**")
            comp_late_fee = st.number_input(
                "Late Fee ($)",
                min_value=0.0,
                max_value=20.0,
                value=st.session_state.comp_late_fee,
                step=0.50,
                key="comp_late_fee_input"
            )
            comp_late_pct = st.slider(
                "% Paid Late",
                min_value=0.0,
                max_value=100.0,
                value=st.session_state.comp_late_pct,
                step=1.0,
                key="comp_late_pct_input"
            )

        with col3:
            st.markdown("**Business Parameters**")
            comp_merchant_comm = st.slider(
                "Merchant Commission (%)",
                min_value=0.0,
                max_value=10.0,
                value=st.session_state.comp_merchant_comm,
                step=0.1,
                key="comp_merchant_comm_input"
            )
            comp_settlement = st.slider(
                "Settlement Delay (days)",
                min_value=0,
                max_value=60,
                value=st.session_state.comp_settlement,
                key="comp_settlement_input"
            )

            st.markdown("**Risk Parameters**")
            comp_default = st.slider(
                "Default Rate (%)",
                min_value=0.0,
                max_value=30.0,
                value=st.session_state.comp_default,
                step=0.5,
                key="comp_default_input"
            )
            comp_recovery = st.slider(
                "Recovery Rate (%)",
                min_value=0.0,
                max_value=100.0,
                value=st.session_state.comp_recovery,
                step=5.0,
                key="comp_recovery_input"
            )

            st.markdown("**Costs**")
            comp_funding = st.slider(
                "Funding Cost APR (%)",
                min_value=0.0,
                max_value=20.0,
                value=st.session_state.comp_funding,
                step=0.5,
                key="comp_funding_input"
            )

    # Calculate comparison scenario
    comp_frequency_days = 30 if comp_frequency == "Monthly" else 14

    comparison_result = calculate_effective_yield(
        principal=comp_principal,
        apr=comp_apr / 100,
        installments=comp_installments,
        merchant_commission_pct=comp_merchant_comm / 100,
        settlement_delay_days=comp_settlement,
        default_rate=comp_default / 100,
        recovery_rate=comp_recovery / 100,
        fixed_fee_pct=comp_fixed_fee / 100,
        funding_cost_apr=comp_funding / 100,
        installment_frequency_days=comp_frequency_days,
        late_fee_amount=comp_late_fee,
        late_installment_pct=comp_late_pct / 100,
        first_installment_upfront=comp_first_upfront,
        early_repayment_rate=comp_early_rate / 100,
        avg_repayment_installment=comp_early_inst
    )

    st.markdown("---")
    st.header("Comparison Results")

    # Key Metrics Comparison
    st.subheader("Key Metrics")

    # Calculate deltas
    yield_delta = comparison_result['effective_yield'] - current_yield_result['effective_yield']
    profit_margin_delta = comparison_result['profit_margin'] - current_yield_result['profit_margin']
    revenue_delta = comparison_result['total_revenue'] - current_yield_result['total_revenue']
    profit_delta = comparison_result['net_profit'] - current_yield_result['net_profit']
    deploy_delta = comparison_result['capital_deployment_days'] - current_yield_result['capital_deployment_days']
    loss_delta = comparison_result['expected_loss'] - current_yield_result['expected_loss']

    # Scenario A metrics
    st.markdown("**Scenario A (Current)**")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("Effective Yield", f"{current_yield_result['effective_yield'] * 100:.1f}%")
    with col2:
        st.metric("Profit Margin", f"{current_yield_result['profit_margin'] * 100:.1f}%")
    with col3:
        st.metric("Total Revenue", f"${current_yield_result['total_revenue']:.2f}")
    with col4:
        st.metric("Net Profit", f"${current_yield_result['net_profit']:.2f}")
    with col5:
        st.metric("Capital Deploy", f"{current_yield_result['capital_deployment_days']:.0f}d")
    with col6:
        st.metric("Expected Loss", f"${current_yield_result['expected_loss']:.2f}")

    # Scenario B metrics with deltas
    st.markdown("**Scenario B (Comparison)**")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("Effective Yield", f"{comparison_result['effective_yield'] * 100:.1f}%",
                 delta=f"{yield_delta * 100:+.1f}pp")
    with col2:
        st.metric("Profit Margin", f"{comparison_result['profit_margin'] * 100:.1f}%",
                 delta=f"{profit_margin_delta * 100:+.1f}pp")
    with col3:
        st.metric("Total Revenue", f"${comparison_result['total_revenue']:.2f}",
                 delta=f"${revenue_delta:+.2f}")
    with col4:
        st.metric("Net Profit", f"${comparison_result['net_profit']:.2f}",
                 delta=f"${profit_delta:+.2f}")
    with col5:
        st.metric("Capital Deploy", f"{comparison_result['capital_deployment_days']:.0f}d",
                 delta=f"{deploy_delta:+.0f}d",
                 delta_color="inverse")
    with col6:
        st.metric("Expected Loss", f"${comparison_result['expected_loss']:.2f}",
                 delta=f"${loss_delta:+.2f}",
                 delta_color="inverse")

    st.markdown("---")

    # Side-by-Side Waterfall Charts
    st.subheader("Profitability Waterfall Comparison")

    wf_col1, wf_col2 = st.columns(2)

    # Helper function to create waterfall chart
    def create_waterfall(result, title):
        waterfall_x = []
        waterfall_y = []
        waterfall_text = []
        waterfall_measure = []

        # Revenue components
        revenue_components = [
            ("Merchant<br>Commission", result['merchant_commission']),
            ("Fixed<br>Fee", result['fixed_fee_income']),
            ("Interest<br>Income", result['interest_income']),
            ("Late<br>Fees", result['late_fee_income'])
        ]

        for label, value in revenue_components:
            if value > 0:
                waterfall_x.append(label)
                waterfall_y.append(value)
                waterfall_text.append(f"${value:.2f}")
                waterfall_measure.append("relative")

        waterfall_x.append("Total<br>Revenue")
        waterfall_y.append(None)
        waterfall_text.append(f"${result['total_revenue']:.2f}")
        waterfall_measure.append("total")

        # Cost components
        cost_components = [
            ("Expected<br>Loss", result['expected_loss']),
            ("Funding<br>Cost", result['funding_cost'])
        ]

        for label, value in cost_components:
            if value > 0:
                waterfall_x.append(label)
                waterfall_y.append(-value)
                waterfall_text.append(f"-${value:.2f}")
                waterfall_measure.append("relative")

        waterfall_x.append("Net<br>Profit")
        waterfall_y.append(None)
        waterfall_text.append(f"${result['net_profit']:.2f}")
        waterfall_measure.append("total")

        fig = go.Figure(go.Waterfall(
            orientation="v",
            measure=waterfall_measure,
            x=waterfall_x,
            y=waterfall_y,
            text=waterfall_text,
            textposition="outside",
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            increasing={"marker": {"color": "#2ecc71"}},
            decreasing={"marker": {"color": "#e74c3c"}},
            totals={"marker": {"color": "#3498db"}}
        ))

        max_value = result['total_revenue']
        min_value = result['net_profit']
        y_top_padding = max_value * 0.25
        y_axis_min = min(0, min_value)
        y_axis_max = max_value + y_top_padding

        fig.update_layout(
            title=title,
            showlegend=False,
            height=400,
            margin=dict(t=100, b=50, l=50, r=50),
            xaxis_title="",
            yaxis_title="Amount ($)",
            yaxis_range=[y_axis_min, y_axis_max],
            hovermode='x'
        )

        return fig

    with wf_col1:
        fig_a = create_waterfall(current_yield_result, "Scenario A (Current)")
        st.plotly_chart(fig_a, config={'displayModeBar': False})

    with wf_col2:
        fig_b = create_waterfall(comparison_result, "Scenario B (Comparison)")
        st.plotly_chart(fig_b, config={'displayModeBar': False})

    st.markdown("---")

    # Revenue & Cost Breakdown Tables with Deltas
    st.subheader("Detailed Breakdown with Deltas")

    table_col1, table_col2 = st.columns(2)

    with table_col1:
        st.markdown("**Revenue Components**")
        revenue_comparison = pd.DataFrame({
            'Component': ['Interest Income', 'Fixed Fee', 'Merchant Commission', 'Late Fees', '**TOTAL**'],
            'Scenario A ($)': [
                current_yield_result['interest_income'],
                current_yield_result['fixed_fee_income'],
                current_yield_result['merchant_commission'],
                current_yield_result['late_fee_income'],
                current_yield_result['total_revenue']
            ],
            'Scenario B ($)': [
                comparison_result['interest_income'],
                comparison_result['fixed_fee_income'],
                comparison_result['merchant_commission'],
                comparison_result['late_fee_income'],
                comparison_result['total_revenue']
            ]
        })
        revenue_comparison['Delta ($)'] = revenue_comparison['Scenario B ($)'] - revenue_comparison['Scenario A ($)']
        revenue_comparison['Delta (%)'] = ((revenue_comparison['Scenario B ($)'] / revenue_comparison['Scenario A ($)']) - 1) * 100
        revenue_comparison['Delta (%)'] = revenue_comparison['Delta (%)'].apply(lambda x: f"{x:+.1f}%" if abs(x) < 1000 else "N/A")
        revenue_comparison['Delta ($)'] = revenue_comparison['Delta ($)'].apply(lambda x: f"${x:+.2f}")

        st.dataframe(revenue_comparison, hide_index=True, use_container_width=True)

    with table_col2:
        st.markdown("**Cost Components**")
        cost_comparison = pd.DataFrame({
            'Component': ['Funding Cost', 'Expected Loss', '**TOTAL**'],
            'Scenario A ($)': [
                current_yield_result['funding_cost'],
                current_yield_result['expected_loss'],
                current_yield_result['funding_cost'] + current_yield_result['expected_loss']
            ],
            'Scenario B ($)': [
                comparison_result['funding_cost'],
                comparison_result['expected_loss'],
                comparison_result['funding_cost'] + comparison_result['expected_loss']
            ]
        })
        cost_comparison['Delta ($)'] = cost_comparison['Scenario B ($)'] - cost_comparison['Scenario A ($)']
        cost_comparison['Delta (%)'] = ((cost_comparison['Scenario B ($)'] / cost_comparison['Scenario A ($)']) - 1) * 100
        cost_comparison['Delta (%)'] = cost_comparison['Delta (%)'].apply(lambda x: f"{x:+.1f}%" if abs(x) < 1000 else "N/A")
        cost_comparison['Delta ($)'] = cost_comparison['Delta ($)'].apply(lambda x: f"${x:+.2f}")

        st.dataframe(cost_comparison, hide_index=True, use_container_width=True)

    # Summary verdict
    st.markdown("---")
    st.subheader("Summary")

    if comparison_result['effective_yield'] > current_yield_result['effective_yield']:
        st.success(f"✅ **Scenario B performs better** with an effective yield of {comparison_result['effective_yield'] * 100:.1f}% vs {current_yield_result['effective_yield'] * 100:.1f}% (Scenario A). This represents a **{yield_delta * 100:+.1f} percentage point** improvement.")
    elif comparison_result['effective_yield'] < current_yield_result['effective_yield']:
        st.warning(f"⚠️ **Scenario A performs better** with an effective yield of {current_yield_result['effective_yield'] * 100:.1f}% vs {comparison_result['effective_yield'] * 100:.1f}% (Scenario B). Scenario B yields **{yield_delta * 100:.1f} percentage points** less.")
    else:
        st.info("ℹ️ **Both scenarios perform equally** with the same effective yield.")

# Footer
st.caption("BNPL Pricing Strategy Simulator v1.4 | Built with Streamlit")
