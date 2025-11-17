#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COLA II v3 FINAL - PDF Compliance Report Generator
Generates professional 10-page compliance reports
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether
)
from reportlab.pdfgen import canvas
from datetime import datetime
from typing import Dict, Any, List
import os


# ============================================================================
# HEADER/FOOTER
# ============================================================================

class NumberedCanvas(canvas.Canvas):
    """Custom canvas with header/footer"""
    
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self.pages = []
        
    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()
        
    def save(self):
        page_count = len(self.pages)
        for page_num, page_dict in enumerate(self.pages, 1):
            self.__dict__.update(page_dict)
            self.draw_page_decorations(page_num, page_count)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)
        
    def draw_page_decorations(self, page_num, page_count):
        """Draw header and footer"""
        page_width, page_height = letter
        
        # Header - Left
        self.setFont("Helvetica-Bold", 10)
        self.setFillColor(colors.HexColor("#1a1a1a"))
        self.drawString(0.75 * inch, page_height - 0.5 * inch, "COLA II")
        
        # Header - Right
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#666666"))
        self.drawRightString(page_width - 0.75 * inch, page_height - 0.5 * inch, 
                            "CONFIDENTIAL - ATTORNEY WORK PRODUCT")
        
        # Footer - Left
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#666666"))
        self.drawString(0.75 * inch, 0.5 * inch, 
                       f"Generated {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
        
        # Footer - Center
        self.drawCentredString(page_width / 2, 0.5 * inch, 
                              f"Page {page_num} of {page_count}")
        
        # Footer - Right
        self.drawRightString(page_width - 0.75 * inch, 0.5 * inch, 
                            "COLA II™ Report")


# ============================================================================
# STYLES
# ============================================================================

def get_custom_styles():
    """Create custom paragraph styles"""
    styles = getSampleStyleSheet()
    
    # Title
    styles.add(ParagraphStyle(
        name='CustomTitle',
        parent=styles['Title'],
        fontSize=28,
        textColor=colors.HexColor("#1a1a1a"),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    ))
    
    # Subtitle
    styles.add(ParagraphStyle(
        name='CustomSubtitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.HexColor("#666666"),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica'
    ))
    
    # Section Header
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor("#1a1a1a"),
        spaceAfter=12,
        spaceBefore=20,
        fontName='Helvetica-Bold',
        borderWidth=0,
        borderColor=colors.HexColor("#DAA520"),
        borderPadding=5
    ))
    
    # Finding Header
    styles.add(ParagraphStyle(
        name='FindingHeader',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor("#1a1a1a"),
        spaceAfter=6,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    ))
    
    # Body
    styles.add(ParagraphStyle(
        name='CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor("#333333"),
        spaceAfter=12,
        alignment=TA_JUSTIFY,
        fontName='Helvetica'
    ))
    
    # Small Text
    styles.add(ParagraphStyle(
        name='SmallText',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor("#666666"),
        spaceAfter=6,
        fontName='Helvetica'
    ))
    
    return styles


# ============================================================================
# REPORT SECTIONS
# ============================================================================

