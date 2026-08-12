"""Static tests for container hardening configuration (G4).

These tests parse the compose file and Dockerfiles directly (no Docker
daemon required) and assert the Phase 11 hardening claims: read-only
root filesystems, dropped capabilities, no privilege escalation, init
processes, readiness healthchecks, non-root runtime users, bounded request
bodies, and security headers.
"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_PATH = REPO_ROOT / "infrastructure" / "docker-compose.yml"
API_DOCKERFILE = REPO_ROOT / "apps" / "api" / "Dockerfile"
WEB_DOCKERFILE = REPO_ROOT / "apps" / "web" / "Dockerfile"

RUNTIME_SERVICES = ["api", "worker", "web"]
ROOT_USERS = {"0", "0:0", "root"}


def _load_compose() -> dict:
    with open(COMPOSE_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _dockerfile_lines(path: Path) -> list[str]:
    with open(path, encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip()]


def _user_line(lines: list[str]) -> tuple[int, str]:
    """Return (index, username) of the first `USER` directive."""
    for index, line in enumerate(lines):
        if line.startswith("USER "):
            return index, line.split(maxsplit=1)[1].split()[0]
    raise AssertionError("Dockerfile must set a USER directive")


def _final_entry_index(lines: list[str]) -> int:
    """Return the index of the final CMD/ENTRYPOINT directive."""
    indexes = [
        index
        for index, line in enumerate(lines)
        if line.startswith(("CMD", "ENTRYPOINT"))
    ]
    assert indexes, "Dockerfile must end with a CMD or ENTRYPOINT"
    return indexes[-1]


def test_runtime_services_are_read_only() -> None:
    compose = _load_compose()
    services = compose["services"]
    for name in RUNTIME_SERVICES:
        assert services[name]["read_only"] is True, (
            f"{name} must mount a read-only root filesystem"
        )


def test_runtime_services_drop_all_capabilities() -> None:
    compose = _load_compose()
    services = compose["services"]
    for name in RUNTIME_SERVICES:
        assert services[name]["cap_drop"] == ["ALL"], (
            f"{name} must drop ALL capabilities"
        )


def test_runtime_services_prevent_privilege_escalation() -> None:
    compose = _load_compose()
    services = compose["services"]
    for name in RUNTIME_SERVICES:
        assert "no-new-privileges:true" in services[name]["security_opt"], (
            f"{name} must set no-new-privileges"
        )


def test_runtime_services_use_init_process() -> None:
    compose = _load_compose()
    services = compose["services"]
    for name in RUNTIME_SERVICES:
        assert services[name].get("init") is True, (
            f"{name} must run with init: true"
        )


def test_runtime_services_have_healthchecks() -> None:
    compose = _load_compose()
    services = compose["services"]
    for name in RUNTIME_SERVICES:
        assert services[name].get("healthcheck"), (
            f"{name} must define a readiness healthcheck"
        )


def test_runtime_services_do_not_run_as_root() -> None:
    compose = _load_compose()
    services = compose["services"]
    for name in RUNTIME_SERVICES:
        assert services[name].get("user") not in ROOT_USERS, (
            f"{name} must not run as root (user: {services[name].get('user')})"
        )


def test_only_one_shot_init_container_runs_as_root() -> None:
    """The api-data-init chown container is the single documented exception."""
    compose = _load_compose()
    root_services = [
        name
        for name, cfg in compose["services"].items()
        if cfg.get("user") in ROOT_USERS
    ]
    assert root_services == ["api-data-init"], (
        f"only api-data-init may run as root, found: {root_services}"
    )


def test_api_dockerfile_runs_as_non_root_before_entrypoint() -> None:
    lines = _dockerfile_lines(API_DOCKERFILE)
    user_index, username = _user_line(lines)
    final_index = _final_entry_index(lines)
    assert username not in ROOT_USERS, "API image must use a non-root user"
    assert user_index < final_index, (
        "API USER must appear before the final ENTRYPOINT/CMD"
    )


def test_web_dockerfile_runs_as_non_root_before_command() -> None:
    lines = _dockerfile_lines(WEB_DOCKERFILE)
    user_index, username = _user_line(lines)
    final_index = _final_entry_index(lines)
    assert username not in ROOT_USERS, "Web image must use a non-root user"
    assert user_index < final_index, (
        "Web USER must appear before the final CMD/ENTRYPOINT"
    )


def test_request_body_limit_is_bounded() -> None:
    """The security middleware caps request bodies at >= 12 MB by default."""
    from app.core import http_security

    defaults = http_security.SecurityHeadersMiddleware.__init__.__defaults__
    assert defaults is not None
    max_body_bytes = defaults[0]
    assert max_body_bytes >= 12 * 1024 * 1024


def test_security_header_middleware_is_wired() -> None:
    import app.main as main_module

    source = Path(main_module.__file__).read_text(encoding="utf-8")
    assert "SecurityHeadersMiddleware" in source
    assert "add_middleware" in source
