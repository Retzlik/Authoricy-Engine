"""
Authoricy Intelligence System - Report Generation

v7: ONE REPORT, ONE ROUTE

This module handles PDF report generation:
- Single comprehensive strategy report (40-60 pages)
- Full confidence tracking - missing data is VISIBLE
- No more external vs internal split

Note: PDF generation requires weasyprint. HTML generation works without it.
"""

# HTML builders
from .report import ReportBuilder
from .charts import ChartGenerator
from .confidence import ReportConfidence, data_missing_html

# Legacy imports for backwards compatibility (deprecated)
from .external import ExternalReportBuilder
from .internal import InternalReportBuilder

# PDF generator requires weasyprint (optional dependency)
try:
    from .generator import ReportGenerator, GeneratedReport
    _HAS_WEASYPRINT = True
except ImportError:
    ReportGenerator = None
    GeneratedReport = None
    _HAS_WEASYPRINT = False

__all__ = [
    # New unified API
    "ReportBuilder",
    "ReportConfidence",
    "data_missing_html",
    "ChartGenerator",
    # Legacy (deprecated)
    "ExternalReportBuilder",
    "InternalReportBuilder",
]

if _HAS_WEASYPRINT:
    __all__.extend(["ReportGenerator", "GeneratedReport"])
