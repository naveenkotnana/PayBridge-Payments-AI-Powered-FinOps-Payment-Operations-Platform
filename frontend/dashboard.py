# -*- coding: utf-8 -*-
# ruff: noqa: E402
"""PayBridge Payments — Fintech Payment Operations & Intelligence Platform UI.

Matches the comprehensive multi-workspace architecture:
- Top Horizontal Quick Navigation Pills (Admin, Merchant, Customer, AI Ops, SBI UPI Demo, Analytics)
- Platform Governance Sidebar (FinOps Command Hub, Multi-Tenant Telemetry, Audit Trail)
- Workspace 3: Payment Operations & Platform Infrastructure (Executive Overview, Payment Monitoring, Bank Switch Telemetry, Incident Command, Merchants & Customers)
- Scoped Merchant & Customer Portals, AI Investigation Workspace, and Interactive SBI UPI Lifecycle Demo.
"""
from pathlib import Path
import sys

# Ensure project root, backend, and frontend are in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
BACKEND_DIR = PROJECT_ROOT / "backend"
APP_DIR = BACKEND_DIR / "app"

for _p in [str(BACKEND_DIR), str(PROJECT_ROOT), str(APP_DIR), str(FRONTEND_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Pre-bind app in sys.modules to prevent circular import or namespace shadowing
try:
    import backend.app as _backend_app
    sys.modules["app"] = _backend_app
except ImportError:
    pass

# Alias dashboard to frontend for seamless imports
import frontend as _frontend_mod
sys.modules["dashboard"] = _frontend_mod

import streamlit as st

# Auto-initialize database schema, demo users, and synthetic data
try:
    from app.core.security import seed_demo_users
    from app.db.base import SessionLocal, init_db
    from app.models import MonthlyRevenue, User
    init_db()
    with SessionLocal() as _bootstrap_db:
        if _bootstrap_db.query(User).count() == 0:
            seed_demo_users(_bootstrap_db)
        if _bootstrap_db.query(MonthlyRevenue).count() == 0:
            from backend.scripts.setup_all import main as _setup_data
            _setup_data()
except Exception:
    pass

from dashboard.styles import RAZORPAY_THEME_CSS

# Workspace Views
from dashboard.views.admin_dashboard import render_admin_dashboard
from dashboard.views.ai_investigation_workspace import render_ai_investigation
from dashboard.views.analytics import render_analytics
from dashboard.views.customer_portal import render_customer_portal
from dashboard.views.merchant_portal import render_merchant_portal
from dashboard.views.overview import render_overview
from dashboard.views.sbi_upi_demo import render_sbi_upi_demo

st.set_page_config(
    page_title="PayBridge Payments — AI Payment Operations Platform",
    page_icon=":zap:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject modern FinTech design styling
st.markdown(RAZORPAY_THEME_CSS, unsafe_allow_html=True)

# ------------------------------------------------------------- Session State Setup
if "token" not in st.session_state:
    st.session_state.token = "demo-admin-token"
    st.session_state.role = "ADMIN"
    st.session_state.username = "admin"
    st.session_state.customer_id = "cust_sw_aarav"
    st.session_state.merchant_id = "mid_swiggy_01"

if "selected_nav" not in st.session_state:
    # Default to Merchants & Customers to match the user's reference screenshot
    st.session_state.selected_nav = "Merchants & Customers"


# ------------------------------------------------------------- 1. TOP NAVBAR
top_c_left, top_c_pills, top_c_right = st.columns([2.5, 4.2, 2.3])

with top_c_left:
    st.markdown("""
    <div style="display:flex; align-items:center; gap:10px; padding:0.2rem 0;">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
            <polygon points="12 2 2 7 12 12 22 7 12 2" fill="#00875A"></polygon>
            <polyline points="2 17 12 22 22 17" stroke="#2F5BFF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"></polyline>
            <polyline points="2 12 12 17 22 12" stroke="#00875A" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"></polyline>
        </svg>
        <div>
            <div style="display:flex; align-items:center; gap:6px;">
                <span style="font-weight:800; font-size:1.15rem; color:#0F172A; letter-spacing:-0.02em;">PayBridge Payments</span>
                <span style="font-size:0.65rem; font-weight:800; background:#ECFDF5; color:#00875A; border:1px solid #A7F3D0; padding:1px 6px; border-radius:4px;">FINTECH</span>
            </div>
            <div style="font-size:0.72rem; color:#64748B;">Razorpay-Inspired AI Platform</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with top_c_pills:
    # Center Quick Workspace Navigation Pills
    p1, p2, p3, p4, p5, p6 = st.columns(6)
    with p1:
        if st.button("🛡️ Admin", key="top_pill_admin", use_container_width=True):
            st.session_state.role = "ADMIN"
            st.session_state.username = "admin"
            st.session_state.selected_nav = "Merchants & Customers"
            st.rerun()
    with p2:
        if st.button("🏪 Merchant", key="top_pill_merchant", use_container_width=True):
            st.session_state.role = "MERCHANT"
            st.session_state.username = "merchant_swiggy"
            st.session_state.merchant_id = "mid_swiggy_01"
            st.session_state.selected_nav = "Merchant Overview"
            st.rerun()
    with p3:
        if st.button("👤 Customer", key="top_pill_customer", use_container_width=True):
            st.session_state.role = "CUSTOMER"
            st.session_state.username = "customer_aarav"
            st.session_state.customer_id = "cust_sw_aarav"
            st.session_state.selected_nav = "Customer Home"
            st.rerun()
    with p4:
        if st.button("🤖 AI Ops", key="top_pill_ai_ops", use_container_width=True):
            st.session_state.selected_nav = "AI Investigation Workspace"
            st.rerun()
    with p5:
        if st.button("▶️ SBI Demo", key="top_pill_sbi_demo", use_container_width=True):
            st.session_state.selected_nav = "SBI UPI Live Demo"
            st.rerun()
    with p6:
        if st.button("📊 Analytics", key="top_pill_analytics", use_container_width=True):
            st.session_state.selected_nav = "Deep Operational Analytics"
            st.rerun()

with top_c_right:
    r1, r2, r3 = st.columns([1.8, 0.5, 1.1])
    with r1:
        persona_map = {
            "admin": "admin",
            "merchant_swiggy": "merchant_swiggy",
            "customer_aarav": "customer_aarav",
            "analyst": "analyst",
            "manager": "manager"
        }
        current_username = st.session_state.get("username", "admin")
        persona_keys = list(persona_map.keys())
        curr_idx = persona_keys.index(current_username) if current_username in persona_keys else 0

        selected_persona = st.selectbox(
            "Active Persona",
            options=persona_keys,
            format_func=lambda k: f"Active Persona: {persona_map[k]}",
            index=curr_idx,
            key="top_persona_dropdown",
            label_visibility="collapsed"
        )
        if selected_persona != current_username:
            st.session_state.username = selected_persona
            if selected_persona == "admin":
                st.session_state.role = "ADMIN"
            elif selected_persona == "merchant_swiggy":
                st.session_state.role = "MERCHANT"
                st.session_state.merchant_id = "mid_swiggy_01"
            elif selected_persona == "customer_aarav":
                st.session_state.role = "CUSTOMER"
                st.session_state.customer_id = "cust_sw_aarav"
            elif selected_persona == "analyst":
                st.session_state.role = "ANALYST"
            elif selected_persona == "manager":
                st.session_state.role = "MANAGER"
            st.rerun()

    with r2:
        if st.button("🔄", key="top_reload_btn", help="Refresh live platform telemetry"):
            st.rerun()

    with r3:
        if st.button("Overview", key="top_ov_btn", type="primary", use_container_width=True):
            st.session_state.selected_nav = "Executive Overview"
            st.rerun()

st.markdown("<div style='height: 0.6rem;'></div>", unsafe_allow_html=True)


# ------------------------------------------------------------- 2. SIDEBAR
with st.sidebar:
    st.markdown("""
    <div style="background:#0F2744; border:1px solid #1E3A5F; border-radius:8px; padding:0.75rem 0.85rem; margin-bottom:1rem;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <span style="font-size:0.62rem; font-weight:800; color:#94A3B8; letter-spacing:0.06em; text-transform:uppercase;">PAYBRIDGE WORKSPACE</span>
            <span style="font-size:0.6rem; font-weight:700; background:#00875A; color:#FFFFFF; padding:1px 6px; border-radius:4px;">ADMIN</span>
        </div>
        <div style="font-size:1.05rem; font-weight:800; color:#FFFFFF; letter-spacing:-0.01em;">FinOps Command Hub</div>
        <div style="font-size:0.7rem; color:#94A3B8; margin-top:2px;">Razorpay-Inspired Multi-Tenant Architecture</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section-header">PLATFORM GOVERNANCE</div>', unsafe_allow_html=True)
    gov_options = [
        "Executive Overview",
        "Payment Monitoring",
        "Bank Switch Telemetry",
        "Incident Command Centre",
        "Merchants & Customers",
        "Data Pipeline & Telemetry",
        "Audit Trail & Approvals",
    ]

    current_nav = st.session_state.get("selected_nav", "Merchants & Customers")
    default_gov = current_nav if current_nav in gov_options else "Merchants & Customers"

    chosen_gov = st.radio(
        "Platform Governance",
        options=gov_options,
        index=gov_options.index(default_gov),
        key="sidebar_governance_radio",
        label_visibility="collapsed"
    )
    if chosen_gov != st.session_state.get("selected_nav") and chosen_gov in gov_options:
        st.session_state.selected_nav = chosen_gov
        st.rerun()

    st.markdown('<div class="sidebar-section-header">INTERACTIVE TOOLS & PREVIEWS</div>', unsafe_allow_html=True)
    c_t1, c_t2 = st.columns(2)
    with c_t1:
        if st.button("🤖 AI Workspace", use_container_width=True, key="side_btn_ai"):
            st.session_state.selected_nav = "AI Investigation Workspace"
            st.rerun()
    with c_t2:
        if st.button("▶️ SBI UPI Demo", use_container_width=True, key="side_btn_sbi"):
            st.session_state.selected_nav = "SBI UPI Live Demo"
            st.rerun()

    st.markdown("""
    <div class="sidebar-user-card" style="margin-top:1.75rem;">
        <div>
            <div class="sidebar-user-name">Lead Platform Administrator</div>
            <div style="font-size:0.7rem; color:#38BDF8; font-weight:600;">@admin</div>
        </div>
        <span style="font-size:0.65rem; font-weight:700; background:#2F5BFF; color:#FFFFFF; padding:2px 6px; border-radius:4px;">ADMIN</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="font-size:0.7rem; color:#64748B; margin-top:1.5rem; text-align:center; border-top:1px solid #1E3A5F; padding-top:0.8rem;">
        Razorpay-Inspired Architecture<br>100% Local Inference · Zero Cloud Egress
    </div>
    """, unsafe_allow_html=True)


# ------------------------------------------------------------- 3. MAIN PAGE ROUTER
current_role = st.session_state.get("role", "ADMIN")
active_view = st.session_state.get("selected_nav", "Merchants & Customers")

# Role portal routing if persona switched
if current_role == "CUSTOMER":
    render_customer_portal(customer_id=st.session_state.get("customer_id", "cust_sw_aarav"))

elif current_role == "MERCHANT":
    render_merchant_portal(merchant_id=st.session_state.get("merchant_id", "mid_swiggy_01"))

elif active_view == "AI Investigation Workspace":
    render_ai_investigation(role=current_role)

elif active_view == "SBI UPI Live Demo":
    render_sbi_upi_demo(role=current_role)

elif active_view == "Deep Operational Analytics":
    render_analytics(role=current_role)

elif active_view == "Executive Overview View":
    render_overview(role=current_role)

else:
    # Render Master Admin Command Dashboard matching user screenshot
    render_admin_dashboard(role=current_role, page=active_view)
