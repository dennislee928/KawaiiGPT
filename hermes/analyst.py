import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from hermes.hermes_provider import HermesProvider

@dataclass
class AnalystReport:
    executive_summary: str
    critical_findings: List[Dict[str, Any]] = field(default_factory=list)
    high_findings: List[Dict[str, Any]] = field(default_factory=list)
    medium_findings: List[Dict[str, Any]] = field(default_factory=list)
    low_findings: List[Dict[str, Any]] = field(default_factory=list)
    info_findings: List[Dict[str, Any]] = field(default_factory=list)
    remediation_plan: str = ""
    risk_score: float = 0.0
    markdown: str = ""

class ResultAnalyst:
    def __init__(self, provider: HermesProvider):
        self.provider = provider

    def analyze(self, module_results: List[Dict[str, Any]], context: str = "") -> AnalystReport:
        all_findings = []
        for res in module_results:
            findings = res.get("findings", [])
            for f in findings:
                # Add module info to finding
                f["module"] = res.get("module", "unknown")
                all_findings.append(f)

        # 2. Deduplicate
        deduped = {}
        for f in all_findings:
            key = (f.get("title"), f.get("host"), f.get("port"))
            if key not in deduped:
                deduped[key] = f
            else:
                # Keep the one with higher severity if duplicates found
                # (Assuming severity order: critical > high > medium > low > info)
                severity_map = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
                current_sev = severity_map.get(deduped[key].get("severity", "info"), 0)
                new_sev = severity_map.get(f.get("severity", "info"), 0)
                if new_sev > current_sev:
                    deduped[key] = f

        findings_list = list(deduped.values())

        # 3. Bucket
        report = AnalystReport(executive_summary="")
        for f in findings_list:
            sev = f.get("severity", "info").lower()
            if sev == "critical":
                report.critical_findings.append(f)
            elif sev == "high":
                report.high_findings.append(f)
            elif sev == "medium":
                report.medium_findings.append(f)
            elif sev == "low":
                report.low_findings.append(f)
            else:
                report.info_findings.append(f)

        # 4. Score
        # risk_score = (10×critical + 7×high + 4×medium + 1×low) / max_possible
        # Let's define max_possible as if there were 10 critical findings for normalization
        c = len(report.critical_findings)
        h = len(report.high_findings)
        m = len(report.medium_findings)
        l = len(report.low_findings)
        
        raw_score = (10 * c) + (7 * h) + (4 * m) + (1 * l)
        report.risk_score = min(10.0, raw_score / 10.0) if raw_score > 0 else 0.0

        # 5. LLM summarize
        top_findings = (report.critical_findings + report.high_findings)[:10]
        if not top_findings and (report.medium_findings):
             top_findings = report.medium_findings[:10]

        summary_prompt = f"""
You are a senior security analyst. Analyze these findings from a penetration test and provide:
1. A concise executive summary (2-3 sentences).
2. A prioritized remediation plan as a numbered list.

Findings:
{json.dumps(top_findings, indent=2)}

Context: {context}
"""
        try:
            llm_response = self.provider.chat([{"role": "user", "content": summary_prompt}], stream=False)
            content = llm_response.content
            
            # Simple split for executive summary and remediation plan
            # (In reality, we might want more robust parsing)
            if "Remediation Plan" in content:
                parts = content.split("Remediation Plan", 1)
                report.executive_summary = parts[0].replace("Executive Summary", "").strip()
                report.remediation_plan = parts[1].strip(": \n")
            else:
                report.executive_summary = content[:200] + "..."
                report.remediation_plan = content
        except Exception as e:
            report.executive_summary = f"Error generating summary: {e}"
            report.remediation_plan = "Manual review required."

        # 6. Render Markdown
        report.markdown = self._render_markdown(report)
        return report

    def _render_markdown(self, report: AnalystReport) -> str:
        md = f"# Pentest Analyst Report\n\n"
        md += f"**Generated At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        md += f"**Risk Score:** {report.risk_score:.1f} / 10.0\n\n"
        
        md += f"## Executive Summary\n{report.executive_summary}\n\n"
        
        md += f"## Findings Overview\n"
        md += f"- **Critical:** {len(report.critical_findings)}\n"
        md += f"- **High:** {len(report.high_findings)}\n"
        md += f"- **Medium:** {len(report.medium_findings)}\n"
        md += f"- **Low:** {len(report.low_findings)}\n\n"
        
        if report.critical_findings:
            md += "### [CRITICAL] Findings\n"
            for f in report.critical_findings:
                md += f"- **{f['title']}** ({f.get('host', 'N/A')})\n  {f['description']}\n"
        
        if report.high_findings:
            md += "### [HIGH] Findings\n"
            for f in report.high_findings:
                md += f"- **{f['title']}** ({f.get('host', 'N/A')})\n  {f['description']}\n"
        
        md += f"\n## Remediation Plan\n{report.remediation_plan}\n"
        
        return md

    def save_report(self, report: AnalystReport, directory: str) -> Path:
        p = Path(directory)
        p.mkdir(parents=True, exist_ok=True)
        filename = f"analyst_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        report_path = p / filename
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report.markdown)
        return report_path
