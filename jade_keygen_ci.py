#!/usr/bin/env python3
"""
💠 JadeGate CI Signing Key Generator
=====================================
用你的 root 私钥签发一个 CI 子密钥。
CI 子密钥只能签 skill，不能签发新 CA 或撤销证书。

用法:
  python jade_keygen_ci.py
"""

import os, sys, json, getpass, hashlib, base64, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Reuse the Ed25519 implementation from keygen
from jade_keygen_root import (
    _publickey, _signature, _checkvalid, generate_keypair
)

def main():
    print()
    print("  💠 JadeGate CI Signing Key Generator")
    print("  =====================================")
    print("  用 root 私钥签发一个权限受限的 CI 子密钥。")
    print("  CI 密钥只能签 skill，不能签发 CA 或撤销证书。")
    print()

    # 1. Input root private key
    root_sk_str = getpass.getpass("  输入 root 私钥 (jade-sk-root-...): ").strip()
    if not root_sk_str.startswith("jade-sk-root-"):
        print("\n  ❌ 必须是 root 私钥")
        sys.exit(1)

    root_seed = base64.b64decode(root_sk_str.split("-", 3)[3])
    root_pk = _publickey(root_seed)
    root_pk_b64 = base64.b64encode(root_pk).decode()
    root_fp = base64.b64encode(hashlib.sha256(root_pk).digest()).decode()

    print(f"  ✅ Root 密钥已加载")
    print(f"  Root 指纹: SHA256:{root_fp}")

    # 2. Generate CI keypair
    print("\n  ⏳ 生成 CI 子密钥...")
    ci_seed = os.urandom(32)
    ci_pk = _publickey(ci_seed)
    ci_sk_b64 = base64.b64encode(ci_seed).decode()
    ci_pk_b64 = base64.b64encode(ci_pk).decode()
    ci_fp = base64.b64encode(hashlib.sha256(ci_pk).digest()).decode()

    # 3. Create CI certificate (signed by root)
    ci_cert = {
        "jade_ca": "ci-signer",
        "version": "1.0.0",
        "issuer": "JadeGate Root CA",
        "issuer_fingerprint": f"SHA256:{root_fp}",
        "subject": "JadeGate CI Signer",
        "algorithm": "Ed25519",
        "fingerprint": f"SHA256:{ci_fp}",
        "public_key": f"jade-pk-ci-{ci_pk_b64}",
        "created": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires": "2027-02-21T00:00:00Z",
        "permissions": ["sign:skill"],  # 只能签 skill！
        "restrictions": [
            "cannot:sign:org-ca",
            "cannot:sign:revocation",
            "cannot:sign:registry"
        ]
    }

    # 4. Sign the CI cert with root key
    cert_bytes = json.dumps(ci_cert, sort_keys=True, separators=(',', ':')).encode()
    sig = _signature(cert_bytes, root_seed, root_pk)
    ci_cert["root_signature"] = base64.b64encode(sig).decode()

    # Verify
    assert _checkvalid(sig, cert_bytes, root_pk), "FATAL: signature verification failed!"

    print(f"\n  ✅ CI 子密钥已生成并由 root 签名！")
    print()
    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║  🔑 CI 私钥（存入 GitHub Secrets）                  ║")
    print("  ╚══════════════════════════════════════════════════════╝")
    print(f"  jade-sk-ci-{ci_sk_b64}")
    print()
    print(f"  指纹: SHA256:{ci_fp}")
    print(f"  权限: 仅 sign:skill")
    print(f"  签发者: SHA256:{root_fp}")
    print()

    # 5. Save CI cert
    with open('jade_schema/ci_signer_ca.json', 'w') as f:
        json.dump(ci_cert, f, indent=2)
    print("  📄 CI 证书已保存到: jade_schema/ci_signer_ca.json")

    print()
    print("  下一步:")
    print("  1. 复制上面的 CI 私钥")
    print("  2. 去 GitHub → Settings → Secrets → Actions")
    print("  3. 新建 secret: JADE_CI_SIGNING_KEY = jade-sk-ci-...")
    print("  4. git add jade_schema/ci_signer_ca.json && git commit && git push")
    print()
    print("  之后每次 PR 合并，GitHub Actions 会自动用 CI 密钥签名新 skill。")
    print("  你的 root 私钥永远不碰网络。")
    print()


if __name__ == "__main__":
    main()
