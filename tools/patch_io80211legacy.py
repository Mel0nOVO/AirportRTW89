#!/usr/bin/env python3
"""
IO80211FamilyLegacy Scan & Node Bypass Patcher
For macOS Sonoma (14.x) / Sequoia (15.x) / Tahoe (26.x) with Realtek RTW89 Cards.

This script patches OCLP-restored IO80211FamilyLegacy binaries to bypass Apple-proprietary
scan filters and node iteration restrictions.
"""

import sys
import os
import shutil

PATCHES = [
    {
        "name": "Scan parameter override",
        "find":    bytes.fromhex("4c89fee82b0100004c89f74c89fee810090000"),
        "replace": bytes.fromhex("be01000000e8d31a0000909090909090909090"),
    },
    {
        "name": "StartScan rsi override & redirect",
        "find":    bytes.fromhex("4889dee8e9f2ffff"),
        "replace": bytes.fromhex("6a015ee8a3040000"),
    },
    {
        "name": "Node bypass conditional jump NOP",
        "find":    bytes.fromhex("0f8553010000"),
        "replace": bytes.fromhex("909090909090"),
    }
]

def patch_binary(target_path):
    if not os.path.isfile(target_path):
        print(f"[-] Error: Target file not found: {target_path}")
        return False

    with open(target_path, "rb") as f:
        data = bytearray(f.read())

    print(f"[*] Analyzing binary: {target_path} ({len(data)} bytes)...")
    backup_path = target_path + ".bak"
    if not os.path.exists(backup_path):
        shutil.copyfile(target_path, backup_path)
        print(f"[+] Created backup: {backup_path}")

    applied_count = 0
    for p in PATCHES:
        name = p["name"]
        find = p["find"]
        repl = p["replace"]
        idx = data.find(find)
        if idx != -1:
            data[idx:idx+len(find)] = repl
            print(f"[+] Successfully applied: {name} at offset 0x{idx:x}")
            applied_count += 1
        else:
            if data.find(repl) != -1:
                print(f"[?] Already patched: {name}")
                applied_count += 1
            else:
                print(f"[-] Pattern not found for: {name}")

    if applied_count == len(PATCHES):
        with open(target_path, "wb") as f:
            f.write(data)
        print("[+] All patches applied successfully!")
        print("[!] Note: You may need to ad-hoc codesign the binary: codesign -f -s - <binary>")
        return True
    else:
        print(f"[-] Warning: Only {applied_count}/{len(PATCHES)} patches could be applied.")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 patch_io80211legacy.py <path_to_IO80211FamilyLegacy_binary>")
        sys.exit(1)
    patch_binary(sys.argv[1])
