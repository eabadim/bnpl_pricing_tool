"""
Test script for five-way portfolio segmentation feature
Tests: Early / Late / On-Time / Default / Fraud portfolio blending
"""

from pricing_engine import calculate_effective_yield

# Test parameters
principal = 100.0
apr = 0.30  # 30% APR
installments = 6
merchant_commission_pct = 0.03  # 3%
settlement_delay_days = 1
fixed_fee_pct = 0.02  # 2%
funding_cost_apr = 0.08  # 8%
installment_frequency_days = 14  # biweekly
late_fee_amount = 3.0
late_installment_pct = 0.20  # 20%

print("=" * 80)
print("FIVE-WAY PORTFOLIO SEGMENTATION TEST")
print("=" * 80)

# Test 1: Baseline (no segmentation - 100% on-time payers)
print("\n1. BASELINE TEST (100% On-Time Payers)")
print("-" * 80)

baseline_result = calculate_effective_yield(
    principal=principal,
    apr=apr,
    installments=installments,
    merchant_commission_pct=merchant_commission_pct,
    settlement_delay_days=settlement_delay_days,
    fraud_rate=0.0,
    default_rate=0.15,  # 15% default
    recovery_rate=0.10,  # 10% recovery
    fraud_recovery_rate=0.10,
    fixed_fee_pct=fixed_fee_pct,
    funding_cost_apr=funding_cost_apr,
    installment_frequency_days=installment_frequency_days,
    late_fee_amount=late_fee_amount,
    late_installment_pct=late_installment_pct,
    first_installment_upfront=False,
    early_repayment_rate=0.0,
    avg_repayment_installment=None,
    late_repayment_rate=0.0,
    avg_days_late_per_installment=0
)

print(f"Has Portfolio Segmentation: {baseline_result['has_portfolio_segmentation']}")
print(f"On-Time %: {baseline_result['ontime_pct'] * 100:.1f}%")
print(f"Effective Yield: {baseline_result['effective_yield'] * 100:.2f}%")
print(f"Net Profit: ${baseline_result['net_profit']:.2f}")
print(f"Expected Loss: ${baseline_result['expected_loss']:.2f}")

# Test 2: Late repayment only (30% late, 70% on-time + defaults)
print("\n2. LATE REPAYMENT TEST (30% late, 5 days per installment)")
print("-" * 80)

late_result = calculate_effective_yield(
    principal=principal,
    apr=apr,
    installments=installments,
    merchant_commission_pct=merchant_commission_pct,
    settlement_delay_days=settlement_delay_days,
    fraud_rate=0.0,
    default_rate=0.15,
    recovery_rate=0.10,
    fraud_recovery_rate=0.10,
    fixed_fee_pct=fixed_fee_pct,
    funding_cost_apr=funding_cost_apr,
    installment_frequency_days=installment_frequency_days,
    late_fee_amount=late_fee_amount,
    late_installment_pct=late_installment_pct,
    first_installment_upfront=False,
    early_repayment_rate=0.0,
    avg_repayment_installment=None,
    late_repayment_rate=0.30,  # 30% pay late
    avg_days_late_per_installment=5
)

print(f"Has Late Repayment: {late_result['has_late_repayment']}")
print(f"Late Repayment Rate: {late_result['late_repayment_rate'] * 100:.0f}%")
print(f"Avg Days Late Per Installment: {late_result['avg_days_late_per_installment']}")
print(f"On-Time %: {late_result['ontime_pct'] * 100:.1f}%")
print(f"Effective Yield: {late_result['effective_yield'] * 100:.2f}%")
print(f"Interest Income: ${late_result['interest_income']:.2f}")
print(f"Late Fee Income: ${late_result['late_fee_income']:.2f}")
print(f"Expected Loss: ${late_result['expected_loss']:.2f}")

# Test 3: Fraud separation (10% fraud, 10% default)
print("\n3. FRAUD SEPARATION TEST (10% fraud, 10% legitimate default)")
print("-" * 80)

