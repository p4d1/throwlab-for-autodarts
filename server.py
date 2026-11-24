#!/usr/bin/env python3
"""
Lokaler Server & CORS-Proxy für den AutoDarts Trainer (Windows, macOS & Linux).
- Liefert die Weboberfläche unter http://localhost:8075/ aus
- Leitet Anfragen auf /api/... (GET, POST, PUT) direkt an den lokalen Autodarts-Service
  (Standard: http://127.0.0.1:3180/api/...) weiter und setzt CORS-Header.
- Bietet unter /api/trainer/version, /api/trainer/update-check und /api/trainer/update-apply
  einen plattformübergreifenden Update-Service (per Git oder direktem GitHub-ZIP-Download).
"""

import http.server
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile

PORT = 8075
AUTODARTS_DEFAULT = "http://127.0.0.1:3180"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(BASE_DIR)


def read_local_version():
    version_path = os.path.join(BASE_DIR, "version.json")
    try:
        with open(version_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"version": "1.3.1", "name": "ThrowLab for Autodarts"}


def parse_semver(ver_str):
    parts = re.sub(r"^v", "", str(ver_str or "0.0.0"), flags=re.IGNORECASE).split(".")
    nums = []
    for i in range(3):
        try:
            nums.append(int(re.match(r"^\d+", parts[i]).group(0)) if i < len(parts) else 0)
        except Exception:
            nums.append(0)
    return tuple(nums)


