import os
import yaml

# ponytail: Lightweight Policy Engine for Filesystem and Tool Boundaries.
# Enforces sandboxing, path traversal protection, and command blacklists.

class PolicyEngine:
    def __init__(self, policy_doc=None):
        self.rules = []
        if policy_doc:
            self.load_policy(policy_doc)

    def load_policy(self, policy_doc):
        if isinstance(policy_doc, str):
            if os.path.exists(policy_doc):
                with open(policy_doc, "r", encoding="utf-8") as f:
                    policy_doc = yaml.safe_load(f)
            else:
                policy_doc = yaml.safe_load(policy_doc)
        
        self.spec = policy_doc.get("spec", policy_doc)
        self.allow_paths = [os.path.abspath(p) for p in self.spec.get("allow_paths", [])]
        self.deny_paths = [os.path.abspath(p) for p in self.spec.get("deny_paths", [])]
        self.denied_commands = self.spec.get("denied_commands", [
            "rm -rf /", "mkfs", "format", "dd if=", ":(){ :|:& };:"
        ])
        self.max_file_size_bytes = self.spec.get("max_file_size_bytes", 50 * 1024 * 1024)

    def validate_file_access(self, target_path, mode="read"):
        """
        Validates file read/write against path confinement rules.
        Prevents directory traversal and access to sensitive system paths.
        """
        abs_path = os.path.abspath(target_path)

        # Check explicit deny paths
        for d in self.deny_paths:
            if abs_path == d or abs_path.startswith(d + os.sep):
                raise PermissionError(f"Policy Violation: Path is explicitly denied by policy: {target_path}")

        # Check sensitive defaults if deny_paths not specified
        sensitive_markers = [".git" + os.sep, ".ssh" + os.sep, ".aws" + os.sep, ".env"]
        for marker in sensitive_markers:
            if marker in abs_path or abs_path.endswith(".env"):
                raise PermissionError(f"Policy Violation: Access to sensitive file/folder blocked: {target_path}")

        # If allow_paths specified, path must be inside at least one allowed directory
        if self.allow_paths:
            allowed = False
            for a in self.allow_paths:
                if abs_path == a or abs_path.startswith(a + os.sep):
                    allowed = True
                    break
            if not allowed:
                raise PermissionError(f"Policy Violation: Path outside allowed workspace boundary: {target_path}")

        return True

    def validate_command(self, cmd_string):
        """
        Validates shell command against dangerous command patterns.
        """
        cmd_lower = cmd_string.lower().strip()
        for dc in self.denied_commands:
            if dc in cmd_lower:
                raise PermissionError(f"Policy Violation: Destructive command blocked by policy: '{dc}' in '{cmd_string}'")
        return True
