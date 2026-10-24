import type { AdminOrderRequest } from "@/lib/checkout";
import { variantLabel } from "@/lib/shop";

export type OrderDocumentKind = "invoice" | "packing-slip";

const escapeHtml = (value: string | number) => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

const money = (amount: number) => new Intl.NumberFormat("en-IN", {
  style: "currency", currency: "INR", maximumFractionDigits: 0,
}).format(amount);

export function buildOrderDocumentHtml(order: AdminOrderRequest, kind: OrderDocumentKind): string {
  const invoice = kind === "invoice";
  const title = invoice ? "ORDER SUMMARY — NOT AN INVOICE" : "PACKING SLIP";
  const itemRows = order.items.map((item) => `<tr>
    <td><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(variantLabel(item))}</small></td>
    <td class="number">${escapeHtml(item.quantity)}</td>
    ${invoice ? `<td class="number">${escapeHtml(money(item.price))}</td><td class="number">${escapeHtml(money(item.line_total))}</td>` : ""}
  </tr>`).join("");
  const missingFields = invoice
    ? "This is an internal order summary, not an invoice or proof of payment. Use the separately generated invoice PDF after store invoice settings are complete."
    : "Prices are intentionally omitted from this packing slip.";
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${title} · ${escapeHtml(order.request_number)}</title><style>
    *{box-sizing:border-box}body{margin:0;background:#f4f0e8;color:#261c19;font:14px/1.5 Georgia,serif}.toolbar{padding:12px;text-align:center}.toolbar button{padding:10px 18px;border:0;background:#261c19;color:#fff;font:700 12px Arial,sans-serif;letter-spacing:.08em}.document{width:min(800px,calc(100% - 32px));margin:0 auto 32px;padding:44px;background:#fff}.top{display:flex;justify-content:space-between;gap:24px;border-bottom:2px solid #261c19;padding-bottom:24px}.brand{font-size:22px;letter-spacing:.18em}.brand small{display:block;margin-top:4px;font:9px Arial,sans-serif;letter-spacing:.35em}.title{text-align:right}.title h1{margin:0;font-size:24px;letter-spacing:.08em}.title span{display:block;margin-top:5px;font:11px Arial,sans-serif}.meta,.addresses{display:grid;grid-template-columns:1fr 1fr;gap:28px;margin:28px 0}.block h2{margin:0 0 8px;font:700 10px Arial,sans-serif;letter-spacing:.13em;text-transform:uppercase}.block p{margin:0;white-space:pre-line}.status{padding:12px;border:1px solid #d7cec1;font-family:Arial,sans-serif;font-size:12px}table{width:100%;border-collapse:collapse;margin:25px 0}th{padding:10px 8px;border-bottom:1px solid #261c19;text-align:left;font:700 10px Arial,sans-serif;letter-spacing:.08em;text-transform:uppercase}td{padding:13px 8px;border-bottom:1px solid #e4ddd3;vertical-align:top}td small{display:block;color:#6e5d55}.number{text-align:right}.total{display:flex;justify-content:flex-end;gap:50px;font-size:16px}.note{margin-top:30px;padding:14px;border-left:3px solid #49343d;background:#f7f3eb;font:11px/1.55 Arial,sans-serif}.customer-note{margin-top:20px}.tracking{margin-top:20px;font:12px Arial,sans-serif}@media print{body{background:#fff}.toolbar{display:none}.document{width:100%;margin:0;padding:20px;box-shadow:none}}@media(max-width:600px){.document{padding:24px}.top,.meta,.addresses{grid-template-columns:1fr;display:grid}.title{text-align:left}}
  </style></head><body><div class="toolbar"><button onclick="window.print()">PRINT ${title}</button></div><main class="document" data-document-kind="${kind}">
    <header class="top"><div class="brand">SAFYRA<small>CHIKANKARI</small></div><div class="title"><h1>${title}</h1><span>${escapeHtml(order.request_number)}</span></div></header>
    <section class="meta"><div class="block"><h2>Order reference</h2><p>${escapeHtml(order.request_number)}\nReceived ${escapeHtml(new Date(order.received_at).toLocaleString("en-IN"))}</p></div><div class="status"><strong>Payment:</strong> ${escapeHtml(order.payment_status)}<br><strong>Fulfilment:</strong> ${escapeHtml(order.cancelled ? "Cancelled" : order.fulfilment_status)}${order.refund_status !== "Not initiated" ? `<br><strong>Refund:</strong> ${escapeHtml(order.refund_status)}` : ""}</div></section>
    <section class="addresses"><div class="block"><h2>${invoice ? "Customer" : "Ship to"}</h2><p>${escapeHtml(order.name)}\n${escapeHtml(order.email)}\n${escapeHtml(order.phone)}</p></div><div class="block"><h2>Delivery address</h2><p>${escapeHtml(order.address)}\n${escapeHtml(order.city)}, ${escapeHtml(order.state_region)} ${escapeHtml(order.postal_code)}\n${escapeHtml(order.country)}</p></div></section>
    <table><thead><tr><th>Item</th><th class="number">Qty</th>${invoice ? '<th class="number">Unit price</th><th class="number">Line total</th>' : ""}</tr></thead><tbody>${itemRows}</tbody></table>
    ${invoice ? `<div class="total"><span>Saved product subtotal</span><strong>${escapeHtml(money(order.subtotal))}</strong></div>` : ""}
    ${order.note ? `<div class="block customer-note"><h2>Customer note</h2><p>${escapeHtml(order.note)}</p></div>` : ""}
    ${(order.courier_name || order.tracking_number) ? `<div class="tracking"><strong>Courier:</strong> ${escapeHtml(order.courier_name || "Not recorded")} · <strong>Tracking:</strong> ${escapeHtml(order.tracking_number || "Not recorded")}</div>` : ""}
    <footer class="note"><strong>${invoice ? "Document limitations" : "Packing note"}</strong><br>${missingFields}</footer>
  </main></body></html>`;
}

export function openOrderPrintView(order: AdminOrderRequest, kind: OrderDocumentKind): void {
  const printWindow = window.open("", "_blank", "width=900,height=760");
  if (!printWindow) throw new Error("Print preview was blocked by the browser");
  printWindow.opener = null;
  printWindow.document.open();
  printWindow.document.write(buildOrderDocumentHtml(order, kind));
  printWindow.document.close();
  printWindow.focus();
}