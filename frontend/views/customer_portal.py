# -*- coding: utf-8 -*-
"""Customer Portal — customer-selected cafe orders and verified Razorpay checkout.

Simple, human-readable customer experience:
- Empty cart by default; total reflects only selected menu items
- Razorpay Standard Web Checkout Integration (checkout.js modal)
- Server-side HMAC-SHA256 Payment Verification
- Provider-backed payment verification and receipt
"""
from pathlib import Path
import uuid
import json
from decimal import Decimal

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from fastapi import HTTPException

from backend.app.api.checkout import (
    create_razorpay_order,
    verify_razorpay_payment,
    CreateOrderRequest,
    VerifyPaymentRequest,
)
from backend.app.core.config import settings
from backend.app.services.demo_wallet import get_wallet, pay_order
from backend.app.db.base import SessionLocal
from backend.app.models.payments import Customer, PaymentTransaction, CafeOrderItems
from backend.app.services.cafe_menu import MENU, DEFAULT_CART, SNACK_CART, price_cart
from frontend.styles import render_html

EMPTY_CART = {item_id: 0 for item_id in MENU}


def _start_cafe_cart(cart):
    if not isinstance(cart, dict) or any(item_id not in MENU for item_id in cart):
        raise ValueError("Choose items from the cafe menu.")
    normalized = {item_id: cart.get(item_id, 0) for item_id in MENU}
    if any(type(qty) is not int or not 0 <= qty <= 10 for qty in normalized.values()):
        raise ValueError("Each quantity must be a whole number from 0 to 10.")
    st.session_state.cafe_cart = normalized
    st.session_state.cafe_cart_explicitly_set = True
    st.session_state.wallet_payment_request = uuid.uuid4().hex
    st.session_state.aarav_payment_status = "PENDING"
    st.session_state.aarav_order_id = ""
    st.session_state.aarav_payment_id = ""
    st.session_state.show_razorpay_modal = False
    st.session_state.aarav_checkout_msg = None


def _render_payment_receipt(db, customer_id):
    payment_id = st.session_state.get("aarav_payment_id")
    if not payment_id:
        return
    payment = db.query(PaymentTransaction).filter(
        PaymentTransaction.payment_id == payment_id,
        PaymentTransaction.customer_id == customer_id,
        PaymentTransaction.order_id == st.session_state.get("aarav_order_id"),
        PaymentTransaction.status == "CAPTURED",
        PaymentTransaction.data_source.in_(["RAZORPAY_TEST", "REAL", "DEMO_WALLET"]),
    ).first()
    if payment is None:
        return
    simulated_wallet = payment.data_source == "DEMO_WALLET"
    st.success("Demo wallet payment successful — your order is confirmed." if simulated_wallet else "Payment successful — your order is confirmed.")
    with st.container(border=True):
        st.subheader("Payment receipt")
        amount, status, mode = st.columns(3)
        amount.metric("Amount paid", f"{payment.currency} {payment.amount:,.2f}")
        status.metric("Payment status", "Captured")
        mode.metric("Mode", "Demo wallet" if simulated_wallet else "Test payment" if payment.data_source == "RAZORPAY_TEST" else "Live payment")
        st.write("Merchant: RAMESHSWARAM CAFE")
        st.write(f"Payment reference: {payment.payment_id}")
        st.write(f"Order reference: {payment.order_id}")
        saved_items = db.get(CafeOrderItems, payment.order_id)
        receipt_items = json.loads(saved_items.items_json) if saved_items else []
        if receipt_items:
            st.dataframe(pd.DataFrame(receipt_items)[["name", "quantity", "unit_price", "subtotal"]], hide_index=True, use_container_width=True)
        st.caption("Paid using simulated wallet credit. No money moved through Razorpay." if simulated_wallet else "Confirmed by server-side signature and payment-provider verification.")
        receipt = (f"PAYBRIDGE PAYMENT RECEIPT\nMerchant: RAMESHSWARAM CAFE\n"
                   f"Amount: {payment.currency} {payment.amount:.2f}\nStatus: CAPTURED\n"
                   f"Payment reference: {payment.payment_id}\nOrder reference: {payment.order_id}\n"
                   f"Source: {payment.data_source}\n")
        receipt += "Items:\n" + "\n".join(f"{i['name']} x {i['quantity']}: INR {i['subtotal']}" for i in receipt_items)
        st.download_button("Download receipt", receipt.encode("utf-8"), file_name="payment_receipt.txt", mime="text/plain", key="download_verified_receipt")


