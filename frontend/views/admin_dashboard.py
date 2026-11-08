# -*- coding: utf-8 -*-
"""Admin Dashboard — Main FinOps Command Center.

Responsibilities:
- Payment operations, FinOps, AI investigation, and incident decisions.
- Real-time KPI monitoring (Total Transactions, Revenue, Success Rate, Failed Payments, Active Anomalies, Data Quality, Gateway Health).
- 10-Stage Visual Workflow:
    DATA INGESTION -> DATA QUALITY -> PAYMENT ANALYTICS -> ML ANOMALY DETECTION ->
    AI INVESTIGATION -> EVIDENCE -> HUMAN APPROVAL -> ACTION -> AUDIT
- Demo Incident: RAMESHSWARAM CAFE UPI Failure Spike with interactive Approve/Reject.
- Full Data Engineering visibility: CSV/URL ingestion, run IDs, data quality, and cryptographic audit.
"""
import datetime as dt
import hashlib
import uuid
from decimal import Decimal
import pandas as pd
from sqlalchemy import text, func
import streamlit as st

from backend.app.db.base import SessionLocal
from backend.app.models.ops import AuditLog
from backend.app.models.payments import (
    PaymentIngestionRun,
    PaymentTransaction,
)
from frontend.styles import render_html


def _render_10_step_workflow():
    """Render the master 10-step visual architecture workflow."""
    render_html("""
    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:1rem 1.25rem; margin-bottom:1.5rem; box-shadow:0 1px 3px rgba(0,0,0,0.02);">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
            <div style="font-size:0.8rem; font-weight:800; text-transform:uppercase; letter-spacing:0.06em; color:#475569;">
                End-to-End Autonomous Payment Pipeline • 10-Stage Lifecycle
            </div>
            <span style="font-size:0.72rem; color:#2563EB; font-weight:700; background:#EFF6FF; padding:2px 8px; border-radius:4px;">
                FinOps + Data Engineering + LangGraph AI
            </span>
        </div>
        <div style="display:grid; grid-template-columns: repeat(10, 1fr); gap:6px;">
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-top:3px solid #0284C7; border-radius:8px; padding:6px 4px; text-align:center;">
                <div style="font-size:0.6rem; font-weight:800; color:#0284C7;">STEP 1</div>
                <div style="font-size:0.72rem; font-weight:700; color:#0F172A; line-height:1.2;">Data Ingestion</div>
            </div>
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-top:3px solid #0284C7; border-radius:8px; padding:6px 4px; text-align:center;">
                <div style="font-size:0.6rem; font-weight:800; color:#0284C7;">STEP 2</div>
                <div style="font-size:0.72rem; font-weight:700; color:#0F172A; line-height:1.2;">Data Quality</div>
            </div>
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-top:3px solid #3B82F6; border-radius:8px; padding:6px 4px; text-align:center;">
                <div style="font-size:0.6rem; font-weight:800; color:#3B82F6;">STEP 3</div>
                <div style="font-size:0.72rem; font-weight:700; color:#0F172A; line-height:1.2;">Payment Analytics</div>
            </div>
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-top:3px solid #EF4444; border-radius:8px; padding:6px 4px; text-align:center;">
                <div style="font-size:0.6rem; font-weight:800; color:#EF4444;">STEP 4</div>
                <div style="font-size:0.72rem; font-weight:700; color:#0F172A; line-height:1.2;">ML Detection</div>
            </div>
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-top:3px solid #8B5CF6; border-radius:8px; padding:6px 4px; text-align:center;">
                <div style="font-size:0.6rem; font-weight:800; color:#8B5CF6;">STEP 5</div>
                <div style="font-size:0.72rem; font-weight:700; color:#0F172A; line-height:1.2;">AI Investigation</div>
            </div>
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-top:3px solid #8B5CF6; border-radius:8px; padding:6px 4px; text-align:center;">
                <div style="font-size:0.6rem; font-weight:800; color:#8B5CF6;">STEP 6</div>
                <div style="font-size:0.72rem; font-weight:700; color:#0F172A; line-height:1.2;">Evidence</div>
            </div>
            <div style="background:#FFFBEB; border:1px solid #FCD34D; border-top:3px solid #F59E0B; border-radius:8px; padding:6px 4px; text-align:center;">
                <div style="font-size:0.6rem; font-weight:800; color:#D97706;">STEP 7</div>
                <div style="font-size:0.72rem; font-weight:800; color:#B45309; line-height:1.2;">Human Approval</div>
            </div>
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-top:3px solid #10B981; border-radius:8px; padding:6px 4px; text-align:center;">
                <div style="font-size:0.6rem; font-weight:800; color:#10B981;">STEP 8</div>
                <div style="font-size:0.72rem; font-weight:700; color:#0F172A; line-height:1.2;">Action Executed</div>
            </div>
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-top:3px solid #059669; border-radius:8px; padding:6px 4px; text-align:center;">
                <div style="font-size:0.6rem; font-weight:800; color:#059669;">STEP 9</div>
                <div style="font-size:0.72rem; font-weight:700; color:#0F172A; line-height:1.2;">Audit Logged</div>
            </div>
            <div style="background:#ECFDF5; border:1px solid #A7F3D0; border-top:3px solid #047857; border-radius:8px; padding:6px 4px; text-align:center;">
                <div style="font-size:0.6rem; font-weight:800; color:#047857;">STEP 10</div>
                <div style="font-size:0.72rem; font-weight:800; color:#065F46; line-height:1.2;">System Restored</div>
            </div>
        </div>
    </div>
    """)


