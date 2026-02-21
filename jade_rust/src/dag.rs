//! Layer 2: DAG Integrity Verification

use crate::schema::JadeSkill;
use std::collections::{HashMap, HashSet, VecDeque};

/// Verify DAG is acyclic and well-formed
pub fn validate_dag(skill: &JadeSkill) -> Vec<String> {
    let mut errors = Vec::new();
    let dag = &skill.execution_dag;

    // Build adjacency list
    let mut adj: HashMap<&str, Vec<&str>> = HashMap::new();
    let mut in_degree: HashMap<&str, usize> = HashMap::new();

    for node in &dag.nodes {
        adj.entry(node.id.as_str()).or_default();
        in_degree.entry(node.id.as_str()).or_insert(0);
    }

    for edge in &dag.edges {
        adj.entry(edge.from.as_str()).or_default().push(&edge.to);
        *in_degree.entry(edge.to.as_str()).or_insert(0) += 1;
    }

    // Kahn's algorithm for cycle detection
    let mut queue: VecDeque<&str> = in_degree
        .iter()
        .filter(|(_, &deg)| deg == 0)
        .map(|(&id, _)| id)
        .collect();

    let mut visited = 0;
    while let Some(node) = queue.pop_front() {
        visited += 1;
        if let Some(neighbors) = adj.get(node) {
            for &next in neighbors {
                if let Some(deg) = in_degree.get_mut(next) {
                    *deg -= 1;
                    if *deg == 0 {
                        queue.push_back(next);
                    }
                }
            }
        }
    }

    if visited != dag.nodes.len() {
        errors.push(format!(
            "DAG contains a cycle ({} of {} nodes reachable)",
            visited,
            dag.nodes.len()
        ));
    }

    // Check for orphan nodes (no incoming or outgoing edges)
    if dag.nodes.len() > 1 {
        let connected: HashSet<&str> = dag
            .edges
            .iter()
            .flat_map(|e| vec![e.from.as_str(), e.to.as_str()])
            .collect();

        for node in &dag.nodes {
            if !connected.contains(node.id.as_str()) && dag.nodes.len() > 1 {
                errors.push(format!("Orphan node: {} (not connected to DAG)", node.id));
            }
        }
    }

    errors
}

/// Get topological execution order
pub fn topological_sort(skill: &JadeSkill) -> Result<Vec<String>, String> {
    let dag = &skill.execution_dag;
    let mut adj: HashMap<&str, Vec<&str>> = HashMap::new();
    let mut in_degree: HashMap<&str, usize> = HashMap::new();

    for node in &dag.nodes {
        adj.entry(node.id.as_str()).or_default();
        in_degree.entry(node.id.as_str()).or_insert(0);
    }

    for edge in &dag.edges {
        adj.entry(edge.from.as_str()).or_default().push(&edge.to);
        *in_degree.entry(edge.to.as_str()).or_insert(0) += 1;
    }

    let mut queue: VecDeque<&str> = in_degree
        .iter()
        .filter(|(_, &deg)| deg == 0)
        .map(|(&id, _)| id)
        .collect();

    let mut order = Vec::new();
    while let Some(node) = queue.pop_front() {
        order.push(node.to_string());
        if let Some(neighbors) = adj.get(node) {
            for &next in neighbors {
                if let Some(deg) = in_degree.get_mut(next) {
                    *deg -= 1;
                    if *deg == 0 {
                        queue.push_back(next);
                    }
                }
            }
        }
    }

    if order.len() != dag.nodes.len() {
        Err("Cycle detected in DAG".into())
    } else {
        Ok(order)
    }
}
