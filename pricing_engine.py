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
    default_rate: float,
    recovery_rate: float,
    fixed_fee_pct: float = 0.0,
    funding_cost_apr: float = 0.0,
    installment_frequency_days: int = 30,
    late_fee_amount: float = 0.0,
    late_installment_pct: float = 0.0
) -> Dict[str, float]:
    """
    Calculate the effective annualized yield for a BNPL loan.

    Formula:
    Effective Yield = (Net Profit / Principal) / Capital Deployment Period (annualized)

    Capital Deployment Period = Loan Duration - Settlement Delay
    Settlement delay reduces deployment period, increasing yield.

    Args:
        principal: Loan principal amount
        apr: Annual percentage rate (as decimal, e.g., 0.30 for 30%)
        installments: Number of installments
        merchant_commission_pct: Merchant fee as % of principal (as decimal)
        settlement_delay_days: Days until merchant is paid (delays capital deployment)
        default_rate: Expected default rate (as decimal)
        recovery_rate: % recovered from defaults (as decimal)
        fixed_fee_pct: Fixed fee as % of principal (as decimal)
        funding_cost_apr: Annual funding cost rate (as decimal)
        installment_frequency_days: Days between installments (30 for monthly, 14 for biweekly)
        late_fee_amount: Late fee amount in $ per late installment
        late_installment_pct: % of installments paid late (as decimal, e.g., 0.20 for 20%)

    Returns:
        Dictionary with yield breakdown
    """
    # Loan duration in days (time from purchase to last customer payment)
    loan_duration_days = installments * installment_frequency_days
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

    # Interest income (simple interest approximation)
    # For installment loans, effective interest is roughly half of stated APR due to declining balance
    effective_interest_rate = apr * loan_duration_years * 0.5
    interest_income = principal * effective_interest_rate

    # Fixed fee income
    fixed_fee_income = principal * fixed_fee_pct

    # Merchant commission income
    merchant_commission = principal * merchant_commission_pct

    # Late fee income
    # Only non-defaulted loans pay late fees
    # Late fee revenue = installments × (1 - default_rate) × % late × late fee amount
    late_fee_income = installments * (1 - default_rate) * late_installment_pct * late_fee_amount

    # Total revenue
    total_revenue = interest_income + fixed_fee_income + merchant_commission + late_fee_income

    # Funding cost from capital deployment
    # This is the cost of capital during the period when capital is deployed to the merchant
    # (from when we pay merchant until we receive final customer payment)
    funding_cost = principal * funding_cost_apr * capital_deployment_years

    # Default loss (principal lost after recovery)
    expected_loss = principal * default_rate * (1 - recovery_rate)

    # Net profit
    net_profit = total_revenue - funding_cost - expected_loss

    # Effective yield (annualized)
    # CRITICAL: Use capital deployment period (loan duration - settlement delay)
    # Longer settlement delay = shorter deployment = HIGHER yield
    effective_yield = (net_profit / principal) / capital_deployment_years

    # Settlement delay impact (for transparency)
    # This shows the BENEFIT of settlement delay (positive impact = higher yield)
    yield_without_delay = (net_profit / principal) / loan_duration_years if loan_duration_years > 0 else 0
    settlement_delay_benefit = effective_yield - yield_without_delay

    return {
        'effective_yield': effective_yield,
        'interest_income': interest_income,
        'fixed_fee_income': fixed_fee_income,
        'merchant_commission': merchant_commission,
        'late_fee_income': late_fee_income,
        'total_revenue': total_revenue,
        'funding_cost': funding_cost,
        'expected_loss': expected_loss,
        'net_profit': net_profit,
        'profit_margin': net_profit / principal if principal > 0 else 0,
        'loan_duration_days': loan_duration_days,
        'capital_deployment_days': capital_deployment_days,
        'settlement_delay_benefit': settlement_delay_benefit,
        'settlement_delay_days': settlement_delay_days,
        'is_float_scenario': is_float_scenario
    }


def calculate_required_apr(
    target_yield: float,
    principal: float,
    installments: int,
    merchant_commission_pct: float,
    settlement_delay_days: int,
    default_rate: float,
    recovery_rate: float,
    fixed_fee_pct: float = 0.0,
    funding_cost_apr: float = 0.0,
    installment_frequency_days: int = 30,
    late_fee_amount: float = 0.0,
    late_installment_pct: float = 0.0,
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
            default_rate=default_rate,
            recovery_rate=recovery_rate,
            fixed_fee_pct=fixed_fee_pct,
            funding_cost_apr=funding_cost_apr,
            installment_frequency_days=installment_frequency_days,
            late_fee_amount=late_fee_amount,
            late_installment_pct=late_installment_pct
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
    default_rate: float,
    recovery_rate: float,
    fixed_fee_pct: float = 0.0,
    funding_cost_apr: float = 0.0,
    installment_frequency_days: int = 30,
    late_fee_amount: float = 0.0,
    late_installment_pct: float = 0.0,
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
            default_rate=default_rate,
            recovery_rate=recovery_rate,
            fixed_fee_pct=fixed_fee_pct,
            funding_cost_apr=funding_cost_apr,
            installment_frequency_days=installment_frequency_days,
            late_fee_amount=late_fee_amount,
            late_installment_pct=late_installment_pct
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
