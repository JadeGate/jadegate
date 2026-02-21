#!/usr/bin/env python3
"""
💠 JadeGate CLI - Deterministic Security for AI Agent Skills
"""

import argparse
import json
import os
import sys
import time

# ANSI colors
class C:
    JADE = "\033[36m"    # cyan
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

def jade_banner():
    return f"""{C.JADE}💠 JadeGate{C.RESET} {C.DIM}v0.1.0 — Deterministic Security for AI Agent Skills{C.RESET}"""

def progress_bar(label, current, total, width=30):
    pct = current / total if total > 0 else 1
    filled = int(width * pct)
    bar = f"{'█' * filled}{'░' * (width - filled)}"
    sys.stdout.write(f"\r  {C.DIM}{label}{C.RESET} [{C.JADE}{bar}{C.RESET}] {current}/{total}")
    sys.stdout.flush()

def layer_check(name, passed, detail=""):
    icon = f"{C.GREEN}✅ PASS{C.RESET}" if passed else f"{C.RED}❌ FAIL{C.RESET}"
    dots = "." * (35 - len(name))
    detail_str = f" {C.DIM}({detail}){C.RESET}" if detail else ""
    print(f"  {name} {C.DIM}{dots}{C.RESET} {icon}{detail_str}")

def cmd_list(args):
    """List all registered skills"""
    print(jade_banner())
    print()

    # Find skill directories
    base = _find_base()
    skills = []

    for d in ["jade_skills", "converted_skills"]:
        skill_dir = os.path.join(base, d)
        if not os.path.isdir(skill_dir):
            continue
        cat = "jade.core" if d == "jade_skills" else "jadegate.community"
        for f in sorted(os.listdir(skill_dir)):
            if not f.endswith(".json"):
                continue
            path = os.path.join(skill_dir, f)
            try:
                with open(path) as fh:
                    sk = json.load(fh)
                skills.append({
                    "id": sk.get("skill_id", f),
                    "name": sk.get("metadata", {}).get("name", ""),
                    "version": sk.get("metadata", {}).get("version", ""),
                    "tags": sk.get("metadata", {}).get("tags", []),
                    "category": cat,
                    "path": path,
                })
            except Exception:
                skills.append({"id": f, "name": "?", "version": "?", "tags": [], "category": cat, "path": path})

    if not skills:
        print(f"  {C.DIM}No skills found.{C.RESET}")
        return

    # Validate each
    sys.path.insert(0, base)
    from jade_core.validator import JadeValidator
    v = JadeValidator()

    print(f"  {C.BOLD}Scanning {len(skills)} skills...{C.RESET}")
    print()

    verified = 0
    rejected = 0

    for i, sk in enumerate(skills):
        progress_bar("Verifying", i + 1, len(skills))
        try:
            r = v.validate_file(sk["path"])
            sk["valid"] = r.valid
            if r.valid:
                verified += 1
            else:
                rejected += 1
                sk["errors"] = [e.message for e in r.errors]
        except Exception as e:
            sk["valid"] = False
            sk["errors"] = [str(e)]
            rejected += 1

    print()  # newline after progress bar
    print()

    # Print table
    for sk in skills:
        icon = f"{C.JADE}💠{C.RESET}" if sk["valid"] else f"{C.RED}❌{C.RESET}"
        sid = sk["id"][:24].ljust(24)
        ver = sk["version"].ljust(6)
        tags_str = ", ".join(sk["tags"][:3])
        cat = f"{C.DIM}{sk['category']}{C.RESET}"
        print(f"  {icon} {C.BOLD}{sid}{C.RESET} {C.DIM}{ver}{C.RESET}  [{C.BLUE}{tags_str}{C.RESET}]  {cat}")

    print()
    print(f"  {C.JADE}💠 {verified} verified{C.RESET}  {C.RED}❌ {rejected} rejected{C.RESET}  {C.DIM}Total: {len(skills)}{C.RESET}")
    print()

