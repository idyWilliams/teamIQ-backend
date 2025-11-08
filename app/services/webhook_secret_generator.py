"""
Webhook Secret Generator
Generates unique webhook secrets per project
"""

import secrets
import hashlib


def generate_webhook_secret(length: int = 32) -> str:
    """
    Generate cryptographically secure webhook secret
    Used for verifying webhook authenticity

    Returns: 32-byte hex string (64 characters)
    """
    return secrets.token_hex(length)


def generate_github_webhook_secret() -> str:
    """Generate GitHub-compatible webhook secret"""
    return generate_webhook_secret(32)


def generate_jira_webhook_secret() -> str:
    """Generate Jira-compatible webhook secret"""
    return generate_webhook_secret(24)


def generate_slack_signing_secret() -> str:
    """Generate Slack-compatible signing secret"""
    return generate_webhook_secret(32)
