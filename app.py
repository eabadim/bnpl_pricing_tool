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

# Initialize session state for comparison scenario (use widget keys directly)
if 'comp_principal_input' not in st.session_state:
    st.session_state.comp_principal_input = 100.0
    st.session_state.comp_installments_input = 7
    st.session_state.comp_frequency_input = "Biweekly"  # Different from Scenario A (Monthly)
    st.session_state.comp_first_upfront_input = False
    st.session_state.comp_early_rate_input = 0.0
    st.session_state.comp_early_inst_input = 3
    st.session_state.comp_late_repay_rate_input = 0.0
    st.session_state.comp_days_late_input = 5
    st.session_state.comp_apr_input = 250.0  # Matches sidebar default (250% interest rate)
    st.session_state.comp_fixed_fee_input = 0.0
    st.session_state.comp_late_fee_input = 3.0
    st.session_state.comp_late_pct_input = 20.0
    st.session_state.comp_merchant_comm_input = 1.0
    st.session_state.comp_settlement_input = 1
    st.session_state.comp_fraud_rate_input = 0.0
    st.session_state.comp_default_input = 15.0
    st.session_state.comp_recovery_input = 10.0
    st.session_state.comp_fraud_recovery_input = 10.0
    st.session_state.comp_funding_input = 8.0

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