def render_customer_portal(customer_id: str = "cust_aarav_01", page: str = "Orders"):
    """Render the simplified, human-friendly Customer Portal for Aarav with Razorpay Checkout."""
    if "cafe_cart" not in st.session_state:
        st.session_state.cafe_cart = dict(EMPTY_CART)
        st.session_state.cafe_cart_explicitly_set = False
    elif not st.session_state.get("cafe_cart_explicitly_set", False):
        # Clear the legacy preselected breakfast combo when an existing browser
        # session first loads the empty-cart version of this page.
        if st.session_state.cafe_cart == DEFAULT_CART:
            st.session_state.cafe_cart = dict(EMPTY_CART)
            for item_id in MENU:
                st.session_state.pop("cart_qty_" + item_id, None)
        else:
            st.session_state.cafe_cart_explicitly_set = True
    # Initialize session states for customer checkout
    if "aarav_payment_status" not in st.session_state:
        st.session_state.aarav_payment_status = "PENDING"
    if "aarav_order_id" not in st.session_state:
        st.session_state.aarav_order_id = ""
    if "aarav_payment_id" not in st.session_state:
        st.session_state.aarav_payment_id = ""
    if st.session_state.aarav_order_id == "order_RC10291":
        st.session_state.aarav_order_id = ""
    if st.session_state.aarav_payment_id == "pay_rc_10291":
        st.session_state.aarav_payment_id = ""
    for field, sample in [("v_pay_id", "pay_rc_10291"), ("v_ord_id", "order_RC10291")]:
        if st.session_state.get(field) == sample:
            st.session_state.pop(field, None)
    if "aarav_checkout_msg" not in st.session_state:
        st.session_state.aarav_checkout_msg = None

    with SessionLocal() as db:
        cust = db.query(Customer).filter(Customer.customer_id == customer_id).first()
        cust_name = cust.name if cust else "Aarav"
        _render_payment_receipt(db, customer_id)

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
                <div style="font-size:0.88rem; font-weight:700; color:#059669;">Verified payment status</div>
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

            st.subheader("Choose your cafe order")
            combo1, combo2 = st.columns(2)
            for col, title, preset in [(combo1, "Breakfast combo · ₹280", DEFAULT_CART), (combo2, "Snack combo · ₹150", SNACK_CART)]:
                with col:
                    if st.button(title, key="preset_" + title, use_container_width=True):
                        _start_cafe_cart(dict(preset))
                        for item_id in MENU:
                            st.session_state["cart_qty_" + item_id] = preset.get(item_id, 0)
                        st.rerun()
            st.caption("Your cart starts empty. Choose an optional combo or set item quantities, then click Update cart. Prices are calculated on the server.")
            with st.form("cafe_cart_form"):
                chosen = {}
                columns = st.columns(3)
                for i, (item_id, (name, price)) in enumerate(MENU.items()):
                    with columns[i % 3]:
                        chosen[item_id] = st.number_input(f"{name} · ₹{price:.0f}", min_value=0, max_value=10, value=st.session_state.cafe_cart.get(item_id, 0), step=1, key="cart_qty_" + item_id)
                apply_cart = st.form_submit_button("Update cart", type="primary")
            if apply_cart:
                try:
                    _start_cafe_cart(chosen)
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
            cart_has_items = any(st.session_state.cafe_cart.values())
            if cart_has_items:
                cart_items, cart_total = price_cart(st.session_state.cafe_cart)
                items_html = "<br>".join(f"• <strong>{item['name']}</strong> × {item['quantity']} — ₹{item['subtotal']}" for item in cart_items)
            else:
                cart_items, cart_total = [], Decimal("0.00")
                items_html = "Your cart is empty. Choose a combo or add menu items above."
            display_order = (st.session_state.aarav_order_id or st.session_state.get("wallet_payment_request", "NEW"))[-8:].upper()

            is_paid = st.session_state.aarav_payment_status == "PAID"

            badge_text = "✅ Payment Successful" if is_paid else (f"⏳ Payment Pending (₹{cart_total:,.2f})" if cart_has_items else "🛒 Cart Empty")
            badge_bg = "#ECFDF5" if is_paid else "#FEF3C7"
            badge_color = "#059669" if is_paid else "#B45309"
            kitchen_status = "Preparing Your Food" if is_paid else ("Awaiting Payment Confirmation" if cart_has_items else "Add items to start an order")
            kitchen_icon = "🍽️" if is_paid else ("⏳" if cart_has_items else "🛒")
            kitchen_sub = "Estimated pickup: 8-10 mins" if is_paid else ("Order will be sent to kitchen upon payment" if cart_has_items else "No items selected")

            # Active Order Card
            render_html(f"""
            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:1.4rem; box-shadow:0 2px 6px rgba(0,0,0,0.02); margin-bottom:1.5rem;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem; padding-bottom:0.75rem; border-bottom:1px solid #F1F5F9;">
                    <div>
                        <div style="font-size:0.75rem; font-weight:700; color:#64748B; text-transform:uppercase;">Current Order • RAMESHSWARAM CAFE</div>
                        <h2 style="font-size:1.25rem; font-weight:800; color:#0F172A; margin:2px 0;">Order #{display_order}</h2>
                    </div>
                    <span style="font-size:0.82rem; font-weight:700; background:{badge_bg}; color:{badge_color}; padding:4px 12px; border-radius:999px;">
                        {badge_text}
                    </span>
                </div>
                <div style="display:grid; grid-template-columns: 1.5fr 1fr; gap:20px;">
                    <div>
                        <div style="font-size:0.82rem; font-weight:700; color:#475569; text-transform:uppercase; margin-bottom:6px;">Items Ordered:</div>
                        <div style="font-size:0.92rem; color:#1E293B; line-height:1.6;">
                            {items_html}
                        </div>
                        <div style="margin-top:12px; font-size:1.15rem; font-weight:800; color:#0F172A;">
                            Total: ₹{cart_total:,.2f}
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
            st.markdown('<div style="font-size:0.85rem; font-weight:800; color:#475569; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.75rem;">Payment options</div>', unsafe_allow_html=True)

            methods = (["PayBridge Wallet (demo)"] if settings.DEMO_MODE else []) + ["UPI (Razorpay)", "Card / Wallet (Razorpay)"]
            payment_method = st.radio("Payment method", methods, horizontal=True, key="customer_payment_method")
            use_wallet = payment_method == "PayBridge Wallet (demo)"
            if use_wallet:
                wallet = get_wallet(db, customer_id)
                st.metric("Wallet balance · simulated INR", f"₹{wallet.balance:,.2f}")
                st.caption(f"Starts with ₹50,000 in demo credit. Pay once to debit ₹{cart_total:,.2f}, save the payment and show your receipt. This wallet is separate from Razorpay.")
            else:
                st.caption("Razorpay UPI and external wallets depend on the methods enabled for your account. Test keys use simulated provider payments.")
            if "wallet_payment_request" not in st.session_state:
                st.session_state.wallet_payment_request = uuid.uuid4().hex

            c_col1, c_col2 = st.columns([1.5, 1.2])

            with c_col1:
                if st.button(f"💰 Pay ₹{cart_total:,.2f} from Wallet" if use_wallet else f"💳 Pay ₹{cart_total:,.2f} via Razorpay", key="btn_open_rzp_modal", type="primary", use_container_width=True, disabled=is_paid or not cart_has_items):
                    if use_wallet:
                        try:
                            paid = pay_order(db, customer_id, st.session_state.wallet_payment_request, cart=st.session_state.cafe_cart)
                            st.session_state.aarav_order_id = paid.order_id
                            st.session_state.aarav_payment_id = paid.payment_id
                            st.session_state.aarav_payment_status = "PAID"
                            st.session_state.show_razorpay_modal = False
                            st.session_state.aarav_checkout_msg = {"type": "success", "text": "Demo wallet payment saved. Your receipt is displayed above."}
                        except Exception as exc:
                            st.session_state.aarav_checkout_msg = {"type": "error", "text": str(exc)}
                        st.rerun()
                    # Call backend create-order endpoint to generate authentic order_id
                    try:
                        ord_res = create_razorpay_order(CreateOrderRequest(
                            amount=int(cart_total * 100),
                            currency="INR",
                            items=st.session_state.cafe_cart,
                            receipt="RC-" + st.session_state.wallet_payment_request[:20],
                            merchant_id="mid_rameshwaram_01",
                            customer_id=customer_id
                        ), db=db)
                        st.session_state.aarav_order_id = ord_res.order_id
                        st.session_state.aarav_checkout_key = ord_res.key_id
                        st.session_state.show_razorpay_modal = True
                        st.session_state.aarav_checkout_msg = {
                            "type": "info",
                            "text": f"Razorpay order initialized ({ord_res.order_id}). Complete payment in the modal."
                        }
                    except Exception as err:
                        st.session_state.aarav_checkout_msg = {
                            "type": "error",
                            "text": f"Failed to create Razorpay order: {err}"
                        }
                    st.rerun()

            with c_col2:
                if st.button("🔄 Reset Order State", key="btn_reset_order_state", use_container_width=True):
                    st.session_state.aarav_payment_status = "PENDING"
                    st.session_state.wallet_payment_request = uuid.uuid4().hex
                    st.session_state.aarav_order_id = ""
                    st.session_state.aarav_payment_id = ""
                    st.session_state.show_razorpay_modal = False
                    st.session_state.aarav_checkout_msg = {
                        "type": "info",
                        "text": "Order reset to PENDING. Ready to initiate checkout."
                    }
                    st.rerun()

            # If user clicked the Razorpay modal button, inject the Standard Checkout checkout.js script
            if st.session_state.get("show_razorpay_modal", False) and not use_wallet:
                checkout = components.declare_component("paybridge_razorpay_checkout", path=str(Path(__file__).resolve().parents[1] / "payment_checkout"))
                response = checkout(key_id=st.session_state.get("aarav_checkout_key", ""), order_id=st.session_state.aarav_order_id, amount=int(cart_total * 100), description="; ".join(f"{item['name']} x {item['quantity']}" for item in cart_items), preferred_method="upi" if payment_method == "UPI (Razorpay)" else "all", key="checkout_" + st.session_state.aarav_order_id, default=None)
                if isinstance(response, dict) and response.get("razorpay_payment_id"):
                    attempt = (response.get("razorpay_order_id"), response.get("razorpay_payment_id"), response.get("razorpay_signature"))
                    if st.session_state.get("last_checkout_verification") != attempt:
                        st.session_state.last_checkout_verification = attempt
                        try:
                            if response.get("razorpay_order_id") != st.session_state.aarav_order_id:
                                raise HTTPException(400, "Checkout result does not match the active order")
                            verified = verify_razorpay_payment(VerifyPaymentRequest(**response), db=db)
                            st.session_state.aarav_payment_status = "PAID"
                            st.session_state.aarav_payment_id = verified.payment_id
                            st.session_state.show_razorpay_modal = False
                            st.session_state.aarav_checkout_msg = {"type": "success", "text": "Payment verified and saved. Your order is confirmed."}
                        except HTTPException as exc:
                            st.session_state.aarav_checkout_msg = {"type": "error", "text": f"Payment is not confirmed: {exc.detail}. Retry verification of this payment before making another payment."}
                        except Exception:
                            st.session_state.aarav_checkout_msg = {"type": "error", "text": "Payment verification could not finish. Verify the existing payment before paying again."}
                        st.rerun()
                    if st.session_state.aarav_payment_status != "PAID" and st.button("Retry verification of this payment", key="retry_checkout_verification"):
                        st.session_state.pop("last_checkout_verification", None)
                        st.rerun()

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
                    <div style="font-size:0.68rem; color:#64748B;">{"Demo wallet" if use_wallet else "Razorpay Standard"}</div>
                </div>
                <div style="flex:0.5; height:2px; background:{c_step4};"></div>
                <div style="display:flex; flex-direction:column; align-items:center; text-align:center; flex:1;">
                    <div style="width:26px; height:26px; border-radius:50%; background:{c_step4}; color:white; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:0.75rem;">{'✓' if is_paid else '⏳'}</div>
                    <div style="font-size:0.78rem; font-weight:700; color:#0F172A; margin-top:4px;">Payment Verified</div>
                    <div style="font-size:0.68rem; color:#64748B;">{"Wallet debit saved" if use_wallet else "HMAC-SHA256 Sig"}</div>
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
                    <strong style="color:#1E40AF; font-size:0.88rem;">Payment status guidance</strong>
                </div>
                <div style="font-size:0.8rem; color:#1E3A8A; margin-top:4px;">
                    If an issuing bank switch times out or delays: <strong>Check your payment status before retrying.</strong> Reversal timing depends on the bank and provider; contact support if a debit remains unconfirmed.
                </div>
            </div>
            """)

        elif tab_choice == "Payments":
            st.markdown('<div style="font-size:0.88rem; font-weight:800; color:#0F172A; margin-bottom:0.75rem;">Aarav\'s Verified Transactions</div>', unsafe_allow_html=True)
            transactions = db.query(PaymentTransaction).filter(PaymentTransaction.customer_id == customer_id).order_by(PaymentTransaction.created_at.desc()).limit(100).all()
            if transactions:
                st.dataframe(pd.DataFrame([{"Payment ID": t.payment_id, "Order": t.order_id, "Merchant": t.merchant_id, "Amount": float(t.amount), "Payment Status": t.status, "Method": t.method, "Source": t.data_source} for t in transactions]), hide_index=True, use_container_width=True)
            else:
                st.info("No stored payments for this customer yet. Completed and verified payments will appear here.")
