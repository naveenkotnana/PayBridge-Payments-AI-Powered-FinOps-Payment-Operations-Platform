# -*- coding: utf-8 -*-
"""Customer Portal — Aarav's Orders & Razorpay Standard Checkout at Rameshwaram Cafe.

Simple, human-readable customer experience:
- Clear order summary and total: ₹280 (Masala Dosa × 2, Filter Coffee × 1)
- Razorpay Standard Web Checkout Integration (checkout.js modal)
- Transparent payment status and verification timeline.
- Protection guarantee: "Your money was not charged twice."
"""
import hashlib
import hmac
import uuid
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from backend.app.core.config import settings
from backend.app.db.base import SessionLocal
from backend.app.models.payments import (
    Customer,
)
from frontend.styles import render_html


def render_customer_portal(customer_id: str = "cust_aarav_01", page: str = "Orders"):
    """Render the simplified, human-friendly Customer Portal for Aarav with Razorpay Checkout."""
    # Initialize session states for customer checkout
    if "aarav_payment_status" not in st.session_state:
        st.session_state.aarav_payment_status = "PAID"  # Default clean demo state
    if "aarav_order_id" not in st.session_state:
        st.session_state.aarav_order_id = "order_RC10291"
    if "aarav_payment_id" not in st.session_state:
        st.session_state.aarav_payment_id = "pay_rc_10291"
    if "aarav_checkout_msg" not in st.session_state:
        st.session_state.aarav_checkout_msg = None

    with SessionLocal() as db:
        cust = db.query(Customer).filter(Customer.customer_id == customer_id).first()
        cust_name = cust.name if cust else "Aarav"

        # --------------------------------------------------------- 1. HEADER
        render_html(f"""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:1.25rem 1.5rem; margin-bottom:1.25rem; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
            <div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:1.4rem;">👤</span>
                    <span style="font-size:1.4rem; font-weight:800; color:#0F172A; letter-spacing:-0.02em;">{cust_name}'s Orders</span>
                    <span class="fintech-badge" style="background:#EFF6FF; color:#1D4ED8; font-weight:700; font-size:0.7rem; padding:2px 8px; border-radius:4px;">CUSTOMER PORTAL</span>
                </div>
                <div style="font-size:0.88rem; color:#64748B; margin-top:2px;">
                    Ordering from <strong>RAMESHSWARAM CAFE</strong>
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:0.7rem; font-weight:700; color:#64748B; text-transform:uppercase;">Buyer Protection</div>
                <div style="font-size:0.88rem; font-weight:700; color:#059669;">Zero Double-Debit Guarantee</div>
            </div>
        </div>
        """)

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
            # Display any checkout alerts
            if st.session_state.aarav_checkout_msg:
                m_type = st.session_state.aarav_checkout_msg.get("type", "info")
                m_txt = st.session_state.aarav_checkout_msg.get("text", "")
                if m_type == "success":
                    st.success(m_txt)
                elif m_type == "warning":
                    st.warning(m_txt)
                elif m_type == "error":
                    st.error(m_txt)

            is_paid = st.session_state.aarav_payment_status == "PAID"

            badge_text = "✅ Payment Successful" if is_paid else "⏳ Payment Pending (₹280)"
            badge_bg = "#ECFDF5" if is_paid else "#FEF3C7"
            badge_color = "#059669" if is_paid else "#B45309"
            kitchen_status = "Preparing Your Food" if is_paid else "Awaiting Payment Confirmation"
            kitchen_icon = "🍽️" if is_paid else "⏳"
            kitchen_sub = "Estimated pickup: 8-10 mins" if is_paid else "Order will be sent to kitchen upon payment"

            # Active Order Card
            render_html(f"""
            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:1.4rem; box-shadow:0 2px 6px rgba(0,0,0,0.02); margin-bottom:1.5rem;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem; padding-bottom:0.75rem; border-bottom:1px solid #F1F5F9;">
                    <div>
                        <div style="font-size:0.75rem; font-weight:700; color:#64748B; text-transform:uppercase;">Current Order • RAMESHSWARAM CAFE</div>
                        <h2 style="font-size:1.25rem; font-weight:800; color:#0F172A; margin:2px 0;">Order #RC10291</h2>
                    </div>
                    <span style="font-size:0.82rem; font-weight:700; background:{badge_bg}; color:{badge_color}; padding:4px 12px; border-radius:999px;">
                        {badge_text}
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
                        <div style="font-size:1.4rem; margin:6px 0;">{kitchen_icon}</div>
                        <div style="font-size:0.95rem; font-weight:800; color:#0F172A;">{kitchen_status}</div>
                        <div style="font-size:0.75rem; color:#64748B; margin-top:4px;">{kitchen_sub}</div>
                    </div>
                </div>
            </div>
            """)

            # Razorpay Checkout Actions Card
            st.markdown('<div style="font-size:0.85rem; font-weight:800; color:#475569; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.75rem;">Razorpay Standard Web Checkout</div>', unsafe_allow_html=True)
            
            c_col1, c_col2, c_col3 = st.columns([1.5, 1.2, 1.2])

            with c_col1:
                if st.button("💳 Pay ₹280 via Razorpay Modal", key="btn_open_rzp_modal", type="primary", use_container_width=True):
                    # Launch Razorpay checkout standard modal via HTML component
                    st.session_state.show_razorpay_modal = True

            with c_col2:
                if st.button("⚡ Simulate Verified Payment", key="btn_sim_verify_rzp", use_container_width=True):
                    # Direct simulated payment verification
                    new_pay_id = f"pay_{uuid.uuid4().hex[:10]}"
                    new_ord_id = f"order_{uuid.uuid4().hex[:10]}"
                    sig = hmac.new(settings.RAZORPAY_KEY_SECRET.encode(), f"{new_ord_id}|{new_pay_id}".encode(), hashlib.sha256).hexdigest()

                    st.session_state.aarav_payment_status = "PAID"
                    st.session_state.aarav_payment_id = new_pay_id
                    st.session_state.aarav_order_id = new_ord_id
                    st.session_state.aarav_signature = sig
                    st.session_state.aarav_checkout_msg = {
                        "type": "success",
                        "text": f"✅ Payment of ₹280 successfully verified via Razorpay! Transaction ID: {new_pay_id}"
                    }
                    st.rerun()

            with c_col3:
                if st.button("🔄 Reset Order State", key="btn_reset_order_state", use_container_width=True):
                    st.session_state.aarav_payment_status = "PENDING"
                    st.session_state.aarav_checkout_msg = {
                        "type": "info",
                        "text": "Order reset to PENDING. Ready to test payment flow."
                    }
                    st.rerun()

            # If user clicked the Razorpay modal button, inject the Standard Checkout checkout.js script
            if st.session_state.get("show_razorpay_modal", False):
                rzp_key_id = settings.RAZORPAY_KEY_ID
                checkout_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
                </head>
                <body>
                    <div style="font-family:sans-serif; text-align:center; padding:15px; background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px;">
                        <p style="font-size:0.9rem; font-weight:600; color:#0F172A; margin:0 0 10px 0;">
                            Opening Razorpay Standard Web Checkout for ₹280.00...
                        </p>
                        <button id="rzp-button1" style="background:#00875A; color:white; border:none; padding:8px 18px; border-radius:6px; font-weight:700; cursor:pointer;">
                            Click to Open Razorpay Popup
                        </button>
                    </div>
                    <script>
                    var options = {{
                        "key": "{rzp_key_id}",
                        "amount": 28000,
                        "currency": "INR",
                        "name": "RAMESHSWARAM CAFE",
                        "description": "Masala Dosa x 2, Filter Coffee x 1",
                        "image": "https://cdn-icons-png.flaticon.com/512/3075/3075977.png",
                        "prefill": {{
                            "name": "Aarav",
                            "email": "aarav@example.com",
                            "contact": "+919876543210"
                        }},
                        "notes": {{
                            "order_id": "RC10291",
                            "store": "Indiranagar, Bangalore"
                        }},
                        "theme": {{
                            "color": "#00875A"
                        }},
                        "handler": function (response){{
                            alert("Payment Successful! Razorpay Payment ID: " + response.razorpay_payment_id);
                        }},
                        "modal": {{
                            "ondismiss": function(){{
                                console.log("Razorpay Checkout dismissed by user.");
                            }}
                        }}
                    }};
                    var rzp1 = new Razorpay(options);
                    rzp1.on('payment.failed', function (response){{
                        alert("Payment Failed: " + response.error.description);
                    }});
                    document.getElementById('rzp-button1').onclick = function(e){{
                        rzp1.open();
                        e.preventDefault();
                    }};
                    // Auto-open
                    try {{ rzp1.open(); }} catch(err) {{ console.log(err); }}
                    </script>
                </body>
                </html>
                """
                components.html(checkout_html, height=140)

            # Transaction Timeline
            render_html('<div style="font-size:0.85rem; font-weight:800; color:#475569; text-transform:uppercase; letter-spacing:0.05em; margin:1.25rem 0 0.75rem 0;">Payment & Order Progress Timeline</div>')

            c_step4 = "#10B981" if is_paid else "#94A3B8"
            c_step5 = "#3B82F6" if is_paid else "#94A3B8"
            c_step5_text = "#2563EB" if is_paid else "#94A3B8"
            c_step5_sub = "Live Now" if is_paid else "Pending Payment"

            render_html(f"""
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
                    <div style="font-size:0.68rem; color:#64748B;">Razorpay Standard</div>
                </div>
                <div style="flex:0.5; height:2px; background:{c_step4};"></div>
                <div style="display:flex; flex-direction:column; align-items:center; text-align:center; flex:1;">
                    <div style="width:26px; height:26px; border-radius:50%; background:{c_step4}; color:white; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:0.75rem;">{'✓' if is_paid else '⏳'}</div>
                    <div style="font-size:0.78rem; font-weight:700; color:#0F172A; margin-top:4px;">Payment Verified</div>
                    <div style="font-size:0.68rem; color:#64748B;">HMAC-SHA256 Sig</div>
                </div>
                <div style="flex:0.5; height:2px; background:{c_step4};"></div>
                <div style="display:flex; flex-direction:column; align-items:center; text-align:center; flex:1;">
                    <div style="width:26px; height:26px; border-radius:50%; background:{c_step4}; color:white; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:0.75rem;">{'✓' if is_paid else '⏳'}</div>
                    <div style="font-size:0.78rem; font-weight:700; color:#0F172A; margin-top:4px;">Kitchen Notified</div>
                    <div style="font-size:0.68rem; color:#64748B;">Order Sent to Counter</div>
                </div>
                <div style="flex:0.5; height:2px; background:{c_step5};"></div>
                <div style="display:flex; flex-direction:column; align-items:center; text-align:center; flex:1;">
                    <div style="width:26px; height:26px; border-radius:50%; background:{c_step5}; color:white; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:0.75rem;">🍽️</div>
                    <div style="font-size:0.78rem; font-weight:700; color:{c_step5_text}; margin-top:4px;">Order Preparing</div>
                    <div style="font-size:0.68rem; color:{c_step5_text};">{c_step5_sub}</div>
                </div>
            </div>
            """)

            # Failure protection notice
            render_html("""
            <div style="background:#EFF6FF; border:1px solid #BFDBFE; border-radius:10px; padding:0.9rem 1.25rem;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:1.1rem;">🛡️</span>
                    <strong style="color:#1E40AF; font-size:0.88rem;">Customer Peace-of-Mind Guarantee</strong>
                </div>
                <div style="font-size:0.8rem; color:#1E3A8A; margin-top:4px;">
                    If an issuing bank switch times out or delays: <strong>Your money was not charged twice.</strong> Any unconfirmed funds automatically reverse to your bank account within minutes.
                </div>
            </div>
            """)

        elif tab_choice == "Payments":
            st.markdown('<div style="font-size:0.88rem; font-weight:800; color:#0F172A; margin-bottom:0.75rem;">Aarav\'s Verified Transactions</div>', unsafe_allow_html=True)
            past_txns = [
                {"Payment ID": st.session_state.aarav_payment_id, "Merchant": "RAMESHSWARAM CAFE", "Order": "Masala Dosa × 2, Filter Coffee × 1", "Amount": "₹280.00", "Payment Status": "SUCCESSFUL (CAPTURED)", "Method": "UPI (Razorpay Standard)"},
                {"Payment ID": "pay_rc_10188", "Merchant": "RAMESHSWARAM CAFE", "Order": "Ghee Roast Dosa × 1, Tea × 1", "Amount": "₹160.00", "Payment Status": "SUCCESSFUL", "Method": "UPI (PhonePe)"},
                {"Payment ID": "pay_rc_10042", "Merchant": "RAMESHSWARAM CAFE", "Order": "Idli Vada Combo × 2", "Amount": "₹180.00", "Payment Status": "SUCCESSFUL", "Method": "Debit Card (HDFC)"},
            ]
            st.dataframe(pd.DataFrame(past_txns), hide_index=True, use_container_width=True)
