# Tafi BNPL Pricing Strategy Simulator

An interactive Python-based tool for modeling and visualizing the profitability and yield of Tafi's Buy Now Pay Later (BNPL) products under different pricing, merchant, and credit assumptions.

## Features

- **Dual Mode Support**: Model both interest-bearing and interest-free BNPL plans
- **Comprehensive Inputs**: Adjust merchant commission, settlement delays, default rates, APR, and more
- **Real-time Calculations**:
  - Effective annualized yield
  - Required APR to hit target yield
  - Maximum interest-free installment count
  - Profit margins and revenue breakdowns
- **Interactive Visualizations**:
  - Yield vs Default Rate sensitivity
  - Yield vs Installment Count analysis
  - APR vs Merchant Commission requirements
  - **Yield vs Settlement Delay** (shows critical impact on profitability)
- **Comparison Tools**: Side-by-side analysis of interest-bearing vs interest-free economics
- **Key Insights**: Automated analysis with actionable recommendations

## Installation

1. Clone or navigate to this repository:
```bash
cd /Users/ernestoabadi/Developer/tafi_pricing_tool
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the Streamlit application:
```bash
streamlit run app.py
```

The application will open in your default web browser at `http://localhost:8501`

## Configuration Parameters

### Loan Parameters
- **Average Loan Principal**: Base loan amount ($)
- **Average Installment Count**: Number of payments (2-12)
- **Installment Frequency**: Choose between Monthly (30 days) or Biweekly (14 days)
- **Interest Rate (APR)**: Annual percentage rate for interest-bearing loans (0-100%)
- **Fixed Loan Fee**: One-time fee as % of principal (0-10%)

### Late Fee Parameters
- **Late Fee Amount ($)**: Fee charged per late installment payment ($2-$20)
- **% of Installments Paid Late**: Percentage of installments that incur late fees (0-100%)

### Business Parameters
- **Merchant Commission**: Fee charged to merchants (0-10%)
- **Settlement Delay**: Days until merchant is paid (0-60)
- **Default Rate**: Expected portfolio default rate (0-30%)
- **Credit Loss Recovery Rate**: % recovered from defaulted loans (0-100%)
- **Target Annualized Yield**: Desired portfolio-level return (10-100%)
- **Funding Cost**: Cost of capital APR (0-20%)

## Core Calculations

### Effective Yield Formula
```
Effective Yield = Net Profit / Principal / Capital Deployment Period (annualized)

where:
Capital Deployment Period = Loan Duration - Settlement Delay
```

**CRITICAL**: Settlement delay INCREASES yield by reducing the capital deployment period. This is because Tafi can delay paying the merchant while still collecting from customers.

**BNPL Cash Flow Timeline:**
- **Day 0**: Customer makes purchase
- **Day 0 + Settlement Delay**: Tafi pays merchant (capital deployed)
- **Day 0 + Loan Duration**: Last customer payment received

If settlement delay is 30 days and loan duration is 120 days, capital is only deployed for **90 days**.

### Key Components
- **Interest Income**: Calculated using declining balance approximation
- **Fixed Fee Income**: One-time fee applied to principal
- **Merchant Commission**: Revenue from merchant partnerships
- **Late Fee Income**: Revenue from late payments (only on non-defaulted loans)
  - Formula: `Installments × (1 - Default Rate) × % Late × Late Fee Amount`
- **Funding Cost**: Cost of capital during settlement delay period
- **Expected Loss**: Principal lost after recovery from defaults
- **Settlement Delay Benefit**: Yield increase from delayed merchant payment

### Settlement Delay Impact Examples
Based on a $100 loan with 6 monthly installments at 60% APR:
- **0-day delay**: 31.01% yield (baseline)
- **7-day delay**: 32.27% yield (+1.25% benefit)
- **14-day delay**: 33.63% yield (+2.62% benefit)
- **30-day delay**: 37.22% yield (+6.20% benefit)

The settlement delay benefit is MORE significant for shorter-term loans (higher % of total duration).

### Late Fee Impact Examples
Based on a $100 loan with 6 monthly installments at 60% APR (with 7-day settlement delay):
- **No late fees**: 32.27% yield (baseline)
- **$5 fee, 10% late**: 38.28% yield (+6.01% from late fees)
- **$5 fee, 20% late**: 44.29% yield (+12.02% from late fees)
- **$10 fee, 20% late**: 56.32% yield (+24.05% from late fees)

Late fees can be a **major revenue driver** for BNPL profitability, potentially adding 10-25%+ to effective yield.

### Float Scenario Edge Case ⚠️

**What is a Float Scenario?**

When **settlement delay ≥ loan duration**, customers pay ALL installments BEFORE Tafi pays the merchant. This creates a "float" where Tafi holds customer money with ZERO capital deployed.

**Example:**
- Biweekly, 2 installments = 28-day loan duration
- Settlement delay = 30 days
- Timeline:
  - Day 14: Customer pays 1st installment
  - Day 28: Customer pays final installment (Tafi has all money)
  - Day 30: Tafi pays merchant
- Result: Tafi holds customer money for 2 days before paying merchant

**Yield Calculation in Float Scenarios:**

Mathematically, yield = Profit / Capital Deployed. When capital deployed = 0, yield is **infinite**.

For practical purposes, the tool:
- Detects float scenarios automatically
- Uses a proxy deployment period (25% of loan duration) for yield calculation
- Displays a warning banner in the UI
- Shows the actual float period

**Float Scenario Yields:**
- Displayed yield: Conservative estimate using proxy (e.g., 245%)
- Actual yield: **Infinite** (no capital at risk)
- These scenarios are favorable but often unrealistic

## Business Logic

The tool uses sophisticated algorithms to:

1. **Calculate Effective Yield**: Accounts for all revenue sources, costs, and default losses
2. **Determine Required APR**: Binary search algorithm to find APR needed for target yield
3. **Estimate Interest-Free Cap**: Maximum installments viable for 0% APR plans
4. **Generate Sensitivity Analysis**: Sweep through parameter ranges for what-if scenarios

## File Structure

```
tafi_pricing_tool/
├── app.py                 # Main Streamlit application
├── pricing_engine.py      # Core calculation functions
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Use Cases

1. **Pricing Strategy**: Determine optimal APR for different merchant partnerships
2. **Product Design**: Evaluate viability of interest-free installment plans
3. **Risk Assessment**: Model impact of default rates on portfolio yield
4. **Merchant Negotiations**: Analyze minimum commission rates needed
5. **Credit Policy**: Set installment limits based on target returns

## Technical Details

- **Python Version**: 3.10+
- **Framework**: Streamlit for web UI
- **Calculations**: NumPy for numerical operations
- **Data Handling**: Pandas for structured data
- **Visualizations**: Plotly for interactive charts

## License

Internal use for Tafi financial modeling.
