#!/usr/bin/env python3
"""
COLA II Omission Detector - Find What's NOT Disclosed
Often the most critical violations are things NOT mentioned in 408(b)(2) disclosures
"""

import re
from typing import List, Dict, Any, Set, Optional
from dataclasses import dataclass
from enum import Enum


class DisclosureElement(Enum):
    """Required 408(b)(2) disclosure elements"""
    FIDUCIARY_STATUS = "fiduciary_status"
    SERVICES_DESCRIPTION = "services_description"
    DIRECT_COMPENSATION = "direct_compensation"
    INDIRECT_COMPENSATION = "indirect_compensation"
    FEE_CALCULATION_METHOD = "fee_calculation_method"
    TERMINATION_PROVISIONS = "termination_provisions"
    RECORDKEEPING_FEE = "recordkeeping_fee"
    ASSET_BASED_FEE = "asset_based_fee"
    TRANSACTION_FEE = "transaction_fee"
    FLOAT_INCOME_TREATMENT = "float_income_treatment"
    REVENUE_SHARING_SOURCE = "revenue_sharing_source"
    REVENUE_SHARING_AMOUNT = "revenue_sharing_amount"
    PARTY_IN_INTEREST_STATUS = "party_in_interest_status"


@dataclass
class OmissionFinding:
    """Finding for a missing disclosure"""
    element: DisclosureElement
    severity: str  # 'critical', 'high', 'medium'
    description: str
    legal_citation: str
    lawsuit_precedent: str
    red_flag_score: int
    explanation: str


