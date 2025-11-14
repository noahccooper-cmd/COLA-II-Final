#!/usr/bin/env python3
"""
COLA II Precedent Scorer - Legal Precedent-Based Confidence Scoring
Adjusts finding confidence based on strength of supporting court precedents
"""

import json
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass


class PrecedentStrength(Enum):
    """Legal precedent strength classifications"""
    SUPREME_COURT = "supreme_court"  # Binding nationwide
    CIRCUIT_AFFIRMED = "circuit_affirmed"  # Strong regional precedent
    CIRCUIT_SPLIT = "circuit_split"  # Legal uncertainty
    DISTRICT_SETTLED_50M_PLUS = "district_settled_50m_plus"  # Strong settlement
    DISTRICT_SETTLED_10M_PLUS = "district_settled_10m_plus"  # Significant settlement
    DISTRICT_SETTLED = "district_settled"  # Settlement evidence
    DISTRICT_DISMISSED = "district_dismissed"  # Weak claim
    NOVEL_THEORY = "novel_theory"  # Untested in courts
    PENDING_LITIGATION = "pending_litigation"  # Outcome uncertain


@dataclass
class LegalPrecedent:
    """Legal case precedent"""
    case_id: str
    case_name: str
    year: int
    settlement_value: Optional[int]
    court_level: str  # 'supreme', 'circuit', 'district'
    precedent_strength: PrecedentStrength
    key_holdings: List[str]
    violation_types: List[str]
    outcome: str  # 'settled', 'judgment_plaintiff', 'judgment_defendant', 'dismissed', 'pending'


