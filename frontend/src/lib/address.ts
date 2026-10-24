import { City, Country, State } from "country-state-city";
import { isValidPhoneNumber, type CountryCode } from "libphonenumber-js";
import { getCountryByCode, validatePostalCode } from "postal-code-checker";
import type { SavedAddressInput } from "@/lib/auth";

export const NO_STATE_REGION = "Not applicable";
export const addressCountries = Country.getAllCountries().sort((left, right) => left.name.localeCompare(right.name));

const normalize = (value: string) => value.trim().toLocaleLowerCase();
const exactMatch = <T extends { name: string }>(items: T[], value: string) => items.find((item) => normalize(item.name) === normalize(value));

export function addressOptions(country: string, state: string) {
  const selectedCountry = exactMatch(addressCountries, country);
  const states = selectedCountry ? State.getStatesOfCountry(selectedCountry.isoCode) : [];
  const selectedState = exactMatch(states, state);
  const cityRecords = selectedCountry && (!states.length || selectedState)
    ? selectedState ? City.getCitiesOfState(selectedCountry.isoCode, selectedState.isoCode) : City.getCitiesOfCountry(selectedCountry.isoCode) ?? []
    : [];
  const cities = [...new Set(cityRecords.map((city) => city.name))].sort((left, right) => left.localeCompare(right));
  const usesPostalCodes = Boolean(selectedCountry && getCountryByCode(selectedCountry.isoCode)?.postalCodePatterns.length);
  return { selectedCountry, states, selectedState, cities, usesPostalCodes };
}

/** Field resets when the country changes, mirroring checkout's rules. */
export function countryDefaults(country: string): Pick<SavedAddressInput, "state_region" | "city" | "postal_code"> {
  const { selectedCountry, states, usesPostalCodes } = addressOptions(country, "");
  return {
    state_region: selectedCountry && !states.length ? NO_STATE_REGION : "",
    city: "",
    postal_code: selectedCountry && !usesPostalCodes ? NO_STATE_REGION : "",
  };
}

export type AddressErrors = Partial<Record<keyof SavedAddressInput, string>>;

export function validateSavedAddress(address: SavedAddressInput): AddressErrors {
  const errors: AddressErrors = {};
  const { selectedCountry, states, selectedState, cities, usesPostalCodes } = addressOptions(address.country, address.state_region);
  if (!address.label.trim()) errors.label = "Give this address a name, like Home.";
  if (address.name.trim().length < 2) errors.name = "Enter the recipient's full name.";
  if (address.address.trim().length < 5) errors.address = "Enter a complete delivery address.";
  if (!selectedCountry) {
    errors.country = "Select a country from the list.";
    return errors;
  }
  try {
    if (!isValidPhoneNumber(address.phone.trim(), selectedCountry.isoCode as CountryCode)) errors.phone = "Enter a valid phone number for this country.";
  } catch {
    errors.phone = "Enter a valid phone number for this country.";
  }
  if (states.length && !selectedState) errors.state_region = "Select a state or region from the list.";
  if (cities.length && !cities.some((city) => normalize(city) === normalize(address.city))) errors.city = "Select a city from the suggestions.";
  if (!cities.length && !address.city.trim()) errors.city = "Enter a city.";
  if (usesPostalCodes && !validatePostalCode(selectedCountry.isoCode, address.postal_code.trim())) errors.postal_code = "Enter a valid postal code.";
  return errors;
}

export function formatAddressLine(address: Pick<SavedAddressInput, "address" | "city" | "state_region" | "postal_code" | "country">): string {
  return [address.address, address.city, address.state_region, address.postal_code, address.country]
    .map((part) => part.trim())
    .filter((part) => part && part !== NO_STATE_REGION)
    .join(", ");
}
