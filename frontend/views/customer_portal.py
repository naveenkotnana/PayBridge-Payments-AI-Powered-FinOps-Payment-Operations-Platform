# -*- coding: utf-8 -*-
"""Customer Portal — Aarav's Orders at Rameshwaram Cafe.

Simple, human-readable customer experience:
- Clear order summary and total.
- Transparent payment status and verification timeline.
- Protection guarantee: "Your money was not charged twice."
"""
import pandas as pd
import streamlit as st

from app.db.base import SessionLocal
from app.models.payments import (
    Customer,
)


def render_customer_portal(customer_id: str = "cust_aarav_01", page: str = "Orders"):
    """Render the simplified, human-friendly Customer Portal for Aarav."""
    with SessionLocal() as db:
        cust = db.query(Customer).filter(Customer.customer_id == customer_id).first()
        cust_name = cust.name if cust else "Aarav"



        # --------------------------------------------------------- 1. HEADER
        st.markdown(f"""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:1.25rem 1.5rem; margin-bottom:1.25rem; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
            <div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:1.4rem;">👤</span>
                    <span style="font-size:1.4rem; font-weight:800; color:#0F172A; letter-spacing:-0.02em;">{cust_name}'s Orders</span>
                    <span class="fintech-badge" style="background:#EFF6FF; color:#1D4ED8; font-weight:700; font-size:0.7rem; padding:2px 8px; border-radius:4px;">CUSTOMER PORTAL</span>
                </div>
                <div style="font-size:0.88rem; color:#64748B; margin-top:2px;">
                    Ordering from <strong>Rameshwaram Cafe</strong>
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:0.7rem; font-weight:700; color:#64748B; text-transform:uppercase;">Buyer Protection</div>
                <div style="font-size:0.88rem; font-weight:700; color:#059669;">Zero Double-Debit Guarantee</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --------------------------------------------------------- 2. SUB-NAVIGATION TABS
        tab_choice = st.radio(
            "Customer Navigation Tabs",
            options=["Orders", "Payments"],
            index=0 if page == "Orders" else 1,
            horizontal=True,
            key="customer_internal_tabs",
            label_visibility="collapsed"
        )

        # --------------------------------------------------------- 3. TAB CONTENTS
        if tab_choice == "Orders":
            # Active Order Card
            st.markdown("""
            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:1.4rem; box-shadow:0 2px 6px rgba(0,0,0,0.02); margin-bottom:1.5rem;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem; padding-bottom:0.75rem; border-bottom:1px solid #F1F5F9;">
                    <div>
                        <div style="font-size:0.75rem; font-weight:700; color:#64748B; text-transform:uppercase;">Current Order • Rameshwaram Cafe</div>
                        <h2 style="font-size:1.25rem; font-weight:800; color:#0F172A; margin:2px 0;">Order #RC10291</h2>
                    </div>
                    <span style="font-size:0.82rem; font-weight:700; background:#ECFDF5; color:#059669; padding:4px 12px; border-radius:999px;">
                        ✅ Payment Successful
                    </span>
                </div>
                <div style="display:grid; grid-template-columns: 1.5fr 1fr; gap:20px;">
                    <div>
                        <div style="font-size:0.82rem; font-weight:700; color:#475569; text-transform:uppercase; margin-bottom:6px;">Items Ordered:</div>
                        <div style="font-size:0.92rem; color:#1E293B; line-height:1.6;">
                            • <strong>Masala Dosa</strong> × 2 (Crispy potato filling with ghee)<br>
                            • <strong>Filter Coffee</strong> × 1 (Authentic South Indian brew)
                        </div>
                        <div style="margin-top:12px; font-size:1.15rem; font-weight:800; color:#0F172A;">
                            Total: ₹280.00
                        </div>
                    </div>
                    <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:1rem; text-align:center;">
                        <div style="font-size:0.75rem; font-weight:700; color:#64748B; text-transform:uppercase;">Kitchen Status</div>
                        <div style="font-size:1.4rem; margin:6px 0;">🍽️</div>
                        <div style="font-size:0.95rem; font-weight:800; color:#0F172A;">Preparing Your Food</div>
                        <div style="font-size:0.75rem; color:#64748B; margin-top:4px;">Estimated pickup: 8-10 mins</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Transaction Timeline
            st.markdown('<div style="font-size:0.85rem; font-weight:800; color:#475569; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.75rem;">Payment & Order Progress Timeline</div>', unsafe_allow_html=True)

            st.markdown("""
            <div style="display:flex; justify-content:space-between; align-items:center; background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:1rem 1.25rem; margin-bottom:1.5rem;">
                <div style="display:flex; flex-direction:column; align-items:center; text-align:center; flex:1;">
                    <div style="width:26px; height:26px; border-radius:50%; background:#10B981; color:white; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:0.75rem;">✓</div>
                    <div style="font-size:0.78rem; font-weight:700; color:#0F172A; margin-top:4px;">Order Placed</div>
                    <div style="font-size:0.68rem; color:#64748B;">10:14:00 AM</div>
                </div>
                <div style="flex:0.5; height:2px; background:#10B981;"></div>
                <div style="display:flex; flex-direction:column; align-items:center; text-align:center; flex:1;">
                    <div style="width:26px; height:26px; border-radius:50%; background:#10B981; color:white; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:0.75rem;">✓</div>
                    <div style="font-size:0.78rem; font-weight:700; color:#0F172A; margin-top:4px;">Payment Initiated</div>
                    <div style="font-size:0.68rem; color:#64748B;">UPI Handle</div>
                </div>
                <div style="flex:0.5; height:2px; background:#10B981;"></div>
                <div style="display:flex; flex-direction:column; align-items:center; text-align:center; flex:1;">
                    <div style="width:26px; height:26px; border-radius:50%; background:#10B981; color:white; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:0.75rem;">✓</div>
                    <div style="font-size:0.78rem; font-weight:700; color:#0F172A; margin-top:4px;">Payment Verified</div>
                    <div style="font-size:0.68rem; color:#64748B;">Confirmed by Bank</div>
                </div>
                <div style="flex:0.5; height:2px; background:#10B981;"></div>
                <div style="display:flex; flex-direction:column; align-items:center; text-align:center; flex:1;">
                    <div style="width:26px; height:26px; border-radius:50%; background:#10B981; color:white; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:0.75rem;">✓</div>
                    <div style="font-size:0.78rem; font-weight:700; color:#0F172A; margin-top:4px;">Restaurant Notified</div>
                    <div style="font-size:0.68rem; color:#64748B;">Order Sent to Kitchen</div>
                </div>
                <div style="flex:0.5; height:2px; background:#3B82F6;"></div>
                <div style="display:flex; flex-direction:column; align-items:center; text-align:center; flex:1;">
                    <div style="width:26px; height:26px; border-radius:50%; background:#3B82F6; color:white; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:0.75rem;">🍽️</div>
                    <div style="font-size:0.78rem; font-weight:700; color:#2563EB; margin-top:4px;">Order Preparing</div>
                    <div style="font-size:0.68rem; color:#3B82F6;">Live Now</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Failure protection notice
            st.markdown("""
            <div style="background:#EFF6FF; border:1px solid #BFDBFE; border-radius:10px; padding:0.9rem 1.25rem;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:1.1rem;">🛡️</span>
                    <strong style="color:#1E40AF; font-size:0.88rem;">Customer Peace-of-Mind Guarantee</strong>
                </div>
                <div style="font-size:0.8rem; color:#1E3A8A; margin-top:4px;">
                    If an issuing bank switch times out or delays: <strong>Your money was not charged twice.</strong> Any unconfirmed funds automatically reverse to your bank account within minutes.
                </div>
            </div>
            """, unsafe_allow_html=True)

        elif tab_choice == "Payments":
            st.markdown('<div style="font-size:0.88rem; font-weight:800; color:#0F172A; margin-bottom:0.75rem;">Aarav\'s Past Transactions</div>', unsafe_allow_html=True)
            past_txns = [
                {"Payment ID": "pay_rc_10291", "Merchant": "Rameshwaram Cafe", "Order": "Masala Dosa × 2, Filter Coffee × 1", "Amount": "₹280.00", "Payment Status": "SUCCESSFUL", "Method": "UPI (Google Pay)"},
                {"Payment ID": "pay_rc_10188", "Merchant": "Rameshwaram Cafe", "Order": "Ghee Roast Dosa × 1, Tea × 1", "Amount": "₹160.00", "Payment Status": "SUCCESSFUL", "Method": "UPI (PhonePe)"},
                {"Payment ID": "pay_rc_10042", "Merchant": "Rameshwaram Cafe", "Order": "Idli Vada Combo × 2", "Amount": "₹180.00", "Payment Status": "SUCCESSFUL", "Method": "Debit Card"},
            ]
            st.dataframe(pd.DataFrame(past_txns), hide_index=True, use_container_width=True)
