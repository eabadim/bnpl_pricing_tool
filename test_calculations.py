"""
Test script to verify settlement delay and installment frequency impacts
"""

from pricing_engine import calculate_effective_yield

# Base parameters
base_params = {
    'principal': 100.0,
    'apr': 0.60,  # 60% APR
    'installments': 6,
    'merchant_commission_pct': 0.025,  # 2.5%
    'default_rate': 0.05,  # 5%
    'recovery_rate': 0.20,  # 20%
    'fixed_fee_pct': 0.02,  # 2%
    'funding_cost_apr': 0.0,
    'late_fee_amount': 5.0,  # $5 late fee
    'late_installment_pct': 0.20  # 20% of installments are late
}

print("=" * 80)
print("TESTING SETTLEMENT DELAY IMPACT")
print("=" * 80)

# Test 1: Settlement delay impact (monthly installments)
print("\n1. Monthly Installments - Settlement Delay Impact:")
print("-" * 80)
print("NOTE: Longer settlement delay = HIGHER yield (capital deployed for less time)")

for delay in [0, 7, 14, 30]:
    result = calculate_effective_yield(
        **base_params,
        settlement_delay_days=delay,
        installment_frequency_days=30
    )
    print(f"\nSettlement Delay: {delay} days")
    print(f"  Loan Duration: {result['loan_duration_days']} days")
    print(f"  Capital Deployment: {result['capital_deployment_days']} days")
    print(f"  Effective Yield: {result['effective_yield'] * 100:.2f}%")
    print(f"  Settlement Benefit: +{result['settlement_delay_benefit'] * 100:.2f}%")
    print(f"  Net Profit: ${result['net_profit']:.2f}")

print("\n" + "=" * 80)
print("TESTING INSTALLMENT FREQUENCY IMPACT")
print("=" * 80)

# Test 2: Installment frequency impact (with same settlement delay)
print("\n2. Installment Frequency Comparison (7-day settlement delay):")
print("-" * 80)

for freq_name, freq_days in [("Monthly", 30), ("Biweekly", 14)]:
    result = calculate_effective_yield(
        **base_params,
        settlement_delay_days=7,
        installment_frequency_days=freq_days
    )
    print(f"\n{freq_name} ({freq_days} days per installment):")
    print(f"  Loan Duration: {result['loan_duration_days']} days")
    print(f"  Capital Deployment: {result['capital_deployment_days']} days")
    print(f"  Effective Yield: {result['effective_yield'] * 100:.2f}%")
    print(f"  Interest Income: ${result['interest_income']:.2f}")
    print(f"  Net Profit: ${result['net_profit']:.2f}")

print("\n" + "=" * 80)
print("TESTING COMBINED IMPACT")
print("=" * 80)

# Test 3: Combined impact
print("\n3. Combined Settlement Delay + Frequency Impact:")
print("-" * 80)

scenarios = [
    ("Monthly, No Delay", 30, 0),
    ("Monthly, 7-day Delay", 30, 7),
    ("Biweekly, No Delay", 14, 0),
    ("Biweekly, 7-day Delay", 14, 7),
]

for name, freq, delay in scenarios:
    result = calculate_effective_yield(
        **base_params,
        settlement_delay_days=delay,
        installment_frequency_days=freq
    )
    print(f"\n{name}:")
    print(f"  Capital Deployment: {result['capital_deployment_days']} days")
    print(f"  Effective Yield: {result['effective_yield'] * 100:.2f}%")

print("\n" + "=" * 80)
print("TESTING LATE FEE IMPACT")
print("=" * 80)

# Test 4: Late fee impact
print("\n4. Late Fee Revenue Impact:")
print("-" * 80)

late_fee_scenarios = [
    ("No Late Fees", 0.0, 0.0),
    ("$5 fee, 10% late", 5.0, 0.10),
    ("$5 fee, 20% late", 5.0, 0.20),
    ("$10 fee, 20% late", 10.0, 0.20),
]

for name, fee, pct_late in late_fee_scenarios:
    result = calculate_effective_yield(
        **{**base_params, 'settlement_delay_days': 7, 'installment_frequency_days': 30,
           'late_fee_amount': fee, 'late_installment_pct': pct_late}
    )
    print(f"\n{name}:")
    print(f"  Late Fee Income: ${result['late_fee_income']:.2f}")
    print(f"  Total Revenue: ${result['total_revenue']:.2f}")
    print(f"  Effective Yield: {result['effective_yield'] * 100:.2f}%")

print("\n" + "=" * 80)
print("KEY FINDINGS:")
print("=" * 80)
print("\n1. Settlement delay INCREASES yield by shortening capital deployment period")
print("2. Longer settlement delays = HIGHER yields (pay merchant later = less time deployed)")
print("3. Biweekly installments = Shorter loan duration = Higher annualized yield")
print("4. Settlement delay benefit is MORE significant for shorter loan terms")
print("5. In BNPL: You collect from customers FIRST, then pay merchant (if delay is long)")
print("6. Late fees provide significant additional revenue (only from non-defaulted loans)")
print("\n" + "=" * 80)
