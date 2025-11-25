#!/usr/bin/env python3
"""
Generate PDF report for PS0140-151 patients in Test1-10 format
"""

import pandas as pd
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
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
OUTPUT_PDF = RESULTS_DIR / "PS0140-151_RBD_Analysis_Report_Test_Format.pdf"

def load_data():
    """Load all PS0140-151 data"""
    complete_df = pd.read_csv(RESULTS_DIR / "PS0140-151_Complete_Analysis.csv", encoding='utf-8-sig')
    return complete_df

def create_pdf_report(data_df):
    """Create PDF report in Test1-10 format"""
    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=landscape(A4),
        rightMargin=1*cm,
        leftMargin=1*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    # Container for PDF elements
    elements = []

    # Create styles
    styles = getSampleStyleSheet()

    # Title style (with Korean support)
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

    # Normal text style
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=9,
        fontName=KOREAN_FONT,
        leading=12
    )

    # Add title
    title = Paragraph(
        "PS0140-151 RBD (REM Sleep Behavior Disorder) Analysis Report<br/>PS0140-151 RBD 분석 보고서",
        title_style
    )
    elements.append(title)
    elements.append(Spacer(1, 0.3*cm))

    # Add generation date
    date_text = f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    date_para = Paragraph(date_text, normal_style)
    elements.append(date_para)
    elements.append(Spacer(1, 0.5*cm))

    # Section 1: Patient Summary
    section_title = Paragraph("<b>1. Patient Summary / 환자 요약</b>", subtitle_style)
    elements.append(section_title)

    # Prepare table data
    table_data = [
        ['Patient\n환자',
         'REM Duration\n(min)',
         'Artifact-free\nREM (%)',
         'CHIN Baseline\n(µV)',
         'LAT Baseline\n(µV)',
         'RAT Baseline\n(µV)',
         'CHIN\nAny (%)',
         'LAT\nAny (%)',
         'RAT\nAny (%)']
    ]

    for _, row in data_df.iterrows():
        table_data.append([
            row['Patient'],
            f"{row['REM_Duration_min']:.1f}",
            f"{row['Artifact_free_%']:.1f}",
            row['CHIN_Baseline'],
            row['LAT_Baseline'],
            row['RAT_Baseline'],
            f"{row['CHIN_Any_%']:.1f}",
            f"{row['LAT_Any_%']:.1f}",
            f"{row['RAT_Any_%']:.1f}"
        ])

    # Add mean row
    table_data.append([
        'Mean ± SD',
        f"{data_df['REM_Duration_min'].mean():.1f}±{data_df['REM_Duration_min'].std():.1f}",
        f"{data_df['Artifact_free_%'].mean():.1f}±{data_df['Artifact_free_%'].std():.1f}",
        f"{data_df['CHIN_Mean'].mean():.2f}±{data_df['CHIN_Std'].mean():.2f}",
        f"{data_df['LAT_Mean'].mean():.2f}±{data_df['LAT_Std'].mean():.2f}",
        f"{data_df['RAT_Mean'].mean():.2f}±{data_df['RAT_Std'].mean():.2f}",
        f"{data_df['CHIN_Any_%'].mean():.1f}±{data_df['CHIN_Any_%'].std():.1f}",
        f"{data_df['LAT_Any_%'].mean():.1f}±{data_df['LAT_Any_%'].std():.1f}",
        f"{data_df['RAT_Any_%'].mean():.1f}±{data_df['RAT_Any_%'].std():.1f}"
    ])

    # Create table
    table = Table(table_data, colWidths=[1.5*cm, 1.8*cm, 1.8*cm, 2*cm, 2*cm, 2*cm, 1.8*cm, 1.8*cm, 1.8*cm])

    # Table style
    table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

        # Data rows
        ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -2), colors.black),
        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),

        # Mean row
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d9e2f3')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),

        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#2c5aa0')),

        # Alternating row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f2f2f2')]),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 0.7*cm))

    # Section 2: Detailed RSWA Metrics
    section_title2 = Paragraph("<b>2. RSWA (REM Sleep Without Atonia) Metrics / RSWA 지표</b>", subtitle_style)
    elements.append(section_title2)

    # RSWA table
    rswa_data = [
        ['Patient',
         'CHIN\nTonic (%)', 'CHIN\nPhasic (%)', 'CHIN\nAny (%)',
         'LAT\nTonic (%)', 'LAT\nPhasic (%)', 'LAT\nAny (%)',
         'RAT\nTonic (%)', 'RAT\nPhasic (%)', 'RAT\nAny (%)']
    ]

    for _, row in data_df.iterrows():
        rswa_data.append([
            row['Patient'],
            f"{row['CHIN_Tonic_%']:.1f}",
            f"{row['CHIN_Phasic_%']:.1f}",
            f"{row['CHIN_Any_%']:.1f}",
            f"{row['LAT_Tonic_%']:.1f}",
            f"{row['LAT_Phasic_%']:.1f}",
            f"{row['LAT_Any_%']:.1f}",
            f"{row['RAT_Tonic_%']:.1f}",
            f"{row['RAT_Phasic_%']:.1f}",
            f"{row['RAT_Any_%']:.1f}"
        ])

    rswa_table = Table(rswa_data, colWidths=[1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm, 1.5*cm])

    rswa_table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

        # Data
        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),

        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#2c5aa0')),

        # Alternating rows
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f2f2f2')]),
    ]))

    elements.append(rswa_table)
    elements.append(Spacer(1, 0.7*cm))

    # Section 3: Clinical Notes
    section_title3 = Paragraph("<b>3. Clinical Notes / 임상 참고사항</b>", subtitle_style)
    elements.append(section_title3)

    notes_text = """
<b>Baseline Amplitude (µV) / 기준 진폭:</b><br/>
• True baseline amplitude calculated as Mean ± SD of RMS (Root Mean Square) during artifact-free REM sleep<br/>
• 아티팩트 없는 REM 수면 중 RMS(제곱 평균 제곱근)의 평균 ± 표준편차로 계산된 실제 기준 진폭<br/>
• Lower baseline indicates better muscle atonia / 낮은 기준값은 더 나은 근육 무긴장을 나타냄<br/>
<br/>
<b>RBD Indicators / RBD 지표:</b><br/>
• <b>Tonic</b>: Sustained elevated EMG (>50% of 30-s epoch) / 지속적 EMG 상승 (30초 에폭의 50% 이상)<br/>
• <b>Phasic</b>: Brief EMG bursts (0.1-5.0 seconds) / 짧은 EMG 폭발 (0.1-5.0초)<br/>
• <b>Any</b>: Tonic OR Phasic activity / Tonic 또는 Phasic 활동<br/>
<br/>
<b>RBDtector SINBAR Criteria (Frauscher et al., 2012):</b><br/>
• Published cutoff: <b>Mentalis Any + FDS Any > 32%</b> suggests RBD<br/>
• Optimal cutoff from validation: <b>Mentalis Any + FDS Any > 20.6%</b> (96% sensitivity, 100% specificity)<br/>
• Note: LAT/RAT correspond to limb EMG channels similar to FDS in SINBAR protocol<br/>
<br/>
<b>Data Quality / 데이터 품질:</b><br/>
• Artifact-free REM: {:.1f}% ± {:.1f}% (range: {:.1f}% - {:.1f}%)<br/>
• All patients meet minimum requirement (≥150s continuous REM for baseline calculation)<br/>
• 모든 환자가 최소 요구사항 충족 (기준선 계산을 위한 ≥150초 연속 REM)<br/>
<br/>
<b>Method / 분석 방법:</b><br/>
• Software: RBDtector (open-source, SINBAR protocol implementation)<br/>
• Channels: Chin1-Chin2, Lat (left leg), Rat (right leg)<br/>
• Baseline detection: RMS in 5-second windows during artifact-free REM sleep<br/>
• RSWA detection: EMG amplitude ≥2× baseline for ≥100 ms<br/>
""".format(
        data_df['Artifact_free_%'].mean(),
        data_df['Artifact_free_%'].std(),
        data_df['Artifact_free_%'].min(),
        data_df['Artifact_free_%'].max()
    )

    notes_para = Paragraph(notes_text, normal_style)
    elements.append(notes_para)

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
Data source: RBDtector analysis results (November 2025)<br/>
Report format: Compatible with Test1-10 analysis report structure<br/>
"""
    footer_para = Paragraph(footer_text, footer_style)
    elements.append(footer_para)

    # Build PDF
    doc.build(elements)
    print(f"\n✓ PDF report generated: {OUTPUT_PDF}")


def main():
    print("=" * 80)
    print("Generating PS0140-151 PDF Report (Test1-10 Format)")
    print("=" * 80)

    # Load data
    print("\nLoading data...")
    data_df = load_data()
    print(f"  Loaded {len(data_df)} patients")

    # Create PDF
    print("\nGenerating PDF report...")
    create_pdf_report(data_df)

    print("\n" + "=" * 80)
    print("PDF Report Generation Complete!")
    print("=" * 80)
    print(f"\nOutput file: {OUTPUT_PDF}")
    print("\n✓ Report successfully generated in Test1-10 format")


if __name__ == "__main__":
    main()