APPROVAL_INCIDENTS = [
    {"id":"INC-RC-982", "workflow":"WF-RAMESHWARAM-REROUTE", "merchant":"Rameshwaram Cafe", "method":"UPI", "change":"6.2% → 14.8% failure rate", "affected":"27 payments", "evidence":"Primary bank-switch latency rose above 4,200 ms; several cafe orders remained pending.", "suggestion":"Review routing through healthy ICICI or Axis switches."},
    {"id":"INC-204", "workflow":"WF-INC-204", "merchant":"Northstar Marketplace", "method":"Cards", "change":"3.1% → 9.7% decline rate", "affected":"43 payments", "evidence":"Issuer timeouts increased across one acquiring route.", "suggestion":"Temporarily shift eligible card traffic to a healthy acquiring route."},
    {"id":"INC-315", "workflow":"WF-INC-315", "merchant":"SwiftDrop Delivery", "method":"Netbanking", "change":"2.4% → 11.2% pending rate", "affected":"31 payments", "evidence":"Payment confirmations are arriving later than the normal processing window.", "suggestion":"Reconcile pending orders before retrying to avoid duplicate charges."},
    {"id":"INC-188", "workflow":"WF-INC-188", "merchant":"TripNest Travel", "method":"Wallet", "change":"0.2% → 4.5% duplicate callback rate", "affected":"12 payments", "evidence":"Repeated provider callbacks share the same order references.", "suggestion":"Apply idempotency checks and reconcile affected orders."},
    {"id":"INC-441", "workflow":"WF-INC-441", "merchant":"LearnWell Subscriptions", "method":"UPI mandate", "change":"4.0% → 12.6% retry failure rate", "affected":"56 payments", "evidence":"Mandate responses show repeated bank-side declines during retries.", "suggestion":"Pause rapid retries and use a spaced retry schedule."},
    {"id":"INC-726", "workflow":"WF-INC-726", "merchant":"BrightPath Education", "method":"Bank transfer", "change":"12 settlements delayed", "affected":"12 settlements", "evidence":"Settlement records are older than the configured expected window.", "suggestion":"Reconcile settlement references and raise a provider follow-up."},
    {"id":"INC-309", "workflow":"WF-INC-309", "merchant":"MealRoute Foods", "method":"Refunds", "change":"18 refund mismatches", "affected":"18 refunds", "evidence":"Refund requests and provider status records do not match for these references.", "suggestion":"Reconcile refund status before issuing any repeat refund."},
    {"id":"INC-592", "workflow":"WF-INC-592", "merchant":"PlayForge Digital", "method":"Cards", "change":"Unusual attempt-rate increase", "affected":"36 attempts", "evidence":"Several rapid attempts share a device and payment fingerprint.", "suggestion":"Review the attempts and apply the configured risk checks."},
    {"id":"INC-147", "workflow":"WF-INC-147", "merchant":"CarePoint Clinic", "method":"UPI", "change":"1.8% → 8.9% failure rate", "affected":"22 payments", "evidence":"Failures cluster around a single payment route while other routes remain stable.", "suggestion":"Review the route health and use an available healthy route if confirmed."},
    {"id":"INC-830", "workflow":"WF-INC-830", "merchant":"CityGrid Utilities", "method":"Cards and UPI", "change":"Provider timeout increase", "affected":"29 payments", "evidence":"Timeout responses rose across a short interval and require reconciliation.", "suggestion":"Check provider status and reconcile uncertain payments before retrying."},
]


