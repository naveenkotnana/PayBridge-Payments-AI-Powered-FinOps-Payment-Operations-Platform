# PayBridge: three moments to demonstrate

## The opening sentence

“PayBridge helps a payment operator turn failed-payment records into an evidence-backed investigation and a recorded human decision.”

## Moment 1 — Turn a CSV into visible payment evidence

**Problem:** a merchant has payment records but needs reliable counts and a way to inspect the failures.

**Show:** Admin → Data Pipeline → Upload Payment CSV. Import a small synthetic payment CSV. Show received, accepted, rejected and duplicate counts. Open Imported Payment Data, select the import and show its stored rows. In Payments, select that import or search its payment ID; older transaction dates remain discoverable through filtering and pagination.

**Say:** “I built a data pipeline that validates payment records, avoids duplicate insertion, stores accepted rows and keeps rejection reasons. The same database supplies the ledger.”

**Explain storage:** payment_transactions contains accepted payment rows; payment_ingestion_runs contains run status, counts and timestamps; payment_ingestion_records contains rejected-row details. Archived inputs and rejection reports are local files. The storage summary shows the actual configured database.

**Boundary:** COMPLETED means the processing run finished; inspect accepted/rejected counts to determine its result. Duplicates are included in rejected counts. A separate quality audit checks further invariants.

## Moment 2 — Explain and investigate a payment failure

**Problem:** elevated failures need evidence and a procedure, rather than a guess about the bank.

**Show:** use RAMESHSWARAM CAFE consistently. The prepared cafe/SBI/UPI synthetic segment has 503 captured, 133 failed and 4 pending transactions: terminal failure rate 20.91%. This aggregate does not prove a time-local outage.

**Say:** “Isolation Forest proposes unusual groups. Explicit rules assign severity. LangGraph then organizes named SQL, analytics and retrieved SOPs into an investigation. The language model explains supplied evidence; a human remains responsible for the decision.”

**Real backend demonstration:** start the API on the same DATABASE_URL. In /docs, authenticate, select an existing alert from GET /alerts, POST /alerts/{alert_id}/investigate, and inspect GET /workflows/{workflow_id}. Show the returned ID, evidence, recommendation and generation source. Use returned identifiers rather than invented values.

**Boundary:** the original AI workspace includes illustrative values. It is not proof that the backend graph ran. Use the API workflow for this portion. TF-IDF is lexical retrieval. Current ML fits and scores the same aggregates; measured predictive accuracy is not established.

## Moment 3 — Record a human decision and inspect the outcome

**Problem:** recommendations should not silently change payment operations.

**Show:** Admin → Approvals. The sample cafe mitigation saves a simulated decision and displays its persisted activity. If already decided, show the saved decision rather than trying to approve it again. Overview and Audit expose that activity.

**Say:** “Approval records an operational decision. It does not turn a failed payment into a captured payment, and this prototype does not reroute bank traffic.”

**Backend extension:** a pending LangGraph workflow can separately be approved or rejected through the API. Approved execution creates a local action record. The original sample incident button is not the same backend workflow approval queue.

**Boundary:** audit rows are inspectable, mutable records; hashes do not make them an immutable ledger. UI persona switching is for presentation and is not production authentication.

## Optional fourth moment — Test checkout and receipt

Customer → Orders → Pay ₹280 via Razorpay Modal → Open Razorpay Checkout. Use only public Razorpay test payment data in Test Mode. The browser returns identifiers and a signature; the server verifies those plus the provider order, amount, currency and captured status. A stored captured payment displays an amount, references, confirmation and downloadable receipt. Customer Payments reads stored transactions.

Order creation and opening the Test Mode checkout have been verified. Receipt visibility and verification contracts pass local tests. A fully completed browser payment has not yet been independently verified; do not describe that external end-to-end check as passed.

## A one-minute explanation to memorize

“Payment failures create confusion for merchants and customers. I built PayBridge to organize the investigation. First, it accepts payment CSVs, validates records and shows accepted and rejected rows. Second, it combines SQL analytics and anomaly signals with a LangGraph investigation that retrieves operating procedures and generates an evidence-backed recommendation. Third, a human reviews the action, and the system records the decision for audit. I used Python, FastAPI, SQLAlchemy, scikit-learn, LangGraph, local retrieval and Streamlit. The current local dataset is synthetic, mitigation is simulated, and some original screens still need backend wiring. My focus is making each decision traceable rather than letting a model act without review.”

## Answers that make your contribution clear

- **Why ML and rules?** ML proposes unusual patterns; explicit rules make escalation understandable and reproducible.
- **Why RAG?** It supplies relevant operational procedures alongside database facts. It does not guarantee a correct diagnosis.
- **Why human review?** A recommendation can be incomplete or wrong, and operational action needs accountability.
- **What did you validate?** 152 automated tests, plus focused upload, persistence, receipt and role-navigation UI checks. See VALIDATION.md.
- **What would you improve?** Connect the original AI and workflow-approval screens to the backend, add authenticated tenant isolation, improve durable execution and evaluate ML on time-separated labels.
- **What business result did you prove?** Centralized evidence and reviewable decisions are demonstrated. Investigation-time savings have not been measured.

## Submission checklist

1. Use the current submission ZIP, not an older copy.
2. Configure local credentials from .env.example; the actual .env is excluded from the ZIP.
3. Use the same DATABASE_URL for the UI and API. The packaged payment dataset is backend/data/payment_data.db.
4. Rehearse these three moments once before recording. Keep the demo synthetic and the mitigation explicitly simulated.
5. Preserve the current interface and explain remaining boundaries accurately.

## Fast customer payment demonstration

Choose Customer → Orders → PayBridge Wallet (demo). A new customer's wallet starts with INR 50,000 synthetic credit. Click Pay INR 280 from Wallet. Show the receipt and remaining INR 49,720 balance, then Customer Payments to inspect the persisted payment. This full local-wallet flow was also verified in the browser. It is distinct from a Razorpay test payment and will not appear as a provider payment in Razorpay's dashboard.

UPI (Razorpay) and Card / Wallet (Razorpay) remain available through the provider checkout, subject to account-enabled methods and customer completion. No real payment is automatic.

## Current live ordering path

Choose Customer → Orders. Pick Breakfast (INR 280), Snack (INR 150), or adjust any of the five menu quantities and click Update cart. Complete a demo-wallet payment, then show the itemized receipt. Merchant → Orders and Merchant → Overview → Recent Customer Orders show the saved items and total; Merchant → Payments shows the transaction. Overview uses stored merchant totals, with no sample monetary additions. The food-preparation illustration is still a demo and does not notify a real kitchen.

## Simple support demonstration

Copy a payment reference from Customer or Merchant Payments. In Admin → AI Investigation → Check a transaction, paste it or ask a question containing it, then click Check payment status. Show the saved status and recorded evidence. Explain that missing reasons and absent references are reported explicitly, not invented. This gives an easy customer-support story before explaining the separate LangGraph incident workflow.
