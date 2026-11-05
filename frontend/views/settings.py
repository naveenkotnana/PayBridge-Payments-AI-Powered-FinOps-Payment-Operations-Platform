# -*- coding: utf-8 -*-
"""Settings & Admin Governance View — FinOps Platform Administration."""
import pandas as pd
import streamlit as st

from dashboard.components import api_call, render_kpi_row, render_top_header


def render_settings(role: str):
    """Render enterprise admin control panel, RBAC governance, and service telemetry."""
    render_top_header(
        title="Admin Control & System Governance",
        subtitle="RBAC clearance controls, security policies, API credentials, and infrastructure telemetry",
        role=role
    )

    t_gov, t_infra, t_api, t_pipe = st.tabs([
        "🛡️ Access & Persona Governance",
        "⚡ Infrastructure Telemetry",
        "🔑 FinOps API & Security Credentials",
        "⚙️ Pipeline & Model Controls"
    ])

    # ------------------------------------------------ Tab 1: Access Governance
    with t_gov:
        st.markdown("""
        <div style="background:#FFFFFF; border:1px solid #E6EAF0; border-radius:10px; padding:1.25rem; margin-bottom:1.5rem;">
            <h3 style="font-size:1rem; font-weight:700; color:#0F172A; margin:0 0 0.25rem 0;">Role & Clearance Persona Switcher</h3>
            <div style="font-size:0.8rem; color:#64748B; margin-bottom:1rem;">Verified role-based view controls across platform actors:</div>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            is_active = (role == "ADMIN")
            st.markdown(f"""
            <div style="background:{'#F0FDF4' if is_active else '#F8FAFC'}; border:1px solid {'#86EFAC' if is_active else '#E2E8F0'}; border-radius:8px; padding:1rem; margin-bottom:0.75rem;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
                    <strong style="color:#0F172A; font-size:0.9rem;">🛡️ Admin</strong>
                    <span class="fintech-badge {'badge-pass' if is_active else 'badge-critical'}">{'ACTIVE' if is_active else 'COMMAND'}</span>
                </div>
                <div style="font-size:0.75rem; color:#64748B; line-height:1.4; min-height:48px;">
                    FinOps operations, AI investigation, incident mitigation approval, data lineage, and audit logs.
                </div>
            </div>
            """, unsafe_allow_html=True)
            if not is_active:
                if st.button("Switch to Admin", key="btn_sw_admin", use_container_width=True):
                    st.session_state.role = "ADMIN"
                    st.session_state.username = "admin"
                    st.session_state.selected_nav = "Overview"
                    st.rerun()
            else:
                st.markdown("<div style='text-align:center; font-size:0.8rem; font-weight:700; color:#16A34A; padding:6px;'>Current Active Role</div>", unsafe_allow_html=True)

        with c2:
            is_active = (role == "MERCHANT")
            st.markdown(f"""
            <div style="background:{'#F0FDF4' if is_active else '#F8FAFC'}; border:1px solid {'#86EFAC' if is_active else '#E2E8F0'}; border-radius:8px; padding:1rem; margin-bottom:0.75rem;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
                    <strong style="color:#0F172A; font-size:0.9rem;">🏪 Merchant (Rameshwaram Cafe)</strong>
                    <span class="fintech-badge {'badge-pass' if is_active else 'badge-high'}">{'ACTIVE' if is_active else 'STORE'}</span>
                </div>
                <div style="font-size:0.75rem; color:#64748B; line-height:1.4; min-height:48px;">
                    Real-time order statuses, revenue settlement metrics, and store-level payment health.
                </div>
            </div>
            """, unsafe_allow_html=True)
            if not is_active:
                if st.button("Switch to Merchant", key="btn_sw_merchant", use_container_width=True, type="primary"):
                    st.session_state.role = "MERCHANT"
                    st.session_state.username = "merchant"
                    st.session_state.merchant_id = "mid_rameshwaram_01"
                    st.session_state.selected_nav = "Overview"
                    st.rerun()
            else:
                st.markdown("<div style='text-align:center; font-size:0.8rem; font-weight:700; color:#16A34A; padding:6px;'>Current Active Role</div>", unsafe_allow_html=True)

        with c3:
            is_active = (role == "CUSTOMER")
            st.markdown(f"""
            <div style="background:{'#F0FDF4' if is_active else '#F8FAFC'}; border:1px solid {'#86EFAC' if is_active else '#E2E8F0'}; border-radius:8px; padding:1rem; margin-bottom:0.75rem;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
                    <strong style="color:#0F172A; font-size:0.9rem;">👤 Customer (Aarav Sharma)</strong>
                    <span class="fintech-badge {'badge-pass' if is_active else 'badge-low'}">{'ACTIVE' if is_active else 'BUYER'}</span>
                </div>
                <div style="font-size:0.75rem; color:#64748B; line-height:1.4; min-height:48px;">
                    Razorpay Checkout order initiation, transparent transaction status, and double-debit refund tracking.
                </div>
            </div>
            """, unsafe_allow_html=True)
            if not is_active:
                if st.button("Switch to Customer", key="btn_sw_customer", use_container_width=True):
                    st.session_state.role = "CUSTOMER"
                    st.session_state.username = "customer"
                    st.session_state.customer_id = "cust_aarav_01"
                    st.session_state.selected_nav = "Orders"
                    st.rerun()
            else:
                st.markdown("<div style='text-align:center; font-size:0.8rem; font-weight:700; color:#16A34A; padding:6px;'>Current Active Role</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        # RBAC Clearance Matrix
        st.markdown("""
        <div style="background:#FFFFFF; border:1px solid #E6EAF0; border-radius:10px; padding:1.25rem; margin-bottom:1.5rem;">
            <h3 style="font-size:1rem; font-weight:700; color:#0F172A; margin:0 0 0.25rem 0;">Hierarchical RBAC Authorization Matrix</h3>
            <div style="font-size:0.8rem; color:#64748B; margin-bottom:1rem;">Verified scope enforcement across platform actors:</div>
        """, unsafe_allow_html=True)
        rbac_matrix = [
            {"Domain / Scope": "Overview & Revenue Analytics", "Customer": "DENIED (403)", "Merchant": "STORE GMV ONLY", "Admin": "FULL REVENUE HUB"},
            {"Domain / Scope": "Order Creation & Checkout", "Customer": "EXECUTE (₹280)", "Merchant": "RECEIVE ORDERS", "Admin": "MONITOR ONLY"},
            {"Domain / Scope": "AI Investigation & RAG Agent", "Customer": "DENIED (403)", "Merchant": "SUMMARY ONLY", "Admin": "FULL COPILOT"},
            {"Domain / Scope": "Exception Remediation Approvals", "Customer": "DENIED (403)", "Merchant": "DENIED (403)", "Admin": "APPROVE / REJECT"},
            {"Domain / Scope": "Cryptographic Audit Ledger", "Customer": "DENIED (403)", "Merchant": "DENIED (403)", "Admin": "VERIFY INTEGRITY"},
            {"Domain / Scope": "Telemetry Data Ingestion / 50K CSV", "Customer": "DENIED (403)", "Merchant": "DENIED (403)", "Admin": "TRIGGER & LINEAGE"}
        ]
        st.dataframe(pd.DataFrame(rbac_matrix), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ------------------------------------------------ Tab 2: Infrastructure Telemetry
    with t_infra:
        h_data, _ = api_call("GET", "/health")
        h = h_data or {}
        models = h.get("ollama_models", [])

        render_kpi_row([
            {
                "label": "API Service",
                "value": h.get("status", "OK").upper(),
                "trend_text": "FastAPI",
                "trend_direction": "up",
                "subtext": "REST endpoints active"
            },
            {
                "label": "Database Engine",
                "value": h.get("database", "UP").upper(),
                "trend_text": "SQLite",
                "trend_direction": "up",
                "subtext": "Postgres-ready schema"
            },
            {
                "label": "Local LLM Inference",
                "value": "OLLAMA" if models else "FALLBACK",
                "trend_text": models[0] if models else "Rule Engine",
                "trend_direction": "up" if models else "neutral",
                "subtext": "Zero API egress cost"
            },
            {
                "label": "RAG Knowledge Index",
                "value": f"{h.get('rag_chunks', 38)}\u00A0Chunks",
                "trend_text": "TF-IDF",
                "trend_direction": "up",
                "subtext": "100% local retrieval"
            }
        ])

        st.markdown("""
        <div style="background:#FFFFFF; border:1px solid #E6EAF0; border-radius:10px; padding:1.25rem; margin-top:1.25rem;">
            <h3 style='font-size:1rem; font-weight:700; color:#0F172A; margin:0 0 0.5rem 0;'>Live System Runtime Telemetry</h3>
        """, unsafe_allow_html=True)
        m, _ = api_call("GET", "/metrics")
        if m:
            st.json(m)
        st.markdown("</div>", unsafe_allow_html=True)

    # ------------------------------------------------ Tab 3: FinOps API & Security Credentials
    with t_api:
        st.markdown("""
        <div style="background:#FFFFFF; border:1px solid #E6EAF0; border-radius:10px; padding:1.25rem; margin-bottom:1.5rem;">
            <h3 style="font-size:1rem; font-weight:700; color:#0F172A; margin:0 0 0.25rem 0;">Razorpay Standard Web Checkout API Credentials</h3>
            <div style="font-size:0.8rem; color:#64748B; margin-bottom:1rem;">API key pair and server-side HMAC-SHA256 signature verification configuration:</div>
        """, unsafe_allow_html=True)

        k1, k2 = st.columns(2)
        with k1:
            st.text_input("Razorpay Key ID", value="rzp_test_••••••••••••", disabled=True, help="Exposed safely to frontend checkout.js")
            st.text_input("Order Creation Endpoint", value="POST /api/create-order", disabled=True)
        with k2:
            st.text_input("Razorpay Key Secret", value="••••••••••••••••••••", type="password", disabled=True, help="Kept strictly on server in .env")
            st.text_input("Payment Verification Endpoint", value="POST /api/verify-payment", disabled=True)

        st.markdown("""
            <div style="font-size:0.78rem; color:#64748B; margin-top:0.5rem;">
                🔐 Server-side signature verified using <code>hmac.compare_digest(HMAC-SHA256(order_id + '|' + payment_id, secret))</code>. No webhooks required.
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ------------------------------------------------ Tab 4: Pipeline & Model Controls
    with t_pipe:
        st.markdown("""
        <div style="background:#FFFFFF; border:1px solid #E6EAF0; border-radius:10px; padding:1.25rem; margin-bottom:1.5rem;">
            <h3 style="font-size:1rem; font-weight:700; color:#0F172A; margin:0 0 0.25rem 0;">On-Demand Automation Pipeline Controls</h3>
            <div style="font-size:0.8rem; color:#64748B; margin-bottom:1rem;">Trigger manual recalculations, model retraining, or schema re-verification:</div>
        """, unsafe_allow_html=True)

        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("Trigger Revenue Recalculation", use_container_width=True, type="primary"):
                from backend.app.services.revenue import calculate_all_months
                calculate_all_months(verbose=False)
                st.success("Revenue aggregation executed successfully!")
        with b2:
            if st.button("Trigger ML Anomaly Detection", use_container_width=True):
                from backend.app.services.anomaly import detect_all_anomalies
                detect_all_anomalies(verbose=False)
                st.success("IsolationForest ML models evaluated!")
        with b3:
            if st.button("Reload Knowledge Base Index", use_container_width=True):
                from backend.app.rag.retriever import get_retriever
                get_retriever()
                st.success("RAG knowledge chunks synced!")

        st.markdown("</div>", unsafe_allow_html=True)