fraud_result = calculate_effective_yield(
    principal=principal,
    apr=apr,
    installments=installments,
    merchant_commission_pct=merchant_commission_pct,
    settlement_delay_days=settlement_delay_days,
    fraud_rate=0.10,  # 10% fraud
    default_rate=0.10,  # 10% legitimate default
    recovery_rate=0.30,  # 30% recovery on defaults
    fraud_recovery_rate=0.05,  # 5% recovery on fraud (lower)
    fixed_fee_pct=fixed_fee_pct,
    funding_cost_apr=funding_cost_apr,
    installment_frequency_days=installment_frequency_days,
    late_fee_amount=late_fee_amount,
    late_installment_pct=late_installment_pct,
    first_installment_upfront=False,
    early_repayment_rate=0.0,
    avg_repayment_installment=None,
    late_repayment_rate=0.0,
    avg_days_late_per_installment=0
)

print(f"Has Portfolio Segmentation: {fraud_result['has_portfolio_segmentation']}")
print(f"Fraud Rate: {fraud_result['fraud_rate'] * 100:.0f}%")
print(f"Default Rate: {fraud_result['default_rate'] * 100:.0f}%")
print(f"On-Time %: {fraud_result['ontime_pct'] * 100:.1f}%")
print(f"Effective Yield: {fraud_result['effective_yield'] * 100:.2f}%")
print(f"Expected Loss: ${fraud_result['expected_loss']:.2f}")

# Test 4: Full five-way segmentation (10% early, 20% late, 50% on-time, 10% default, 10% fraud)
print("\n4. FULL FIVE-WAY SEGMENTATION TEST")
print("-" * 80)

full_result = calculate_effective_yield(
    principal=principal,
    apr=apr,
    installments=installments,
    merchant_commission_pct=merchant_commission_pct,
    settlement_delay_days=settlement_delay_days,
    fraud_rate=0.10,  # 10% fraud
    default_rate=0.10,  # 10% default
    recovery_rate=0.30,
    fraud_recovery_rate=0.05,
    fixed_fee_pct=fixed_fee_pct,
    funding_cost_apr=funding_cost_apr,
    installment_frequency_days=installment_frequency_days,
    late_fee_amount=late_fee_amount,
    late_installment_pct=late_installment_pct,
    first_installment_upfront=False,
    early_repayment_rate=0.10,  # 10% early
    avg_repayment_installment=3,
    late_repayment_rate=0.20,  # 20% late
    avg_days_late_per_installment=5
)

print(f"Has Portfolio Segmentation: {full_result['has_portfolio_segmentation']}")
print(f"Early: {full_result['early_repayment_rate'] * 100:.0f}% | "
      f"Late: {full_result['late_repayment_rate'] * 100:.0f}% | "
      f"On-Time: {full_result['ontime_pct'] * 100:.0f}% | "
      f"Default: {full_result['default_rate'] * 100:.0f}% | "
      f"Fraud: {full_result['fraud_rate'] * 100:.0f}%")
total_pct = (full_result['early_repayment_rate'] +
             full_result['late_repayment_rate'] +
             full_result['ontime_pct'] +
             full_result['default_rate'] +
             full_result['fraud_rate']) * 100
print(f"Total Portfolio: {total_pct:.0f}%")
print(f"Effective Yield: {full_result['effective_yield'] * 100:.2f}%")
print(f"Interest Income: ${full_result['interest_income']:.2f}")
print(f"Late Fee Income: ${full_result['late_fee_income']:.2f}")
print(f"Expected Loss: ${full_result['expected_loss']:.2f}")
print(f"Net Profit: ${full_result['net_profit']:.2f}")

# Test 5: Fraud with first installment upfront
print("\n5. FRAUD WITH FIRST INSTALLMENT UPFRONT")
print("-" * 80)

fraud_upfront_result = calculate_effective_yield(
    principal=principal,
    apr=apr,
    installments=installments,
    merchant_commission_pct=merchant_commission_pct,
    settlement_delay_days=settlement_delay_days,
    fraud_rate=0.20,  # 20% fraud
    default_rate=0.10,
    recovery_rate=0.30,
    fraud_recovery_rate=0.05,
    fixed_fee_pct=fixed_fee_pct,
    funding_cost_apr=funding_cost_apr,
    installment_frequency_days=installment_frequency_days,
    late_fee_amount=late_fee_amount,
    late_installment_pct=late_installment_pct,
    first_installment_upfront=True,  # Collect first installment
    early_repayment_rate=0.0,
    avg_repayment_installment=None,
    late_repayment_rate=0.0,
    avg_days_late_per_installment=0
)

