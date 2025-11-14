#!/usr/bin/env python3
"""
COLA II NLP Analyzer - Fuzzy Matching and Obfuscation Detection
Catches variations, misspellings, and intentionally vague language in messy real-world documents
"""

import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass


@dataclass
class FuzzyMatch:
    """Result of fuzzy pattern matching"""
    pattern: str
    matched_text: str
    score: int  # 0-100
    start_pos: int
    end_pos: int
    context: str


@dataclass
class ObfuscationDetection:
    """Detected obfuscation tactic"""
    tactic_type: str
    evidence: str
    severity: str
    explanation: str
    page_no: int = 0


class FuzzyMatcher:
    """
    Fuzzy pattern matching for messy real-world language

    Catches:
    - "revenue sharing" / "revenue-sharing" / "rev share" / "revshare"
    - "float income" / "floating income" / "float proceeds"
    - "basis points" / "bps" / "b.p.s." / "basis pts"
    - Misspellings and variations
    """

    @staticmethod
    def similarity_score(s1: str, s2: str) -> int:
        """
        Calculate similarity score (0-100) using Levenshtein-like algorithm

        100 = exact match
        80+ = very similar (likely same concept)
        60-79 = similar (review manually)
        <60 = different
        """
        s1, s2 = s1.lower(), s2.lower()

        if s1 == s2:
            return 100

        # Normalize spacing and punctuation
        s1 = re.sub(r'[^\w\s]', '', s1)
        s2 = re.sub(r'[^\w\s]', '', s2)
        s1 = re.sub(r'\s+', ' ', s1).strip()
        s2 = re.sub(r'\s+', ' ', s2).strip()

        if s1 == s2:
            return 100

        # Check for abbreviations
        if FuzzyMatcher._is_abbreviation(s1, s2) or FuzzyMatcher._is_abbreviation(s2, s1):
            return 90

        # Simple Levenshtein distance
        distance = FuzzyMatcher._levenshtein_distance(s1, s2)
        max_len = max(len(s1), len(s2))

        if max_len == 0:
            return 100

        similarity = (1 - distance / max_len) * 100
        return int(similarity)

    @staticmethod
    def _levenshtein_distance(s1: str, s2: str) -> int:
        """Calculate Levenshtein distance"""
        if len(s1) < len(s2):
            return FuzzyMatcher._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # Cost of insertions, deletions, or substitutions
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    @staticmethod
    def _is_abbreviation(short: str, long: str) -> bool:
        """Check if short is an abbreviation of long"""
        if len(short) >= len(long):
            return False

        # Extract first letters of words in long string
        words = long.split()
        abbrev = ''.join(w[0] for w in words if w)

        return short.replace('.', '').replace(' ', '') == abbrev

    def fuzzy_search(self,
                    text: str,
                    pattern: str,
                    threshold: int = 80) -> List[FuzzyMatch]:
        """
        Find fuzzy matches for pattern in text

        Uses sliding window approach to find similar phrases
        """
        matches = []
        words = text.split()
        pattern_words = pattern.split()
        pattern_len = len(pattern_words)

        for i in range(len(words) - pattern_len + 1):
            window = ' '.join(words[i:i + pattern_len])
            score = self.similarity_score(window, pattern)

            if score >= threshold:
                # Find position in original text
                start_pos = text.find(window)
                if start_pos != -1:
                    matches.append(FuzzyMatch(
                        pattern=pattern,
                        matched_text=window,
                        score=score,
                        start_pos=start_pos,
                        end_pos=start_pos + len(window),
                        context=self._get_context(text, start_pos, start_pos + len(window))
                    ))

        return matches

    def _get_context(self, text: str, start: int, end: int, window: int = 100) -> str:
        """Extract context around match"""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end]


