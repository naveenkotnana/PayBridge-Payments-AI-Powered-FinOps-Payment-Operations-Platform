"""Data Generation & Simulation Workbench View.

Allows operators and managers to:
1. Inspect live database availability and data gaps.
2. Select and run any of the 10 operational simulation scenarios.
3. Apply targeted data augmentation (stratified failure balance).
4. Run real-time mathematical & schema data quality audits with score reporting.
5. Inspect class balance distributions and data provenance breakdown.
"""
import streamlit as st
from dashboard.components import api_call


def render_simulation(role: str):
    st.markdown("""
    <div style="margin-bottom:1.5rem;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <h1 style="font-size:1.8rem; font-weight:700; color:#0F172A; margin:0;">
                    Data Generation & Simulation Workbench
                </h1>
                <p style="color:#64748B; font-size:0.9rem; margin-top:4px;">
                    Scenario-based event simulation, class-balanced augmentation, and automated quality auditing.
                </p>
            </div>
            <span class="fintech-badge badge-high" style="font-size:0.8rem; padding:6px 12px;">
                SYNTHETIC DEMO ENVIRONMENT
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab_inspect, tab_generate, tab_augment, tab_quality = st.tabs([
        "📊 Data Availability & Distribution",
        "⚡ Scenario Generator",
        "🎯 Advanced Augmentation",
        "🛡️ Data Quality & Audit",
    ])

    # ------------------------------------------------------------- 1. Data Availability
    with tab_inspect:
        st.subheader("Database Records & Provenance")
        avail, err = api_call("GET", "/api/v1/simulation/availability")

        if err:
            st.error(f"Failed to inspect data availability: {err}")
        elif avail:
            prov = avail.get("provenance", {})
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Records", f"{avail.get('total_records_inspected', 0):,}")
            with col2:
                st.metric("Synthetic Records", f"{prov.get('synthetic_records', 0):,}", f"{prov.get('synthetic_ratio_pct', 0)}%")
            with col3:
                st.metric("Augmented Records", f"{prov.get('augmented_records', 0):,}")
            with col4:
                st.metric("Real Records", f"{prov.get('real_records', 0):,}")

            # Gaps & Recommendations
            gaps = avail.get("gaps_identified", [])
            recs = avail.get("recommendations", [])
            if gaps:
                st.warning("⚠️ **Data Gaps Detected:**")
                for g in gaps:
                    st.write(f"- {g}")
                if recs:
                    st.info("💡 **Recommended Actions:**")
                    for r in recs:
                        st.write(f"- {r}")
            else:
                st.success("✅ **Dataset is well-balanced and ready for ML/Analytics engines.**")

            st.markdown("---")
            st.subheader("Class & Rail Distribution")
            dist = avail.get("distributions", {})
            c1, c2, c3 = st.columns(3)
            with c1:
                st.write("**Payment Methods:**")
                st.json(dist.get("method", {}))
            with c2:
                st.write("**Bank Volumes:**")
                st.json(dist.get("bank", {}))
            with c3:
                st.write("**Status Distribution:**")
                st.json(dist.get("status", {}))

    # ------------------------------------------------------------- 2. Scenario Generator
    with tab_generate:
        st.subheader("Scenario-Based Event Generator")
        st.markdown("""
        Generate realistic payment lifecycles under specific operational conditions.
        Every record reconciles mathematically (`net_amount = amount - fee - tax`).
        """)

        scenarios_res, _ = api_call("GET", "/api/v1/simulation/scenarios")
        scenarios_list = [s["name"] for s in (scenarios_res or {}).get("scenarios", [])] or [
            "NORMAL_TRAFFIC", "BANK_OUTAGE", "UPI_DEGRADATION", "GATEWAY_TIMEOUT_SPIKE",
            "MERCHANT_FAILURE_SPIKE", "HIGH_VOLUME_SURGE", "DUPLICATE_EVENTS",
            "SETTLEMENT_DELAYS", "REFUND_ANOMALIES", "SIMULTANEOUS_INCIDENTS"
        ]

        with st.form("form_generate_scenario"):
            c_sc, c_cnt, c_days, c_seed = st.columns([3, 2, 2, 2])
            with c_sc:
                chosen_sc = st.selectbox("Operational Scenario", options=scenarios_list, index=0)
            with c_cnt:
                vol_option = st.selectbox("Volume Preset", options=["Small (1,000)", "Medium (10,000)", "Custom"], index=0)
                if vol_option == "Small (1,000)":
                    count_val = 1000
                elif vol_option == "Medium (10,000)":
                    count_val = 10000
                else:
                    count_val = st.number_input("Count", min_value=50, max_value=50000, value=500, step=100)
            with c_days:
                days_val = st.number_input("Time Window (Days)", min_value=1, max_value=60, value=7)
            with c_seed:
                seed_val = st.number_input("Reproducibility Seed", value=42, min_value=1)

            submit_gen = st.form_submit_button("🚀 Generate Scenario Data", use_container_width=True)

            if submit_gen:
                with st.spinner(f"Generating {count_val} payment events for {chosen_sc}..."):
                    payload = {
                        "scenario": chosen_sc,
                        "count": count_val,
                        "days_back": days_val,
                        "seed": seed_val,
                    }
                    gen_res, gen_err = api_call("POST", "/api/v1/simulation/generate", json=payload)
                    if gen_err:
                        st.error(f"Generation error: {gen_err}")
                    elif gen_res:
                        st.success(f"Generated {gen_res.get('records_generated', {}).get('payments', 0)} payments under {chosen_sc}!")
                        st.json(gen_res)

    # ------------------------------------------------------------- 3. Advanced Augmentation
    with tab_augment:
        st.subheader("Targeted Data Augmentation")
        st.markdown("""
        Balance rare failure classes (fraud blocks, security decline, bank timeouts)
        without corrupting historical temporal order or financial decimals.
        """)
        with st.form("form_augmentation"):
            c_strat, c_recs, c_aug_seed = st.columns([3, 2, 2])
            with c_strat:
                strat = st.selectbox("Strategy", options=["STRATIFIED_FAILURE_BALANCE", "UPI_LATENCY_AUGMENTATION"])
            with c_recs:
                aug_count = st.number_input("Additional Records", min_value=50, max_value=5000, value=300, step=50)
            with c_aug_seed:
                aug_seed = st.number_input("Seed", value=99, min_value=1)

            submit_aug = st.form_submit_button("🎯 Run Augmentation", use_container_width=True)
            if submit_aug:
                with st.spinner("Augmenting dataset..."):
                    aug_res, aug_err = api_call("POST", "/api/v1/simulation/augment", json={
                        "strategy": strat,
                        "target_additional_records": aug_count,
                        "seed": aug_seed,
                    })
                    if aug_err:
                        st.error(aug_err)
                    elif aug_res:
                        st.success(f"Augmentation complete! Added {aug_count} records marked as AUGMENTED.")
                        st.json(aug_res)

    # ------------------------------------------------------------- 4. Data Quality & Audit
    with tab_quality:
        st.subheader("Automated Data Quality & Mathematical Invariants Audit")
        if st.button("🛡️ Execute Quality Audit Now", use_container_width=True):
            with st.spinner("Auditing referential integrity, schemas, and decimal invariants..."):
                q_res, q_err = api_call("GET", "/api/v1/simulation/quality-report")
                if q_err:
                    st.error(q_err)
                elif q_res:
                    score = q_res.get("quality_score_pct", 0)
                    col_s1, col_s2, col_s3 = st.columns(3)
                    with col_s1:
                        st.metric("Quality Score", f"{score}%")
                    with col_s2:
                        st.metric("Checks Passed", q_res.get("total_checks_passed", 0))
                    with col_s3:
                        st.metric("Checks Failed", q_res.get("total_checks_failed", 0))

                    st.markdown("---")
                    st.subheader("Detailed Audit Invariants")
                    for c in q_res.get("checks", []):
                        badge_color = "#16A34A" if c["passed"] else "#DC2626"
                        icon = "✅" if c["passed"] else "❌"
                        st.markdown(f"""
                        <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-left:4px solid {badge_color}; padding:10px 14px; border-radius:6px; margin-bottom:8px;">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <strong style="color:#0F172A;">{icon} {c['check_name']}</strong>
                                <span style="font-size:0.75rem; color:#64748B; background:#EDF2F7; padding:2px 8px; border-radius:4px;">{c['category']}</span>
                            </div>
                            <div style="font-size:0.82rem; color:#475569; margin-top:4px;">{c['details']}</div>
                        </div>
                        """, unsafe_allow_html=True)