print(f"First Installment Upfront: {fraud_upfront_result['first_installment_upfront']}")
print(f"Fraud Rate: {fraud_upfront_result['fraud_rate'] * 100:.0f}%")
print(f"Installment Amount: ${fraud_upfront_result['installment_amount']:.2f}")
print(f"Capital to Deploy: ${fraud_upfront_result['capital_to_deploy']:.2f}")
print(f"Expected Loss: ${fraud_upfront_result['expected_loss']:.2f}")
print(f"Note: Fraud cases paid first installment, then disappeared")

# Test 6: Portfolio validation - should fail if segments exceed 100%
print("\n6. PORTFOLIO VALIDATION TEST (Should Fail)")
print("-" * 80)

try:
    invalid_result = calculate_effective_yield(
        principal=principal,
        apr=apr,
        installments=installments,
        merchant_commission_pct=merchant_commission_pct,
        settlement_delay_days=settlement_delay_days,
        fraud_rate=0.40,  # 40%
        default_rate=0.30,  # 30%
        recovery_rate=0.10,
        fraud_recovery_rate=0.10,
        fixed_fee_pct=fixed_fee_pct,
        funding_cost_apr=funding_cost_apr,
        installment_frequency_days=installment_frequency_days,
        late_fee_amount=late_fee_amount,
        late_installment_pct=late_installment_pct,
        first_installment_upfront=False,
        early_repayment_rate=0.30,  # 30%
        avg_repayment_installment=3,
        late_repayment_rate=0.20,  # 20%  (Total = 120% > 100%)
        avg_days_late_per_installment=5
    )
    print("ERROR: Validation should have failed!")
except ValueError as e:
    print(f"✓ Validation passed - caught error as expected:")
    print(f"  {str(e)}")

# Test 7: Compare late repayment impact
print("\n7. LATE REPAYMENT IMPACT ANALYSIS")
print("-" * 80)

# Baseline without late repayment
baseline_no_late = calculate_effective_yield(
    principal=principal,
    apr=apr,
    installments=installments,
    merchant_commission_pct=merchant_commission_pct,
    settlement_delay_days=settlement_delay_days,
    fraud_rate=0.0,
    default_rate=0.15,
    recovery_rate=0.10,
    fraud_recovery_rate=0.10,
    fixed_fee_pct=fixed_fee_pct,
    funding_cost_apr=funding_cost_apr,
    installment_frequency_days=installment_frequency_days,
    late_fee_amount=late_fee_amount,
    late_installment_pct=late_installment_pct,
    first_installment_upfront=False,
    early_repayment_rate=0.0,
    avg_repayment_installment=None,
    late_repayment_rate=0.0,
    avg_days_late_per_installment=0
)

# With 30% late repayment
with_late = calculate_effective_yield(
    principal=principal,
    apr=apr,
    installments=installments,
    merchant_commission_pct=merchant_commission_pct,
    settlement_delay_days=settlement_delay_days,
    fraud_rate=0.0,
    default_rate=0.15,
    recovery_rate=0.10,
    fraud_recovery_rate=0.10,
    fixed_fee_pct=fixed_fee_pct,
    funding_cost_apr=funding_cost_apr,
    installment_frequency_days=installment_frequency_days,
    late_fee_amount=late_fee_amount,
    late_installment_pct=late_installment_pct,
    first_installment_upfront=False,
    early_repayment_rate=0.0,
    avg_repayment_installment=None,
    late_repayment_rate=0.30,
    avg_days_late_per_installment=5
)

print(f"Baseline Yield (no late): {baseline_no_late['effective_yield'] * 100:.2f}%")
print(f"With Late Repayment (30%): {with_late['effective_yield'] * 100:.2f}%")
print(f"Yield Change: {(with_late['effective_yield'] - baseline_no_late['effective_yield']) * 100:+.2f} percentage points")
print(f"\nInterest Income Change: ${with_late['interest_income'] - baseline_no_late['interest_income']:+.2f}")
print(f"Late Fee Income Change: ${with_late['late_fee_income'] - baseline_no_late['late_fee_income']:+.2f}")
print(f"Expected Loss Change: ${with_late['expected_loss'] - baseline_no_late['expected_loss']:+.2f}")
print(f"Expected: Late repayment should INCREASE yield (more interest + late fees, zero defaults on late segment)")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
