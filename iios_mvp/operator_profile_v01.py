from __future__ import annotations

"""Private, opt-in defaults for reusable operator preferences.

Only cross-company portfolio guardrails and a suggested valuation model are
stored. Per-company entry-price zones and project-in-baseline scope are
intentionally excluded. File permissions are access controls, not encryption.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import secrets
import stat
from typing import Any, Iterator, Mapping

PROFILE_SCHEMA = "IIOS-LOCAL-OPERATOR-PROFILE-0.1"
DEFAULT_PROFILE_PATH = (
    Path.home() / ".iios-private" / "local-pilot" / "profile" / "operator-defaults.json"
)
_MAX_PROFILE_BYTES = 64 * 1024
_PORTFOLIO_CONTEXT_KEYS = {
    "constraint_status",
    "can_add",
    "risk_budget_pct_nav",
    "entry_zone_low",
    "entry_zone_high",
    "initial_position_pct",
    "target_position_pct",
    "max_position_pct",
}
_PORTFOLIO_PREFERENCE_KEYS = {
    "constraint_status",
    "can_add",
    "risk_budget_pct_nav",
    "initial_position_pct",
    "target_position_pct",
    "max_position_pct",
}
_MODEL_FAMILIES = {"EPS_MULTIPLE", "FCF_DCF", "DDM", "SOTP", "RNPV", "OTHER", "UNKNOWN"}


class OperatorProfileError(ValueError):
    """Invalid, unsafe or unreadable local operator profile."""


def _fail_constant(token: str) -> None:
    raise OperatorProfileError("OPERATOR_PROFILE_NONFINITE_JSON_VALUE:" + token)


def _decimal(value: Any, field: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise OperatorProfileError("OPERATOR_PROFILE_NUMERIC_FIELD_INVALID:" + field) from exc
    if not number.is_finite():
        raise OperatorProfileError("OPERATOR_PROFILE_NUMERIC_FIELD_NONFINITE:" + field)
    return number


def validate_portfolio_context(value: Any) -> dict[str, Any] | None:
    """Validate the exact per-task operator input emitted by the current wizard."""
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise OperatorProfileError("OPERATOR_PROFILE_PORTFOLIO_CONTEXT_NOT_OBJECT")
    status = value.get("constraint_status")
    can_add = value.get("can_add")
    if not isinstance(status, str) or status not in {"PASS", "BLOCKED", "UNKNOWN"} or not isinstance(can_add, bool):
        raise OperatorProfileError("OPERATOR_PROFILE_PORTFOLIO_STATUS_INVALID")
    if status != "PASS":
        if can_add or set(value) != {"constraint_status", "can_add"}:
            raise OperatorProfileError("OPERATOR_PROFILE_NONPASS_PORTFOLIO_MUST_NOT_CARRY_BUDGET")
        return {"constraint_status": status, "can_add": False}
    if set(value) != _PORTFOLIO_CONTEXT_KEYS:
        raise OperatorProfileError("OPERATOR_PROFILE_PORTFOLIO_FIELDS_MISMATCH")

    percentages: dict[str, str] = {}
    for field in (
        "risk_budget_pct_nav",
        "initial_position_pct",
        "target_position_pct",
        "max_position_pct",
    ):
        number = _decimal(value.get(field), field)
        if number < 0 or number > 100:
            raise OperatorProfileError("OPERATOR_PROFILE_PERCENT_OUT_OF_RANGE:" + field)
        percentages[field] = format(number, "f")

    low = _decimal(value.get("entry_zone_low"), "entry_zone_low")
    high = _decimal(value.get("entry_zone_high"), "entry_zone_high")
    if low <= 0 or high <= 0 or low > high:
        raise OperatorProfileError("OPERATOR_PROFILE_ENTRY_ZONE_INVALID")
    initial = Decimal(percentages["initial_position_pct"])
    target = Decimal(percentages["target_position_pct"])
    maximum = Decimal(percentages["max_position_pct"])
    if not initial <= target <= maximum:
        raise OperatorProfileError("OPERATOR_PROFILE_POSITION_LIMIT_ORDER_INVALID")
    return {
        "constraint_status": "PASS",
        "can_add": can_add,
        "risk_budget_pct_nav": percentages["risk_budget_pct_nav"],
        "entry_zone_low": format(low, "f"),
        "entry_zone_high": format(high, "f"),
        "initial_position_pct": percentages["initial_position_pct"],
        "target_position_pct": percentages["target_position_pct"],
        "max_position_pct": percentages["max_position_pct"],
    }


def portfolio_preferences_from_context(value: Any) -> dict[str, Any] | None:
    """Strip case-specific entry-price range; retain only cross-company guardrails."""
    context = validate_portfolio_context(value)
    if context is None:
        return None
    if context["constraint_status"] != "PASS":
        return {"constraint_status": context["constraint_status"], "can_add": False}
    return {
        "constraint_status": "PASS",
        "can_add": context["can_add"],
        "risk_budget_pct_nav": context["risk_budget_pct_nav"],
        "initial_position_pct": context["initial_position_pct"],
        "target_position_pct": context["target_position_pct"],
        "max_position_pct": context["max_position_pct"],
    }


def validate_portfolio_preferences(value: Any) -> dict[str, Any] | None:
    """Validate the reduced profile form; entry-price bands are forbidden here."""
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise OperatorProfileError("OPERATOR_PROFILE_PORTFOLIO_PREFERENCES_NOT_OBJECT")
    status = value.get("constraint_status")
    can_add = value.get("can_add")
    if not isinstance(status, str) or status not in {"PASS", "BLOCKED", "UNKNOWN"} or not isinstance(can_add, bool):
        raise OperatorProfileError("OPERATOR_PROFILE_PORTFOLIO_STATUS_INVALID")
    if status != "PASS":
        if can_add or set(value) != {"constraint_status", "can_add"}:
            raise OperatorProfileError("OPERATOR_PROFILE_NONPASS_PORTFOLIO_MUST_NOT_CARRY_BUDGET")
        return {"constraint_status": status, "can_add": False}
    if set(value) != _PORTFOLIO_PREFERENCE_KEYS:
        raise OperatorProfileError("OPERATOR_PROFILE_PORTFOLIO_PREFERENCE_FIELDS_MISMATCH")
    percentages: dict[str, str] = {}
    for field in (
        "risk_budget_pct_nav",
        "initial_position_pct",
        "target_position_pct",
        "max_position_pct",
    ):
        number = _decimal(value.get(field), field)
        if number < 0 or number > 100:
            raise OperatorProfileError("OPERATOR_PROFILE_PERCENT_OUT_OF_RANGE:" + field)
        percentages[field] = format(number, "f")
    initial = Decimal(percentages["initial_position_pct"])
    target = Decimal(percentages["target_position_pct"])
    maximum = Decimal(percentages["max_position_pct"])
    if not initial <= target <= maximum:
        raise OperatorProfileError("OPERATOR_PROFILE_POSITION_LIMIT_ORDER_INVALID")
    return {
        "constraint_status": "PASS",
        "can_add": can_add,
        "risk_budget_pct_nav": percentages["risk_budget_pct_nav"],
        "initial_position_pct": percentages["initial_position_pct"],
        "target_position_pct": percentages["target_position_pct"],
        "max_position_pct": percentages["max_position_pct"],
    }


def validate_valuation_context(value: Any) -> dict[str, Any]:
    expected = {
        "selected_model_family",
        "baseline_includes_project",
        "input_owner",
        "selection_source",
        "selection_confirmed",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise OperatorProfileError("OPERATOR_PROFILE_VALUATION_FIELDS_MISMATCH")
    family = value.get("selected_model_family")
    baseline = value.get("baseline_includes_project")
    confirmed = value.get("selection_confirmed")
    if not isinstance(family, str) or family not in _MODEL_FAMILIES or not isinstance(confirmed, bool):
        raise OperatorProfileError("OPERATOR_PROFILE_VALUATION_SELECTION_INVALID")
    if value.get("input_owner") != "OPERATOR" or value.get("selection_source") != "INTERACTIVE_OPERATOR_PROMPT":
        raise OperatorProfileError("OPERATOR_PROFILE_VALUATION_PROVENANCE_INVALID")
    if family == "UNKNOWN":
        if confirmed or baseline is not None:
            raise OperatorProfileError("OPERATOR_PROFILE_UNKNOWN_MODEL_MUST_REMAIN_UNCONFIRMED")
    else:
        if not confirmed:
            raise OperatorProfileError("OPERATOR_PROFILE_SELECTED_MODEL_NOT_CONFIRMED")
        if baseline is not None and not isinstance(baseline, bool):
            raise OperatorProfileError("OPERATOR_PROFILE_PROJECT_SCOPE_INVALID")
        if family != "EPS_MULTIPLE" and baseline is not None:
            raise OperatorProfileError("OPERATOR_PROFILE_PROJECT_SCOPE_ONLY_FOR_EPS_MULTIPLE")
    return {
        "selected_model_family": family,
        "baseline_includes_project": baseline,
        "input_owner": "OPERATOR",
        "selection_source": "INTERACTIVE_OPERATOR_PROMPT",
        "selection_confirmed": confirmed,
    }


def validate_preferred_model_family(value: Any) -> str:
    if not isinstance(value, str) or value not in _MODEL_FAMILIES:
        raise OperatorProfileError("OPERATOR_PROFILE_PREFERRED_MODEL_FAMILY_INVALID")
    return value


def _validate_profile(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise OperatorProfileError("OPERATOR_PROFILE_ROOT_NOT_OBJECT")
    expected = {
        "profile_schema",
        "created_at",
        "updated_at",
        "portfolio_preferences",
        "preferred_valuation_model_family",
    }
    if set(value) != expected or value.get("profile_schema") != PROFILE_SCHEMA:
        raise OperatorProfileError("OPERATOR_PROFILE_SCHEMA_OR_FIELDS_MISMATCH")
    for field in ("created_at", "updated_at"):
        raw = value.get(field)
        if not isinstance(raw, str):
            raise OperatorProfileError("OPERATOR_PROFILE_TIMESTAMP_INVALID:" + field)
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError as exc:
            raise OperatorProfileError("OPERATOR_PROFILE_TIMESTAMP_INVALID:" + field) from exc
        if parsed.tzinfo is None:
            raise OperatorProfileError("OPERATOR_PROFILE_TIMESTAMP_MUST_HAVE_TIMEZONE:" + field)
    return {
        "profile_schema": PROFILE_SCHEMA,
        "created_at": value["created_at"],
        "updated_at": value["updated_at"],
        "portfolio_preferences": validate_portfolio_preferences(value["portfolio_preferences"]),
        "preferred_valuation_model_family": validate_preferred_model_family(
            value["preferred_valuation_model_family"]
        ),
    }


def _ensure_private_directory(profile_path: Path) -> tuple[Path, Path]:
    home = Path.home().resolve(strict=True)
    target = profile_path.expanduser()
    if not target.is_absolute():
        raise OperatorProfileError("OPERATOR_PROFILE_PATH_MUST_BE_ABSOLUTE")
    try:
        relative_parent = target.parent.relative_to(home)
    except ValueError as exc:
        raise OperatorProfileError("OPERATOR_PROFILE_MUST_REMAIN_UNDER_HOME") from exc
    if any(part in {".", ".."} for part in relative_parent.parts):
        raise OperatorProfileError("OPERATOR_PROFILE_PATH_TRAVERSAL_REJECTED")

    current = home
    for part in relative_parent.parts:
        current = current / part
        if current.is_symlink():
            raise OperatorProfileError("OPERATOR_PROFILE_DIRECTORY_IS_SYMLINK")
        if current.exists():
            if not current.is_dir():
                raise OperatorProfileError("OPERATOR_PROFILE_DIRECTORY_NOT_DIRECTORY")
        else:
            current.mkdir(mode=0o700)
        if os.name != "nt":
            current.chmod(0o700)
    if target.is_symlink():
        raise OperatorProfileError("OPERATOR_PROFILE_FILE_IS_SYMLINK")
    return target, target.parent


@contextmanager
def _profile_lock(parent: Path) -> Iterator[None]:
    lock_path = parent / ".operator-defaults.lock"
    if lock_path.is_symlink():
        raise OperatorProfileError("OPERATOR_PROFILE_LOCK_IS_SYMLINK")
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if os.name != "nt":
        import fcntl

        try:
            fd = os.open(lock_path, flags, 0o600)
        except OSError as exc:
            raise OperatorProfileError("OPERATOR_PROFILE_LOCK_UNAVAILABLE") from exc
        try:
            os.fchmod(fd, 0o600)
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
        return

    try:
        fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise OperatorProfileError("OPERATOR_PROFILE_LOCK_EXISTS_REQUIRES_REVIEW") from exc
    try:
        os.close(fd)
        yield
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _read_unlocked(profile_path: Path) -> dict[str, Any] | None:
    if profile_path.is_symlink():
        raise OperatorProfileError("OPERATOR_PROFILE_FILE_IS_SYMLINK")
    try:
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        if hasattr(os, "O_NONBLOCK"):
            flags |= os.O_NONBLOCK
        fd = os.open(profile_path, flags)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise OperatorProfileError("OPERATOR_PROFILE_FILE_OPEN_FAILED") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise OperatorProfileError("OPERATOR_PROFILE_FILE_NOT_REGULAR")
        if os.name != "nt":
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(_MAX_PROFILE_BYTES + 1)
    finally:
        os.close(fd)
    if len(raw) > _MAX_PROFILE_BYTES:
        raise OperatorProfileError("OPERATOR_PROFILE_FILE_TOO_LARGE")
    try:
        parsed = json.loads(raw.decode("utf-8"), parse_constant=_fail_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OperatorProfileError("OPERATOR_PROFILE_JSON_INVALID") from exc
    return _validate_profile(parsed)


def load_operator_profile(path: str | Path | None = None) -> dict[str, Any] | None:
    target, parent = _ensure_private_directory(Path(path) if path is not None else DEFAULT_PROFILE_PATH)
    with _profile_lock(parent):
        return _read_unlocked(target)


def save_operator_profile(
    *,
    portfolio_context: Any,
    valuation_context: Any,
    path: str | Path | None = None,
) -> dict[str, Any]:
    """Atomically save reduced preferences; caller must obtain explicit consent."""
    target, parent = _ensure_private_directory(Path(path) if path is not None else DEFAULT_PROFILE_PATH)
    portfolio_preferences = portfolio_preferences_from_context(portfolio_context)
    if not isinstance(valuation_context, Mapping):
        raise OperatorProfileError("OPERATOR_PROFILE_VALUATION_CONTEXT_NOT_OBJECT")
    # Validate all per-task valuation inputs even though only the model hint is persisted.
    normalized_valuation = validate_valuation_context(valuation_context)
    family = validate_preferred_model_family(normalized_valuation["selected_model_family"])
    with _profile_lock(parent):
        existing = _read_unlocked(target)
        now = datetime.now(timezone.utc).isoformat()
        payload = {
            "profile_schema": PROFILE_SCHEMA,
            "created_at": existing["created_at"] if existing else now,
            "updated_at": now,
            "portfolio_preferences": portfolio_preferences,
            "preferred_valuation_model_family": family,
        }
        encoded = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
        temporary = parent / (target.name + ".tmp-" + secrets.token_hex(8))
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(temporary, flags, 0o600)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            if target.is_symlink():
                raise OperatorProfileError("OPERATOR_PROFILE_FILE_BECAME_SYMLINK")
            os.replace(temporary, target)
            if os.name != "nt":
                target.chmod(0o600)
                directory_fd = os.open(parent, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        except Exception:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise
    return payload


def profile_section_summary(section: str, value: Any) -> str:
    if section == "portfolio":
        context = validate_portfolio_preferences(value)
        if context is None:
            return "跨公司组合约束：未保存，保持 UNKNOWN"
        if context["constraint_status"] != "PASS":
            return "组合风险约束：" + context["constraint_status"] + "；不会按 PASS 允许新增风险"
        return (
            "跨公司组合约束 PASS；单股风险预算 "
            + context["risk_budget_pct_nav"] + "%；初始/目标/最大仓位 "
            + context["initial_position_pct"] + "%/"
            + context["target_position_pct"] + "%/"
            + context["max_position_pct"] + "%"
        )
    if section == "valuation":
        family = validate_preferred_model_family(value)
        return (
            "上次选择的估值模型：" + family
            + "（仅作为本次预选提示；仍需按当前公司重新确认）"
        )
    raise OperatorProfileError("OPERATOR_PROFILE_SECTION_UNSUPPORTED")
