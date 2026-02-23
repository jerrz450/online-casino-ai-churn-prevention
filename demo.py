#!/usr/bin/env python3
"""
Casino Churn Detection V2 — Live Demo
--------------------------------------
Runs the full pipeline end-to-end in one command:
  simulation → live monitoring → analyst agent → apply → summary

Usage:
  python demo.py            # 100 players, 60s simulation
  python demo.py --quick    # 50 players, 20s simulation
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import timedelta

try:
    import httpx
    from rich import box
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
except ImportError:
    print("Demo requires 'rich' and 'httpx'. Install with:  pip install rich httpx")
    sys.exit(1)


BACKEND          = "http://localhost:8000"
SIMULATOR        = "http://localhost:8001"
BACKEND_INTERNAL = "http://backend:8000"   # used by simulator container to reach backend

console = Console()


# ─── output helpers ───────────────────────────────────────────────────────────

def phase(n: int, title: str):
    console.print()
    console.print(f"[bold cyan]● PHASE {n}  {title}[/bold cyan]")

def ok(msg: str):
    console.print(f"  [green]✓[/green] {msg}")

def warn(msg: str):
    console.print(f"  [yellow]⚠[/yellow]  {msg}")

def err(msg: str):
    console.print(f"  [red]✗[/red] {msg}")


# ─── Phase 1: health check ────────────────────────────────────────────────────

async def check_health(client: httpx.AsyncClient) -> bool:
    phase(1, "SERVICE HEALTH CHECK")
    all_ok = True
    for name, url in [("backend", BACKEND), ("simulator", SIMULATOR)]:
        try:
            r = await client.get(f"{url}/health", timeout=5)
            if r.status_code == 200:
                ok(f"{name:<12} {url}  [dim]healthy[/dim]")
            else:
                err(f"{name:<12} {url}  HTTP {r.status_code}")
                all_ok = False
        except Exception:
            err(f"{name:<12} {url}  unreachable")
            all_ok = False
    if not all_ok:
        console.print()
        console.print("  [bold red]Start services first:[/bold red]  docker compose up -d")
    return all_ok


# ─── Phase 2: start simulation ────────────────────────────────────────────────

async def start_simulation(client: httpx.AsyncClient, num_players: int):
    phase(2, "SIMULATION START")
    console.print(f"  {num_players} players  ·  whale 10%  ·  grinder 30%  ·  casual 60%")
    await client.post(f"{BACKEND}/ingest/new-run", timeout=10)
    ok("New run initialized")
    await client.post(
        f"{SIMULATOR}/simulator/start",
        params={
            "num_players": num_players,
            "tick_interval_seconds": 0.05,
            "target_url": f"{BACKEND_INTERNAL}/ingest/event",
            "mode": "inference",
        },
        timeout=10,
    )
    ok("Simulator started")


# ─── Phase 3: live monitoring ─────────────────────────────────────────────────

def _query_decisions() -> dict:
    try:
        import os
        import psycopg
        from dotenv import load_dotenv
        load_dotenv()
        conn_str = (
            f"host=localhost "
            f"port=5432 "
            f"dbname={os.getenv('POSTGRES_CASINO_DB', 'casino_churn')} "
            f"user={os.getenv('POSTGRES_CASINO_USER', 'casino_user')} "
            f"password={os.getenv('POSTGRES_CASINO_PASSWORD', 'casino_pass')}"
        )
        with psycopg.connect(conn_str) as conn:
            row = conn.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE action = 'offer_sent')  AS churns,
                    COUNT(*)                                        AS total,
                    ROUND(AVG(churn_score)::numeric, 3)            AS avg_score
                FROM decisions
                WHERE timestamp > NOW() - INTERVAL '10 minutes'
            """).fetchone()
        return {"churns": row[0], "total": row[1], "avg_score": float(row[2] or 0)}
    except Exception:
        return {"churns": 0, "total": 0, "avg_score": 0.0}