with st.sidebar.expander("**Payment Behavior**", expanded=False):
    st.markdown("**Early Repayment**")
    early_repayment_rate = st.slider(
        "Early Repayment Rate (%)",
        min_value=0.0,
        max_value=50.0,
        value=15.0,
        step=1.0,
        help="Percentage of loans repaid early (zero defaults, reduced interest income)"
    ) / 100.0

    avg_repayment_installment = None
    if early_repayment_rate > 0:
        avg_repayment_installment = st.slider(
            "Avg Early Repayment Installment",
            min_value=1,
            max_value=max(1, avg_installments - 1),
            value=max(1, avg_installments // 2),
            help="Average installment number at which early repayment occurs"
        )

    st.markdown("---")
    st.markdown("**Late Repayment**")
    late_repayment_rate = st.slider(
        "Late Repayment Rate (%)",
        min_value=0.0,
        max_value=50.0,
        value=15.0,
        step=1.0,
        help="Percentage of loans that pay late (zero defaults, extra interest + all late fees)"
    ) / 100.0

    avg_days_late_per_installment = 0
    if late_repayment_rate > 0:
        avg_days_late_per_installment = st.slider(
            "Avg Days Late Per Installment",
            min_value=0,
            max_value=30,
            value=20,
            help="Average days late per installment payment"
        )

with st.sidebar.expander("**Pricing**", expanded=False):
    # Interest rate
    interest_apr = st.slider(
        "Interest Rate (%)",
        min_value=0.0,
        max_value=500.0,
        value=250.0,
        step=5.0,
        help="Nominal annual interest rate charged on the principal (set to 0% for interest-free plans)"
    ) / 100.0

    # Late interest rate
    st.markdown("---")
    use_same_late_rate = st.checkbox(
        "Use same rate for late payments",
        value=True,
        help="When checked, late payers are charged the same interest rate. When unchecked, you can set a higher penalty rate for late payers."
    )

    if use_same_late_rate:
        late_interest_apr = interest_apr
    else:
        late_interest_apr = st.slider(
            "Late Interest Rate (%)",
            min_value=0.0,
            max_value=500.0,
            value=250.0,
            step=5.0,
            help="Higher penalty rate charged to late payers (does not affect APR shown to customers)"
        ) / 100.0

    st.markdown("---")
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
    st.markdown("**Business Parameters**")
    # Merchant parameters
    merchant_commission = st.slider(
        "Merchant Commission (%)",
        min_value=0.0,
        max_value=20.0,
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

    st.markdown("---")
    st.markdown("**Loss Rates**")
    # Fraud and default parameters
    fraud_rate = st.slider(
        "Fraud Rate (%)",
        min_value=0.0,
        max_value=30.0,
        value=12.0,
        step=0.5,
        help="Customers who never pay (immediate loss)"
    ) / 100.0

    default_rate = st.slider(
        "Default Rate (%)",
        min_value=0.0,
        max_value=30.0,
        value=8.0,
        step=0.5,
        help="Legitimate defaults due to financial hardship"
    ) / 100.0

    st.markdown("---")
    st.markdown("**Recovery Rates**")
    recovery_rate = st.slider(
        "Default Recovery Rate (%)",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=5.0,
        help="% recovered from legitimate defaults"
    ) / 100.0

    fraud_recovery_rate = st.slider(
        "Fraud Recovery Rate (%)",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=5.0,
        help="% recovered from fraud cases"
    ) / 100.0

    # Funding cost (optional, defaulted to 0)
    funding_cost = st.slider(
        "Funding Cost (%)",
        min_value=0.0,
        max_value=20.0,
        value=8.0,
        step=0.5,
        help="Annual cost of capital (optional)"
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
    fraud_rate=fraud_rate,
    default_rate=default_rate,
    recovery_rate=recovery_rate,
    fraud_recovery_rate=fraud_recovery_rate,
    fixed_fee_pct=fixed_fee_pct,
    funding_cost_apr=funding_cost,
    installment_frequency_days=installment_frequency_days,
    late_fee_amount=late_fee_amount,
    late_installment_pct=late_installment_pct,
    first_installment_upfront=first_installment_upfront,
    early_repayment_rate=early_repayment_rate,
    avg_repayment_installment=avg_repayment_installment,
    late_repayment_rate=late_repayment_rate,
    avg_days_late_per_installment=avg_days_late_per_installment,
    late_interest_apr=late_interest_apr
)

# Calculate required APR
required_apr = calculate_required_apr(
    target_yield=target_yield,
    principal=avg_principal,
    installments=avg_installments,
    merchant_commission_pct=merchant_commission,
    settlement_delay_days=settlement_delay,
    fraud_rate=fraud_rate,
    default_rate=default_rate,
    recovery_rate=recovery_rate,
    fraud_recovery_rate=fraud_recovery_rate,
    fixed_fee_pct=fixed_fee_pct,
    funding_cost_apr=funding_cost,
    installment_frequency_days=installment_frequency_days,
    late_fee_amount=late_fee_amount,
    late_installment_pct=late_installment_pct,
    first_installment_upfront=first_installment_upfront,
    early_repayment_rate=early_repayment_rate,
    avg_repayment_installment=avg_repayment_installment,
    late_repayment_rate=late_repayment_rate,
    avg_days_late_per_installment=avg_days_late_per_installment,
    late_interest_apr=late_interest_apr
)

# Calculate interest-free installment cap
interest_free_cap = estimate_interest_free_cap(
    target_yield=target_yield,
    principal=avg_principal,
    merchant_commission_pct=merchant_commission,
    settlement_delay_days=settlement_delay,
    fraud_rate=fraud_rate,
    default_rate=default_rate,
    recovery_rate=recovery_rate,
    fraud_recovery_rate=fraud_recovery_rate,
    fixed_fee_pct=fixed_fee_pct,
    funding_cost_apr=funding_cost,
    installment_frequency_days=installment_frequency_days,
    late_fee_amount=late_fee_amount,
    late_installment_pct=late_installment_pct,
    first_installment_upfront=first_installment_upfront,
    early_repayment_rate=early_repayment_rate,
    avg_repayment_installment=avg_repayment_installment,
    late_repayment_rate=late_repayment_rate,
    avg_days_late_per_installment=avg_days_late_per_installment,
    late_interest_apr=late_interest_apr,
    max_installments=12
)

# Summary metrics - Compact view
st.header("Key Metrics")

col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

with col1:
    st.metric(
        "Effective Yield",
        f"{current_yield_result['effective_yield'] * 100:.1f}%",
        delta=f"{(current_yield_result['effective_yield'] - target_yield) * 100:.1f}%",
        help="The annualized return on capital after accounting for all revenues, costs, defaults, and time value of money. This is your actual portfolio-level profitability. Delta shows difference from target yield."
    )

with col2:
    st.metric(
        "Interest Rate",
        f"{interest_apr * 100:.1f}%",
        delta=f"{(required_apr - interest_apr) * 100:.1f}%",
        help="Current nominal interest rate. Delta shows the change needed to hit your target yield (positive = need to increase, negative = can decrease)."
    )

with col3:
    st.metric(
        "APR",
        f"{current_yield_result['apr'] * 100:.1f}%",
        help="Annual Percentage Rate - the total annualized cost to the customer including interest rate plus annualized fixed fees. This is the regulatory/customer-facing rate."
    )

with col4:
    st.metric(
        "Profit Margin",
        f"{current_yield_result['profit_margin'] * 100:.1f}%",
        help="Net profit as a percentage of principal (Net Profit / Principal). Shows profitability per loan before annualizing."
    )

with col5:
    st.metric(
        "Loan Duration",
        f"{current_yield_result['loan_duration_days']}d",
        help="Total time from loan origination to final payment in days (installments × frequency)."
    )

with col6:
    st.metric(
        "Capital Deploy",
        f"{current_yield_result['capital_deployment_days']:.0f}d",
        help="Average days capital is deployed, accounting for when merchant is paid. Lower is better - capital locked up for less time."
    )

with col7:
    st.metric(
        "Settle Benefit",
        f"+{current_yield_result['settlement_delay_benefit'] * 100:.1f}%",
        help="The yield boost from settlement delay. When you pay the merchant later, you earn extra yield on the float."
    )

# Portfolio normalization warning
if current_yield_result.get('portfolio_normalized', False):
    original_total = (early_repayment_rate + late_repayment_rate + default_rate + fraud_rate) * 100
    st.warning(
        f"⚠️ **Portfolio segments exceeded 100%** (total: {original_total:.1f}%). "
        f"Percentages have been automatically normalized to sum to 100%. "
        f"Adjusted values: Early {current_yield_result['early_repayment_rate']*100:.1f}%, "
        f"Late {current_yield_result['late_repayment_rate']*100:.1f}%, "
        f"Default {current_yield_result['default_rate']*100:.1f}%, "
        f"Fraud {current_yield_result['fraud_rate']*100:.1f}%",
        icon="⚠️"
    )

# Portfolio Breakdown Section
with st.expander("📊 Portfolio Breakdown", expanded=False):
    # Calculate portfolio percentages
    early_pct = current_yield_result['early_repayment_rate'] * 100
    late_pct = current_yield_result['late_repayment_rate'] * 100
    default_pct = current_yield_result['default_rate'] * 100
    fraud_pct = current_yield_result['fraud_rate'] * 100
    ontime_pct = current_yield_result['ontime_pct'] * 100

    # Two-column layout
    left_col, right_col = st.columns([1, 1])

    with left_col:
        st.markdown("### Customer Cohorts")

        # Early Repayers
        with st.expander(f"⚡ Early Repayers ({early_pct:.1f}%)", expanded=False):
            st.markdown("""
            **What**: Customers who repay their loan before the scheduled final installment.

            **Behavior**:
            - Repay at installment {avg_inst} on average (out of {total_inst} total)
            - Zero defaults in this segment
            - Shorter loan duration than expected

            **Revenue Impact**:
            - ✅ Fixed fees collected in full (upfront)
            - ✅ Merchant commission collected in full
            - ⚠️ Reduced interest income (shorter duration)
            - ✅ Capital freed up faster for redeployment

            **Key Characteristic**: Low-risk segment with reduced interest revenue but excellent credit quality.
            """.format(
                avg_inst=avg_repayment_installment if avg_repayment_installment else "N/A",
                total_inst=avg_installments
            ))

        # Late Repayers
        with st.expander(f"🕐 Late Repayers ({late_pct:.1f}%)", expanded=False):
            st.markdown("""
            **What**: Customers who consistently pay late on every installment but eventually pay in full.

            **Behavior**:
            - Pay {days_late}d late per installment on average
            - Total delay: +{total_delay}d across all installments
            - Zero defaults in this segment
            - Extended loan duration

            **Revenue Impact**:
            - ✅ Fixed fees collected in full
            - ✅ Merchant commission collected in full
            - ✅ Increased interest income (extended duration)
            - ✅ ALL installments incur late fees (guaranteed late fee revenue)
            - ⚠️ Capital locked up longer

            **Key Characteristic**: Higher revenue segment due to extended interest accrual and guaranteed late fees, but slower capital turnover.
            """.format(
                days_late=avg_days_late_per_installment,
                total_delay=avg_installments * avg_days_late_per_installment
            ))

        # On-Time Payers
        with st.expander(f"✅ On-Time Payers ({ontime_pct:.1f}%)", expanded=False):
            st.markdown("""
            **What**: Customers who follow the payment schedule as planned.

            **Behavior**:
            - Pay on scheduled due dates
            - Zero defaults in this segment
            - Standard loan duration
            - Occasional late payments ({late_pct:.0f}% of installments)

            **Revenue Impact**:
            - ✅ Fixed fees collected in full
            - ✅ Merchant commission collected in full
            - ✅ Standard interest income (normal duration)
            - ✅ Sporadic late fee revenue
            - ✅ Predictable capital deployment

            **Key Characteristic**: Core revenue segment with predictable cash flows and zero credit losses.
            """.format(
                late_pct=late_installment_pct * 100
            ))

        # Defaults
        with st.expander(f"⚠️ Defaults ({default_pct:.1f}%)", expanded=False):
            st.markdown("""
            **What**: Legitimate customers who default due to financial hardship (job loss, medical emergency, etc.).

            **Behavior**:
            - Intend to pay but cannot due to circumstances
            - May have made partial payments before defaulting
            - Some recovery possible through collections

            **Revenue Impact**:
            - ⚠️ Partial interest income (up to default point)
            - ⚠️ Partial fixed fees
            - ✅ Merchant commission collected (full principal disbursed)
            - ⚠️ Sporadic late fees before default
            - ❌ Expected loss: {loss_pct:.1f}% of principal (after {recovery_pct:.0f}% recovery)

            **Key Characteristic**: Credit risk with partial recovery potential. Different from fraud - legitimate financial distress.
            """.format(
                loss_pct=(1 - recovery_rate) * 100,
                recovery_pct=recovery_rate * 100
            ))

        # Fraud
        with st.expander(f"🚨 Fraud ({fraud_pct:.1f}%)", expanded=False):
            st.markdown("""
            **What**: Bad actors who never intend to pay - identity theft, synthetic fraud, or deliberate non-payment.

            **Behavior**:
            - Zero payments made (immediate loss)
            - Never intend to repay
            - Minimal recovery through collections

            **Revenue Impact**:
            - ❌ Zero interest income
            - ❌ Zero fixed fees
            - ✅ Merchant commission collected (full principal disbursed)
            - ❌ Zero late fees
            - ❌ Expected loss: {loss_pct:.1f}% of principal (after {recovery_pct:.0f}% fraud recovery)

            **Key Characteristic**: Highest risk segment. Must be minimized through fraud detection, identity verification, and screening.
            """.format(
                loss_pct=(1 - fraud_recovery_rate) * 100,
                recovery_pct=fraud_recovery_rate * 100
            ))

    with right_col:
        st.markdown("### Portfolio Distribution")

        # Create pie chart
        labels = ['Early Repayers', 'Late Repayers', 'On-Time Payers', 'Defaults', 'Fraud']
        values = [early_pct, late_pct, ontime_pct, default_pct, fraud_pct]
        colors = ['#9b59b6', '#FED740', '#2ecc71', '#f39c12', '#e74c3c']

        fig_pie = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.3,
            marker=dict(colors=colors),
            textinfo='label+percent',
            textposition='auto',
            hovertemplate='<b>%{label}</b><br>%{value:.1f}%<br>(%{percent})<extra></extra>'
        )])

        fig_pie.update_layout(
            showlegend=False,
            height=400,
            margin=dict(t=20, b=20, l=20, r=20)
        )

        st.plotly_chart(fig_pie, config={'displayModeBar': False}, use_container_width=True)

