"""
Test script to verify revenue and loss breakdown
"""

from pricing_engine import calculate_effective_yield

# Test parameters with five-way segmentation
principal = 100.0
apr = 0.30  # 30% APR
installments = 6
merchant_commission_pct = 0.03
settlement_delay_days = 1
fixed_fee_pct = 0.02
funding_cost_apr = 0.08
installment_frequency_days = 14
late_fee_amount = 3.0
late_installment_pct = 0.20

print("=" * 80)
print("REVENUE & LOSS BREAKDOWN TEST")
print("=" * 80)

# Full five-way segmentation with late repayment and fraud
result = calculate_effective_yield(
    principal=principal,
    apr=apr,
    installments=installments,
    merchant_commission_pct=merchant_commission_pct,
    settlement_delay_days=settlement_delay_days,
    fraud_rate=0.10,  # 10% fraud
    default_rate=0.10,  # 10% default
    recovery_rate=0.30,  # 30% recovery on defaults
    fraud_recovery_rate=0.05,  # 5% recovery on fraud
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

print("\nPORTFOLIO SEGMENTATION:")
print("-" * 80)
print(f"Early: {result['early_repayment_rate'] * 100:.0f}%")
print(f"Late: {result['late_repayment_rate'] * 100:.0f}%")
print(f"On-Time: {result['ontime_pct'] * 100:.0f}%")
print(f"Default: {result['default_rate'] * 100:.0f}%")
print(f"Fraud: {result['fraud_rate'] * 100:.0f}%")

print("\nREVENUE BREAKDOWN:")
print("-" * 80)
print(f"Base Interest Income:    ${result['interest_income']:.2f}")
print(f"Late Interest Income:    ${result['late_interest_income']:.2f}  (extra from extended duration)")
print(f"Total Interest:          ${result['interest_income'] + result['late_interest_income']:.2f}")
print(f"Fixed Fee Income:        ${result['fixed_fee_income']:.2f}")
print(f"Merchant Commission:     ${result['merchant_commission']:.2f}")
print(f"Late Fee Income:         ${result['late_fee_income']:.2f}")
print(f"─" * 80)
print(f"TOTAL REVENUE:           ${result['total_revenue']:.2f}")

print("\nCOST & LOSS BREAKDOWN:")
print("-" * 80)
print(f"Default Loss:            ${result['default_loss']:.2f}  (10% portfolio @ 70% net loss)")
print(f"Fraud Loss:              ${result['fraud_loss']:.2f}  (10% portfolio @ 95% net loss)")
print(f"Total Expected Loss:     ${result['expected_loss']:.2f}")
print(f"Funding Cost:            ${result['funding_cost']:.2f}")
print(f"─" * 80)
print(f"TOTAL COSTS:             ${result['expected_loss'] + result['funding_cost']:.2f}")

print("\nNET PROFIT:")
print("-" * 80)
print(f"Net Profit:              ${result['net_profit']:.2f}")
print(f"Effective Yield:         {result['effective_yield'] * 100:.2f}%")

# Verify calculations
print("\nVERIFICATION:")
print("-" * 80)
total_revenue_calc = (result['interest_income'] +
                     result['late_interest_income'] +
                     result['fixed_fee_income'] +
                     result['merchant_commission'] +
                     result['late_fee_income'])
print(f"Revenue sum check: ${total_revenue_calc:.2f} = ${result['total_revenue']:.2f} ✓"
      if abs(total_revenue_calc - result['total_revenue']) < 0.01 else "✗")

total_loss_calc = result['default_loss'] + result['fraud_loss']
print(f"Loss sum check: ${total_loss_calc:.2f} = ${result['expected_loss']:.2f} ✓"
      if abs(total_loss_calc - result['expected_loss']) < 0.01 else "✗")

net_profit_calc = result['total_revenue'] - result['funding_cost'] - result['expected_loss']
print(f"Net profit check: ${net_profit_calc:.2f} = ${result['net_profit']:.2f} ✓"
      if abs(net_profit_calc - result['net_profit']) < 0.01 else "✗")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
