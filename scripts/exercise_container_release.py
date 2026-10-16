from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROJECT_PATTERN = re.compile(r"^sekbexercise-[a-z0-9-]+$")


def run(
    *args: str,
    env: dict[str, str] | None = None,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=PROJECT_ROOT,
        env=env,
        check=check,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )


def compose(
    project: str,
    *args: str,
    env: dict[str, str],
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    return run(
        "docker",
        "compose",
        "--project-name",
        project,
        "--file",
        str(PROJECT_ROOT / "deploy" / "docker-compose.yml"),
        *args,
        env=env,
        check=check,
        capture=capture,
    )


def wait_healthy(project: str, env: dict[str, str]) -> None:
    container_id = compose(project, "ps", "--quiet", "kb-api", env=env, capture=True).stdout.strip()
    if not container_id:
        raise RuntimeError("Compose did not return the kb-api container id")
    for _ in range(60):
        status = run(
            "docker",
            "inspect",
            "--format",
            "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}",
            container_id,
            capture=True,
        ).stdout.strip()
        if status == "healthy":
            return
        if status in {"dead", "exited"}:
            compose(project, "logs", "kb-api", env=env, check=False)
            raise RuntimeError(f"container entered terminal state {status}")
        time.sleep(2)
    compose(project, "logs", "kb-api", env=env, check=False)
    raise TimeoutError("container did not become healthy within 120 seconds")


def exec_python(project: str, env: dict[str, str], source: str, *, capture: bool = False) -> str:
    result = compose(
        project,
        "exec",
        "-T",
        "kb-api",
        "python",
        "-c",
        source,
        env=env,
        capture=capture,
    )
    return result.stdout.strip() if result.stdout else ""


def smoke(project: str, env: dict[str, str]) -> None:
    exec_python(
        project,
        env,
        """
import urllib.error
import urllib.request

for endpoint in ("live", "ready"):
    response = urllib.request.urlopen(f"http://127.0.0.1:8000/api/v1/{endpoint}", timeout=3)
    assert response.status == 200

try:
    urllib.request.urlopen("http://127.0.0.1:8000/api/v1/admin/diagnostics", timeout=3)
except urllib.error.HTTPError as error:
    assert error.code == 401
else:
    raise AssertionError("unauthenticated diagnostics request unexpectedly succeeded")

request = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1/admin/diagnostics",
    headers={"Authorization": "Bearer fake-container-admin-key"},
)
assert urllib.request.urlopen(request, timeout=3).status == 200
""",
    )


def exercise(project: str, output: Path) -> dict[str, object]:
    if not PROJECT_PATTERN.fullmatch(project):
        raise ValueError(f"refusing unsafe Compose project name: {project}")

    suffix = project.removeprefix("sekbexercise-")
    old_tag = f"exercise-old-{suffix}"
    new_tag = f"exercise-new-{suffix}"
    base_env = os.environ.copy()
    base_env.update(
        {
            "KB_READ_KEYS": "fake-container-read-key",
            "KB_ADMIN_KEYS": "fake-container-admin-key",
        }
    )
    cleanup_ok = False
    report: dict[str, object] | None = None
    try:
        old_env = base_env | {"SE_KB_IMAGE_TAG": old_tag}
        new_env = base_env | {"SE_KB_IMAGE_TAG": new_tag}
        compose(project, "build", "kb-api", env=old_env)
        run("docker", "tag", f"se-kb-api:{old_tag}", f"se-kb-api:{new_tag}")

        compose(project, "up", "--detach", "--no-build", "kb-api", env=old_env)
        wait_healthy(project, old_env)
        smoke(project, old_env)
        uid = compose(
            project, "exec", "-T", "kb-api", "id", "-u", env=old_env, capture=True
        ).stdout.strip()
        if uid != "10001":
            raise RuntimeError(f"container ran as unexpected uid {uid!r}")
        writable_root = compose(
            project,
            "exec",
            "-T",
            "kb-api",
            "sh",
            "-c",
            "touch /app/root-filesystem-must-be-read-only",
            env=old_env,
            check=False,
            capture=True,
        )
        if writable_root.returncode == 0:
            raise RuntimeError("container root filesystem is writable")

        old_hash = exec_python(
            project,
            old_env,
            """
from hashlib import sha256
from pathlib import Path

payload = b"temporary release artifact and index fixture\\n"
artifact = Path("/app/data/release-artifact.bin")
index = Path("/app/se_kb/release-old/index.bin")
artifact.write_bytes(payload)
index.parent.mkdir(parents=True, exist_ok=True)
index.write_bytes(payload)
Path("/app/se_kb/active-index.txt").write_text("release-old\\n", encoding="utf-8")
print(sha256(payload).hexdigest())
""",
            capture=True,
        )
        compose(project, "stop", "--timeout", "35", "kb-api", env=old_env)

        compose(project, "up", "--detach", "--no-build", "--force-recreate", "kb-api", env=new_env)
        wait_healthy(project, new_env)
        smoke(project, new_env)
        upgrade_hash = exec_python(
            project,
            new_env,
            """
from hashlib import sha256
from pathlib import Path
import shutil

artifact = Path("/app/data/release-artifact.bin")
old_index = Path("/app/se_kb/release-old/index.bin")
new_index = Path("/app/se_kb/release-new/index.bin")
new_index.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(old_index, new_index)
Path("/app/se_kb/active-index.txt").write_text("release-new\\n", encoding="utf-8")
assert artifact.read_bytes() == old_index.read_bytes() == new_index.read_bytes()
print(sha256(new_index.read_bytes()).hexdigest())
""",
            capture=True,
        )
        compose(project, "stop", "--timeout", "35", "kb-api", env=new_env)

        compose(project, "up", "--detach", "--no-build", "--force-recreate", "kb-api", env=old_env)
        wait_healthy(project, old_env)
        smoke(project, old_env)
        rollback_hash = exec_python(
            project,
            old_env,
            """
from hashlib import sha256
from pathlib import Path

artifact = Path("/app/data/release-artifact.bin")
old_index = Path("/app/se_kb/release-old/index.bin")
Path("/app/se_kb/active-index.txt").write_text("release-old\\n", encoding="utf-8")
assert artifact.read_bytes() == old_index.read_bytes()
assert Path("/app/se_kb/active-index.txt").read_text(encoding="utf-8") == "release-old\\n"
print(sha256(old_index.read_bytes()).hexdigest())
""",
            capture=True,
        )
        compose(project, "stop", "--timeout", "35", "kb-api", env=old_env)
        if len({old_hash, upgrade_hash, rollback_hash}) != 1:
            raise RuntimeError("artifact/index digests changed across upgrade or rollback")
        expected = hashlib.sha256(b"temporary release artifact and index fixture\n").hexdigest()
        if old_hash != expected:
            raise RuntimeError("fixture digest did not match the expected source digest")
        report = {
            "compose_project": project,
            "temporary_named_volumes": True,
            "non_root_uid": int(uid),
            "read_only_root": True,
            "startup_and_auth_smoke": True,
            "upgrade_ok": True,
            "rollback_ok": True,
            "artifact_and_index_sha256": old_hash,
        }
    finally:
        cleanup_env = base_env | {"SE_KB_IMAGE_TAG": old_tag}
        down = compose(
            project,
            "down",
            "--volumes",
            "--remove-orphans",
            env=cleanup_env,
            check=False,
            capture=True,
        )
        images = run(
            "docker",
            "image",
            "rm",
            f"se-kb-api:{old_tag}",
            f"se-kb-api:{new_tag}",
            check=False,
            capture=True,
        )
        cleanup_ok = down.returncode == 0 and images.returncode == 0

    if report is None:
        raise RuntimeError("container release exercise did not produce a report")
    if not cleanup_ok:
        raise RuntimeError("container release exercise passed but scoped cleanup failed")
    report["temporary_resources_removed"] = True
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Exercise isolated container upgrade and rollback")
    parser.add_argument("--project", default=f"sekbexercise-local-{os.getpid()}")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "docs" / "baseline" / "container-release-exercise.json",
    )
    args = parser.parse_args()
    try:
        report = exercise(args.project, args.output.resolve())
    except (OSError, subprocess.CalledProcessError, RuntimeError, ValueError) as error:
        print(f"container release exercise failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
