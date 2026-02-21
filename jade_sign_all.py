#!/usr/bin/env python3
"""
💠 JadeGate Batch Signer
========================
用你的 root 私钥给所有 skill 盖印。

用法:
  python jade_sign_all.py
  
会扫描 jade_skills/ 和 converted_skills/ 下所有 .json 文件，
逐个签名并写入 jade_signature 字段 + .sig.json 文件。
"""

import os
import sys
import json
import getpass

# 把 jade_core 加入路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jade_core.crypto import JadeKeyPair, JadeSkillSigner

def main():
    print()
    print("  💠 JadeGate Batch Signer")
    print("  ========================")
    print("  用你的 root 私钥给所有 skill 盖印。")
    print()
    
    # 输入私钥
    private_key = getpass.getpass("  输入你的 root 私钥 (jade-sk-root-...): ")
    private_key = private_key.strip()
    
    if not private_key.startswith("jade-sk-"):
        print("\n  ❌ 无效的私钥格式，应以 jade-sk- 开头")
        sys.exit(1)
    
    try:
        kp = JadeKeyPair.from_private_key(private_key)
    except Exception as e:
        print(f"\n  ❌ 私钥加载失败: {e}")
        sys.exit(1)
    
    print(f"\n  ✅ 密钥加载成功")
    print(f"  公钥: {kp.public_key_str}")
    print(f"  指纹: {kp.fingerprint}")
    print(f"  角色: {kp.role}")
    print()
    
    confirm = input("  确认用这个密钥签名所有 skill? [Y/n]: ").strip().lower()
    if confirm == 'n':
        print("  取消。")
        sys.exit(0)
    
    signer = JadeSkillSigner(kp)
    
    # 扫描所有 skill 目录
    skill_dirs = ['jade_skills/mcp', 'converted_skills']
    signed = 0
    failed = 0
    
    print()
    for d in skill_dirs:
        if not os.path.exists(d):
            print(f"  ⚠️  目录不存在: {d}")
            continue
        
        for fname in sorted(os.listdir(d)):
            if not fname.endswith('.json') or fname.endswith('.sig.json'):
                continue
            
            fpath = os.path.join(d, fname)
            try:
                result = signer.sign_skill(fpath)
                sig = result['jade_signature']
                print(f"  💠 {fname}")
                print(f"     hash: {sig['content_hash'][:30]}...")
                signed += 1
            except Exception as e:
                print(f"  ❌ {fname}: {e}")
                failed += 1
    
    print()
    print(f"  ════════════════════════════════════")
    print(f"  签名完成: {signed} 成功, {failed} 失败")
    print(f"  签名者: {kp.fingerprint}")
    print(f"  ════════════════════════════════════")
    print()
    
    if signed > 0:
        print("  下一步:")
        print("    git add -A")
        print("    git commit -m '💠 Root CA signed all skills'")
        print("    git push")
        print()


if __name__ == "__main__":
    main()
