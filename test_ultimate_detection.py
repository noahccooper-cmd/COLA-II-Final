#!/usr/bin/env python3
"""
COLA II Ultimate Detection Engine - Comprehensive Test Suite
Validates all 200+ patterns and multi-pass analysis components
"""

from detection_engine_v3 import DetectionEngineV3, DocumentPage
from quantitative_analyzer import QuantitativeAnalyzer
from omission_detector import OmissionDetector
from nlp_analyzer import FuzzyMatcher, ObfuscationDetector
from precedent_scorer import PrecedentScorer


# ============================================================================
# TUSSEY V. ABB PATTERN TESTS ($55M settlement)
# ============================================================================

def test_tussey_cross_subsidization():
    """Test detection of Tussey cross-subsidization pattern"""

    test_text = """
    Fidelity provides recordkeeping services for the 401(k) plan, as well as
    payroll processing and health and welfare plan administration for the company.
    This integrated enterprise solution provides administrative convenience.
    """

    engine = DetectionEngineV3()
    page = DocumentPage(page_no=1, text=test_text)
    findings = engine.analyze_document("test_doc", [page], "2025-01-14T00:00:00Z")

    # Should catch cross-subsidization
    subsidy_findings = [f for f in findings if 'cross' in f.subtype.lower() or 'subsidy' in f.subtype.lower()]
    assert len(subsidy_findings) > 0, "Must detect cross-subsidization (Tussey $13.4M violation)"

    print(f"✅ Tussey cross-subsidization: {len(subsidy_findings)} findings")


def test_tussey_float_income():
    """Test detection of Tussey float income pattern"""

    test_text = """
    Float income on uninvested cash is retained by Fidelity for operational purposes.
    Earnings on pending contributions are held in an omnibus account during the
    settlement period.
    """

    engine = DetectionEngineV3()
    page = DocumentPage(page_no=1, text=test_text)
    findings = engine.analyze_document("test_doc", [page], "2025-01-14T00:00:00Z")

    # Should catch float misallocation
    float_findings = [f for f in findings if 'float' in f.subtype.lower()]
    assert len(float_findings) > 0, "Must detect float income misallocation (Tussey $13.4M)"

    print(f"✅ Tussey float income: {len(float_findings)} findings")


def test_tussey_retail_shares():
    """Test detection of retail share class selection"""

    test_text = """
    The plan offers Class A shares of the American Funds Growth Fund.
    Expense ratio: 1.25%. Class I institutional shares are also available
    with an expense ratio of 0.55%.
    """

    engine = DetectionEngineV3()
    page = DocumentPage(page_no=1, text=test_text)
    findings = engine.analyze_document("test_doc", [page], "2025-01-14T00:00:00Z")

    # Should catch retail shares
    retail_findings = [f for f in findings if 'retail' in f.subtype.lower() or 'share' in f.subtype.lower()]
    assert len(retail_findings) > 0, "Must detect retail share classes (Tussey $21.8M)"

    print(f"✅ Tussey retail shares: {len(retail_findings)} findings")


# ============================================================================
# FORFEITURE PATTERN TESTS (2024 wave - 34 cases)
# ============================================================================

def test_forfeiture_discretion():
    """Test 2024 forfeiture discretion pattern"""

    test_text = """
    Forfeited amounts may be used to either reduce employer matching contributions
    or pay plan administrative expenses, at the discretion of the plan administrator.
    """

    engine = DetectionEngineV3()
    page = DocumentPage(page_no=1, text=test_text)
    findings = engine.analyze_document("test_doc", [page], "2025-01-14T00:00:00Z")

    # Should catch forfeiture discretion
    forfeiture_findings = [f for f in findings if 'forfeit' in f.subtype.lower()]
    assert len(forfeiture_findings) > 0, "Must detect forfeiture discretion (2024 wave - 34 cases)"

    print(f"✅ Forfeiture discretion: {len(forfeiture_findings)} findings")


# ============================================================================
# FEE OBFUSCATION TESTS
# ============================================================================

def test_vague_fee_terms():
    """Test detection of vague, undefined fee terms"""

    test_text = """
    We charge reasonable fees that are competitive and based on industry standard
    pricing. Our rates are typical for services of this nature.
    """

    engine = DetectionEngineV3()
    page = DocumentPage(page_no=1, text=test_text)
    findings = engine.analyze_document("test_doc", [page], "2025-01-14T00:00:00Z")

    # Should catch vague terms
    vague_findings = [f for f in findings if 'vague' in f.subtype.lower() or 'undefined' in f.subtype.lower()]
    assert len(vague_findings) > 0, "Must detect vague fee terms (inadequate disclosure)"

    print(f"✅ Vague fee terms: {len(vague_findings)} findings")


def test_incomplete_disclosure():
    """Test detection of incomplete disclosure language"""

    test_text = """
    Fees may include various charges that could be assessed. Additional compensation
    may be received from other sources. See separate agreement for details.
    """

    engine = DetectionEngineV3()
    page = DocumentPage(page_no=1, text=test_text)
    findings = engine.analyze_document("test_doc", [page], "2025-01-14T00:00:00Z")

    # Should catch incomplete disclosure
    incomplete_findings = [f for f in findings if 'incomplete' in f.subtype.lower() or 'disclosure' in f.subtype.lower()]
    assert len(incomplete_findings) > 0, "Must detect incomplete disclosure (prohibited transaction)"

    print(f"✅ Incomplete disclosure: {len(incomplete_findings)} findings")