def _render_approval_incident(db, incident):
    """Render one independent illustrative incident and its recorded decision."""
    decision = db.query(AuditLog).filter(
        AuditLog.workflow_id == incident["workflow"],
        AuditLog.result_status.in_(["APPROVED", "REJECTED"]),
    ).order_by(AuditLog.timestamp.desc(), AuditLog.audit_id.desc()).first()
    approved = decision is not None and decision.result_status == "APPROVED"
    rejected = decision is not None and decision.result_status == "REJECTED"
    status = "Approved • decision recorded" if approved else "Rejected • review required" if rejected else "Awaiting admin decision"
    badge_color = "#059669" if approved else ("#DC2626" if rejected else "#B45309")
    badge_bg = "#ECFDF5" if approved else ("#FEF2F2" if rejected else "#FEF3C7")
    label = f"{incident['id']} · {incident['merchant']} · {incident['method']} · {status}"

    with st.expander(label, expanded=incident["id"] == "INC-RC-982" and decision is None):
        if approved:
            st.success("The admin approved this recommendation. The decision is recorded; live routing and payment status were not changed.")
        elif rejected:
            st.warning("The admin rejected this recommendation. The decision is recorded for review.")
        render_html(f"""
        <div style="background:#FFFFFF;border:1px solid #FCD34D;border-left:6px solid #F59E0B;border-radius:12px;padding:1rem 1.2rem;margin-bottom:0.75rem;">
          <div style="font-weight:800;color:#92400E;margin-bottom:8px;">Merchant payment issue · {incident['merchant']} · {incident['method']}</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
            <div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:8px;padding:.7rem;">
              <b>Observed impact</b><br>{incident['change']}<br>{incident['affected']} affected
            </div>
            <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;padding:.7rem;">
              <b>Evidence summary</b><br>{incident['evidence']}
            </div>
          </div>
          <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;padding:.7rem;margin-top:10px;">
            <b>Suggested response · admin decides</b><br>{incident['suggestion']}
          </div>
          <div style="margin-top:10px;color:{badge_color};background:{badge_bg};padding:6px 10px;border-radius:6px;font-weight:700;">Admin decision: {status}</div>
        </div>
        """)
        c1, c2, c3 = st.columns([1.2, 1, 1])
        with c1:
            st.button("🔍 Review evidence in AI Investigation", key=f"review_{incident['id']}", use_container_width=True, on_click=_navigate_to_ai_workspace)
        with c2:
            if st.button("✅ Approve suggestion" if not approved else "✅ Decision recorded: approved", key=f"approve_{incident['id']}", type="primary", use_container_width=True, disabled=decision is not None):
                _save_incident_decision(db, "APPROVED", incident)
                st.rerun()
        with c3:
            if st.button("Reject suggestion" if not rejected else "Decision recorded: rejected", key=f"reject_{incident['id']}", use_container_width=True, disabled=decision is not None):
                _save_incident_decision(db, "REJECTED", incident)
                st.rerun()
        if decision:
            st.caption(f"Decision saved for this incident at {str(decision.timestamp)[:19]}.")
            _render_recent_decisions(db, incident)


def _navigate_to_ai_workspace():
    """Select the AI Investigation page before Streamlit rebuilds its widgets."""
    st.session_state.selected_nav = "AI Investigation"
    st.session_state["main_role_navigation_radio_ADMIN"] = "AI Investigation"


def _save_incident_decision(db, decision, incident):
    if decision not in {"APPROVED", "REJECTED"}:
        raise ValueError("Invalid incident decision")
    existing = db.query(AuditLog).filter(AuditLog.workflow_id == incident["workflow"], AuditLog.result_status.in_(["APPROVED", "REJECTED"])).first()
    if existing:
        return
    db.add(AuditLog(
        audit_id="AUD-" + uuid.uuid4().hex,
        workflow_id=incident["workflow"], user_id="ADMIN",
        agent_node="human_approval_gate", tool_name="mitigation_review",
        input_hash=hashlib.sha256(f"{incident['id']}:{decision}:ILLUSTRATIVE".encode()).hexdigest(),
        result_status=decision, approval_status=decision,
        action="MITIGATION_APPROVED" if decision == "APPROVED" else "MITIGATION_REJECTED",
        timestamp=dt.datetime.now(dt.timezone.utc),
    ))
    db.commit()


