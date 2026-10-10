import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { City, Country, State } from "country-state-city";
import { isValidPhoneNumber, type CountryCode } from "libphonenumber-js";
import { getCountryByCode, validatePostalCode } from "postal-code-checker";
import { ArrowLeft, Check, CreditCard, MessageCircle, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";
import BrandHeader from "@/components/BrandHeader";
import SafeProductImage from "@/components/SafeProductImage";
import { useShop } from "@/components/ShopProvider";
import { formatPrice, whatsappUrl } from "@/lib/shop";
import { apiPost, apiPut } from "@/lib/api";
import type { OrderRequestCreate, OrderRequestResponse, PaymentQuoteResponse, PayUCheckoutResponse } from "@/lib/checkout";
import type { CheckoutSessionSummary, CheckoutSessionUpsert } from "@/lib/abandonedCheckout";

type CheckoutStep = "details" | "review" | "complete";
type CheckoutField = "name" | "email" | "phone" | "address" | "city" | "state" | "postalCode" | "country" | "shipping";
type CheckoutErrors = Partial<Record<CheckoutField, string>>;

interface CheckoutFormState {
  name: string;
  email: string;
  phone: string;
  address: string;
  city: string;
  state: string;
  postalCode: string;
  country: string;
  note: string;
}

const countries = Country.getAllCountries().sort((left, right) => left.name.localeCompare(right.name));
const NO_STATE_REGION = "Not applicable";
const normalize = (value: string) => value.trim().toLocaleLowerCase();
const exactMatch = <T extends { name: string }>(items: T[], value: string) => items.find((item) => normalize(item.name) === normalize(value));
const validEmail = (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(value.trim());

function FieldError({ field, message }: { field: CheckoutField; message?: string }) {
  return message ? <small className="checkout-field-error" aria-live="polite" data-testid={`checkout-${field}-error`}>{message}</small> : null;
}

export default function Checkout() {
  const { cart, cartTotal, orderNote, setOrderNote } = useShop();
  const [step, setStep] = useState<CheckoutStep>("details");
  const [shipping, setShipping] = useState("india");
  const [form, setForm] = useState<CheckoutFormState>({ name: "", email: "", phone: "", address: "", city: "", state: "", postalCode: "", country: "India", note: orderNote });
  const [errors, setErrors] = useState<CheckoutErrors>({});
  const [request, setRequest] = useState<OrderRequestResponse | null>(null);
  const [checkoutSessionKey] = useState(() => {
    const stored = window.localStorage.getItem("safyra-checkout-session");
    if (stored) return stored;
    const created = window.crypto.randomUUID();
    window.localStorage.setItem("safyra-checkout-session", created);
    return created;
  });
  const selectedCountry = exactMatch(countries, form.country);
  const postalCountry = selectedCountry ? getCountryByCode(selectedCountry.isoCode) : undefined;
  const countryUsesPostalCodes = Boolean(postalCountry?.postalCodePatterns.length);
  const states = selectedCountry ? State.getStatesOfCountry(selectedCountry.isoCode) : [];
  const selectedState = exactMatch(states, form.state);
  const cityRecords = selectedCountry && (!states.length || selectedState)
    ? selectedState
      ? City.getCitiesOfState(selectedCountry.isoCode, selectedState.isoCode)
      : City.getCitiesOfCountry(selectedCountry.isoCode) ?? []
    : [];
  const cities = [...new Set(cityRecords.map((city) => city.name))].sort((left, right) => left.localeCompare(right));

  const submitRequest = useMutation({
    mutationFn: (payload: OrderRequestCreate) => apiPost<OrderRequestResponse>("/order-requests", payload),
    onSuccess: (response) => {
      setRequest(response);
      setStep("complete");
      window.localStorage.removeItem("safyra-checkout-session");
      window.scrollTo({ top: 0, behavior: "smooth" });
    },
  });
  const quotePayment = useMutation({ mutationFn: (payload: OrderRequestCreate) => apiPost<PaymentQuoteResponse>("/payments/quote", payload) });
  const createPayment = useMutation({
    mutationFn: (payload: OrderRequestCreate) => apiPost<PayUCheckoutResponse>("/payments/create", payload),
    onSuccess: (response) => {
      const paymentForm = document.createElement("form");
      paymentForm.method = "POST";
      paymentForm.action = response.action;
      Object.entries(response.fields).forEach(([name, value]) => {
        const input = document.createElement("input");
        input.type = "hidden";
        input.name = name;
        input.value = value;
        paymentForm.appendChild(input);
      });
      document.body.appendChild(paymentForm);
      paymentForm.submit();
    },
  });
  const checkoutTracking = useMutation({
    mutationFn: (payload: CheckoutSessionUpsert) => apiPut<CheckoutSessionSummary>("/checkout-sessions", payload),
  });

  const trackCurrentCheckout = () => {
    const hasContact = validEmail(form.email) || form.phone.replace(/\D/g, "").length >= 7;
    if (form.name.trim().length < 2 || !hasContact || !cart.length) return;
    checkoutTracking.mutate({
      session_key: checkoutSessionKey,
      name: form.name.trim(),
      email: validEmail(form.email) ? form.email.trim() : null,
      phone: form.phone.trim(),
      address: form.address.trim(),
      city: form.city.trim(),
      state_region: form.state.trim(),
      postal_code: form.postalCode.trim(),
      country: form.country.trim(),
      note: form.note.trim(),
      whatsapp_opt_in: false,
      marketing_email_opt_in: false,
      items: cart.map((item) => ({ product_id: item.productId, set_type: item.setType || null, size: item.size, color: item.color, quantity: item.quantity })),
    });
  };

  const validateForm = (): CheckoutErrors => {
    const next: CheckoutErrors = {};
    if (form.name.trim().length < 2 || !/[\p{L}]{2}/u.test(form.name)) next.name = "Enter your full name.";
    if (!validEmail(form.email)) next.email = "Enter a valid email address.";
    if (!selectedCountry) next.country = "Select a country from the list.";
    if (selectedCountry) {
      try {
        if (!isValidPhoneNumber(form.phone.trim(), selectedCountry.isoCode as CountryCode)) next.phone = "Enter a valid phone number for this country.";
      } catch {
        next.phone = "Enter a valid phone number for this country.";
      }
      if (countryUsesPostalCodes && !validatePostalCode(selectedCountry.isoCode, form.postalCode.trim())) next.postalCode = "Enter a valid postal code for this country.";
      if (!countryUsesPostalCodes && form.postalCode !== NO_STATE_REGION) next.postalCode = "This country does not use postal codes; use the available option.";
    } else {
      if (!form.phone.trim()) next.phone = "Enter your phone number.";
      if (!form.postalCode.trim()) next.postalCode = "Enter your postal code.";
    }
    if (form.address.trim().length < 5 || !/[\p{L}\p{N}]{3}/u.test(form.address)) next.address = "Enter a complete delivery address.";
    if (states.length && !selectedState) next.state = "Select a state or region from the list.";
    if (!states.length && selectedCountry && form.state !== NO_STATE_REGION) next.state = "Select the available region option.";
    if (!selectedCountry || !cities.length) next.city = "City suggestions are unavailable for this destination. Please contact SAFYRA.";
    else if (!cities.some((city) => normalize(city) === normalize(form.city))) next.city = "Select a city from the suggestions.";
    if (selectedCountry && ((selectedCountry.isoCode === "IN" && shipping !== "india") || (selectedCountry.isoCode !== "IN" && shipping !== "international"))) next.shipping = "Shipping selection must match the delivery country.";
    return next;
  };

  const setField = (field: keyof CheckoutFormState, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
    if (field === "note") setOrderNote(value);
    if (field !== "note") setErrors((current) => ({ ...current, [field]: undefined }));
  };
  const setCountry = (value: string) => {
    const country = exactMatch(countries, value);
    const countryStates = country ? State.getStatesOfCountry(country.isoCode) : [];
    const postalDetails = country ? getCountryByCode(country.isoCode) : undefined;
    if (country) setShipping(country.isoCode === "IN" ? "india" : "international");
    setForm((current) => ({ ...current, country: value, state: country && !countryStates.length ? NO_STATE_REGION : "", city: "", postalCode: country && !postalDetails?.postalCodePatterns.length ? NO_STATE_REGION : "" }));
    setErrors((current) => ({ ...current, country: undefined, state: undefined, city: undefined, postalCode: undefined, phone: undefined }));
  };
  const setStateRegion = (value: string) => {
    setForm((current) => ({ ...current, state: value, city: "" }));
    setErrors((current) => ({ ...current, state: undefined, city: undefined }));
  };
  const showFieldError = (field: CheckoutField) => setErrors((current) => ({ ...current, [field]: validateForm()[field] }));
  const buildPayload = (): OrderRequestCreate | null => selectedCountry ? {
    name: form.name.trim(), email: form.email.trim(), phone: form.phone.trim(), address: form.address.trim(),
    city: form.city.trim(), state_region: form.state.trim(), postal_code: form.postalCode.trim(),
    country: selectedCountry.name, country_code: selectedCountry.isoCode, shipping: shipping as "india" | "international",
    note: form.note.trim(), checkout_session_id: checkoutSessionKey,
    items: cart.map((item) => ({ product_id: item.productId, set_type: item.setType || null, size: item.size, color: item.color, quantity: item.quantity })),
  } : null;
  const continueToReview = (event: FormEvent) => {
    event.preventDefault();
    const next = validateForm();
    setErrors(next);
    if (Object.keys(next).length) return;
    trackCurrentCheckout();
    const payload = buildPayload();
    if (!payload) return;
    const showReview = () => { setStep("review"); window.scrollTo({ top: 0, behavior: "smooth" }); };
    if (payload.country_code === "IN") quotePayment.mutate(payload, { onSuccess: showReview }); else showReview();
  };
  const orderSummary = cart.map((item) => `${item.title} — Size ${item.size}, ${item.color}, Qty ${item.quantity}`).join("; ");
  const handoff = whatsappUrl(`Hello SAFYRA, my order request${request ? ` ${request.request_number}` : ""} is ready for review. Items: ${orderSummary}. Total before shipping: ${formatPrice(cartTotal)}. Shipping: ${shipping === "india" ? "India delivery" : "International shipping quote"}. Deliver to: ${form.name}, ${form.address}, ${form.city}, ${form.state}, ${form.postalCode}, ${form.country}. Contact: ${form.phone}, ${form.email}.${form.note.trim() ? ` Note: ${form.note.trim()}` : ""}`);
  const noCityData = Boolean(selectedCountry && (!states.length || selectedState) && !cities.length);
  const contactForLocation = whatsappUrl(`Hello SAFYRA, I need help entering my delivery city for ${form.country || "my country"}.`);
  const checkoutHelpUrl = whatsappUrl("Hello SAFYRA, I need help before submitting my order request.");
  const submitOrderRequest = () => {
    const payload = buildPayload();
    if (!payload) return;
    if (payload.country_code === "IN") createPayment.mutate(payload); else submitRequest.mutate(payload);
  };
  const isIndia = selectedCountry?.isoCode === "IN";
  const estimatedShipping = isIndia ? (cartTotal >= 1000 ? 0 : 120) : 0;
  const shippingAmount = quotePayment.data?.shipping_amount ?? estimatedShipping;
  const payableTotal = quotePayment.data?.total ?? cartTotal + shippingAmount;
  if (!cart.length) return <div className="page-shell"><BrandHeader /><main className="checkout-empty"><h1>Your bag is empty.</h1><Link to="/shop" className="button button-dark" data-testid="checkout-empty-shop">Return to shop</Link></main></div>;
  return <div className="page-shell">
    <BrandHeader />
    <main className="checkout-page">
      <Link to="/cart" className="back-link" data-testid="checkout-back"><ArrowLeft size={15} /> Back to bag</Link>
      <div className="checkout-heading">
        <span className="eyebrow">Secure checkout</span>
        <h1 data-testid="checkout-heading">{step === "details" ? "Where should your order go?" : step === "review" ? "Review every detail." : "YOUR SAFYRA ORDER REQUEST IS RECEIVED."}</h1>
        <p data-testid="checkout-supporting-copy">{step === "complete" ? "Thank you. We’ve received your international order request and will confirm shipping personally." : isIndia ? "Review the final total here, then complete payment securely on PayU’s hosted checkout." : "International shipping remains personally confirmed by SAFYRA before payment."}</p>
      </div>
      <div className="checkout-layout">
        <section className="checkout-form-card">
          {step === "details" && <form onSubmit={continueToReview} noValidate data-testid="checkout-address-form">
            <div className="checkout-step"><span>1</span><div><strong>Contact & delivery</strong><small>Required for shipping confirmation</small></div></div>
            <div className="checkout-fields">
              <label>Full name
                <input value={form.name} onChange={(event) => setField("name", event.target.value)} onBlur={() => { showFieldError("name"); trackCurrentCheckout(); }} autoComplete="name" required aria-invalid={Boolean(errors.name)} data-testid="checkout-name" />
                <FieldError field="name" message={errors.name} />
              </label>
              <label>Email
                <input type="email" value={form.email} onChange={(event) => setField("email", event.target.value)} onBlur={() => { showFieldError("email"); trackCurrentCheckout(); }} autoComplete="email" required aria-invalid={Boolean(errors.email)} data-testid="checkout-email" />
                <FieldError field="email" message={errors.email} />
              </label>
              <label>Phone
                <input value={form.phone} onChange={(event) => setField("phone", event.target.value)} onBlur={() => { showFieldError("phone"); trackCurrentCheckout(); }} autoComplete="tel" required aria-invalid={Boolean(errors.phone)} data-testid="checkout-phone" />
                <FieldError field="phone" message={errors.phone} />
              </label>
              <label className="field-wide">Address
                <textarea value={form.address} onChange={(event) => setField("address", event.target.value)} onBlur={() => showFieldError("address")} autoComplete="street-address" required aria-invalid={Boolean(errors.address)} data-testid="checkout-address" />
                <FieldError field="address" message={errors.address} />
              </label>
              <label>Country
                <input list="checkout-country-options" value={form.country} onChange={(event) => setCountry(event.target.value)} onBlur={() => showFieldError("country")} autoComplete="country-name" required aria-invalid={Boolean(errors.country)} data-testid="checkout-country" />
                <datalist id="checkout-country-options" data-testid="checkout-country-options">{countries.map((country) => <option key={country.isoCode} value={country.name} />)}</datalist>
                <FieldError field="country" message={errors.country} />
              </label>
              <label>State / region
                <input list="checkout-state-options" value={form.state} onChange={(event) => setStateRegion(event.target.value)} onBlur={() => showFieldError("state")} autoComplete="address-level1" required readOnly={Boolean(selectedCountry && !states.length)} disabled={!selectedCountry} aria-invalid={Boolean(errors.state)} data-testid="checkout-state" />
                <datalist id="checkout-state-options" data-testid="checkout-state-options">{states.length ? states.map((state) => <option key={state.isoCode} value={state.name} />) : <option value={NO_STATE_REGION} />}</datalist>
                <FieldError field="state" message={errors.state} />
              </label>
              <label>City
                <input list="checkout-city-options" value={form.city} onChange={(event) => setField("city", event.target.value)} onBlur={() => showFieldError("city")} autoComplete="address-level2" required disabled={!selectedCountry || Boolean(states.length && !selectedState) || noCityData} aria-invalid={Boolean(errors.city)} data-testid="checkout-city" />
                <datalist id="checkout-city-options" data-testid="checkout-city-options">{cities.map((city) => <option key={city} value={city} />)}</datalist>
                <FieldError field="city" message={errors.city} />
                {noCityData && <a href={contactForLocation} target="_blank" rel="noreferrer" className="checkout-location-help" data-testid="checkout-location-help">Chat with SAFYRA for address help</a>}
              </label>
              <label>Postal code
                <input value={form.postalCode} onChange={(event) => setField("postalCode", event.target.value)} onBlur={() => showFieldError("postalCode")} autoComplete="postal-code" required readOnly={Boolean(selectedCountry && !countryUsesPostalCodes)} aria-invalid={Boolean(errors.postalCode)} data-testid="checkout-postal-code" />
                <FieldError field="postalCode" message={errors.postalCode} />
              </label>
              <label className="field-wide">A note for SAFYRA
                <textarea value={form.note} onChange={(event) => setField("note", event.target.value)} placeholder="Any special instructions for your order?" data-testid="checkout-order-note" />
              </label>
            </div>
            <fieldset className="shipping-options">
              <legend>Shipping selection</legend>
              <label className={shipping === "india" ? "is-selected" : ""}><input type="radio" name="shipping" value="india" checked={shipping === "india"} disabled={Boolean(selectedCountry && selectedCountry.isoCode !== "IN")} onChange={() => { setShipping("india"); setErrors((current) => ({ ...current, shipping: undefined })); }} data-testid="shipping-india" /><span><strong>India delivery</strong><small>₹120 for orders up to ₹999 · Free from ₹1,000</small></span></label>
              <label className={shipping === "international" ? "is-selected" : ""}><input type="radio" name="shipping" value="international" checked={shipping === "international"} disabled={Boolean(selectedCountry && selectedCountry.isoCode === "IN")} onChange={() => { setShipping("international"); setErrors((current) => ({ ...current, shipping: undefined })); }} data-testid="shipping-international" /><span><strong>International shipping</strong><small>SAFYRA will confirm the destination quote personally</small></span></label>
            </fieldset>
            <FieldError field="shipping" message={errors.shipping} />
            {quotePayment.isError && <div className="form-error" data-testid="checkout-quote-error">We couldn’t verify the current prices or availability. Please review your bag and try again.</div>}
            <button className="button button-dark button-full" type="submit" disabled={quotePayment.isPending} data-testid="checkout-review-button">{quotePayment.isPending ? "VERIFYING TOTAL…" : "REVIEW ORDER"}</button>
          </form>}

          {step === "review" && <div className="checkout-review" data-testid="checkout-review">
            <div className="checkout-step"><span><Check size={15} /></span><div><strong>Delivery details</strong><small>{form.name} · {form.city}, {form.country}</small></div><button onClick={() => setStep("details")} data-testid="checkout-edit-address">Edit</button></div>
            <div className="review-address"><p>{form.address}</p><p>{form.city}, {form.state} {form.postalCode}</p><p>{form.phone} · {form.email}</p>{form.note && <p data-testid="checkout-review-note">{form.note}</p>}</div>
            <div className="handoff-note"><ShieldCheck size={20} /><p><strong>{isIndia ? "PayU Hosted Checkout" : "Personal shipping confirmation"}</strong>{isIndia ? "Your card or UPI details are entered only on PayU. SAFYRA verifies the payment server-to-server before confirming fulfilment." : "SAFYRA will confirm the international shipping charge before requesting payment."}</p></div>
            {(submitRequest.isError || createPayment.isError) && <div className="form-error" data-testid="checkout-request-error">We couldn’t begin checkout. No payment was taken. Please review your details and try again.</div>}
            <button type="button" className="button button-dark button-full" onClick={submitOrderRequest} disabled={submitRequest.isPending || createPayment.isPending} data-testid="checkout-submit-request">{submitRequest.isPending || createPayment.isPending ? "Preparing secure checkout…" : isIndia ? <><CreditCard size={17} /> Pay securely with PayU · {formatPrice(payableTotal)}</> : "Submit international order request"}</button>
            <a href={checkoutHelpUrl} target="_blank" rel="noreferrer" className="button button-outline button-full" data-testid="checkout-support-whatsapp">Need checkout help?</a>
          </div>}

          {step === "complete" && request && <div className="checkout-complete" data-testid="checkout-complete">
            <Check size={24} />
            <p data-testid="checkout-request-reference">Request reference: <strong>{request.request_number}</strong></p>
            <h2>WHAT HAPPENS NEXT</h2>
            <ol data-testid="checkout-next-steps">
              <li>SAFYRA reviews your destination and shipping feasibility.</li>
              <li>We confirm the international shipping charge personally.</li>
              <li>Payment is requested only after those details are agreed.</li>
            </ol>
            <a href={handoff} target="_blank" rel="noreferrer" className="button button-dark button-full" data-testid="checkout-chat-with-safyra"><MessageCircle size={17} /> CHAT WITH SAFYRA</a>
          </div>}
        </section>

        <aside className="checkout-summary">
          <span className="eyebrow">Your order</span>
          {cart.map((item) => <div className="checkout-item" key={item.key} data-testid={`checkout-item-${item.productId}`}><SafeProductImage src={item.imageUrl} alt={item.title} productName={item.title} /><div><strong>{item.title}</strong><small>Size {item.size} · {item.color} · Qty {item.quantity}</small><span>{formatPrice(item.price * item.quantity)}</span></div></div>)}
          {quotePayment.data && quotePayment.data.discount_total > 0 && <div className="summary-line" data-testid="checkout-discount-total"><span>Automatic savings</span><strong>−{formatPrice(quotePayment.data.discount_total)}</strong></div>}
          <div className="summary-line"><span>Product subtotal</span><strong data-testid="checkout-subtotal">{formatPrice(quotePayment.data?.subtotal ?? cartTotal)}</strong></div>
          {isIndia && <div className="summary-line"><span>India shipping</span><strong data-testid="checkout-shipping-total">{shippingAmount === 0 ? "Free" : formatPrice(shippingAmount)}</strong></div>}
          {isIndia && <div className="summary-line checkout-payable-total"><span>Total</span><strong data-testid="checkout-payable-total">{formatPrice(payableTotal)}</strong></div>}
          <small>{isIndia ? "Taxes included. The total is recalculated by SAFYRA before PayU opens." : "International shipping is confirmed personally before payment."}</small>
        </aside>
      </div>
    </main>
  </div>;
}