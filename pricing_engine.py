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
    late_installment_pct: float = 0.0,
    first_installment_upfront: bool = False,
    early_repayment_rate: float = 0.0,
    avg_repayment_installment: int = None
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
        first_installment_upfront: If True, customer pays first installment at purchase (Day 0)
        early_repayment_rate: % of loans repaid early (as decimal, e.g., 0.30 for 30%)
        avg_repayment_installment: Average installment number at which early repayment occurs

    Returns:
        Dictionary with yield breakdown (blended if early_repayment_rate > 0)
    """
    # Validation: Can't have first installment upfront with only 1 installment
    if first_installment_upfront and installments <= 1:
        # Treat as full upfront payment - no loan needed
        first_installment_upfront = False

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
    # Late fee revenue = late_fee_installments × (1 - default_rate) × % late × late fee amount
    late_fee_income = late_fee_installments * (1 - default_rate) * late_installment_pct * late_fee_amount

    # Total revenue
    total_revenue = interest_income + fixed_fee_income + merchant_commission + late_fee_income

    # Funding cost from capital deployment
    # This is the cost of capital during the period when capital is deployed to the merchant
    # (from when we pay merchant until we receive final customer payment)
    # If first installment is upfront, we deploy less capital (capital_to_deploy)
    funding_cost = capital_to_deploy * funding_cost_apr * capital_deployment_years

    # Default loss (capital at risk after recovery)
    # If first installment is upfront, less capital is at risk
    expected_loss = capital_to_deploy * default_rate * (1 - recovery_rate)

    # Net profit
    net_profit = total_revenue - funding_cost - expected_loss

    # Effective yield (annualized)
    # CRITICAL: Use capital deployment period (loan duration - settlement delay)
    # Longer settlement delay = shorter deployment = HIGHER yield
    if capital_deployment_years > 0:
        effective_yield = (net_profit / principal) / capital_deployment_years
    else:
        # Edge case: no capital deployment (e.g., 1 installment upfront or extreme float scenario)
        # Return a very high yield if profitable, very low if not
        effective_yield = 1000.0 if net_profit > 0 else -1000.0

    # Settlement delay impact (for transparency)
    # This shows the BENEFIT of settlement delay (positive impact = higher yield)
    yield_without_delay = (net_profit / principal) / loan_duration_years if loan_duration_years > 0 else 0
    settlement_delay_benefit = effective_yield - yield_without_delay if capital_deployment_years > 0 else 0

    # Early repayment blending logic
    has_early_repayment = early_repayment_rate > 0 and avg_repayment_installment and avg_repayment_installment < installments

    if has_early_repayment:
        # Store regular portfolio results
        regular_pct = 1 - early_repayment_rate
        regular_results = {
            'interest_income': interest_income,
            'late_fee_income': late_fee_income,
            'total_revenue': total_revenue,
            'funding_cost': funding_cost,
            'expected_loss': expected_loss,
            'net_profit': net_profit,
            'effective_yield': effective_yield,
            'capital_deployment_days': capital_deployment_days
        }

        # Calculate early repayment portfolio (these customers repay early and don't default)
        early_pct = early_repayment_rate
        early_loan_duration_days = avg_repayment_installment * installment_frequency_days
        early_loan_duration_years = early_loan_duration_days / 365

        # Early repayment interest (reduced due to shorter term)
        early_interest_rate = apr * early_loan_duration_years * 0.5
        early_interest_income = principal * early_interest_rate

        # Early repayment late fees (fewer installments)
        early_late_fee_income = avg_repayment_installment * late_installment_pct * late_fee_amount

        # Fixed fee and merchant commission are PROTECTED (still earned in full)
        early_fixed_fee_income = principal * fixed_fee_pct
        early_merchant_commission = principal * merchant_commission_pct

        # Early repayers don't default (higher quality customers)
        early_expected_loss = 0.0

        # Capital deployment for early repayment
        if settlement_delay_days >= early_loan_duration_days:
            early_capital_deployment_days = early_loan_duration_days * 0.25
        else:
            early_capital_deployment_days = early_loan_duration_days - settlement_delay_days
        early_capital_deployment_years = early_capital_deployment_days / 365

        # Funding cost for early repayment
        early_funding_cost = capital_to_deploy * funding_cost_apr * early_capital_deployment_years

        # Total revenue and profit for early repayment
        early_total_revenue = early_interest_income + early_fixed_fee_income + early_merchant_commission + early_late_fee_income
        early_net_profit = early_total_revenue - early_funding_cost - early_expected_loss

        # Effective yield for early repayment
        if early_capital_deployment_years > 0:
            early_effective_yield = (early_net_profit / principal) / early_capital_deployment_years
        else:
            early_effective_yield = 1000.0 if early_net_profit > 0 else -1000.0

        # Blend the two portfolios (weighted average)
        interest_income = (regular_results['interest_income'] * regular_pct) + (early_interest_income * early_pct)
        late_fee_income = (regular_results['late_fee_income'] * regular_pct) + (early_late_fee_income * early_pct)
        total_revenue = (regular_results['total_revenue'] * regular_pct) + (early_total_revenue * early_pct)
        funding_cost = (regular_results['funding_cost'] * regular_pct) + (early_funding_cost * early_pct)
        expected_loss = (regular_results['expected_loss'] * regular_pct) + (early_expected_loss * early_pct)
        net_profit = (regular_results['net_profit'] * regular_pct) + (early_net_profit * early_pct)

        # Weighted average capital deployment
        capital_deployment_days = (regular_results['capital_deployment_days'] * regular_pct) + (early_capital_deployment_days * early_pct)
        capital_deployment_years = capital_deployment_days / 365

        # Blended effective yield
        if capital_deployment_years > 0:
            effective_yield = (net_profit / principal) / capital_deployment_years
        else:
            effective_yield = 1000.0 if net_profit > 0 else -1000.0

        # Recalculate settlement delay benefit
        yield_without_delay = (net_profit / principal) / loan_duration_years if loan_duration_years > 0 else 0
        settlement_delay_benefit = effective_yield - yield_without_delay if capital_deployment_years > 0 else 0

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
        'is_float_scenario': is_float_scenario,
        'first_installment_upfront': first_installment_upfront,
        'installment_amount': installment_amount,
        'capital_to_deploy': capital_to_deploy,
        'has_early_repayment': has_early_repayment,
        'early_repayment_rate': early_repayment_rate if has_early_repayment else 0.0,
        'avg_repayment_installment': avg_repayment_installment if has_early_repayment else None
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
    first_installment_upfront: bool = False,
    early_repayment_rate: float = 0.0,
    avg_repayment_installment: int = None,
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
            late_installment_pct=late_installment_pct,
            first_installment_upfront=first_installment_upfront,
            early_repayment_rate=early_repayment_rate,
            avg_repayment_installment=avg_repayment_installment
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
    first_installment_upfront: bool = False,
    early_repayment_rate: float = 0.0,
    avg_repayment_installment: int = None,
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
            late_installment_pct=late_installment_pct,
            first_installment_upfront=first_installment_upfront,
            early_repayment_rate=early_repayment_rate,
            avg_repayment_installment=avg_repayment_installment
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
