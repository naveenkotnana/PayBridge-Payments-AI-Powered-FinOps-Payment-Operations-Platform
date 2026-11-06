# PayBridge verification — 6 November 2026

## Passed

- Full automated suite: **152 passed**, three existing datetime deprecation warnings. The suite used a disposable copy of the legacy database and an unavailable local model endpoint for deterministic fallback behavior.
- Focused payment suite: **12 passed**, including local credential rotation and signature/provider-state checks. Provider calls in unit tests are mocked.
- CSV upload UI: a valid row was accepted, an invalid amount was rejected, and the result, stored-row preview and persistent Imported Payment Data tab rendered successfully.
- Admin Payments search: an uploaded payment with an older transaction date was found. Import filtering and 100-row pagination replace the previous 15-newest-row-only view.
- Sample incident UI: first approval persists, decision activity is visible, session-label changes do not overwrite the saved decision, and repeated approval is disabled.
- Receipt UI: visible for a stored captured provider payment, hidden for a pending payment. Amount rendering checked using local fixture data.
- Role navigation: Merchant → Payments retains the Merchant role rather than reverting to Admin. This focused test exercised the actual navigation code with view-renderer stubs.
- Razorpay credentials authenticated through a read-only provider lookup. A test order was created and stored. Test Mode checkout opened in the browser with the INR 280 order and reached the payment form.
- JavaScript callback check: payment identifiers and signature are returned through the component message protocol. This check used a mocked browser environment.
- Ruff passed for the changed payment and portal files; source compilation passed.
- The named payment dataset contains 50,000 rows and passes SQLite quick_check. It was created using SQLite backup without deleting the previous file.

## Outstanding external checks and scope boundaries

- A completed Razorpay browser payment and its resulting real provider-confirmed receipt have **not** been independently observed end to end. Order creation, checkout display, mocked callback checks and local verification tests are separate pieces of evidence.
- Some original AI/incident/gateway displays remain illustrative. Backend LangGraph investigation and stored workflow approvals exist, but the original screen controls are not a complete integration of those services.
- Sample mitigation approval saves a simulated decision. It changes neither bank routing nor payment status.
- PostgreSQL is a configuration/migration target; successful migration and application operation against it remain unverified.
- SQLite is the packaged local database. The UI/API must use the same explicit DATABASE_URL to see the same records.
- Docker builds, production deployment, load testing and real-money payments are not certified by these checks.
- UI persona switching is not authenticated identity. Production tenant authorization and crash-safe decisions remain work to do.

## Credentials and packaging

Test keys are stored in the ignored local .env file. Payment requests read that file per request so key rotation does not require cached credential values. The browser receives the public key and payment callback data, never the key secret.

The archive excludes .env, caches, ingestion archives, rejected-row files and extra database files. It includes the named synthetic payment dataset. Archive integrity and the exact packaged README are checked during final packaging.

## Wallet and UPI addition

Six wallet tests passed: one-time starting credit, idempotent payment, insufficient funds, commit-failure rollback, demo-mode restriction and customer separation. The complete Customer UI was exercised with a disposable database: initial INR 50,000 credit became INR 49,720 after payment, the receipt appeared and the pay button became disabled. The same local wallet flow was verified in the live browser. A JavaScript check verified the UPI-preferred and card/wallet display configurations. Provider UPI completion remains subject to account configuration and has not been observed end to end.

## Cart and merchant overview update

The full suite now passes 152 tests with the same three deprecation warnings. New checks cover two preset totals, custom quantities, invalid/empty carts, server pricing overriding a client-supplied amount, and changed-cart retries. A focused Customer UI check selected the Snack combo, paid INR 150 from the wallet and displayed its saved itemized receipt. A focused Merchant Overview check displayed a newly paid three-dosa-and-coffee order with its INR 400 total. The five-item menu and two combinations were also observed in the live browser. Merchant Orders, recent cards and totals now read stored records; other illustrative incident/kitchen displays remain unchanged.

## Payment-support check

Seven new tests pass for successful reference extraction, failure without an invented reason, saved failure detail, pending status, missing payment, order without a transaction and multiple-reference rejection. A focused UI check confirms recorded failure details and a distinct not-found warning. Lookup is read-only and does not update provider state.

## Uploaded batch reflected in Overview

An end-to-end UI check imported six CSV rows into a disposable database: four accepted, two rejected (including a duplicate). Selecting that batch on Overview displayed two captured, one failed and one pending payment, INR 330 captured GMV and 66.7% terminal success rate. No illustrative fallback amount was used for an empty total. Ruff passed for the changed view.
