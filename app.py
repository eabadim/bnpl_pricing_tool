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

# First installment upfront
first_installment_upfront = st.sidebar.checkbox(
    "Charge First Installment Upfront",
    value=False,
    help="Customer pays first installment at purchase. Reduces capital deployed and loan duration. Merchant still charged on full transaction value."
)

# Interest rate
interest_apr = st.sidebar.slider(
    "Interest Rate (APR %)",
    min_value=0.0,
    max_value=500.0,
    value=250.0,
    step=5.0,
    help="Annual Percentage Rate (set to 0% for interest-free plans)"
) / 100.0

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
    late_installment_pct=late_installment_pct,
    first_installment_upfront=first_installment_upfront
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
    first_installment_upfront=first_installment_upfront
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
        'first_installment_upfront': first_installment_upfront
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

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig9, config={'displayModeBar': False})
        st.caption("💸 **Funding Cost Impact**: Your cost of capital directly reduces net yield. Lower funding costs = higher profitability. Critical for debt-financed BNPL models.")
    with col2:
        st.write("")  # Empty placeholder for symmetry

# Footer
st.caption("BNPL Pricing Strategy Simulator v1.4 | Built with Streamlit")
