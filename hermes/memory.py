import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

class SessionMemory:
    def __init__(self, session_dir: str = "hermes_sessions", session_id: Optional[str] = None):
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure .gitignore exists in sessions dir
        gitignore_path = self.session_dir / ".gitignore"
        if not gitignore_path.exists():
            with open(gitignore_path, "w") as f:
                f.write("*\n!.gitignore\n")
        
        if not session_id:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_id = session_id
        
        self.session_path = self.session_dir / self.session_id
        self.session_path.mkdir(exist_ok=True)
        
        self.transcript_path = self.session_path / "transcript.jsonl"
        self.findings_path = self.session_path / "findings_index.json"
        
        # Ensure findings index exists
        if not self.findings_path.exists():
            with open(self.findings_path, "w") as f:
                json.dump([], f)

    def append_turn(self, role: str, content: str, metadata: Dict[str, Any] = None) -> None:
        """Add a single message turn to the session transcript."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content
        }
        if metadata:
            entry.update(metadata)
            
        with open(self.transcript_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def append_findings(self, findings: List[Dict[str, Any]]) -> None:
        """Append and deduplicate findings to the session index."""
        if not findings:
            return
            
        all_findings = self.load_findings()
        all_findings.extend(findings)
        
        # Deduplication by (title, host, port)
        seen = set()
        deduped = []
        for f in all_findings:
            key = (f.get("title"), f.get("host"), f.get("port"))
            if key not in seen:
                seen.add(key)
                deduped.append(f)
        
        with open(self.findings_path, "w", encoding="utf-8") as f:
            json.dump(deduped, f, indent=2)

    def load_transcript(self) -> List[Dict[str, Any]]:
        """Load all turns from the transcript file."""
        if not self.transcript_path.exists():
            return []
        
        turns = []
        with open(self.transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        turns.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return turns

    def load_findings(self) -> List[Dict[str, Any]]:
        """Load all findings from the index."""
        if not self.findings_path.exists():
            return []
        try:
            with open(self.findings_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    def get_context_summary(self, max_turns: int = 20) -> str:
        """Return a brief textual summary of the current session state."""
        findings = self.load_findings()
        if not findings:
            return "No findings recorded in this session yet."
        
        summary = f"Session {self.session_id} contains {len(findings)} unique findings.\n"
        # Show a snippet of the most recent findings
        for f in findings[-5:]:
            summary += f"- [{f.get('severity', 'info').upper()}] {f.get('title')} ({f.get('host', 'N/A')})\n"
        return summary

    def save_analyst_report(self, report_content: str, filename: Optional[str] = None) -> Path:
        """Save a generated Markdown report to the session's reports directory."""
        reports_dir = self.session_path / "reports"
        reports_dir.mkdir(exist_ok=True)
        
        if not filename:
            filename = f"analyst_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            
        report_path = reports_dir / filename
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        return report_path
