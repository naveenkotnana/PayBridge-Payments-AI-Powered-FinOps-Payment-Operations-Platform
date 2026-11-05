"""Merchant Portal — Razorpay-Inspired Role-Based Fintech Platform.

Features:
- Complete visibility into merchant's business transactions and settlements.
- Strict data isolation per merchant_id (e.g., Swiggy, CRED, Zomato, Zepto).
- Real-time operational alerts (SBI UPI spike, pending order fulfillment advisory).
- Bank-wise & Method-wise performance slicing.
- Settlement overview with UTR payout tracking and discrepancy management.
"""
import streamlit as st
from decimal import Decimal
from app.db.base import SessionLocal
from app.models.payments import (
    Merchant,
    PaymentTransaction,
    Settlement,
    ReconciliationDiscrepancy,
    PaymentIncident,
    IncidentMerchant,
)


def _render_merchant_overview(merchant, txns, pending):
    """Render Merchant Overview KPI Cards & Profile."""
    captured = [t for t in txns if t.status == "CAPTURED"]
    failed = [t for t in txns if t.status == "FAILED"]

    gmv = sum([Decimal(str(t.amount)) for t in captured], Decimal("0.00"))
    net_payout = sum([Decimal(str(t.net_amount)) for t in captured], Decimal("0.00"))
    total_fees = sum([Decimal(str(t.fee + t.tax)) for t in captured], Decimal("0.00"))

    terminal = len(captured) + len(failed)
    sr_pct = (len(captured) / terminal * 100) if terminal > 0 else 0.0

    # Overview KPI Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Captured GMV", f"₹{float(gmv):,.2f}", f"{len(captured)} Payments")
    with c2:
        st.metric("Success Rate", f"{sr_pct:.1f}%", f"{len(failed)} Failed")
    with c3:
        st.metric("Pending Verification", len(pending), "Awaiting Bank Confirmation")
    with c4:
        st.metric("Net Merchant Payout", f"₹{float(net_payout):,.2f}", f"-₹{float(total_fees):,.2f} Fees & Tax")

    if pending:
        st.warning(
            f"⚠️ **Fulfillment Advisory:** There are currently **{len(pending)} pending payment(s)**. "
            "**Do NOT dispatch goods or fulfill orders** for pending transactions until confirmed."
        )

    st.markdown("### Merchant Profile Details")
    if merchant:
        p1, p2, p3, p4 = st.columns(4)
        p1.write(f"**Merchant ID:** `{merchant.merchant_id}`")
        p2.write(f"**Settlement Cycle:** `{merchant.settlement_cycle}`")
        p3.write(f"**Pricing Plan:** `{merchant.pricing_plan}`")
        p4.write(f"**Risk Tier:** `{merchant.risk_tier}`")


def _render_merchant_transactions(txns):
    """Render Merchant Scoped Transactions Table."""
    st.markdown("### Merchant Transaction Stream")
    if txns:
        records = []
        for t in txns:
            records.append({
                "Payment ID": t.payment_id,
                "Customer": t.customer_id or "Anonymous Buyer",
                "Gross Amount": f"₹{float(t.amount):,.2f}",
                "MDR Fee": f"₹{float(t.fee):,.2f}",
                "Tax (GST)": f"₹{float(t.tax):,.2f}",
                "Net Payout": f"₹{float(t.net_amount):,.2f}",
                "Method": t.method,
                "Bank": t.bank or "—",
                "Status": t.status,
                "Timestamp": t.created_at.strftime("%Y-%m-%d %H:%M:%S") if t.created_at else "—",
                "Error Code": t.error_code or "—",
            })
        st.dataframe(records, use_container_width=True)
    else:
        st.info("No transaction records found for this merchant.")


