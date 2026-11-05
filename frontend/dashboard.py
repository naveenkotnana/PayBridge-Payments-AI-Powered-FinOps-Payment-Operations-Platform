# -*- coding: utf-8 -*-
# ruff: noqa: E402
"""PayBridge Payments — Modern FinTech Payment Operations & Intelligence Platform UI.

Core Design Philosophy:
- Simple > complex
- Visual clarity > information overload
- High-signal metrics & transparent workflows
- 30-60 second interviewer comprehension:
    DATA -> DETECTION -> AI INVESTIGATION -> EVIDENCE -> HUMAN APPROVAL -> ACTION -> AUDIT
"""
import sys
from pathlib import Path

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
    from app.db.base import init_db, SessionLocal
    from app.core.security import seed_demo_users
    from app.models import User, MonthlyRevenue
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

# Clean View Renderers
from dashboard.views.overview import render_overview
from dashboard.views.anomalies import render_anomalies
from dashboard.views.ai_investigation_workspace import render_ai_investigation
from dashboard.views.admin_dashboard import render_admin_dashboard
from dashboard.views.merchant_portal import render_merchant_portal
from dashboard.views.customer_portal import render_customer_portal
from dashboard.views.sbi_upi_demo import render_sbi_upi_demo

st.set_page_config(
    page_title="PayBridge Payments — AI Payment Operations Platform",
    page_icon=":zap:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject modern FinTech design styling
st.markdown(RAZORPAY_THEME_CSS, unsafe_allow_html=True)

# ------------------------------------------------------------- Session State & Default Auth
# Seamless entry: Default to Lead Administrator so interviewer sees the full system immediately
if "token" not in st.session_state:
    st.session_state.token = "demo-admin-token"
    st.session_state.role = "ADMIN"
    st.session_state.username = "admin"
    st.session_state.customer_id = "cust_sw_aarav"
    st.session_state.merchant_id = "mid_swiggy_01"

if "selected_nav" not in st.session_state:
    st.session_state.selected_nav = "📊 Overview"

# ------------------------------------------------------------- Sidebar Navigation
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand-box">
        <div class="sidebar-brand-title">
            <span style="font-size:1.3rem;">⚡</span>
            <span>PAYBRIDGE</span>
            <span class="sidebar-brand-badge" style="background:#00875A;">PAYMENTS</span>
        </div>
        <div class="sidebar-brand-sub">AI-Powered Payment Operations</div>
    </div>
    """, unsafe_allow_html=True)

    # 1. Minimal 7-Item Navigation
    st.markdown('<div class="sidebar-section-header">PLATFORM NAVIGATION</div>', unsafe_allow_html=True)
    nav_options = [
        "📊 Overview",
        "💳 Payments",
        "⚠️ Anomalies",
        "🤖 AI Investigation",
        "👥 Merchants & Customers",
        "⚙️ Data Pipeline",
        "🛡️ Audit & Approvals",
    ]

    # Ensure selected_nav is valid
    if st.session_state.selected_nav not in nav_options:
        st.session_state.selected_nav = "📊 Overview"

    nav_index = nav_options.index(st.session_state.selected_nav)
    chosen_nav = st.radio(
        "Navigation",
        options=nav_options,
        index=nav_index,
        key="main_navigation_radio",
        label_visibility="collapsed"
    )
    if chosen_nav != st.session_state.selected_nav:
        st.session_state.selected_nav = chosen_nav
        st.rerun()

    st.markdown("---")

    # 2. Quick Persona Switcher for Interviewers
    st.markdown('<div class="sidebar-section-header">SWITCH PERSONA</div>', unsafe_allow_html=True)
    persona_map = {
        "admin": "Lead Administrator (@admin)",
        "merchant_swiggy": "Merchant: Swiggy (@merchant_swiggy)",
        "customer_aarav": "Customer: Aarav Sharma (@customer_aarav)",
        "analyst": "FinOps Analyst (@analyst)",
        "manager": "Operations Manager (@manager)"
    }
    current_username = st.session_state.get("username", "admin")
    persona_keys = list(persona_map.keys())
    curr_idx = persona_keys.index(current_username) if current_username in persona_keys else 0

    selected_persona = st.selectbox(
        "Active Persona",
        options=persona_keys,
        format_func=lambda k: persona_map[k],
        index=curr_idx,
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

    # 3. Quick Interactive Demo Button
    st.markdown("<div style='height: 0.8rem;'></div>", unsafe_allow_html=True)
    if st.button("🎬 Run SBI UPI Incident Demo", use_container_width=True):
        st.session_state.selected_nav = "🎬 SBI UPI Demo"
        st.rerun()

    # Footer note
    st.markdown("""
    <div style="font-size:0.7rem; color:#64748B; margin-top:2rem; text-align:center; border-top:1px solid #1E3A5F; padding-top:0.8rem;">
        Razorpay-Inspired Architecture<br>100% Local Inference · Zero Cloud Egress
    </div>
    """, unsafe_allow_html=True)


# ------------------------------------------------------------- Page Router
current_role = st.session_state.get("role", "ADMIN")
nav_selection = st.session_state.selected_nav

# Role overrides if switched to Merchant or Customer explicitly
if current_role == "CUSTOMER":
    render_customer_portal(customer_id=st.session_state.get("customer_id", "cust_sw_aarav"))

elif current_role == "MERCHANT":
    render_merchant_portal(merchant_id=st.session_state.get("merchant_id", "mid_swiggy_01"))

elif nav_selection == "🎬 SBI UPI Demo":
    render_sbi_upi_demo(role=current_role)

elif nav_selection == "📊 Overview":
    render_overview(role=current_role)

elif nav_selection == "💳 Payments":
    render_admin_dashboard(role=current_role, page="Payment Monitoring")

elif nav_selection == "⚠️ Anomalies":
    render_anomalies(role=current_role)

elif nav_selection == "🤖 AI Investigation":
    render_ai_investigation(role=current_role)

elif nav_selection == "👥 Merchants & Customers":
    render_admin_dashboard(role=current_role, page="Merchants & Customers")

elif nav_selection == "⚙️ Data Pipeline":
    render_admin_dashboard(role=current_role, page="Data Pipeline")

elif nav_selection == "🛡️ Audit & Approvals":
    render_admin_dashboard(role=current_role, page="Audit & Approvals")

else:
    render_overview(role=current_role)
