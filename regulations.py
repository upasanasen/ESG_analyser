"""
Regulatory applicability layer for the ESG Report Analyser.

Rule-based and transparent, like the rest of the app:
  1. The user answers a few profile questions (sidebar).
  2. Each regulation gets an applicability status from those answers.
  3. The uploaded report is checked for evidence that the company already
     addresses that regulation.

This is a screening aid, NOT legal advice. All thresholds and dates below are
dated in LAST_REVIEWED and must be re-checked whenever the law changes.
"""

import pandas as pd

LAST_REVIEWED = "7 October 2026"

# Status labels (kept short so they fit in a chip)
LIKELY = "Likely applies"
MAYBE = "Check further"
UNLIKELY = "Unlikely to apply"
NOT_RELEVANT = "Not this check"

STATUS_STYLE = {
    LIKELY: ("#FBEAE8", "#B23A2F"),
    MAYBE: ("#FCF3E0", "#9A6A12"),
    UNLIKELY: ("#E7F5EC", "#0C7C43"),
    NOT_RELEVANT: ("#EDF1EE", "#59635C"),
}

CBAM_MASS_GOODS = ["Iron and steel", "Aluminium", "Cement", "Fertilisers"]
CBAM_NO_THRESHOLD_GOODS = ["Hydrogen", "Electricity"]
CBAM_GOODS = CBAM_MASS_GOODS + CBAM_NO_THRESHOLD_GOODS

YES, NO, NOT_SURE = "Yes", "No", "Not sure"

# ---------------------------------------------------------------------------
# Regulation library: facts live here, logic lives in the assess_* functions
# ---------------------------------------------------------------------------

