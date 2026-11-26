#!/usr/bin/env python3
"""Re-pins the cart's GitHub mods to their latest releases (or versions you name).

  python3 tools/repin.py                              every GitHub pin to its latest release
  python3 tools/repin.py pokepink-g1r=0.3.1           one repo (or mod id) to a set version
  python3 tools/repin.py --add ElvieBlooms/name_tags  pin another mod at its latest release
  python3 tools/repin.py --add ElvieBlooms/recomp_achievements:recomp_achievements_online
                                                      a second mod from the same repo, by id
  python3 tools/repin.py --off field_notes            ship a pin switched off (--on undoes it)
  python3 tools/repin.py --cart-version 0.1.0-beta.3  also bump the cart
  python3 tools/repin.py --dry-run                    show what would change, write nothing

A mod's hash comes from its release's sha256sums.txt when it has one, and
otherwise from downloading <id>-<version>.zip and hashing it, which is what
cartkit does. Options and load_order are kept; an added mod goes on the end
of load_order. Pre-releases are skipped unless you name the version.
A pin shipped off is installed with its options but doesn't run until the
player switches it on in the mod manager.
Needs only Python 3; set GITHUB_TOKEN if GitHub rate-limits you.
"""
import argparse, hashlib, json, os, re, subprocess, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CART = os.path.join(HERE, "..", "cart.json")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "pokepink-cart-repin"})
    if os.environ.get("GITHUB_TOKEN") and "api.github.com" in url:
        req.add_header("Authorization", "Bearer " + os.environ["GITHUB_TOKEN"])
    return urllib.request.urlopen(req, timeout=60)


def vkey(v):
    return [int(x) if x.isdigit() else x for x in re.split(r"[.-]", v)]


def latest_tag(repo):
    # where the release page can't be reached: the newest v1.2.3 tag that
    # isn't a pre-release (anything with a "-" after the version)
    out = subprocess.run(["git", "ls-remote", "--tags", "--refs", "https://github.com/%s" % repo],
                         capture_output=True, text=True, timeout=120)
    tags = [l.rsplit("refs/tags/", 1)[-1] for l in out.stdout.splitlines()]
    stable = [t[1:] for t in tags if re.fullmatch(r"v\d+(\.\d+)*", t)]
    if not stable:
        raise RuntimeError("%s has no release tags" % repo)
    return max(stable, key=vkey)


def latest(repo):
    # github.com/<repo>/releases/latest redirects to .../releases/tag/v1.2.3
    try:
        with get("https://github.com/%s/releases/latest" % repo) as r:
            m = re.search(r"/releases/tag/v?([^/?#]+)$", r.geturl())
    except Exception:
        return latest_tag(repo)
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
    ap.add_argument("--add", action="append", default=[], metavar="OWNER/REPO[:ID]")
    ap.add_argument("--off", action="append", default=[], metavar="ID")
    ap.add_argument("--on", action="append", default=[], metavar="ID")
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
    for spec in a.add:
        repo, _, mod_id = spec.partition(":")
        mod_id = mod_id or repo.split("/")[-1].replace("-", "_").lower()
        if any(m.get("id") == mod_id for m in mods):
            print("repin: %s is already pinned" % mod_id)
            continue
        mods.append({"id": mod_id, "source": "github", "repo": repo, "version": "", "sha256": ""})
        if isinstance(cart.get("load_order"), list):
            cart["load_order"].append(mod_id)

    for mod_id, on in [(i, False) for i in a.off] + [(i, True) for i in a.on]:
        mod = next((m for m in mods if m.get("id") == mod_id), None)
        if not mod:
            sys.exit("repin: %s isn't pinned" % mod_id)
        if on:
            mod.pop("enabled", None)
        else:
            mod["enabled"] = False
        print("  %-26s ships %s" % (mod_id, "on" if on else "off"))

    versions, failed, changed = {}, [], 0
    for mod in mods:
        if mod.get("source") != "github" or not mod.get("repo"):
            continue
        repo, mod_id = mod["repo"], mod["id"]
        short = repo.split("/")[-1].lower()
        try:
            version = wanted.get(mod_id.lower()) or wanted.get(short) or wanted.get(repo.lower())
            if not version and "-" in (mod.get("version") or ""):
                # a pinned pre-release stays put until you name a version
                version = mod["version"]
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
