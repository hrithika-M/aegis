# input — canonical real sources

To avoid duplicating large files, the twin reads the real inputs directly from the
repo's data folder rather than copies here:

| Logical input | Actual file |
|---|---|
| VTZ schedule (`MAIN FILE` sheet) | `../../data/bhogapuram_vtz/VTZ_schedule_S26.xlsx` |
| Monthly traffic (airport totals) | `../../data/bhogapuram_vtz/vtz_monthly_traffic.csv` |
| Route-level monthly pax (DGCA) | `../../data/bhogapuram_vtz/vtz_citypair_monthly.csv` |
| Route profile (airline/aircraft/LF) | `../../data/bhogapuram_vtz/vtz_route_profile.csv` |
| National daily reference (MoCA) | `../../data/bhogapuram_vtz/national_daily_reference.csv` |

These are the single source of truth. `build/build_masters.py` reads the schedule
from the path above (the `MAIN FILE` sheet specifically — the workbook also holds
our derived CSVs as extra tabs).