# Float scenario warning - critical alert
if current_yield_result['is_float_scenario']:
    st.warning(
        f"⚠️ **FLOAT SCENARIO**: Settlement ({settlement_delay}d) ≥ Loan ({current_yield_result['loan_duration_days']}d) — "
        f"Customers pay BEFORE merchant. Float: {settlement_delay - current_yield_result['loan_duration_days']}d. Actual yield: INFINITE.",
        icon="⚠️"
    )

# Revenue breakdown - in expander to save space
with st.expander("💰 Revenue & Cost Breakdown", expanded=False):
    # Calculate surrendered early repayment interest
    surrendered_early_interest = 0.0
    if current_yield_result['has_early_repayment']:
        # What early repayers would have paid if they stayed full term
        full_term_interest_early = avg_principal * interest_apr * (avg_installments * installment_frequency_days / 365) * 0.5 * early_repayment_rate
        # What they actually paid (shorter duration)
        early_duration_years = (avg_repayment_installment * installment_frequency_days / 365) if avg_repayment_installment else 0
        actual_interest_early = avg_principal * interest_apr * early_duration_years * 0.5 * early_repayment_rate
        # Surrendered = foregone interest
        surrendered_early_interest = full_term_interest_early - actual_interest_early

    # Build waterfall chart dynamically, excluding zero values
    waterfall_x = []
    waterfall_y = []
    waterfall_text = []
    waterfall_measure = []

    # Revenue components (in order: Merchant Commission, Fixed Fee, Interest, Late Interest, Late Fees)
    revenue_components = [
        ("Merchant<br>Commission", current_yield_result['merchant_commission']),
        ("Fixed<br>Fee", current_yield_result['fixed_fee_income']),
        ("Interest<br>Income", current_yield_result['interest_income']),
        ("Late<br>Interest", current_yield_result['late_interest_income']),
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

    # Cost components (show default and fraud losses separately)
    cost_components = [
        ("Default<br>Loss", current_yield_result['default_loss']),
        ("Fraud<br>Loss", current_yield_result['fraud_loss']),
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

    # Add Surrendered Early Repayment Interest as a separate grey bar (if applicable)
    if surrendered_early_interest > 0:
        waterfall_fig.add_trace(go.Bar(
            x=["Surrendered<br>Early Interest"],
            y=[surrendered_early_interest],
            marker=dict(color="#95a5a6"),  # Grey
            text=[f"${surrendered_early_interest:.2f}"],
            textposition="outside",
            name="Surrendered Interest",
            showlegend=False,
            base=[current_yield_result['net_profit']],  # Start from Net Profit
            hovertemplate='<b>%{x}</b><br>$%{y:.2f}<extra></extra>'
        ))

    # Calculate y-axis range - extend above total revenue for better label visibility
    max_value = current_yield_result['total_revenue']
    if surrendered_early_interest > 0:
        # If surrendered interest bar exists, it goes UP from Net Profit
        max_value = max(max_value, current_yield_result['net_profit'] + surrendered_early_interest)
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
        hovermode='x',
        barmode='overlay'  # Allow grey bar to overlay at its position
    )

    st.plotly_chart(waterfall_fig, config={'displayModeBar': False})

    st.markdown("---")

    # Detailed breakdown tables
    col1, col2 = st.columns(2)

    with col1:
        # Revenue components (show late interest separately)
        revenue_data = {
            'Component': ['Interest Income', 'Late Interest', 'Fixed Fee', 'Merchant Commission', 'Late Fees'],
            'Amount ($)': [
                current_yield_result['interest_income'],
                current_yield_result['late_interest_income'],
                current_yield_result['fixed_fee_income'],
                current_yield_result['merchant_commission'],
                current_yield_result['late_fee_income']
            ]
        }
        revenue_df = pd.DataFrame(revenue_data)
        # Filter out zero values
        revenue_df = revenue_df[revenue_df['Amount ($)'] > 0]
        if not revenue_df.empty:
            revenue_df['Percentage'] = (revenue_df['Amount ($)'] / revenue_df['Amount ($)'].sum() * 100).round(2)

        st.write("**Revenue Sources**")
        st.dataframe(revenue_df, hide_index=True, width='stretch')

        st.metric("Total Revenue", f"${current_yield_result['total_revenue']:.2f}")

    with col2:
        # Cost/loss components (show default and fraud separately)
        cost_data = {
            'Component': ['Default Loss', 'Fraud Loss', 'Funding Cost'],
            'Amount ($)': [
                current_yield_result['default_loss'],
                current_yield_result['fraud_loss'],
                current_yield_result['funding_cost']
            ]
        }
        cost_df = pd.DataFrame(cost_data)
        # Filter out zero values
        cost_df = cost_df[cost_df['Amount ($)'] > 0]

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
        'fraud_rate': fraud_rate,
        'default_rate': default_rate,
        'recovery_rate': recovery_rate,
        'fraud_recovery_rate': fraud_recovery_rate,
        'fixed_fee_pct': fixed_fee_pct,
        'funding_cost_apr': funding_cost,
        'installment_frequency_days': installment_frequency_days,
        'late_fee_amount': late_fee_amount,
        'late_installment_pct': late_installment_pct,
        'first_installment_upfront': first_installment_upfront,
        'early_repayment_rate': early_repayment_rate,
        'avg_repayment_installment': avg_repayment_installment,
        'late_repayment_rate': late_repayment_rate,
        'avg_days_late_per_installment': avg_days_late_per_installment,
        'late_interest_apr': late_interest_apr
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
    commission_range = np.linspace(0.01, 0.20, 20)
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

    # Chart 4: Effective Yield vs Settlement Delay (NEW - shows settlement delay impact)
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
        title="Effective Yield vs Settlement Delay",
        xaxis_title="Settlement Delay (days)",
        yaxis_title="Effective Yield (%)",
        yaxis_range=[-25, 150],
        hovermode='x unified',
        height=300
    )

    # Chart 5: Yield vs Interest Rate
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
        annotation_text="Current Rate"
    )
    fig5.update_layout(
        title="Effective Yield vs Interest Rate",
        xaxis_title="Interest Rate (%)",
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
        xaxis_title="Funding Cost (%)",
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
        st.caption("💰 **Interest Rate Impact**: Interest rate is the most direct yield driver. Linear relationship - each percentage point increase in interest rate translates to higher effective yield. Set to 0% for interest-free plans.")
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

    # Chart 11: Yield vs Late Repayment Rate
    late_repayment_range = np.linspace(0, 0.50, 20)  # 0% to 50%
    yields_by_late_repayment = []

    for late_rate in late_repayment_range:
        params = base_params.copy()
        params['apr'] = interest_apr
        params['late_repayment_rate'] = late_rate
        # Use reasonable default for days late if rate > 0
        params['avg_days_late_per_installment'] = avg_days_late_per_installment if late_rate > 0 else 0
        result = calculate_effective_yield(**params)
        yields_by_late_repayment.append(result['effective_yield'])

    fig11 = go.Figure()
    fig11.add_trace(go.Scatter(
        x=late_repayment_range * 100,
        y=np.array(yields_by_late_repayment) * 100,
        mode='lines+markers',
        name='Effective Yield',
        line=dict(color='orange', width=2)
    ))
    fig11.add_hline(
        y=target_yield * 100,
        line_dash="dash",
        line_color="red",
        annotation_text="Target Yield"
    )
    fig11.update_layout(
        title="Effective Yield vs Late Repayment Rate",
        xaxis_title="Late Repayment Rate (%)",
        yaxis_title="Effective Yield (%)",
        yaxis_range=[-25, 150],
        hovermode='x unified',
        height=300
    )

    # Chart 12: Yield vs Fraud Rate
    fraud_rate_range = np.linspace(0, 0.30, 20)  # 0% to 30%
    yields_by_fraud = []

    for fraud in fraud_rate_range:
        params = base_params.copy()
        params['apr'] = interest_apr
        params['fraud_rate'] = fraud
        result = calculate_effective_yield(**params)
        yields_by_fraud.append(result['effective_yield'])

    fig12 = go.Figure()
    fig12.add_trace(go.Scatter(
        x=fraud_rate_range * 100,
        y=np.array(yields_by_fraud) * 100,
        mode='lines+markers',
        name='Effective Yield',
        line=dict(color='red', width=2)
    ))
    fig12.add_hline(
        y=target_yield * 100,
        line_dash="dash",
        line_color="red",
        annotation_text="Target Yield"
    )
    fig12.update_layout(
        title="Effective Yield vs Fraud Rate",
        xaxis_title="Fraud Rate (%)",
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

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig11, config={'displayModeBar': False})
        st.caption("🕐 **Late Repayment Impact**: Late repayers increase yield through extended interest accrual and guaranteed late fees on ALL installments. Zero defaults on late segment. Positive yield impact if days late > 0.")
    with col2:
        st.plotly_chart(fig12, config={'displayModeBar': False})
        st.caption("🚨 **Fraud Rate Impact**: Fraud cases generate immediate losses with minimal recovery. Distinct from defaults - fraudsters never intend to pay. Critical to minimize through identity verification and fraud detection.")

# Scenario Comparison
with st.expander("🔄 Scenario Comparison", expanded=False):
    st.markdown("""
    Compare your current scenario (Scenario A) against an alternative configuration (Scenario B).
    Adjust the parameters below to model different pricing strategies and see side-by-side comparisons of key metrics, profitability, and revenue breakdown.
    """)

    # Copy current scenario button
    if st.button("📋 Copy Current Scenario to Comparison"):
        # Update only the widget keys (with _input suffix)
        st.session_state.comp_principal_input = avg_principal
        st.session_state.comp_installments_input = avg_installments
        st.session_state.comp_frequency_input = installment_frequency
        st.session_state.comp_first_upfront_input = first_installment_upfront
        st.session_state.comp_early_rate_input = early_repayment_rate * 100
        st.session_state.comp_early_inst_input = avg_repayment_installment if avg_repayment_installment else max(1, avg_installments // 2)
        st.session_state.comp_late_repay_rate_input = late_repayment_rate * 100
        st.session_state.comp_days_late_input = avg_days_late_per_installment
        st.session_state.comp_apr_input = interest_apr * 100
        st.session_state.comp_fixed_fee_input = fixed_fee_pct * 100
        st.session_state.comp_late_fee_input = late_fee_amount
        st.session_state.comp_late_pct_input = late_installment_pct * 100
        st.session_state.comp_merchant_comm_input = merchant_commission * 100
        st.session_state.comp_settlement_input = settlement_delay
        st.session_state.comp_fraud_rate_input = fraud_rate * 100
        st.session_state.comp_default_input = default_rate * 100
        st.session_state.comp_recovery_input = recovery_rate * 100
        st.session_state.comp_fraud_recovery_input = fraud_recovery_rate * 100
        st.session_state.comp_funding_input = funding_cost * 100
        st.session_state.show_copy_success = True
        st.rerun()

    # Show success message after copy
    if st.session_state.get('show_copy_success', False):
        st.success("✅ Current scenario copied to Scenario B! Expand the configuration below to view/adjust.")
        st.session_state.show_copy_success = False

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
                step=10.0,
                key="comp_principal_input"
            )
            comp_installments = st.slider(
                "Installments",
                min_value=1,
                max_value=36,
                key="comp_installments_input"
            )
            comp_frequency = st.radio(
                "Frequency",
                options=["Biweekly", "Monthly"],
                index=0 if st.session_state.comp_frequency_input == "Biweekly" else 1,
                key="comp_frequency_input"
            )
            comp_first_upfront = st.checkbox(
                "First Installment Upfront",
                key="comp_first_upfront_input"
            )

            st.markdown("**Early Repayment**")
            comp_early_rate = st.slider(
                "Early Repayment Rate (%)",
                min_value=0.0,
                max_value=50.0,
                step=1.0,
                key="comp_early_rate_input"
            )
            comp_early_inst = None
            if comp_early_rate > 0:
                comp_early_inst = st.slider(
                    "Avg Early Installment",
                    min_value=1,
                    max_value=max(1, comp_installments - 1),
                    value=min(st.session_state.get('comp_early_inst_input', 3), max(1, comp_installments - 1)),
                    key="comp_early_inst_input"
                )

            st.markdown("**Late Repayment**")
            comp_late_repay_rate = st.slider(
                "Late Repayment Rate (%)",
                min_value=0.0,
                max_value=50.0,
                step=1.0,
                key="comp_late_repay_rate_input"
            )
            comp_days_late = 0
            if comp_late_repay_rate > 0:
                comp_days_late = st.slider(
                    "Avg Days Late Per Inst.",
                    min_value=0,
                    max_value=30,
                    key="comp_days_late_input"
                )

        with col2:
            st.markdown("**Pricing**")
            comp_apr = st.slider(
                "Interest Rate (%)",
                min_value=0.0,
                max_value=500.0,
                step=5.0,
                key="comp_apr_input"
            )

            # Late interest rate for comparison scenario
            comp_use_same_late_rate = st.checkbox(
                "Use same rate for late payments (B)",
                value=True,
                key="comp_use_same_late_rate"
            )
            if comp_use_same_late_rate:
                comp_late_interest_apr = comp_apr
            else:
                comp_late_interest_apr = st.slider(
                    "Late Interest Rate (%) (B)",
                    min_value=0.0,
                    max_value=500.0,
                    step=5.0,
                    key="comp_late_interest_apr_input"
                )

            comp_fixed_fee = st.slider(
                "Fixed Fee (%)",
                min_value=0.0,
                max_value=100.0,
                step=1.0,
                key="comp_fixed_fee_input"
            )

            st.markdown("**Late Fees**")
            comp_late_fee = st.number_input(
                "Late Fee ($)",
                min_value=0.0,
                max_value=20.0,
                step=0.50,
                key="comp_late_fee_input"
            )
            comp_late_pct = st.slider(
                "% Paid Late",
                min_value=0.0,
                max_value=100.0,
                step=1.0,
                key="comp_late_pct_input"
            )

        with col3:
            st.markdown("**Business Parameters**")
            comp_merchant_comm = st.slider(
                "Merchant Commission (%)",
                min_value=0.0,
                max_value=20.0,
                step=0.1,
                key="comp_merchant_comm_input"
            )
            comp_settlement = st.slider(
                "Settlement Delay (days)",
                min_value=0,
                max_value=60,
                key="comp_settlement_input"
            )

            st.markdown("**Risk Parameters**")
            comp_fraud_rate = st.slider(
                "Fraud Rate (%)",
                min_value=0.0,
                max_value=30.0,
                step=0.5,
                key="comp_fraud_rate_input"
            )
            comp_default = st.slider(
                "Default Rate (%)",
                min_value=0.0,
                max_value=30.0,
                step=0.5,
                key="comp_default_input"
            )
            comp_recovery = st.slider(
                "Default Recovery Rate (%)",
                min_value=0.0,
                max_value=100.0,
                step=5.0,
                key="comp_recovery_input"
            )
            comp_fraud_recovery = st.slider(
                "Fraud Recovery Rate (%)",
                min_value=0.0,
                max_value=100.0,
                step=5.0,
                key="comp_fraud_recovery_input"
            )

            st.markdown("**Costs**")
            comp_funding = st.slider(
                "Funding Cost (%)",
                min_value=0.0,
                max_value=20.0,
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
        fraud_rate=comp_fraud_rate / 100,
        default_rate=comp_default / 100,
        recovery_rate=comp_recovery / 100,
        fraud_recovery_rate=comp_fraud_recovery / 100,
        fixed_fee_pct=comp_fixed_fee / 100,
        funding_cost_apr=comp_funding / 100,
        installment_frequency_days=comp_frequency_days,
        late_fee_amount=comp_late_fee,
        late_installment_pct=comp_late_pct / 100,
        first_installment_upfront=comp_first_upfront,
        early_repayment_rate=comp_early_rate / 100,
        avg_repayment_installment=comp_early_inst,
        late_repayment_rate=comp_late_repay_rate / 100,
        avg_days_late_per_installment=comp_days_late,
        late_interest_apr=comp_late_interest_apr / 100
    )

    st.markdown("---")
    st.header("Comparison Results")

    # Portfolio normalization warning for Scenario B
    if comparison_result.get('portfolio_normalized', False):
        original_total = (comp_early_rate + comp_late_repay_rate + comp_default + comp_fraud_rate)
        st.warning(
            f"⚠️ **Scenario B portfolio segments exceeded 100%** (total: {original_total:.1f}%). "
            f"Percentages have been automatically normalized to sum to 100%. "
            f"Adjusted values: Early {comparison_result['early_repayment_rate']*100:.1f}%, "
            f"Late {comparison_result['late_repayment_rate']*100:.1f}%, "
            f"Default {comparison_result['default_rate']*100:.1f}%, "
            f"Fraud {comparison_result['fraud_rate']*100:.1f}%",
            icon="⚠️"
        )

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
    def create_waterfall(result, title, surrendered_interest=0.0):
        waterfall_x = []
        waterfall_y = []
        waterfall_text = []
        waterfall_measure = []

        # Revenue components (show late interest separately)
        revenue_components = [
            ("Merchant<br>Commission", result['merchant_commission']),
            ("Fixed<br>Fee", result['fixed_fee_income']),
            ("Interest<br>Income", result['interest_income']),
            ("Late<br>Interest", result['late_interest_income']),
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

        # Cost components (show default and fraud separately)
        cost_components = [
            ("Default<br>Loss", result['default_loss']),
            ("Fraud<br>Loss", result['fraud_loss']),
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
            increasing={"marker": {"color": "#2ecc71"}},  # Green for revenue
            decreasing={"marker": {"color": "#e74c3c"}},  # Red for costs
            totals={"marker": {"color": "#3498db"}}  # Blue for totals
        ))

        # Add Surrendered Early Repayment Interest as a separate grey bar (if applicable)
        if surrendered_interest > 0:
            fig.add_trace(go.Bar(
                x=["Surrendered<br>Early Interest"],
                y=[surrendered_interest],
                marker=dict(color="#95a5a6"),  # Grey
                text=[f"${surrendered_interest:.2f}"],
                textposition="outside",
                name="Surrendered Interest",
                showlegend=False,
                base=[result['net_profit']],  # Start from Net Profit
                hovertemplate='<b>%{x}</b><br>$%{y:.2f}<extra></extra>'
            ))

        max_value = result['total_revenue']
        if surrendered_interest > 0:
            # If surrendered interest bar exists, it goes UP from Net Profit
            max_value = max(max_value, result['net_profit'] + surrendered_interest)
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
            hovermode='x',
            barmode='overlay'  # Allow grey bar to overlay at its position
        )

        return fig

    # Calculate surrendered early interest for Scenario A
    surrendered_a = 0.0
    if current_yield_result['has_early_repayment']:
        full_term_interest_a = avg_principal * interest_apr * (avg_installments * installment_frequency_days / 365) * 0.5 * early_repayment_rate
        early_duration_years_a = (avg_repayment_installment * installment_frequency_days / 365) if avg_repayment_installment else 0
        actual_interest_a = avg_principal * interest_apr * early_duration_years_a * 0.5 * early_repayment_rate
        surrendered_a = full_term_interest_a - actual_interest_a

    # Calculate surrendered early interest for Scenario B
    surrendered_b = 0.0
    if comparison_result['has_early_repayment']:
        comp_early_rate_decimal = comp_early_rate / 100 if comp_early_rate > 0 else 0
        full_term_interest_b = comp_principal * (comp_apr / 100) * (comp_installments * comp_frequency_days / 365) * 0.5 * comp_early_rate_decimal
        early_duration_years_b = (comp_early_inst * comp_frequency_days / 365) if comp_early_inst else 0
        actual_interest_b = comp_principal * (comp_apr / 100) * early_duration_years_b * 0.5 * comp_early_rate_decimal
        surrendered_b = full_term_interest_b - actual_interest_b

    with wf_col1:
        fig_a = create_waterfall(current_yield_result, "Scenario A (Current)", surrendered_a)
        st.plotly_chart(fig_a, config={'displayModeBar': False})

    with wf_col2:
        fig_b = create_waterfall(comparison_result, "Scenario B (Comparison)", surrendered_b)
        st.plotly_chart(fig_b, config={'displayModeBar': False})

    st.markdown("---")

    # Revenue & Cost Breakdown Tables with Deltas
    st.subheader("Detailed Breakdown with Deltas")

    table_col1, table_col2 = st.columns(2)

    with table_col1:
        st.markdown("**Revenue Components**")
        revenue_comparison = pd.DataFrame({
            'Component': ['Interest Income', 'Late Interest', 'Fixed Fee', 'Merchant Commission', 'Late Fees', '**TOTAL**'],
            'Scenario A ($)': [
                current_yield_result['interest_income'],
                current_yield_result['late_interest_income'],
                current_yield_result['fixed_fee_income'],
                current_yield_result['merchant_commission'],
                current_yield_result['late_fee_income'],
                current_yield_result['total_revenue']
            ],
            'Scenario B ($)': [
                comparison_result['interest_income'],
                comparison_result['late_interest_income'],
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
            'Component': ['Default Loss', 'Fraud Loss', 'Funding Cost', '**TOTAL**'],
            'Scenario A ($)': [
                current_yield_result['default_loss'],
                current_yield_result['fraud_loss'],
                current_yield_result['funding_cost'],
                current_yield_result['funding_cost'] + current_yield_result['expected_loss']
            ],
            'Scenario B ($)': [
                comparison_result['default_loss'],
                comparison_result['fraud_loss'],
                comparison_result['funding_cost'],
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

# Cash Flow Projection
with st.expander("💰 Cash Flow Projection", expanded=False):
    st.markdown("""
    Project your portfolio's cash flows over time based on current loan parameters.
    This models new loan originations, customer repayments, and funding requirements month by month.
    """)

    # Input controls
    col1, col2, col3 = st.columns(3)

    with col1:
        starting_portfolio = st.number_input(
            "Starting Portfolio Size ($)",
            min_value=10000.0,
            max_value=1000000000.0,
            value=1000000.0,
            step=100000.0,
            help="Initial portfolio principal outstanding"
        )

    with col2:
        projection_months = st.slider(
            "Projection Period (months)",
            min_value=1,
            max_value=24,
            value=12,
            help="Number of months to project"
        )

    with col3:
        monthly_overhead = st.number_input(
            "Monthly Overhead ($)",
            min_value=0.0,
            max_value=10000000.0,
            value=200000.0,
            step=10000.0,
            help="Fixed monthly operating costs (salaries, rent, etc.)"
        )

    # Projection mode selection
    st.markdown("---")
    projection_mode = st.radio(
        "Projection Mode",
        options=["Simple Growth", "Custom Monthly Targets"],
        horizontal=True,
        help="Simple: uniform growth rate. Custom: specify exact originations per month"
    )

    # Growth/Origination inputs based on mode
    if projection_mode == "Simple Growth":
        monthly_growth = st.slider(
            "Monthly Growth Rate (%)",
            min_value=0.0,
            max_value=50.0,
            value=10.0,
            step=1.0,
            help="Target monthly growth in portfolio principal (compounds each month)"
        ) / 100.0
        custom_originations = None
    else:
        # Custom monthly targets mode
        monthly_growth = None

        # Quick fill buttons
        st.markdown("**Quick Fill Presets:**")
        preset_col1, preset_col2, preset_col3, preset_col4 = st.columns(4)

        # Initialize session state for custom originations if not exists
        if 'custom_originations_df' not in st.session_state:
            # Default: even distribution
            avg_origination = starting_portfolio * 0.10  # 10% of starting portfolio per month
            st.session_state.custom_originations_df = pd.DataFrame({
                'Month': list(range(1, projection_months + 1)),
                'New Originations ($)': [avg_origination] * projection_months,
                'Notes': [''] * projection_months
            })

        # Update number of rows if projection_months changed
        if len(st.session_state.custom_originations_df) != projection_months:
            current_val = st.session_state.custom_originations_df['New Originations ($)'].iloc[0] if len(st.session_state.custom_originations_df) > 0 else starting_portfolio * 0.10
            st.session_state.custom_originations_df = pd.DataFrame({
                'Month': list(range(1, projection_months + 1)),
                'New Originations ($)': [current_val] * projection_months,
                'Notes': [''] * projection_months
            })

        with preset_col1:
            if st.button("Constant", help="Same amount each month"):
                avg_val = st.session_state.custom_originations_df['New Originations ($)'].mean()
                st.session_state.custom_originations_df['New Originations ($)'] = [avg_val] * projection_months

        with preset_col2:
            if st.button("Linear Ramp", help="Gradual linear increase"):
                start_val = starting_portfolio * 0.05
                end_val = starting_portfolio * 0.20
                st.session_state.custom_originations_df['New Originations ($)'] = [
                    start_val + (end_val - start_val) * (i / max(1, projection_months - 1))
                    for i in range(projection_months)
                ]

        with preset_col3:
            if st.button("Front-Loaded", help="High early, tapering off"):
                st.session_state.custom_originations_df['New Originations ($)'] = [
                    starting_portfolio * 0.20 * (1 - 0.5 * i / max(1, projection_months))
                    for i in range(projection_months)
                ]

        with preset_col4:
            if st.button("Back-Loaded", help="Low early, ramping up"):
                st.session_state.custom_originations_df['New Originations ($)'] = [
                    starting_portfolio * 0.05 * (1 + 3 * i / max(1, projection_months))
                    for i in range(projection_months)
                ]

        # Editable table
        st.markdown("**Monthly Origination Targets:**")
        edited_df = st.data_editor(
            st.session_state.custom_originations_df,
            hide_index=True,
            use_container_width=True,
            num_rows="fixed",
            column_config={
                "Month": st.column_config.NumberColumn("Month", disabled=True),
                "New Originations ($)": st.column_config.NumberColumn(
                    "New Originations ($)",
                    min_value=0,
                    format="$%.0f"
                ),
                "Notes": st.column_config.TextColumn("Notes", width="medium")
            }
        )

        # Update session state
        st.session_state.custom_originations_df = edited_df

        # Extract originations list for calculation
        custom_originations = edited_df['New Originations ($)'].tolist()

    # Calculate cash flow projection
    def calculate_cash_flow_projection(starting_portfolio, months, growth_rate, loan_params, overhead, custom_originations=None):
        """
        Calculate month-by-month cash flow projections.

        Args:
            starting_portfolio: Initial portfolio size ($)
            months: Number of months to project
            growth_rate: Monthly growth rate (as decimal) - used if custom_originations is None
            loan_params: Dictionary of current loan parameters
            overhead: Monthly overhead cost ($)
            custom_originations: List of monthly origination amounts (overrides growth_rate if provided)

        Returns:
            DataFrame with monthly cash flow breakdown
        """
        # Extract loan parameters
        principal = loan_params['principal']
        installments = loan_params['installments']
        frequency_days = loan_params['frequency_days']
        apr = loan_params['apr']
        merchant_commission = loan_params['merchant_commission']
        fixed_fee = loan_params['fixed_fee']
        late_fee_amount = loan_params['late_fee_amount']
        late_installment_pct = loan_params['late_installment_pct']
        early_repayment_rate = loan_params['early_repayment_rate']
        avg_repayment_installment = loan_params['avg_repayment_installment']
        late_repayment_rate = loan_params['late_repayment_rate']
        avg_days_late_per_installment = loan_params['avg_days_late_per_installment']
        late_interest_apr = loan_params.get('late_interest_apr', apr)  # Default to normal apr if not specified

        # Convert installment frequency to months
        payments_per_month = 30 / frequency_days
        loan_duration_months = installments / payments_per_month

        # Calculate blended loan duration accounting for early/late repayments
        ontime_rate = 1.0 - early_repayment_rate - late_repayment_rate

        # Early repayers
        if early_repayment_rate > 0 and avg_repayment_installment:
            early_duration_months = avg_repayment_installment / payments_per_month
        else:
            early_duration_months = loan_duration_months

        # Late repayers
        if late_repayment_rate > 0 and avg_days_late_per_installment > 0:
            total_days_late = installments * avg_days_late_per_installment
            late_duration_months = loan_duration_months + (total_days_late / 30)
        else:
            late_duration_months = loan_duration_months

        # Blended loan duration
        blended_duration_months = (
            early_repayment_rate * early_duration_months +
            late_repayment_rate * late_duration_months +
            ontime_rate * loan_duration_months
        )

        # Calculate per-loan cash flows based on blended portfolio
        # Early repayers: reduced interest (shorter duration)
        early_interest = principal * apr * (early_duration_months / 12) * 0.5 if early_repayment_rate > 0 else 0
        # Late repayers: penalty interest rate with extended duration
        late_interest = principal * late_interest_apr * (late_duration_months / 12) * 0.5 if late_repayment_rate > 0 else 0
        # On-time: normal interest
        ontime_interest = principal * apr * (loan_duration_months / 12) * 0.5

        # Blended interest
        total_interest = (
            early_repayment_rate * early_interest +
            late_repayment_rate * late_interest +
            ontime_rate * ontime_interest
        )

        # Fixed fees (collected regardless of early repayment)
        total_fixed_fees = principal * fixed_fee

        # Late fees (only from late repayers)
        total_late_fees = late_repayment_rate * installments * late_installment_pct * late_fee_amount

        merchant_comm_per_loan = principal * merchant_commission

        # Monthly payment per loan (principal + interest)
        monthly_payment_per_loan = (principal + total_interest) / blended_duration_months
        monthly_fees_per_loan = (total_fixed_fees + total_late_fees) / blended_duration_months

        # Initialize tracking
        results = []
        portfolio_balance = starting_portfolio
        loan_cohorts = []  # List of (origination_month, principal, months_remaining)

        for month in range(months + 1):
            # Calculate new loans to originate this month
            if month == 0:
                # Initial portfolio - assume exists at start
                new_loans_principal = starting_portfolio
                loan_cohorts.append({
                    'month': 0,
                    'principal': starting_portfolio,
                    'months_remaining': blended_duration_months
                })
            else:
                # Calculate new loans to originate
                if custom_originations is not None:
                    # Custom mode: use specified origination amount for this month
                    new_loans_principal = custom_originations[month - 1]
                else:
                    # Simple growth mode: calculate based on compound growth
                    target_portfolio = starting_portfolio * ((1 + growth_rate) ** month)
                    # New loans needed to achieve growth
                    new_loans_principal = target_portfolio - portfolio_balance

                if new_loans_principal > 0:
                    loan_cohorts.append({
                        'month': month,
                        'principal': new_loans_principal,
                        'months_remaining': blended_duration_months
                    })

            # Calculate cash flows for this month
            principal_repayments = 0
            interest_collected = 0
            fees_collected = 0

            # Process each active cohort (skip month 0 - just the starting snapshot)
            if month > 0:
                for cohort in loan_cohorts:
                    if cohort['months_remaining'] > 0:
                        # Calculate proportion of this cohort's payments
                        cohort_loans = cohort['principal'] / principal

                        # Monthly repayments from this cohort
                        principal_repayments += (principal / blended_duration_months) * cohort_loans
                        interest_collected += (total_interest / blended_duration_months) * cohort_loans
                        fees_collected += monthly_fees_per_loan * cohort_loans

                        # Decrement remaining months
                        cohort['months_remaining'] -= 1

            # Merchant commission on new loans
            merchant_comm_collected = (new_loans_principal / principal) * merchant_comm_per_loan if month > 0 else 0

            # Cash outflows
            merchant_payments = new_loans_principal if month > 0 else 0
            overhead_cost = overhead if month > 0 else 0  # No overhead in month 0 (starting point)

            # Total cash flows
            total_inflows = merchant_comm_collected + principal_repayments + interest_collected + fees_collected
            total_outflows = merchant_payments + overhead_cost
            net_funding = total_outflows - total_inflows

            # Update portfolio balance
            portfolio_balance = sum(c['principal'] * (c['months_remaining'] / blended_duration_months) for c in loan_cohorts if c['months_remaining'] > 0)

            results.append({
                'month': month,
                'portfolio_balance': portfolio_balance,
                'merchant_commission': merchant_comm_collected,
                'principal_repayments': principal_repayments,
                'interest_collected': interest_collected,
                'fees_collected': fees_collected,
                'total_inflows': total_inflows,
                'merchant_payments': merchant_payments,
                'overhead': overhead_cost,
                'total_outflows': total_outflows,
                'net_funding_need': net_funding
            })

        return pd.DataFrame(results)

    # Prepare loan parameters
    loan_params = {
        'principal': avg_principal,
        'installments': avg_installments,
        'frequency_days': installment_frequency_days,
        'apr': interest_apr,
        'merchant_commission': merchant_commission,
        'fixed_fee': fixed_fee_pct,
        'late_fee_amount': late_fee_amount,
        'late_installment_pct': late_installment_pct,
        'early_repayment_rate': early_repayment_rate,
        'avg_repayment_installment': avg_repayment_installment,
        'late_repayment_rate': late_repayment_rate,
        'avg_days_late_per_installment': avg_days_late_per_installment,
        'late_interest_apr': late_interest_apr
    }

    # Calculate projection
    cf_projection = calculate_cash_flow_projection(
        starting_portfolio,
        projection_months,
        monthly_growth,
        loan_params,
        monthly_overhead,
        custom_originations
    )

    # Calculate summary metrics
    final_portfolio = cf_projection.iloc[-1]['portfolio_balance']
    starting_portfolio_balance = cf_projection.iloc[0]['portfolio_balance']
    total_growth = final_portfolio - starting_portfolio_balance
    total_growth_pct = (total_growth / starting_portfolio_balance * 100) if starting_portfolio_balance > 0 else 0

    peak_funding_need = cf_projection[cf_projection['net_funding_need'] > 0]['net_funding_need'].max() if (cf_projection['net_funding_need'] > 0).any() else 0
    total_funding_required = cf_projection[cf_projection['net_funding_need'] > 0]['net_funding_need'].sum() if (cf_projection['net_funding_need'] > 0).any() else 0
    cumulative_net_funding = cf_projection['net_funding_need'].sum()

    # Total revenue = interest + fees + commissions (excluding principal repayments)
    total_revenue_collected = (cf_projection['interest_collected'].sum() +
                              cf_projection['fees_collected'].sum() +
                              cf_projection['merchant_commission'].sum())
    total_overhead_paid = cf_projection['overhead'].sum()

    # Display summary metrics
    st.markdown("### Summary Metrics")

    row1_col1, row1_col2, row1_col3 = st.columns(3)
    with row1_col1:
        st.metric(
            "Final Portfolio Balance",
            f"${final_portfolio:,.0f}",
            delta=f"${total_growth:,.0f} ({total_growth_pct:+.1f}%)",
            help="Ending portfolio balance with total growth over projection period"
        )
    with row1_col2:
        st.metric(
            "Peak Monthly Funding Need",
            f"${peak_funding_need:,.0f}",
            help="Maximum funding required in any single month"
        )
    with row1_col3:
        st.metric(
            "Total Funding Required",
            f"${total_funding_required:,.0f}",
            help="Sum of all positive net funding needs (capital required for growth)"
        )

    row2_col1, row2_col2, row2_col3 = st.columns(3)
    with row2_col1:
        st.metric(
            "Cumulative Net Funding",
            f"${cumulative_net_funding:,.0f}",
            help="Total net funding over entire period (positive = capital deployed)"
        )
    with row2_col2:
        st.metric(
            "Total Revenue Collected",
            f"${total_revenue_collected:,.0f}",
            help="Total interest, fees, and commissions collected (excludes principal)"
        )
    with row2_col3:
        st.metric(
            "Total Overhead Paid",
            f"${total_overhead_paid:,.0f}",
            help="Total operating costs over projection period"
        )

    st.markdown("---")

    # Create both charts side-by-side
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        # Portfolio balance bar chart with data labels
        fig_portfolio = go.Figure()

        fig_portfolio.add_trace(go.Bar(
            x=cf_projection['month'],
            y=cf_projection['portfolio_balance'],
            marker=dict(color='#3498db'),
            text=[f'${val:,.0f}' for val in cf_projection['portfolio_balance']],
            textposition='outside',
            customdata=cf_projection[[
                'merchant_commission', 'principal_repayments', 'interest_collected',
                'fees_collected', 'total_inflows', 'merchant_payments', 'overhead',
                'total_outflows', 'net_funding_need'
            ]],
            hovertemplate='<b>Month %{x}</b><br>' +
                          'Portfolio Balance: $%{y:,.0f}<br>' +
                          '<br><b>Inflows:</b><br>' +
                          '  • Merchant Commission: $%{customdata[0]:,.0f}<br>' +
                          '  • Principal Repayments: $%{customdata[1]:,.0f}<br>' +
                          '  • Interest: $%{customdata[2]:,.0f}<br>' +
                          '  • Fees: $%{customdata[3]:,.0f}<br>' +
                          '  <b>Total Inflows: $%{customdata[4]:,.0f}</b><br>' +
                          '<br><b>Outflows:</b><br>' +
                          '  • Merchant Payments: $%{customdata[5]:,.0f}<br>' +
                          '  • Company Overhead: $%{customdata[6]:,.0f}<br>' +
                          '  <b>Total Outflows: $%{customdata[7]:,.0f}</b><br>' +
                          '<br><b>Net Funding Need: $%{customdata[8]:,.0f}</b>' +
                          '<extra></extra>',
            name='Portfolio Balance'
        ))

        fig_portfolio.update_layout(
            title="Outstanding Portfolio Balance",
            xaxis_title="Month",
            yaxis_title="Portfolio Balance ($)",
            height=500,
            hovermode='closest'
        )

        st.plotly_chart(fig_portfolio, config={'displayModeBar': False}, use_container_width=True)

    with chart_col2:
        # Create stacked bar chart for cash flows
        fig_cashflow = go.Figure()

        # Prepare custom hover data for all components
        customdata = cf_projection[[
            'merchant_commission', 'principal_repayments', 'interest_collected',
            'fees_collected', 'total_inflows', 'merchant_payments', 'overhead',
            'total_outflows', 'net_funding_need'
        ]]

        # Inflows - stacked positive bars (different shades of green)
        # Only first trace shows detailed tooltip to avoid repetition
        fig_cashflow.add_trace(go.Bar(
            name='Merchant Commission',
            x=cf_projection['month'],
            y=cf_projection['merchant_commission'],
            marker_color='#27ae60',
            customdata=customdata,
            hovertemplate='<b>Month %{x}</b><br><br>' +
                          '<b>Inflows:</b><br>' +
                          '  • Merchant Commission: $%{customdata[0]:,.0f}<br>' +
                          '  • Principal Repayments: $%{customdata[1]:,.0f}<br>' +
                          '  • Interest: $%{customdata[2]:,.0f}<br>' +
                          '  • Fees: $%{customdata[3]:,.0f}<br>' +
                          '  <b>Total Inflows: $%{customdata[4]:,.0f}</b><br><br>' +
                          '<b>Outflows:</b><br>' +
                          '  • Merchant Payments: $%{customdata[5]:,.0f}<br>' +
                          '  • Overhead: $%{customdata[6]:,.0f}<br>' +
                          '  <b>Total Outflows: $%{customdata[7]:,.0f}</b><br><br>' +
                          '<b>Net Cash Flow: $%{customdata[8]:,.0f}</b>' +
                          '<extra></extra>',
            showlegend=False
        ))

        fig_cashflow.add_trace(go.Bar(
            name='Principal Repayments',
            x=cf_projection['month'],
            y=cf_projection['principal_repayments'],
            marker_color='#2ecc71',
            hoverinfo='skip',
            showlegend=False
        ))

        fig_cashflow.add_trace(go.Bar(
            name='Interest Collected',
            x=cf_projection['month'],
            y=cf_projection['interest_collected'],
            marker_color='#58d68d',
            hoverinfo='skip',
            showlegend=False
        ))

        fig_cashflow.add_trace(go.Bar(
            name='Fees Collected',
            x=cf_projection['month'],
            y=cf_projection['fees_collected'],
            marker_color='#82e0aa',
            hoverinfo='skip',
            showlegend=False
        ))

        # Outflows - stacked negative bars (different shades of red)
        fig_cashflow.add_trace(go.Bar(
            name='Merchant Payments',
            x=cf_projection['month'],
            y=-cf_projection['merchant_payments'],
            marker_color='#c0392b',
            hoverinfo='skip',
            showlegend=False
        ))

        fig_cashflow.add_trace(go.Bar(
            name='Company Overhead',
            x=cf_projection['month'],
            y=-cf_projection['overhead'],
            marker_color='#e74c3c',
            hoverinfo='skip',
            showlegend=False
        ))

        fig_cashflow.update_layout(
            title="Monthly Cash Flows",
            xaxis_title="Month",
            yaxis_title="Cash Flows ($)",
            barmode='relative',
            height=500,
            hovermode='x unified',
            showlegend=False
        )

        st.plotly_chart(fig_cashflow, config={'displayModeBar': False}, use_container_width=True)

    # Create detailed table
    st.markdown("### Monthly Cash Flow Details")

    table_df = cf_projection[['month', 'merchant_commission', 'principal_repayments',
                               'interest_collected', 'fees_collected', 'total_inflows',
                               'merchant_payments', 'overhead', 'total_outflows',
                               'net_funding_need', 'portfolio_balance']].copy()

    # Rename columns for display
    table_df.columns = ['Month', 'Merchant Commission', 'Principal Repayments',
                        'Interest Collected', 'Fees Collected', 'Total Inflows',
                        'Merchant Payments', 'Company Overhead', 'Total Outflows',
                        'Net Funding Need', 'Portfolio Balance']

    # Format currency columns
    currency_cols = ['Merchant Commission', 'Principal Repayments', 'Interest Collected',
                     'Fees Collected', 'Total Inflows', 'Merchant Payments', 'Company Overhead',
                     'Total Outflows', 'Net Funding Need', 'Portfolio Balance']

    for col in currency_cols:
        table_df[col] = table_df[col].apply(lambda x: f'${x:,.0f}')

    # Display table
    st.dataframe(
        table_df,
        hide_index=True,
        use_container_width=True,
        height=400
    )

# Footer
st.caption("BNPL Pricing Strategy Simulator v1.4 | Built with Streamlit")
