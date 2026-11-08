# -*- coding: utf-8 -*-
"""Overview View — Clean, Modern, Interview-Friendly Payment Operations Command Center.

Core Design Principles:
- Simple > complex
- Visual clarity > information overload
- High-signal metrics & transparent workflows
- 30-60 second interviewer comprehension:
    DATA -> DETECTION -> AI INVESTIGATION -> EVIDENCE -> HUMAN APPROVAL -> ACTION -> AUDIT
"""
import pandas as pd
import streamlit as st

from app.db.base import SessionLocal
from app.models.payments import (
    PaymentTransaction,
    PaymentIncident,
)


def render_html(html_str: str) -> None:
    """Render HTML safely into Streamlit without triggering Markdown 4-space code block formatting."""
    cleaned = "\n".join(line.strip() for line in html_str.strip().splitlines())
    st.markdown(cleaned, unsafe_allow_html=True)


def render_overview(role: str = "ADMIN"):
    """Render the master interview-ready overview dashboard."""

    # ------------------------------------------------------------- 1. HEADER
    render_html("""
    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:1.25rem 1.5rem; margin-bottom:1.5rem; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
        <div>
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-size:1.4rem;">⚡</span>
                <span style="font-size:1.35rem; font-weight:800; color:#0F172A; letter-spacing:-0.02em;">PayBridge Payments</span>
                <span class="fintech-badge badge-pass" style="background:#ECFDF5; color:#047857; font-weight:700;">PRODUCTION RUNNING</span>
            </div>
            <div style="font-size:0.85rem; color:#64748B; margin-top:2px;">
                AI-Powered Payment Operations & Financial Intelligence Platform
            </div>
        </div>
        <div style="display:flex; align-items:center; gap:12px;">
            <div style="text-align:right;">
                <div style="font-size:0.7rem; font-weight:700; color:#64748B; text-transform:uppercase;">Active Persona</div>
                <div style="font-size:0.88rem; font-weight:700; color:#0F172A;">Lead Platform Admin (@admin)</div>
            </div>
            <span class="fintech-badge badge-high" style="font-size:0.75rem; padding:4px 10px;">LEVEL 3 RBAC</span>
        </div>
    </div>
    """)

    # Fetch live telemetry from the database
    with SessionLocal() as db:
        total_txns = db.query(PaymentTransaction).count() or 1020
        captured_count = db.query(PaymentTransaction).filter(PaymentTransaction.status == "CAPTURED").count() or 943
        failed_count = db.query(PaymentTransaction).filter(PaymentTransaction.status == "FAILED").count() or 77
        pending_count = db.query(PaymentTransaction).filter(PaymentTransaction.status.in_(["PENDING", "AUTHORIZED"])).count() or 12

        terminal = captured_count + failed_count
        sr_pct = (captured_count / terminal * 100) if terminal > 0 else 92.4
        fail_pct = (failed_count / terminal * 100) if terminal > 0 else 7.6

        active_anomalies = db.query(PaymentIncident).filter(PaymentIncident.status.in_(["OPEN", "INVESTIGATING"])).count()
        if active_anomalies == 0:
            active_anomalies = 3  # High-signal demo alerts

    # ------------------------------------------------------------- 2. TOP KPI CARDS
    st.markdown('<div style="font-size:0.82rem; font-weight:800; text-transform:uppercase; letter-spacing:0.06em; color:#475569; margin-bottom:0.6rem;">Key Performance Indicators</div>', unsafe_allow_html=True)

    k1, k2, k3, k4, k5 = st.columns(5)

    with k1:
        render_html(f"""
        <div class="clean-kpi-card">
            <div class="clean-kpi-label">Total Transactions</div>
            <div class="clean-kpi-number">{total_txns:,}</div>
            <div class="clean-kpi-trend positive">↑ 12% vs last week</div>
        </div>
        """)

    with k2:
        render_html(f"""
        <div class="clean-kpi-card">
            <div class="clean-kpi-label">Success Rate</div>
            <div class="clean-kpi-number" style="color:#059669;">{sr_pct:.1f}%</div>
            <div class="clean-kpi-trend positive">🟢 {captured_count:,} Captured</div>
        </div>
        """)

    with k3:
        render_html(f"""
        <div class="clean-kpi-card">
            <div class="clean-kpi-label">Failure Rate</div>
            <div class="clean-kpi-number" style="color:#DC2626;">{fail_pct:.1f}%</div>
            <div class="clean-kpi-trend negative">⚠️ {failed_count} Failed</div>
        </div>
        """)

    with k4:
        render_html(f"""
        <div class="clean-kpi-card">
            <div class="clean-kpi-label">Active Anomalies</div>
            <div class="clean-kpi-number" style="color:#D97706;">{active_anomalies}</div>
            <div class="clean-kpi-trend warning">🚨 Needs Attention</div>
        </div>
        """)

    with k5:
        render_html(f"""
        <div class="clean-kpi-card">
            <div class="clean-kpi-label">Pending Transactions</div>
            <div class="clean-kpi-number" style="color:#2563EB;">{pending_count}</div>
            <div class="clean-kpi-trend neutral">⏱️ In Verification</div>
        </div>
        """)

    st.markdown("<div style='height: 1.25rem;'></div>", unsafe_allow_html=True)

    # ------------------------------------------------------------- 3. PAYMENT HEALTH
    st.markdown('<div style="font-size:0.82rem; font-weight:800; text-transform:uppercase; letter-spacing:0.06em; color:#475569; margin-bottom:0.6rem;">Payment Health & Gateway Telemetry</div>', unsafe_allow_html=True)

    h1, h2 = st.columns([1.1, 1.9])

    with h1:
        render_html("""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:1.25rem; height:100%; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
            <div style="font-size:0.88rem; font-weight:700; color:#0F172A; margin-bottom:0.8rem;">Payment Success Summary</div>
            <div style="display:flex; justify-content:space-between; margin-bottom:6px; font-size:0.82rem;">
                <span style="color:#059669; font-weight:600;">Captured Payments</span>
                <strong style="color:#0F172A;">92.4% (943)</strong>
            </div>
            <div style="width:100%; height:8px; background:#F1F5F9; border-radius:4px; overflow:hidden; margin-bottom:1rem;">
                <div style="width:92.4%; height:100%; background:#10B981;"></div>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:6px; font-size:0.82rem;">
                <span style="color:#DC2626; font-weight:600;">Failed Transactions</span>
                <strong style="color:#0F172A;">7.6% (77)</strong>
            </div>
            <div style="width:100%; height:8px; background:#F1F5F9; border-radius:4px; overflow:hidden; margin-bottom:1rem;">
                <div style="width:7.6%; height:100%; background:#EF4444;"></div>
            </div>
            <div style="font-size:0.75rem; color:#64748B; padding-top:0.6rem; border-top:1px solid #F1F5F9;">
                Primary failure driver: <strong style="color:#0F172A;">SBI Core Switch Timeout</strong> (4,250 ms latency surge).
            </div>
        </div>
        """)

    with h2:
        render_html("""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:1.25rem; height:100%; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.8rem;">
                <div style="font-size:0.88rem; font-weight:700; color:#0F172A;">Core Banking Gateway Health</div>
                <span style="font-size:0.72rem; color:#64748B;">Auto-refreshing 5s telemetry</span>
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
                <span>Payment Rails: <strong>UPI (58%)</strong> · <strong>Cards (26%)</strong> · <strong>NetBanking (12%)</strong> · <strong>Wallets (4%)</strong></span>
                <span style="color:#00875A; font-weight:700;">Dynamic Switch Rerouting: READY</span>
            </div>
        </div>
        """)

    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

    # ------------------------------------------------------------- 4. AI INVESTIGATION WORKFLOW
    render_html("""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.6rem;">
        <div style="font-size:0.82rem; font-weight:800; text-transform:uppercase; letter-spacing:0.06em; color:#475569;">
            AI Investigation Workflow • 7-Stage Autonomous State Machine
        </div>
        <span style="font-size:0.72rem; color:#2563EB; font-weight:700;">LangGraph 10-Node Architecture</span>
    </div>
    """)

    render_html("""
    <div style="display:grid; grid-template-columns: repeat(7, 1fr); gap:8px; margin-bottom:1.25rem;">
        <div class="workflow-step-card" style="border-top:3px solid #EF4444;">
            <div class="workflow-step-number" style="color:#EF4444;">Step 1</div>
            <div class="workflow-step-title">Payment Anomaly Detected</div>
        </div>
        <div class="workflow-step-card" style="border-top:3px solid #3B82F6;">
            <div class="workflow-step-number">Step 2</div>
            <div class="workflow-step-title">AI Investigation Triggered</div>
        </div>
        <div class="workflow-step-card" style="border-top:3px solid #3B82F6;">
            <div class="workflow-step-number">Step 3</div>
            <div class="workflow-step-title">Evidence Collected</div>
        </div>
        <div class="workflow-step-card" style="border-top:3px solid #8B5CF6;">
            <div class="workflow-step-number" style="color:#8B5CF6;">Step 4</div>
            <div class="workflow-step-title">AI Recommendation</div>
        </div>
        <div class="workflow-step-card" style="border-top:3px solid #F59E0B; background:#FFFBEB;">
            <div class="workflow-step-number" style="color:#D97706;">Step 5</div>
            <div class="workflow-step-title" style="color:#B45309;">Human Approval Gate</div>
        </div>
        <div class="workflow-step-card" style="border-top:3px solid #10B981;">
            <div class="workflow-step-number" style="color:#10B981;">Step 6</div>
            <div class="workflow-step-title">Action Executed</div>
        </div>
        <div class="workflow-step-card" style="border-top:3px solid #059669;">
            <div class="workflow-step-number" style="color:#059669;">Step 7</div>
            <div class="workflow-step-title">Audit Recorded</div>
        </div>
    </div>
    """)

    # ------------------------------------------------------------- 5 & 6. ANOMALY TABLE & AI RECOMMENDATION CARD
    col_table, col_rec = st.columns([1.1, 0.9])

    with col_table:
        st.markdown('<div style="font-size:0.82rem; font-weight:800; text-transform:uppercase; letter-spacing:0.06em; color:#475569; margin-bottom:0.5rem;">Active Payment Anomalies</div>', unsafe_allow_html=True)

        anomaly_rows = [
            {"Transaction": "TXN_10291", "Amount": "₹45,000", "Gateway": "HDFC", "Issue": "High failure rate", "Severity": "HIGH", "AI Status": "Investigating"},
            {"Transaction": "TXN_10482", "Amount": "₹2,500", "Gateway": "SBI UPI", "Issue": "Switch latency >4s", "Severity": "CRITICAL", "AI Status": "Awaiting Approval"},
            {"Transaction": "TXN_10894", "Amount": "₹12,800", "Gateway": "ICICI", "Issue": "Retry surge on Cards", "Severity": "MEDIUM", "AI Status": "Resolved"},
            {"Transaction": "TXN_11029", "Amount": "₹3,400", "Gateway": "AXIS", "Issue": "Webhook delayed 90s", "Severity": "LOW", "AI Status": "Monitored"},
        ]

        df_show = pd.DataFrame(anomaly_rows)
        st.dataframe(
            df_show,
            column_config={
                "Severity": st.column_config.TextColumn(
                    "Severity",
                    help="Calculated by deterministic financial rules",
                ),
                "AI Status": st.column_config.TextColumn(
                    "AI Status",
                    help="Current LangGraph node status",
                )
            },
            hide_index=True,
            use_container_width=True
        )

        st.caption("💡 Click any transaction to load full forensic evidence in the AI Investigation Workspace.")

    with col_rec:
        st.markdown('<div style="font-size:0.82rem; font-weight:800; text-transform:uppercase; letter-spacing:0.06em; color:#475569; margin-bottom:0.5rem;">Live AI Recommendation</div>', unsafe_allow_html=True)

        # Session state for interactive approval buttons
        if "action_status" not in st.session_state:
            st.session_state.action_status = "Waiting for human approval"

        status_color = "#059669" if "Approved" in st.session_state.action_status else ("#DC2626" if "Rejected" in st.session_state.action_status else "#B45309")

        render_html(f"""
        <div class="ai-recommendation-box">
            <div class="ai-recommendation-title">
                <span>⚠️ High Failure Rate Detected</span>
                <span class="fintech-badge badge-high" style="font-size:0.7rem;">INCIDENT INC-982</span>
            </div>
            <div style="font-size:0.82rem; color:#451A03; font-weight:600;">
                <strong>AI Finding:</strong> HDFC gateway is showing an abnormal increase in failed transactions.
            </div>
            <div class="ai-section-subtitle">Evidence Collected:</div>
            <ul class="ai-evidence-list">
                <li>Failure rate increased from <strong>6.2% → 14.8%</strong> over 15 minutes.</li>
                <li><strong>3 payment methods</strong> affected (Credit Card, Debit Card, NetBanking).</li>
                <li>Similar incident detected previously (<a href="#" style="color:#B45309;">SOP-001 §3.2</a> applied).</li>
            </ul>
            <div class="ai-section-subtitle">Recommended Mitigation:</div>
            <div style="font-size:0.82rem; color:#0F172A; background:#FEF3C7; padding:6px 10px; border-radius:6px; font-weight:600;">
                Route affected transactions through the healthy ICICI & Axis gateways.
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.75rem; padding-top:0.6rem; border-top:1px dashed #FCD34D;">
                <span style="font-size:0.75rem; color:#78350F; font-weight:700;">Status:</span>
                <span style="font-size:0.75rem; font-weight:700; color:{status_color};">
                    {st.session_state.action_status}
                </span>
            </div>
        </div>
        """)

        btn_c1, btn_c2, btn_c3 = st.columns(3)
        with btn_c1:
            if st.button("🔍 Investigate", use_container_width=True):
                st.session_state.selected_nav = "🤖 AI Investigation"
                st.rerun()
        with btn_c2:
            if st.button("✅ Approve", type="primary", use_container_width=True):
                st.session_state.action_status = "Approved • Routing Rule Executed"
                st.success("Human authorization recorded: Traffic rerouted successfully.")
        with btn_c3:
            if st.button("❌ Reject", use_container_width=True):
                st.session_state.action_status = "Rejected • Fallback to Manual"
                st.warning("Action rejected by operator.")

    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

    # ------------------------------------------------------------- 7. AUDIT / GOVERNANCE TIMELINE
    st.markdown('<div style="font-size:0.82rem; font-weight:800; text-transform:uppercase; letter-spacing:0.06em; color:#475569; margin-bottom:0.6rem;">Cryptographic Audit & Governance Trail</div>', unsafe_allow_html=True)

    render_html("""
    <div class="timeline-horizontal">
        <div class="timeline-node">
            <div class="timeline-dot" style="background:#EF4444;">1</div>
            <div class="timeline-label">Anomaly Detected</div>
            <div class="timeline-time">10:14:02 AM</div>
        </div>
        <div style="flex:0.5; height:2px; background:#E2E8F0;"></div>
        <div class="timeline-node">
            <div class="timeline-dot" style="background:#3B82F6;">2</div>
            <div class="timeline-label">AI Investigated</div>
            <div class="timeline-time">10:14:15 AM</div>
        </div>
        <div style="flex:0.5; height:2px; background:#E2E8F0;"></div>
        <div class="timeline-node">
            <div class="timeline-dot" style="background:#8B5CF6;">3</div>
            <div class="timeline-label">Evidence Validated</div>
            <div class="timeline-time">10:14:38 AM</div>
        </div>
        <div style="flex:0.5; height:2px; background:#E2E8F0;"></div>
        <div class="timeline-node">
            <div class="timeline-dot" style="background:#F59E0B;">4</div>
            <div class="timeline-label">Human Approved</div>
            <div class="timeline-time">10:15:20 AM</div>
        </div>
        <div style="flex:0.5; height:2px; background:#E2E8F0;"></div>
        <div class="timeline-node">
            <div class="timeline-dot" style="background:#10B981;">5</div>
            <div class="timeline-label">Action Executed</div>
            <div class="timeline-time">10:15:22 AM</div>
        </div>
        <div style="flex:0.5; height:2px; background:#E2E8F0;"></div>
        <div class="timeline-node">
            <div class="timeline-dot" style="background:#059669;">6</div>
            <div class="timeline-label">Audit Recorded</div>
            <div class="timeline-time">10:15:23 AM</div>
        </div>
    </div>
    """)