def _stats_table(stats: dict, decisions: dict, elapsed: float) -> Table:
    from rich.columns import Columns

    sim = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold dim", padding=(0, 1), title="[dim]Simulator[/dim]")
    sim.add_column("Elapsed",  style="cyan",  min_width=10)
    sim.add_column("Events",   justify="right", style="white", min_width=10)
    sim.add_column("EPS",      justify="right", style="green", min_width=8)
    sim.add_column("Errors",   justify="right", style="red",   min_width=8)
    sim.add_row(
        str(timedelta(seconds=int(elapsed))),
        f"{stats.get('total_events', 0):,}",
        f"{stats.get('actual_eps', 0.0):.1f}",
        str(stats.get('total_errors', 0)),
    )

    dec = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold dim", padding=(0, 1), title="[dim]XGBoost Decisions[/dim]")
    dec.add_column("Scored",       justify="right", style="white",  min_width=8)
    dec.add_column("Churn Alerts", justify="right", style="red",    min_width=14)
    dec.add_column("Avg Score",    justify="right", style="yellow", min_width=10)
    churns = decisions.get("churns", 0)
    total  = decisions.get("total", 0)
    pct    = f"({100*churns//total}%)" if total else ""
    dec.add_row(
        f"{total:,}",
        f"[bold red]{churns:,}[/bold red] {pct}",
        f"{decisions.get('avg_score', 0.0):.3f}",
    )

    return Columns([sim, dec], padding=(0, 4))


async def monitor_simulation(client: httpx.AsyncClient, duration: int):
    phase(3, f"LIVE DECISIONS  [{duration}s]")
    start = time.monotonic()
    decisions: dict = {"churns": 0, "total": 0, "avg_score": 0.0}
    with Live(console=console, refresh_per_second=2) as live:
        while True:
            elapsed = time.monotonic() - start
            try:
                r = await client.get(f"{SIMULATOR}/simulator/stats", timeout=3)
                stats = r.json()
            except Exception:
                stats = {}
            decisions = await asyncio.to_thread(_query_decisions)
            live.update(_stats_table(stats, decisions, elapsed))
            if elapsed >= duration:
                break
            await asyncio.sleep(3)


async def stop_simulation(client: httpx.AsyncClient):
    try:
        await client.post(f"{SIMULATOR}/simulator/stop", timeout=10)
    except Exception:
        pass
    ok("Simulation stopped")


# ─── Phase 4: analyst agent ───────────────────────────────────────────────────

_NODE_LABELS = {
    "gather_stats":   "Collecting metrics...",
    "analyze":        "Reasoning...",
    "self_evaluate":  "Self-critiquing...",
    "await_approval": "Analysis complete.",
    "apply":          "Executing...",
}


async def stream_analyst(client: httpx.AsyncClient) -> dict | None:
    phase(4, "ANALYST AGENT")

    streaming_tokens = False
    interrupt_payload: dict | None = None

    def end_token_line():
        nonlocal streaming_tokens
        if streaming_tokens:
            sys.stdout.write("\n")
            sys.stdout.flush()
            streaming_tokens = False

    async with client.stream("POST", f"{BACKEND}/agents/analyze", timeout=None) as resp:
        async for line in resp.aiter_lines():
            if not line.startswith("data: "):
                continue
            try:
                msg = json.loads(line[6:])
            except json.JSONDecodeError:
                continue

            mtype = msg.get("type")

            if mtype == "node":
                end_token_line()
                label = _NODE_LABELS.get(msg["name"], "")
                console.print(f"\n  [bold white][{msg['name']}][/bold white] [dim]{label}[/dim]")

            elif mtype == "tool_start":
                name = msg.get("name", "")
                console.print(f"    [dim]↳ {name} ...[/dim]")

            elif mtype == "tool_end":
                preview = (msg.get("preview") or "")[:100]
                name = msg.get("name", "")
                console.print(f"    [dim]↳[/dim] [cyan]{name:<30}[/cyan] [green]✓[/green]  [dim]{preview}[/dim]")

            elif mtype == "token":
                content = msg.get("content") or ""
                if content:
                    if not streaming_tokens:
                        sys.stdout.write("    ")
                        streaming_tokens = True
                    sys.stdout.write(content)
                    sys.stdout.flush()

            elif mtype == "interrupt":
                end_token_line()
                interrupt_payload = msg

            elif mtype == "done":
                end_token_line()
                ok("Done")

    end_token_line()
    return interrupt_payload


