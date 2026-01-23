"""
Report Generator - Main orchestrator for PDF generation.

v7: Single report - ONE REPORT, ONE ROUTE.

Makes missing data VISIBLE with confidence tracking.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

from weasyprint import HTML, CSS

logger = logging.getLogger(__name__)

# Template directory
TEMPLATE_DIR = Path(__file__).parent / "templates"


@dataclass
class GeneratedReport:
    """A generated PDF report with confidence tracking."""
    filename: str
    pdf_bytes: bytes
    page_count: int
    generated_at: datetime
    # Confidence tracking
    confidence_score: float = 0.0
    confidence_level: str = "UNKNOWN"
    missing_data: list = field(default_factory=list)


class ReportGenerator:
    """
    Main report generator coordinating PDF creation.

    v7: ONE REPORT - comprehensive 40-60 page strategy guide.
    No more external vs internal split.
    """

    def __init__(self):
        self.template_dir = TEMPLATE_DIR

    async def generate(
        self,
        analysis_result: Any,  # AnalysisResult from engine
        analysis_data: Dict[str, Any],
    ) -> GeneratedReport:
        """
        Generate THE report - comprehensive strategy guide.

        Args:
            analysis_result: Complete analysis result from engine
            analysis_data: Original compiled data

        Returns:
            GeneratedReport with PDF bytes and confidence info
        """
        from .report import ReportBuilder

        builder = ReportBuilder(self.template_dir)
        html_content, confidence = builder.build(analysis_result, analysis_data)

        # Generate PDF
        pdf_bytes = self._html_to_pdf(html_content)

        domain = analysis_data.get("metadata", {}).get("domain", "report")
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"{domain}_seo_strategy_{timestamp}.pdf"

        # Log confidence warning if low
        if confidence.confidence_score < 50:
            logger.warning(
                f"Report confidence LOW: {confidence.confidence_score:.0f}% "
                f"Missing: {confidence.missing_required[:3]}"
            )

        return GeneratedReport(
            filename=filename,
            pdf_bytes=pdf_bytes,
            page_count=self._estimate_pages(len(pdf_bytes)),
            generated_at=datetime.now(),
            confidence_score=confidence.confidence_score,
            confidence_level=confidence.confidence_level,
            missing_data=confidence.missing_required[:10],
        )

    def _html_to_pdf(self, html_content: str) -> bytes:
        """
        Convert HTML to PDF using WeasyPrint.

        Args:
            html_content: Complete HTML document

        Returns:
            PDF as bytes
        """
        try:
            # Load base CSS
            css_path = self.template_dir / "components" / "styles.css"
            css = None
            if css_path.exists():
                css = CSS(filename=str(css_path))

            # Generate PDF
            html = HTML(string=html_content)
            if css:
                pdf_bytes = html.write_pdf(stylesheets=[css])
            else:
                pdf_bytes = html.write_pdf()

            logger.info(f"Generated PDF: {len(pdf_bytes)} bytes")
            return pdf_bytes

        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            raise

    def _estimate_pages(self, pdf_size: int) -> int:
        """Estimate page count from PDF size."""
        # Rough estimate: ~50KB per page for a typical report
        return max(1, pdf_size // 50000)

    def save_report(self, report: GeneratedReport, output_dir: str) -> str:
        """
        Save report to disk.

        Args:
            report: Generated report
            output_dir: Directory to save to

        Returns:
            Full path to saved file
        """
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, report.filename)

        with open(filepath, "wb") as f:
            f.write(report.pdf_bytes)

        logger.info(f"Saved report: {filepath}")
        return filepath
