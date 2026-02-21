//! 💠 5-Layer Validator — combines all verification layers

use crate::schema::{self, JadeSkill};
use crate::dag;
use crate::security;
use crate::crypto;
use serde_json;
use std::path::Path;

#[derive(Debug)]
pub struct ValidationIssue {
    pub layer: u8,
    pub severity: Severity,
    pub code: String,
    pub message: String,
}

#[derive(Debug, PartialEq)]
pub enum Severity {
    Error,
    Warning,
    Info,
}

#[derive(Debug)]
pub struct ValidationResult {
    pub valid: bool,
    pub issues: Vec<ValidationIssue>,
    pub layers_passed: u8,
}

pub struct JadeValidator;

impl JadeValidator {
    pub fn new() -> Self {
        Self
    }

    pub fn validate_file(&self, path: &Path) -> Result<ValidationResult, String> {
        let content = std::fs::read_to_string(path)
            .map_err(|e| format!("Cannot read file: {}", e))?;

        let skill: JadeSkill = serde_json::from_str(&content)
            .map_err(|e| format!("Invalid JSON: {}", e))?;

        Ok(self.validate(&skill, &content))
    }

    pub fn validate(&self, skill: &JadeSkill, raw_json: &str) -> ValidationResult {
        let mut issues = Vec::new();
        let mut layers_passed: u8 = 0;

        // Layer 1: Schema
        let schema_errors = schema::validate_schema(skill);
        if schema_errors.is_empty() {
            layers_passed = 1;
        } else {
            for err in schema_errors {
                issues.push(ValidationIssue {
                    layer: 1, severity: Severity::Error,
                    code: "SCHEMA_ERROR".into(), message: err,
                });
            }
            return ValidationResult { valid: false, issues, layers_passed };
        }

        // Layer 2: DAG
        let dag_errors = dag::validate_dag(skill);
        if dag_errors.is_empty() {
            layers_passed = 2;
        } else {
            for err in dag_errors {
                issues.push(ValidationIssue {
                    layer: 2, severity: Severity::Error,
                    code: "DAG_ERROR".into(), message: err,
                });
            }
            return ValidationResult { valid: false, issues, layers_passed };
        }

        // Layer 3 & 4: Security + Injection
        let sec_issues = security::validate_security(skill);
        let mut has_sec_error = false;
        for (severity, message) in sec_issues {
            let sev = match severity.as_str() {
                "error" => { has_sec_error = true; Severity::Error },
                "warning" => Severity::Warning,
                _ => Severity::Info,
            };
            issues.push(ValidationIssue {
                layer: 3, severity: sev,
                code: "SEC_ISSUE".into(), message,
            });
        }
        if !has_sec_error {
            layers_passed = 4;
        } else {
            return ValidationResult { valid: false, issues, layers_passed };
        }

        // Layer 5: Crypto (if signature present)
        if let Some(sig) = &skill.jade_signature {
            // Extract public key from the key string
            let pk_b64 = sig.public_key
                .strip_prefix("jade-pk-root-")
                .or_else(|| sig.public_key.strip_prefix("jade-pk-ci-"))
                .unwrap_or(&sig.public_key);

            // Compute content hash (exclude signature fields)
            let mut skill_copy = skill.clone();
            skill_copy.jade_signature = None;
            skill_copy.community_signatures = None;
            let content = serde_json::to_string(&skill_copy).unwrap_or_default();

            match crypto::verify_signature(pk_b64, content.as_bytes(), &sig.signature) {
                Ok(true) => { layers_passed = 5; },
                Ok(false) => {
                    issues.push(ValidationIssue {
                        layer: 5, severity: Severity::Error,
                        code: "SIG_INVALID".into(),
                        message: "Signature verification failed".into(),
                    });
                },
                Err(e) => {
                    issues.push(ValidationIssue {
                        layer: 5, severity: Severity::Warning,
                        code: "SIG_ERROR".into(),
                        message: format!("Cannot verify signature: {}", e),
                    });
                }
            }
        } else {
            layers_passed = 5; // No signature = pass (unsigned is valid, just not sealed)
        }

        ValidationResult {
            valid: !issues.iter().any(|i| i.severity == Severity::Error),
            issues,
            layers_passed,
        }
    }
}