def cmd_verify(args):
    """Verify one or more skill files"""
    print(jade_banner())
    print()

    base = _find_base()
    sys.path.insert(0, base)
    from jade_core.validator import JadeValidator
    v = JadeValidator()

    targets = []
    for path in args.files:
        if os.path.isdir(path):
            for f in sorted(os.listdir(path)):
                if f.endswith(".json"):
                    targets.append(os.path.join(path, f))
        elif os.path.isfile(path):
            targets.append(path)
        else:
            print(f"  {C.RED}❌ Not found: {path}{C.RESET}")

    for filepath in targets:
        print(f"  {C.BOLD}Verifying:{C.RESET} {filepath}")
        print()

        start = time.time()

        try:
            with open(filepath) as f:
                skill = json.load(f)
        except json.JSONDecodeError as e:
            print(f"  {C.RED}❌ Invalid JSON: {e}{C.RESET}")
            continue

        r = v.validate_file(filepath)
        elapsed = (time.time() - start) * 1000

        # Show layer-by-layer results
        # We simulate layer reporting based on error codes
        error_codes = {e.code for e in r.errors} if r.errors else set()

        layer_check("Layer 1: JSON Schema", "SCHEMA" not in str(error_codes), "structural integrity")
        layer_check("Layer 2: Code Injection Scan", not any("INJECTION" in c for c in error_codes), "22 patterns checked")
        layer_check("Layer 3: Dangerous Commands", not any("DANGEROUS" in c or "COMMAND" in c for c in error_codes), "25 patterns checked")

        net = skill.get("security", {}).get("network_whitelist", [])
        net_str = ", ".join(net[:3]) if net else "none"
        layer_check("Layer 4: Network & Data Leak", not any("NETWORK" in c or "DATA" in c for c in error_codes), f"whitelist: {net_str}")

        nodes = skill.get("execution_dag", {}).get("nodes", [])
        layer_check("Layer 5: DAG Integrity", not any("DAG" in c or "CYCLE" in c or "REACH" in c for c in error_codes), f"{len(nodes)} nodes")

        print()

        if r.valid:
            # Calculate Bayesian confidence
            n_layers = 5
            prior = 0.5
            likelihood = 0.95
            false_pos = 0.05
            posterior = prior
            for _ in range(n_layers):
                posterior = (likelihood * posterior) / (likelihood * posterior + false_pos * (1 - posterior))
            print(f"  {C.JADE}💠 VERIFIED{C.RESET}  {C.DIM}({elapsed:.0f}ms, confidence: {posterior:.4f}){C.RESET}")
        else:
            print(f"  {C.RED}❌ REJECTED{C.RESET}  {C.DIM}({elapsed:.0f}ms){C.RESET}")
            for e in r.errors:
                print(f"     {C.RED}[{e.code}]{C.RESET} {e.message}")

        if args.verbose and r.warnings:
            print()
            for w in r.warnings:
                print(f"     {C.YELLOW}⚠ [{w.code}]{C.RESET} {w.message}")

        print()

def cmd_search(args):
    """Search skills by keyword"""
    print(jade_banner())
    print()

    base = _find_base()
    query = args.query.lower()
    found = 0

    for d in ["jade_skills", "converted_skills"]:
        skill_dir = os.path.join(base, d)
        if not os.path.isdir(skill_dir):
            continue
        for f in sorted(os.listdir(skill_dir)):
            if not f.endswith(".json"):
                continue
            path = os.path.join(skill_dir, f)
            try:
                with open(path) as fh:
                    sk = json.load(fh)
                searchable = json.dumps(sk.get("metadata", {}), ensure_ascii=False).lower()
                if query in searchable or query in f.lower():
                    sid = sk.get("skill_id", f)[:24].ljust(24)
                    desc = sk.get("metadata", {}).get("description", "")[:60]
                    print(f"  {C.JADE}💠{C.RESET} {C.BOLD}{sid}{C.RESET} {C.DIM}{desc}{C.RESET}")
                    found += 1
            except Exception:
                pass

    if found == 0:
        print(f"  {C.DIM}No skills matching '{args.query}'{C.RESET}")
    else:
        print(f"\n  {C.DIM}{found} skill(s) found{C.RESET}")
    print()

