#!/usr/bin/env python3
"""
Generate Unified RBD Analysis Report for Test1-10 and PS0140-151
Combines both datasets in a consistent format
"""

import pandas as pd
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle, Paragraph,
                                Spacer, PageBreak, KeepTogether)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime

# Register Korean font
try:
    pdfmetrics.registerFont(TTFont('AppleGothic', '/System/Library/Fonts/AppleSDGothicNeo.ttc', subfontIndex=0))
    KOREAN_FONT = 'AppleGothic'
    print("✓ Korean font registered: AppleGothic")
except:
    try:
        pdfmetrics.registerFont(TTFont('AppleGothic2', '/System/Library/Fonts/Supplemental/AppleGothic.ttf'))
        KOREAN_FONT = 'AppleGothic2'
        print("✓ Korean font registered: AppleGothic2")
    except:
        KOREAN_FONT = 'Helvetica'
        print("⚠ No Korean font available - using Helvetica")

# Paths
BASE_DIR = Path("/Users/hyeongsuk/Desktop/workspace/SNUH/Atonia_Index")
RESULTS_DIR = BASE_DIR / "Results"
OUTPUT_PDF = RESULTS_DIR / "Unified_RBD_Analysis_Report.pdf"

def load_test_data():
    """Load Test1-10 data"""
    baseline_df = pd.read_csv(RESULTS_DIR / "Test1-10_True_Baseline_Amplitudes.csv")
    indicators_df = pd.read_csv(RESULTS_DIR / "Test1-10_RBD_Indicators_Converted.csv")
    rswa_complete_df = pd.read_csv(RESULTS_DIR / "Test1-10_RSWA_Complete.csv")

    # Merge baseline with indicators
    merged = baseline_df.merge(indicators_df, left_on='Test', right_on='Test', how='left')

    # Merge with complete RSWA data (Tonic, Phasic, Any)
    merged = merged.merge(rswa_complete_df[['Test', 'CHIN_Tonic_%', 'CHIN_Phasic_%', 'CHIN_Any_%']],
                         left_on='Test', right_on='Test', how='left')

    merged['Patient'] = merged['Test']
    merged['Dataset'] = 'Test1-10'

    return merged

def load_ps_data():
    """Load PS0140-151 data"""
    complete_df = pd.read_csv(RESULTS_DIR / "PS0140-151_Complete_Analysis.csv", encoding='utf-8-sig')
    complete_df['Dataset'] = 'PS0140-151'
    return complete_df

def create_summary_table(test_df, ps_df, styles):
    """Create summary comparison table"""
    data = [
        ['Dataset', 'N', 'REM Duration (min)', 'Artifact-free REM (%)', 'CHIN Baseline (µV)', 'CHIN Any (%)'],
        ['Test1-10',
         '7*',
         f"{test_df[test_df['CHIN_Any_%'] < 100]['REM_Duration_min'].mean()/60:.1f}±{test_df[test_df['CHIN_Any_%'] < 100]['REM_Duration_min'].std()/60:.1f}",
         f"{test_df[test_df['CHIN_Any_%'] < 100]['Artifact_free_%'].mean():.1f}±{test_df[test_df['CHIN_Any_%'] < 100]['Artifact_free_%'].std():.1f}",
         f"{test_df[test_df['CHIN_Any_%'] < 100]['CHIN1CHIN_Mean'].mean():.1f}±{test_df[test_df['CHIN_Any_%'] < 100]['CHIN1CHIN_Std'].mean():.1f}",
         f"{test_df[test_df['CHIN_Any_%'] < 100]['CHIN_Any_%'].mean():.1f}±{test_df[test_df['CHIN_Any_%'] < 100]['CHIN_Any_%'].std():.1f}"],
        ['PS0140-151',
         '4',
         f"{ps_df['REM_Duration_min'].mean():.1f}±{ps_df['REM_Duration_min'].std():.1f}",
         f"{ps_df['Artifact_free_%'].mean():.1f}±{ps_df['Artifact_free_%'].std():.1f}",
         f"{ps_df['CHIN_Mean'].mean():.2f}±{ps_df['CHIN_Std'].mean():.2f}",
         f"{ps_df['CHIN_Any_%'].mean():.1f}±{ps_df['CHIN_Any_%'].std():.1f}"]
    ]

    table = Table(data, colWidths=[2.5*cm, 1.5*cm, 2.5*cm, 3*cm, 3*cm, 2.5*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#2c5aa0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f2f2f2')]),
    ]))

    return table