def create_cover_page(findings_data: Dict[str, Any], styles) -> List:
    """Create cover page"""
    elements = []
    
    # Spacer
    elements.append(Spacer(1, 2 * inch))
    
    # Title
    elements.append(Paragraph("COLA II", styles['CustomTitle']))
    
    # Gold bars
    gold_bars_data = [['■', '■', '■', '■', '■']]
    gold_bars_table = Table(gold_bars_data, colWidths=[0.3*inch]*5)
    gold_bars_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#DAA520")),
        ('FONTSIZE', (0, 0), (-1, -1), 20),
    ]))
    elements.append(gold_bars_table)
    elements.append(Spacer(1, 0.3 * inch))
    
    # Subtitle
    elements.append(Paragraph("ERISA COMPLIANCE ANALYSIS", styles['CustomSubtitle']))
    elements.append(Spacer(1, 0.5 * inch))
    
    # Info table
    info_data = [
        ['Document Analyzed', findings_data.get('document', 'N/A')],
        ['Analysis Date', datetime.now().strftime('%B %d, %Y')],
        ['Report Time', datetime.now().strftime('%I:%M %p')],
        ['Generated By', 'COLA II Internal Intelligence System'],
        ['Report Type', '408(b)(2) Fee Disclosure Compliance'],
        ['Classification', 'CONFIDENTIAL - ATTORNEY WORK PRODUCT']
    ]
    
    info_table = Table(info_data, colWidths=[2.5*inch, 3.5*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#1a1a1a")),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
        ('BACKGROUND', (1, 0), (1, -1), colors.HexColor("#f5f5f5")),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor("#333333")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 1 * inch))
    
    # Confidentiality notice
    notice = """
    <b>CONFIDENTIALITY NOTICE:</b> This report contains confidential attorney work product prepared in 
    anticipation of litigation. It is protected by attorney-client privilege and work product doctrine. 
    Unauthorized disclosure may waive privilege protections.
    """
    
    notice_para = Paragraph(notice, styles['SmallText'])
    notice_box = Table([[notice_para]], colWidths=[6*inch])
    notice_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#fff8dc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#DAA520")),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    
    elements.append(notice_box)
    elements.append(PageBreak())
    
    return elements


def create_executive_summary(findings_data: Dict[str, Any], styles) -> List:
    """Create executive summary"""
    elements = []
    
    summary = findings_data.get('summary', {})
    total = summary.get('total_findings', 0)
    high_severity = summary.get('high_severity_count', 0)
    lawsuit_risk = summary.get('lawsuit_risk_score', 0)
    
    # Header
    elements.append(Paragraph("EXECUTIVE SUMMARY", styles['SectionHeader']))
    
    # Intro text
    intro = f"""
    This report presents findings from an automated ERISA compliance analysis conducted by COLA II 
    (Compliance Operations and Legal Analysis - Internal Intelligence) on the referenced 408(b)(2) fee 
    disclosure document. The analysis employed advanced pattern recognition and regulatory 
    cross-referencing to identify potential compliance issues.
    """
    elements.append(Paragraph(intro, styles['CustomBody']))
    elements.append(Spacer(1, 0.2 * inch))
    
    # Risk box
    risk_level = "HIGH RISK" if lawsuit_risk >= 70 else "MEDIUM RISK" if lawsuit_risk >= 50 else "LOW RISK"
    risk_color = colors.HexColor("#dc3545") if lawsuit_risk >= 70 else colors.HexColor("#ffc107") if lawsuit_risk >= 50 else colors.HexColor("#28a745")
    
    risk_data = [[
        Paragraph(f"<b>{risk_level}</b>", styles['CustomBody']),
        Paragraph(f"<b>{total}</b><br/>Total Findings", styles['CustomBody']),
        Paragraph(f"<b>{high_severity}</b><br/>High Severity", styles['CustomBody']),
        Paragraph(f"<b>{lawsuit_risk}/100</b><br/>Lawsuit Risk", styles['CustomBody'])
    ]]
    
    risk_table = Table(risk_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    risk_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), risk_color),
        ('BACKGROUND', (1, 0), (-1, 0), colors.HexColor("#f8f9fa")),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#dee2e6")),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    
    elements.append(risk_table)
    elements.append(Spacer(1, 0.3 * inch))
    
    # Recommendation
    if lawsuit_risk >= 70:
        recommendation = """
        <b>Immediate legal review is strongly recommended.</b> This disclosure contains multiple high-severity 
        compliance issues that may expose the plan to DOL enforcement action and participant litigation. 
        Fiduciary committee should convene within 7 days to address findings.
        """
    elif lawsuit_risk >= 50:
        recommendation = """
        <b>Legal review recommended.</b> This disclosure contains compliance issues that should be addressed 
        to reduce fiduciary risk.
        """
    else:
        recommendation = """
        <b>Standard monitoring recommended.</b> Continue regular oversight of service provider disclosures.
        """
    
    elements.append(Paragraph(recommendation, styles['CustomBody']))
    elements.append(Spacer(1, 0.3 * inch))
    
    # Findings breakdown
    by_category = summary.get('by_category', {})
    by_severity = summary.get('by_severity', {})
    
    # Category table
    elements.append(Paragraph("<b>FINDINGS BY CATEGORY</b>", styles['FindingHeader']))
    
    category_data = [['Category', 'Count']]
    for cat, count in by_category.items():
        category_data.append([cat.replace('_', ' ').title(), str(count)])
    
    if len(category_data) > 1:
        category_table = Table(category_data, colWidths=[4*inch, 2*inch])
        category_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1a1a1a")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(category_table)
    
    elements.append(Spacer(1, 0.3 * inch))
    
    # Severity table
    elements.append(Paragraph("<b>FINDINGS BY SEVERITY</b>", styles['FindingHeader']))
    
    severity_data = [['Severity', 'Count']]
    for sev, count in by_severity.items():
        severity_data.append([sev.upper(), str(count)])
    
    if len(severity_data) > 1:
        severity_table = Table(severity_data, colWidths=[4*inch, 2*inch])
        severity_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1a1a1a")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(severity_table)
    
    elements.append(PageBreak())
    
    return elements


