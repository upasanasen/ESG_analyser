# ESG Report Analyser: CSRD Readiness & Greenwashing Risk Scanner

A public no-API Streamlit app that screens sustainability reports for ESG disclosure maturity, CSRD/ESRS readiness, framework coverage, disclosure gaps, and greenwashing risks.

## Live app

Try the deployed Streamlit app here: [ESG Report Analyser](https://esganalyser-vi66mikxysdymj3hyd8aga.streamlit.app/)

## What it does

- Upload a sustainability report PDF
- Extract text using PyMuPDF
- Run rule-based checks for ESG, CSRD/ESRS, GRI, TCFD, GHG Protocol, and SDG terms
- Score ESG disclosure maturity
- Flag possible greenwashing claims
- Generate a template-based executive summary
- Show dashboard visualisations
- Export CSV outputs for gaps, ESRS coverage, greenwashing review, and regulatory check
- Check which regulations may apply (EU CBAM, CSRD for non-EU groups, UAE Climate Law) from a short company profile

## Regulatory check (new)

A short profile in the sidebar (HQ location, UAE operations, EU exports, EU turnover) drives a rule-based applicability check for:

- **EU CBAM**: definitive period since 1 January 2026; 50-tonne annual threshold per EU importer (none for hydrogen and electricity)
- **EU CSRD for non-EU groups (Article 40a, after Omnibus I)**: more than €450m EU turnover in each of the last two years plus an EU subsidiary or branch above €200m; first reporting year FY2028
- **UAE Climate Law (Federal Decree-Law No. 11 of 2024)**: in force since 30 May 2025, full compliance due 30 May 2026

The uploaded report is also scanned for evidence that each regulation is already addressed. All rules live in `regulations.py` and are dated (`LAST_REVIEWED`). This is a screening aid, not legal advice.

## Tech stack

- Python
- Streamlit
- PyMuPDF
- Pandas
- Plotly

## Important note

This public version does not use paid AI APIs. It uses a rule-based ESG intelligence engine and should be treated as a screening tool, not a formal ESG audit or assurance opinion.

## Future roadmap

- Optional local LLM mode
- Optional API-based AI analysis
- ESRS datapoint-level mapping
- PDF report export
- Benchmark comparison across companies