# ─── Recommendations ──────────────────────────────────────────────────────────

SAFE_ACTIONS = {"update_threshold", "reload_model", "update_train_config"}
SKIP_ACTIONS = {"trigger_retrain"}


def prompt_approval(recs: list[dict]) -> tuple[list[str], dict]:
    console.print()
    console.print("  [bold]RECOMMENDATIONS[/bold]")

    safe_recs = [r for r in recs if r.get("action") in SAFE_ACTIONS]
    skip_recs = [r for r in recs if r.get("action") in SKIP_ACTIONS]

    t = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold", padding=(0, 1))
    t.add_column("#",         width=4)
    t.add_column("Action",    width=24)
    t.add_column("Rationale", width=54, no_wrap=False)
    t.add_column("Params",    width=20)

    for i, r in enumerate(recs, 1):
        params = r.get("params") or {}
        param_str = "  ".join(f"{k}={v}" for k, v in params.items() if v is not None)
        skipped = r.get("action") in SKIP_ACTIONS
        style = "dim" if skipped else ""
        suffix = "  [dim](skipped — takes minutes)[/dim]" if skipped else ""
        t.add_row(str(i), r.get("action", "") + suffix, r.get("rationale", "")[:52], param_str or "—", style=style)

    console.print(t)

    if not safe_recs:
        warn("No approvable actions (trigger_retrain skipped in demo).")
        return [], {}

    console.print()
    console.print("  [bold]Approve recommendations?[/bold]")
    console.print("  [cyan][a][/cyan] Approve all safe actions")
    console.print("  [cyan][s][/cyan] Select individually by number")
    console.print("  [cyan][n][/cyan] Skip — apply nothing")
    console.print()

    while True:
        choice = input("  Choice [a/s/n]: ").strip().lower()
        if choice in ("a", "s", "n"):
            break
        console.print("  [yellow]Enter a, s, or n[/yellow]")

    if choice == "n":
        console.print("  [dim]Skipping apply.[/dim]")
        return [], {}

    if choice == "a":
        approved = safe_recs
    else:
        console.print()
        for i, r in enumerate(safe_recs, 1):
            params = r.get("params") or {}
            param_str = " ".join(f"{k}={v}" for k, v in params.items() if v is not None)
            console.print(f"    {i}. [cyan]{r['action']}[/cyan]  [dim]{param_str}[/dim]")
        console.print()
        sel = input("  Numbers to approve (e.g. 1,2 or 'all'): ").strip()
        if sel.lower() == "all":
            approved = safe_recs
        else:
            indices = []
            for x in sel.split(","):
                x = x.strip()
                if x.isdigit() and 1 <= int(x) <= len(safe_recs):
                    indices.append(int(x) - 1)
            approved = [safe_recs[i] for i in indices]

    if approved:
        console.print(f"\n  [green]Approving:[/green] {', '.join(r['action'] for r in approved)}")
    else:
        warn("Nothing selected.")

    approved_actions = [r["action"] for r in approved]
    params_out = {
        r["action"]: {k: v for k, v in (r.get("params") or {}).items() if v is not None}
        for r in approved
    }
    return approved_actions, params_out


# ─── Phase 5: apply ───────────────────────────────────────────────────────────