def create_detailed_findings(findings_data: Dict[str, Any], styles) -> List:
    """Create detailed findings section"""
    elements = []
    
    findings = findings_data.get('findings', [])
    
    if not findings:
        elements.append(Paragraph("DETAILED FINDINGS", styles['SectionHeader']))
        elements.append(Paragraph("No findings to report.", styles['CustomBody']))
        elements.append(PageBreak())
        return elements
    
    # Header
    elements.append(Paragraph("DETAILED FINDINGS", styles['SectionHeader']))
    
    intro = """
    The following section presents detailed findings identified during the automated compliance analysis. 
    Each finding includes the severity classification, confidence level, supporting evidence, and regulatory 
    analysis. Findings are ordered by severity and confidence to prioritize review efforts.
    """
    elements.append(Paragraph(intro, styles['CustomBody']))
    elements.append(Spacer(1, 0.2 * inch))
    
    # Group by severity
    high_findings = [f for f in findings if f.get('severity') in ['prohibited_transaction', 'critical', 'high']]
    medium_findings = [f for f in findings if f.get('severity') == 'medium']
    low_findings = [f for f in findings if f.get('severity') == 'low']
    
    # High severity findings
    if high_findings:
        elements.append(Paragraph(f"HIGH SEVERITY FINDINGS ({len(high_findings)} issues)", styles['SectionHeader']))
        
        for idx, finding in enumerate(high_findings[:10], 1):  # Limit to 10 for space
            elements.extend(create_finding_box(finding, idx, styles))
    
    # Medium severity findings
    if medium_findings:
        elements.append(PageBreak())
        elements.append(Paragraph(f"MEDIUM SEVERITY FINDINGS ({len(medium_findings)} issues)", styles['SectionHeader']))
        
        for idx, finding in enumerate(medium_findings[:10], 1):
            elements.extend(create_finding_box(finding, idx, styles))
    
    return elements


def create_finding_box(finding: Dict[str, Any], idx: int, styles) -> List:
    """Create a single finding box"""
    elements = []
    
    # Header
    header_text = f"Finding #{idx} - {finding.get('category', 'Unknown').replace('_', ' ').title()} - " \
                  f"{finding.get('severity', 'unknown').upper()} - " \
                  f"{int(finding.get('confidence', 0) * 100)}% Confidence"
    
    elements.append(Paragraph(header_text, styles['FindingHeader']))
    
    # Details table
    details = [
        ['Location:', f"Page {finding.get('citations', [{}])[0].get('page_no', 'N/A')}"],
        ['Decision:', finding.get('decision', 'Unknown')],
        ['Issue Type:', finding.get('category', 'Unknown').replace('_', ' ').title()]
    ]
    
    details_table = Table(details, colWidths=[1.5*inch, 4.5*inch])
    details_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    
    elements.append(details_table)
    elements.append(Spacer(1, 0.1 * inch))
    
    # Analysis
    analysis = finding.get('llm_analysis', 'No analysis available.')
    elements.append(Paragraph(f"<b>Analysis:</b> {analysis}", styles['CustomBody']))
    
    # Citation
    citations = finding.get('citations', [])
    if citations and citations[0].get('excerpt'):
        excerpt = citations[0]['excerpt'][:150] + "..." if len(citations[0]['excerpt']) > 150 else citations[0]['excerpt']
        elements.append(Paragraph(f"<i>\"{excerpt}\"</i>", styles['SmallText']))
    
    # Lawsuit precedent
    if finding.get('lawsuit_precedent'):
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph(f"<b>Lawsuit Precedent:</b> {finding['lawsuit_precedent']}", styles['SmallText']))
    
    elements.append(Spacer(1, 0.2 * inch))
    
    return elements


