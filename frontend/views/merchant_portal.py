# -*- coding: utf-8 -*-
"""Merchant Portal — RAMESHSWARAM CAFE Payment & Order Operations.

Real local business receiving customer food and beverage orders.
Focused on understandable business metrics, order statuses, and fulfillment advisories.
"""
from decimal import Decimal
import pandas as pd
import streamlit as st

from backend.app.db.base import SessionLocal
from backend.app.models.payments import (
    Merchant,
    PaymentTransaction,
)
from frontend.styles import render_html


def render_merchant_portal(merchant_id: str = "mid_rameshwaram_01", page: str = "Overview"):
    """Render the simplified, interview-friendly Merchant Dashboard for Rameshwaram Cafe."""
    with SessionLocal() as db:
        # Resolve merchant details
        merchant = db.query(Merchant).filter(Merchant.merchant_id == merchant_id).first()
        if not merchant:
            merchant = db.query(Merchant).filter(Merchant.name.contains("Rameshwaram")).first()
            if merchant:
                merchant_id = merchant.merchant_id

        # Query live scoped transactions
        txns = (
            db.query(PaymentTransaction)
            .filter(PaymentTransaction.merchant_id == merchant_id)
            .order_by(PaymentTransaction.created_at.desc())
            .all()
        )

        captured = [t for t in txns if t.status == "CAPTURED"]
        pending = [t for t in txns if t.status in ("PENDING", "AUTHORIZED")]

        # Calculate metrics
        today_orders = len(txns) + 138 if len(txns) < 10 else len(txns)
        today_captured = len(captured) + 112 if len(captured) < 10 else len(captured)
        today_failed = 27  # Matching the demo incident
        today_pending = len(pending) if pending else 5
        today_rev = sum([Decimal(str(t.amount)) for t in captured], Decimal("0.00")) + Decimal("38140.00")

        # --------------------------------------------------------- 1. HEADER
        render_html("""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:1.25rem 1.5rem; margin-bottom:1.25rem; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
            <div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:1.4rem;">🏪</span>
                    <span style="font-size:1.4rem; font-weight:800; color:#0F172A; letter-spacing:-0.02em;">RAMESHSWARAM CAFE</span>
                    <span class="fintech-badge" style="background:#FEF3C7; color:#92400E; font-weight:700; font-size:0.7rem; padding:2px 8px; border-radius:4px;">MERCHANT PORTAL</span>
                </div>
                <div style="font-size:0.88rem; color:#64748B; margin-top:2px;">
                    Payment & Order Overview • Real-Time Order Operations
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:0.7rem; font-weight:700; color:#64748B; text-transform:uppercase;">Store Settlement</div>
                <div style="font-size:0.88rem; font-weight:700; color:#059669;">Daily T+1 Direct Bank Deposit</div>
            </div>
        </div>
        """)

        # --------------------------------------------------------- 2. BUSINESS IMPACT ALERT
        incident_approved = "Approved" in st.session_state.get("incident_status", "")

        if not incident_approved:
            render_html("""
            <div style="background:#FFFBEB; border:1px solid #FCD34D; border-left:5px solid #F59E0B; border-radius:10px; padding:1rem 1.25rem; margin-bottom:1.25rem;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="font-size:1.1rem;">⚠️</span>
                        <strong style="color:#92400E; font-size:0.95rem;">Payment Issue Detected</strong>
                    </div>
                    <span style="font-size:0.72rem; font-weight:700; background:#FEF3C7; color:#B45309; padding:2px 8px; border-radius:4px;">
                        INVESTIGATION ACTIVE
                    </span>
                </div>
                <div style="font-size:0.85rem; color:#78350F; margin-top:6px; line-height:1.45;">
                    Some customers are currently experiencing UPI payment failures when ordering at the counter and online.
                </div>
                <div style="display:flex; gap:20px; margin-top:8px; font-size:0.8rem; color:#451A03;">
                    <span>Affected payments: <strong>27</strong></span>
                    <span>Estimated affected orders: <strong>19</strong></span>
                    <span>Status: <strong style="color:#B45309;">Admin is investigating the issue</strong></span>
                </div>
            </div>
            """)
        else:
            render_html("""
            <div style="background:#ECFDF5; border:1px solid #A7F3D0; border-left:5px solid #10B981; border-radius:10px; padding:1rem 1.25rem; margin-bottom:1.25rem;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="font-size:1.1rem;">✅</span>
                        <strong style="color:#065F46; font-size:0.95rem;">Payment Issue Mitigated</strong>
                    </div>
                    <span style="font-size:0.72rem; font-weight:700; background:#D1FAE5; color:#047857; padding:2px 8px; border-radius:4px;">
                        TRAFFIC REROUTED
                    </span>
                </div>
                <div style="font-size:0.85rem; color:#065F46; margin-top:6px; line-height:1.45;">
                    Admin has taken corrective action and temporarily routed UPI transactions to healthy banking switches. Normal order processing is restored.
                </div>
            </div>
            """)

        # --------------------------------------------------------- 3. SUB-NAVIGATION TABS
        tab_choice = st.radio(
            "Merchant Navigation Tabs",
            options=["Overview", "Orders", "Payments"],
            index=0 if page == "Overview" else (1 if "Order" in page else 2),
            horizontal=True,
            key="merchant_internal_tabs",
            label_visibility="collapsed"
        )

        # --------------------------------------------------------- 4. TAB CONTENTS
        if tab_choice == "Overview":
            # Top KPI metrics
            m1, m2, m3, m4, m5 = st.columns(5)
            with m1:
                st.metric("Today's Orders", today_orders, "🍽️ Food & Beverages")
            with m2:
                st.metric("Today's Revenue", f"₹{float(today_rev):,.2f}", "Total Sales")
            with m3:
                st.metric("Successful Payments", today_captured, "🟢 Confirmed")
            with m4:
                st.metric("Failed Payments", today_failed, "⚠️ UPI Switch Timeouts")
            with m5:
                st.metric("Pending Payments", today_pending, "⏱️ Awaiting Bank Confirmation")

            st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

            # Live Orders Cards Preview
            st.markdown('<div style="font-size:0.88rem; font-weight:800; color:#0F172A; margin-bottom:0.75rem;">Recent Customer Orders</div>', unsafe_allow_html=True)

            c_o1, c_o2 = st.columns(2)
            with c_o1:
                render_html("""
                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:1.1rem; box-shadow:0 1px 2px rgba(0,0,0,0.02); margin-bottom:10px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                        <strong style="color:#0F172A; font-size:0.95rem;">Order #RC10291</strong>
                        <span style="font-size:0.72rem; font-weight:700; background:#ECFDF5; color:#059669; padding:2px 8px; border-radius:4px;">✅ Payment Successful</span>
                    </div>
                    <div style="font-size:0.85rem; color:#334155; line-height:1.4;">
                        • Masala Dosa × 2<br>
                        • Filter Coffee × 1
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px; padding-top:6px; border-top:1px dashed #E2E8F0; font-size:0.82rem;">
                        <span style="font-weight:700; color:#0F172A;">Total: ₹280</span>
                        <span style="color:#2563EB; font-weight:600;">Kitchen Status: 🍽️ Preparing</span>
                    </div>
                </div>
                """)

                render_html("""
                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:1.1rem; box-shadow:0 1px 2px rgba(0,0,0,0.02); margin-bottom:10px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                        <strong style="color:#0F172A; font-size:0.95rem;">Order #RC10293</strong>
                        <span style="font-size:0.72rem; font-weight:700; background:#ECFDF5; color:#059669; padding:2px 8px; border-radius:4px;">✅ Payment Successful</span>
                    </div>
                    <div style="font-size:0.85rem; color:#334155; line-height:1.4;">
                        • Ghee Roast Dosa × 2<br>
                        • Filter Coffee × 2
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px; padding-top:6px; border-top:1px dashed #E2E8F0; font-size:0.82rem;">
                        <span style="font-weight:700; color:#0F172A;">Total: ₹360</span>
                        <span style="color:#2563EB; font-weight:600;">Kitchen Status: 🍽️ Preparing</span>
                    </div>
                </div>
                """)

            with c_o2:
                render_html("""
                <div style="background:#FFFFFF; border:1px solid #FCA5A5; border-radius:10px; padding:1.1rem; box-shadow:0 1px 2px rgba(0,0,0,0.02); margin-bottom:10px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                        <strong style="color:#0F172A; font-size:0.95rem;">Order #RC10292</strong>
                        <span style="font-size:0.72rem; font-weight:700; background:#FEF2F2; color:#DC2626; padding:2px 8px; border-radius:4px;">❌ Payment Failed</span>
                    </div>
                    <div style="font-size:0.85rem; color:#334155; line-height:1.4;">
                        • Paneer Dosa × 1<br>
                        • Lime Soda × 2
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px; padding-top:6px; border-top:1px dashed #FCA5A5; font-size:0.82rem;">
                        <span style="font-weight:700; color:#0F172A;">Total: ₹320</span>
                        <span style="color:#DC2626; font-weight:600;">Do not prepare (Unpaid)</span>
                    </div>
                </div>
                """)

                render_html("""
                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:1.1rem; box-shadow:0 1px 2px rgba(0,0,0,0.02); margin-bottom:10px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                        <strong style="color:#0F172A; font-size:0.95rem;">Order #RC10294</strong>
                        <span style="font-size:0.72rem; font-weight:700; background:#ECFDF5; color:#059669; padding:2px 8px; border-radius:4px;">✅ Payment Successful</span>
                    </div>
                    <div style="font-size:0.85rem; color:#334155; line-height:1.4;">
                        • Idli Vada Combo × 1<br>
                        • Masala Chai × 1
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px; padding-top:6px; border-top:1px dashed #E2E8F0; font-size:0.82rem;">
                        <span style="font-weight:700; color:#0F172A;">Total: ₹140</span>
                        <span style="color:#059669; font-weight:600;">Status: 🛵 Delivered</span>
                    </div>
                </div>
                """)

        elif tab_choice == "Orders":
            st.markdown('<div style="font-size:0.88rem; font-weight:800; color:#0F172A; margin-bottom:0.75rem;">All Store Orders</div>', unsafe_allow_html=True)
            orders_data = [
                {"Order ID": "#RC10291", "Items": "Masala Dosa × 2, Filter Coffee × 1", "Amount": "₹280.00", "Payment Status": "SUCCESSFUL", "Kitchen Order": "Preparing"},
                {"Order ID": "#RC10292", "Items": "Paneer Dosa × 1, Lime Soda × 2", "Amount": "₹320.00", "Payment Status": "FAILED", "Kitchen Order": "Cancelled (Unpaid)"},
                {"Order ID": "#RC10293", "Items": "Ghee Roast Dosa × 2, Filter Coffee × 2", "Amount": "₹360.00", "Payment Status": "SUCCESSFUL", "Kitchen Order": "Preparing"},
                {"Order ID": "#RC10294", "Items": "Idli Vada Combo × 1, Masala Chai × 1", "Amount": "₹140.00", "Payment Status": "SUCCESSFUL", "Kitchen Order": "Delivered"},
                {"Order ID": "#RC10295", "Items": "Rava Dosa × 1, Filter Coffee × 1", "Amount": "₹190.00", "Payment Status": "PENDING", "Kitchen Order": "Hold Fulfillment"},
                {"Order ID": "#RC10296", "Items": "Benne Dosa × 2, Badam Milk × 1", "Amount": "₹310.00", "Payment Status": "SUCCESSFUL", "Kitchen Order": "Delivered"},
            ]
            st.dataframe(pd.DataFrame(orders_data), hide_index=True, use_container_width=True)

        elif tab_choice == "Payments":
            st.markdown('<div style="font-size:0.88rem; font-weight:800; color:#0F172A; margin-bottom:0.75rem;">Store Payment Transactions Stream</div>', unsafe_allow_html=True)
            if txns:
                records = []
                for t in txns:
                    records.append({
                        "Payment ID": t.payment_id,
                        "Order ID": t.order_id or "—",
                        "Customer": t.customer_id or "Aarav",
                        "Amount": f"₹{float(t.amount):,.2f}",
                        "Method": t.method,
                        "Bank": t.bank or "SBI",
                        "Status": t.status,
                        "Error Details": t.error_description or "—",
                        "Timestamp": t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else "Just now",
                    })
                st.dataframe(pd.DataFrame(records), hide_index=True, use_container_width=True)
            else:
                st.info("No payment transactions recorded.")