def _render_recent_decisions(db, incident):
    st.markdown("**Latest decision for this incident**")
    records = db.query(AuditLog).filter(AuditLog.workflow_id == incident["workflow"], AuditLog.result_status.in_(["APPROVED", "REJECTED"])).order_by(AuditLog.timestamp.desc(), AuditLog.audit_id.desc()).limit(1).all()
    if not records:
        st.caption("No operational decisions recorded yet.")
    else:
        st.dataframe([{"Incident": f"{incident['merchant']} · {incident['id']}", "Decision": r.result_status, "Outcome": "Suggestion approved" if r.result_status == "APPROVED" else "Suggestion rejected", "Operator": r.user_id, "Timestamp": str(r.timestamp)[:19]} for r in records], hide_index=True, use_container_width=True)


def _render_admin_overview(db):
    """Render the complete Admin Overview with KPIs, 10-step workflow, and Demo Incident."""
    imports = db.query(PaymentIngestionRun).order_by(PaymentIngestionRun.started_at.desc()).all()
    selected_import = st.selectbox("Overview data", ["All payments"] + [r.run_id for r in imports], format_func=lambda rid: "All payments" if rid == "All payments" else next(f"{r.source_identifier} · {rid}" for r in imports if r.run_id == rid), key="overview_import_filter")
    query = db.query(PaymentTransaction)
    if selected_import != "All payments":
        query = query.filter(PaymentTransaction.augmentation_method == "CSV_LINEAGE_" + selected_import)
    total_txns = query.count()
    captured_count = query.filter(PaymentTransaction.status == "CAPTURED").count()
    failed_count = query.filter(PaymentTransaction.status == "FAILED").count()
    pending_count = query.filter(PaymentTransaction.status.in_(["PENDING", "AUTHORIZED"])).count()
    gmv = query.filter(PaymentTransaction.status == "CAPTURED").with_entities(func.sum(PaymentTransaction.amount)).scalar() or Decimal("0.00")
    terminal = captured_count + failed_count
    sr_pct = captured_count / terminal * 100 if terminal else 0.0
    fail_pct = failed_count / terminal * 100 if terminal else 0.0
    st.caption("Accepted rows from the configured database. Choose All payments or an import batch. Success/failure rates exclude pending payments. Rejected CSV rows are shown in ingestion history, not counted as failed payments.")
    counts = st.columns(3)
    counts[0].metric("Captured payments", captured_count)
    counts[1].metric("Failed payments", failed_count)
    counts[2].metric("Pending / authorized", pending_count)

    # 1. Top KPI Row (payment data only)
    st.markdown('<div style="font-size:0.82rem; font-weight:800; text-transform:uppercase; letter-spacing:0.06em; color:#475569; margin-bottom:0.6rem;">Platform Key Performance Indicators</div>', unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Total Transactions", f"{total_txns:,}", "Selected payment records")
    with k2:
        st.metric("Captured GMV", f"₹{float(gmv):,.0f}", f"{captured_count:,} Captured")
    with k3:
        st.metric("Success Rate", f"{sr_pct:.1f}%", "Target: >90%")
    with k4:
        st.metric("Failed Payments", f"{failed_count:,}", f"{fail_pct:.1f}% Failures ({pending_count} Pending)")

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    # 2. Main 10-Stage Visual Workflow
    _render_10_step_workflow()

    # 3. Live Demo Incident (Rameshwaram Cafe UPI Spike)
    _render_approval_incident(db, APPROVAL_INCIDENTS[0])

    # 4. Gateway Health & Volume Breakdown
    st.markdown('<div style="font-size:0.82rem; font-weight:800; text-transform:uppercase; letter-spacing:0.06em; color:#475569; margin-bottom:0.6rem;">Banking Gateway Routing & Method Telemetry</div>', unsafe_allow_html=True)
    h1, h2 = st.columns([1.1, 1.9])
    with h1:
        render_html(f"""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:1.25rem; height:100%; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
            <div style="font-size:0.88rem; font-weight:700; color:#0F172A; margin-bottom:0.8rem;">Payment Success Summary</div>
            <div style="display:flex; justify-content:space-between; margin-bottom:6px; font-size:0.82rem;">
                <span style="color:#059669; font-weight:600;">Captured Payments</span>
                <strong style="color:#0F172A;">{sr_pct:.1f}% ({captured_count:,})</strong>
            </div>
            <div style="width:100%; height:8px; background:#F1F5F9; border-radius:4px; overflow:hidden; margin-bottom:1rem;">
                <div style="width:{sr_pct:.1f}%; height:100%; background:#10B981;"></div>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:6px; font-size:0.82rem;">
                <span style="color:#DC2626; font-weight:600;">Failed Transactions</span>
                <strong style="color:#0F172A;">{fail_pct:.1f}% ({failed_count:,})</strong>
            </div>
            <div style="width:100%; height:8px; background:#F1F5F9; border-radius:4px; overflow:hidden; margin-bottom:1rem;">
                <div style="width:{fail_pct:.1f}%; height:100%; background:#EF4444;"></div>
            </div>
            <div style="font-size:0.75rem; color:#64748B; padding-top:0.6rem; border-top:1px solid #F1F5F9;">
                Pending / authorized: <strong style="color:#0F172A;">{pending_count:,}</strong>. Counts use the selected database records.
            </div>
        </div>
        """)

    with h2:
        render_html("""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:1.25rem; height:100%; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.8rem;">
                <div style="font-size:0.88rem; font-weight:700; color:#0F172A;">Core Banking Gateway Health</div>
                <span style="font-size:0.72rem; color:#64748B;">Illustrative scenario · not live telemetry</span>
            </div>
            <div style="display:grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap:10px;">
                <div style="border:1px solid #FCA5A5; background:#FEF2F2; border-radius:8px; padding:0.65rem; text-align:center;">
                    <div style="font-size:0.72rem; font-weight:700; color:#991B1B;">SBI UPI SWITCH</div>
                    <div style="font-size:1.15rem; font-weight:800; color:#DC2626; margin:2px 0;">76.2%</div>
                    <div style="font-size:0.65rem; color:#B91C1C; font-weight:600;">🚨 DEGRADED (4.2s)</div>
                </div>
                <div style="border:1px solid #A7F3D0; background:#ECFDF5; border-radius:8px; padding:0.65rem; text-align:center;">
                    <div style="font-size:0.72rem; font-weight:700; color:#065F46;">HDFC BANK</div>
                    <div style="font-size:1.15rem; font-weight:800; color:#059669; margin:2px 0;">97.8%</div>
                    <div style="font-size:0.65rem; color:#047857; font-weight:600;">🟢 HEALTHY (320ms)</div>
                </div>
                <div style="border:1px solid #A7F3D0; background:#ECFDF5; border-radius:8px; padding:0.65rem; text-align:center;">
                    <div style="font-size:0.72rem; font-weight:700; color:#065F46;">ICICI BANK</div>
                    <div style="font-size:1.15rem; font-weight:800; color:#059669; margin:2px 0;">98.4%</div>
                    <div style="font-size:0.65rem; color:#047857; font-weight:600;">🟢 HEALTHY (290ms)</div>
                </div>
                <div style="border:1px solid #A7F3D0; background:#ECFDF5; border-radius:8px; padding:0.65rem; text-align:center;">
                    <div style="font-size:0.72rem; font-weight:700; color:#065F46;">AXIS BANK</div>
                    <div style="font-size:1.15rem; font-weight:800; color:#059669; margin:2px 0;">96.9%</div>
                    <div style="font-size:0.65rem; color:#047857; font-weight:600;">🟢 HEALTHY (380ms)</div>
                </div>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.8rem; font-size:0.75rem; color:#64748B;">
                <span>Active Routing Engine: <strong>Rule-based Smart Routing</strong></span>
                <span style="color:#059669; font-weight:600;">Dynamic Fallback Enabled</span>
            </div>
        </div>
        """)


def _render_admin_payments(db):
    """Render payments ledger and filter controls."""
    st.markdown('<div style="font-size:0.88rem; font-weight:800; color:#0F172A; margin-bottom:0.75rem;">Payment Transaction Stream</div>', unsafe_allow_html=True)
    runs = db.query(PaymentIngestionRun).order_by(PaymentIngestionRun.started_at.desc()).all()
    selected_run = st.selectbox("Payment source", ["All payments"] + [r.run_id for r in runs], format_func=lambda rid: "All payments" if rid == "All payments" else next(f"{r.source_identifier} · {rid}" for r in runs if r.run_id == rid), key="ledger_import_filter")
    search = st.text_input("Search payment ID", key="ledger_payment_search").strip()
    query = db.query(PaymentTransaction)
    if selected_run != "All payments":
        query = query.filter(PaymentTransaction.augmentation_method == "CSV_LINEAGE_" + selected_run)
    if search:
        query = query.filter(PaymentTransaction.payment_id.contains(search, autoescape=True))
    total = query.count()
    page_count = max(1, (total + 99) // 100)
    page = st.number_input("Page", min_value=1, max_value=page_count, value=1, step=1, key=f"ledger_page_{selected_run}_{search}")
    txns = query.order_by(PaymentTransaction.created_at.desc(), PaymentTransaction.payment_id).offset((page - 1) * 100).limit(100).all()
    st.caption(f"{total:,} matching stored payments · Page {page} of {page_count} · 100 rows per page. Select your import to include older transaction dates.")
    if txns:
        st.dataframe([{
            "Payment ID": t.payment_id,
            "Order ID": t.order_id,
            "Merchant": t.merchant_id,
            "Amount (INR)": f"₹{float(t.amount):,.2f}",
            "Method": t.method,
            "Gateway": t.gateway,
            "Status": t.status,
            "Fee": f"₹{float(t.fee or 0):,.2f}",
            "Tax": f"₹{float(t.tax or 0):,.2f}",
            "Created": str(t.created_at)[:19] if t.created_at else "—",
        } for t in txns], hide_index=True, use_container_width=True)
    else:
        st.info("No transaction data available.")


def _render_admin_anomalies(db):
    """Render compact anomaly table."""
    st.markdown('<div style="font-size:0.88rem; font-weight:800; color:#0F172A; margin-bottom:0.75rem;">Active Payment Operations Anomalies</div>', unsafe_allow_html=True)
    anomalies_data = [
        {"Transaction / Incident": "INC-RC-982", "Entity": "RAMESHSWARAM CAFE", "Amount": "₹280 - ₹4,200", "Gateway": "SBI UPI Switch", "Issue": "High failure rate (14.8%)", "Severity": "CRITICAL", "AI Status": "Investigating", "Action": "Review Gate"},
        {"Transaction / Incident": "TXN_10291", "Entity": "RAMESHSWARAM CAFE", "Amount": "₹280", "Gateway": "SBI UPI", "Issue": "Gateway timeout (4,250ms)", "Severity": "HIGH", "AI Status": "Correlated", "Action": "Auto-Route"},
        {"Transaction / Incident": "TXN_10292", "Entity": "RAMESHSWARAM CAFE", "Amount": "₹320", "Gateway": "SBI UPI", "Issue": "Switch latency spike", "Severity": "HIGH", "AI Status": "Correlated", "Action": "Auto-Route"},
        {"Transaction / Incident": "TXN_10304", "Entity": "HDFC Retail Rail", "Amount": "₹45,000", "Gateway": "HDFC", "Issue": "Settlement variance", "Severity": "LOW", "AI Status": "Resolved", "Action": "Audited"},
    ]
    st.dataframe(pd.DataFrame(anomalies_data), hide_index=True, use_container_width=True)


def _render_admin_data_pipeline(db):
    """Render Data Engineering pipeline status, CSV/URL ingestion, and runs."""
    st.markdown('<div style="font-size:0.88rem; font-weight:800; color:#0F172A; margin-bottom:0.75rem;">Data Engineering & Pipeline Observability</div>', unsafe_allow_html=True)

    storage = db.get_bind().url
    storage_type = "PostgreSQL" if storage.get_backend_name() == "postgresql" else storage.get_backend_name().upper()
    st.markdown("**Data storage**")
    st.caption(f"Active database: {storage_type} · {storage.database or 'Configured database'}")
    st.caption("Accepted payments → payment_transactions · Import counts, status and timestamps → payment_ingestion_runs · Rejected-row details → payment_ingestion_records")
    st.caption("Original CSV files: backend/data/raw/ingestion_archive/ · Rejection reports: backend/data/rejected/")

    tab_csv, tab_data, tab_runs, tab_dq = st.tabs(["Upload Payment CSV", "Imported Payment Data", "Ingestion Runs & History", "Data Quality Guardrails"])

    with tab_data:
        st.subheader("Stored imported payments")
        imports = db.query(PaymentIngestionRun).order_by(PaymentIngestionRun.started_at.desc()).all()
        if not imports:
            st.info("No imports have been recorded in this database yet. Upload a payment CSV first.")
        else:
            chosen_run = st.selectbox("Choose an import", options=[r.run_id for r in imports], format_func=lambda rid: next(f"{r.source_identifier} · {r.run_id} · {r.status}" for r in imports if r.run_id == rid), key="stored_payment_import")
            stored = db.execute(text("SELECT payment_id, order_id, merchant_id, customer_id, amount, currency, method, bank, status, created_at FROM payment_transactions WHERE augmentation_method = :lineage ORDER BY created_at DESC LIMIT 1000"), {"lineage": "CSV_LINEAGE_" + chosen_run}).mappings().all()
            st.caption("Showing up to 1,000 accepted payment records for the selected import. Rejected and duplicate rows are not inserted as new payments.")
            if stored:
                frame = pd.DataFrame([dict(row) for row in stored])
                st.dataframe(frame, use_container_width=True, hide_index=True)
                st.download_button("Download displayed payment records", frame.to_csv(index=False).encode("utf-8"), file_name="imported_payments.csv", mime="text/csv", key="stored_payments_download")
            else:
                st.info("This run has no stored payment rows. Check its accepted/rejected counts in Ingestion Runs & History.")

    with tab_csv:
        st.markdown('<style>[data-testid="stFileUploaderDropzone"] svg {display:none;}</style>', unsafe_allow_html=True)
        st.subheader("Upload payment data")
        st.caption("CSV files up to 10 MB. Required columns: payment_id and amount (INR, in rupees). Include merchant_id, order_id, customer_id, currency, method, bank, status and created_at when available.")
        uploaded = st.file_uploader("Choose a payment CSV", type=["csv"], key="payment_csv_upload")
        if st.button("Validate & Import CSV", key="payment_csv_import", disabled=uploaded is None):
            if uploaded.size > 10 * 1024 * 1024:
                st.error("The CSV exceeds the 10 MB limit. Split it into smaller files.")
            else:
                from backend.app.services.ingestion_payments import PaymentCSVIngestionService
                try:
                    uploaded.seek(0)
                    with st.spinner("Validating and importing payment records..."):
                        result = PaymentCSVIngestionService(db).ingest_csv_file(uploaded, source_name=uploaded.name)
                    st.session_state["payment_csv_result"] = result
                except Exception as exc:
                    st.session_state.pop("payment_csv_result", None)
                    st.error(f"Import failed: {exc}")
        result = st.session_state.get("payment_csv_result")
        if result:
            st.success(f"Import completed · Run {result['run_id']}")
            cols = st.columns(4)
            for col, label, field in zip(cols, ["Received", "Accepted", "Rejected", "Duplicates"], ["records_received", "records_accepted", "records_rejected", "records_duplicated"]):
                col.metric(label, result[field])
            st.caption("Duplicates are included in the rejected count. Accepted records are saved immediately; review rejected rows before retrying.")
            from pathlib import Path
            report = result.get("rejected_file_generated")
            from backend.app.services.ingestion_payments import PaymentCSVIngestionService
            report_path = PaymentCSVIngestionService(db).rejected_dir / Path(report).name if report else None
            if report_path and report_path.is_file():
                st.download_button("Download rejected rows", report_path.read_bytes(), file_name="rejected_payment_rows.csv", mime="text/csv", key="payment_csv_rejections")
            with st.expander("Imported records and detected columns"):
                st.json(result["detected_mapping"])
                st.dataframe(db.execute(text("SELECT payment_id, merchant_id, amount, currency, method, bank, status FROM payment_transactions WHERE augmentation_method = :lineage LIMIT 100"), {"lineage": "CSV_LINEAGE_" + result["run_id"]}).mappings().all(), use_container_width=True)
        st.info("Where to see your data: Payments shows the payment ledger. Ingestion Runs & History shows processing counts and status. Accepted rows are stored in payment_transactions in the configured database. Original uploads and rejection reports are retained by the ingestion service.")

    with tab_runs:
        runs = db.query(PaymentIngestionRun).order_by(PaymentIngestionRun.started_at.desc()).limit(10).all()
        if not runs:
            st.info("No ingestion runs yet. Upload a payment CSV to create a processing record.")
        else:
            st.dataframe([{
                "Run ID": r.run_id,
                "Source": r.source_type,
                "Records": r.records_received,
                "Accepted": r.records_accepted,
                "Rejected": r.records_rejected,
                "Duplicated": r.records_duplicated,
                "Status": r.status,
                "Started": str(r.started_at)[:19] if r.started_at else "—",
                "Completed": str(r.completed_at)[:19] if r.completed_at else "—",
            } for r in runs[:10]], hide_index=True, use_container_width=True)

    with tab_dq:
        st.markdown("**Data Quality & Integrity Guardrails:**")
        dq_c1, dq_c2 = st.columns(2)
        with dq_c1:
            render_html("""
            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:1rem;">
                <strong>Mathematical Consistency Rules:</strong>
                <ul style="font-size:0.82rem; color:#334155; margin-top:6px; padding-left:1.2rem;">
                    <li><code>Gross Amount = Net Payout + Fees + Tax</code> (Zero variance tolerance).</li>
                    <li>Timestamp timezone normalization to UTC ISO-8601.</li>
                    <li>Currency standardization (INR default, multi-currency conversion).</li>
                </ul>
            </div>
            """)
        with dq_c2:
            render_html("""
            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:1rem;">
                <strong>Deduplication & Anomaly Defense:</strong>
                <ul style="font-size:0.82rem; color:#334155; margin-top:6px; padding-left:1.2rem;">
                    <li>Natural key deduplication on <code>(merchant_id, payment_id)</code>.</li>
                    <li>Payment signature verification: Server-side HMAC-SHA256 with replay prevention.</li>
                    <li>Out-of-order event handling with deterministic state transitions.</li>
                </ul>
            </div>
            """)


def _render_admin_audit(db):
    """Render Cryptographic SHA-256 Audit Records."""
    st.markdown('<div style="font-size:0.88rem; font-weight:800; color:#0F172A; margin-bottom:0.75rem;">Cryptographic Audit Trail (SHA-256 Verification)</div>', unsafe_allow_html=True)
    audits = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(20).all()
    if audits:
        st.dataframe([{
            "Audit ID": a.audit_id,
            "Operator": a.user_id,
            "Action": a.action,
            "Tool Executed": a.tool_name,
            "Decision Status": a.result_status,
            "Latency": f"{a.latency_ms} ms",
            "Input Hash (SHA-256)": a.input_hash,
            "Timestamp": str(a.timestamp)[:19] if a.timestamp else "—",
        } for a in audits], hide_index=True, use_container_width=True)
    else:
        st.info("No audit entries recorded.")


def render_admin_dashboard(role: str = "ADMIN", page: str = "Overview"):
    """Master Admin Command Dashboard router."""
    # Clearance Header matching platform governance
    render_html("""
    <div style="margin-bottom:1.25rem;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <span class="fintech-badge badge-critical" style="background:#FEE2E2; color:#991B1B; font-weight:700; font-size:0.68rem; padding:3px 8px; border-radius:4px;">
                    WORKSPACE 3 • PLATFORM ADMIN COMMAND
                </span>
                <span class="fintech-badge badge-high" style="background:#EFF6FF; color:#1E40AF; font-weight:700; font-size:0.68rem; padding:3px 8px; border-radius:4px; margin-left:6px;">
                    LEVEL 3 CLEARANCE GRANTED
                </span>
                <h1 style="font-size:1.75rem; font-weight:800; color:#0F172A; margin:6px 0 2px 0; letter-spacing:-0.02em;">
                    Payment Operations & Platform Infrastructure
                </h1>
                <div style="font-size:0.85rem; color:#64748B;">
                    Full platform observability: real-time bank routing health, incident command, and event pipeline telemetry.
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:0.7rem; font-weight:700; color:#64748B; text-transform:uppercase;">Operator Clearance</div>
                <div style="font-size:0.88rem; font-weight:700; color:#0F172A;">Lead Platform Admin (@admin)</div>
            </div>
        </div>
    </div>
    """)

    with SessionLocal() as db:
        if page == "Overview":
            _render_admin_overview(db)
        elif page == "Payments":
            _render_admin_payments(db)
        elif page == "Anomalies":
            _render_admin_anomalies(db)
        elif page == "AI Investigation":
            from frontend.views.ai_investigation_workspace import render_ai_investigation
            render_ai_investigation(role=role)
        elif page == "Data Pipeline":
            _render_admin_data_pipeline(db)
        elif page == "Approvals":
            st.markdown('<div style="font-size:0.88rem; font-weight:800; color:#0F172A; margin-bottom:0.75rem;">Incident Review & Admin Decisions</div>', unsafe_allow_html=True)
            st.caption("Ten illustrative incident scenarios with independent decisions. They are not live incidents; decisions are recorded for review and do not change payment status or live routing.")
            for incident in APPROVAL_INCIDENTS:
                _render_approval_incident(db, incident)
        elif page == "Audit":
            _render_admin_audit(db)
        else:
            _render_admin_overview(db)