def create_recommendations(findings_data: Dict[str, Any], styles) -> List:
    """Create recommendations section"""
    elements = []
    
    lawsuit_risk = findings_data.get('summary', {}).get('lawsuit_risk_score', 0)
    
    elements.append(PageBreak())
    elements.append(Paragraph("RECOMMENDATIONS & NEXT STEPS", styles['SectionHeader']))
    
    intro = """
    Based on the findings documented in this report, COLA II recommends the following course of action to 
    address identified compliance issues and maintain prudent fiduciary process:
    """
    elements.append(Paragraph(intro, styles['CustomBody']))
    elements.append(Spacer(1, 0.2 * inch))
    
    # Immediate actions
    elements.append(Paragraph("1. IMMEDIATE ACTIONS (0-7 Days)", styles['FindingHeader']))
    
    if lawsuit_risk >= 70:
        immediate = """
        <b>URGENT:</b> Multiple high-severity issues require immediate attention.<br/><br/>
        - <b>Convene Fiduciary Committee:</b> Schedule emergency meeting within 7 days<br/>
        - <b>Engage ERISA Counsel:</b> Retain qualified attorney to review findings<br/>
        - <b>Document Review:</b> Pull complete service provider file<br/>
        - <b>Preserve Records:</b> Implement litigation hold on all related documents<br/>
        - <b>Assess DOL Risk:</b> Evaluate likelihood of DOL inquiry
        """
    else:
        immediate = """
        - Review all findings with fiduciary committee<br/>
        - Document review process in minutes<br/>
        - Consult with ERISA counsel as appropriate
        """
    
    elements.append(Paragraph(immediate, styles['CustomBody']))
    elements.append(Spacer(1, 0.2 * inch))
    
    # Short-term actions
    elements.append(Paragraph("2. SHORT-TERM ACTIONS (30 Days)", styles['FindingHeader']))
    
    shortterm = """
    - <b>Request Amended Disclosures:</b> Work with service provider to obtain corrected disclosures<br/>
    - <b>Fee Benchmarking:</b> Conduct independent fee analysis<br/>
    - <b>Conflict Documentation:</b> Document all conflicts of interest<br/>
    - <b>Alternative Evaluation:</b> Begin evaluation of alternative service providers if needed<br/>
    - <b>Remediation Plan:</b> Develop specific plan for each finding
    """
    
    elements.append(Paragraph(shortterm, styles['CustomBody']))
    elements.append(Spacer(1, 0.2 * inch))
    
    # Long-term actions
    elements.append(Paragraph("3. LONG-TERM ACTIONS (90+ Days)", styles['FindingHeader']))
    
    longterm = """
    - <b>Quarterly Monitoring:</b> Implement quarterly review process using COLA II<br/>
    - <b>RFP Process:</b> Establish regular RFP cycle (every 3-5 years)<br/>
    - <b>Fiduciary Training:</b> Provide ERISA training to committee members<br/>
    - <b>Compliance Calendar:</b> Track disclosure receipt dates and deadlines<br/>
    - <b>Vendor Management:</b> Develop formal vendor management framework
    """
    
    elements.append(Paragraph(longterm, styles['CustomBody']))
    
    return elements


