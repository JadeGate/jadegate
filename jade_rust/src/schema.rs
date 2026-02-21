//! Layer 1: Schema Validation

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JadeSkill {
    pub jade_version: String,
    pub skill_id: String,
    pub metadata: Metadata,
    pub input_schema: serde_json::Value,
    pub output_schema: serde_json::Value,
    pub execution_dag: ExecutionDag,
    pub security: SecurityPolicy,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub jade_signature: Option<JadeSignature>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub community_signatures: Option<Vec<CommunitySignature>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Metadata {
    pub name: String,
    pub description: String,
    pub version: String,
    #[serde(default)]
    pub author: String,
    #[serde(default)]
    pub tags: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionDag {
    pub nodes: Vec<DagNode>,
    pub edges: Vec<DagEdge>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DagNode {
    pub id: String,
    #[serde(default)]
    pub action: String,
    #[serde(default)]
    pub params: HashMap<String, serde_json::Value>,
    #[serde(default)]
    pub timeout_ms: Option<u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DagEdge {
    pub from: String,
    pub to: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub condition: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityPolicy {
    pub sandbox: String,
    #[serde(default)]
    pub network_whitelist: Vec<String>,
    #[serde(default)]
    pub max_execution_time_ms: u64,
    #[serde(default)]
    pub env_whitelist: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JadeSignature {
    pub signer: String,
    pub algorithm: String,
    pub public_key: String,
    pub content_hash: String,
    pub signature: String,
    #[serde(default)]
    pub signed_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommunitySignature {
    pub signer_fingerprint: String,
    pub public_key: String,
    pub content_hash: String,
    pub signature: String,
    pub signed_at: String,
    pub trust_level: String,
}

/// Validate schema structure
pub fn validate_schema(skill: &JadeSkill) -> Vec<String> {
    let mut errors = Vec::new();

    if skill.jade_version.is_empty() {
        errors.push("Missing jade_version".into());
    }
    if skill.skill_id.is_empty() {
        errors.push("Missing skill_id".into());
    }
    if skill.metadata.name.is_empty() {
        errors.push("Missing metadata.name".into());
    }
    if skill.execution_dag.nodes.is_empty() {
        errors.push("DAG has no nodes".into());
    }

    // Validate node IDs are unique
    let mut seen = std::collections::HashSet::new();
    for node in &skill.execution_dag.nodes {
        if !seen.insert(&node.id) {
            errors.push(format!("Duplicate node ID: {}", node.id));
        }
    }

    // Validate edges reference existing nodes
    let node_ids: std::collections::HashSet<_> = skill.execution_dag.nodes.iter().map(|n| &n.id).collect();
    for edge in &skill.execution_dag.edges {
        if !node_ids.contains(&edge.from) {
            errors.push(format!("Edge references unknown node: {}", edge.from));
        }
        if !node_ids.contains(&edge.to) {
            errors.push(format!("Edge references unknown node: {}", edge.to));
        }
    }

    errors
}
