//! DAG Executor (Rust runtime)
//! Placeholder for full execution engine

use crate::schema::JadeSkill;
use crate::dag;

pub struct JadeExecutor {
    pub dry_run: bool,
}

impl JadeExecutor {
    pub fn new(dry_run: bool) -> Self {
        Self { dry_run }
    }

    pub fn execute(&self, skill: &JadeSkill, inputs: serde_json::Value) -> Result<serde_json::Value, String> {
        let order = dag::topological_sort(skill)?;

        if self.dry_run {
            return Ok(serde_json::json!({
                "dry_run": true,
                "execution_order": order,
                "node_count": skill.execution_dag.nodes.len(),
            }));
        }

        // TODO: Full execution with HTTP client, template engine, etc.
        Ok(serde_json::json!({
            "status": "executed",
            "execution_order": order,
        }))
    }
}
