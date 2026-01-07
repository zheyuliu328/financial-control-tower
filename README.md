<div align="center">
  <h1>📊 VaR Risk Dashboard</h1>
  <p><strong>A market risk engine that calculates 99% Value-at-Risk and validates it with statistical backtesting.</strong></p>
  
  <a href="https://github.com/zheyuliu328/risk-var-dashboard/stargazers"><img alt="GitHub stars" src="https://img.shields.io/github/stars/zheyuliu328/risk-var-dashboard?style=for-the-badge&logo=github&labelColor=000000&logoColor=FFFFFF&color=0500ff" /></a>
  <a href="https://github.com/zheyuliu328/risk-var-dashboard/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge&labelColor=000000&color=00C853" /></a>
  <a href="https://www.python.org/"><img alt="Python" src="https://img.shields.io/badge/python-3.9+-blue?style=for-the-badge&logo=python&labelColor=000000&logoColor=FFFFFF" /></a>
</div>

<br>

<div align="center">
  <img src="images/var_dashboard.png" alt="VaR Dashboard" width="800"/>
</div>

<br>

## What is this?

This project builds a Value-at-Risk engine using real S&P 500 data from 2020 to 2026. It calculates how much money you could lose on a bad day at the 99% confidence level, then checks whether the model actually works by counting how often losses exceeded the prediction.

The punchline is that the model failed more than it should have. It predicted a 1% breach rate but the actual rate was 1.67%. The Kupiec test confirmed this statistically. This is exactly what risk managers worry about: normal distributions underestimate tail risk during market stress.

<br>

## The Key Finding

The model uses a rolling 252-day window to estimate volatility and calculate VaR. When we backtest against actual returns, we see more breaches than expected.

| Metric | Expected | Actual |
|:-------|:---------|:-------|
| Breach Rate | 1.00% | 1.67% |
| Kupiec LR Statistic | — | 4.77 |
| Test Result | — | Reject H₀ |

What does this mean? The standard normal assumption underestimates risk. In practice, you would need Expected Shortfall or stress testing to capture the true tail risk.

<br>

## Quick Start

Three commands and you have a working risk dashboard.

```bash
pip install -r requirements.txt
```

```bash
python download_data.py
```

This fetches S&P 500 price data from Yahoo Finance.

```bash
python main.py
```

This calculates VaR, runs the backtest, and generates the dashboard image.

<br>

## How It Works

The engine implements two VaR calculation methods and one validation test.

**Parametric VaR** assumes returns follow a normal distribution. It uses the mean and standard deviation from the past 252 trading days to estimate the 99th percentile loss.

**Historical Simulation VaR** makes no distribution assumption. It simply takes the 1st percentile of actual historical returns as the VaR estimate.

**Kupiec Test** checks whether the number of VaR breaches matches the expected rate. If the model is correct, breaches should occur about 1% of the time. The test uses a likelihood ratio to determine if the observed breach rate is statistically different from 1%.

<br>

## Project Structure

```
risk-var-dashboard/
├── main.py              # Main engine: VaR calculation and backtesting
├── download_data.py     # Fetches S&P 500 data from Yahoo Finance
├── data/
│   └── sp500.csv        # Historical price data
├── images/
│   └── var_dashboard.png    # Output visualization
├── DEVELOPMENT_NOTES.md     # Technical notes
└── requirements.txt
```

<br>

## The Math Behind It

For Parametric VaR at confidence level α:

```
VaR_α = μ + σ × Z_α
```

Where μ is the rolling mean return, σ is the rolling standard deviation, and Z_α is the quantile of the standard normal distribution. For 99% confidence, Z_0.01 ≈ -2.33.

For the Kupiec test, the likelihood ratio is:

```
LR = -2 × ln[(1-p)^(n-x) × p^x] + 2 × ln[(1-x/n)^(n-x) × (x/n)^x]
```

Where p is the expected breach probability (0.01), n is the number of observations, and x is the number of actual breaches. Under the null hypothesis, LR follows a chi-squared distribution with 1 degree of freedom.

<br>

## Why This Matters

VaR is the standard risk metric used by banks, hedge funds, and regulators. Basel III requires banks to calculate VaR daily and hold capital against potential losses.

But VaR has a known weakness: it assumes returns are normally distributed, which underestimates tail risk. This project demonstrates that weakness empirically. The 1.67% breach rate during a period that included COVID-19 volatility shows why risk managers cannot rely on VaR alone.

<br>

## Tech Stack

| Tool | Purpose |
|:-----|:--------|
| Python 3.9+ | Main language |
| NumPy | Numerical computation |
| Pandas | Data manipulation |
| SciPy | Statistical tests |
| Matplotlib | Visualization |
| yfinance | Market data |

<br>

## Author

**Zheyu Liu**

This is a portfolio project demonstrating market risk concepts. The methodology follows standard industry practice for VaR calculation and backtesting.

<br>

---

<div align="center">
  <sub>Built for learning. Inspired by Basel III risk frameworks.</sub>
</div>

