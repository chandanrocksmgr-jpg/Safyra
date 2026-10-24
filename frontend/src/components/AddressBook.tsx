import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { MapPin, Pencil, Plus, Star, Trash2, X } from "lucide-react";
import { toast } from "sonner";
import { apiDelete, apiPost, apiPut, ApiError } from "@/lib/api";
import { addressCountries, addressOptions, countryDefaults, formatAddressLine, NO_STATE_REGION, validateSavedAddress, type AddressErrors } from "@/lib/address";
import type { SavedAddress, SavedAddressInput } from "@/lib/auth";

interface AddressBookProps {
  addresses: SavedAddress[];
  defaultName: string;
  defaultPhone: string;
}

const LABEL_SUGGESTIONS = ["Home", "Work", "Parents", "Other"];

function FieldError({ field, errors }: { field: keyof SavedAddressInput; errors: AddressErrors }) {
  return errors[field] ? <small className="address-field-error" data-testid={`address-${field}-error`}>{errors[field]}</small> : null;
}

export default function AddressBook({ addresses, defaultName, defaultPhone }: AddressBookProps) {
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<SavedAddressInput | null>(null);
  const [errors, setErrors] = useState<AddressErrors>({});
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["account"] });
  const errorMessage = (reason: unknown, fallback: string) => reason instanceof ApiError && reason.status === 400 && typeof (reason.body as { detail?: unknown })?.detail === "string" ? (reason.body as { detail: string }).detail : fallback;

  const saveMutation = useMutation({
    mutationFn: (input: SavedAddressInput) => editingId ? apiPut<SavedAddress[]>(`/account/addresses/${editingId}`, input) : apiPost<SavedAddress[]>("/account/addresses", input),
    onSuccess: async () => { await refresh(); toast.success(editingId ? "Address updated" : "Address saved"); closeForm(); },
    onError: (reason) => toast.error(errorMessage(reason, "Address could not be saved")),
  });
  const defaultMutation = useMutation({
    mutationFn: (id: string) => apiPost<SavedAddress[]>(`/account/addresses/${id}/default`, {}),
    onSuccess: async () => { await refresh(); toast.success("Default address updated"); },
    onError: () => toast.error("Default address could not be changed"),
  });
  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiDelete<SavedAddress[]>(`/account/addresses/${id}`),
    onSuccess: async () => { await refresh(); toast.success("Address removed"); },
    onError: () => toast.error("Address could not be removed"),
  });

  const openNew = () => {
    setEditingId(null);
    setErrors({});
    setForm({ label: addresses.length ? "Other" : "Home", name: defaultName, phone: defaultPhone, address: "", city: "", state_region: "", postal_code: "", country: "India", is_default: !addresses.length });
  };
  const openEdit = (address: SavedAddress) => {
    setEditingId(address.id);
    setErrors({});
    const { id: _id, ...input } = address;
    setForm(input);
  };
  const closeForm = () => { setForm(null); setEditingId(null); setErrors({}); };
  const update = (patch: Partial<SavedAddressInput>) => {
    setForm((current) => current && { ...current, ...patch });
    setErrors((current) => ({ ...current, ...Object.fromEntries(Object.keys(patch).map((key) => [key, undefined])) }));
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!form) return;
    const next = validateSavedAddress(form);
    setErrors(next);
    if (Object.keys(next).length) return;
    saveMutation.mutate({ ...form, label: form.label.trim(), name: form.name.trim(), phone: form.phone.trim(), address: form.address.trim(), city: form.city.trim(), postal_code: form.postal_code.trim() });
  };

  const options = form ? addressOptions(form.country, form.state_region) : null;

  return <section id="addresses" className="account-section address-book" data-testid="account-address-book">
    <div className="account-section-heading">
      <div><span className="eyebrow">Delivery</span><h2>Address book</h2><p className="address-book-intro">Your default address is filled in automatically at checkout.</p></div>
      {!form && addresses.length < 10 && <button type="button" className="button button-outline" onClick={openNew} data-testid="address-add-button"><Plus size={15} /> Add address</button>}
    </div>

    {form && options && <form className="address-form" onSubmit={submit} noValidate data-testid="address-form">
      <div className="address-form-heading"><strong data-testid="address-form-title">{editingId ? "Edit address" : "New address"}</strong><button type="button" className="icon-button" onClick={closeForm} aria-label="Cancel" data-testid="address-form-cancel-icon"><X size={18} /></button></div>
      <div className="address-form-grid">
        <label>Save as
          <input list="address-label-options" value={form.label} onChange={(event) => update({ label: event.target.value })} maxLength={40} data-testid="address-label" />
          <datalist id="address-label-options">{LABEL_SUGGESTIONS.map((label) => <option key={label} value={label} />)}</datalist>
          <FieldError field="label" errors={errors} />
        </label>
        <label>Recipient name
          <input value={form.name} onChange={(event) => update({ name: event.target.value })} autoComplete="name" data-testid="address-name" />
          <FieldError field="name" errors={errors} />
        </label>
        <label>Phone
          <input value={form.phone} onChange={(event) => update({ phone: event.target.value })} autoComplete="tel" inputMode="tel" data-testid="address-phone" />
          <FieldError field="phone" errors={errors} />
        </label>
        <label>Country
          <input list="address-country-options" value={form.country} onChange={(event) => update({ country: event.target.value, ...countryDefaults(event.target.value) })} autoComplete="country-name" data-testid="address-country" />
          <datalist id="address-country-options">{addressCountries.map((country) => <option key={country.isoCode} value={country.name} />)}</datalist>
          <FieldError field="country" errors={errors} />
        </label>
        <label className="field-wide">Address
          <textarea value={form.address} onChange={(event) => update({ address: event.target.value })} autoComplete="street-address" placeholder="House / flat, street, area, landmark" data-testid="address-line" />
          <FieldError field="address" errors={errors} />
        </label>
        <label>State / region
          <input list="address-state-options" value={form.state_region} onChange={(event) => update({ state_region: event.target.value, city: "" })} readOnly={Boolean(options.selectedCountry && !options.states.length)} disabled={!options.selectedCountry} autoComplete="address-level1" data-testid="address-state" />
          <datalist id="address-state-options">{options.states.length ? options.states.map((state) => <option key={state.isoCode} value={state.name} />) : <option value={NO_STATE_REGION} />}</datalist>
          <FieldError field="state_region" errors={errors} />
        </label>
        <label>City
          <input list="address-city-options" value={form.city} onChange={(event) => update({ city: event.target.value })} disabled={!options.selectedCountry || Boolean(options.states.length && !options.selectedState)} autoComplete="address-level2" data-testid="address-city" />
          <datalist id="address-city-options">{options.cities.map((city) => <option key={city} value={city} />)}</datalist>
          <FieldError field="city" errors={errors} />
        </label>
        <label>Postal code
          <input value={form.postal_code} onChange={(event) => update({ postal_code: event.target.value })} readOnly={Boolean(options.selectedCountry && !options.usesPostalCodes)} autoComplete="postal-code" inputMode="numeric" data-testid="address-postal-code" />
          <FieldError field="postal_code" errors={errors} />
        </label>
      </div>
      <label className="address-default-toggle"><input type="checkbox" checked={form.is_default} onChange={(event) => update({ is_default: event.target.checked })} data-testid="address-default-checkbox" /> Use as my default delivery address</label>
      <div className="address-form-actions">
        <button className="button button-dark" disabled={saveMutation.isPending} data-testid="address-save-button">{saveMutation.isPending ? "Saving…" : "Save address"}</button>
        <button type="button" className="button button-outline" onClick={closeForm} data-testid="address-cancel-button">Cancel</button>
      </div>
    </form>}

    {addresses.length > 0 ? <div className="address-grid" data-testid="address-list">{addresses.map((address) => <article key={address.id} className={address.is_default ? "address-card is-default" : "address-card"} data-testid={`address-card-${address.id}`}>
      <div className="address-card-top"><strong data-testid={`address-card-label-${address.id}`}>{address.label}</strong>{address.is_default && <span className="address-default-badge" data-testid={`address-default-badge-${address.id}`}>Default</span>}</div>
      <p className="address-card-name">{address.name}</p>
      <p data-testid={`address-card-line-${address.id}`}>{formatAddressLine(address)}</p>
      <p className="address-card-phone">{address.phone}</p>
      <div className="address-card-actions">
        <button type="button" onClick={() => openEdit(address)} data-testid={`address-edit-${address.id}`}><Pencil size={13} /> Edit</button>
        {!address.is_default && <button type="button" onClick={() => defaultMutation.mutate(address.id)} disabled={defaultMutation.isPending} data-testid={`address-make-default-${address.id}`}><Star size={13} /> Set as default</button>}
        <button type="button" className="is-danger" onClick={() => window.confirm(`Remove the ${address.label} address?`) && deleteMutation.mutate(address.id)} disabled={deleteMutation.isPending} data-testid={`address-delete-${address.id}`}><Trash2 size={13} /> Remove</button>
      </div>
    </article>)}</div> : !form && <div className="account-empty" data-testid="address-empty"><MapPin size={28} /><h3>No saved addresses yet.</h3><p>Add one now, or tick “Save this address” at checkout.</p></div>}
  </section>;
}
