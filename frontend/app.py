# -*- coding: utf-8 -*-
# ruff: noqa: E402
"""Razorpay-Inspired AI Payments – Role-Based Fintech Platform UI.

Independent Role-Based Workspaces:
1. Customer Portal (/customer) — Scoped buyer transactions, verification timeline & notifications
2. Merchant Portal (/merchant) — Scoped business GMV, fulfillment hold advisories & settlements
3. Admin Dashboard (/admin) — Executive overview, bank switch telemetry, incident command & audit
4. AI Investigation Workspace (/ai-investigation) — Evidence-based root-cause analysis & human approval gate
+ Interactive SBI UPI Live Lifecycle Demonstration.

Synthetic portfolio project. Local Ollama LLM. Zero paid external APIs.
"""
import sys
from pathlib import Path

# Ensure project root, backend, and frontend are in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
BACKEND_DIR = PROJECT_ROOT / "backend"
for _p in [str(PROJECT_ROOT), str(BACKEND_DIR), str(FRONTEND_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Alias dashboard to frontend for seamless imports
import frontend as _frontend_mod
sys.modules.setdefault("dashboard", _frontend_mod)

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

from dashboard.components import api_call, get_image_base64
from dashboard.styles import RAZORPAY_THEME_CSS

# Workspace Views
from dashboard.views.customer_portal import render_customer_portal
from dashboard.views.merchant_portal import render_merchant_portal
from dashboard.views.admin_dashboard import render_admin_dashboard
from dashboard.views.ai_investigation_workspace import render_ai_investigation
from dashboard.views.sbi_upi_demo import render_sbi_upi_demo

# Deep-dive Operational Views
from dashboard.views.analytics import render_analytics
from dashboard.views.anomalies import render_anomalies
from dashboard.views.approvals import render_approvals
from dashboard.views.audit import render_audit
from dashboard.views.data_quality import render_data_quality
from dashboard.views.exceptions import render_exceptions
from dashboard.views.overview import render_overview
from dashboard.views.revenue import render_revenue
from dashboard.views.settings import render_settings
from dashboard.views.transactions import render_transactions

st.set_page_config(
    page_title="Razorpay-Inspired AI Payments — Role-Based Fintech Platform",
    page_icon=":zap:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject Razorpay-inspired visual styling
st.markdown(RAZORPAY_THEME_CSS, unsafe_allow_html=True)


# ------------------------------------------------------------- Authentication
def login_view():
    """Fintech-styled authentication gateway supporting 4 role portals."""
    bg_uri = get_image_base64(PROJECT_ROOT / "dashboard" / "login_bg.jpg")
    admin_banner_uri = get_image_base64(PROJECT_ROOT / "dashboard" / "admin_banner.jpg")

    if bg_uri:
        st.markdown(f"""
        <style>
        .stApp {{
            background-image: url('{bg_uri}') !important;
            background-size: cover !important;
            background-position: center center !important;
            background-repeat: no-repeat !important;
            background-attachment: fixed !important;
        }}
        [data-testid="stSidebar"] {{
            display: none !important;
        }}
        /* Centered floating glassmorphism card */
        div[data-testid="column"]:nth-child(2) > div {{
            background: rgba(255, 255, 255, 0.94) !important;
            backdrop-filter: blur(24px) !important;
            -webkit-backdrop-filter: blur(24px) !important;
            border: 1px solid rgba(255, 255, 255, 0.95) !important;
            border-radius: 28px !important;
            padding: 2.25rem 2.25rem 1.75rem 2.25rem !important;
            box-shadow: 0 20px 60px rgba(15, 23, 42, 0.09), 0 2px 8px rgba(0, 0, 0, 0.02) !important;
        }}
        </style>
        """, unsafe_allow_html=True)

    # Top-left brand mark
    st.markdown("""
    <div class="login-brand-topbar">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#00875A" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
            <polyline points="2 17 12 22 22 17"></polyline>
            <polyline points="2 12 12 17 22 12"></polyline>
        </svg>
        <span style="font-weight:800; font-size:1.15rem; color:#0A142F; letter-spacing:-0.02em;">Razorpay-Inspired AI Payments</span>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1.0, 2.0, 1.0])
    with col_c:
        st.markdown("""
        <div style="text-align:center;">
            <div class="login-avatar-pill">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#0F172A" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path>
                    <polyline points="10 17 15 12 10 7"></polyline>
                    <line x1="15" y1="12" x2="3" y2="12"></line>
                </svg>
            </div>
            <div class="login-title-text">Role-Based Fintech Authentication</div>
            <div class="login-sub-text">Select your authorized workspace portal to access your scoped payments environment.</div>
        </div>
        """, unsafe_allow_html=True)

        tab_ad, tab_m, tab_cust, tab_op = st.tabs([
            "🛡️ Admin Portal",
            "🏪 Merchant Portal",
            "👤 Customer Portal",
            "🤖 AI Operations",
        ])

        # 1. ADMIN PORTAL
        with tab_ad:
            if admin_banner_uri:
                st.markdown(f"""
                <div class="login-admin-banner">
                    <img src="{admin_banner_uri}" style="width:100%; max-height:120px; object-fit:cover; display:block;" />
                </div>
                """, unsafe_allow_html=True)
            st.markdown("""
            <div style="padding:0.2rem 0 0.8rem 0; text-align:left;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <strong style="color:#0F172A; font-size:0.92rem;">Platform Administrator</strong>
                    <span class="fintech-badge badge-critical">LEVEL 3 CLEARANCE</span>
                </div>
                <div style="font-size:0.78rem; color:#64748B; line-height:1.4;">
                    Full platform governance, bank routing switch, and incident command.
                </div>
            </div>
            """, unsafe_allow_html=True)
            with st.form("form_admin"):
                u_ad = st.text_input("Username", value="admin", key="u_ad")
                p_ad = st.text_input("Password", value="admin123", type="password", key="p_ad")
                sub_ad = st.form_submit_button("Sign In as Platform Admin", use_container_width=True)
                if sub_ad:
                    res, err = api_call("POST", "/auth/login", json={"username": u_ad, "password": p_ad})
                    if err:
                        st.error(err)
                    elif res:
                        st.session_state.clear()
                        st.session_state.update(
                            token=res["access_token"],
                            role=res["role"],
                            user_id=res["user_id"],
                            username=u_ad,
                        )
                        st.rerun()

        # 2. MERCHANT PORTAL
        with tab_m:
            st.markdown("""
            <div style="padding:0.4rem 0 0.8rem 0; text-align:left;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <strong style="color:#0F172A; font-size:0.92rem;">Merchant Business Portal</strong>
                    <span class="fintech-badge badge-medium">MERCHANT SCOPED</span>
                </div>
                <div style="font-size:0.78rem; color:#64748B; line-height:1.4;">
                    Incoming orders, fulfillment advisories, bank SR slicing, and settlement payouts.
                </div>
            </div>
            """, unsafe_allow_html=True)
            with st.form("form_merchant"):
                u_m = st.text_input("Username", value="merchant_swiggy", key="u_m")
                p_m = st.text_input("Password", value="merchant123", type="password", key="p_m")
                sub_m = st.form_submit_button("Sign In to Merchant Portal (Swiggy)", use_container_width=True)
                if sub_m:
                    res, err = api_call("POST", "/auth/login", json={"username": u_m, "password": p_m})
                    if err:
                        st.error(err)
                    elif res:
                        st.session_state.clear()
                        st.session_state.update(
                            token=res["access_token"],
                            role="MERCHANT",
                            user_id=res["user_id"],
                            username=u_m,
                            merchant_id="mid_swiggy_01",
                        )
                        st.rerun()

        # 3. CUSTOMER PORTAL
        with tab_cust:
            st.markdown("""
            <div style="padding:0.4rem 0 0.8rem 0; text-align:left;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <strong style="color:#0F172A; font-size:0.92rem;">Customer Portal (Aarav Sharma)</strong>
                    <span class="fintech-badge badge-low">BUYER ACCOUNT</span>
                </div>
                <div style="font-size:0.78rem; color:#64748B; line-height:1.4;">
                    Personal transaction ledger, bank verification timelines, and order notifications.
                </div>
            </div>
            """, unsafe_allow_html=True)
            with st.form("form_customer"):
                u_c = st.text_input("Username", value="customer_aarav", key="u_c")
                p_c = st.text_input("Password", value="customer123", type="password", key="p_c")
                sub_c = st.form_submit_button("Sign In to Customer Portal", use_container_width=True)
                if sub_c:
                    res, err = api_call("POST", "/auth/login", json={"username": u_c, "password": p_c})
                    if err:
                        st.error(err)
                    elif res:
                        st.session_state.clear()
                        st.session_state.update(
                            token=res["access_token"],
                            role="CUSTOMER",
                            user_id=res["user_id"],
                            username=u_c,
                            customer_id="cust_sw_aarav",
                        )
                        st.rerun()

        # 4. OPERATIONS / ANALYST PORTAL
        with tab_op:
            st.markdown("""
            <div style="padding:0.4rem 0 0.8rem 0; text-align:left;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <strong style="color:#0F172A; font-size:0.92rem;">FinOps Operations & AI</strong>
                    <span class="fintech-badge badge-high">OPERATIONS</span>
                </div>
                <div style="font-size:0.78rem; color:#64748B; line-height:1.4;">
                    Telemetry triage, SOP evidence retrieval, and LangGraph root-cause analysis.
                </div>
            </div>
            """, unsafe_allow_html=True)
            with st.form("form_ops"):
                u_o = st.text_input("Username", value="analyst", key="u_o")
                p_o = st.text_input("Password", value="analyst123", type="password", key="p_o")
                sub_o = st.form_submit_button("Sign In to Operations & AI", use_container_width=True)
                if sub_o:
                    res, err = api_call("POST", "/auth/login", json={"username": u_o, "password": p_o})
                    if err:
                        st.error(err)
                    elif res:
                        st.session_state.clear()
                        st.session_state.update(
                            token=res["access_token"],
                            role="ANALYST",
                            user_id=res["user_id"],
                            username=u_o,
                        )
                        st.rerun()

        st.markdown("""
        <div style="margin-top:1.5rem; padding-top:1rem; border-top:1px solid #F1F5F9; font-size:0.75rem; color:#64748B; display:flex; justify-content:center; align-items:center; gap:8px;">
            <span style="display:inline-block; width:6px; height:6px; border-radius:50%; background:#16A34A;"></span>
            <span>Razorpay-Inspired Independent Platform • Synthetic Data • Local Inference</span>
        </div>
        """, unsafe_allow_html=True)


if "token" not in st.session_state:
    login_view()
    st.stop()

# Current user state
role = st.session_state.get("role", "ADMIN")
username = st.session_state.get("username", "admin")
active_customer_id = st.session_state.get("customer_id", "cust_sw_aarav")
active_merchant_id = st.session_state.get("merchant_id", "mid_swiggy_01")

USER_PROFILES = {
    "admin": {"name": "Lead Platform Administrator", "title": "Platform Admin", "clearance": "Level 3 (Full Governance)"},
    "manager": {"name": "Senior Operations Manager", "title": "Operations Manager", "clearance": "Level 2 (Approve & Execute)"},
    "analyst": {"name": "FinOps Analyst", "title": "Operations Analyst", "clearance": "Level 1 (View & Investigate)"},
    "merchant_swiggy": {"name": "Swiggy India (Finance)", "title": "Merchant Admin", "clearance": "Merchant Scoped (mid_swiggy_01)"},
    "customer_aarav": {"name": "Aarav Sharma", "title": "Verified Customer", "clearance": "Customer Scoped (cust_sw_aarav)"},
}
user_profile = USER_PROFILES.get(username.lower(), {"name": f"User {username}", "title": role, "clearance": role})


# ------------------------------------------------------------------- Role-Specific Sidebar Navigation
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand-box">
        <div class="sidebar-brand-title">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#00875A" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:6px;"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>
            OPSPILOT PAYMENTS
            <span class="sidebar-brand-badge" style="background:#00875A;">FINTECH</span>
        </div>
        <div class="sidebar-brand-sub">Razorpay-Inspired Operations Hub</div>
    </div>
    """, unsafe_allow_html=True)

    # 1. Strictly Scoped Customer Navigation
    if role == "CUSTOMER":
        st.markdown('<div class="sidebar-section-header">CUSTOMER ACCOUNT</div>', unsafe_allow_html=True)
        customer_options = [
            "🏠 Customer Home",
            "💳 My Transactions",
            "⏱️ Payment Details & Timeline",
            "🔔 Customer Notifications",
        ]
        current_nav = st.radio(
            "Customer Navigation",
            options=customer_options,
            key=f"nav_{role}_{username}",
            label_visibility="collapsed"
        )

    # 2. Strictly Scoped Merchant Navigation
    elif role == "MERCHANT":
        st.markdown('<div class="sidebar-section-header">MERCHANT PORTAL</div>', unsafe_allow_html=True)
        merchant_options = [
            "📊 Merchant Overview",
            "💳 Transactions",
            "🚨 Merchant Alerts & Advisories",
            "📈 Payment Analytics",
            "💰 Settlement Overview",
        ]
        current_nav = st.radio(
            "Merchant Navigation",
            options=merchant_options,
            key=f"nav_{role}_{username}",
            label_visibility="collapsed"
        )

    # 3. Operations & Analyst Navigation
    elif role in ("ANALYST", "MANAGER"):
        st.markdown('<div class="sidebar-section-header">FINOPS OPERATIONS</div>', unsafe_allow_html=True)
        ops_options = [
            "🤖 AI Investigation Workspace",
            "🎬 SBI UPI Live Demonstration",
            "🚨 Incident Command Centre",
            "🏦 Bank Switch Telemetry",
            "📊 Executive Overview",
            "🛡️ Platform Audit & Approvals",
        ]
        current_nav = st.radio(
            "Operations Navigation",
            options=ops_options,
            key=f"nav_{role}_{username}",
            label_visibility="collapsed"
        )

    # 4. Platform Administrator Navigation
    else:
        st.markdown('<div class="sidebar-section-header">PLATFORM GOVERNANCE</div>', unsafe_allow_html=True)
        admin_options = [
            "📊 Executive Overview",
            "💳 Payment Monitoring",
            "🏦 Bank Switch Telemetry",
            "🚨 Incident Command Centre",
            "👥 Merchants & Customers",
            "⚙️ Data Pipeline & Ingestion",
            "🛡️ Platform Audit & Approvals",
            "🤖 AI Investigation Workspace",
            "🎬 SBI UPI Live Demonstration",
            "🏪 Preview Merchant Portal",
            "👤 Preview Customer Portal",
            "📈 Deep Operational Analytics",
        ]
        current_nav = st.radio(
            "Admin Navigation",
            options=admin_options,
            key=f"nav_{role}_{username}",
            label_visibility="collapsed"
        )

    # User profile and sign-out card
    st.markdown(f"""
    <div class="sidebar-user-card" style="margin-top:1.5rem;">
        <div>
            <div class="sidebar-user-name">{user_profile['name']}</div>
            <div class="sidebar-user-role" style="background:rgba(0,135,90,0.2); color:#A7F3D0 !important;">@{username} · {role}</div>
            <div style="font-size:0.68rem; color:#94A3B8; margin-top:2px;">{user_profile['clearance']}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Sign Out", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    st.markdown("""
    <div style="font-size:0.7rem; color:#64748B; margin-top:1.25rem; text-align:center;">
        Razorpay-Inspired Prototype<br>100% Synthetic Demo Data
    </div>
    """, unsafe_allow_html=True)


# ------------------------------------------------------------- Role-Aware Page Router
if role == "CUSTOMER":
    # Customer Portal (Workspace 1)
    render_customer_portal(customer_id=active_customer_id, page=current_nav)

elif role == "MERCHANT":
    # Merchant Portal (Workspace 2)
    render_merchant_portal(merchant_id=active_merchant_id, page=current_nav)

elif current_nav == "🤖 AI Investigation Workspace":
    # AI Investigation Workspace (Workspace 4)
    render_ai_investigation(role=role)

elif current_nav == "🎬 SBI UPI Live Demonstration":
    # Interactive SBI UPI Live Lifecycle Demonstration
    render_sbi_upi_demo(role=role)

elif current_nav == "🏪 Preview Merchant Portal":
    render_merchant_portal(merchant_id="mid_swiggy_01", page="Merchant Overview")

elif current_nav == "👤 Preview Customer Portal":
    render_customer_portal(customer_id="cust_sw_aarav", page="Customer Home")

elif current_nav == "📈 Deep Operational Analytics":
    sub_page = st.sidebar.selectbox("Deep Dive Views:", [
        "Overview", "Revenue", "Transactions", "Exceptions", "Anomalies",
        "Analytics", "Approvals", "Audit Trail", "Data Quality", "Settings"
    ])
    if sub_page == "Overview":
        render_overview(role)
    elif sub_page == "Revenue":
        render_revenue(role)
    elif sub_page == "Transactions":
        render_transactions(role)
    elif sub_page == "Exceptions":
        render_exceptions(role)
    elif sub_page == "Anomalies":
        render_anomalies(role)
    elif sub_page == "Analytics":
        render_analytics(role)
    elif sub_page == "Approvals":
        render_approvals(role)
    elif sub_page == "Audit Trail":
        render_audit(role)
    elif sub_page == "Data Quality":
        render_data_quality(role)
    elif sub_page == "Settings":
        render_settings(role)

else:
    # Admin Dashboard (Workspace 3) or Operations overview
    render_admin_dashboard(role=role, page=current_nav)