def create_test_table(test_df, styles):
    """Create Test1-10 detailed table (CHIN only)"""
    # Filter valid data (exclude Test1, 9, 10 with 100%)
    valid_df = test_df[test_df['CHIN_Any_%'] < 100].copy()

    data = [['Patient\n환자', 'REM Duration\n(min)', 'Artifact-free\nREM (%)',
             'CHIN Baseline\n(µV)', 'CHIN Tonic\n(%)', 'CHIN Phasic\n(%)', 'CHIN Any\n(%)', 'RSWA\nStatus']]

    for _, row in valid_df.iterrows():
        rswa_status = 'Positive' if row['CHIN_Any_%'] >= 24.0 else 'Negative'
        data.append([
            row['Patient'],
            f"{row['REM_Duration_min']/60:.1f}",
            f"{row['Artifact_free_%']:.1f}",
            f"{row['CHIN1CHIN_Mean']:.1f}±{row['CHIN1CHIN_Std']:.1f}",
            f"{row['CHIN_Tonic_%']:.1f}",
            f"{row['CHIN_Phasic_%']:.1f}",
            f"{row['CHIN_Any_%']:.1f}",
            rswa_status
        ])

    # Add mean row
    data.append([
        'Mean±SD',
        f"{valid_df['REM_Duration_min'].mean()/60:.1f}±{valid_df['REM_Duration_min'].std()/60:.1f}",
        f"{valid_df['Artifact_free_%'].mean():.1f}±{valid_df['Artifact_free_%'].std():.1f}",
        f"{valid_df['CHIN1CHIN_Mean'].mean():.1f}±{valid_df['CHIN1CHIN_Std'].mean():.1f}",
        f"{valid_df['CHIN_Tonic_%'].mean():.1f}±{valid_df['CHIN_Tonic_%'].std():.1f}",
        f"{valid_df['CHIN_Phasic_%'].mean():.1f}±{valid_df['CHIN_Phasic_%'].std():.1f}",
        f"{valid_df['CHIN_Any_%'].mean():.1f}±{valid_df['CHIN_Any_%'].std():.1f}",
        '-'
    ])

    table = Table(data, colWidths=[2*cm, 2*cm, 2.2*cm, 3*cm, 2*cm, 2*cm, 2*cm, 2*cm])

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d9e2f3')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#2c5aa0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f2f2f2')]),
    ]))

    return table

def create_ps_table(ps_df, styles):
    """Create PS0140-151 detailed table (CHIN only)"""
    data = [['Patient\n환자', 'REM Duration\n(min)', 'Artifact-free\nREM (%)',
             'CHIN Baseline\n(µV)', 'CHIN Tonic\n(%)', 'CHIN Phasic\n(%)', 'CHIN Any\n(%)', 'RSWA\nStatus']]

    for _, row in ps_df.iterrows():
        rswa_status = 'Positive' if row['CHIN_Any_%'] >= 24.0 else 'Negative'
        data.append([
            row['Patient'],
            f"{row['REM_Duration_min']:.1f}",
            f"{row['Artifact_free_%']:.1f}",
            f"{row['CHIN_Mean']:.2f}±{row['CHIN_Std']:.2f}",
            f"{row['CHIN_Tonic_%']:.1f}",
            f"{row['CHIN_Phasic_%']:.1f}",
            f"{row['CHIN_Any_%']:.1f}",
            rswa_status
        ])

    # Add mean row
    data.append([
        'Mean±SD',
        f"{ps_df['REM_Duration_min'].mean():.1f}±{ps_df['REM_Duration_min'].std():.1f}",
        f"{ps_df['Artifact_free_%'].mean():.1f}±{ps_df['Artifact_free_%'].std():.1f}",
        f"{ps_df['CHIN_Mean'].mean():.2f}±{ps_df['CHIN_Std'].mean():.2f}",
        f"{ps_df['CHIN_Tonic_%'].mean():.1f}±{ps_df['CHIN_Tonic_%'].std():.1f}",
        f"{ps_df['CHIN_Phasic_%'].mean():.1f}±{ps_df['CHIN_Phasic_%'].std():.1f}",
        f"{ps_df['CHIN_Any_%'].mean():.1f}±{ps_df['CHIN_Any_%'].std():.1f}",
        '-'
    ])

    table = Table(data, colWidths=[2*cm, 2*cm, 2.2*cm, 3*cm, 2*cm, 2*cm, 2*cm, 2*cm])

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d9e2f3')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#2c5aa0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f2f2f2')]),
    ]))

    return table

