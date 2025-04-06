# -*- coding: utf-8 -*-
"""
@file: agentfy/common/security/validators.py
@desc: Validate user input for security issues, including SQL injection, XSS, and prompt injection.
@auth: Callmeiks
"""
import re
import html
from typing import List, Dict, Any, Optional
from ..models.messages import SecurityCheckResult, SecurityIssue


class SecurityValidator:
    """Security validator for checking user input for malicious content."""

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r'(\s|^)(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|UNION|CREATE|WHERE)(\s)',
        r'(\s|^)(OR|AND)(\s)+(\d|\w)+(\s)*=(\s)*(\d|\w)+',
        r'--',
        r'\/\*.*\*\/',
        r';(\s)*(SELECT|INSERT|UPDATE|DELETE|DROP)',
        r'1=1',
        r'1\s*=\s*1',
    ]

    # XSS patterns
    XSS_PATTERNS = [
        r'<script\b[^>]*>.*?<\/script>',
        r'javascript:',
        r'onerror=',
        r'onload=',
        r'eval\(',
        r'document\.cookie',
        r'<img[^>]+src[^>]*=',
    ]

    # Prompt injection patterns
    PROMPT_INJECTION_PATTERNS = [
        r'ignore previous instructions',
        r'ignore above instructions',
        r'disregard previous',
        r'forget your instructions',
        r'override previous instructions',
        r'override above instructions',
        r'override previous command',
        r'override above command',
        r'new instructions:',
        r'you are now',
        r'you will now',
        r'you must now',
    ]

    def check_for_sql_injection(self, text: str) -> List[Dict[str, Any]]:
        """Check for SQL injection attacks in the input text."""
        issues = []

        if not text:
            return issues

        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append({
                    "type": "SQL_INJECTION",
                    "details": "Potential SQL injection pattern detected",
                    "severity": "HIGH"
                })
                break

        return issues

    def check_for_xss(self, text: str) -> List[Dict[str, Any]]:
        """Check for XSS attacks in the input text."""
        issues = []

        if not text:
            return issues

        for pattern in self.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append({
                    "type": "XSS",
                    "details": "Potential cross-site scripting pattern detected",
                    "severity": "HIGH"
                })
                break

        return issues

    def check_for_prompt_injection(self, text: str) -> List[Dict[str, Any]]:
        """Check for prompt injection attacks in the input text."""
        issues = []

        if not text:
            return issues

        for pattern in self.PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append({
                    "type": "PROMPT_INJECTION",
                    "details": "Potential prompt injection pattern detected",
                    "severity": "MEDIUM"
                })
                break

        return issues

    def check_for_injection(self, text: str) -> SecurityCheckResult:
        """Perform all security checks on the input text."""
        if not text:
            return SecurityCheckResult(is_safe=True)

        issues = []

        # Check for SQL injection
        sql_issues = self.check_for_sql_injection(text)
        issues.extend(sql_issues)

        # Check for XSS
        xss_issues = self.check_for_xss(text)
        issues.extend(xss_issues)

        # Check for prompt injection
        prompt_issues = self.check_for_prompt_injection(text)
        issues.extend(prompt_issues)

        # If any issues were found, mark as unsafe
        if issues:
            detected_issues = [SecurityIssue(**issue) for issue in issues]
            return SecurityCheckResult(
                is_safe=False,
                detected_issues=detected_issues,
                mitigation_applied=False
            )

        return SecurityCheckResult(is_safe=True)