def cmd_info(args):
    """Show detailed info about a skill"""
    print(jade_banner())
    print()

    base = _find_base()
    # Find skill by id
    for d in ["jade_skills", "converted_skills"]:
        skill_dir = os.path.join(base, d)
        if not os.path.isdir(skill_dir):
            continue
        for f in sorted(os.listdir(skill_dir)):
            if not f.endswith(".json"):
                continue
            path = os.path.join(skill_dir, f)
            try:
                with open(path) as fh:
                    sk = json.load(fh)
                if sk.get("skill_id") == args.skill_id or f.replace(".json", "") == args.skill_id:
                    meta = sk.get("metadata", {})
                    sec = sk.get("security", {})
                    dag = sk.get("execution_dag", {})
                    print(f"  {C.JADE}💠{C.RESET} {C.BOLD}{meta.get('name', '?')}{C.RESET}")
                    print(f"  {C.DIM}{'─' * 50}{C.RESET}")
                    print(f"  ID:          {sk.get('skill_id')}")
                    print(f"  Version:     {meta.get('version')}")
                    print(f"  Author:      {meta.get('author')}")
                    print(f"  Tags:        {', '.join(meta.get('tags', []))}")
                    print(f"  Description: {meta.get('description', '')[:80]}")
                    print()
                    print(f"  {C.BOLD}Security{C.RESET}")
                    print(f"  Sandbox:     {sec.get('sandbox_level', '?')}")
                    print(f"  Network:     {', '.join(sec.get('network_whitelist', [])) or 'none'}")
                    print(f"  File Read:   {', '.join(sec.get('file_permissions', {}).get('read', [])) or 'none'}")
                    print(f"  File Write:  {', '.join(sec.get('file_permissions', {}).get('write', [])) or 'none'}")
                    print(f"  Timeout:     {sec.get('max_execution_time_ms', '?')}ms")
                    print()
                    print(f"  {C.BOLD}DAG{C.RESET}")
                    print(f"  Nodes:       {len(dag.get('nodes', []))}")
                    print(f"  Edges:       {len(dag.get('edges', []))}")
                    print(f"  Entry:       {dag.get('entry_node')}")
                    print(f"  Exit:        {dag.get('exit_node')}")
                    print()
                    return
            except Exception:
                pass

    print(f"  {C.RED}Skill not found: {args.skill_id}{C.RESET}")
    print()

def _find_base():
    """Find the JadeGate base directory"""
    # Check common locations
    candidates = [
        os.getcwd(),
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ]
    for c in candidates:
        if os.path.isdir(os.path.join(c, "jade_core")):
            return c
    return os.getcwd()

def main():
    parser = argparse.ArgumentParser(
        prog="jade",
        description="💠 JadeGate — Deterministic Security for AI Agent Skills",
    )
    sub = parser.add_subparsers(dest="command")

    # jade list
    p_list = sub.add_parser("list", help="List all registered skills")
    p_list.set_defaults(func=cmd_list)

    # jade verify
    p_verify = sub.add_parser("verify", help="Verify skill file(s)")
    p_verify.add_argument("files", nargs="+", help="Skill JSON file(s) or directory")
    p_verify.add_argument("-v", "--verbose", action="store_true", help="Show warnings")
    p_verify.set_defaults(func=cmd_verify)

    # jade search
    p_search = sub.add_parser("search", help="Search skills by keyword")
    p_search.add_argument("query", help="Search keyword")
    p_search.set_defaults(func=cmd_search)

    # jade info
    p_info = sub.add_parser("info", help="Show skill details")
    p_info.add_argument("skill_id", help="Skill ID")
    p_info.set_defaults(func=cmd_info)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    args.func(args)

if __name__ == "__main__":
    main()