def normalize_repo_slug(repo_val):
    if not repo_val:
        return ""
    slug = str(repo_val).strip()
    slug = re.sub(r"^https?://github\.com/", "", slug, flags=re.IGNORECASE)
    slug = slug.strip("/")
    if re.match(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", slug):
        return slug
    return ""


def run_git_cmd(args, timeout=8):
    try:
        res = subprocess.run(
            ["git"] + args,
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def fetch_github_version(repo_slug):
    if not repo_slug:
        return None, None
    for branch in ("main", "master"):
        raw_url = f"https://raw.githubusercontent.com/{repo_slug}/{branch}/version.json"
        try:
            req = urllib.request.Request(raw_url, headers={"User-Agent": "AutoDarts-Trainer-Updater"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data, branch
        except Exception:
            continue
    return None, None


class DartTrainerHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, X-Autodarts-Target, Authorization, x-api-key",
        )
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/api/trainer/version"):
            self.handle_trainer_version()
        elif self.path.startswith("/api/trainer/update-check"):
            self.handle_trainer_update_check()
        elif self.path.startswith("/api/"):
            self.proxy_to_autodarts("GET")
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/trainer/update-apply"):
            self.handle_trainer_update_apply()
        elif self.path.startswith("/api/"):
            self.proxy_to_autodarts("POST")
        else:
            self.send_error(404)

    def do_PUT(self):
        if self.path.startswith("/api/"):
            self.proxy_to_autodarts("PUT")
        else:
            self.send_error(404)

    def send_json(self, status_code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def handle_trainer_version(self):
        ver_data = read_local_version()
        code, commit_hash, _ = run_git_cmd(["rev-parse", "--short", "HEAD"])
        code_b, branch, _ = run_git_cmd(["rev-parse", "--abbrev-ref", "HEAD"])
        ver_data["git_commit"] = commit_hash if code == 0 else None
        ver_data["git_branch"] = branch if code_b == 0 else None
        self.send_json(200, ver_data)

    def handle_trainer_update_check(self):
        ver_data = read_local_version()
        local_ver = ver_data.get("version", "1.3.0")

        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        repo_param = qs.get("repo", [""])[0]
        repo_slug = normalize_repo_slug(repo_param or ver_data.get("repo", ""))

        # 1. Check local Git if inside a git repo with upstream
        code, inside, _ = run_git_cmd(["rev-parse", "--is-inside-work-tree"])
        if code == 0 and inside == "true":
            run_git_cmd(["fetch", "--quiet"], timeout=6)
            _, local_sha, _ = run_git_cmd(["rev-parse", "--short", "HEAD"])
            rc_u, remote_sha, _ = run_git_cmd(["rev-parse", "--short", "@{u}"])
            if rc_u == 0:
                _, behind_count, _ = run_git_cmd(["rev-list", "--count", "HEAD..@{u}"])
                behind = int(behind_count) if behind_count.isdigit() else 0
                _, latest_subject, _ = run_git_cmd(["log", "-1", "--format=%s", "@{u}"])
                self.send_json(
                    200,
                    {
                        "ok": True,
                        "method": "git",
                        "git_available": True,
                        "remote_configured": True,
                        "can_auto_update": True,
                        "local_version": local_ver,
                        "local_commit": local_sha,
                        "remote_commit": remote_sha,
                        "commits_behind": behind,
                        "update_available": behind > 0,
                        "latest_message": latest_subject,
                        "message": (
                            f"{behind} neue(s) Update(s) auf Git verfügbar!"
                            if behind > 0
                            else "Du bist auf dem neuesten Git-Stand."
                        ),
                    },
                )
                return

        # 2. Cross-platform GitHub check (works on Windows/macOS/Linux even without Git!)
        if repo_slug:
            remote_ver, branch = fetch_github_version(repo_slug)
            if remote_ver and remote_ver.get("version"):
                is_newer = parse_semver(remote_ver["version"]) > parse_semver(local_ver)
                self.send_json(
                    200,
                    {
                        "ok": True,
                        "method": "github-zip",
                        "git_available": (code == 0 and inside == "true"),
                        "remote_configured": False,
                        "can_auto_update": True,
                        "repo": repo_slug,
                        "branch": branch,
                        "local_version": local_ver,
                        "remote_version": remote_ver["version"],
                        "update_available": is_newer,
                        "download_url": f"https://github.com/{repo_slug}/archive/refs/heads/{branch}.zip",
                        "message": (
                            f"Neue Version v{remote_ver['version']} auf GitHub verfügbar!"
                            if is_newer
                            else f"Du nutzt bereits die aktuellste Version (v{local_ver})."
                        ),
                    },
                )
                return

        self.send_json(
            200,
            {
                "ok": True,
                "method": "local",
                "git_available": (code == 0 and inside == "true"),
                "remote_configured": False,
                "can_auto_update": False,
                "local_version": local_ver,
                "update_available": False,
                "message": "Installierte Version aktiv. Trage dein GitHub-Repository ein, um plattformübergreifende Updates zu prüfen.",
            },
        )

    def handle_trainer_update_apply(self):
        ver_data = read_local_version()
        body_data = {}
        try:
            content_len = int(self.headers.get("Content-Length", 0))
            if content_len > 0:
                body_data = json.loads(self.rfile.read(content_len).decode("utf-8"))
        except Exception:
            body_data = {}

        # 1. Prefer git pull if inside a git repo with upstream
        code, inside, _ = run_git_cmd(["rev-parse", "--is-inside-work-tree"])
        rc_u, _, _ = run_git_cmd(["rev-parse", "--short", "@{u}"])
        if code == 0 and inside == "true" and rc_u == 0:
            rc, out, err = run_git_cmd(["pull", "--ff-only"], timeout=15)
            new_ver = read_local_version()
            if rc == 0:
                self.send_json(
                    200,
                    {
                        "ok": True,
                        "method": "git",
                        "version": new_ver.get("version", "1.3.0"),
                        "output": out or "Erfolgreich via Git aktualisiert.",
                    },
                )
            else:
                self.send_json(500, {"ok": False, "error": err or out or "git pull fehlgeschlagen."})
            return

        # 2. Cross-platform GitHub ZIP self-updater (Windows, macOS, Linux without Git!)
        repo_slug = normalize_repo_slug(body_data.get("repo") or ver_data.get("repo", ""))
        if not repo_slug:
            self.send_json(400, {"ok": False, "error": "Kein GitHub-Repository konfiguriert."})
            return

        _, branch = fetch_github_version(repo_slug)
        branch = branch or "main"
        zip_url = f"https://github.com/{repo_slug}/archive/refs/heads/{branch}.zip"

        try:
            req = urllib.request.Request(zip_url, headers={"User-Agent": "AutoDarts-Trainer-Updater"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                zip_bytes = resp.read()

            allowed_files = {
                "index.html",
                "server.py",
                "version.json",
                "appicon.svg",
                "favicon.svg",
                "README.md",
                "start.sh",
            }

            updated_count = 0
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                with tempfile.TemporaryDirectory() as tmpdir:
                    for member in zf.infolist():
                        if member.is_dir():
                            continue
                        # Strip top-level folder (e.g. throwlab-for-autodarts-main/)
                        parts = member.filename.split("/", 1)
                        rel_name = parts[1] if len(parts) == 2 else parts[0]
                        if rel_name not in allowed_files:
                            continue
                        target_path = os.path.realpath(os.path.join(BASE_DIR, rel_name))
                        if not target_path.startswith(os.path.realpath(BASE_DIR) + os.sep):
                            continue
                        tmp_file = os.path.join(tmpdir, os.path.basename(rel_name))
                        with zf.open(member) as src, open(tmp_file, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                        shutil.move(tmp_file, target_path)
                        updated_count += 1

            new_ver = read_local_version()
            self.send_json(
                200,
                {
                    "ok": True,
                    "method": "github-zip",
                    "version": new_ver.get("version", "1.3.0"),
                    "output": f"{updated_count} Dateien erfolgreich aktualisiert.",
                },
            )
        except Exception as e:
            self.send_json(500, {"ok": False, "error": f"Download/Update fehlgeschlagen: {e}"})

    def proxy_to_autodarts(self, method):
        target_base = self.headers.get("X-Autodarts-Target", AUTODARTS_DEFAULT).rstrip("/")
        if not (target_base.startswith("http://") or target_base.startswith("https://")):
            self.send_json(400, {"error": "Ungültige Ziel-URL"})
            return

        target_url = f"{target_base}{self.path}"

        try:
            body = None
            if method in ("POST", "PUT"):
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len) if content_len > 0 else b""

            req_headers = {"Accept": "application/json"}
            auth_header = self.headers.get("Authorization")
            api_key_header = self.headers.get("x-api-key")
            if auth_header:
                req_headers["Authorization"] = auth_header
            if api_key_header:
                req_headers["x-api-key"] = api_key_header

            req = urllib.request.Request(
                target_url,
                data=body,
                method=method,
                headers=req_headers,
            )
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                resp_body = resp.read()
                self.send_response(resp.status)
                self.send_header(
                    "Content-Type",
                    resp.headers.get("Content-Type", "application/json"),
                )
                self.end_headers()
                self.wfile.write(resp_body)
        except urllib.error.HTTPError as e:
            err_body = b""
            try:
                err_body = e.read()
            except Exception:
                pass
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                err_body
                if err_body
                else json.dumps({"error": f"HTTP {e.code}"}).encode("utf-8")
            )
        except urllib.error.URLError as e:
            self.send_json(
                502,
                {"connected": False, "running": False, "error": str(e)},
            )
        except Exception as e:
            self.send_json(500, {"error": str(e)})

    def log_message(self, format, *args):
        if len(args) > 0 and isinstance(args[0], str) and "/api/state" in args[0]:
            return
        super().log_message(format, *args)


if __name__ == "__main__":
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    with http.server.ThreadingHTTPServer(("0.0.0.0", PORT), DartTrainerHandler) as httpd:
        print(f"🎯 AutoDarts Trainer läuft auf http://localhost:{PORT}")
        httpd.serve_forever()
