#!/usr/bin/env python3
"""Re-pins the cart's GitHub mods to their latest releases (or versions you name).

  python3 tools/repin.py                              every GitHub pin to its latest release
  python3 tools/repin.py pokepink-g1r=0.3.1           one repo (or mod id) to a set version
  python3 tools/repin.py --add ElvieBlooms/name_tags  pin another mod at its latest release
  python3 tools/repin.py --cart-version 0.1.0-beta.3  also bump the cart
  python3 tools/repin.py --dry-run                    show what would change, write nothing

A mod's hash comes from its release's sha256sums.txt when it has one, and
otherwise from downloading <id>-<version>.zip and hashing it, which is what
cartkit does. Options and load_order are kept; an added mod goes on the end
of load_order. Pre-releases are skipped unless you name the version.
Needs only Python 3; set GITHUB_TOKEN if GitHub rate-limits you.
"""
import argparse, hashlib, json, os, re, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CART = os.path.join(HERE, "..", "cart.json")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "pokepink-cart-repin"})
    if os.environ.get("GITHUB_TOKEN") and "api.github.com" in url:
        req.add_header("Authorization", "Bearer " + os.environ["GITHUB_TOKEN"])
    return urllib.request.urlopen(req, timeout=60)


def latest(repo):
    # github.com/<repo>/releases/latest redirects to .../releases/tag/v1.2.3
    with get("https://github.com/%s/releases/latest" % repo) as r:
        m = re.search(r"/releases/tag/v?([^/?#]+)$", r.geturl())
    if not m:
        raise RuntimeError("%s has no published release" % repo)
    return m.group(1)


_sums = {}
def sums(repo, version):
    key = (repo, version)
    if key not in _sums:
        table = {}
        try:
            with get("https://github.com/%s/releases/download/v%s/sha256sums.txt" % (repo, version)) as r:
                for line in r.read().decode("utf-8").splitlines():
                    parts = line.split()
                    if len(parts) == 2:
                        table[parts[1].lstrip("*")] = parts[0]
        except Exception:
            pass
        _sums[key] = table
    return _sums[key]


def sha256(repo, mod_id, version):
    name = "%s-%s.zip" % (mod_id, version)
    known = sums(repo, version).get(name)
    if known:
        return known, "sha256sums.txt"
    url = "https://github.com/%s/releases/download/v%s/%s" % (repo, version, name)
    h = hashlib.sha256()
    try:
        with get(url) as r:
            for chunk in iter(lambda: r.read(1 << 16), b""):
                h.update(chunk)
    except Exception as e:
        raise RuntimeError("no %s in %s v%s (%s)" % (name, repo, version, e))
    return h.hexdigest(), "download"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pins", nargs="*", metavar="REPO_OR_ID=VERSION")
    ap.add_argument("--add", action="append", default=[], metavar="OWNER/REPO")
    ap.add_argument("--cart-version")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    wanted = {}
    for pin in a.pins:
        if "=" not in pin:
            sys.exit("repin: write %r as REPO_OR_ID=VERSION" % pin)
        k, v = pin.split("=", 1)
        wanted[k.lower()] = v.lstrip("v")

    with open(CART, encoding="utf-8") as fh:
        cart = json.load(fh)
    mods = cart.setdefault("mods", [])
    for repo in a.add:
        mod_id = repo.split("/")[-1].replace("-", "_").lower()
        if any(m.get("id") == mod_id for m in mods):
            print("repin: %s is already pinned" % mod_id)
            continue
        mods.append({"id": mod_id, "source": "github", "repo": repo, "version": "", "sha256": ""})
        if isinstance(cart.get("load_order"), list):
            cart["load_order"].append(mod_id)

    versions, failed, changed = {}, [], 0
    for mod in mods:
        if mod.get("source") != "github" or not mod.get("repo"):
            continue
        repo, mod_id = mod["repo"], mod["id"]
        short = repo.split("/")[-1].lower()
        try:
            version = wanted.get(mod_id.lower()) or wanted.get(short) or wanted.get(repo.lower())
            if not version:
                if repo not in versions:
                    versions[repo] = latest(repo)
                version = versions[repo]
            digest, how = sha256(repo, mod_id, version)
        except Exception as e:
            failed.append("%s: %s" % (mod_id, e))
            continue
        old = mod.get("version") or "new"
        if old != version or mod.get("sha256") != digest:
            mod["version"], mod["sha256"] = version, digest
            changed += 1
            print("  %-26s %-8s -> %-8s (%s)" % (mod_id, old, version, how))
        else:
            print("  %-26s %s, unchanged" % (mod_id, version))

    if failed:
        print("repin: nothing was written, these didn't resolve:")
        for f in failed:
            print("  " + f)
        sys.exit(1)
    if a.cart_version:
        cart["version"] = a.cart_version.lstrip("v")
    if a.dry_run:
        print("repin: %d would change (dry run)" % changed)
        return
    with open(CART, "w", encoding="utf-8") as fh:
        json.dump(cart, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print("repin: %d pins changed%s" % (changed, (", cart is now %s" % cart["version"]) if a.cart_version else ""))


if __name__ == "__main__":
    main()
