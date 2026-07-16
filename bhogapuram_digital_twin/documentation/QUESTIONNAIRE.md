# Questionnaire — items needing clarification (for Avra / Bhogapuram ops)

From the Jul-2026 meeting feedback. Everything implementable without guessing has
been implemented; each item below blocks or refines something specific, noted as
**[blocks]** or **[refines]**. Where we proceeded with an assumption, the current
default is stated so it can simply be corrected.

## Operations & scenarios
1. **Runway edge-lighting damage scenario** *[refines events.csv]* — we assumed
   damaged edge-line section → increased spacing/inspection ≈ **40-min average
   delay for movements 19:00–24:00**. What is the actual contingency procedure and
   realistic delay band (night-ops restriction? diversions after what duration)?
2. **Wildlife strike on taxiway** *[refines events.csv]* — we modelled a taxiway
   inspection/closure ≈ **30-min average arrival delay over a 2-hour window**.
   (a) Is the intended scenario an animal strike during taxi? (b) Typical
   inspection/closure duration at Bhogapuram? (c) Which taxiway(s) matter most?
3. **SLA targets** *[refines scenario verdicts]* — we assume max wait **20 min
   check-in / 15 min security**. What are the official Bhogapuram SLA targets
   (and any IATA LoS class committed to)?

## Staffing
4. **Staff ratios** *[refines POD staffing]* — we assume **1.2 staff per open
   check-in counter** (agents + supervision) and **4 staff per security lane**
   (lane crew). What are the planned crewing ratios — and separately for the
   **SBD self-bag-drop** positions (B01–B08, C01–C10) vs conventional counters?
5. **"Fine-tune according to our experience"** *[blocks the fine-tuned version]* —
   which parameters should carry the ops team's numbers: passenger show-up window
   (we use 150→45 min before STD), check-in service rate (72 pax/hr/counter),
   security throughput (144 pax/hr/lane), opening-period load factors? Please mark
   any that differ from our defaults.

## Data feeds
6. **SITA AODB** *[blocks live-mode design]* — delivery mechanism (API / file
   drop), message format (AIDX? custom?), fields available, refresh frequency, and
   whether a test feed is possible before COD.
7. **20-day data drops** *[refines pattern store]* — exactly what is shared 20
   days ahead (seasonal schedule only? ad-hoc changes? expected bookloads?), in
   what format, and via whom — so ingestion is automated, not manual.
8. **Post-opening actuals** *[blocks real retraining]* — with CUPPS/CUSS/E-Boarding
   confirmed unavailable, which feeds WILL exist for actual passenger counts
   (security-lane counters? boarding-gate scans by airline? SITA AODB pax fields?)—
   this determines what the models retrain on and what Aegis heals.

## Timing & master data
9. **COD date** *[blocks POD-on-COD final]* — we generated the POD for
   **2026-07-08**. Confirm the operative COD for the deliverable.
10. **Master data completeness** *[refines resource views]* — stands/gates/belts/CIC
    are taken from MASTER DATA RESOURCES.xlsx as-is (18 stands, 12 gates, 4 belts,
    40 check-in positions). Any additions/renumbering expected before COD, and the
    official runway/taxiway designators for event naming?
11. **Opening-period demand** *[refines twin volumes]* — should the twin assume
    VTZ traffic transfers 1:1 to Bhogapuram from day one, or a ramp-up factor
    (e.g. 85% in month 1)? Any airline schedule changes announced for the move?
