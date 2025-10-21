"""
Tafi BNPL Pricing Engine - Core Calculation Functions
"""

import numpy as np
from typing import Dict, Tuple


def calculate_effective_yield(
    principal: float,
    apr: float,
    installments: int,
    merchant_commission_pct: float,
    settlement_delay_days: int,
    fraud_rate: float = 0.0,
    default_rate: float = 0.0,
    recovery_rate: float = 0.0,
    fraud_recovery_rate: float = 0.0,
    fixed_fee_pct: float = 0.0,
    funding_cost_apr: float = 0.0,
    installment_frequency_days: int = 30,
    late_fee_amount: float = 0.0,
    late_installment_pct: float = 0.0,
    first_installment_upfront: bool = False,
    early_repayment_rate: float = 0.0,
    avg_repayment_installment: int = None,
    late_repayment_rate: float = 0.0,
    avg_days_late_per_installment: int = 0
) -> Dict[str, float]:
    """
    Calculate the effective annualized yield for a BNPL loan with five-way portfolio segmentation.

    Portfolio Segments:
    1. Early Repayers (early_repayment_rate): Zero loss, reduced duration, less interest
    2. Late Repayers (late_repayment_rate): Zero loss, extended duration, more interest + all late fees
    3. On-Time Payers (remainder): Zero loss, normal duration, sporadic late fees
    4. Defaults (default_rate): Legitimate defaults, uses recovery_rate
    5. Fraud (fraud_rate): Immediate loss, uses fraud_recovery_rate

    Formula:
    Effective Yield = (Net Profit / Principal) / Capital Deployment Period (annualized)

    Args:
        principal: Loan principal amount
        apr: Annual percentage rate (as decimal, e.g., 0.30 for 30%)
        installments: Number of installments
        merchant_commission_pct: Merchant fee as % of principal (as decimal)
        settlement_delay_days: Days until merchant is paid (delays capital deployment)
        fraud_rate: Expected fraud rate (as decimal) - customers who never pay
        default_rate: Expected legitimate default rate (as decimal) - financial hardship
        recovery_rate: % recovered from legitimate defaults (as decimal)
        fraud_recovery_rate: % recovered from fraud cases (as decimal)
        fixed_fee_pct: Fixed fee as % of principal (as decimal)
        funding_cost_apr: Annual funding cost rate (as decimal)
        installment_frequency_days: Days between installments (30 for monthly, 14 for biweekly)
        late_fee_amount: Late fee amount in $ per late installment
        late_installment_pct: % of installments paid late for on-time/default segments (as decimal)
        first_installment_upfront: If True, customer pays first installment at purchase (Day 0)
        early_repayment_rate: % of loans repaid early (as decimal, e.g., 0.30 for 30%)
        avg_repayment_installment: Average installment number at which early repayment occurs
        late_repayment_rate: % of loans that pay late (as decimal, e.g., 0.20 for 20%)
        avg_days_late_per_installment: Average days late per installment for late payers

    Returns:
        Dictionary with yield breakdown (blended across all portfolio segments)
    """
    # Validation: Can't have first installment upfront with only 1 installment
    if first_installment_upfront and installments <= 1:
        # Treat as full upfront payment - no loan needed
        first_installment_upfront = False

    # Validation: Portfolio segments can't exceed 100%
    total_portfolio = early_repayment_rate + late_repayment_rate + default_rate + fraud_rate
    if total_portfolio > 1.0:
        raise ValueError(f"Portfolio segments exceed 100%: {total_portfolio * 100:.1f}% (early: {early_repayment_rate*100:.1f}%, late: {late_repayment_rate*100:.1f}%, default: {default_rate*100:.1f}%, fraud: {fraud_rate*100:.1f}%)")

    # Calculate installment amount
    installment_amount = principal / installments

    # Adjust for first installment upfront
    if first_installment_upfront:
        # Customer pays first installment immediately at purchase
        # This reduces the capital we need to deploy to the merchant
        capital_to_deploy = principal - installment_amount
        # Loan duration is shorter (one fewer period)
        loan_duration_days = (installments - 1) * installment_frequency_days
        # Number of installments that can incur late fees (excluding upfront one)
        late_fee_installments = installments - 1
    else:
        # Standard case: we deploy full principal
        capital_to_deploy = principal
        loan_duration_days = installments * installment_frequency_days
        late_fee_installments = installments

    loan_duration_years = loan_duration_days / 365

    # CRITICAL: Settlement delay REDUCES deployment period
    # Timeline:
    #   Day 0: Purchase happens
    #   Day 0 + settlement_delay: Tafi pays merchant (capital deployed)
    #   Day 0 + loan_duration: Last customer payment received
    # Capital deployment = loan_duration - settlement_delay

    # EDGE CASE: If settlement delay >= loan duration
    # Customer pays ALL installments BEFORE Tafi pays merchant
    # This is a "float" scenario - Tafi holds customer money before paying merchant
    # Capital deployed = 0 (or negative), resulting in infinite/undefined yield

    if settlement_delay_days >= loan_duration_days:
        # Float scenario: No capital deployed (customer pays before merchant)
        # Use the "float period" for yield calculation
        # Float period = time Tafi holds customer money after collecting it all
        float_period_days = settlement_delay_days - loan_duration_days
        # For yield calculation, use loan_duration as proxy
        # (representing the average time capital would have been deployed if normal)
        capital_deployment_days = loan_duration_days * 0.25  # Use 25% of loan duration as proxy
        is_float_scenario = True
    else:
        # Normal BNPL scenario
        capital_deployment_days = loan_duration_days - settlement_delay_days
        is_float_scenario = False

    capital_deployment_years = capital_deployment_days / 365

    # Five-way portfolio segmentation
    has_early_repayment = early_repayment_rate > 0 and avg_repayment_installment and avg_repayment_installment < installments
    has_late_repayment = late_repayment_rate > 0 and avg_days_late_per_installment > 0
    has_portfolio_segmentation = has_early_repayment or has_late_repayment or default_rate > 0 or fraud_rate > 0

    if has_portfolio_segmentation:
        # Calculate percentages for each segment
        early_pct = early_repayment_rate
        late_pct = late_repayment_rate
        default_pct = default_rate
        fraud_pct = fraud_rate
        ontime_pct = 1.0 - early_pct - late_pct - default_pct - fraud_pct

        # =================================================================
        # SEGMENT 1: EARLY REPAYMENT (zero loss, reduced duration)
        # =================================================================
        if has_early_repayment:
            early_loan_duration_days = avg_repayment_installment * installment_frequency_days
            early_loan_duration_years = early_loan_duration_days / 365

            early_interest_income = principal * apr * early_loan_duration_years * 0.5
            early_fixed_fee = principal * fixed_fee_pct
            early_merchant_comm = principal * merchant_commission_pct
            early_late_fees = 0.0  # Early repayers don't pay late
            early_expected_loss = 0.0

            if settlement_delay_days >= early_loan_duration_days:
                early_cap_deploy_days = early_loan_duration_days * 0.25
            else:
                early_cap_deploy_days = early_loan_duration_days - settlement_delay_days
            early_cap_deploy_years = early_cap_deploy_days / 365
            early_funding_cost = capital_to_deploy * funding_cost_apr * early_cap_deploy_years
        else:
            early_interest_income = early_fixed_fee = early_merchant_comm = early_late_fees = 0.0
            early_expected_loss = early_funding_cost = 0.0
            early_cap_deploy_days = 0.0

        # =================================================================
        # SEGMENT 2: LATE REPAYMENT (zero loss, extended duration)
        # =================================================================
        if has_late_repayment:
            total_late_delay = installments * avg_days_late_per_installment
            late_loan_duration_days = loan_duration_days + total_late_delay
            late_loan_duration_years = late_loan_duration_days / 365

            late_interest_income = principal * apr * late_loan_duration_years * 0.5
            late_fixed_fee = principal * fixed_fee_pct
            late_merchant_comm = principal * merchant_commission_pct
            late_late_fees = late_fee_installments * late_fee_amount  # ALL installments late
            late_expected_loss = 0.0  # Late payers don't default

            if settlement_delay_days >= late_loan_duration_days:
                late_cap_deploy_days = late_loan_duration_days * 0.25
            else:
                late_cap_deploy_days = late_loan_duration_days - settlement_delay_days
            late_cap_deploy_years = late_cap_deploy_days / 365
            late_funding_cost = capital_to_deploy * funding_cost_apr * late_cap_deploy_years
        else:
            late_interest_income = late_fixed_fee = late_merchant_comm = late_late_fees = 0.0
            late_expected_loss = late_funding_cost = 0.0
            late_cap_deploy_days = 0.0

        # =================================================================
        # SEGMENT 3: ON-TIME PAYERS (zero loss, normal duration, sporadic late fees)
        # =================================================================
        ontime_interest_income = principal * apr * loan_duration_years * 0.5
        ontime_fixed_fee = principal * fixed_fee_pct
        ontime_merchant_comm = principal * merchant_commission_pct
        ontime_late_fees = late_fee_installments * late_installment_pct * late_fee_amount
        ontime_expected_loss = 0.0  # On-time payers don't default
        ontime_funding_cost = capital_to_deploy * funding_cost_apr * capital_deployment_years
        ontime_cap_deploy_days = capital_deployment_days

        # =================================================================
        # SEGMENT 4: DEFAULTS (legitimate defaults with recovery)
        # =================================================================
        default_interest_income = principal * apr * loan_duration_years * 0.5
        default_fixed_fee = principal * fixed_fee_pct
        default_merchant_comm = principal * merchant_commission_pct
        default_late_fees = late_fee_installments * late_installment_pct * late_fee_amount
        default_expected_loss = capital_to_deploy * (1 - recovery_rate)
        default_funding_cost = capital_to_deploy * funding_cost_apr * capital_deployment_years
        default_cap_deploy_days = capital_deployment_days

        # =================================================================
        # SEGMENT 5: FRAUD (immediate loss, different recovery)
        # =================================================================
        if first_installment_upfront:
            # Fraud cases paid first installment, then disappeared
            fraud_interest_income = 0.0
            fraud_fixed_fee = 0.0
            fraud_merchant_comm = principal * merchant_commission_pct  # Still charged
            fraud_late_fees = 0.0
            fraud_expected_loss = (capital_to_deploy) * (1 - fraud_recovery_rate)
            fraud_funding_cost = capital_to_deploy * funding_cost_apr * capital_deployment_years
            fraud_cap_deploy_days = capital_deployment_days
        else:
            # Fraud cases never paid anything
            fraud_interest_income = 0.0
            fraud_fixed_fee = 0.0
            fraud_merchant_comm = principal * merchant_commission_pct  # Still charged
            fraud_late_fees = 0.0
            fraud_expected_loss = principal * (1 - fraud_recovery_rate)
            fraud_funding_cost = capital_to_deploy * funding_cost_apr * capital_deployment_years
            fraud_cap_deploy_days = capital_deployment_days

        # =================================================================
        # WEIGHTED AVERAGE BLENDING ACROSS ALL 5 SEGMENTS
        # =================================================================
        # Calculate base interest (what late payers would have paid on-time)
        late_base_interest = principal * apr * loan_duration_years * 0.5

        # Separate late interest income (extra from extended duration)
        late_interest_extra = (late_interest_income - late_base_interest) * late_pct if has_late_repayment else 0.0

        # Base interest income (all segments at their respective durations)
        base_interest_income = (early_interest_income * early_pct +
                               late_base_interest * late_pct +
                               ontime_interest_income * ontime_pct +
                               default_interest_income * default_pct +
                               fraud_interest_income * fraud_pct)

        # Total interest income
        interest_income = base_interest_income + late_interest_extra

        fixed_fee_income = (early_fixed_fee * early_pct +
                           late_fixed_fee * late_pct +
                           ontime_fixed_fee * ontime_pct +
                           default_fixed_fee * default_pct +
                           fraud_fixed_fee * fraud_pct)

        merchant_commission = (early_merchant_comm * early_pct +
                              late_merchant_comm * late_pct +
                              ontime_merchant_comm * ontime_pct +
                              default_merchant_comm * default_pct +
                              fraud_merchant_comm * fraud_pct)

        late_fee_income = (early_late_fees * early_pct +
                          late_late_fees * late_pct +
                          ontime_late_fees * ontime_pct +
                          default_late_fees * default_pct +
                          fraud_late_fees * fraud_pct)

        # Separate default and fraud losses
        default_loss = default_expected_loss * default_pct
        fraud_loss = fraud_expected_loss * fraud_pct

        expected_loss = (early_expected_loss * early_pct +
                        late_expected_loss * late_pct +
                        ontime_expected_loss * ontime_pct +
                        default_loss +
                        fraud_loss)

        funding_cost = (early_funding_cost * early_pct +
                       late_funding_cost * late_pct +
                       ontime_funding_cost * ontime_pct +
                       default_funding_cost * default_pct +
                       fraud_funding_cost * fraud_pct)

        capital_deployment_days = (early_cap_deploy_days * early_pct +
                                  late_cap_deploy_days * late_pct +
                                  ontime_cap_deploy_days * ontime_pct +
                                  default_cap_deploy_days * default_pct +
                                  fraud_cap_deploy_days * fraud_pct)
        capital_deployment_years = capital_deployment_days / 365

        total_revenue = interest_income + fixed_fee_income + merchant_commission + late_fee_income
        net_profit = total_revenue - funding_cost - expected_loss

        if capital_deployment_years > 0:
            effective_yield = (net_profit / principal) / capital_deployment_years
        else:
            effective_yield = 1000.0 if net_profit > 0 else -1000.0

        yield_without_delay = (net_profit / principal) / loan_duration_years if loan_duration_years > 0 else 0
        settlement_delay_benefit = effective_yield - yield_without_delay if capital_deployment_years > 0 else 0

    else:
        # No portfolio segmentation - simple calculation
        interest_income = principal * apr * loan_duration_years * 0.5
        fixed_fee_income = principal * fixed_fee_pct
        merchant_commission = principal * merchant_commission_pct
        late_fee_income = late_fee_installments * late_installment_pct * late_fee_amount
        funding_cost = capital_to_deploy * funding_cost_apr * capital_deployment_years
        expected_loss = 0.0  # No losses if no defaults/fraud

        # No breakdown for simple case
        late_interest_extra = 0.0
        default_loss = 0.0
        fraud_loss = 0.0

        total_revenue = interest_income + fixed_fee_income + merchant_commission + late_fee_income
        net_profit = total_revenue - funding_cost - expected_loss

        if capital_deployment_years > 0:
            effective_yield = (net_profit / principal) / capital_deployment_years
        else:
            effective_yield = 1000.0 if net_profit > 0 else -1000.0

        yield_without_delay = (net_profit / principal) / loan_duration_years if loan_duration_years > 0 else 0
        settlement_delay_benefit = effective_yield - yield_without_delay if capital_deployment_years > 0 else 0

    return {
        'effective_yield': effective_yield,
        'interest_income': interest_income - late_interest_extra,  # Base interest only (for display)
        'late_interest_income': late_interest_extra,
        'fixed_fee_income': fixed_fee_income,
        'merchant_commission': merchant_commission,
        'late_fee_income': late_fee_income,
        'total_revenue': total_revenue,
        'funding_cost': funding_cost,
        'expected_loss': expected_loss,
        'default_loss': default_loss,
        'fraud_loss': fraud_loss,
        'net_profit': net_profit,
        'profit_margin': net_profit / principal if principal > 0 else 0,
        'loan_duration_days': loan_duration_days,
        'capital_deployment_days': capital_deployment_days,
        'settlement_delay_benefit': settlement_delay_benefit,
        'settlement_delay_days': settlement_delay_days,
        'is_float_scenario': is_float_scenario,
        'first_installment_upfront': first_installment_upfront,
        'installment_amount': installment_amount,
        'capital_to_deploy': capital_to_deploy,
        'has_early_repayment': has_early_repayment,
        'early_repayment_rate': early_repayment_rate if has_early_repayment else 0.0,
        'avg_repayment_installment': avg_repayment_installment if has_early_repayment else None,
        'has_late_repayment': has_late_repayment,
        'late_repayment_rate': late_repayment_rate if has_late_repayment else 0.0,
        'avg_days_late_per_installment': avg_days_late_per_installment if has_late_repayment else 0,
        'has_portfolio_segmentation': has_portfolio_segmentation,
        'fraud_rate': fraud_rate,
        'default_rate': default_rate,
        'ontime_pct': ontime_pct if has_portfolio_segmentation else 1.0
    }


