import datetime

# ponytail: Human-First Mission Interaction Dashboard (Phase C).
# Renders exception-first "Needs You" status, cost, risk, and verified outcomes.
# Formats clean, distraction-free markdown/terminal output for delegating users.

class MissionDashboard:
    def __init__(self, engine):
        self.engine = engine

    def render_view(self):
        """Renders the complete human-first mission status view."""
        m = self.engine.mission or {}
        meta = m.get("metadata", {})
        objective = m.get("objective", {}).get("outcome", "No mission loaded")
        state = self.engine.state
        metrics = self.engine.get_metrics()
        spent = metrics["budget_spent"]

        # Needs You section: active if in NEEDS_INPUT, PAUSED, or RECOVERING
        needs_you_alert = None
        if state == "NEEDS_INPUT":
            needs_you_alert = "⚠️ ACTION REQUIRED: Mission is blocked waiting for your input or authorization."
        elif state == "PAUSED":
            needs_you_alert = "⏸️ PAUSED: Execution suspended by operator. Resume when ready."
        elif state == "RECOVERING":
            needs_you_alert = "🔄 RECOVERING: An automated verification failed. The engine is attempting recovery."
        elif state == "FAILED":
            needs_you_alert = "❌ FAILED: Mission failed acceptance criteria or exceeded retry budget."

        lines = [
            "==================================================",
            f" MISSION CONTROL: {meta.get('id', 'UNNAMED')}",
            "==================================================",
            f"Goal:     {objective}",
            f"Status:   [{state}]",
        ]

        if needs_you_alert:
            lines.extend([
                "--------------------------------------------------",
                f"🚨 NEEDS YOU:",
                f"   {needs_you_alert}",
                "--------------------------------------------------"
            ])

        lines.extend([
            f"Progress: Actions Executed: {spent['actions']} | Trajectory Events: {metrics['trajectory_length']}",
            f"Spend:    Tokens: {spent['tokens']} | Cost: ${spent['usd']:.4f} USD",
            f"Tax:      Control Plane Overhead: {metrics['control_plane_tax']:.1%}",
            "--------------------------------------------------",
            "EVIDENCE & VERIFICATION STATUS:"
        ])

        required_criteria = m.get("success", {}).get("all", [])
        if not required_criteria:
            lines.append("   (No formal criteria defined)")
        else:
            for crit in required_criteria:
                ev = self.engine.evidence_store.get(crit)
                if not ev:
                    lines.append(f"   [ ] {crit}: Awaiting Evidence")
                elif ev["result"] == "SATISFIED":
                    tier_str = ev.get("tier", "unknown")
                    lines.append(f"   [✓] {crit}: VERIFIED ({tier_str})")
                else:
                    lines.append(f"   [✗] {crit}: FAILED ({ev['result']})")

        lines.append("==================================================")
        return "\n".join(lines)

    def user_pause(self):
        """User requests immediate pause."""
        self.engine.pause(reason="Operator requested pause from dashboard")
        return "Mission paused successfully."

    def user_resume(self):
        """User resumes execution."""
        self.engine.resume()
        return "Mission resumed."

    def user_takeover(self, reason="Manual intervention"):
        """User takes over control from autonomous loop."""
        self.engine.takeover(operator_id="dashboard_user", reason=reason)
        return "Operator takeover initiated. Autonomous actions blocked until resume."

    def user_cancel(self, reason="Operator cancelled"):
        """User cancels mission."""
        self.engine.cancel(reason=reason)
        return "Mission cancelled."
