# Quantitative Options & Backtest Audit Checklist

This checklist defines the rigorous verification standard for options trading strategies, machine learning models (e.g. ML28), and simulation engines.

---

## 📐 1. Machine Learning & Feature Integrity (ML28)
- [ ] **Lookahead Bias**: Verify that features at timestamp $T$ only utilize information strictly available at or before $T - \epsilon$.
- [ ] **Survivorship Bias**: Ensure delisted or expired contracts and tickers are accurately represented.
- [ ] **Data Leakage in Normalization**: Were scaler transforms (`StandardScaler`, `MinMaxScaler`) fit strictly on the training partition and only transformed on test/inference?
- [ ] **NaN / Inf / Zero Division**: Verify feature computation handlers for zero volume, zero open interest, or zero bid-ask spread.
- [ ] **Feature Skew**: Check feature distribution shifts between backtest periods and live market data.

---

## 📈 2. Options Mechanics & Greeks Sanity
- [ ] **Strike Selection & Delta Range**: Ensure short legs strictly respect target delta bounds (e.g. 0.10 - 0.20 delta).
- [ ] **Spread Width vs Credit**: Check that minimum credit / maximum risk ratio is enforced (e.g., credit must be $\ge X\%$ of wing width).
- [ ] **Greeks Consistency**:
  - Call Delta $\in [0, 1]$; Put Delta $\in [-1, 0]$.
  - Gamma $\ge 0$ for long options, $\le 0$ for short options.
  - Theta $\le 0$ for long options (time decay), $\ge 0$ for net short options.
- [ ] **Bid-Ask Spread Slippage**: Never assume fills at mid-price. Require realistic slippage modeling (e.g., fill at worst price or mid $\pm$ fraction of spread).

---

## 💰 3. PnL Accounting & Execution Ledger
- [ ] **Intraday vs Lifetime PnL**: Check that `day_pnl` resets strictly at market open/close and is not erroneously mapped to cumulative `total_pnl`.
- [ ] **Peak Profit Tracking**: Verify peak profit tracking logic for trailing stop and dynamic exit rules.
- [ ] **Commissions & Fees**: Include exchange fees, regulatory fees, and broker clearing costs ($0.65+ per contract).
- [ ] **Early Assignment / Expiration Handling**: Ensure ITM spreads at expiration correctly account for max loss without infinite liabilities.

---

## 🕒 4. Timezone & Timeline Synchronization
- [ ] Normalize all timestamps to UTC with explicit local market offsets (US/Eastern: 09:30 - 16:00 EST/EDT; CET/CEST).
- [ ] Ensure end-of-day (EOD) actions trigger reliably prior to market close (e.g., 15:45 - 15:55 US/Eastern).