class ObfuscationDetector:
    """
    Detect intentionally vague or misleading language

    Tactics to detect:
    1. Passive voice (hides responsibility)
    2. Vague quantifiers ("reasonable", "competitive", "standard")
    3. Conditional language ("may", "could", "might")
    4. Missing subjects ("fees may be charged" - by whom?)
    5. Undefined terms without explanation
    6. Excessive jargon
    7. Contradictory statements
    """

    VAGUE_QUANTIFIERS = [
        'reasonable', 'competitive', 'standard', 'typical', 'normal',
        'customary', 'prevailing', 'market', 'industry standard',
        'usual', 'appropriate', 'adequate', 'sufficient'
    ]

    CONDITIONAL_LANGUAGE = [
        'may', 'might', 'could', 'possibly', 'potentially',
        'at times', 'in some cases', 'depending on', 'subject to'
    ]

    EVASIVE_PHRASES = [
        'among other things', 'including but not limited to',
        'various', 'certain', 'some', 'miscellaneous',
        'other fees', 'additional charges', 'from time to time'
    ]

    def detect_passive_voice(self, text: str) -> List[ObfuscationDetection]:
        """
        Detect passive voice that hides responsibility

        Example: "Fees are charged" (by whom?)
        Better: "Fidelity charges fees"
        """
        passive_patterns = [
            r'\b(?:is|are|was|were|be|been|being)\s+\w+ed\b',
            r'\bfees?\s+(?:are|were|will\s+be)\s+charged\b',
            r'\b(?:may|might|could)\s+be\s+\w+ed\b'
        ]

        detections = []
        for pattern in passive_patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if len(matches) > 5:  # Only flag if excessive
                detections.append(ObfuscationDetection(
                    tactic_type='excessive_passive_voice',
                    evidence=f'Found {len(matches)} instances of passive voice',
                    severity='medium',
                    explanation='Passive voice hides WHO is taking action or receiving fees'
                ))

        return detections

    def detect_vague_quantifiers(self, text: str) -> List[ObfuscationDetection]:
        """
        Detect vague terms like "reasonable fees" without specific amounts

        This is inadequate disclosure per 408(b)(2)
        """
        detections = []

        for quantifier in self.VAGUE_QUANTIFIERS:
            pattern = rf'\b{re.escape(quantifier)}\b'
            matches = list(re.finditer(pattern, text, re.IGNORECASE))

            for match in matches:
                # Check if there's a specific amount nearby
                context = text[max(0, match.start() - 100):min(len(text), match.end() + 100)]
                has_amount = bool(re.search(r'\$[\d,]+|[\d.]+%|[\d.]+\s*(?:bps|basis)', context))

                if not has_amount:
                    detections.append(ObfuscationDetection(
                        tactic_type='vague_quantifier_no_amount',
                        evidence=f'"{match.group(0)}" without specific amount',
                        severity='high',
                        explanation=f'Term "{quantifier}" is undefined - must provide specific amounts per 408(b)(2)'
                    ))

        return detections

    def detect_conditional_language(self, text: str) -> List[ObfuscationDetection]:
        """
        Detect conditional language that creates disclosure loopholes

        Example: "Fees may include..." (may or may not? Must disclose ALL)
        """
        detections = []

        for conditional in self.CONDITIONAL_LANGUAGE:
            pattern = rf'\b{re.escape(conditional)}\s+(?:include|receive|be|charge)'
            matches = list(re.finditer(pattern, text, re.IGNORECASE))

            if matches:
                detections.append(ObfuscationDetection(
                    tactic_type='conditional_disclosure',
                    evidence=f'Found {len(matches)} uses of conditional "{conditional}"',
                    severity='high',
                    explanation='Conditional language creates incomplete disclosure - must state what WILL happen, not what MAY happen'
                ))

        return detections

    def detect_evasive_phrases(self, text: str) -> List[ObfuscationDetection]:
        """
        Detect phrases that evade complete disclosure

        "Among other things" = admission of incomplete disclosure
        """
        detections = []

        for phrase in self.EVASIVE_PHRASES:
            pattern = rf'\b{re.escape(phrase)}\b'
            matches = list(re.finditer(pattern, text, re.IGNORECASE))

            if matches:
                detections.append(ObfuscationDetection(
                    tactic_type='evasive_phrase',
                    evidence=f'"{phrase}" used {len(matches)} times',
                    severity='high',
                    explanation=f'Phrase "{phrase}" signals incomplete disclosure - 408(b)(2) requires ALL compensation disclosed'
                ))

        return detections

    def detect_missing_subjects(self, text: str) -> List[ObfuscationDetection]:
        """
        Detect sentences missing clear subjects

        Example: "May receive compensation" (who receives it?)
        """
        missing_subject_patterns = [
            r'(?:^|\.\s+)(?:May|Could|Might)\s+(?:receive|charge|include)',
            r'(?:^|\.\s+)(?:Is|Are|Will\s+be)\s+(?:charged|paid|received)',
        ]

        detections = []
        for pattern in missing_subject_patterns:
            matches = list(re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE))
            if matches:
                detections.append(ObfuscationDetection(
                    tactic_type='missing_subject',
                    evidence=f'Found {len(matches)} sentences without clear subjects',
                    severity='medium',
                    explanation='Sentences must clearly identify WHO receives fees or performs actions'
                ))

        return detections

    def detect_all_obfuscation(self, text: str) -> List[ObfuscationDetection]:
        """Run all obfuscation checks"""
        detections = []

        detections.extend(self.detect_passive_voice(text))
        detections.extend(self.detect_vague_quantifiers(text))
        detections.extend(self.detect_conditional_language(text))
        detections.extend(self.detect_evasive_phrases(text))
        detections.extend(self.detect_missing_subjects(text))

        return detections


