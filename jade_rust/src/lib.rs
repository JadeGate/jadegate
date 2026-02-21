//! 💠 JadeGate — Deterministic Security for AI Agent Skills
//!
//! Zero-trust verification engine for JADE skill files.
//! Pure Rust, zero runtime dependencies on Python.

pub mod schema;
pub mod dag;
pub mod security;
pub mod crypto;
pub mod validator;
pub mod executor;

pub use validator::JadeValidator;
pub use executor::JadeExecutor;