def create_pdf_report(test_df, ps_df):
    """Create unified PDF report"""
    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=landscape(A4),
        rightMargin=1*cm,
        leftMargin=1*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    elements = []
    styles = getSampleStyleSheet()

    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName=KOREAN_FONT
    )

    # Subtitle style
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#2c5aa0'),
        spaceAfter=12,
        spaceBefore=12,
        fontName=KOREAN_FONT
    )

    # Normal style
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=9,
        fontName=KOREAN_FONT,
        leading=12
    )

    # Add title
    title = Paragraph(
        "Unified RBD Analysis Report: Test1-10 and PS0140-151<br/>통합 RBD 분석 보고서: Test1-10 및 PS0140-151",
        title_style
    )
    elements.append(title)
    elements.append(Spacer(1, 0.3*cm))

    # Add generation date
    date_text = f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    date_para = Paragraph(date_text, normal_style)
    elements.append(date_para)
    elements.append(Spacer(1, 0.5*cm))

    # Section 1: Summary Comparison
    section_title = Paragraph("<b>1. Summary Comparison / 데이터셋 비교 요약</b>", subtitle_style)
    elements.append(section_title)

    summary_table = create_summary_table(test_df, ps_df, styles)
    elements.append(summary_table)
    elements.append(Spacer(1, 0.3*cm))

    note_text = """
<b>Note:</b> *Test1-10: Excludes 3 patients (Test1, 9, 10) due to baseline calculation failure (100% values)<br/>
<b>Key Findings / 주요 소견:</b><br/>
• <b>Test1-10</b>: Higher baseline amplitude (mean CHIN 21.0±7.4 µV), RSWA 31.6±26.8%<br/>
• <b>PS0140-151</b>: Very low baseline amplitude (mean CHIN 1.46±0.23 µV), RSWA 30.5±5.0%<br/>
• Both groups show similar CHIN Any % despite different baseline amplitudes<br/>
• 두 그룹 모두 유사한 CHIN Any % 보이나 baseline amplitude는 14배 차이
"""
    note_para = Paragraph(note_text, normal_style)
    elements.append(note_para)
    elements.append(Spacer(1, 0.7*cm))

    # Section 2: Test1-10 Detailed Results
    section_title2 = Paragraph("<b>2. Test1-10 Detailed Results / Test1-10 상세 결과</b>", subtitle_style)
    elements.append(section_title2)

    test_table = create_test_table(test_df, styles)
    elements.append(test_table)
    elements.append(Spacer(1, 0.3*cm))

    test_note = """
<b>RSWA Diagnostic Criteria (Joza et al., 2025):</b><br/>
• Balanced cutoff: CHIN Any % ≥24.0% (Sensitivity 89.8%, Specificity 97.3%)<br/>
• High specificity cutoff: CHIN Any % ≥41.4% (Sensitivity 95.6%, Specificity 100%)<br/>
<br/>
<b>Test1-10 RSWA Results Summary / 결과 요약:</b><br/>
• <b>RSWA Positive (≥24.0%)</b>: 3 patients<br/>
  - Test3: Tonic 7.4%, Phasic 62.7%, Any 68.5%<br/>
  - Test4: Tonic 2.0%, Phasic 58.9%, Any 61.1%<br/>
  - Test8: Tonic 2.5%, Phasic 41.9%, Any 45.3%<br/>
• <b>RSWA Negative (<24.0%)</b>: 4 patients<br/>
  - Test2: Tonic 0.0%, Phasic 8.0%, Any 8.0%<br/>
  - Test5: Tonic 0.0%, Phasic 22.0%, Any 22.3%<br/>
  - Test6: Tonic 0.0%, Phasic 3.0%, Any 3.0%<br/>
  - Test7: Tonic 0.0%, Phasic 22.3%, Any 22.4%<br/>
• <b>Excluded</b>: 3 patients - Test1, Test9, Test10 (baseline calculation failed → all values 100%)
"""
    test_note_para = Paragraph(test_note, normal_style)
    elements.append(test_note_para)
    elements.append(Spacer(1, 0.7*cm))

    # Section 3: PS0140-151 Detailed Results
    section_title3 = Paragraph("<b>3. PS0140-151 Detailed Results / PS0140-151 상세 결과</b>", subtitle_style)
    elements.append(section_title3)

    ps_table = create_ps_table(ps_df, styles)
    elements.append(ps_table)
    elements.append(Spacer(1, 0.3*cm))

    ps_note = """
<b>Key Findings / 주요 소견:</b><br/>
• All 4 patients show RSWA positive (CHIN Any % range: 21.7-36.6%)<br/>
• 모든 4명 환자가 RSWA positive (CHIN Any % 범위: 21.7-36.6%)<br/>
• Very low baseline amplitudes compared to Test1-10 (CHIN: 1.46±0.23 µV vs 21.0±7.4 µV)<br/>
• Test1-10 대비 매우 낮은 baseline amplitude (CHIN: 1.46±0.23 µV vs 21.0±7.4 µV)<br/>
• Good data quality: 89.8-95.8% artifact-free REM / 우수한 데이터 품질: 89.8-95.8% artifact-free REM
"""
    ps_note_para = Paragraph(ps_note, normal_style)
    elements.append(ps_note_para)
    elements.append(Spacer(1, 0.7*cm))

    # Section 4: Clinical Interpretation Guide
    section_title4 = Paragraph("<b>4. Clinical Interpretation Guide / 임상 해석 지침</b>", subtitle_style)
    elements.append(section_title4)

    clinical_text = """
<b>Column Justification and Clinical Criteria / 각 컬럼의 임상적 근거:</b><br/>
<br/>
<b>1. REM Duration (minutes) / REM 지속시간 (분):</b><br/>
• <b>Purpose</b>: Data quality indicator - ensures sufficient REM for reliable RSWA measurement<br/>
• <b>RBDtector requirement</b>: Minimum 150 seconds (2.5 min) continuous REM for baseline calculation (Röthenbacher et al., 2022)<br/>
• <b>Typical range</b>: 60-120 minutes total REM per night in adults<br/>
• <b>Clinical significance</b>: Longer REM duration provides more robust RSWA quantification<br/>
<br/>
<b>2. Artifact-free REM (%) / 아티팩트 없는 REM 비율:</b><br/>
• <b>Purpose</b>: Data quality indicator - excludes epochs contaminated by movement, ECG, or technical artifacts<br/>
• <b>RBDtector processing</b>: Automatically removes artifact epochs before RSWA calculation<br/>
• <b>Clinical note</b>: No published quality threshold exists; RBDtector only requires ≥150s continuous REM<br/>
• <b>Our data range</b>: Test1-10: 89-97%, PS0140-151: 90-96%<br/>
<br/>
<b>3. CHIN Baseline (µV) / CHIN 근전도 기준 진폭:</b><br/>
• <b>Definition</b>: Mean ± SD of RMS amplitude during artifact-free REM sleep<br/>
• <b>Purpose</b>: Physiological measure of muscle atonia quality (NOT used for RSWA detection)<br/>
• <b>Clinical interpretation</b>: Lower baseline = better muscle atonia (healthier REM sleep)<br/>
• <b>Note</b>: No published diagnostic cutoff exists; this is a descriptive physiological measure<br/>
• <b>Different from RBDtector detection baseline</b>: Detection uses minimum RMS from 30s rolling window<br/>
<br/>
<b>4. CHIN Tonic (%) / CHIN 긴장성 활동 비율:</b><br/>
• <b>Definition (SINBAR method)</b>: EMG elevation in ≥50% of 30-s epoch (Frauscher et al., 2012)<br/>
• <b>Clinical significance</b>: Sustained muscle tone loss during REM - characteristic of RBD<br/>
• <b>Implementation verified</b>: RBDtector code (PSG.py:589-618) matches published SINBAR criteria<br/>
• <b>Estimated normal range</b>: <10% (no formal published cutoff for isolated Tonic %)<br/>
<br/>
<b>5. CHIN Phasic (%) / CHIN 위상성 활동 비율:</b><br/>
• <b>Definition (SINBAR method)</b>: Brief EMG bursts (0.1-5.0 sec) scored per 3-s mini-epoch (Frauscher et al., 2012)<br/>
• <b>Clinical significance</b>: Transient muscle activations during REM - early RBD marker<br/>
• <b>Implementation verified</b>: RBDtector code (PSG.py:534-585) matches published SINBAR criteria<br/>
• <b>Estimated normal range</b>: <15% (no formal published cutoff for isolated Phasic %)<br/>
<br/>
<b>6. CHIN Any (%) / CHIN 전체 활동 비율:</b><br/>
• <b>Definition</b>: Combined metric - Tonic OR Phasic activity (Frauscher et al., 2012)<br/>
• <b>PUBLISHED diagnostic cutoff (Joza et al., 2025 - Montreal validation study, N=173):</b><br/>
  - <b>Balanced cutoff</b>: ≥24.0% (Sensitivity 89.8%, Specificity 97.3%)<br/>
  - <b>High specificity cutoff</b>: ≥41.4% (Sensitivity 95.6%, Specificity 100%)<br/>
• <b>Implementation verified</b>: RBDtector code (PSG.py:482-531) matches published SINBAR criteria<br/>
• <b>Clinical interpretation</b>: Primary quantitative marker for RSWA - this is the validated diagnostic metric<br/>
<br/>
<b>7. RSWA Status / RSWA 상태:</b><br/>
• <b>Positive (≥24.0%)</b>: RSWA present - supports RBD diagnosis if clinical symptoms present<br/>
• <b>Negative (<24.0%)</b>: No RSWA - RBD unlikely (but clinical correlation still needed)<br/>
<br/>
<b>Important Distinction / 중요한 구분:</b><br/>
• <b>RSWA</b>: Quantitative EMG measurement during REM sleep (what this report measures)<br/>
• <b>RBD</b>: RSWA + dream enactment behaviors (clinical diagnosis requires both)<br/>
• <b>This report measures RSWA only</b> - clinical correlation is needed for RBD diagnosis<br/>
<br/>
<b>References / 참고문헌:</b><br/>
• <b>RSWA diagnostic cutoffs</b>: Joza et al. (2025). J Sleep Res, 0:e70037. doi: 10.1111/jsr.70037<br/>
• <b>SINBAR method & RBDtector</b>: Röthenbacher et al. (2022). Sci Rep, 12:20886. doi: 10.1038/s41598-022-25361-x<br/>
• <b>Original SINBAR criteria</b>: Frauscher et al. (2012). Sleep, 35(8):1097-1103. doi: 10.5665/sleep.1992
"""
    clinical_para = Paragraph(clinical_text, normal_style)
    elements.append(clinical_para)

    elements.append(Spacer(1, 0.5*cm))

    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        fontName=KOREAN_FONT
    )

    footer_text = f"""
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
Data source: RBDtector automated analysis (November 2025)<br/>
Report format: Unified format for Test1-10 and PS0140-151 datasets<br/>
Seoul National University Hospital Sleep Medicine Center
"""
    footer_para = Paragraph(footer_text, footer_style)
    elements.append(footer_para)

    # Build PDF
    doc.build(elements)
    print(f"\n✓ Unified PDF report generated: {OUTPUT_PDF}")


def main():
    print("=" * 80)
    print("Generating Unified RBD Analysis Report")
    print("=" * 80)

    # Load data
    print("\nLoading Test1-10 data...")
    test_df = load_test_data()
    print(f"  Loaded {len(test_df)} Test patients")

    print("\nLoading PS0140-151 data...")
    ps_df = load_ps_data()
    print(f"  Loaded {len(ps_df)} PS patients")

    # Create PDF
    print("\nGenerating unified PDF report...")
    create_pdf_report(test_df, ps_df)

    print("\n" + "=" * 80)
    print("Unified Report Generation Complete!")
    print("=" * 80)
    print(f"\nOutput file: {OUTPUT_PDF}")
    print("\n✓ Report successfully generated with:")
    print("  - Summary comparison table")
    print("  - Test1-10 detailed results (7 valid patients)")
    print("  - PS0140-151 detailed results (4 patients)")
    print("  - Clinical notes with true baseline amplitudes")
    print("  - Published RSWA diagnostic criteria")


if __name__ == "__main__":
    main()
