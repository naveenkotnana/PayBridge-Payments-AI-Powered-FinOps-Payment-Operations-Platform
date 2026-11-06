# -*- coding: utf-8 -*-
"""Merchant Portal — RAMESHSWARAM CAFE Payment & Order Operations.

Real local business receiving customer food and beverage orders.
Focused on understandable business metrics, order statuses, and fulfillment advisories.
"""
from decimal import Decimal
import json
from html import escape
import pandas as pd
import streamlit as st

from backend.app.db.base import SessionLocal
from backend.app.models.payments import (
    Merchant,
    PaymentTransaction, PaymentOrder, CafeOrderItems,
)
from frontend.styles import render_html
from backend.app.models.ops import AuditLog


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
        today_orders = db.query(PaymentOrder).filter(PaymentOrder.merchant_id == merchant_id).count()
        today_captured = len(captured)
        today_failed = sum(t.status == "FAILED" for t in txns)
        today_pending = len(pending)
        today_rev = sum([Decimal(str(t.amount)) for t in captured], Decimal("0.00"))

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
        decision = (
            db.query(AuditLog)
            .filter(
                AuditLog.workflow_id == "WF-RAMESHWARAM-REROUTE",
                AuditLog.result_status.in_(["APPROVED", "REJECTED"]),
            )
            .order_by(AuditLog.timestamp.desc(), AuditLog.audit_id.desc())
            .first()
        )
        incident_approved = bool(decision and decision.result_status == "APPROVED")

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
                        <strong style="color:#065F46; font-size:0.95rem;">Demo Mitigation Approved</strong>
                    </div>
                    <span style="font-size:0.72rem; font-weight:700; background:#D1FAE5; color:#047857; padding:2px 8px; border-radius:4px;">
                        SIMULATED DECISION SAVED
                    </span>
                </div>
                <div style="font-size:0.85rem; color:#065F46; margin-top:6px; line-height:1.45;">
                    The Admin approved the simulated mitigation. The review is complete; this prototype has not changed bank routing or the status of existing payments.
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
                st.metric("Stored Orders", today_orders, "🍽️ Food & Beverages")
            with m2:
                st.metric("Captured GMV", f"₹{float(today_rev):,.2f}", "Stored payment volume")
            with m3:
                st.metric("Successful Payments", today_captured, "🟢 Confirmed")
                if st.button(f"View successful ({today_captured})", key="merchant_view_successful", disabled=today_captured == 0, use_container_width=True):
                    st.session_state["merchant_payment_status_view"] = "CAPTURED"
            with m4:
                st.metric("Failed Payments", today_failed, "Stored failed payments")
                if st.button(f"View failed ({today_failed})", key="merchant_view_failed", disabled=today_failed == 0, use_container_width=True):
                    st.session_state["merchant_payment_status_view"] = "FAILED"
            with m5:
                st.metric("Pending Payments", today_pending, "⏱️ Awaiting Bank Confirmation")
                if st.button(f"View pending ({today_pending})", key="merchant_view_pending", disabled=today_pending == 0, use_container_width=True):
                    st.session_state["merchant_payment_status_view"] = "PENDING"

            status_view = st.session_state.get("merchant_payment_status_view")
            if status_view:
                view_title = {"CAPTURED": "Successful payments", "FAILED": "Failed payments", "PENDING": "Pending and authorized payments"}[status_view]
                st.markdown(f"**{view_title} · Rameshwaram Cafe**")
                if st.button("Close payment details", key="merchant_close_payment_details"):
                    st.session_state.pop("merchant_payment_status_view", None)
                    st.rerun()
                visible_statuses = {"PENDING", "AUTHORIZED"} if status_view == "PENDING" else {status_view}
                visible_txns = [t for t in txns if t.status in visible_statuses]
                payment_records = [{
                    "Payment ID": t.payment_id,
                    "Order ID": t.order_id or "—",
                    "Amount": f"₹{float(t.amount):,.2f}",
                    "Method": t.method,
                    "Bank": t.bank or "—",
                    "Status": t.status,
                    "Failure reason": t.error_description or "—",
                    "Last update": t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else "—",
                } for t in visible_txns]
                if payment_records:
                    st.dataframe(pd.DataFrame(payment_records), hide_index=True, use_container_width=True)
                else:
                    st.info("No saved payments currently match this status.")

            st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

            # Live Orders Cards Preview
            st.markdown('<div style="font-size:0.88rem; font-weight:800; color:#0F172A; margin-bottom:0.75rem;">Recent Customer Orders</div>', unsafe_allow_html=True)

            if st.button("Refresh recent orders", key="refresh_merchant_orders"):
                st.rerun()
            recent = db.query(PaymentOrder, CafeOrderItems).join(CafeOrderItems, CafeOrderItems.order_id == PaymentOrder.order_id).filter(PaymentOrder.merchant_id == merchant_id).order_by(PaymentOrder.created_at.desc(), PaymentOrder.order_id.desc()).limit(4).all()
            if not recent:
                st.info("No customer menu orders yet. Place an order from Customer → Orders.")
            columns = st.columns(2)
            for i, (order, details) in enumerate(recent):
                with columns[i % 2]:
                    items = json.loads(details.items_json)
                    item_lines = "<br>".join(f"• {escape(item['name'])} × {item['quantity']}" for item in items)
                    paid = order.status == "PAID"
                    status = "Payment successful" if paid else "Awaiting payment"
                    render_html(f"""
                    <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:10px;padding:1.1rem;box-shadow:0 1px 2px rgba(0,0,0,0.02);margin-bottom:10px;">
                        <div style="display:flex;justify-content:space-between;gap:8px;margin-bottom:8px;">
                            <strong>Order #{escape(order.order_id[-8:].upper())}</strong>
                            <span style="color:{'#059669' if paid else '#B45309'};font-weight:700;">{status}</span>
                        </div>
                        <div style="font-size:0.85rem;line-height:1.5;">{item_lines}</div>
                        <div style="margin-top:10px;border-top:1px dashed #E2E8F0;padding-top:8px;"><strong>Total: ₹{order.amount:,.2f}</strong></div>
                        <div style="font-size:0.75rem;color:#64748B;margin-top:5px;">{escape(order.data_source or '')} · {escape(str(order.created_at)[:19])}</div>
                    </div>
                    """)

        elif tab_choice == "Orders":
            st.markdown('<div style="font-size:0.88rem; font-weight:800; color:#0F172A; margin-bottom:0.75rem;">All Store Orders</div>', unsafe_allow_html=True)
            orders = db.query(PaymentOrder, CafeOrderItems).join(CafeOrderItems, CafeOrderItems.order_id == PaymentOrder.order_id).filter(PaymentOrder.merchant_id == merchant_id).order_by(PaymentOrder.created_at.desc()).limit(100).all()
            if orders:
                st.dataframe(pd.DataFrame([{"Order ID": order.order_id, "Customer": order.customer_id, "Items": ", ".join(f"{item['name']} × {item['quantity']}" for item in json.loads(details.items_json)), "Amount": f"₹{order.amount:,.2f}", "Payment Status": order.status, "Source": order.data_source} for order, details in orders]), hide_index=True, use_container_width=True)
            else:
                st.info("No cafe menu orders yet. Completed customer checkout orders will appear here.")

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
                        "Bank": t.bank or "—",
                        "Source": t.data_source,
                        "Status": t.status,
                        "Error Details": t.error_description or "—",
                        "Timestamp": t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else "Just now",
                    })
                st.dataframe(pd.DataFrame(records), hide_index=True, use_container_width=True)
            else:
                st.info("No payment transactions recorded.")