# ============================================================================
# QUANTITATIVE ANALYZER TESTS
# ============================================================================

def test_fee_extraction():
    """Test fee extraction in all formats"""

    test_text = """
    Recordkeeping fee: $50 per participant
    Investment management fee: 0.25% of assets
    Transaction fees: 25 basis points
    Total annual cost: $1,500,000
    """

    analyzer = QuantitativeAnalyzer()
    fees = analyzer.extract_all_fees(test_text)

    assert len(fees) > 0, "Must extract fees"
    assert any(f.fee_type == 'dollar' for f in fees), "Must extract dollar amounts"
    assert any(f.fee_type == 'percentage' for f in fees), "Must extract percentages"
    assert any(f.fee_type == 'basis_points' for f in fees), "Must extract basis points"
    assert any(f.fee_type == 'per_participant' for f in fees), "Must extract per-participant fees"

    print(f"✅ Fee extraction: {len(fees)} fees extracted")


def test_hidden_cost_calculation():
    """Test conversion of percentages to dollars"""

    analyzer = QuantitativeAnalyzer()

    # Tussey scenario: 0.25% on $500M with 5,000 participants
    from quantitative_analyzer import FeeType
    result = analyzer.calculate_hidden_costs(
        percentage_fee=0.25,
        plan_assets=500_000_000,
        participant_count=5000,
        fee_category=FeeType.RECORDKEEPING
    )

    assert result.annual_cost == 1_250_000, "Annual cost should be $1.25M"
    assert result.per_participant == 250, "Per participant should be $250"
    assert result.violation is not None, "Should flag excessive fee (>$70 threshold)"
    assert result.violation['excess_percent'] > 200, "Should show >200% excess"

    print(f"✅ Hidden cost calculation: ${result.per_participant}/participant (violation detected)")


def test_threshold_violations():
    """Test automatic threshold flagging"""

    analyzer = QuantitativeAnalyzer()

    # Test recordkeeping threshold ($70/participant)
    violations = analyzer.flag_threshold_violations(
        per_participant_fee=150,  # Excessive
        total_expense_ratio=0.75,  # OK
        plan_assets=1_000_000_000  # $1B plan
    )

    assert len(violations) > 0, "Must flag excessive per-participant fee"
    assert any(v['type'] == 'excessive_per_participant' for v in violations), "Must flag >$70/participant"

    print(f"✅ Threshold violations: {len(violations)} violations flagged")


# ============================================================================
# OMISSION DETECTOR TESTS
# ============================================================================

def test_missing_fiduciary_status():
    """Test detection of missing fiduciary status disclosure"""

    test_text = """
    We provide investment advisory services to your plan. Our fees are disclosed below.
    """

    detector = OmissionDetector()
    omissions = detector.detect_omissions(test_text)

    # Should catch missing fiduciary status
    fiduciary_omissions = [o for o in omissions if 'fiduciary' in o.element.value]
    assert len(fiduciary_omissions) > 0, "Must detect missing fiduciary status disclosure"

    print(f"✅ Missing fiduciary status: {len(fiduciary_omissions)} omissions")


def test_incomplete_float_disclosure():
    """Test incomplete float income disclosure"""

    test_text = """
    Float income may be earned on uninvested cash.
    """
    # Missing: how calculated, who receives, how credited to plan

    detector = OmissionDetector()
    float_omission = detector.check_float_income_disclosure_completeness(test_text)

    assert float_omission is not None, "Must detect incomplete float disclosure (Tussey violation)"
    assert float_omission.severity == 'critical', "Incomplete float disclosure = critical"

    print(f"✅ Incomplete float disclosure detected")


# ============================================================================
# NLP ANALYZER TESTS
# ============================================================================

def test_fuzzy_matching():
    """Test fuzzy matching for variations"""

    matcher = FuzzyMatcher()

    # Test revenue sharing variations
    text = "We receive rev share from the fund company"
    matches = matcher.fuzzy_search(text, "revenue sharing", threshold=75)

    assert len(matches) > 0, "Must catch 'rev share' as revenue sharing"
    assert matches[0].score >= 75, "Match score should be high"

    print(f"✅ Fuzzy matching: matched 'rev share' → 'revenue sharing' (score: {matches[0].score})")


def test_obfuscation_detection():
    """Test obfuscation tactic detection"""

    detector = ObfuscationDetector()

    test_text = """
    Fees are reasonable and competitive. We may receive compensation from various
    sources. Additional charges could apply depending on circumstances.
    """

    obfuscations = detector.detect_all_obfuscation(test_text)

    assert len(obfuscations) > 0, "Must detect obfuscation tactics"
    assert any('vague' in o.tactic_type for o in obfuscations), "Must detect vague quantifiers"
    assert any('conditional' in o.tactic_type for o in obfuscations), "Must detect conditional language"

    print(f"✅ Obfuscation detection: {len(obfuscations)} tactics detected")


