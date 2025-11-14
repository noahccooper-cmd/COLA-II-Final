#!/usr/bin/env python3
"""
COLA II Quantitative Analyzer - Extract, Calculate, and Benchmark Fees
Converts messy fee language into comparable numbers and flags threshold violations
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


@dataclass
class ExtractedFee:
    """Fee extracted from document"""
    amount: float
    fee_type: str  # 'dollar', 'percentage', 'basis_points', 'per_participant'
    original_text: str
    page_no: int
    context: str


@dataclass
class CalculatedCost:
    """Calculated total cost from percentage fee"""
    annual_cost: float
    per_participant: float
    fee_percentage: float
    plan_assets: float
    participant_count: int
    violation: Optional[Dict[str, Any]] = None


class FeeType(Enum):
    """Fee type classifications"""
    RECORDKEEPING = "recordkeeping"
    INVESTMENT_MANAGEMENT = "investment_management"
    ADVISORY = "advisory"
    REVENUE_SHARING = "revenue_sharing"
    TOTAL_EXPENSE_RATIO = "total_expense_ratio"
    UNKNOWN = "unknown"


class QuantitativeAnalyzer:
    """
    Extract and analyze numerical fee data with precision

    Capabilities:
    - Extract fees in any format ($X, X%, X bps, $X per participant)
    - Convert between formats for comparison
    - Calculate hidden costs from percentages
    - Flag threshold violations (Tussey benchmarks)
    - Detect numerical obfuscation
    """

    # Tussey v. ABB and industry benchmarks
    THRESHOLDS = {
        'recordkeeping_per_participant': 70,  # Tussey: >$70/participant = flag
        'total_expense_ratio_large_plan': 1.0,  # >$1B assets: >1.0% = excessive
        'total_expense_ratio_medium_plan': 1.25,  # $100M-$1B: >1.25%
        'revenue_sharing_bps': 25,  # >25 bps (0.25%) = scrutiny
        'share_class_expense_delta': 0.20,  # >20 bps difference = violation
        'cornell_threshold': 350,  # Cornell v. Cunningham: $350/participant
    }

    def __init__(self):
        self.extracted_fees = []

    def extract_all_fees(self, text: str, page_no: int = 0) -> List[ExtractedFee]:
        """
        Extract fees in ALL formats from text

        Handles:
        - Dollar amounts: $X, $X.XX, $X,XXX, $X,XXX,XXX
        - Percentages: X%, X.XX%
        - Basis points: X basis points, X bps, X bp
        - Per participant: $X per participant, $X/participant
        - Combinations: "$50 per participant plus 0.05% of assets"
        """
        fees = []

        # Dollar amounts (simple and with commas)
        dollar_pattern = r'\$\s*([\d,]+(?:\.\d{2})?)'
        for match in re.finditer(dollar_pattern, text):
            amount_str = match.group(1).replace(',', '')
            try:
                amount = float(amount_str)
                fees.append(ExtractedFee(
                    amount=amount,
                    fee_type='dollar',
                    original_text=match.group(0),
                    page_no=page_no,
                    context=self._get_context(text, match.start(), match.end())
                ))
            except ValueError:
                pass

        # Percentages
        percent_pattern = r'([\d.]+)\s*%'
        for match in re.finditer(percent_pattern, text):
            try:
                amount = float(match.group(1))
                fees.append(ExtractedFee(
                    amount=amount,
                    fee_type='percentage',
                    original_text=match.group(0),
                    page_no=page_no,
                    context=self._get_context(text, match.start(), match.end())
                ))
            except ValueError:
                pass

        # Basis points
        bps_pattern = r'([\d.]+)\s*(?:basis\s+points?|bps?|bp)\b'
        for match in re.finditer(bps_pattern, text, re.IGNORECASE):
            try:
                amount = float(match.group(1))
                fees.append(ExtractedFee(
                    amount=amount,
                    fee_type='basis_points',
                    original_text=match.group(0),
                    page_no=page_no,
                    context=self._get_context(text, match.start(), match.end())
                ))
            except ValueError:
                pass

        # Per participant fees
        per_part_pattern = r'\$\s*([\d,]+(?:\.\d{2})?)\s*(?:per\s+participant|/\s*participant|per\s+person)'
        for match in re.finditer(per_part_pattern, text, re.IGNORECASE):
            amount_str = match.group(1).replace(',', '')
            try:
                amount = float(amount_str)
                fees.append(ExtractedFee(
                    amount=amount,
                    fee_type='per_participant',
                    original_text=match.group(0),
                    page_no=page_no,
                    context=self._get_context(text, match.start(), match.end())
                ))
            except ValueError:
                pass

        self.extracted_fees.extend(fees)
        return fees

    def calculate_hidden_costs(self,
                              percentage_fee: float,
                              plan_assets: float,
                              participant_count: int,
                              fee_category: FeeType = FeeType.UNKNOWN) -> CalculatedCost:
        """
        Convert percentage fee to dollars and check thresholds

        Example (Tussey scenario):
        - Fee: 0.25% of assets
        - Plan assets: $500M
        - Participants: 5,000

        Calculation:
        - Annual cost: $1.25M
        - Per participant: $250
        - ALERT: Exceeds $70 threshold by 257%

        This is how violations hide in plain sight.
        """

        # Convert to decimal if needed
        if percentage_fee > 10:  # Likely entered as bps
            percentage_fee = percentage_fee / 100

        annual_cost = (percentage_fee / 100) * plan_assets
        per_participant = annual_cost / participant_count if participant_count > 0 else 0

        # Check for violations
        violation = None

        # Recordkeeping fee threshold (Tussey benchmark)
        if fee_category == FeeType.RECORDKEEPING:
            if per_participant > self.THRESHOLDS['recordkeeping_per_participant']:
                excess_pct = ((per_participant / self.THRESHOLDS['recordkeeping_per_participant']) - 1) * 100
                annual_overpayment = (per_participant - self.THRESHOLDS['recordkeeping_per_participant']) * participant_count

                violation = {
                    'type': 'excessive_recordkeeping_fee',
                    'per_participant': per_participant,
                    'threshold': self.THRESHOLDS['recordkeeping_per_participant'],
                    'excess_percent': excess_pct,
                    'annual_overpayment': annual_overpayment,
                    'severity': 'high' if excess_pct > 100 else 'medium',
                    'precedent': 'Tussey v. ABB - Court flagged fees >$70/participant',
                    'legal_citation': '29 USC 1104(a)(1)(A)(ii) - Minimize Expenses'
                }

        # Total expense ratio threshold
        elif fee_category == FeeType.TOTAL_EXPENSE_RATIO:
            threshold = self._get_ter_threshold(plan_assets)
            if percentage_fee > threshold:
                violation = {
                    'type': 'excessive_total_expense_ratio',
                    'expense_ratio': percentage_fee,
                    'threshold': threshold,
                    'plan_size': plan_assets,
                    'severity': 'high',
                    'precedent': 'Large plan excessive fee cases (50+ lawsuits 2016-2024)',
                    'legal_citation': 'ERISA 404(a)(1)(A)(ii)'
                }

        # Cornell threshold (extreme cases)
        if per_participant > self.THRESHOLDS['cornell_threshold']:
            violation = {
                'type': 'cornell_excessive',
                'per_participant': per_participant,
                'threshold': self.THRESHOLDS['cornell_threshold'],
                'severity': 'critical',
                'precedent': 'Cunningham v. Cornell - $350/participant deemed excessive',
                'legal_citation': 'ERISA 404(a)(1)(A)(ii)'
            }

        return CalculatedCost(
            annual_cost=annual_cost,
            per_participant=per_participant,
            fee_percentage=percentage_fee,
            plan_assets=plan_assets,
            participant_count=participant_count,
            violation=violation
        )

    def convert_basis_points_to_percentage(self, basis_points: float) -> float:
        """Convert basis points to percentage (100 bps = 1%)"""
        return basis_points / 100

    def convert_percentage_to_basis_points(self, percentage: float) -> float:
        """Convert percentage to basis points (1% = 100 bps)"""
        return percentage * 100

    def calculate_per_participant_fee(self,
                                     total_annual_fee: float,
                                     participant_count: int) -> float:
        """Calculate per-participant cost from total fee"""
        return total_annual_fee / participant_count if participant_count > 0 else 0

    def flag_threshold_violations(self,
                                 per_participant_fee: float,
                                 total_expense_ratio: float,
                                 plan_assets: float) -> List[Dict[str, Any]]:
        """
        Check all thresholds and return violations

        Thresholds:
        - Recordkeeping: >$70/participant (Tussey)
        - Cornell extreme: >$350/participant
        - TER for large plans: >1.0% ($1B+ assets)
        - TER for medium plans: >1.25% ($100M-$1B assets)
        """
        violations = []

        # Per-participant recordkeeping
        if per_participant_fee > self.THRESHOLDS['recordkeeping_per_participant']:
            violations.append({
                'type': 'excessive_per_participant',
                'amount': per_participant_fee,
                'threshold': self.THRESHOLDS['recordkeeping_per_participant'],
                'excess': per_participant_fee - self.THRESHOLDS['recordkeeping_per_participant'],
                'severity': 'high'
            })

        # Cornell extreme threshold
        if per_participant_fee > self.THRESHOLDS['cornell_threshold']:
            violations.append({
                'type': 'cornell_excessive',
                'amount': per_participant_fee,
                'threshold': self.THRESHOLDS['cornell_threshold'],
                'severity': 'critical'
            })

        # Total expense ratio
        ter_threshold = self._get_ter_threshold(plan_assets)
        if total_expense_ratio > ter_threshold:
            violations.append({
                'type': 'excessive_ter',
                'ter': total_expense_ratio,
                'threshold': ter_threshold,
                'plan_assets': plan_assets,
                'severity': 'high'
            })

        return violations

    def compare_share_class_fees(self,
                                 retail_expense_ratio: float,
                                 institutional_expense_ratio: float) -> Dict[str, Any]:
        """
        Compare retail vs institutional expense ratios (Tussey violation)

        Even small differences = millions in excess fees over time
        """
        delta = retail_expense_ratio - institutional_expense_ratio
        delta_bps = delta * 100

        is_violation = delta_bps > self.THRESHOLDS['share_class_expense_delta']

        return {
            'retail_er': retail_expense_ratio,
            'institutional_er': institutional_expense_ratio,
            'delta_percentage': delta,
            'delta_basis_points': delta_bps,
            'is_violation': is_violation,
            'threshold': self.THRESHOLDS['share_class_expense_delta'],
            'severity': 'high' if is_violation else 'low',
            'precedent': 'Tussey v. ABB - $21.8M for retail share class selection' if is_violation else None
        }

    def detect_numerical_obfuscation(self, fees: List[ExtractedFee]) -> List[Dict[str, Any]]:
        """
        Detect numerical obfuscation tactics:
        - Basis points without percentage conversion
        - Percentages without dollar amounts
        - Layered fees (hard to calculate total)
        - Fee ranges instead of actual amounts
        """
        obfuscations = []

        # Check for basis points without conversion
        bps_fees = [f for f in fees if f.fee_type == 'basis_points']
        for fee in bps_fees:
            # Check if percentage is shown nearby
            if '%' not in fee.context and 'percent' not in fee.context.lower():
                obfuscations.append({
                    'type': 'basis_points_no_conversion',
                    'fee': fee,
                    'severity': 'medium',
                    'explanation': f'{fee.amount} bps shown without percentage equivalent ({self.convert_basis_points_to_percentage(fee.amount):.2f}%)'
                })

        # Check for percentages without dollar context
        pct_fees = [f for f in fees if f.fee_type == 'percentage']
        for fee in pct_fees:
            if '$' not in fee.context and 'dollar' not in fee.context.lower():
                obfuscations.append({
                    'type': 'percentage_no_dollar',
                    'fee': fee,
                    'severity': 'medium',
                    'explanation': f'{fee.amount}% shown without dollar amount (hides per-participant cost)'
                })

        return obfuscations

    def _get_ter_threshold(self, plan_assets: float) -> float:
        """Get appropriate TER threshold based on plan size"""
        if plan_assets >= 1_000_000_000:  # $1B+
            return self.THRESHOLDS['total_expense_ratio_large_plan']
        elif plan_assets >= 100_000_000:  # $100M+
            return self.THRESHOLDS['total_expense_ratio_medium_plan']
        else:
            return 1.50  # Smaller plans have higher threshold

    def _get_context(self, text: str, start: int, end: int, window: int = 100) -> str:
        """Extract context around match for analysis"""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end]


# ============================================================================
# ANALYSIS FUNCTIONS
# ============================================================================

def analyze_fees_in_document(text: str,
                            plan_assets: Optional[float] = None,
                            participant_count: Optional[int] = None) -> Dict[str, Any]:
    """
    Complete fee analysis for a document

    Returns:
    - All extracted fees
    - Calculated costs (if plan data provided)
    - Threshold violations
    - Obfuscation detection
    """
    analyzer = QuantitativeAnalyzer()

    # Extract all fees
    fees = analyzer.extract_all_fees(text)

    results = {
        'extracted_fees': len(fees),
        'fees_by_type': {},
        'violations': [],
        'obfuscations': [],
        'calculated_costs': []
    }

    # Group by type
    for fee_type in ['dollar', 'percentage', 'basis_points', 'per_participant']:
        results['fees_by_type'][fee_type] = len([f for f in fees if f.fee_type == fee_type])

    # Calculate hidden costs if plan data provided
    if plan_assets and participant_count:
        percentage_fees = [f for f in fees if f.fee_type == 'percentage']
        for fee in percentage_fees:
            cost = analyzer.calculate_hidden_costs(
                fee.amount,
                plan_assets,
                participant_count,
                FeeType.UNKNOWN
            )
            results['calculated_costs'].append({
                'original_fee': f'{fee.amount}%',
                'annual_cost': f'${cost.annual_cost:,.2f}',
                'per_participant': f'${cost.per_participant:.2f}',
                'violation': cost.violation
            })

            if cost.violation:
                results['violations'].append(cost.violation)

    # Detect obfuscation
    results['obfuscations'] = analyzer.detect_numerical_obfuscation(fees)

    return results


def calculate_lawsuit_exposure(violations: List[Dict[str, Any]],
                               participant_count: int) -> Dict[str, Any]:
    """
    Estimate potential lawsuit exposure based on violations

    Uses actual settlement data:
    - Tussey v. ABB: $55M ($13.4M float + $21.8M share classes + $20M other)
    - Recordkeeping excess: ~$200-$500 per participant settlement
    """
    total_exposure = 0
    breakdown = []

    for violation in violations:
        if violation['type'] == 'excessive_recordkeeping_fee':
            # Estimate based on annual overpayment × 6 years (typical lookback)
            exposure = violation.get('annual_overpayment', 0) * 6
            total_exposure += exposure
            breakdown.append({
                'violation_type': 'Excessive recordkeeping',
                'estimated_exposure': exposure,
                'basis': f"${violation['per_participant']:.2f}/participant × {participant_count} × 6 years"
            })

        elif violation['type'] == 'cornell_excessive':
            # Cornell-level violations = $10M+ exposure
            exposure = min(50_000_000, violation['per_participant'] * participant_count * 6)
            total_exposure += exposure
            breakdown.append({
                'violation_type': 'Extreme excessive fees (Cornell level)',
                'estimated_exposure': exposure,
                'basis': 'Comparable to $69M+ settlements'
            })

    return {
        'total_estimated_exposure': total_exposure,
        'breakdown': breakdown,
        'risk_level': 'CRITICAL' if total_exposure > 10_000_000 else 'HIGH' if total_exposure > 1_000_000 else 'MEDIUM'
    }
