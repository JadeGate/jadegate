#!/usr/bin/env python3
"""
💠 JadeGate Root CA Key Generator
==================================
在本地生成根密钥对。私钥永远不离开你的机器。

用法:
  python jade_keygen.py
  python jade_keygen.py --passphrase "你的密码"
  python jade_keygen.py --org "Alibaba Cloud" --badge "Alibaba Authentic"

依赖: 无（纯 Python，零依赖）
"""

import hashlib
import os
import sys
import json
import base64
import datetime
import getpass

# ============================================================
# Ed25519 Pure Python (RFC 8032, zero dependencies)
# ============================================================

b = 256
q = 2**255 - 19
l_order = 2**252 + 27742317777372353535851937790883648493

def _H(m): return hashlib.sha512(m).digest()

def _expmod(b_val, e, m):
    if e == 0: return 1
    t = _expmod(b_val, e // 2, m) ** 2 % m
    if e & 1: t = (t * b_val) % m
    return t

def _inv(x): return _expmod(x, q - 2, q)

_d = -121665 * _inv(121666) % q
_I = _expmod(2, (q - 1) // 4, q)

def _xrecover(y):
    xx = (y * y - 1) * _inv(_d * y * y + 1)
    x = _expmod(xx, (q + 3) // 8, q)
    if (x * x - xx) % q != 0: x = (x * _I) % q
    if x % 2 != 0: x = q - x
    return x

_By = 4 * _inv(5)
_Bx = _xrecover(_By)
_B = [_Bx % q, _By % q]

def _edwards(P, Q):
    x1, y1 = P; x2, y2 = Q
    x3 = (x1*y2 + x2*y1) * _inv(1 + _d*x1*x2*y1*y2)
    y3 = (y1*y2 + x1*x2) * _inv(1 - _d*x1*x2*y1*y2)
    return [x3 % q, y3 % q]

def _scalarmult(P, e):
    if e == 0: return [0, 1]
    Q = _scalarmult(P, e // 2)
    Q = _edwards(Q, Q)
    if e & 1: Q = _edwards(Q, P)
    return Q

def _encodeint(y):
    bits = [(y >> i) & 1 for i in range(b)]
    return bytes([sum([bits[i*8+j] << j for j in range(8)]) for i in range(b//8)])

def _encodepoint(P):
    x, y = P
    bits = [(y >> i) & 1 for i in range(b - 1)] + [x & 1]
    return bytes([sum([bits[i*8+j] << j for j in range(8)]) for i in range(b//8)])

def _bit(h, i): return (h[i // 8] >> (i % 8)) & 1

def _publickey(sk):
    h = _H(sk)
    a = 2**(b-2) + sum(2**i * _bit(h, i) for i in range(3, b-2))
    A = _scalarmult(_B, a)
    return _encodepoint(A)

def _Hint(m):
    h = _H(m)
    return sum(2**i * _bit(h, i) for i in range(2*b))

def _signature(m, sk, pk):
    h = _H(sk)
    a = 2**(b-2) + sum(2**i * _bit(h, i) for i in range(3, b-2))
    r = _Hint(bytes([h[j] for j in range(b//8, b//4)]) + m)
    R = _scalarmult(_B, r)
    S = (r + _Hint(_encodepoint(R) + pk + m) * a) % l_order
    return _encodepoint(R) + _encodeint(S)

def _isoncurve(P):
    x, y = P
    return (-x*x + y*y - 1 - _d*x*x*y*y) % q == 0

def _decodeint(s):
    return sum(2**i * _bit(s, i) for i in range(0, b))

def _decodepoint(s):
    y = sum(2**i * _bit(s, i) for i in range(0, b-1))
    x = _xrecover(y)
    if x & 1 != _bit(s, b-1): x = q - x
    P = [x, y]
    if not _isoncurve(P): raise ValueError("point not on curve")
    return P

def _checkvalid(s, m, pk):
    if len(s) != 64 or len(pk) != 32: return False
    try:
        R = _decodepoint(s[:32])
        A = _decodepoint(pk)
    except: return False
    S = _decodeint(s[32:])
    h = _Hint(_encodepoint(R) + pk + m)
    return _scalarmult(_B, S) == _edwards(R, _scalarmult(A, h))

# ============================================================
# Key Generation
# ============================================================

def generate_keypair(role="root", passphrase=None):
    """Generate Ed25519 keypair. If passphrase given, derive seed from it + random salt."""
    if passphrase:
        salt = os.urandom(16)
        # PBKDF2-like derivation: SHA-512 iterated 100k times
        seed = hashlib.pbkdf2_hmac('sha512', passphrase.encode(), salt, 100000, dklen=32)
        salt_b64 = base64.b64encode(salt).decode()
    else:
        seed = os.urandom(32)
        salt_b64 = None

    pk = _publickey(seed)
    sk_b64 = base64.b64encode(seed).decode()
    pk_b64 = base64.b64encode(pk).decode()
    fingerprint = base64.b64encode(hashlib.sha256(pk).digest()).decode()

    # Self-test
    test_msg = b"JadeGate self-test"
    sig = _signature(test_msg, seed, pk)
    assert _checkvalid(sig, test_msg, pk), "FATAL: self-test failed!"

    return {
        "private_key": f"jade-sk-{role}-{sk_b64}",
        "public_key": f"jade-pk-{role}-{pk_b64}",
        "fingerprint": f"SHA256:{fingerprint}",
        "algorithm": "Ed25519",
        "salt": salt_b64,
        "created": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def main():
    print()
    print("  💠 JadeGate Key Generator")
    print("  ========================")
    print("  私钥在本地生成，永远不离开你的机器。")
    print()

    # Role
    print("  角色说明:")
    print("    root — 最高权限（签发一切：skill、组织CA、撤销证书）")
    print("           整个 JadeGate 只有一个 root。你是创始人，选这个。")
    print("    org  — 组织级别（只能签自己组织的 skill）")
    print("           给企业/开源组织发的二级证书用这个。")
    print()
    role = input("  密钥角色 [root/org]: ").strip() or "root"

    # Passphrase (optional)
    print()
    print("  可选：设置密码短语（passphrase）")
    print("  设置后，密钥 = 随机盐 + 你的密码 派生")
    print("  不设置则纯随机生成（更安全但必须备份）")
    print()
    use_pass = input("  使用密码短语? [y/N]: ").strip().lower()

    passphrase = None
    if use_pass == 'y':
        passphrase = getpass.getpass("  输入密码短语: ")
        confirm = getpass.getpass("  确认密码短语: ")
        if passphrase != confirm:
            print("\n  ❌ 密码不匹配，退出。")
            sys.exit(1)

    print("\n  ⏳ 生成中...")
    result = generate_keypair(role, passphrase)

    print("\n  ✅ 密钥对已生成！")
    print()
    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║  🔐 私钥（绝对保密，离线保存）                      ║")
    print("  ╚══════════════════════════════════════════════════════╝")
    print(f"  {result['private_key']}")
    print()
    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║  🌐 公钥（可以公开发布）                            ║")
    print("  ╚══════════════════════════════════════════════════════╝")
    print(f"  {result['public_key']}")
    print()
    print(f"  指纹: {result['fingerprint']}")
    print(f"  算法: {result['algorithm']}")
    print(f"  生成时间: {result['created']}")
    if result['salt']:
        print(f"  盐值: {result['salt']}（如果用密码短语，需要同时备份盐值）")
    print()

    # Save options
    save = input("  保存公钥证书到文件? [Y/n]: ").strip().lower()
    if save != 'n':
        cert = {
            "jade_ca": role,
            "version": "1.0.0",
            "issuer": f"JadeGate {role.title()} CA",
            "subject": f"JadeGate {role.title()} CA",
            "algorithm": result['algorithm'],
            "fingerprint": result['fingerprint'],
            "public_key": result['public_key'],
            "created": result['created'],
            "expires": "2036-01-01T00:00:00Z",
            "permissions": ["sign:skill", "sign:org-ca", "sign:revocation", "sign:registry"] if role == "root" else ["sign:skill"],
        }
        fname = f"jadegate_{role}_ca.json"
        with open(fname, 'w') as f:
            json.dump(cert, f, indent=2)
        print(f"\n  📄 公钥证书已保存到: {fname}")

    print()
    print("  ⚠️  请立即备份私钥！丢失后无法恢复。")
    print("  ⚠️  建议：抄写到纸上 + 加密U盘各一份。")
    print()


if __name__ == "__main__":
    main()
