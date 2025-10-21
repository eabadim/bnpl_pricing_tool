"""
Test script for early repayment feature
"""

from pricing_engine import calculate_effective_yield

# Test parameters
principal = 100.0
apr = 0.30  # 30% APR
installments = 6
merchant_commission_pct = 0.03  # 3%
settlement_delay_days = 1
default_rate = 0.15  # 15%
recovery_rate = 0.10  # 10%
fixed_fee_pct = 0.02  # 2%
funding_cost_apr = 0.08  # 8%
installment_frequency_days = 14  # biweekly
late_fee_amount = 3.0
late_installment_pct = 0.20  # 20%

print("=" * 80)
print("EARLY REPAYMENT FEATURE TEST")
print("=" * 80)

# Test 1: Baseline (no early repayment)
print("\n1. BASELINE TEST (No Early Repayment)")
print("-" * 80)

baseline_result = calculate_effective_yield(
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
    first_installment_upfront=False,
    early_repayment_rate=0.0,
    avg_repayment_installment=None
)

print(f"Has Early Repayment: {baseline_result['has_early_repayment']}")
print(f"Effective Yield: {baseline_result['effective_yield'] * 100:.2f}%")
print(f"Interest Income: ${baseline_result['interest_income']:.2f}")
print(f"Merchant Commission: ${baseline_result['merchant_commission']:.2f}")
print(f"Fixed Fee Income: ${baseline_result['fixed_fee_income']:.2f}")
print(f"Late Fee Income: ${baseline_result['late_fee_income']:.2f}")
print(f"Expected Loss: ${baseline_result['expected_loss']:.2f}")
print(f"Net Profit: ${baseline_result['net_profit']:.2f}")

# Test 2: Early repayment enabled (30% rate, repay at installment 3)
print("\n2. EARLY REPAYMENT TEST (30% rate, repay at installment 3)")
print("-" * 80)

early_result = calculate_effective_yield(
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
    first_installment_upfront=False,
    early_repayment_rate=0.30,  # 30% repay early
    avg_repayment_installment=3  # at installment 3
)

print(f"Has Early Repayment: {early_result['has_early_repayment']}")
print(f"Early Repayment Rate: {early_result['early_repayment_rate'] * 100:.0f}%")
print(f"Avg Repayment Installment: {early_result['avg_repayment_installment']}")
print(f"Effective Yield: {early_result['effective_yield'] * 100:.2f}%")
print(f"Interest Income: ${early_result['interest_income']:.2f}")
print(f"Merchant Commission: ${early_result['merchant_commission']:.2f}")
print(f"Fixed Fee Income: ${early_result['fixed_fee_income']:.2f}")
print(f"Late Fee Income: ${early_result['late_fee_income']:.2f}")
print(f"Expected Loss: ${early_result['expected_loss']:.2f}")
print(f"Net Profit: ${early_result['net_profit']:.2f}")

# Test 3: Verify portfolio blending effects
print("\n3. PORTFOLIO BLENDING ANALYSIS")
print("-" * 80)

print(f"\nInterest Income Change:")
print(f"  Baseline: ${baseline_result['interest_income']:.2f}")
print(f"  With Early Repayment: ${early_result['interest_income']:.2f}")
print(f"  Change: ${early_result['interest_income'] - baseline_result['interest_income']:.2f} ({((early_result['interest_income'] / baseline_result['interest_income']) - 1) * 100:.1f}%)")
print(f"  Expected: Should DECREASE (early repayers pay less interest)")

print(f"\nExpected Loss Change:")
print(f"  Baseline: ${baseline_result['expected_loss']:.2f}")
print(f"  With Early Repayment: ${early_result['expected_loss']:.2f}")
print(f"  Change: ${early_result['expected_loss'] - baseline_result['expected_loss']:.2f} ({((early_result['expected_loss'] / baseline_result['expected_loss']) - 1) * 100:.1f}%)")
print(f"  Expected: Should DECREASE (30% of portfolio has 0% defaults)")

print(f"\nMerchant Commission (should be PROTECTED):")
print(f"  Baseline: ${baseline_result['merchant_commission']:.2f}")
print(f"  With Early Repayment: ${early_result['merchant_commission']:.2f}")
print(f"  Change: ${early_result['merchant_commission'] - baseline_result['merchant_commission']:.2f}")
print(f"  Expected: Should be IDENTICAL (merchant commission protected)")

print(f"\nFixed Fee Income (should be PROTECTED):")
print(f"  Baseline: ${baseline_result['fixed_fee_income']:.2f}")
print(f"  With Early Repayment: ${early_result['fixed_fee_income']:.2f}")
print(f"  Change: ${early_result['fixed_fee_income'] - baseline_result['fixed_fee_income']:.2f}")
print(f"  Expected: Should be IDENTICAL (fixed fees protected)")

print(f"\nNet Impact on Yield:")
print(f"  Baseline Yield: {baseline_result['effective_yield'] * 100:.2f}%")
print(f"  Early Repayment Yield: {early_result['effective_yield'] * 100:.2f}%")
print(f"  Change: {(early_result['effective_yield'] - baseline_result['effective_yield']) * 100:.2f} percentage points")
print(f"  Note: Net impact depends on trade-off between lower interest income and lower defaults")

# Test 4: Edge case - 100% early repayment
print("\n4. EDGE CASE TEST (100% Early Repayment)")
print("-" * 80)

full_early_result = calculate_effective_yield(
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
    first_installment_upfront=False,
    early_repayment_rate=1.0,  # 100% repay early
    avg_repayment_installment=3
)

print(f"Effective Yield: {full_early_result['effective_yield'] * 100:.2f}%")
print(f"Expected Loss: ${full_early_result['expected_loss']:.2f}")
print(f"Expected: Expected loss should be $0.00 (100% early repayment = 0% defaults)")

# Test 5: Edge case - early repayment at last installment (should have no effect)
print("\n5. EDGE CASE TEST (Early Repayment at Last Installment)")
print("-" * 80)

late_early_result = calculate_effective_yield(
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
    first_installment_upfront=False,
    early_repayment_rate=0.30,
    avg_repayment_installment=6  # Same as total installments
)

print(f"Has Early Repayment: {late_early_result['has_early_repayment']}")
print(f"Note: Should be False because avg_repayment_installment >= installments")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
