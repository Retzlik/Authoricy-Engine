"""
Chart Generator for Reports

Generates SVG/PNG charts for inclusion in PDF reports.
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ChartGenerator:
    """
    Generates charts for reports.

    Uses inline SVG for PDF compatibility.
    """

    @staticmethod
    def generate_trend_chart(
        data: List[Dict[str, Any]],
        x_key: str = "date",
        y_key: str = "value",
        width: int = 600,
        height: int = 300,
        color: str = "#4361ee",
    ) -> str:
        """
        Generate a simple line chart as SVG.

        Args:
            data: List of {x_key: x, y_key: y} dicts
            x_key: Key for x-axis values
            y_key: Key for y-axis values
            width: Chart width
            height: Chart height
            color: Line color

        Returns:
            SVG string
        """
        if not data:
            return "<p>No data available for chart.</p>"

        # Extract values
        values = [d.get(y_key, 0) for d in data]
        labels = [str(d.get(x_key, ""))[:10] for d in data]

        if not values or max(values) == 0:
            return "<p>Insufficient data for chart.</p>"

        # Calculate scale
        max_val = max(values)
        min_val = min(values)
        range_val = max_val - min_val or 1

        # Margins
        margin = {"top": 20, "right": 20, "bottom": 40, "left": 60}
        chart_width = width - margin["left"] - margin["right"]
        chart_height = height - margin["top"] - margin["bottom"]

        # Build path
        points = []
        for i, val in enumerate(values):
            x = margin["left"] + (i / (len(values) - 1 or 1)) * chart_width
            y = margin["top"] + chart_height - ((val - min_val) / range_val) * chart_height
            points.append(f"{x},{y}")

        path_d = "M " + " L ".join(points)

        # Build SVG
        svg = f"""
        <svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
            <!-- Background -->
            <rect width="{width}" height="{height}" fill="white"/>

            <!-- Grid lines -->
            {"".join(f'<line x1="{margin["left"]}" y1="{margin["top"] + i * chart_height / 4}" x2="{width - margin["right"]}" y2="{margin["top"] + i * chart_height / 4}" stroke="#eee" stroke-width="1"/>' for i in range(5))}

            <!-- Line -->
            <path d="{path_d}" fill="none" stroke="{color}" stroke-width="2"/>

            <!-- Points -->
            {"".join(f'<circle cx="{margin["left"] + (i / (len(values) - 1 or 1)) * chart_width}" cy="{margin["top"] + chart_height - ((v - min_val) / range_val) * chart_height}" r="4" fill="{color}"/>' for i, v in enumerate(values))}

            <!-- Y-axis labels -->
            <text x="{margin["left"] - 10}" y="{margin["top"]}" text-anchor="end" font-size="10" fill="#666">{max_val:,.0f}</text>
            <text x="{margin["left"] - 10}" y="{margin["top"] + chart_height}" text-anchor="end" font-size="10" fill="#666">{min_val:,.0f}</text>
        </svg>
        """

        return svg

    @staticmethod
    def generate_bar_chart(
        data: List[Dict[str, Any]],
        label_key: str = "label",
        value_key: str = "value",
        width: int = 600,
        height: int = 300,
        color: str = "#4361ee",
    ) -> str:
        """
        Generate a horizontal bar chart as SVG.

        Args:
            data: List of {label_key: label, value_key: value} dicts
            label_key: Key for labels
            value_key: Key for values
            width: Chart width
            height: Chart height
            color: Bar color

        Returns:
            SVG string
        """
        if not data:
            return "<p>No data available for chart.</p>"

        data = data[:10]  # Limit to 10 bars
        max_val = max(d.get(value_key, 0) for d in data) or 1

        margin = {"left": 150, "right": 50, "top": 20, "bottom": 20}
        chart_width = width - margin["left"] - margin["right"]
        bar_height = (height - margin["top"] - margin["bottom"]) / len(data) * 0.8
        bar_gap = (height - margin["top"] - margin["bottom"]) / len(data) * 0.2

        bars = ""
        for i, d in enumerate(data):
            label = str(d.get(label_key, ""))[:20]
            value = d.get(value_key, 0)
            bar_width = (value / max_val) * chart_width

            y = margin["top"] + i * (bar_height + bar_gap)

            bars += f"""
            <text x="{margin["left"] - 10}" y="{y + bar_height / 2 + 4}" text-anchor="end" font-size="10" fill="#333">{label}</text>
            <rect x="{margin["left"]}" y="{y}" width="{bar_width}" height="{bar_height}" fill="{color}" rx="2"/>
            <text x="{margin["left"] + bar_width + 5}" y="{y + bar_height / 2 + 4}" font-size="10" fill="#666">{value:,.0f}</text>
            """

        svg = f"""
        <svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
            <rect width="{width}" height="{height}" fill="white"/>
            {bars}
        </svg>
        """

        return svg

    @staticmethod
    def generate_pie_chart(
        data: List[Dict[str, Any]],
        label_key: str = "label",
        value_key: str = "value",
        size: int = 300,
        colors: Optional[List[str]] = None,
    ) -> str:
        """
        Generate a simple pie chart as SVG.

        Args:
            data: List of {label_key: label, value_key: value} dicts
            label_key: Key for labels
            value_key: Key for values
            size: Chart size (square)
            colors: List of colors to use

        Returns:
            SVG string
        """
        if not data:
            return "<p>No data available for chart.</p>"

        if colors is None:
            colors = ["#4361ee", "#3f37c9", "#4895ef", "#4cc9f0", "#f72585", "#b5179e"]

        total = sum(d.get(value_key, 0) for d in data) or 1
        cx, cy = size / 2, size / 2
        r = size / 2 - 20

        import math

        paths = ""
        start_angle = 0

        for i, d in enumerate(data[:6]):
            value = d.get(value_key, 0)
            angle = (value / total) * 360

            # Calculate arc
            end_angle = start_angle + angle
            large_arc = 1 if angle > 180 else 0

            x1 = cx + r * math.cos(math.radians(start_angle - 90))
            y1 = cy + r * math.sin(math.radians(start_angle - 90))
            x2 = cx + r * math.cos(math.radians(end_angle - 90))
            y2 = cy + r * math.sin(math.radians(end_angle - 90))

            color = colors[i % len(colors)]

            paths += f'<path d="M {cx} {cy} L {x1} {y1} A {r} {r} 0 {large_arc} 1 {x2} {y2} Z" fill="{color}"/>'

            start_angle = end_angle

        svg = f"""
        <svg width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg">
            <rect width="{size}" height="{size}" fill="white"/>
            {paths}
        </svg>
        """

        return svg
