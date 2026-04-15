"""RumpTACO CLI — Typer 엔트리.

Usage:
    python cli.py collect        # 시장+발언 수집 (Supabase 없으면 stdout)
    python cli.py score          # 최근 발언 Aggression 점수화
    python cli.py predict        # 전체 파이프라인 + 예측만 (리포트 X)
    python cli.py daily          # 전체 파이프라인 + 텔레그램 발송 + 파일 저장
    python cli.py smoke-agg      # Aggression 샘플 테스트
    python cli.py smoke-pain     # Pain 샘플 테스트
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import typer
from dotenv import load_dotenv
from rich import print as rprint

from collectors.market import collect_snapshot, snapshot_dict
from collectors.statements import collect_recent, to_dicts
from scoring.aggression import score_batch, score_statement
from scoring.pain import compute_pain
from scoring.translator import translate_batch
from models.rule_based import predict as rule_predict
from notify.telegram import format_daily_report, send_message, save_report
from dashboard.export import write_snapshot
from db import supabase_client as sbdb


load_dotenv()
app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def collect(hours: int = 24):
    """시장 스냅샷 + 최근 발언 수집 후 stdout 출력."""
    snap = collect_snapshot()
    rprint("[bold cyan]Market Snapshot[/]")
    rprint(snapshot_dict(snap))

    items = collect_recent(hours=hours)
    rprint(f"\n[bold cyan]Statements ({len(items)}건)[/]")
    for s in items[:10]:
        rprint(f"  [{s.source}] {s.posted_at} {s.content[:90]}...")


@app.command()
def score(hours: int = 24, threshold: float = 50.0):
    """발언 점수화 (Haiku→Opus 단계)."""
    items = to_dicts(collect_recent(hours=hours))
    scored = score_batch(items, precise_threshold=threshold)
    for s in scored:
        rprint({k: s.get(k) for k in ("source", "aggression_score", "topic_tags", "rationale", "_model")})


@app.command()
def predict(hours: int = 24):
    """수집→점수화→Pain→TACO 확률 산출 후 출력."""
    snap = snapshot_dict(collect_snapshot())
    items = to_dicts(collect_recent(hours=hours))
    scored = score_batch(items) if items else []
    top = sorted(
        [s for s in scored if isinstance(s.get("aggression_score"), (int, float))],
        key=lambda x: x["aggression_score"],
        reverse=True,
    )
    max_agg = top[0]["aggression_score"] if top else 0.0

    pain = compute_pain(snap, history=None)
    pred = rule_predict(max_agg, pain.pain_index)

    rprint("[bold green]=== TACO Prediction ===[/]")
    rprint(f"Aggression (max): {max_agg}")
    rprint(f"Pain Index: {pain.pain_index} (contributions top: "
           f"{sorted(pain.contributions.items(), key=lambda x: -abs(x[1]))[:3]})")
    rprint(f"TACO Probability: {pred.taco_probability}%")
    rprint(f"Window: {pred.expected_window_hours}")
    rprint(f"Explanation: {pred.explanation}")


@app.command()
def daily(hours: int = 24, send: bool = True):
    """전체 파이프라인 + 텔레그램 발송 + 리포트 파일 저장."""
    snap = snapshot_dict(collect_snapshot())
    items = to_dicts(collect_recent(hours=hours))
    scored = score_batch(items) if items else []
    top = sorted(
        [s for s in scored if isinstance(s.get("aggression_score"), (int, float))],
        key=lambda x: x["aggression_score"],
        reverse=True,
    )
    max_agg = top[0]["aggression_score"] if top else 0.0

    pain = compute_pain(snap, history=None)
    pred = rule_predict(max_agg, pain.pain_index)

    top = translate_batch(top[:5])

    # --- Supabase 저장 (진실의 원천) ---
    if sbdb.is_enabled():
        rprint("[cyan]Supabase 저장 시작...[/]")
        sbdb.upsert_market_snapshot(snap)
        stmt_ids = sbdb.insert_statements(top)
        trigger_id = stmt_ids[0] if stmt_ids else None
        pred_id = sbdb.insert_prediction(
            taco_probability=pred.taco_probability,
            expected_window_hours=pred.expected_window_hours,
            aggression_score=pred.aggression_score,
            pain_index=pain.pain_index,
            model_version=pred.model_version,
            explanation=pred.explanation,
            trigger_statement_id=trigger_id,
        )
        rprint(f"[green]Supabase: predictions={pred_id}, statements={len(stmt_ids)}건[/]")
    else:
        rprint("[yellow]Supabase 미설정 — DB 저장 생략 (JSON만 사용)[/]")

    report = format_daily_report(
        prediction=pred, top_statements=top, market_snapshot=snap, pain_result=pain,
    )
    path = save_report(report)
    rprint(f"[green]리포트 저장: {path}[/]")

    json_path = write_snapshot(
        prediction=pred, pain_result=pain, market_snapshot=snap,
        top_statements=top,
    )
    rprint(f"[green]대시보드 JSON 저장: {json_path}[/]")

    rprint(report)
    if send:
        ok = send_message(report)
        rprint(f"[{'green' if ok else 'yellow'}]텔레그램 발송: {ok}[/]")


@app.command("smoke-agg")
def smoke_aggression():
    samples = [
        "I will impose 200% tariffs on all European cars effective May 1. Non-negotiable.",
        "China should be respectful. Just saying.",
        "Something very big is coming next week. Trust me.",
    ]
    for s in samples:
        r = score_statement(s, precise=False)
        rprint(json.dumps(r, ensure_ascii=False, indent=2))


@app.command("smoke-pain")
def smoke_pain():
    sample = {
        "treasury_10y": 4.7, "sp500": 5050, "djia": 38500, "nasdaq": 16000,
        "vix": 22, "wti_usd": 87, "breakeven_5y": 2.6, "btc_usd": 62000,
        "trump_approval": 43.5,
    }
    r = compute_pain(sample)
    rprint(f"Pain Index: {r.pain_index} / Weighted Z: {r.weighted_z}")
    for k, v in sorted(r.contributions.items(), key=lambda x: -abs(x[1])):
        rprint(f"  {k:18s} {v:+.4f}")


if __name__ == "__main__":
    app()
