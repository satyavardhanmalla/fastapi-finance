import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dateutil import parser

app = FastAPI()

# Enable CORS for the grader
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class InvoiceInput(BaseModel):
    invoice_text: str

@app.post("/extract")
async def extract_invoice(data: InvoiceInput):
    text = data.invoice_text
    
    # 1. Normalize: Replace tabs/newlines with spaces to handle bad formatting
    text = " ".join(text.split())

    # 2. Invoice No: Look for variations of "Invoice" + separator
    inv_match = re.search(r"Invoice\s*(?:No|#|Number|ID)[:.\s]*([A-Z0-9-]+)", text, re.IGNORECASE)
    invoice_no = inv_match.group(1) if inv_match else None

    # 3. Date: Look for "Date" and capture content until the next word/line
    date_match = re.search(r"Date[:.\s]*([\d]{1,2}[/-][\d]{1,2}[/-][\d]{2,4}|[\d]{1,2}\s+[A-Za-z]+\s+[\d]{4})", text, re.IGNORECASE)
    formatted_date = None
    if date_match:
        try:
            formatted_date = parser.parse(date_match.group(1)).strftime('%Y-%m-%d')
        except:
            formatted_date = None

    # 4. Vendor: Look for "Vendor" or "Seller" or "From"
    vendor_match = re.search(r"(?:Vendor|Seller|From)[:.\s]*(.*?)(?=\s+(?:Invoice|Date|Subtotal|$))", text, re.IGNORECASE)
    vendor = vendor_match.group(1).strip() if vendor_match else None

    # 5. Amount: Look for "Subtotal", "Total", or "Amount"
    # This pattern captures the first number found after any of those keywords
    amount_match = re.search(r"(?:Subtotal|Total|Amount)[:.\s]*(?:Rs\.?|USD|[$])?\s*([\d,]+\.\d+)", text, re.IGNORECASE)
    amount = float(amount_match.group(1).replace(',', '')) if amount_match else None

    # 6. Tax: Look for "GST", "VAT", or "Tax"
    tax_match = re.search(r"(?:GST|VAT|Tax)[:.\s]*(?:Rs\.?|USD|[$])?\s*([\d,]+\.\d+)", text, re.IGNORECASE)
    tax = float(tax_match.group(1).replace(',', '')) if tax_match else None

    return {
        "invoice_no": invoice_no,
        "date": formatted_date,
        "vendor": vendor,
        "amount": amount,
        "tax": tax,
        "currency": "INR" if "Rs" in text else ("USD" if "USD" in text else "INR")
    }