class OmissionDetector:
    """
    Detect missing required disclosures

    Philosophy: What's NOT said is often more important than what is.

    Under 408(b)(2), service providers MUST disclose:
    1. Fiduciary status
    2. Services provided
    3. ALL compensation (direct + indirect)
    4. How compensation is calculated
    5. How to terminate the relationship

    Missing ANY = Prohibited Transaction
    """

    # Required 408(b)(2) elements with detection patterns
    REQUIRED_ELEMENTS = {
        DisclosureElement.FIDUCIARY_STATUS: {
            'patterns': [
                r'fiduciary\s+(?:status|capacity|role)',
                r'(?:act|serve|acting)\s+as\s+(?:a\s+)?fiduciary',
                r'ERISA\s+(?:section\s+)?3\(21\)',
                r'ERISA\s+(?:section\s+)?3\(38\)',
                r'investment\s+(?:manager|advisor).*?fiduciary',
                r'acknowledge.*?fiduciary',
            ],
            'severity': 'critical',
            'red_flag_score': 10,
            'description': 'Fiduciary status disclosure missing',
            'legal_citation': '29 CFR 2550.408b-2(c)(1)(iv)(A)',
            'lawsuit_precedent': 'Harris v. Amgen - failure to disclose fiduciary status',
            'explanation': 'Service providers must explicitly state whether they are acting as an ERISA fiduciary'
        },

        DisclosureElement.SERVICES_DESCRIPTION: {
            'patterns': [
                r'services?\s+(?:provided|offered|to\s+be\s+provided)',
                r'scope\s+of\s+(?:services?|work)',
                r'(?:will|shall)\s+provide',
                r'responsibilities?\s+(?:include|are)',
                r'service\s+description',
            ],
            'severity': 'critical',
            'red_flag_score': 9,
            'description': 'Services description missing or inadequate',
            'legal_citation': '29 CFR 2550.408b-2(c)(1)(iv)(B)',
            'lawsuit_precedent': 'Tussey v. ABB - vague service descriptions contributed to violation',
            'explanation': 'Must provide clear, detailed description of all services to be provided to the plan'
        },

        DisclosureElement.DIRECT_COMPENSATION: {
            'patterns': [
                r'direct\s+(?:compensation|fees?|payment)',
                r'(?:paid|pay|payment)\s+directly',
                r'(?:plan|sponsor)\s+(?:will\s+)?pay',
                r'\$[\d,]+(?:\.\d{2})?\s+(?:per|for)',
                r'compensation.*?(?:paid|payable)\s+(?:by|from)\s+(?:the\s+)?plan',
            ],
            'severity': 'critical',
            'red_flag_score': 10,
            'description': 'Direct compensation not disclosed',
            'legal_citation': '29 CFR 2550.408b-2(c)(1)(iv)(C)(1)',
            'lawsuit_precedent': 'All compensation must be disclosed per DOL final rule',
            'explanation': 'Must disclose all fees paid directly by plan or sponsor'
        },

        DisclosureElement.INDIRECT_COMPENSATION: {
            'patterns': [
                r'indirect\s+(?:compensation|fees?|payment)',
                r'revenue\s+shar(?:ing|e)',
                r'12b-1',
                r'sub[- ]?(?:ta|transfer\s+agent)',
                r'shareholder\s+servicing',
                r'paid\s+(?:by|from).*?(?:fund|investment|third\s+party)',
            ],
            'severity': 'critical',
            'red_flag_score': 10,
            'description': 'Indirect compensation not disclosed',
            'legal_citation': '29 CFR 2550.408b-2(c)(1)(iv)(C)(2)',
            'lawsuit_precedent': 'Tussey v. ABB - $35M judgment for hidden revenue sharing',
            'explanation': 'Must disclose ALL compensation from any source related to plan services'
        },

        DisclosureElement.FEE_CALCULATION_METHOD: {
            'patterns': [
                r'(?:calculated|computed|determined)\s+(?:by|as|based\s+on)',
                r'(?:calculation|computation)\s+(?:method|methodology|formula)',
                r'formula(?:\s+(?:for|is|:))?',
                r'(?:fee|compensation).*?(?:calculated|computed)',
            ],
            'severity': 'high',
            'red_flag_score': 8,
            'description': 'Fee calculation method not disclosed',
            'legal_citation': '29 CFR 2550.408b-2(c)(1)(iv)(C)',
            'lawsuit_precedent': 'Participants must be able to verify fee calculations',
            'explanation': 'Must explain HOW fees are calculated so plan can verify accuracy'
        },

        DisclosureElement.TERMINATION_PROVISIONS: {
            'patterns': [
                r'terminat(?:e|ion)',
                r'cancel(?:lation|)',
                r'end\s+(?:the\s+)?(?:agreement|relationship|services?)',
                r'notice\s+(?:period|requirement)',
                r'(?:without|with)\s+cause',
            ],
            'severity': 'high',
            'red_flag_score': 7,
            'description': 'Termination provisions not disclosed',
            'legal_citation': '29 CFR 2550.408b-2(c)(1)(iv)(D)',
            'lawsuit_precedent': 'Plans must know how to end relationship if fees excessive',
            'explanation': 'Must disclose how plan can terminate service arrangement'
        },

        DisclosureElement.RECORDKEEPING_FEE: {
            'patterns': [
                r'recordkeep(?:ing|er)',
                r'administration.*?fee',
                r'record.*?maintenance',
                r'\$[\d,]+\s+per\s+participant',
                r'administrative\s+(?:services?|fee)',
            ],
            'severity': 'high',
            'red_flag_score': 8,
            'description': 'Recordkeeping fee amount not disclosed',
            'legal_citation': '29 CFR 2550.408b-2(c)(1)(iv)(C)',
            'lawsuit_precedent': 'Tussey v. ABB - recordkeeping fee disclosure inadequate',
            'explanation': 'Recordkeeping fee must be disclosed in clear dollar or percentage terms'
        },

        DisclosureElement.ASSET_BASED_FEE: {
            'patterns': [
                r'asset[- ]based\s+fee',
                r'[\d.]+%\s+of\s+assets',
                r'[\d.]+\s+basis\s+points',
                r'percentage\s+of\s+(?:plan\s+)?assets',
            ],
            'severity': 'medium',
            'red_flag_score': 6,
            'description': 'Asset-based fee not clearly disclosed',
            'legal_citation': '29 CFR 2550.408b-2(c)(1)(iv)(C)',
            'lawsuit_precedent': 'Asset-based fees must be disclosed if charged',
            'explanation': 'If any fees calculated as % of assets, must be disclosed'
        },

        DisclosureElement.FLOAT_INCOME_TREATMENT: {
            'patterns': [
                r'float\s+income',
                r'earnings?\s+on\s+(?:uninvested|pending|float)',
                r'(?:uninvested|pending)\s+(?:cash|contributions?)',
                r'credited\s+to\s+(?:the\s+)?plan',
                r'settlement\s+(?:period|account)',
            ],
            'severity': 'critical',
            'red_flag_score': 9,
            'description': 'Float income treatment not disclosed',
            'legal_citation': '29 CFR 2550.408b-2(c)(1)(iv)(C)',
            'lawsuit_precedent': 'Tussey v. ABB - $13.4M for float income misallocation',
            'explanation': 'If float income exists, MUST disclose: how calculated, who receives it, how credited to plan'
        },

        DisclosureElement.REVENUE_SHARING_SOURCE: {
            'patterns': [
                r'revenue\s+shar(?:ing|e).*?(?:from|paid\s+by|source)',
                r'(?:paid|received)\s+(?:by|from).*?(?:fund|investment)',
                r'source\s+of.*?compensation',
            ],
            'severity': 'high',
            'red_flag_score': 8,
            'description': 'Revenue sharing source not disclosed',
            'legal_citation': '29 CFR 2550.408b-2(c)(1)(iv)(C)(2)',
            'lawsuit_precedent': 'Tussey v. ABB - hidden revenue sharing sources = violation',
            'explanation': 'Must identify WHO pays revenue sharing (fund company, investment provider, etc.)'
        },

        DisclosureElement.REVENUE_SHARING_AMOUNT: {
            'patterns': [
                r'revenue\s+shar(?:ing|e).*?(?:\$|[\d.]+%|[\d.]+\s+(?:bps|basis))',
                r'12b-1.*?(?:\$|[\d.]+%)',
                r'sub[- ]?ta.*?(?:\$|[\d.]+%|[\d.]+\s+(?:bps|basis))',
            ],
            'severity': 'high',
            'red_flag_score': 8,
            'description': 'Revenue sharing amount not disclosed',
            'legal_citation': '29 CFR 2550.408b-2(c)(1)(iv)(C)(2)',
            'lawsuit_precedent': 'Tussey v. ABB - failure to disclose revenue sharing amounts',
            'explanation': 'Must specify AMOUNT of revenue sharing in dollars, percentages, or basis points'
        },

        DisclosureElement.PARTY_IN_INTEREST_STATUS: {
            'patterns': [
                r'party\s+in\s+interest',
                r'disqualified\s+person',
                r'ERISA\s+(?:section\s+)?406',
                r'prohibited\s+transaction\s+exemption',
                r'related\s+party',
            ],
            'severity': 'high',
            'red_flag_score': 8,
            'description': 'Party in interest status not disclosed',
            'legal_citation': 'ERISA §406(a)',
            'lawsuit_precedent': 'Harris v. Amgen - affiliated relationships must be disclosed',
            'explanation': 'If service provider is party in interest or has affiliate relationships, must disclose'
        },
    }

    def __init__(self):
        self.omissions = []

    def detect_omissions(self, document_text: str) -> List[OmissionFinding]:
        """
        Scan document for missing required elements

        Returns CRITICAL findings for any missing 408(b)(2) requirement
        """
        omissions = []

        for element, config in self.REQUIRED_ELEMENTS.items():
            if not self._element_present(document_text, config['patterns']):
                omission = OmissionFinding(
                    element=element,
                    severity=config['severity'],
                    description=config['description'],
                    legal_citation=config['legal_citation'],
                    lawsuit_precedent=config['lawsuit_precedent'],
                    red_flag_score=config['red_flag_score'],
                    explanation=config['explanation']
                )
                omissions.append(omission)

        self.omissions = omissions
        return omissions

    def check_float_income_disclosure_completeness(self, document_text: str) -> Optional[OmissionFinding]:
        """
        Special check for float income (Tussey $13.4M violation)

        If float is mentioned, must have ALL of:
        1. How it's calculated
        2. Who receives it
        3. How it's credited to plan
        """
        float_mentioned = any(
            re.search(pattern, document_text, re.IGNORECASE)
            for pattern in [
                r'float\s+income',
                r'earnings?\s+on\s+(?:uninvested|pending)',
                r'uninvested\s+cash'
            ]
        )

        if not float_mentioned:
            return None  # No float = no disclosure needed

        # If float mentioned, check for required sub-elements
        required_disclosures = {
            'how_calculated': [
                r'(?:how|method).*?(?:calculated|determined|computed)',
                r'calculation.*?(?:of|for).*?float',
            ],
            'who_receives': [
                r'(?:received|retained|paid|credited)\s+(?:by|to)',
                r'(?:plan|participant|provider|recordkeeper).*?(?:receives?|retains?)',
            ],
            'credited_to_plan': [
                r'credited\s+to\s+(?:the\s+)?plan',
                r'allocated\s+to\s+participant',
                r'benefit\s+of\s+(?:the\s+)?plan',
            ]
        }

        missing = []
        for disclosure_name, patterns in required_disclosures.items():
            if not any(re.search(p, document_text, re.IGNORECASE) for p in patterns):
                missing.append(disclosure_name.replace('_', ' ').title())

        if missing:
            return OmissionFinding(
                element=DisclosureElement.FLOAT_INCOME_TREATMENT,
                severity='critical',
                description=f'Float income mentioned but incomplete: missing {", ".join(missing)}',
                legal_citation='29 CFR 2550.408b-2(c)(1)(iv)(C)',
                lawsuit_precedent='Tussey v. ABB - $13.4M for incomplete float disclosure',
                red_flag_score=10,
                explanation='Float income requires complete disclosure of calculation, recipient, and plan credit'
            )

        return None

    def check_revenue_sharing_disclosure_completeness(self, document_text: str) -> Optional[OmissionFinding]:
        """
        Special check for revenue sharing (Tussey $35M violation)

        If revenue sharing mentioned, must have ALL of:
        1. Source (who pays it)
        2. Amount ($ or %)
        3. Purpose (what services it compensates)
        4. Recipient (who receives it)
        """
        rev_share_mentioned = any(
            re.search(pattern, document_text, re.IGNORECASE)
            for pattern in [
                r'revenue\s+shar(?:ing|e)',
                r'12b-1',
                r'sub[- ]?ta',
                r'indirect\s+compensation'
            ]
        )

        if not rev_share_mentioned:
            return None

        required = {
            'source': [
                r'(?:paid|provided|received)\s+(?:by|from)',
                r'source\s+of',
            ],
            'amount': [
                r'\$[\d,]+',
                r'[\d.]+%',
                r'[\d.]+\s+(?:basis\s+points?|bps?)',
            ],
            'purpose': [
                r'(?:for|to\s+(?:compensate|pay)\s+for)',
                r'services?\s+(?:provided|compensated)',
            ],
            'recipient': [
                r'(?:received|paid\s+to|retained)\s+by',
                r'(?:advisor|recordkeeper|provider|we).*?(?:receives?|retains?)',
            ]
        }

        missing = []
        for element, patterns in required.items():
            if not any(re.search(p, document_text, re.IGNORECASE) for p in patterns):
                missing.append(element.title())

        if missing:
            return OmissionFinding(
                element=DisclosureElement.INDIRECT_COMPENSATION,
                severity='critical',
                description=f'Revenue sharing incomplete: missing {", ".join(missing)}',
                legal_citation='29 CFR 2550.408b-2(c)(1)(iv)(C)(2)',
                lawsuit_precedent='Tussey v. ABB - $35M judgment for inadequate revenue sharing disclosure',
                red_flag_score=10,
                explanation='Revenue sharing requires: source, amount, purpose, and recipient'
            )

        return None

    def generate_omission_report(self) -> Dict[str, Any]:
        """Generate summary report of all omissions"""
        if not self.omissions:
            return {
                'total_omissions': 0,
                'compliance_status': 'COMPLETE',
                'risk_level': 'LOW'
            }

        critical_count = len([o for o in self.omissions if o.severity == 'critical'])
        high_count = len([o for o in self.omissions if o.severity == 'high'])

        return {
            'total_omissions': len(self.omissions),
            'by_severity': {
                'critical': critical_count,
                'high': high_count,
                'medium': len([o for o in self.omissions if o.severity == 'medium'])
            },
            'compliance_status': 'INCOMPLETE - PROHIBITED TRANSACTION RISK',
            'risk_level': 'CRITICAL' if critical_count > 0 else 'HIGH' if high_count > 0 else 'MEDIUM',
            'total_red_flag_score': sum(o.red_flag_score for o in self.omissions),
            'omission_details': [
                {
                    'element': o.element.value,
                    'severity': o.severity,
                    'description': o.description,
                    'lawsuit_precedent': o.lawsuit_precedent,
                    'red_flag_score': o.red_flag_score
                }
                for o in self.omissions
            ]
        }

    def _element_present(self, text: str, patterns: List[str]) -> bool:
        """Check if any pattern matches in text"""
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def check_document_completeness(document_text: str) -> Dict[str, Any]:
    """
    Complete omission check for a document

    Returns all missing elements + special checks for float and revenue sharing
    """
    detector = OmissionDetector()

    # Main omission check
    omissions = detector.detect_omissions(document_text)

    # Special detailed checks
    float_issue = detector.check_float_income_disclosure_completeness(document_text)
    if float_issue:
        omissions.append(float_issue)

    rev_share_issue = detector.check_revenue_sharing_disclosure_completeness(document_text)
    if rev_share_issue:
        omissions.append(rev_share_issue)

    detector.omissions = omissions
    return detector.generate_omission_report()
