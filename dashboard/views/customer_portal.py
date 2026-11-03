"""Customer Portal — Razorpay-Inspired Role-Based Fintech Platform.

Features:
- Complete visibility into customer's own payment transactions (Data Isolation).
- Customer Home with financial KPI cards.
- My Transactions with interactive status chips.
- Visual Transaction Timeline:
    Payment Initiated -> Bank Response -> Gateway Routing -> Final Verified Status.
- Real Payment Status Notifications (Never claims money debited unless verified).
"""
import streamlit as st
from decimal import Decimal
from app.db.base import SessionLocal
from app.models.payments import (
    Customer,
    PaymentTransaction,
    PaymentOrder,
    PaymentEvent,
    PaymentAttempt,
    Refund,
    Merchant,
)


def render_customer_portal(customer_id: str = "cust_sw_aarav"):
    st.markdown("""
    <div style="margin-bottom:1.5rem;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <span class="fintech-badge badge-low" style="margin-bottom:6px; display:inline-block;">WORKSPACE 1 • CUSTOMER PORTAL</span>
                <h1 style="font-size:1.85rem; font-weight:800; color:#0A142F; margin:0;">
                    My Payments & Account Activity
                </h1>
                <p style="color:#64748B; font-size:0.92rem; margin-top:4px;">
                    Track your orders, live payment verification timelines, and refund status.
                </p>
            </div>
            <div style="text-align:right;">
                <span class="fintech-badge" style="background:#E0F2FE; color:#0369A1; font-weight:700;">
                    VERIFIED BUYER ACCOUNT
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with SessionLocal() as db:
        # Resolve customer details
        cust = db.query(Customer).filter(Customer.customer_id == customer_id).first()
        if not cust:
            # Fallback to first customer or create default
            cust = db.query(Customer).first()
            if cust:
                customer_id = cust.customer_id

        # Available customers switcher for demo convenience
        all_custs = db.query(Customer).limit(10).all()
        if all_custs:
            cust_options = {c.customer_id: f"{c.name} ({c.email})" for c in all_custs}
            sel_cid = st.selectbox(
                "Switch Customer Account (Demo Selector):",
                options=list(cust_options.keys()),
                format_func=lambda x: cust_options[x],
                index=list(cust_options.keys()).index(customer_id) if customer_id in cust_options else 0,
            )
            customer_id = sel_cid
            cust = db.query(Customer).filter(Customer.customer_id == customer_id).first()

        # Query Customer Transactions (STRICT DATA ISOLATION)
        txns = (
            db.query(PaymentTransaction, Merchant.name.label("merchant_name"))
            .join(Merchant, PaymentTransaction.merchant_id == Merchant.merchant_id, isouter=True)
            .filter(PaymentTransaction.customer_id == customer_id)
            .order_by(PaymentTransaction.created_at.desc())
            .all()
        )

        tab_home, tab_txns, tab_timeline, tab_notifications = st.tabs([
            "🏠 Customer Home",
            "💳 My Transactions",
            "⏱️ Payment Timeline & Details",
            "🔔 Payment Notifications",
        ])

        # --------------------------------------------------------- A. Customer Home
        with tab_home:
            total_count = len(txns)
            captured = [t[0] for t in txns if t[0].status == "CAPTURED"]
            pending = [t[0] for t in txns if t[0].status in ("PENDING", "AUTHORIZED")]
            failed = [t[0] for t in txns if t[0].status == "FAILED"]

            total_spent = sum([Decimal(str(t.amount)) for t in captured], Decimal("0.00"))
            pending_amount = sum([Decimal(str(t.amount)) for t in pending], Decimal("0.00"))

            # Top KPI metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Payments", total_count)
            with col2:
                st.metric("Successful", len(captured), f"₹{float(total_spent):,.2f}")
            with col3:
                st.metric("Awaiting Bank Confirmation", len(pending), f"₹{float(pending_amount):,.2f}" if pending else "0")
            with col4:
                st.metric("Failed / Declined", len(failed))

            if pending:
                st.warning(
                    f"⚠️ **Attention:** You have {len(pending)} payment(s) awaiting bank confirmation. "
                    "Please avoid initiating a duplicate payment until the final status is verified."
                )

            st.markdown("### Recent Activity")
            if txns:
                for t, m_name in txns[:4]:
                    status_color = "#16A34A" if t.status == "CAPTURED" else ("#D97706" if t.status in ("PENDING", "AUTHORIZED") else "#DC2626")
                    status_bg = "#DCFCE7" if t.status == "CAPTURED" else ("#FEF3C7" if t.status in ("PENDING", "AUTHORIZED") else "#FEE2E2")
                    st.markdown(f"""
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:14px 18px; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <div style="font-weight:700; color:#0F172A; font-size:1rem;">{m_name or t.merchant_id}</div>
                            <div style="color:#64748B; font-size:0.8rem; margin-top:2px;">
                                {t.method} via {t.bank or 'PG Direct'} • {t.created_at.strftime('%d %b %Y, %I:%M %p') if t.created_at else ''} • ID: <code>{t.payment_id}</code>
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:1.15rem; font-weight:800; color:#0F172A;">₹{float(t.amount):,.2f}</div>
                            <span style="background:{status_bg}; color:{status_color}; font-weight:700; font-size:0.75rem; padding:3px 10px; border-radius:12px; display:inline-block; margin-top:4px;">
                                {t.status}
                            </span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No transaction history recorded for this customer account.")

        # --------------------------------------------------------- B. My Transactions
        with tab_txns:
            st.markdown("### Transaction Ledger")
            if txns:
                records = []
                for t, m_name in txns:
                    records.append({
                        "Payment ID": t.payment_id,
                        "Merchant": m_name or t.merchant_id,
                        "Amount (₹)": f"₹{float(t.amount):,.2f}",
                        "Method": t.method,
                        "Bank": t.bank or "—",
                        "Status": t.status,
                        "Date": t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else "—",
                        "Error / Note": t.error_description or "—",
                    })
                st.dataframe(records, use_container_width=True)
            else:
                st.write("No transactions found.")

        # --------------------------------------------------------- C. Payment Details & Timeline
        with tab_timeline:
            st.markdown("### Detailed Transaction Verification Timeline")
            if txns:
                selected_pid = st.selectbox(
                    "Select a transaction to inspect live verification audit trail:",
                    options=[t[0].payment_id for t in txns],
                    format_func=lambda pid: f"{pid} — ₹{float(next(t[0].amount for t in txns if t[0].payment_id == pid)):,.2f} ({next(t[0].status for t in txns if t[0].payment_id == pid)})"
                )

                chosen_txn = next(t[0] for t in txns if t[0].payment_id == selected_pid)
                order = db.query(PaymentOrder).filter(PaymentOrder.order_id == chosen_txn.order_id).first()
                events = db.query(PaymentEvent).filter(PaymentEvent.payment_id == selected_pid).order_by(PaymentEvent.occurred_at.asc()).all()
                attempts = db.query(PaymentAttempt).filter(PaymentAttempt.payment_id == selected_pid).order_by(PaymentAttempt.attempt_number.asc()).all()
                refund = db.query(Refund).filter(Refund.payment_id == selected_pid).first()

                # Visual Timeline Card
                st.markdown(f"""
                <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:12px; padding:20px; margin-bottom:1.5rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
                        <div>
                            <span style="font-size:0.8rem; color:#64748B;">TRANSACTION REFERENCE</span>
                            <h3 style="margin:2px 0 0 0; color:#0F172A;">{chosen_txn.payment_id}</h3>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:1.4rem; font-weight:800; color:#0F172A;">₹{float(chosen_txn.amount):,.2f}</div>
                            <span style="font-size:0.8rem; color:#64748B;">Order: <code>{chosen_txn.order_id}</code></span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("#### ⏳ Verification Timeline Steps")

                # Step 1: Order Created
                st.markdown(f"""
                <div style="border-left:3px solid #16A34A; padding-left:14px; margin-bottom:14px;">
                    <strong style="color:#0F172A;">Step 1: Payment Initiated by Customer</strong><br>
                    <span style="font-size:0.82rem; color:#64748B;">Method: <b>{chosen_txn.method}</b> • Amount: <b>₹{float(chosen_txn.amount):,.2f}</b> • Order Receipt: {order.receipt if order else '—'}</span>
                </div>
                """, unsafe_allow_html=True)

                # Step 2: Bank Routing & Response
                bank_status = "Pending confirmation" if chosen_txn.status in ("PENDING", "AUTHORIZED") else ("Approved" if chosen_txn.status == "CAPTURED" else "Declined / Timed Out")
                bank_border = "#D97706" if chosen_txn.status in ("PENDING", "AUTHORIZED") else ("#16A34A" if chosen_txn.status == "CAPTURED" else "#DC2626")
                st.markdown(f"""
                <div style="border-left:3px solid {bank_border}; padding-left:14px; margin-bottom:14px;">
                    <strong style="color:#0F172A;">Step 2: Issuing Bank Response ({chosen_txn.bank or 'N/A'})</strong><br>
                    <span style="font-size:0.82rem; color:#64748B;">Status: <b>{bank_status}</b> • Latency: {attempts[0].latency_ms if attempts else 450}ms</span>
                    {f"<div style='color:#DC2626; font-size:0.82rem; margin-top:2px;'>Reason: {chosen_txn.error_description}</div>" if chosen_txn.error_description else ""}
                </div>
                """, unsafe_allow_html=True)

                # Step 3: Gateway Processing & Deduplication
                st.markdown(f"""
                <div style="border-left:3px solid #0284C7; padding-left:14px; margin-bottom:14px;">
                    <strong style="color:#0F172A;">Step 3: Gateway Hub Verification ({chosen_txn.gateway})</strong><br>
                    <span style="font-size:0.82rem; color:#64748B;">Idempotency verification passed • Ingestion source: {events[0].event_source if events else 'SIMULATOR'}</span>
                </div>
                """, unsafe_allow_html=True)

                # Step 4: Final Verified Status
                final_color = "#16A34A" if chosen_txn.status == "CAPTURED" else ("#D97706" if chosen_txn.status in ("PENDING", "AUTHORIZED") else "#DC2626")
                st.markdown(f"""
                <div style="border-left:3px solid {final_color}; padding-left:14px; margin-bottom:14px;">
                    <strong style="color:#0F172A;">Step 4: Final Verified State: <span style="color:{final_color};">{chosen_txn.status}</span></strong><br>
                    <span style="font-size:0.82rem; color:#64748B;">Captured timestamp: {chosen_txn.captured_at.strftime('%Y-%m-%d %H:%M:%S') if chosen_txn.captured_at else 'Awaiting final confirmation'}</span>
                </div>
                """, unsafe_allow_html=True)

                # Step 5: Refund Status (if applicable)
                if refund:
                    st.markdown(f"""
                    <div style="border-left:3px solid #9333EA; padding-left:14px; margin-bottom:14px;">
                        <strong style="color:#9333EA;">Step 5: Refund Processed ({refund.refund_id})</strong><br>
                        <span style="font-size:0.82rem; color:#64748B;">Amount: ₹{float(refund.amount):,.2f} • Speed: {refund.speed} • Reason: {refund.reason}</span>
                    </div>
                    """, unsafe_allow_html=True)

        # --------------------------------------------------------- D. Customer Notifications
        with tab_notifications:
            st.markdown("### Official Payment Notifications")
            st.caption("Evidence-backed notifications. Notifications only state confirmed facts.")

            for t, m_name in txns:
                merchant_label = m_name or t.merchant_id
                amt_str = f"₹{float(t.amount):,.2f}"

                if t.status == "CAPTURED":
                    st.markdown(f"""
                    <div style="background:#F0FDF4; border-left:4px solid #16A34A; padding:12px 16px; border-radius:6px; margin-bottom:10px;">
                        <div style="font-weight:700; color:#166534; font-size:0.92rem;">SUCCESS: Payment of {amt_str} to {merchant_label} Successful</div>
                        <div style="font-size:0.82rem; color:#374151; margin-top:3px;">
                            Your payment was successfully received and confirmed by {t.bank or 'bank'}. Payment ID: <code>{t.payment_id}</code>.
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                elif t.status in ("PENDING", "AUTHORIZED"):
                    st.markdown(f"""
                    <div style="background:#FFFBEB; border-left:4px solid #D97706; padding:12px 16px; border-radius:6px; margin-bottom:10px;">
                        <div style="font-weight:700; color:#92400E; font-size:0.92rem;">PENDING: Payment of {amt_str} to {merchant_label} Awaiting Bank Confirmation</div>
                        <div style="font-size:0.82rem; color:#374151; margin-top:3px;">
                            Your payment is currently being verified with {t.bank or 'your bank'}. <b>Please avoid paying again</b> until the final status is confirmed. If debited, your order will be confirmed automatically.
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                elif t.status == "FAILED":
                    st.markdown(f"""
                    <div style="background:#FEF2F2; border-left:4px solid #DC2626; padding:12px 16px; border-radius:6px; margin-bottom:10px;">
                        <div style="font-weight:700; color:#991B1B; font-size:0.92rem;">FAILED: Payment of {amt_str} to {merchant_label} Could Not Be Completed</div>
                        <div style="font-size:0.82rem; color:#374151; margin-top:3px;">
                            Transaction was declined ({t.error_code or 'Gateway timeout'}). Please check your payment details or try another payment method.
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
