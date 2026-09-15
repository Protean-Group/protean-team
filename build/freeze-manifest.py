#!/usr/bin/env python3
"""Build build/manifest.frozen.tsv — the frozen, self-contained shipped
surface for the open-core demo.

Rules:
1. Only rows whose template target exists under templates/ (shipped surface).
2. relpath stored SANITIZED — the committed artifact must not carry instance
   tokens in paths (target_path/sanitize_path are idempotent, so a sanitized
   relpath resolves to the same template target).
3. profiles_detail column dropped (it names the live fleet).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from genericize import sanitize_path, load_instance_identifiers, derive_identity_inventory


def _leak_terms():
    """Instance tokens to catch: the identifiers config (empty in the open kit)
    plus the live fleet's handles and display names. Derived, never hardcoded."""
    inst, _ = load_instance_identifiers()
    handles, names = derive_identity_inventory()
    terms = set()
    for key, val in inst.items():
        if isinstance(val, list):
            terms.update(val)
    terms.update(handles)
    terms.update(names)
    return sorted({t.lower() for t in terms if t and len(t) >= 2})

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_LIVE = os.path.join(ROOT, "build", "manifest.tsv")
MANIFEST_FROZEN = os.path.join(ROOT, "build", "manifest.frozen.tsv")
TEMPLATES = os.path.join(ROOT, "templates")


def target_exists(rel):
    base = os.path.basename(rel)
    if base == "profile.yaml":
        return os.path.isfile(os.path.join(TEMPLATES, "personas", "profile.yaml.tmpl"))
    if base in ("SOUL.md", "AGENTS.md", "USER.md", "HERMES.md"):
        return os.path.isfile(os.path.join(TEMPLATES, "personas", f"{base}.tmpl"))
    if rel.startswith("skills/"):
        return os.path.isfile(os.path.join(TEMPLATES, "skills",
                                           sanitize_path(rel[len("skills/"):])))
    return os.path.isfile(os.path.join(TEMPLATES, rel))


def main():
    rows = []
    with open(MANIFEST_LIVE, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line.startswith("relpath"):
                continue
            parts = line.split("\t")
            if len(parts) < 5:
                continue
            rel = parts[0]
            if not target_exists(rel):
                continue
            # Sanitize the stored relpath — first 5 cols only (no fleet names)
            san = sanitize_path(rel)
            rows.append("\t".join([san] + parts[1:5]))

    out = "relpath\tclass\tprofiles\ttotal_hits\tverdict\n" + "\n".join(sorted(set(rows))) + "\n"
    with open(MANIFEST_FROZEN, "w", encoding="utf-8") as fh:
        fh.write(out)

    # Verify no instance tokens in the frozen manifest. The term list is
    # DERIVED from the same identity sources the genericizer uses (live fleet
    # handles/display names + build/identifiers.yaml) — never hardcoded here.
    # A hardcoded list both misses new members and ships the very instance
    # tokens it is meant to catch. In the open kit the config is empty, so the
    # check is scoped to the live fleet when one is present.
    low = out.lower()
    leaks = []
    for bad in _leak_terms():
        if bad in low:
            leaks.append(bad)
    print(f"frozen manifest: {len(rows)} shipped-surface rows")
    print(f"leaks: {leaks if leaks else 'NONE'}")
    if leaks:
        sys.exit(1)


if __name__ == "__main__":
    main()