def _render_merchant_alerts(db, merchant_id, pending):
    """Render Merchant Operational Alerts & Fulfillment Advisories."""
    st.markdown("### Active Merchant Alerts & Fulfillment Advisories")

    # Check for SBI UPI spike or active incidents affecting this merchant
    incidents = (
        db.query(PaymentIncident, IncidentMerchant.failed_amount)
        .join(IncidentMerchant, PaymentIncident.incident_id == IncidentMerchant.incident_id)
        .filter(IncidentMerchant.merchant_id == merchant_id)
        .all()
    )

    # High pending volume advisory
    if pending:
        st.markdown(f"""
        <div style="background:#FFFBEB; border-left:4px solid #D97706; padding:14px 18px; border-radius:8px; margin-bottom:14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <strong style="color:#B45309; font-size:1rem;">⚠️ HIGH PENDING VOLUME DETECTED ({len(pending)} Orders)</strong>
                <span class="fintech-badge badge-high">FULFILLMENT HOLD</span>
            </div>
            <div style="font-size:0.85rem; color:#451A03; margin-top:6px; line-height:1.5;">
                Issuing banks are experiencing confirmation webhook delays. <b>Advisory:</b> Do not fulfill pending orders or cancel shipments yet.
                The gateway hub will auto-reconcile transactions within 15 minutes.
            </div>
        </div>
        """, unsafe_allow_html=True)

    if incidents:
        for inc, exp in incidents:
            st.markdown(f"""
            <div style="background:#FEF2F2; border-left:4px solid #DC2626; padding:14px 18px; border-radius:8px; margin-bottom:14px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <strong style="color:#991B1B; font-size:1rem;">🚨 {inc.title}</strong>
                    <span class="fintech-badge badge-critical">{inc.severity} SEVERITY</span>
                </div>
                <div style="font-size:0.85rem; color:#450A0A; margin-top:6px; line-height:1.5;">
                    <b>Impacted Bank:</b> {inc.affected_banks} • <b>Method:</b> {inc.affected_methods}<br>
                    <b>Your Estimated Exposure:</b> ₹{float(exp):,.2f}<br>
                    <b>Incident Status:</b> {inc.status} • <b>Detected At:</b> {inc.detected_at.strftime('%Y-%m-%d %H:%M') if inc.detected_at else '—'}
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("✅ No critical bank outages or settlement interruptions currently impacting your account.")


def _render_merchant_analytics(txns):
    """Render Method and Bank Breakdown Analytics."""
    st.markdown("### Performance & Rail Slicing")

    # Method breakdown
    method_counts = {}
    for t in txns:
        method_counts[t.method] = method_counts.get(t.method, 0) + 1

    # Bank breakdown
    bank_sr = {}
    for t in txns:
        if t.bank:
            if t.bank not in bank_sr:
                bank_sr[t.bank] = {"total": 0, "captured": 0}
            bank_sr[t.bank]["total"] += 1
            if t.status == "CAPTURED":
                bank_sr[t.bank]["captured"] += 1

    col_a, col_b = st.columns(2)
    with col_a:
        st.write("**Payment Methods Distribution:**")
        st.json(method_counts)
    with col_b:
        st.write("**Bank-wise Success Rates:**")
        bank_display = {}
        for b, v in bank_sr.items():
            sr = (v["captured"] / v["total"] * 100) if v["total"] > 0 else 0
            bank_display[b] = f"{sr:.1f}% ({v['captured']}/{v['total']})"
        st.json(bank_display)


def _render_merchant_settlements(db, merchant_id):
    """Render Merchant Settlements, UTR references and Discrepancies."""
    st.markdown("### Merchant Payouts & Settlement Batches")
    settlements = (
        db.query(Settlement)
        .filter(Settlement.merchant_id == merchant_id)
        .order_by(Settlement.settlement_date.desc())
        .all()
    )

    discrepancies = (
        db.query(ReconciliationDiscrepancy)
        .filter(ReconciliationDiscrepancy.merchant_id == merchant_id)
        .all()
    )

    settled_sum = sum([Decimal(str(s.net_payout)) for s in settlements if s.status == "SETTLED"], Decimal("0.00"))
    pending_settle_sum = sum([Decimal(str(s.net_payout)) for s in settlements if s.status == "PENDING"], Decimal("0.00"))

    s_col1, s_col2, s_col3 = st.columns(3)
    with s_col1:
        st.metric("Total Settled (UTR Disbursed)", f"₹{float(settled_sum):,.2f}")
    with s_col2:
        st.metric("Pending Payout Batch", f"₹{float(pending_settle_sum):,.2f}")
    with s_col3:
        st.metric("Open Discrepancies", len(discrepancies))

    if settlements:
        s_records = []
        for s in settlements:
            s_records.append({
                "Settlement ID": s.settlement_id,
                "Date": str(s.settlement_date),
                "Gross Volume": f"₹{float(s.gross_amount):,.2f}",
                "Fees Deducted": f"₹{float(s.fee_deducted):,.2f}",
                "Net Payout": f"₹{float(s.net_payout):,.2f}",
                "Status": s.status,
                "Bank UTR Number": s.utr_number or "Awaiting Dispatch",
            })
        st.dataframe(s_records, use_container_width=True)
    else:
        st.info("No settlements processed yet for this billing cycle.")


def render_merchant_portal(merchant_id: str = "mid_swiggy_01", page: str = "Merchant Overview"):
    st.markdown("""
    <div style="margin-bottom:1.5rem;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <span class="fintech-badge badge-medium" style="margin-bottom:6px; display:inline-block;">WORKSPACE 2 • MERCHANT PORTAL</span>
                <h1 style="font-size:1.85rem; font-weight:800; color:#0A142F; margin:0;">
                    Merchant Operations & Payment Intelligence
                </h1>
                <p style="color:#64748B; font-size:0.92rem; margin-top:4px;">
                    Monitor incoming payments, fulfillment advisories, settlement payouts, and bank performance.
                </p>
            </div>
            <div style="text-align:right;">
                <span class="fintech-badge badge-low" style="font-weight:700;">
                    LIVE PRODUCTION INTEGRATION
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with SessionLocal() as db:
        # Load merchants for selector
        merchants = db.query(Merchant).all()
        m_dict = {m.merchant_id: f"{m.name} ({m.business_category})" for m in merchants}

        if m_dict:
            sel_mid = st.selectbox(
                "Active Merchant Account (Data Scoped):",
                options=list(m_dict.keys()),
                format_func=lambda x: m_dict[x],
                index=list(m_dict.keys()).index(merchant_id) if merchant_id in m_dict else 0,
            )
            merchant_id = sel_mid

        merchant = db.query(Merchant).filter(Merchant.merchant_id == merchant_id).first()

        # Query Merchant Scoped Data (STRICT ISOLATION)
        txns = (
            db.query(PaymentTransaction)
            .filter(PaymentTransaction.merchant_id == merchant_id)
            .order_by(PaymentTransaction.created_at.desc())
            .all()
        )

        pending = [t for t in txns if t.status in ("PENDING", "AUTHORIZED")]

        # Route directly if page is specified from sidebar navigation
        if "Overview" in page:
            _render_merchant_overview(merchant, txns, pending)
        elif "Transaction" in page:
            _render_merchant_transactions(txns)
        elif "Alert" in page or "Advisory" in page:
            _render_merchant_alerts(db, merchant_id, pending)
        elif "Analytic" in page:
            _render_merchant_analytics(txns)
        elif "Settlement" in page:
            _render_merchant_settlements(db, merchant_id)
        else:
            # Fallback to full tabs view
            tab_overview, tab_txns, tab_alerts, tab_analytics, tab_settlements = st.tabs([
                "📊 Merchant Overview",
                "💳 Transactions",
                "🚨 Merchant Alerts & Advisories",
                "📈 Payment Analytics",
                "💰 Settlement Overview",
            ])
            with tab_overview:
                _render_merchant_overview(merchant, txns, pending)
            with tab_txns:
                _render_merchant_transactions(txns)
            with tab_alerts:
                _render_merchant_alerts(db, merchant_id, pending)
            with tab_analytics:
                _render_merchant_analytics(txns)
            with tab_settlements:
                _render_merchant_settlements(db, merchant_id)
