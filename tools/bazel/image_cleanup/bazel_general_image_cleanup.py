#!/usr/bin/env python3

import io
import sys
import tarfile
import re

_EXCLUDE_RE = re.compile(
    r"^\.?/?("
    r"usr/share/(doc|man|locale|info|lintian|groff|linda)(/|$)"
    r"|var/cache/man(/|$)"
    r"|(.*/)?__pycache__(/|$)"
    r")"
)

def _read_payload_paths(tar_path):
    paths = set()
    with tarfile.open(tar_path, "r:*") as tf:
        for member in tf:
            if member.isfile() or member.islnk() or member.issym():
                paths.add(member.name.removeprefix("./") or ".")
    return paths


def _read_hardlink_edges(tar_path):
    edges = {}
    with tarfile.open(tar_path, "r:*") as tf:
        for member in tf:
            if member.islnk():
                name = member.name.removeprefix("./") or "."
                linkname = member.linkname.removeprefix("./") or "."
                edges.setdefault(name, set()).add(linkname)
    return edges


def _expand_drop_set_for_hardlinks(initial_drop, src_path):
    edges = _read_hardlink_edges(src_path)
    drop = set(initial_drop)
    changed = True
    while changed:
        changed = False
        for name in edges.keys():
            for linkname in edges[name]:
                if linkname in drop and name not in drop:
                    drop.add(name)
                    changed = True
    return drop


def subtract(src_path, out_path, ref_paths):
    exclude = set()
    for ref in ref_paths:
        exclude.update(_read_payload_paths(ref))
    exclude = _expand_drop_set_for_hardlinks(exclude, src_path)

    kept_entries = 0
    dropped_entries = 0
    dropped_bytes = 0
    with tarfile.open(src_path, "r:*") as src, \
         tarfile.open(out_path, "w") as dst:
        for member in src:
            name = member.name.removeprefix("./") or "."
            if bool(_EXCLUDE_RE.search(name)) or name in exclude and (
                member.isfile() or member.islnk() or member.issym()
            ):
                dropped_entries += 1
                if member.isfile():
                    dropped_bytes += member.size
            else:
                kept_entries += 1
                if member.isfile():
                    with src.extractfile(member) as f:
                        data = f.read()
                    dst.addfile(member, io.BytesIO(data))
                else:
                    dst.addfile(member)
    return kept_entries, dropped_entries, dropped_bytes


def main():
    # 3 args required (src + out); reference tars are optional. With zero
    # refs the script runs in filter-only mode — equivalent to the old
    # filter_tar.py. With one or more refs it also subtracts paths.
    if len(sys.argv) < 3:
        print(
            f"usage: {sys.argv[0]} <src.tar> <out.tar> "
            f"[<ref1.tar> <ref2.tar> ...]",
            file=sys.stderr,
        )
        return 2
    src_path = sys.argv[1]
    out_path = sys.argv[2]
    ref_paths = sys.argv[3:]
    kept_entries, dropped_entries, dropped_bytes = subtract(src_path, out_path, ref_paths)
    print(
        f"image_cleanup: kept {kept_entries}, dropped {dropped_entries} entries "
        f"({dropped_bytes / 1048576:.1f} MB uncompressed) — "
        f"refs={len(ref_paths)} "
        f"({'filter+subtract' if ref_paths else 'filter-only'})",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
