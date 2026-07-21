# Making the Outage Lifecycle "Real-World" — Design Plans

## Problem statement

Today a single Excel/CSV upload carries **every field with its final value**, including
`cancellation_flag` and `actual_end_time`. In `dev_rebase_times` mode the importer even
sets `actual_end_time = now + 8min` at import (`file_ingestion_service._rebase_outage_dataframe`).

So at ingestion the system already "knows the future":
- **`actual_end_time`** — in reality this is a *post-fact* value, only knowable once power is
  actually restored. Knowing it upfront is time-travel.
- **`cancellation_flag`** — in reality this is a *later event* that may or may not happen, not
  an initial attribute.

Consequently the agent / lifecycle logic (`planned_outage_service._next_due_notification_type`)
doesn't truly *react* to events — it reads a snapshot whose answers were pre-written.

Real world: an outage is a **living record** updated by a **stream of events** from source
systems (OMS/ADMS/SCADA; planned work from work-management/GIS). Lifecycle:

| Stage | Known at this point | `actual_end_time` | `cancellation_flag` |
|-------|---------------------|-------------------|---------------------|
| Scheduled (create) | start_time, estimated_end_time (ETR) | NULL | false |
| Cancelled (event, optional) | work called off | NULL | **true** (arrives later) |
| Active (start) | outage began | NULL | false |
| Restored (event) | power actually back | **stamped now** | false |

Existing building blocks we can lean on:
- `RawOutageEvent` table already exists "for audit and replay" — the seed of event sourcing.
- `PlannedOutageScheduler` (APScheduler) + `get_due_lifecycle_notifications` already polls
  state over time — a primitive live loop.
- `estimated_end_time` (plan/ETR) vs `actual_end_time` (reality) are already separate columns.

---

## Option 1 — Event-driven / incremental updates (event-sourcing lite)

**Goal:** Data arrives as a stream of events, each carrying only what is realistically known
at that time; current state is derived by applying events in order.

**Event types:** `outage.created` (scheduled), `outage.updated` (ETR change), `outage.cancelled`,
`outage.started`, `outage.restored`.

**Design:**
- Add an ingestion endpoint that accepts a single event (and/or a batch/stream), e.g.
  `POST {API}/events/outage` with `{event_type, outage_id, payload, event_time}`.
- Persist raw into `RawOutageEvent` (already exists) for audit/replay.
- An **event applier/reducer** maps each event onto `OutageEvent` current state:
  - `created` → insert row: status=Scheduled, actual_end_time=NULL, cancellation_flag=false.
  - `cancelled` → set cancellation_flag=true, status=Cancelled.
  - `started` → status=Active.
  - `restored` → set actual_end_time=event_time, status=Completed/Restored.
- Optional: a `replay` command that rebuilds `OutageEvent` from `RawOutageEvent` (proves the
  event log is the source of truth).

**Touch points:** new `events` endpoint + router entry; new `EventApplierService`;
reuse `RawOutageEvent`; `OutageEvent` unchanged structurally.

**Effort:** High. **Risk:** Medium (new write path, ordering/idempotency concerns).
**Payoff:** Highest realism; foundation for everything else.

---

## Option 2 — Ingestion guards against "future knowledge"

**Goal:** Even with the current bulk upload, refuse to store values that couldn't be known yet,
so the data itself looks real.

**Rules to enforce in `FileIngestionService._clean_records` (OUTAGE_EVENT):**
- If status ∈ {Scheduled, Active}: force `actual_end_time = NULL` (drop any provided value).
- On initial create: force `cancellation_flag = false` (cancellation must come via an update/event).
- Invariant validation: reject/normalize illegal combos (e.g. Scheduled + actual_end_time set,
  or cancellation_flag true while status still Scheduled without a cancel timestamp).
- Rebase mode: stop pre-filling `actual_end_time`; only rebase start_time / estimated_end_time.
  (Restoration time should come from a restore event/simulator, not the importer.)

**Touch points:** `file_ingestion_service._clean_records` + `_rebase_outage_dataframe`;
possibly a small `outage_lifecycle_rules.py` for the invariants so they're reusable.

**Effort:** Low. **Risk:** Low. **Payoff:** Immediate realism of stored data; cheap guardrail.
Good first step even before Option 1.

---

## Option 3 — Cancellation as an event, not a preset column

**Goal:** Cancellation arrives asynchronously so the "Cancellation Alert" is genuinely reactive.

**Design:**
- Add `POST {API}/outages/{outage_id}/cancel` (or the `outage.cancelled` event from Option 1).
- Handler sets cancellation_flag=true, status=Cancelled, optionally records a `cancelled_at`.
- The existing lifecycle rule (`_next_due_notification_type`: `if outage.cancellation_flag →
  Cancellation Alert`) then fires only after the cancel event arrives — no code change needed
  there, just the *timing* of the flag flip becomes real.
- Consider adding a `cancelled_at` column (nullable) so cancellation has its own timestamp
  distinct from created_at (parallels actual_end_time for restoration).

**Touch points:** new cancel endpoint/handler; optional `cancelled_at` column + migration;
lifecycle logic unchanged.

**Effort:** Low–Medium. **Risk:** Low. **Payoff:** Cancellation demo becomes reactive.
Subset of Option 1; can ship standalone.

---

## Option 4 — Simulation harness (live-feed emulator)

**Goal:** With no real ADMS/OMS, a simulator drives realistic state transitions over time so the
system behaves like it's consuming a live feed.

**Design:**
- A `OutageFeedSimulator` (new job, or extend `PlannedOutageScheduler`) that on each tick:
  - Flips Scheduled → Active when `now >= start_time`.
  - Emits a **restoration** for Active outages after a realistic delay vs ETR — with jitter
    (sometimes early, sometimes late), setting actual_end_time + status=Completed.
  - Occasionally emits a **cancellation** for a Scheduled outage before its start.
- It should call the Option 1 event endpoint / Option 3 handlers (not write columns directly),
  so the simulator and real feeds share one path.
- Config knobs (reuse the `dev_*` / offset pattern in `config.py`): enable flag, restore-delay
  distribution, cancellation probability, tick interval.

**Touch points:** new `OutageFeedSimulator` in `app/jobs`; wire into lifespan/scheduler;
config settings; depends on Option 1 or 3 endpoints for the write path.

**Effort:** Medium. **Risk:** Low–Medium (timing/nondeterminism in demos — make it seedable/toggle).
**Payoff:** Best demo realism — "the system is reacting to live events."

---

## How they fit together & recommended sequencing

```
Option 2 (guards)  ─┐
                     ├─►  Option 3 (cancel event)  ─┐
Option 1 (events) ──┘                               ├─►  Option 4 (simulator)
                                                     ┘
```

Recommended order (each independently demoable):
1. **Option 2** — cheapest, instantly makes stored data honest. Ship first.
2. **Option 3** — add the cancel event path; cancellation becomes reactive.
3. **Option 1** — generalize to a full event ingestion + applier (created/started/restored too).
4. **Option 4** — simulator on top, driving Options 1/3 endpoints to emulate a live feed.

Minimal "feels real" milestone = Option 2 + Option 3. Full realism = all four.

## Cross-cutting concerns (apply to whichever options we pick)
- **Idempotency:** repeated/duplicate events must not double-apply (event id / dedupe).
- **Ordering:** out-of-order events (restore before start) — decide reject vs reconcile.
- **Lifecycle invariants:** one shared module so importer, event applier, and simulator agree.
- **Notifications already-sent guard** (`_already_sent`) stays the safety net against re-sends.
- **Reset/replay:** keep `dev_reset_on_upload`; add event-log replay if Option 1 lands.
