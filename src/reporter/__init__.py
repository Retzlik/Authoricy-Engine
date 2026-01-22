"""
Authoricy Intelligence System - Report Generation

This module handles PDF report generation:
- External Report (Lead Magnet): 10-15 pages, executive-focused
- Internal Report (Strategy Guide): 40-60 pages, tactical playbook

Note: PDF generation requires weasyprint. HTML generation works without it.
"""

# HTML builders always available
from .external import ExternalReportBuilder
from .internal import InternalReportBuilder
from .charts import ChartGenerator

# PDF generator requires weasyprint (optional dependency)
try:
    from .generator import ReportGenerator
    _HAS_WEASYPRINT = True
except ImportError:
    ReportGenerator = None
    _HAS_WEASYPRINT = False

__all__ = [
    "ExternalReportBuilder",
    "InternalReportBuilder",
    "ChartGenerator",
]

if _HAS_WEASYPRINT:
    __all__.append("ReportGenerator")
