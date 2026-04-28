# ESG Report Analyser: CSRD Readiness & Greenwashing Risk Scanner

A public no-API Streamlit app that screens sustainability reports for ESG disclosure maturity, CSRD/ESRS readiness, framework coverage, disclosure gaps, and greenwashing risks.

## What it does

- Upload a sustainability report PDF
- Extract text using PyMuPDF
- Run rule-based checks for ESG, CSRD/ESRS, GRI, TCFD, GHG Protocol, and SDG terms
- Score ESG disclosure maturity
- Flag possible greenwashing claims
- Generate a template-based executive summary
- Show dashboard visualisations
- Export CSV outputs for gaps, ESRS coverage, and greenwashing review

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
