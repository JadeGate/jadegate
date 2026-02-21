//! Layer 5: Cryptographic Verification

use ed25519_dalek::{Signature, VerifyingKey, Verifier};
use sha2::{Sha256, Digest};
use base64::Engine;
use base64::engine::general_purpose::STANDARD as BASE64;

/// Verify an Ed25519 signature
pub fn verify_signature(
    public_key_b64: &str,
    content: &[u8],
    signature_b64: &str,
) -> Result<bool, String> {
    // Decode public key
    let pk_bytes = BASE64.decode(public_key_b64)
        .map_err(|e| format!("Invalid public key base64: {}", e))?;

    let pk_array: [u8; 32] = pk_bytes.try_into()
        .map_err(|_| "Public key must be 32 bytes")?;

    let verifying_key = VerifyingKey::from_bytes(&pk_array)
        .map_err(|e| format!("Invalid public key: {}", e))?;

    // Decode signature
    let sig_bytes = BASE64.decode(signature_b64)
        .map_err(|e| format!("Invalid signature base64: {}", e))?;

    let sig_array: [u8; 64] = sig_bytes.try_into()
        .map_err(|_| "Signature must be 64 bytes")?;

    let signature = Signature::from_bytes(&sig_array);

    // Verify
    Ok(verifying_key.verify(content, &signature).is_ok())
}

/// Compute SHA-256 hash of content
pub fn content_hash(content: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(content);
    let result = hasher.finalize();
    format!("sha256:{}", hex::encode(result))
}

/// Compute fingerprint of a public key
pub fn key_fingerprint(public_key_b64: &str) -> Result<String, String> {
    let pk_bytes = BASE64.decode(public_key_b64)
        .map_err(|e| format!("Invalid base64: {}", e))?;

    let mut hasher = Sha256::new();
    hasher.update(&pk_bytes);
    let result = hasher.finalize();
    Ok(format!("SHA256:{}", BASE64.encode(result)))
}
