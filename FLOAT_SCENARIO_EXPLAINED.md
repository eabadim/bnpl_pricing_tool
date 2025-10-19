# Float Scenario: Deep Dive

## What is a Float Scenario?

A **float scenario** occurs when the settlement delay (days before Tafi pays the merchant) **exceeds or equals** the loan duration (time for customer to pay all installments).

## The Problem (Pre-Fix)

### Example: Biweekly 2-Installment Loan with 30-Day Settlement

**Loan Parameters:**
- Principal: $100
- Installments: 2 biweekly = 28 days total
- Settlement delay: 30 days

**Timeline:**
```
Day 0:  Customer purchases $100 item
Day 14: Customer pays 1st installment → Tafi receives ~$52
Day 28: Customer pays 2nd installment → Tafi receives ~$52 (has all money)
Day 30: Tafi pays merchant $100
```

**The Issue:**

OLD LOGIC calculated:
```python
capital_deployment_days = max(1, 28 - 30) = max(1, -2) = 1 day
```

This created:
- Net profit: $10
- Yield = ($10 / $100) / (1/365) = **3,650% annualized** ❌

This is **wrong** because:
1. Artificially inflates yield by dividing by 1 day
2. Doesn't reflect that capital was never deployed
3. Misleading for business decisions

## The Solution (Post-Fix)

### Detection Logic

```python
if settlement_delay_days >= loan_duration_days:
    # FLOAT SCENARIO
    float_period_days = settlement_delay_days - loan_duration_days
    capital_deployment_days = loan_duration_days * 0.25  # Conservative proxy
    is_float_scenario = True
else:
    # NORMAL SCENARIO
    capital_deployment_days = loan_duration_days - settlement_delay_days
    is_float_scenario = False
```

### Corrected Calculation

For the same example:
```python
settlement_delay_days = 30
loan_duration_days = 28

# Detected: 30 >= 28 → Float scenario!
float_period_days = 30 - 28 = 2 days
capital_deployment_days = 28 * 0.25 = 7 days (proxy)
is_float_scenario = True
```

Yield calculation:
```python
Net profit: $10
Proxy deployment: 7 days
Yield = ($10 / $100) / (7/365) = 521% annualized
```

**Plus UI Warning:**
```
⚠️ FLOAT SCENARIO DETECTED ⚠️

Settlement delay (30 days) ≥ Loan duration (28 days)

What this means:
- Customers pay ALL installments BEFORE Tafi pays merchant
- Tafi holds customer money for 2 days
- Zero net capital deployed
- Yield calculation uses proxy deployment (7 days)
- Actual yield is effectively INFINITE (no capital at risk)

This is extremely favorable but may not be realistic.
```

## Why Float Scenarios Matter

### Business Reality

**In Normal BNPL:**
1. Merchant wants money quickly (1-7 days)
2. Customer pays slowly (30-180 days)
3. BNPL company deploys capital for gap period
4. Earns interest/fees on deployed capital

**In Float Scenarios:**
1. Customer pays FAST (14-28 days for short loans)
2. Merchant gets money SLOWLY (30+ days)
3. BNPL holds customer money BEFORE paying merchant
4. ZERO capital deployed = INFINITE ROI

### When Might This Happen?

1. **Very short loans**: 2-3 biweekly installments (14-42 days)
2. **Extended merchant agreements**: 30-90 day settlement terms
3. **Promotional campaigns**: Delayed merchant payment incentives
4. **Testing edge cases**: Exploring parameter boundaries

### Float as Arbitrage Opportunity

If Tafi could achieve a float scenario:
- Collect all customer money Day 28
- Pay merchant Day 60 (32-day float)
- Invest customer money for 32 days
- Earn interest on $100 for 32 days
- **Risk-free profit** (plus all the normal BNPL revenue)

This is why float scenarios show "infinite yield" - there's no capital at risk.

## Comparison Table

| Metric | Normal Scenario | Float Scenario |
|--------|----------------|----------------|
| **Timeline** | Pay merchant → Collect from customer | Collect from customer → Pay merchant |
| **Capital Deployed** | Positive (gap period) | Zero or negative |
| **Risk** | Capital at risk for deployment period | No capital at risk |
| **Yield** | Finite (e.g., 40-100%) | Infinite (mathematically) |
| **Tool Handling** | Direct calculation | Proxy + warning |
| **Realism** | Very common | Rare but possible |

## Mathematical Analysis

### Normal Case (Settlement < Loan Duration)

Example: Monthly 4 installments (120 days), 7-day settlement
```
Capital deployment = 120 - 7 = 113 days
Net profit = $20
Yield = ($20 / $100) / (113/365) = 64.6%
```

✅ This makes sense - capital deployed for 113 days earning 64.6% annualized return.

### Float Case (Settlement ≥ Loan Duration)

Example: Biweekly 2 installments (28 days), 30-day settlement

**Mathematically:**
```
Capital deployment = 28 - 30 = -2 days (negative!)
Net profit = $10
Yield = ($10 / $100) / (-2/365) = UNDEFINED (negative deployment)

Or: Capital deployment = 0
Yield = ($10 / $100) / (0/365) = INFINITY
```

⚠️ This is mathematically correct but not useful for business planning.

**Tool Solution:**
```
Use proxy: 28 * 0.25 = 7 days
Yield = ($10 / $100) / (7/365) = 521%
+ Display warning about infinite actual yield
```

✅ Provides conservative estimate while flagging the special case.

## Key Takeaways

1. **Float scenarios are REAL** but rare in typical BNPL operations
2. **The tool now detects** them automatically and warns users
3. **Yield shown** is conservative proxy - actual is infinite
4. **Business value**: Highlights extreme leverage opportunities
5. **Use case**: Understand boundaries of BNPL economics

## Testing

Run `python test_float_scenario.py` to see:
- Normal scenarios working correctly
- Float scenarios detected and flagged
- Comparison of old (broken) vs new (fixed) logic
- Multiple float scenario examples

## Recommendations

**For Users:**
1. If you see the float warning, verify parameters are realistic
2. Consider if such extreme settlement delays are achievable
3. Use as theoretical best-case scenario
4. Reduce settlement delay for normal modeling

**For Product Teams:**
1. Float scenarios represent **maximum possible leverage**
2. Could inform merchant negotiation strategies
3. Short-term promotional loans most susceptible
4. Balance merchant satisfaction vs capital efficiency

---

**Version**: 1.4
**Author**: Tafi Development Team
**Date**: 2025-10-18
