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

    # 1. Extract Invoice No: Handles "Invoice No" or "Invoice #"
    inv_match = re.search(r"Invoice\s*(?:No|#):?\s*(.*)", text, re.IGNORECASE)
    invoice_no = inv_match.group(1).strip() if inv_match else None

    # 2. Extract Date: Handles flexible date formats
    date_match = re.search(r"Date:?\s*(.*)", text, re.IGNORECASE)
    formatted_date = None
    if date_match:
        try:
            formatted_date = parser.parse(date_match.group(1)).strftime('%Y-%m-%d')
        except:
            formatted_date = None

    # 3. Extract Vendor: Handles "Vendor" or "Seller"
    vendor_match = re.search(r"(?:Vendor|Seller):?\s*(.*)", text, re.IGNORECASE)
    vendor = vendor_match.group(1).strip() if vendor_match else None

    # 4. Extract Amount (Subtotal)
    amount_match = re.search(r"Subtotal:?\s*(?:Rs\.?|USD\s*)?\s*([\d,]+\.\d+)", text, re.IGNORECASE)
    amount = float(amount_match.group(1).replace(',', '')) if amount_match else 0.0

    # 5. Extract Tax (Percentage and Amount)
    # This captures the tax percentage (group 1) and the explicit tax amount (group 2)
    tax_match = re.search(r"(?:GST|VAT)\s*\((\d+)%\):?\s*(?:Rs\.?|USD\s*)?\s*([\d,]+\.\d+)?", text, re.IGNORECASE)
    
    tax = None
    if tax_match:
        tax_percent = int(tax_match.group(1))
        # If tax amount exists in text, use it; otherwise, calculate it from subtotal
        if tax_match.group(2):
            tax = float(tax_match.group(2).replace(',', ''))
        else:
            tax = round(amount * (tax_percent / 100), 2)

    # Return the dictionary
    return {
        "invoice_no": invoice_no,
        "date": formatted_date,
        "vendor": vendor,
        "amount": amount,
        "tax": tax,
        "currency": "INR" if "Rs" in text else ("USD" if "USD" in text else None)
    }