REGULATIONS = {
    "cbam": {
        "name": "EU CBAM (Carbon Border Adjustment Mechanism)",
        "plain": "The EU puts a carbon price on certain imported goods, so it matches what EU producers pay under the EU ETS.",
        "key_facts": [
            "Definitive period started 1 January 2026 (the 2023–2025 phase was reporting only).",
            "Covers iron and steel, aluminium, cement, fertilisers, hydrogen and electricity.",
            "Importers bringing in more than 50 tonnes a year (cumulative) of the mass-based goods must be authorised CBAM declarants. Hydrogen and electricity have no such threshold.",
            "The legal obligation sits with the EU importer, but non-EU producers are asked to supply verified embedded-emissions data for their installations.",
        ],
        "evidence_terms": [
            "cbam", "carbon border", "embedded emissions", "embodied emissions",
            "product carbon footprint", "installation", "verified", "precursor",
        ],
        "sources": [
            ("European Commission – CBAM definitive regime",
             "https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/cbam-definitive-regime_en"),
        ],
    },
    "csrd_non_eu": {
        "name": "EU CSRD for non-EU groups (Article 40a, after Omnibus I)",
        "plain": "Large non-EU groups with substantial EU business must publish a group-level sustainability report.",
        "key_facts": [
            "Omnibus I (Directive (EU) 2026/470) is final and in force since March 2026.",
            "A non-EU group is in scope if its EU net turnover exceeds €450 million in each of the last two financial years AND it has an EU subsidiary or branch with net turnover above €200 million.",
            "First reporting year is FY2028, with the first report published in 2029.",
            "Smaller suppliers (up to 1,000 employees) are protected by a value-chain cap on what in-scope customers can demand from them.",
        ],
        "evidence_terms": [
            "csrd", "esrs", "double materiality", "sustainability statement",
            "value chain", "impact materiality", "financial materiality",
        ],
        "sources": [
            ("Directive (EU) 2026/470 (Omnibus I) – Clifford Chance summary",
             "https://www.cliffordchance.com/insights/resources/blogs/business-and-human-rights-insights/2026/02/omnibus-i-the-european-union-concludes-csddd-and-csrd-reforms.html"),
        ],
    },
    "uae_climate_law": {
        "name": "UAE Climate Law (Federal Decree-Law No. 11 of 2024)",
        "plain": "UAE entities that generate greenhouse gas emissions must measure, report and reduce them.",
        "key_facts": [
            "In force since 30 May 2025, with full compliance due by 30 May 2026.",
            "Applies to public and private entities in the UAE, including free zones.",
            "Core duties: measure emissions, keep an emissions inventory, report to MOCCAE through the national MRV system, and take reduction measures.",
            "Emissions records should be kept for at least five years.",
        ],
        "evidence_terms": [
            "scope 1", "scope 2", "emissions inventory", "greenhouse gas",
            "moccae", "mrv", "decree-law", "uae",
        ],
        "sources": [
            ("PwC Middle East – UAE Climate Change Law reporting obligations",
             "https://www.pwc.com/m1/en/services/legal/legal-news-alerts/2025/uae-climate-change-law-mandatory-emissions-reporting-obligations.html"),
        ],
    },
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _evidence(text: str, terms: list):
    found = [t for t in terms if t in text]
    missing = [t for t in terms if t not in text]
    return found, missing


def _result(key, status, why, actions, text):
    reg = REGULATIONS[key]
    found, missing = _evidence(text, reg["evidence_terms"])
    return {
        "key": key,
        "name": reg["name"],
        "plain": reg["plain"],
        "status": status,
        "why": why,
        "actions": actions,
        "key_facts": reg["key_facts"],
        "evidence_found": found,
        "evidence_missing": missing,
        "sources": reg["sources"],
    }

# ---------------------------------------------------------------------------
# Rule logic
# ---------------------------------------------------------------------------

def assess_cbam(profile: dict, text: str) -> dict:
    exports = profile.get("exports_to_eu", NOT_SURE)
    goods = profile.get("cbam_goods", [])
    tonnage = profile.get("cbam_tonnage", NOT_SURE)

    if exports == NO:
        return _result("cbam", UNLIKELY,
                       "You said you don't export goods to the EU.",
                       ["Re-check if you start selling physical goods into the EU."], text)

    if exports == YES and not goods:
        return _result("cbam", UNLIKELY,
                       "You export to the EU, but none of the goods you selected are covered by CBAM today.",
                       ["Watch for scope extensions: the Commission has proposed widening CBAM to some downstream products."],
                       text)

    if exports == NOT_SURE:
        return _result("cbam", MAYBE,
                       "Not enough information about your EU exports.",
                       ["Confirm whether you sell iron and steel, aluminium, cement, fertilisers, hydrogen or electricity into the EU."],
                       text)

    data_actions = [
        "Expect your EU customers (the importers) to ask for embedded-emissions data per product and installation.",
        "Set up installation-level emissions monitoring so you can supply actual values instead of EU default values, which are usually higher.",
        "Plan for third-party verification of those emissions data.",
    ]

    if any(g in CBAM_NO_THRESHOLD_GOODS for g in goods):
        return _result("cbam", LIKELY,
                       "You export hydrogen or electricity to the EU, which have no de minimis threshold.",
                       data_actions, text)

    if tonnage == "More than 50 tonnes a year":
        return _result("cbam", LIKELY,
                       "Your EU importers likely exceed the 50-tonne annual threshold for CBAM goods.",
                       data_actions, text)

    if tonnage == "Less than 50 tonnes a year":
        return _result("cbam", MAYBE,
                       "Your own volumes are under 50 tonnes, but the threshold is counted per EU importer, across all their suppliers.",
                       ["Ask your EU buyers whether they are authorised CBAM declarants; if so, they will still need your emissions data."],
                       text)

    return _result("cbam", MAYBE,
                   "You export CBAM goods but the annual tonnage is unclear.",
                   ["Estimate annual net tonnage of CBAM goods shipped to each EU buyer."] + data_actions[:1],
                   text)


def assess_csrd_non_eu(profile: dict, text: str) -> dict:
    hq = profile.get("hq", NOT_SURE)
    eu_turnover = profile.get("eu_turnover_450", NOT_SURE)
    sub_branch = profile.get("eu_sub_branch_200", NOT_SURE)

    if hq == "Inside the EU":
        return _result("csrd_non_eu", NOT_RELEVANT,
                       "This check is for non-EU groups. EU companies are in scope only above 1,000 employees and €450 million net turnover.",
                       ["Use the CSRD / ESRS readiness score on the dashboard for your own reporting."],
                       text)

    value_chain_action = ("Prepare for data requests from EU customers that are in scope; if you have 1,000 "
                          "employees or fewer, the value-chain cap limits what they can demand.")

    if eu_turnover == NO:
        return _result("csrd_non_eu", UNLIKELY,
                       "Your EU turnover is below the €450 million threshold.",
                       [value_chain_action], text)

    if eu_turnover == YES and sub_branch == YES:
        return _result("csrd_non_eu", LIKELY,
                       "Both Article 40a conditions appear to be met.",
                       ["Plan for group-level sustainability reporting from FY2028 (published 2029).",
                        "Start a double materiality assessment now; it drives what you must disclose.",
                        "Confirm which EU entity will publish the report and arrange the required assurance."],
                       text)

    if eu_turnover == YES and sub_branch == NO:
        return _result("csrd_non_eu", UNLIKELY,
                       "EU turnover is above €450 million, but no EU subsidiary or branch exceeds €200 million.",
                       ["Re-check each year, since subsidiary or branch growth can bring you into scope.",
                        value_chain_action],
                       text)

    return _result("csrd_non_eu", MAYBE,
                   "Not enough information about EU turnover or your EU subsidiaries and branches.",
                   ["Check EU net turnover for the last two financial years and the turnover of each EU subsidiary or branch."],
                   text)


def assess_uae(profile: dict, text: str) -> dict:
    uae = profile.get("operates_in_uae", NOT_SURE)

    if uae == NO:
        return _result("uae_climate_law", UNLIKELY,
                       "You said you have no operations in the UAE.",
                       ["Re-check if you open an office, branch or facility in the UAE (free zones included)."],
                       text)

    if uae == YES:
        return _result("uae_climate_law", LIKELY,
                       "You operate in the UAE, and the law applies broadly to entities that generate emissions there.",
                       ["Build a Scope 1 and Scope 2 emissions inventory for your UAE operations.",
                        "Register with MOCCAE's national MRV system and follow its reporting format and schedule.",
                        "Document reduction measures and keep emissions records for at least five years.",
                        "Check MOCCAE guidance for your sector, as implementing rules are still being detailed."],
                       text)

    return _result("uae_climate_law", MAYBE,
                   "Not clear whether you have UAE operations.",
                   ["Confirm whether any entity, branch or site of yours is in the UAE, including free zones."],
                   text)


def run_regulatory_checks(profile: dict, text: str) -> list:
    return [assess_cbam(profile, text), assess_csrd_non_eu(profile, text), assess_uae(profile, text)]


def results_to_dataframe(results: list) -> pd.DataFrame:
    return pd.DataFrame([{
        "Regulation": r["name"],
        "Status": r["status"],
        "Why": r["why"],
        "Evidence found in report": ", ".join(r["evidence_found"]) or "None",
        "Suggested actions": " | ".join(r["actions"]),
        "Rules last reviewed": LAST_REVIEWED,
    } for r in results])
