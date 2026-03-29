"""
IBKR account scope for UI vs execution (domain boundary).

Positions can be listed without a configured account (show all legs TWS reports).
Order routing and PnL still use SUB_ACCOUNT_ID / managed_account from TWS when config is empty.

When ACCOUNT_ID is set but not in TWS managedAccounts, filtering would hide every leg
(typo, stale machine, wrong paper/live id). We fail-open for *display* only and surface a warning.
"""

from __future__ import annotations


def resolve_position_account_filter(
    configured_account_id: str,
    tws_managed_account_ids: tuple[str, ...] | list[str] | None,
) -> tuple[str | None, str | None]:
    """
    Decide whether to filter the positions table by account.

    Returns:
        (filter_account, warning_message)
        - filter_account is None → show positions from all accounts TWS streams.
        - filter_account is non-empty → only legs where pos.account == filter_account.
        - warning_message set when config was ignored for display (fail-open).
    """
    cfg = (configured_account_id or "").strip()
    if not cfg:
        return None, None

    ids = tuple(tws_managed_account_ids) if tws_managed_account_ids else ()
    if not ids:
        # managedAccounts not received yet — apply filter as requested; may hide rows briefly.
        return cfg, None

    if cfg in ids:
        return cfg, None

    return None, (
        f"ACCOUNT_ID '{cfg}' is not in TWS managed accounts {list(ids)}. "
        f"Showing positions for ALL accounts until this matches your login (or leave Account empty). "
        f"Fix before relying on order routing — orders still use the configured Account field when set."
    )
