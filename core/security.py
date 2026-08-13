"""Shared security helpers for path/secret guards and role checks."""
from pathlib import Path
from typing import Iterable, List, Union, Optional

SECRET_BASENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "credentials.json",
    "service_account.json",
}

SECRET_SUFFIXES = (
    ".session",
    ".session-journal",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
)

SECRET_PATH_PARTS = (
    ".ssh",
    "credentials",
)


def normalize_roles(owner_role: Union[str, List[str], None]) -> List[str]:
    if owner_role is None or owner_role == "all":
        return ["all"]
    if isinstance(owner_role, list):
        return [str(r) for r in owner_role]
    return [str(owner_role)]


def role_allowed(caller_role: str, owner_role: Union[str, List[str], None]) -> bool:
    roles = normalize_roles(owner_role)
    return "all" in roles or caller_role in roles


def is_secret_path(path: Union[Path, str], base_dir: Optional[Path] = None) -> bool:
    """Return True if the path looks like a secret/credential file."""
    p = Path(path)
    name = p.name.lower()
    if name in SECRET_BASENAMES:
        return True
    if any(name.endswith(suf) for suf in SECRET_SUFFIXES):
        return True
    parts = {part.lower() for part in p.parts}
    if any(part in parts for part in SECRET_PATH_PARTS):
        return True
    if ".env" in parts:
        return True
    if base_dir is not None:
        try:
            resolved = p.resolve()
            base = base_dir.resolve()
            rel = resolved.relative_to(base)
            if any(
                part.lower() in SECRET_PATH_PARTS or part.lower() in SECRET_BASENAMES
                for part in rel.parts
            ):
                return True
        except Exception:
            pass
    return False


def path_contains_any(command: str, protected: Iterable[str]) -> bool:
    lowered = command.lower()
    return any(item.lower() in lowered for item in protected)
