"""
Authoricy Intelligence System - Report Generation

This module handles PDF report generation:
- External Report (Lead Magnet): 10-15 pages, executive-focused
- Internal Report (Strategy Guide): 40-60 pages, tactical playbook
"""

from .generator import ReportGenerator
from .external import ExternalReportBuilder
from .internal import InternalReportBuilder
from .charts import ChartGenerator

__all__ = [
    "ReportGenerator",
    "ExternalReportBuilder",
    "InternalReportBuilder",
    "ChartGenerator",
]
