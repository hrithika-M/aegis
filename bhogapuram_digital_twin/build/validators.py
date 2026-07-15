# -*- coding: utf-8 -*-
"""Input validation for the schedule — fail LOUDLY on bad data, don't guess silently.

A digital twin headed to production must reject malformed input with a clear message
rather than produce quietly-wrong numbers. This separates:
  ERRORS   — unrecoverable (missing seats, unparseable time): stop the build.
  WARNINGS — recoverable (unknown airport/aircraft code): fall back + log.
"""


class ScheduleValidationError(Exception):
    """Raised when the schedule has errors that make a correct build impossible."""


def _valid_time(v):
    try:
        h, m = str(v).strip().split(':')
        return 0 <= int(h) <= 23 and 0 <= int(m) <= 59
    except (ValueError, AttributeError):
        return False


def _valid_freq(v):
    s = str(v).strip()
    return len(s) > 0 and all(c in '1234567' for c in s)


def validate_schedule(ws, known_airports, known_aircraft):
    """Return (errors, warnings). `errors` non-empty => caller should stop the build."""
    errors, warnings = [], []
    if ws is None:
        return ["schedule sheet 'MAIN FILE' not found in workbook"], []
    seen_sl = set()
    for r in range(3, ws.max_row + 1):
        sl = ws.cell(r, 1).value
        if not isinstance(sl, int):
            break                                        # reached legend / end of data
        if sl in seen_sl:
            errors.append(f"row {r}: duplicate SL NO {sl}")
        seen_sl.add(sl)
        seats = ws.cell(r, 11).value
        if not isinstance(seats, (int, float)) or seats <= 0:
            errors.append(f"row {r} (SL {sl}): seat_capacity missing or non-positive ({seats!r})")
        for col, label in [(6, 'STA'), (9, 'STD')]:
            if not _valid_time(ws.cell(r, col).value):
                errors.append(f"row {r} (SL {sl}): {label} not a valid HH:MM ({ws.cell(r, col).value!r})")
        if not _valid_freq(ws.cell(r, 2).value):
            errors.append(f"row {r} (SL {sl}): FREQ not digits 1-7 ({ws.cell(r, 2).value!r})")
        for col, label in [(5, 'ORG'), (8, 'DEST')]:
            code = str(ws.cell(r, col).value).strip()
            if code not in known_airports:
                warnings.append(f"row {r} (SL {sl}): {label} '{code}' unknown airport -> flagged UNK")
        ac = str(ws.cell(r, 3).value).strip()
        if ac not in known_aircraft:
            warnings.append(f"row {r} (SL {sl}): aircraft '{ac}' unknown -> kept as-is (no specs)")
        for col, label in [(4, 'arr FLT NO'), (7, 'dep FLT NO')]:
            if not str(ws.cell(r, col).value).strip():
                warnings.append(f"row {r} (SL {sl}): {label} empty")
    if not seen_sl:
        errors.append("no data rows found under the header")
    return errors, warnings
