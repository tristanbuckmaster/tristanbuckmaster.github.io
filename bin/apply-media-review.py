#!/usr/bin/env python3
"""Preview or apply a media-review export to the website's existing Media archive."""

import argparse
import fcntl
import json
import os
import stat
import tempfile
from pathlib import Path


DEFAULT_ARCHIVE = Path(__file__).resolve().parents[1] / "_data" / "media.json"
DECISIONS = ("keep", "remove", "unreviewed")


def read_rows(items, *, review=False):
    """Check the shared archive/export schema and index exact URLs within each row."""
    if not isinstance(items, list):
        raise ValueError("Expected a list of media entries.")
    by_primary = {}
    for n, item in enumerate(items, start=1):
        if not isinstance(item, dict) or not isinstance(item.get("links", []), list):
            raise ValueError(f"Invalid media entry or links list at row {n}.")
        links = {}
        for name_key, link in [("title", item)] + [("label", x) for x in item.get("links", [])]:
            if not isinstance(link, dict) or not isinstance(link.get(name_key), str) or not link[name_key].strip():
                raise ValueError(f"Missing {name_key} at row {n}.")
            url = link.get("url")
            if not isinstance(url, str) or not url.strip() or url != url.strip():
                raise ValueError(f"Invalid URL at row {n}.")
            if url in links:
                raise ValueError(f"Duplicate URL within row {n}: {url}")
            decision = link.get("decision")
            if review and decision not in DECISIONS:
                raise ValueError(f"Invalid or missing decision for {url}.")
            links[url] = decision
        if item["url"] in by_primary:
            raise ValueError(f"Duplicate primary URL: {item['url']}")
        by_primary[item["url"]] = links
    return by_primary


def read_review(path):
    document = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(document, dict) or document.get("format") != "plates-media-review"
            or type(document.get("version")) is not int or document["version"] != 1):
        raise ValueError("Expected a plates-media-review version 1 export.")
    return read_rows(document.get("items"), review=True)


def apply_decisions(items, decisions):
    """Only use decisions from the review of this item's exact primary URL."""
    read_rows(items)
    result = []
    changes = []
    for item in items:
        primary = item["url"]
        row = decisions.get(primary, {})
        companions = item.get("links", [])
        retained = []
        for link in companions:
            if row.get(link["url"]) == "remove":
                changes.append(f"Remove link: {link['label']} — {link['url']}")
            else:
                retained.append(link)

        updated = item.copy()
        if row.get(primary) == "remove":
            if not retained:
                changes.append(f"Remove entry: {item['title']} — {primary}")
                continue
            # A retained companion keeps the entry and its current catalogue metadata.
            # Prefer a checked link; use the archive order to break ties.
            replacement = next((link for link in retained if row.get(link["url"]) == "keep"), retained[0])
            if replacement["url"] in decisions:
                raise ValueError(f"Cannot promote {replacement['url']}: it is a separate primary entry in this review.")
            retained.remove(replacement)
            updated["url"] = replacement["url"]
            updated["primary_label"] = replacement["label"]
            extra = {k: v for k, v in replacement.items() if k not in ("url", "label")}
            updated.pop("primary_link_metadata", None)
            if extra:
                updated["primary_link_metadata"] = extra
            changes.append(f"Replace primary link for {item['title']}: {primary} → {replacement['label']} — {replacement['url']}")

        if retained != companions:
            if retained:
                updated["links"] = retained
            else:
                updated.pop("links", None)
        result.append(updated)
    # A promotion can collide with the primary URL of another surviving entry.
    read_rows(result)
    return result, changes


def replace_archive(path, original, result):
    """Write the entire JSON before replacing the file; preserve its permissions."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as f:
            temporary = Path(f.name)
            json.dump(result, f, ensure_ascii=False, indent=2)
            f.write("\n")
            os.fchmod(f.fileno(), stat.S_IMODE(path.stat().st_mode))
        # Lock the directory because replacing the archive changes its inode.
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            fcntl.flock(directory, fcntl.LOCK_EX)
            if path.read_bytes() != original:
                raise ValueError("The archive changed during this review. Rerun the command.")
            os.replace(temporary, path)
            temporary = None
        finally:
            os.close(directory)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review", type=Path, help="JSON file downloaded from Media review")
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE, help="archive JSON (default: _data/media.json)")
    parser.add_argument("--apply", action="store_true", help="write the listed changes; the default is a preview")
    args = parser.parse_args()
    try:
        decisions = read_review(args.review)
        original = args.archive.read_bytes()
        result, changes = apply_decisions(json.loads(original), decisions)
        if changes and args.apply:
            replace_archive(args.archive, original, result)
    except (OSError, UnicodeError, ValueError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    for change in changes:
        print(change)
    if not changes:
        print("No changes.")
    elif args.apply:
        print(f"Saved {len(result)} media entries to {args.archive}.")
    else:
        print(f"Preview only. Rerun with --apply to save {len(result)} media entries.")


if __name__ == "__main__":
    main()