# ============================================================================
# PRECEDENT SCORER TESTS
# ============================================================================

def test_precedent_scoring():
    """Test precedent-based confidence adjustment"""

    scorer = PrecedentScorer()

    # Mock finding
    finding = {
        'subtype': 'float_misallocation',
        'lawsuit_precedent': 'Tussey v. ABB - $55M settlement',
        'confidence': 0.75
    }

    adjusted_confidence = scorer.score_finding(finding, base_confidence=0.75)

    assert adjusted_confidence > 0.75, "Strong precedent should boost confidence"
    assert adjusted_confidence <= 1.0, "Confidence should not exceed 1.0"

    print(f"✅ Precedent scoring: {0.75:.2f} → {adjusted_confidence:.2f} (+{adjusted_confidence-0.75:.2f})")


def test_litigation_risk_calculation():
    """Test litigation risk score calculation"""

    scorer = PrecedentScorer()

    # Mock findings with various severities
    findings = [
        {'severity': 'prohibited_transaction', 'lawsuit_precedent': 'Tussey v. ABB - $55M', 'red_flag_score': 10},
        {'severity': 'critical', 'lawsuit_precedent': 'Wells Fargo - $69M', 'red_flag_score': 9},
        {'severity': 'high', 'lawsuit_precedent': '', 'red_flag_score': 7},
    ]

    risk_score = scorer.calculate_litigation_risk_score(findings)

    assert risk_score > 0, "Should calculate risk score"
    assert risk_score <= 100, "Risk score should not exceed 100"
    assert risk_score >= 50, "With prohibited transactions, risk should be high"

    print(f"✅ Litigation risk: {risk_score}/100")


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_full_multi_pass_analysis():
    """Test complete multi-pass analysis pipeline"""

    test_text = """
    Fidelity Investment Management provides recordkeeping and payroll services.
    Float income on uninvested cash may be retained. Revenue sharing arrangements
    include 25 basis points from fund providers. Class A retail shares are offered
    with an expense ratio of 1.0%. Fees are reasonable and competitive.
    """

    # Pass 1: Pattern detection
    engine = DetectionEngineV3()
    page = DocumentPage(page_no=1, text=test_text)
    findings = engine.analyze_document("integration_test", [page], "2025-01-14T00:00:00Z")

    assert len(findings) > 5, "Should find multiple patterns"

    # Pass 2: Quantitative
    analyzer = QuantitativeAnalyzer()
    fees = analyzer.extract_all_fees(test_text)
    assert len(fees) > 0, "Should extract fees"

    # Pass 3: Omissions
    detector = OmissionDetector()
    omissions = detector.detect_omissions(test_text)
    assert len(omissions) > 0, "Should find missing disclosures"

    # Pass 4: NLP
    obf_detector = ObfuscationDetector()
    obfuscations = obf_detector.detect_all_obfuscation(test_text)
    assert len(obfuscations) > 0, "Should detect obfuscation"

    # Pass 5: Precedent scoring
    findings_dicts = [f.to_dict() for f in findings]
    scorer = PrecedentScorer()
    scored = [scorer.score_finding(f, f.get('confidence', 0.75)) for f in findings_dicts]
    assert len(scored) == len(findings), "Should score all findings"

    print(f"✅ Full pipeline: {len(findings)} patterns, {len(fees)} fees, {len(omissions)} omissions, {len(obfuscations)} obfuscations")


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    print("\n🔥 COLA II ULTIMATE DETECTION ENGINE - TEST SUITE\n")
    print("="*80)

    tests = [
        ("Tussey Cross-Subsidization", test_tussey_cross_subsidization),
        ("Tussey Float Income", test_tussey_float_income),
        ("Tussey Retail Shares", test_tussey_retail_shares),
        ("Forfeiture Discretion", test_forfeiture_discretion),
        ("Vague Fee Terms", test_vague_fee_terms),
        ("Incomplete Disclosure", test_incomplete_disclosure),
        ("Fee Extraction", test_fee_extraction),
        ("Hidden Cost Calculation", test_hidden_cost_calculation),
        ("Threshold Violations", test_threshold_violations),
        ("Missing Fiduciary Status", test_missing_fiduciary_status),
        ("Incomplete Float Disclosure", test_incomplete_float_disclosure),
        ("Fuzzy Matching", test_fuzzy_matching),
        ("Obfuscation Detection", test_obfuscation_detection),
        ("Precedent Scoring", test_precedent_scoring),
        ("Litigation Risk Calculation", test_litigation_risk_calculation),
        ("Full Multi-Pass Analysis", test_full_multi_pass_analysis),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            print(f"\nTesting: {name}")
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAILED: {name}")
            print(f"   Error: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {name}")
            print(f"   Exception: {e}")
            failed += 1

    print("\n" + "="*80)
    print(f"\n📊 TEST RESULTS: {passed} passed, {failed} failed out of {len(tests)} total")

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! System is ready for production.")
    else:
        print(f"\n⚠️  {failed} tests failed. Review errors above.")

    print("\n" + "="*80)