async def apply_actions(client: httpx.AsyncClient, thread_id: str, approved_actions: list[str], params: dict):
    phase(5, "APPLYING CHANGES")
    body = {"approved_actions": approved_actions, "params": params}
    async with client.stream("POST", f"{BACKEND}/agents/apply/{thread_id}", json=body, timeout=None) as resp:
        async for line in resp.aiter_lines():
            if not line.startswith("data: "):
                continue
            try:
                msg = json.loads(line[6:])
                if msg.get("type") == "node":
                    console.print(f"  [{msg['name']}] Executing...")
                elif msg.get("type") == "done":
                    ok("Done")
            except json.JSONDecodeError:
                pass


# ─── Phase 6: summary ─────────────────────────────────────────────────────────

def show_summary(interrupt_payload: dict | None, approved_actions: list[str], params: dict, old_threshold: float):
    phase(6, "SUMMARY")

    recs = (interrupt_payload or {}).get("recommendations", [])
    new_threshold = old_threshold
    for r in recs:
        if r.get("action") == "update_threshold" and "update_threshold" in approved_actions:
            v = (r.get("params") or {}).get("value")
            if v is not None:
                new_threshold = float(v)

    t = Table(box=box.SIMPLE_HEAVY, show_header=False, padding=(0, 1))
    t.add_column("Metric", style="cyan", width=30)
    t.add_column("Value",  width=34)

    t.add_row("Actions applied",  ", ".join(approved_actions) if approved_actions else "none")
    t.add_row("Threshold before", f"{old_threshold:.2f}")
    t.add_row("Threshold after",  f"[bold green]{new_threshold:.2f}[/bold green]" if new_threshold != old_threshold else f"{new_threshold:.2f}")

    if interrupt_payload:
        report = (interrupt_payload.get("report") or "").replace("\n", " ")
        if report:
            t.add_row("Report excerpt", report[:80] + ("..." if len(report) > 80 else ""))

    console.print(t)


# ─── main ─────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="Casino Churn Detection V2 — Live Demo")
    parser.add_argument("--quick", action="store_true", help="20s simulation with 50 players")
    args = parser.parse_args()

    num_players   = 50  if args.quick else 100
    duration      = 20  if args.quick else 60
    old_threshold = 0.30

    console.print(Panel.fit(
        "[bold cyan]CASINO CHURN DETECTION — V2 LIVE DEMO[/bold cyan]\n"
        "[dim]XGBoost scoring  ·  LangGraph analyst  ·  human-in-the-loop[/dim]",
        border_style="cyan",
    ))

    async with httpx.AsyncClient() as client:

        if not await check_health(client):
            return

        await start_simulation(client, num_players)
        try:
            await monitor_simulation(client, duration)
        except (KeyboardInterrupt, asyncio.CancelledError):
            console.print("\n  [yellow]Interrupted — stopping simulation...[/yellow]")
            await stop_simulation(client)
            return

        await stop_simulation(client)

        try:
            interrupt_payload = await stream_analyst(client)
        except (KeyboardInterrupt, asyncio.CancelledError):
            console.print("\n  [yellow]Interrupted.[/yellow]")
            return

        approved_actions: list[str] = []
        params_dict: dict = {}
        thread_id = "analyst_main"

        if interrupt_payload:
            thread_id = interrupt_payload.get("thread_id", "analyst_main")
            recs = interrupt_payload.get("recommendations", [])
            if recs:
                approved_actions, params_dict = prompt_approval(recs)
            else:
                warn("Analyst returned no recommendations.")
        else:
            warn("No interrupt received from analyst — check backend logs.")

        if approved_actions:
            await apply_actions(client, thread_id, approved_actions, params_dict)
        else:
            console.print()
            console.print("  [dim]No safe actions to apply — skipping apply phase.[/dim]")

        show_summary(interrupt_payload, approved_actions, params_dict, old_threshold)

    console.print()


if __name__ == "__main__":
    asyncio.run(main())