def calculate_required_apr(
    target_yield: float,
    principal: float,
    installments: int,
    merchant_commission_pct: float,
    settlement_delay_days: int,
    fraud_rate: float = 0.0,
    default_rate: float = 0.0,
    recovery_rate: float = 0.0,
    fraud_recovery_rate: float = 0.0,
    fixed_fee_pct: float = 0.0,
    funding_cost_apr: float = 0.0,
    installment_frequency_days: int = 30,
    late_fee_amount: float = 0.0,
    late_installment_pct: float = 0.0,
    first_installment_upfront: bool = False,
    early_repayment_rate: float = 0.0,
    avg_repayment_installment: int = None,
    late_repayment_rate: float = 0.0,
    avg_days_late_per_installment: int = 0,
    max_iterations: int = 100,
    tolerance: float = 0.0001
) -> float:
    """
    Calculate the required APR to achieve a target annualized yield.
    Uses binary search to find the APR that produces the target yield.

    Args:
        target_yield: Target annualized yield (as decimal)
        (other args same as calculate_effective_yield)
        max_iterations: Maximum iterations for binary search
        tolerance: Tolerance for convergence

    Returns:
        Required APR (as decimal)
    """
    # Binary search bounds
    apr_low = 0.0
    apr_high = 4.0  # 400% max

    for _ in range(max_iterations):
        apr_mid = (apr_low + apr_high) / 2

        result = calculate_effective_yield(
            principal=principal,
            apr=apr_mid,
            installments=installments,
            merchant_commission_pct=merchant_commission_pct,
            settlement_delay_days=settlement_delay_days,
            fraud_rate=fraud_rate,
            default_rate=default_rate,
            recovery_rate=recovery_rate,
            fraud_recovery_rate=fraud_recovery_rate,
            fixed_fee_pct=fixed_fee_pct,
            funding_cost_apr=funding_cost_apr,
            installment_frequency_days=installment_frequency_days,
            late_fee_amount=late_fee_amount,
            late_installment_pct=late_installment_pct,
            first_installment_upfront=first_installment_upfront,
            early_repayment_rate=early_repayment_rate,
            avg_repayment_installment=avg_repayment_installment,
            late_repayment_rate=late_repayment_rate,
            avg_days_late_per_installment=avg_days_late_per_installment
        )

        current_yield = result['effective_yield']

        if abs(current_yield - target_yield) < tolerance:
            return apr_mid
        elif current_yield < target_yield:
            apr_low = apr_mid
        else:
            apr_high = apr_mid

    # Return best approximation
    return apr_mid


