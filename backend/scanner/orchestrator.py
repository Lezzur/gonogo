import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session
from database import SessionLocal
from models import Scan
from config import REPORTS_DIR
from utils.progress import progress_manager

from scanner.recon import run_reconnaissance
from scanner.intent import analyze_intent
from scanner.tech_stack import detect_tech_stack
from scanner.lenses.functionality import evaluate_functionality
from scanner.lenses.design import evaluate_design
from scanner.lenses.ux import evaluate_ux
from scanner.lenses.performance import evaluate_performance
from scanner.lenses.accessibility import evaluate_accessibility
from scanner.lenses.code_content import evaluate_code_content
from scanner.synthesis import synthesize_findings
from scanner.report_gen import generate_reports


async def run_scan(
    scan_id: str,
    api_key: str,
    llm_provider: str = "gemini",
    auth_credentials: Optional[Dict[str, str]] = None
):
    """Main pipeline orchestrator - runs Steps 0-10."""
    db = SessionLocal()

    try:
        # Get scan record
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            return

        # Update status
        scan.status = "running"
        scan.started_at = datetime.now(timezone.utc)
        db.commit()

        # Step 0: Reconnaissance (No LLM)
        await progress_manager.send_progress(
            scan_id, "step_0_recon", "Crawling site and gathering data...", 5
        )
        scan.current_step = "step_0_recon"
        db.commit()

        recon_data = await run_reconnaissance(
            url=scan.url,
            scan_id=scan_id,
            test_route=scan.test_route,
            auth_credentials=auth_credentials
        )

        # Track auth status for synthesis
        auth_status = "no_auth_required"
        if auth_credentials:
            # Check if we got authenticated pages (more than just login page)
            authenticated_pages = [p for p in recon_data.pages if '/login' not in p.url.lower() and '/signin' not in p.url.lower()]
            if authenticated_pages:
                auth_status = "auth_successful"
            else:
                auth_status = "auth_attempted_unclear"

        await progress_manager.send_progress(
            scan_id, "step_0_recon", "Reconnaissance complete", 15
        )

        # Step 1: Intent Analysis
        await progress_manager.send_progress(
            scan_id, "step_1_intent", "Analyzing project intent...", 20
        )
        scan.current_step = "step_1_intent"
        db.commit()

        intent_analysis = await analyze_intent(
            recon_data=recon_data,
            user_brief=scan.user_brief,
            api_key=api_key,
            llm_provider=llm_provider
        )
        scan.intent_analysis = intent_analysis.model_dump()
        db.commit()

        # Step 2: Tech Stack Detection
        await progress_manager.send_progress(
            scan_id, "step_2_tech", "Detecting tech stack...", 25
        )
        scan.current_step = "step_2_tech"
        db.commit()

        tech_stack = await detect_tech_stack(
            recon_data=recon_data,
            user_provided=scan.tech_stack_input,
            api_key=api_key,
            llm_provider=llm_provider
        )
        scan.tech_stack_detected = tech_stack.model_dump()
        db.commit()

        # Steps 3-8: Lens Evaluations (Parallel)
        await progress_manager.send_progress(
            scan_id, "step_3_8_lenses", "Evaluating across all quality lenses...", 30
        )
        scan.current_step = "step_3_8_lenses"
        db.commit()

        # Run all lens evaluations in parallel
        lens_tasks = [
            evaluate_functionality(recon_data, intent_analysis, tech_stack, api_key, llm_provider),
            evaluate_design(recon_data, intent_analysis, tech_stack, api_key, llm_provider),
            evaluate_ux(recon_data, intent_analysis, tech_stack, api_key, llm_provider),
            evaluate_performance(recon_data, intent_analysis, tech_stack, api_key, llm_provider),
            evaluate_accessibility(recon_data, intent_analysis, tech_stack, api_key, llm_provider),
            evaluate_code_content(recon_data, intent_analysis, tech_stack, api_key, llm_provider),
        ]

        lens_results = await asyncio.gather(*lens_tasks, return_exceptions=True)

        # Collect findings from all lenses
        all_findings = []
        lens_names = ["functionality", "design", "ux", "performance", "accessibility", "code_content"]
        for i, result in enumerate(lens_results):
            lens_name = lens_names[i] if i < len(lens_names) else f"lens_{i}"
            if isinstance(result, Exception):
                print(f"❌ {lens_name} lens failed: {result}")
                continue
            print(f"✓ {lens_name} lens returned {len(result)} findings")
            all_findings.extend(result)

        print(f"\n📊 Total findings collected from all lenses: {len(all_findings)}")

        await progress_manager.send_progress(
            scan_id, "step_3_8_lenses", "All lens evaluations complete", 70
        )

        # Step 9: Synthesis & Scoring
        await progress_manager.send_progress(
            scan_id, "step_9_synthesis", "Synthesizing findings and scoring...", 75
        )
        scan.current_step = "step_9_synthesis"
        db.commit()

        synthesis = await synthesize_findings(
            findings=all_findings,
            intent_analysis=intent_analysis,
            auth_status=auth_status,
            api_key=api_key,
            llm_provider=llm_provider
        )

        scan.verdict = synthesis.verdict
        scan.overall_score = synthesis.overall_score
        scan.overall_grade = synthesis.overall_grade
        scan.lens_scores = {k: v.model_dump() for k, v in synthesis.lens_scores.items()}
        scan.findings_count = synthesis.findings_count
        scan.top_3_actions = synthesis.top_3_actions
        db.commit()

        await progress_manager.send_progress(
            scan_id, "step_9_synthesis", "Scoring complete", 85
        )

        # Step 10: Report Generation
        await progress_manager.send_progress(
            scan_id, "step_10_reports", "Generating reports...", 90
        )
        scan.current_step = "step_10_reports"
        db.commit()

        report_a_path, report_b_path = await generate_reports(
            scan_id=scan_id,
            url=scan.url,
            synthesis=synthesis,
            tech_stack=tech_stack,
            api_key=api_key,
            llm_provider=llm_provider
        )

        scan.report_a_path = str(report_a_path)
        scan.report_b_path = str(report_b_path)
        db.commit()

        # Complete
        scan.status = "completed"
        scan.completed_at = datetime.now(timezone.utc)
        scan.duration_seconds = (scan.completed_at - scan.started_at).total_seconds()
        scan.current_step = None
        scan.progress_message = "Scan complete"
        db.commit()

        await progress_manager.send_complete(
            scan_id, synthesis.verdict, synthesis.overall_score
        )

    except Exception as e:
        # Handle failure
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if scan:
            scan.status = "failed"
            scan.error_message = str(e)
            scan.completed_at = datetime.now(timezone.utc)
            if scan.started_at:
                scan.duration_seconds = (scan.completed_at - scan.started_at).total_seconds()
            db.commit()

        await progress_manager.send_error(scan_id, str(e))
        raise

    finally:
        db.close()
