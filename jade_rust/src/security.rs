//! Layer 3 & 4: Security Policy + Injection Detection

use crate::schema::JadeSkill;
use std::collections::HashSet;

/// Dangerous patterns that indicate code injection
const INJECTION_PATTERNS: &[&str] = &[
    "eval(", "exec(", "import ", "__import__",
    "subprocess", "os.system", "os.popen",
    "child_process", "require(", "Function(",
    "<script", "javascript:", "data:text/html",
    "; DROP ", "UNION SELECT", "OR 1=1",
    "${", "$(", "`", "\\x00",
];

/// Suspicious environment variable patterns
const SENSITIVE_ENV_PATTERNS: &[&str] = &[
    "AWS_SECRET", "PRIVATE_KEY", "PASSWORD",
    "DATABASE_URL", "MONGO_URI",
];

pub fn validate_security(skill: &JadeSkill) -> Vec<(String, String)> {
    let mut issues = Vec::new(); // (severity, message)
    let security = &skill.security;

    // Check sandbox level
    if security.sandbox != "strict" && security.sandbox != "standard" {
        issues.push(("error".into(),
            format!("Unknown sandbox level: '{}'. Must be 'strict' or 'standard'", security.sandbox)));
    }

    // Check network whitelist
    for domain in &security.network_whitelist {
        if domain == "*" && security.sandbox == "strict" {
            issues.push(("warning".into(),
                "Wildcard '*' in network_whitelist with strict sandbox".into()));
        }
        // Check for suspicious domains
        let lower = domain.to_lowercase();
        if lower == "localhost" || lower.starts_with("127.") || lower.starts_with("10.")
            || lower.starts_with("192.168.") || lower.starts_with("0.0.0.0") {
            issues.push(("warning".into(),
                format!("Suspicious domain in whitelist: '{}'", domain)));
        }
    }

    // Check timeout
    if security.max_execution_time_ms == 0 {
        issues.push(("warning".into(), "No execution timeout set".into()));
    }
    if security.max_execution_time_ms > 300_000 {
        issues.push(("warning".into(),
            format!("Very long timeout: {}ms (>5min)", security.max_execution_time_ms)));
    }

    // Scan all string values for injection
    let skill_json = serde_json::to_string(skill).unwrap_or_default();
    for pattern in INJECTION_PATTERNS {
        if skill_json.contains(pattern) {
            // Check if it's in a legitimate context (e.g., description mentioning eval)
            // For now, flag all occurrences
            issues.push(("error".into(),
                format!("Potential code injection: pattern '{}' found in skill", pattern)));
        }
    }

    // Check env_whitelist for sensitive vars
    for env in &security.env_whitelist {
        let upper = env.to_uppercase();
        for pattern in SENSITIVE_ENV_PATTERNS {
            if upper.contains(pattern) {
                issues.push(("warning".into(),
                    format!("Sensitive env var pattern '{}' in env_whitelist", env)));
            }
        }
    }

    issues
}

/// Check if a domain matches a whitelist entry
pub fn domain_matches_whitelist(domain: &str, whitelist: &[String]) -> bool {
    for allowed in whitelist {
        if allowed == "*" {
            return true;
        }
        if domain == allowed {
            return true;
        }
        if allowed.starts_with("*.") && domain.ends_with(&allowed[1..]) {
            return true;
        }
    }
    false
}
