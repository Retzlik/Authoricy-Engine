"""
Report Generator - Main orchestrator for PDF generation.

Generates both external (lead magnet) and internal (strategy guide) reports.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from weasyprint import HTML, CSS

logger = logging.getLogger(__name__)

# Template directory
TEMPLATE_DIR = Path(__file__).parent / "templates"


@dataclass
class GeneratedReport:
    """A generated PDF report."""
    filename: str
    pdf_bytes: bytes
    page_count: int
    report_type: str  # "external" or "internal"
    generated_at: datetime


class ReportGenerator:
    """
    Main report generator coordinating PDF creation.

    Generates:
    - External Report: 10-15 pages, executive-focused, sales-enabling
    - Internal Report: 40-60 pages, tactical playbook
    """

    def __init__(self):
        self.template_dir = TEMPLATE_DIR

    async def generate_external(
        self,
        analysis_result: Any,  # AnalysisResult from engine
        analysis_data: Dict[str, Any],
    ) -> GeneratedReport:
        """
        Generate external report (lead magnet).

        Args:
            analysis_result: Complete analysis result from engine
            analysis_data: Original compiled data

        Returns:
            GeneratedReport with PDF bytes
        """
        from .external import ExternalReportBuilder

        builder = ExternalReportBuilder(self.template_dir)
        html_content = builder.build(analysis_result, analysis_data)

        # Generate PDF
        pdf_bytes = self._html_to_pdf(html_content)

        domain = analysis_data.get("metadata", {}).get("domain", "report")
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"{domain}_seo_analysis_{timestamp}.pdf"

        return GeneratedReport(
            filename=filename,
            pdf_bytes=pdf_bytes,
            page_count=self._estimate_pages(len(pdf_bytes)),
            report_type="external",
            generated_at=datetime.now(),
        )

    async def generate_internal(
        self,
        analysis_result: Any,
        analysis_data: Dict[str, Any],
    ) -> GeneratedReport:
        """
        Generate internal report (strategy guide).

        Args:
            analysis_result: Complete analysis result from engine
            analysis_data: Original compiled data

        Returns:
            GeneratedReport with PDF bytes
        """
        from .internal import InternalReportBuilder

        builder = InternalReportBuilder(self.template_dir)
        html_content = builder.build(analysis_result, analysis_data)

        # Generate PDF
        pdf_bytes = self._html_to_pdf(html_content)

        domain = analysis_data.get("metadata", {}).get("domain", "report")
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"{domain}_strategy_guide_{timestamp}.pdf"

        return GeneratedReport(
            filename=filename,
            pdf_bytes=pdf_bytes,
            page_count=self._estimate_pages(len(pdf_bytes)),
            report_type="internal",
            generated_at=datetime.now(),
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
