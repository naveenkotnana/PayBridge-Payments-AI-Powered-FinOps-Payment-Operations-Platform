# -*- coding: utf-8 -*-
# ruff: noqa: E402
"""PayBridge Payments — Fintech Payment Operations & Intelligence Platform UI.

Unified 3-Role Platform:
1. 🛡️ Admin: FinOps Command Center, Analytics, ML Anomaly Detection, AI Investigation, Approvals & Audit
2. 🏪 Merchant (Rameshwaram Cafe): Real local store orders, GMV, fulfillment hold advisories & business impact
3. 👤 Customer (Aarav): Transparent buyer ledger, live order cooking status & double-debit protection guarantee
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
    from backend.app.core.security import seed_demo_users
    from backend.app.db.base import SessionLocal, init_db
    from backend.app.models import MonthlyRevenue, User
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

# Clean View Renderers for the 3 Core Roles
from dashboard.views.admin_dashboard import render_admin_dashboard
from dashboard.views.customer_portal import render_customer_portal
from dashboard.views.merchant_portal import render_merchant_portal

st.set_page_config(
    page_title="PayBridge Payments — AI FinOps Platform",
    page_icon=":zap:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject modern FinTech design styling
st.markdown(RAZORPAY_THEME_CSS, unsafe_allow_html=True)

# ------------------------------------------------------------- Session State
if "role" not in st.session_state:
    st.session_state.role = "ADMIN"
    st.session_state.username = "admin"
    st.session_state.customer_id = "cust_aarav_01"
    st.session_state.merchant_id = "mid_rameshwaram_01"

if "incident_status" not in st.session_state:
    st.session_state.incident_status = "Waiting for Admin Approval"

current_role = st.session_state.role

# ------------------------------------------------------------- 1. TOP NAVBAR (STRICTLY 3 ROLES)
top_c_left, top_c_pills, top_c_right = st.columns([2.6, 4.2, 2.2])

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
            <div style="font-size:0.72rem; color:#64748B;">AI-Powered Payment Operations Platform</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with top_c_pills:
    # Exactly 3 Core Role Switcher Pills
    p1, p2, p3 = st.columns(3)
    with p1:
        if st.button("🛡️ Admin", key="btn_top_admin", use_container_width=True, type="primary" if current_role == "ADMIN" else "secondary"):
            st.session_state.role = "ADMIN"
            st.session_state.username = "admin"
            st.session_state.selected_nav = "Overview"
            st.rerun()
    with p2:
        if st.button("🏪 Merchant", key="btn_top_merchant", use_container_width=True, type="primary" if current_role == "MERCHANT" else "secondary"):
            st.session_state.role = "MERCHANT"
            st.session_state.username = "merchant"
            st.session_state.merchant_id = "mid_rameshwaram_01"
            st.session_state.selected_nav = "Overview"
            st.rerun()
    with p3:
        if st.button("👤 Customer", key="btn_top_customer", use_container_width=True, type="primary" if current_role == "CUSTOMER" else "secondary"):
            st.session_state.role = "CUSTOMER"
            st.session_state.username = "customer"
            st.session_state.customer_id = "cust_aarav_01"
            st.session_state.selected_nav = "Orders"
            st.rerun()

with top_c_right:
    r1, r2 = st.columns([2.0, 0.6])
    with r1:
        roles_list = ["Admin", "Merchant", "Customer"]
        role_map = {"Admin": "ADMIN", "Merchant": "MERCHANT", "Customer": "CUSTOMER"}
        current_idx = 0 if current_role == "ADMIN" else (1 if current_role == "MERCHANT" else 2)

        selected_role_label = st.selectbox(
            "Active Role",
            options=roles_list,
            index=current_idx,
            key="top_role_dropdown",
            label_visibility="collapsed"
        )
        new_role = role_map[selected_role_label]
        if new_role != current_role:
            st.session_state.role = new_role
            if new_role == "ADMIN":
                st.session_state.username = "admin"
                st.session_state.selected_nav = "Overview"
            elif new_role == "MERCHANT":
                st.session_state.username = "merchant"
                st.session_state.merchant_id = "mid_rameshwaram_01"
                st.session_state.selected_nav = "Overview"
            elif new_role == "CUSTOMER":
                st.session_state.username = "customer"
                st.session_state.customer_id = "cust_aarav_01"
                st.session_state.selected_nav = "Orders"
            st.rerun()

    with r2:
        if st.button("🔄", key="top_reload_btn", help="Refresh platform state"):
            st.rerun()

st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)


# ------------------------------------------------------------- 2. SIDEBAR (ROLE-SCOPED NAVIGATION)
with st.sidebar:
    # Brand Workspace Card
    badge_color = "#00875A" if current_role == "ADMIN" else ("#F59E0B" if current_role == "MERCHANT" else "#2563EB")
    role_label = "PLATFORM ADMIN" if current_role == "ADMIN" else ("MERCHANT STORE" if current_role == "MERCHANT" else "CUSTOMER")

    st.markdown(f"""
    <div style="background:#0F2744; border:1px solid #1E3A5F; border-radius:8px; padding:0.75rem 0.85rem; margin-bottom:1rem;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <span style="font-size:0.62rem; font-weight:800; color:#94A3B8; letter-spacing:0.06em; text-transform:uppercase;">PAYBRIDGE WORKSPACE</span>
            <span style="font-size:0.6rem; font-weight:700; background:{badge_color}; color:#FFFFFF; padding:1px 6px; border-radius:4px;">{role_label}</span>
        </div>
        <div style="font-size:1.05rem; font-weight:800; color:#FFFFFF; letter-spacing:-0.01em;">
            {'FinOps Command Hub' if current_role == 'ADMIN' else ('Rameshwaram Cafe' if current_role == 'MERCHANT' else 'Aarav Sharma')}
        </div>
        <div style="font-size:0.7rem; color:#94A3B8; margin-top:2px;">
            {'Multi-Tenant Platform Governance' if current_role == 'ADMIN' else ('Food & Beverage Merchant' if current_role == 'MERCHANT' else 'Verified Buyer Profile')}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Scoped Navigation Options
    if current_role == "ADMIN":
        st.markdown('<div class="sidebar-section-header">ADMIN NAVIGATION</div>', unsafe_allow_html=True)
        nav_options = [
            "Overview",
            "Payments",
            "Anomalies",
            "AI Investigation",
            "Data Pipeline",
            "Approvals",
            "Audit",
        ]
    elif current_role == "MERCHANT":
        st.markdown('<div class="sidebar-section-header">MERCHANT NAVIGATION</div>', unsafe_allow_html=True)
        nav_options = [
            "Overview",
            "Orders",
            "Payments",
        ]
    else:  # CUSTOMER
        st.markdown('<div class="sidebar-section-header">CUSTOMER NAVIGATION</div>', unsafe_allow_html=True)
        nav_options = [
            "Orders",
            "Payments",
        ]

    if "selected_nav" not in st.session_state or st.session_state.selected_nav not in nav_options:
        st.session_state.selected_nav = nav_options[0]

    chosen_nav = st.radio(
        "Platform Navigation",
        options=nav_options,
        index=nav_options.index(st.session_state.selected_nav),
        key="main_role_navigation_radio",
        label_visibility="collapsed"
    )
    if chosen_nav != st.session_state.selected_nav:
        st.session_state.selected_nav = chosen_nav
        st.rerun()

    # User Profile Card
    user_name = "Lead Platform Administrator" if current_role == "ADMIN" else ("Rameshwaram Cafe (Finance)" if current_role == "MERCHANT" else "Aarav Sharma")
    user_handle = "@admin" if current_role == "ADMIN" else ("@merchant" if current_role == "MERCHANT" else "@customer")

    st.markdown(f"""
    <div class="sidebar-user-card" style="margin-top:2rem;">
        <div>
            <div class="sidebar-user-name">{user_name}</div>
            <div style="font-size:0.7rem; color:#38BDF8; font-weight:600;">{user_handle}</div>
        </div>
        <span style="font-size:0.65rem; font-weight:700; background:#2F5BFF; color:#FFFFFF; padding:2px 6px; border-radius:4px;">{current_role}</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="font-size:0.7rem; color:#64748B; margin-top:1.5rem; text-align:center; border-top:1px solid #1E3A5F; padding-top:0.8rem;">
        PayBridge FinOps Engine<br>100% Synthetic Demo Data · Local Inference
    </div>
    """, unsafe_allow_html=True)


# ------------------------------------------------------------- 3. MAIN ROUTER
active_page = st.session_state.selected_nav

if current_role == "ADMIN":
    render_admin_dashboard(role="ADMIN", page=active_page)

elif current_role == "MERCHANT":
    render_merchant_portal(merchant_id="mid_rameshwaram_01", page=active_page)

else:  # CUSTOMER
    render_customer_portal(customer_id="cust_aarav_01", page=active_page)