class PrecedentScorer:
    """
    Score findings based on legal precedent strength

    Philosophy:
    - Supreme Court ruling = 1.0 confidence boost
    - Circuit split = 0.5 (uncertain law)
    - District dismissed = penalty (weak claim)
    - High settlement value = strong signal
    - Recent cases = more relevant
    """

    # Precedent strength multipliers
    PRECEDENT_WEIGHTS = {
        PrecedentStrength.SUPREME_COURT: 1.0,
        PrecedentStrength.CIRCUIT_AFFIRMED: 0.9,
        PrecedentStrength.DISTRICT_SETTLED_50M_PLUS: 0.85,
        PrecedentStrength.DISTRICT_SETTLED_10M_PLUS: 0.75,
        PrecedentStrength.DISTRICT_SETTLED: 0.65,
        PrecedentStrength.CIRCUIT_SPLIT: 0.5,  # Uncertain
        PrecedentStrength.PENDING_LITIGATION: 0.4,
        PrecedentStrength.NOVEL_THEORY: 0.3,
        PrecedentStrength.DISTRICT_DISMISSED: 0.2,  # Weak
    }

    # Settlement value score multipliers
    SETTLEMENT_TIERS = [
        (100_000_000, 0.25),  # $100M+ = +25% confidence
        (50_000_000, 0.20),   # $50M+ = +20%
        (10_000_000, 0.15),   # $10M+ = +15%
        (1_000_000, 0.10),    # $1M+ = +10%
        (0, 0.05)             # Any settlement = +5%
    ]

    def __init__(self, precedent_database_path: Optional[str] = None):
        """Initialize with optional precedent database"""
        self.precedents = {}
        if precedent_database_path:
            self.load_precedents(precedent_database_path)

    def load_precedents(self, filepath: str):
        """Load precedents from JSON file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                for case in data.get('cases', []):
                    precedent = LegalPrecedent(
                        case_id=case['case_id'],
                        case_name=case['case_name'],
                        year=case['year'],
                        settlement_value=case.get('settlement_value'),
                        court_level=case.get('court_level', 'district'),
                        precedent_strength=PrecedentStrength(case.get('precedent_strength', 'district_settled')),
                        key_holdings=case.get('key_holdings', []),
                        violation_types=case.get('violation_types', []),
                        outcome=case.get('outcome', 'settled')
                    )
                    self.precedents[case['case_id']] = precedent
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load precedents from {filepath}: {e}")

    def score_finding(self,
                     finding_dict: Dict[str, Any],
                     base_confidence: float = 0.75) -> float:
        """
        Score a finding based on legal precedent strength

        Inputs:
        - finding_dict: Finding with lawsuit_precedent, legal_citation, etc.
        - base_confidence: Starting confidence from pattern match

        Returns:
        - Adjusted confidence (0.0-1.0)

        Factors:
        1. Precedent strength (Supreme Court > Circuit > District)
        2. Settlement value (higher = stronger signal)
        3. Legal clarity (vague language = higher risk, so higher confidence in violation)
        4. Recency (more recent = more relevant)
        """

        confidence = base_confidence

        # Factor 1: Precedent strength
        precedent_boost = self._get_precedent_boost(finding_dict)
        confidence += precedent_boost

        # Factor 2: Settlement value
        settlement_boost = self._get_settlement_boost(finding_dict)
        confidence += settlement_boost

        # Factor 3: Vagueness penalty/boost
        vagueness_adjustment = self._get_vagueness_adjustment(finding_dict)
        confidence += vagueness_adjustment

        # Factor 4: Recency bonus
        recency_bonus = self._get_recency_bonus(finding_dict)
        confidence += recency_bonus

        # Cap at 1.0
        return min(1.0, max(0.0, confidence))

    def _get_precedent_boost(self, finding: Dict[str, Any]) -> float:
        """Calculate precedent strength boost"""
        lawsuit_precedent = finding.get('lawsuit_precedent', '')

        # Check for known cases in our database
        for case_id, precedent in self.precedents.items():
            if precedent.case_name.lower() in lawsuit_precedent.lower():
                weight = self.PRECEDENT_WEIGHTS.get(
                    precedent.precedent_strength,
                    0.5
                )
                return weight * 0.2  # Up to +20% for strongest precedents

        # Default boost based on keywords
        if 'supreme court' in lawsuit_precedent.lower():
            return 0.20
        elif 'circuit' in lawsuit_precedent.lower() and 'affirmed' in lawsuit_precedent.lower():
            return 0.18
        elif 'settled' in lawsuit_precedent.lower():
            return 0.13
        elif 'dismissed' in lawsuit_precedent.lower():
            return -0.10  # Penalty for dismissed cases
        else:
            return 0.10  # Generic case reference

    def _get_settlement_boost(self, finding: Dict[str, Any]) -> float:
        """Calculate settlement value boost"""
        lawsuit_precedent = finding.get('lawsuit_precedent', '')

        # Extract settlement amount from text
        settlement = self._extract_settlement_amount(lawsuit_precedent)

        if not settlement:
            return 0.0

        # Find appropriate tier
        for threshold, boost in self.SETTLEMENT_TIERS:
            if settlement >= threshold:
                return boost

        return 0.0

    def _get_vagueness_adjustment(self, finding: Dict[str, Any]) -> float:
        """
        Vague language = violation more likely

        If finding contains vague terms like "reasonable", "may include",
        etc., it's MORE likely to be a violation (inadequate disclosure).
        So we INCREASE confidence.
        """
        subtype = finding.get('subtype', '').lower()
        llm_analysis = finding.get('llm_analysis', '').lower()

        vague_indicators = [
            'vague', 'undefined', 'incomplete', 'obfuscation',
            'may include', 'could', 'reasonable', 'standard'
        ]

        vagueness_count = sum(
            1 for indicator in vague_indicators
            if indicator in subtype or indicator in llm_analysis
        )

        # More vagueness = higher confidence in violation
        return min(0.10, vagueness_count * 0.025)

    def _get_recency_bonus(self, finding: Dict[str, Any]) -> float:
        """More recent cases = more relevant"""
        lawsuit_precedent = finding.get('lawsuit_precedent', '')

        # Extract year
        import re
        year_match = re.search(r'\b(20\d{2}|19\d{2})\b', lawsuit_precedent)

        if year_match:
            year = int(year_match.group(1))

            # 2023-2025 = most recent
            if year >= 2023:
                return 0.05
            # 2020-2022 = recent
            elif year >= 2020:
                return 0.03
            # 2015-2019 = somewhat recent
            elif year >= 2015:
                return 0.01
            # Pre-2015 = older (but still relevant)
            else:
                return 0.0

        return 0.0

    def _extract_settlement_amount(self, text: str) -> Optional[int]:
        """Extract settlement dollar amount from text"""
        import re

        # Look for patterns like "$55M", "$55 million", "$55,000,000"
        patterns = [
            r'\$(\d+(?:\.\d+)?)\s*[Bb]illion',  # $1.5 billion
            r'\$(\d+(?:\.\d+)?)\s*[Mm]illion',  # $55 million
            r'\$(\d+(?:\.\d+)?)[Mm]',  # $55M
            r'\$(\d{1,3}(?:,\d{3})+)',  # $55,000,000
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                amount_str = match.group(1).replace(',', '')
                amount = float(amount_str)

                # Convert to dollars
                if 'billion' in text[match.start():match.end()].lower():
                    return int(amount * 1_000_000_000)
                elif 'million' in text[match.start():match.end()].lower() or 'M' in match.group(0):
                    return int(amount * 1_000_000)
                else:
                    return int(amount)

        return None

    def calculate_litigation_risk_score(self, findings: List[Dict[str, Any]]) -> int:
        """
        Calculate overall litigation risk score (0-100)

        Based on:
        - Number of prohibited transaction findings (weight = 40)
        - Number of critical findings (weight = 30)
        - Total settlement value of matched precedents (weight = 20)
        - Red flag scores (weight = 10)
        """
        score = 0

        prohibited = len([f for f in findings if f.get('severity') == 'prohibited_transaction'])
        critical = len([f for f in findings if f.get('severity') == 'critical'])
        high = len([f for f in findings if f.get('severity') == 'high'])

        # Prohibited transactions (most severe)
        score += min(40, prohibited * 10)

        # Critical violations
        score += min(30, critical * 6)

        # High severity
        score += min(15, high * 3)

        # Total settlement exposure from matched precedents
        total_settlement = sum(
            self._extract_settlement_amount(f.get('lawsuit_precedent', '')) or 0
            for f in findings
        )

        if total_settlement >= 100_000_000:
            score += 20
        elif total_settlement >= 50_000_000:
            score += 15
        elif total_settlement >= 10_000_000:
            score += 10
        elif total_settlement >= 1_000_000:
            score += 5

        # Red flag scores
        total_red_flags = sum(f.get('red_flag_score', 0) for f in findings)
        score += min(10, total_red_flags // 10)

        return min(100, score)

    def generate_precedent_report(self, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate comprehensive precedent analysis report

        Shows:
        - Matched precedents
        - Precedent strength distribution
        - Total settlement exposure
        - Litigation risk score
        """
        matched_cases = set()
        total_settlement = 0

        for finding in findings:
            precedent = finding.get('lawsuit_precedent', '')
            if precedent:
                # Extract case name
                import re
                match = re.search(r'([A-Z][a-z]+\s+v\.\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', precedent)
                if match:
                    matched_cases.add(match.group(1))

                # Extract settlement
                settlement = self._extract_settlement_amount(precedent)
                if settlement:
                    total_settlement += settlement

        litigation_risk = self.calculate_litigation_risk_score(findings)

        risk_level = 'LOW'
        if litigation_risk >= 75:
            risk_level = 'CRITICAL'
        elif litigation_risk >= 50:
            risk_level = 'HIGH'
        elif litigation_risk >= 25:
            risk_level = 'MEDIUM'

        return {
            'litigation_risk_score': litigation_risk,
            'risk_level': risk_level,
            'matched_precedents': list(matched_cases),
            'total_precedent_count': len(matched_cases),
            'estimated_settlement_exposure': f'${total_settlement:,}' if total_settlement > 0 else 'Unknown',
            'findings_breakdown': {
                'prohibited_transactions': len([f for f in findings if f.get('severity') == 'prohibited_transaction']),
                'critical': len([f for f in findings if f.get('severity') == 'critical']),
                'high': len([f for f in findings if f.get('severity') == 'high']),
                'medium': len([f for f in findings if f.get('severity') == 'medium']),
                'low': len([f for f in findings if f.get('severity') == 'low']),
            },
            'top_precedents': [
                {
                    'case': case,
                    'relevance': 'High' if any(case in f.get('lawsuit_precedent', '') for f in findings if f.get('severity') in ['critical', 'prohibited_transaction']) else 'Medium'
                }
                for case in list(matched_cases)[:10]
            ]
        }


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def score_findings_with_precedents(findings: List[Dict[str, Any]],
                                  precedent_db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Score all findings with precedent-adjusted confidence

    Returns new findings list with updated confidence scores
    """
    scorer = PrecedentScorer(precedent_db_path)

    scored_findings = []
    for finding in findings:
        original_confidence = finding.get('confidence', 0.75)
        adjusted_confidence = scorer.score_finding(finding, original_confidence)

        # Create updated finding
        scored_finding = finding.copy()
        scored_finding['confidence'] = adjusted_confidence
        scored_finding['confidence_original'] = original_confidence
        scored_finding['confidence_adjustment'] = adjusted_confidence - original_confidence

        scored_findings.append(scored_finding)

    return scored_findings
