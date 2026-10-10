import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, Clock3, ShieldCheck, X } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import BrandHeader from "@/components/BrandHeader";
import { useShop } from "@/components/ShopProvider";
import { apiGet } from "@/lib/api";
import type { PaymentStatusResponse } from "@/lib/checkout";
import { formatPrice } from "@/lib/shop";


export default function PaymentResult() {
  const [params] = useSearchParams();
  const transactionId = params.get("txnid") ?? "";
  const { clearCart } = useShop();
  const cleared = useRef(false);
  const payment = useQuery({
    queryKey: ["payment-status", transactionId],
    queryFn: () => apiGet<PaymentStatusResponse>(`/payments/${transactionId}`),
    enabled: Boolean(transactionId),
    retry: false,
    refetchInterval: (query) => query.state.data?.status === "pending" ? 3000 : false,
  });
  useEffect(() => {
    if (payment.data?.status === "paid" && !cleared.current) {
      cleared.current = true;
      clearCart();
      window.localStorage.removeItem("safyra-checkout-session");
    }
  }, [clearCart, payment.data?.status]);

  const status = payment.data?.status;
  return <div className="page-shell"><BrandHeader /><main className="payment-result-page" data-testid="payment-result-page">
    {!transactionId || payment.isError ? <section className="payment-result-card is-failed" data-testid="payment-result-error"><X size={28} /><span className="eyebrow">Payment status unavailable</span><h1>We could not verify this payment.</h1><p>No order will be fulfilled without independent PayU confirmation. Please return to checkout or contact SAFYRA with your payment reference.</p><Link to="/checkout" className="button button-dark" data-testid="payment-result-return-checkout">Return to checkout</Link></section>
    : payment.isPending || status === "pending" ? <section className="payment-result-card is-pending" data-testid="payment-result-pending"><Clock3 size={28} /><span className="eyebrow">Secure verification</span><h1>Your payment is being confirmed.</h1><p>PayU is confirming the transaction with SAFYRA. Please keep this page open; it updates automatically.</p>{payment.data && <div className="payment-reference" data-testid="payment-result-reference"><span>Order reference</span><strong>{payment.data.request_number}</strong><span>Payable total</span><strong>{formatPrice(payment.data.amount)}</strong></div>}<button className="button button-outline" onClick={() => payment.refetch()} data-testid="payment-result-refresh">Check again</button></section>
    : status === "paid" ? <section className="payment-result-card is-paid" data-testid="payment-result-paid"><Check size={28} /><span className="eyebrow">Payment confirmed</span><h1>Your SAFYRA order is confirmed.</h1><p>PayU has verified your payment. We have emailed your confirmation and your handcrafted piece will now enter fulfilment.</p><div className="payment-reference" data-testid="payment-result-reference"><span>Order reference</span><strong>{payment.data.request_number}</strong><span>Paid total</span><strong>{formatPrice(payment.data.amount)}</strong></div><div className="payment-result-actions"><Link to="/account" className="button button-dark" data-testid="payment-result-account">View your orders</Link><Link to="/shop" className="button button-outline" data-testid="payment-result-shop">Continue shopping</Link></div></section>
    : <section className="payment-result-card is-failed" data-testid="payment-result-failed"><X size={28} /><span className="eyebrow">Payment not completed</span><h1>Your bag is still with you.</h1><p>PayU did not confirm a successful payment, so SAFYRA will not fulfil or charge this order. You can safely try again.</p><div className="payment-reference"><span>Order reference</span><strong>{payment.data.request_number}</strong></div><Link to="/checkout" className="button button-dark" data-testid="payment-result-retry">Try payment again</Link></section>}
    <div className="payment-security-note" data-testid="payment-security-note"><ShieldCheck size={17} /> Payment details are entered only on PayU’s hosted checkout.</div>
  </main></div>;
}