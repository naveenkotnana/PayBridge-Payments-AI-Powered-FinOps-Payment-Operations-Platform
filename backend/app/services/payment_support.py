"""Read-only payment support answers grounded in saved transaction records."""
import re

from app.models.payments import PaymentOrder, PaymentTransaction


def lookup_payment(db, question):
    reference = question.strip()
    ids = re.findall(r"\b(?:pay|wlt|order)_[A-Za-z0-9_-]+\b", reference)
    if len(set(ids)) > 1:
        raise ValueError("Check one payment or order reference at a time.")
    if ids:
        reference = ids[0]
    if not reference or len(reference) > 100:
        raise ValueError("Enter a payment reference or an order reference.")
    transactions = db.query(PaymentTransaction).filter(PaymentTransaction.payment_id == reference).all()
    if not transactions:
        transactions = db.query(PaymentTransaction).filter(PaymentTransaction.order_id == reference).order_by(PaymentTransaction.created_at.desc()).all()
    order = db.get(PaymentOrder, reference)
    matches = []
    for payment in transactions:
        if payment.status == "CAPTURED":
            explanation = "The saved payment is captured. It is recorded as completed. Settlement is a separate process."
        elif payment.status == "FAILED":
            explanation = "The saved payment failed."
            if payment.error_description:
                explanation += " Recorded reason: " + payment.error_description
            elif payment.error_code:
                explanation += " Recorded error code: " + payment.error_code + ". No detailed reason was saved."
            else:
                explanation += " No failure reason was saved; the cause cannot be determined from this record."
        elif payment.status in {"PENDING", "AUTHORIZED"}:
            explanation = "This payment is not recorded as captured yet. Confirm its final provider status before asking the customer to pay again."
        else:
            explanation = f"The saved status is {payment.status}. Review the provider record for its final outcome."
        matches.append({"payment_id": payment.payment_id, "order_id": payment.order_id,
                        "merchant_id": payment.merchant_id, "amount": str(payment.amount),
                        "currency": payment.currency, "method": payment.method,
                        "bank": payment.bank, "status": payment.status,
                        "error_code": payment.error_code, "error_description": payment.error_description,
                        "source": payment.data_source, "recorded_at": str(payment.created_at),
                        "explanation": explanation})
    return {"reference": reference, "matches": matches,
            "order_status": order.status if order else None,
            "message": "Stored payment evidence found." if matches else
            "An order exists, but no matching payment record is stored. Payment completion is not confirmed." if order else
            "No matching record in the currently configured database. Check the reference and database; this does not prove the payment failed."}