def estimate_interest_free_cap(
    target_yield: float,
    principal: float,
    merchant_commission_pct: float,
    settlement_delay_days: int,
    fraud_rate: float = 0.0,
    default_rate: float = 0.0,
    recovery_rate: float = 0.0,
    fraud_recovery_rate: float = 0.0,
    fixed_fee_pct: float = 0.0,
    funding_cost_apr: float = 0.0,
    installment_frequency_days: int = 30,
    late_fee_amount: float = 0.0,
    late_installment_pct: float = 0.0,
    first_installment_upfront: bool = False,
    early_repayment_rate: float = 0.0,
    avg_repayment_installment: int = None,
    late_repayment_rate: float = 0.0,
    avg_days_late_per_installment: int = 0,
    max_installments: int = 12
) -> int:
    """
    Estimate the maximum number of installments for an interest-free plan
    that still achieves the target yield.

    For interest-free plans, revenue comes only from merchant commission and fixed fees.

    Args:
        target_yield: Target annualized yield (as decimal)
        (other args same as calculate_effective_yield)
        max_installments: Maximum installments to consider

    Returns:
        Maximum number of installments (0 if target cannot be met)
    """
    apr = 0.0  # Interest-free

    # Try from 1 installment up to max
    for installments in range(1, max_installments + 1):
        result = calculate_effective_yield(
            principal=principal,
            apr=apr,
            installments=installments,
            merchant_commission_pct=merchant_commission_pct,
            settlement_delay_days=settlement_delay_days,
            fraud_rate=fraud_rate,
            default_rate=default_rate,
            recovery_rate=recovery_rate,
            fraud_recovery_rate=fraud_recovery_rate,
            fixed_fee_pct=fixed_fee_pct,
            funding_cost_apr=funding_cost_apr,
            installment_frequency_days=installment_frequency_days,
            late_fee_amount=late_fee_amount,
            late_installment_pct=late_installment_pct,
            first_installment_upfront=first_installment_upfront,
            early_repayment_rate=early_repayment_rate,
            avg_repayment_installment=avg_repayment_installment,
            late_repayment_rate=late_repayment_rate,
            avg_days_late_per_installment=avg_days_late_per_installment
        )

        if result['effective_yield'] < target_yield:
            # Previous installment count was the max
            return max(1, installments - 1)

    # All installments meet target
    return max_installments