class EntityExtractor:
    """
    Extract key entities from text:
    - Service provider names
    - Fee amounts
    - Relationships between entities
    """

    @staticmethod
    def extract_money_amounts(text: str) -> List[Tuple[float, str]]:
        """Extract all monetary amounts"""
        amounts = []

        # Dollar amounts
        pattern = r'\$\s*([\d,]+(?:\.\d{2})?)'
        for match in re.finditer(pattern, text):
            amount_str = match.group(1).replace(',', '')
            try:
                amounts.append((float(amount_str), match.group(0)))
            except ValueError:
                pass

        return amounts

    @staticmethod
    def extract_percentages(text: str) -> List[Tuple[float, str]]:
        """Extract all percentages"""
        percentages = []

        pattern = r'([\d.]+)\s*%'
        for match in re.finditer(pattern, text):
            try:
                percentages.append((float(match.group(1)), match.group(0)))
            except ValueError:
                pass

        return percentages

    @staticmethod
    def extract_basis_points(text: str) -> List[Tuple[float, str]]:
        """Extract basis points"""
        bps = []

        pattern = r'([\d.]+)\s*(?:basis\s+points?|bps?)\b'
        for match in re.finditer(pattern, text, re.IGNORECASE):
            try:
                bps.append((float(match.group(1)), match.group(0)))
            except ValueError:
                pass

        return bps

    @staticmethod
    def extract_organizations(text: str) -> List[str]:
        """
        Extract organization names (simple pattern-based)

        Looks for:
        - Capitalized phrases
        - Known provider types (Fidelity, Vanguard, etc.)
        - Words like "Inc", "LLC", "Corp"
        """
        orgs = []

        # Look for capitalized consecutive words
        pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Inc|LLC|Corp|LP|LLP|Company|Group)\.?))\b'
        matches = re.findall(pattern, text)
        orgs.extend(matches)

        return list(set(orgs))  # Remove duplicates


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def analyze_document_language(text: str) -> Dict[str, Any]:
    """
    Complete NLP analysis of document

    Returns:
    - Fuzzy matches for key violation terms
    - Obfuscation detections
    - Extracted entities
    """
    fuzzy_matcher = FuzzyMatcher()
    obfuscation_detector = ObfuscationDetector()
    entity_extractor = EntityExtractor()

    # Key terms to fuzzy match
    key_terms = [
        'revenue sharing',
        'float income',
        'basis points',
        'indirect compensation',
        'party in interest',
        'fiduciary',
        'prohibited transaction'
    ]

    fuzzy_matches = {}
    for term in key_terms:
        matches = fuzzy_matcher.fuzzy_search(text, term, threshold=80)
        if matches:
            fuzzy_matches[term] = [
                {
                    'matched_text': m.matched_text,
                    'score': m.score,
                    'context': m.context[:100]
                }
                for m in matches[:5]  # Top 5 matches
            ]

    # Detect obfuscation
    obfuscations = obfuscation_detector.detect_all_obfuscation(text)

    # Extract entities
    money = entity_extractor.extract_money_amounts(text)
    percentages = entity_extractor.extract_percentages(text)
    basis_points = entity_extractor.extract_basis_points(text)
    organizations = entity_extractor.extract_organizations(text)

    return {
        'fuzzy_matches': fuzzy_matches,
        'obfuscation_detections': [
            {
                'type': o.tactic_type,
                'evidence': o.evidence,
                'severity': o.severity,
                'explanation': o.explanation
            }
            for o in obfuscations
        ],
        'extracted_entities': {
            'money_amounts': len(money),
            'percentages': len(percentages),
            'basis_points': len(basis_points),
            'organizations': organizations[:10]  # Top 10
        }
    }
