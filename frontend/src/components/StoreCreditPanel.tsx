import { WalletCards } from "lucide-react";
import { formatPrice } from "@/lib/shop";
import { CREDIT_ACTIVITY_LABEL, formatCreditDate, type StoreCreditSummary } from "@/lib/storeCredit";

/** Balance, per-credit validity and history. Shared by the customer account and the admin customer view. */
export default function StoreCreditPanel({ summary, audience, testId = "store-credit" }: { summary: StoreCreditSummary; audience: "customer" | "admin"; testId?: string }) {
  return <div className="store-credit-panel" data-testid={testId}>
    <div className="store-credit-balance">
      <WalletCards size={22} />
      <div>
        <small>{audience === "customer" ? "Available to spend" : "Current balance"}</small>
        <strong data-testid={`${testId}-balance`}>{formatPrice(summary.balance)}</strong>
        {summary.next_expiry
          ? <span data-testid={`${testId}-next-expiry`}>{formatPrice(summary.next_expiry_amount)} expires on {formatCreditDate(summary.next_expiry)}</span>
          : <span>{audience === "customer" ? "No active credit right now." : "No active credit."}</span>}
      </div>
    </div>
    {audience === "customer" && summary.balance > 0 && <p className="store-credit-hint">Tick “Use my SAFYRA Credit” at checkout. Credit can pay for the whole order, including shipping, and the soonest-expiring credit is used first.</p>}
    {summary.grants.length > 0 && <div className="store-credit-table-wrap"><table className="store-credit-table" data-testid={`${testId}-grants`}>
      <thead><tr><th>Issued</th><th>Amount</th><th>Remaining</th><th>Valid until</th><th>Status</th></tr></thead>
      <tbody>{summary.grants.map((grant) => <tr key={grant.id} data-testid={`${testId}-grant-${grant.id}`}>
        <td>{formatCreditDate(grant.issued_at)}</td><td>{formatPrice(grant.amount)}</td><td>{formatPrice(grant.remaining)}</td><td>{formatCreditDate(grant.expires_at)}</td>
        <td><span className={`store-credit-status is-${grant.status.toLowerCase()}`}>{grant.status}</span></td>
      </tr>)}</tbody>
    </table></div>}
    {summary.activity.length > 0 && <div className="store-credit-activity" data-testid={`${testId}-activity`}>
      <span className="eyebrow">History</span>
      <ul>{summary.activity.map((item) => <li key={item.id} data-testid={`${testId}-activity-${item.id}`}>
        <span><strong>{CREDIT_ACTIVITY_LABEL[item.type]}</strong>{item.request_number && <small>{item.request_number}</small>}{item.type === "issued" && item.expires_at && <small>Valid until {formatCreditDate(item.expires_at)}</small>}</span>
        <span className={item.type === "redeemed" ? "is-debit" : "is-credit"}>{item.type === "redeemed" ? "−" : "+"}{formatPrice(item.amount)}<small>{formatCreditDate(item.created_at)}</small></span>
      </li>)}</ul>
    </div>}
  </div>;
}