def generate_sensitivity_data(
    parameter_name: str,
    parameter_range: np.ndarray,
    base_params: Dict,
    metric: str = 'effective_yield'
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate sensitivity analysis data by varying one parameter.

    Args:
        parameter_name: Name of parameter to vary
        parameter_range: Array of values to test
        base_params: Dictionary of base parameters
        metric: Metric to calculate ('effective_yield' or 'required_apr')

    Returns:
        Tuple of (parameter values, metric values)
    """
    results = []

    for value in parameter_range:
        params = base_params.copy()
        params[parameter_name] = value

        if metric == 'effective_yield':
            result = calculate_effective_yield(**params)
            results.append(result['effective_yield'])
        elif metric == 'required_apr':
            apr = calculate_required_apr(**params)
            results.append(apr)

    return parameter_range, np.array(results)


def compare_interest_models(
    principal: float,
    installments: int,
    merchant_commission_pct: float,
    settlement_delay_days: int,
    default_rate: float,
    recovery_rate: float,
    fixed_fee_pct: float,
    interest_bearing_apr: float,
    funding_cost_apr: float = 0.0,
    installment_frequency_days: int = 30,
    late_fee_amount: float = 0.0,
    late_installment_pct: float = 0.0
) -> Dict:
    """
    Compare interest-bearing vs interest-free loan economics.

    Returns:
        Dictionary with comparison metrics for both models
    """
    # Interest-bearing model
    ib_result = calculate_effective_yield(
        principal=principal,
        apr=interest_bearing_apr,
        installments=installments,
        merchant_commission_pct=merchant_commission_pct,
        settlement_delay_days=settlement_delay_days,
        default_rate=default_rate,
        recovery_rate=recovery_rate,
        fixed_fee_pct=fixed_fee_pct,
        funding_cost_apr=funding_cost_apr,
        installment_frequency_days=installment_frequency_days,
        late_fee_amount=late_fee_amount,
        late_installment_pct=late_installment_pct
    )

    # Interest-free model
    if_result = calculate_effective_yield(
        principal=principal,
        apr=0.0,
        installments=installments,
        merchant_commission_pct=merchant_commission_pct,
        settlement_delay_days=settlement_delay_days,
        default_rate=default_rate,
        recovery_rate=recovery_rate,
        fixed_fee_pct=fixed_fee_pct,
        funding_cost_apr=funding_cost_apr,
        installment_frequency_days=installment_frequency_days,
        late_fee_amount=late_fee_amount,
        late_installment_pct=late_installment_pct
    )

    return {
        'interest_bearing': {
            'apr': interest_bearing_apr,
            'effective_yield': ib_result['effective_yield'],
            'total_revenue': ib_result['total_revenue'],
            'net_profit': ib_result['net_profit'],
            'profit_margin': ib_result['profit_margin']
        },
        'interest_free': {
            'apr': 0.0,
            'effective_yield': if_result['effective_yield'],
            'total_revenue': if_result['total_revenue'],
            'net_profit': if_result['net_profit'],
            'profit_margin': if_result['profit_margin']
        }
    }