def create_disclaimer(styles) -> List:
    """Create disclaimer section"""
    elements = []
    
    elements.append(PageBreak())
    elements.append(Paragraph("METHODOLOGY & DISCLAIMER", styles['SectionHeader']))
    
    methodology = """
    <b>Analysis Methodology:</b><br/><br/>
    This report was generated by COLA II (Compliance Operations and Legal Analysis - Internal Intelligence), 
    an advanced automated compliance analysis system developed specifically for ERISA 408(b)(2) fee disclosure 
    review. The system employs multi-stage pattern recognition to identify potential compliance issues, including:<br/><br/>
    
    1. Document Processing: PDF parsing and text extraction<br/>
    2. Keyword Detection: 70+ regulatory term patterns from actual lawsuits<br/>
    3. Context Analysis: Pattern evaluation for regulatory significance<br/>
    4. Citation Extraction: Precise location identification<br/>
    5. Confidence Scoring: Statistical calculation based on pattern strength<br/>
    6. Severity Classification: Risk-based categorization<br/><br/>
    
    <b>Limitations:</b><br/><br/>
    Automated analysis is designed to assist, not replace, qualified legal review. Pattern matching may 
    produce false positives or miss contextual factors. All findings should be validated by experienced 
    ERISA counsel before taking action.<br/><br/>
    
    <b>IMPORTANT LEGAL DISCLAIMER:</b><br/><br/>
    
    <b>Not Legal Advice:</b> This report does not constitute legal advice. It is intended solely to assist 
    qualified legal counsel in identifying areas warranting further investigation.<br/><br/>
    
    <b>Attorney Work Product:</b> This document is prepared in anticipation of litigation and constitutes 
    attorney work product protected under Federal Rule of Civil Procedure 26(b)(3).<br/><br/>
    
    <b>Privilege and Confidentiality:</b> This report is protected by attorney-client privilege and work 
    product doctrine. Unauthorized disclosure may waive privilege protections.<br/><br/>
    
    <b>No Warranty:</b> While COLA II employs sophisticated analysis techniques, automated systems cannot 
    replicate the judgment and expertise of qualified ERISA counsel.<br/><br/>
    
    <b>Validation Required:</b> All findings must be validated through independent legal review before 
    taking any action.<br/><br/>
    
    <b>Report Generation:</b> {datetime}
    """.format(datetime=datetime.now().strftime("%B %d, %Y at %I:%M %p"))
    
    elements.append(Paragraph(methodology, styles['CustomBody']))
    
    return elements


# ============================================================================
# MAIN GENERATOR
# ============================================================================

def generate_compliance_report(findings_data: Dict[str, Any], output_path: str):
    """Generate complete PDF compliance report"""
    
    # Create document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=1*inch,
        bottomMargin=0.75*inch
    )
    
    # Get styles
    styles = get_custom_styles()
    
    # Build content
    content = []
    
    # Cover page
    content.extend(create_cover_page(findings_data, styles))
    
    # Executive summary
    content.extend(create_executive_summary(findings_data, styles))
    
    # Detailed findings
    content.extend(create_detailed_findings(findings_data, styles))
    
    # Recommendations
    content.extend(create_recommendations(findings_data, styles))
    
    # Disclaimer
    content.extend(create_disclaimer(styles))
    
    # Build PDF with custom canvas
    doc.build(content, canvasmaker=NumberedCanvas)
    
    print(f"✅ PDF Report Generated: {output_path}")


# ============================================================================
# MAIN (for testing)
# ============================================================================

if __name__ == '__main__':
    # Test data
    test_data = {
        "document": "test_disclosure.pdf",
        "pages": 10,
        "summary": {
            "total_findings": 12,
            "high_severity_count": 8,
            "lawsuit_risk_score": 75,
            "by_category": {
                "hidden_fees": 5,
                "conflicts": 3,
                "float": 2,
                "missing_basics": 2
            },
            "by_severity": {
                "high": 8,
                "medium": 3,
                "low": 1
            }
        },
        "findings": [
            {
                "category": "hidden_fees",
                "severity": "high",
                "confidence": 0.85,
                "decision": "present",
                "citations": [{"page_no": 1, "excerpt": "Revenue sharing arrangements..."}],
                "llm_analysis": "Hidden fee detected requiring disclosure",
                "lawsuit_precedent": "Tussey v. ABB - Revenue sharing must be fully disclosed"
            }
        ]
    }
    
    generate_compliance_report(test_data, "test_report.pdf")
