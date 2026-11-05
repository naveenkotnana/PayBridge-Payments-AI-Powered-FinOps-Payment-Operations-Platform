"""End-to-End SBI UPI Demonstration Workflow.

Demonstrates the full fintech lifecycle:
1. Customer initiates ₹2,500 payment via SBI UPI.
2. Delayed bank response -> status marked PENDING.
3. Customer Portal reflects pending confirmation.
4. Merchant Portal advises against order fulfillment.
5. Admin Incident Command detects SBI UPI spike and groups incident.
6. AI Investigation evaluates evidence and recommends mitigation.
7. Final verification arrives -> updates Customer, Merchant, Admin, and logs audit record.
"""
import streamlit as st
import datetime as dt
from backend.app.db.base import SessionLocal
from backend.app.models.payments import (
    PaymentTransaction,
)
from backend.app.models.ops import AuditLog


def render_sbi_upi_demo(role: str = "ADMIN"):
    st.markdown("""
    <div style="margin-bottom:1.5rem;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <span class="fintech-badge badge-critical" style="margin-bottom:6px; display:inline-block;">INTERACTIVE DEMO • FINTECH INTERVIEW SHOWCASE</span>
                <h1 style="font-size:1.85rem; font-weight:800; color:#0A142F; margin:0;">
                    Live SBI UPI Pending Lifecycle Demonstration
                </h1>
                <p style="color:#64748B; font-size:0.92rem; margin-top:4px;">
                    Experience how PayBridge handles a real-world ₹2,500 SBI UPI bank delay across all four platform personas.
                </p>
            </div>
            <div style="text-align:right;">
                <span class="fintech-badge badge-high" style="font-weight:700;">
                    6-STEP VERIFICATION JOURNEY
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with SessionLocal() as db:
        txn = db.query(PaymentTransaction).filter(PaymentTransaction.payment_id == "pay_sbi_upi_demo_01").first()

        # Step progression tabs
        step = st.radio(
            "Select Journey Milestone to Inspect:",
            [
                "Step 1: Customer Attempt & Initial Delay",
                "Step 2: Customer Portal View",
                "Step 3: Merchant Fulfillment Advisory",
                "Step 4: Admin Incident Correlation",
                "Step 5: AI Root-Cause Investigation",
                "Step 6: Final Verification Webhook & Resolution",
            ],
            horizontal=True,
        )

        st.markdown("---")

        if step.startswith("Step 1"):
            st.subheader("1. Payment Initiation & SBI Bank Switch Timeout")
            st.markdown("""
            - **Customer:** Aarav Sharma (`cust_sw_aarav`)
            - **Merchant:** Swiggy India (`mid_swiggy_01`)
            - **Amount:** ₹2,500.00
            - **Rail:** UPI (VPA: `aarav@oksbi`)
            - **Issuing Bank:** State Bank of India (SBI)
            - **Gateway:** Razorpay Direct Switch
            """)
            st.warning("""
            ⏱️ **Observed Behaviour:** Customer entered UPI PIN on their mobile application.
            The issuing bank debited the customer's account, but the NPCI acknowledgment webhook timed out (>14,500ms).
            **Initial Platform State:** Marked as **PENDING / UNKNOWN**.
            """)

        elif step.startswith("Step 2"):
            st.subheader("2. Customer Portal Experience")
            st.info("""
            **Customer Advisory Shown:**
            "PENDING: Payment of ₹2,500.00 to Swiggy India Awaiting Bank Confirmation.
            Your payment is currently being verified with SBI. **Please avoid paying again** until the status is verified.
            If debited, your order will be confirmed automatically."
            """)
            st.write("✅ **Evidence Rule Upheld:** Platform never claims money is debited or refunded until verified.")

        elif step.startswith("Step 3"):
            st.subheader("3. Merchant Operations & Fulfillment Advisory")
            st.warning("""
            **Merchant Portal Advisory Shown:**
            "⚠️ HIGH PENDING VOLUME: Transaction `pay_sbi_upi_demo_01` (₹2,500.00) is AWAITING BANK CONFIRMATION.
            **Do NOT dispatch food delivery order or goods** until final webhook is received.
            Gateway hub will auto-reconcile within 15 minutes."
            """)
            st.write("✅ **Prevents Merchant Financial Loss:** Protects merchant from fulfilling unconfirmed orders.")

        elif step.startswith("Step 4"):
            st.subheader("4. Admin Incident Command Center Detection")
            st.markdown("""
            The incident correlation engine detected **48 concurrent SBI UPI timeouts** across 3 merchants and grouped them into:
            - **Incident ID:** `INC-SBI-UPI-001`
            - **Category:** `BANK_CONNECTIVITY`
            - **Severity:** `HIGH`
            - **Estimated Financial Exposure:** ₹120,000.00
            - **Baseline vs Observed SR:** 94.5% ➔ 52.3%
            """)

        elif step.startswith("Step 5"):
            st.subheader("5. AI Agent Investigation & Evidence Formulation")
            st.markdown("""
            AI Agent formulated:
            - **Evidence:** 48 transaction socket timeouts, 14,500ms latency.
            - **Attribution:** Issuing Bank core-banking switch saturation (HDFC and ICICI normal).
            - **Recommended Action:** Throttle SBI UPI routing weight & prompt customer checkout to prefer alternate UPI handle or Card.
            """)

        elif step.startswith("Step 6"):
            st.subheader("6. Final Verification Webhook & State Transition")
            if txn and txn.status == "PENDING":
                st.write(f"Current Transaction Status: **{txn.status}**")
                col_res1, col_res2 = st.columns(2)
                with col_res1:
                    if st.button("Simulate Confirmed Webhook: CAPTURED", use_container_width=True):
                        txn.status = "CAPTURED"
                        txn.captured_at = dt.datetime.utcnow()
                        txn.error_code = None
                        txn.error_description = None
                        # Log to audit trail
                        db.add(AuditLog(
                            audit_id=f"AUD-{dt.datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                            workflow_id="WF-SBI-DEMO",
                            user_id="ADMIN",
                            agent_node="webhook_receiver",
                            tool_name="bank_reconciliation",
                            input_hash="SHA256_VERIFIED_NPCI_WEBHOOK",
                            result_status="SUCCESS",
                            latency_ms=120,
                            action="RESOLVE_PENDING_PAYMENT_CAPTURED"
                        ))
                        db.commit()
                        st.success("Transaction updated to CAPTURED! Customer and Merchant notified.")
                        st.rerun()

                with col_res2:
                    if st.button("Simulate Bank Failure Webhook: FAILED", use_container_width=True):
                        txn.status = "FAILED"
                        txn.error_code = "BANK_DECLINED_REVERSED"
                        txn.error_description = "Bank reversed transaction to customer account"
                        db.commit()
                        st.warning("Transaction updated to FAILED. Customer notified money will auto-reverse.")
                        st.rerun()

            elif txn and txn.status == "CAPTURED":
                st.success("✅ **Final Verified State: CAPTURED!**")
                st.markdown("""
                - **Customer Notification:** "SUCCESS: Payment of ₹2,500.00 to Swiggy India Successful. Order confirmed."
                - **Merchant Portal:** Order released for kitchen preparation and rider dispatch.
                - **Admin Analytics:** Success rate counters updated, exposure cleared.
                - **Audit Record:** Cryptographic SHA-256 verification receipt stored in audit ledger.
                """)
                if st.button("Reset Demo Transaction to PENDING", use_container_width=True):
                    txn.status = "PENDING"
                    txn.captured_at = None
                    db.commit()
                    st.rerun()
            else:
                st.error("Transaction status: FAILED")
                if st.button("Reset Demo Transaction to PENDING", use_container_width=True):
                    txn.status = "PENDING"
                    txn.captured_at = None
                    db.commit()
                    st.rerun()
