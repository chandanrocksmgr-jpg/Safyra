/**
 * Pure unit coverage for the made-to-order-aware stock rules used by the cart/PDP quantity
 * limit (ShopProvider.addToCart / updateQuantity call availableQuantity() directly) and by
 * purchasability gating (isProductUnavailable()). These are synthetic fixtures -- no real
 * catalog product is mutated -- per the instruction to verify stock-controlled scenarios with
 * pure helper checks rather than altering the four approved products.
 */
import { describe, expect, it } from "vitest";
import { availableQuantity, isMadeToOrder, isProductUnavailable } from "./shop";

type StockInput = Pick<import("./shop").Product, "availability" | "sizes" | "stock" | "stock_by_size">;

const base: StockInput = {
  availability: "Made to order",
  sizes: ["S", "M", "L"],
  stock: 0,
  stock_by_size: {},
};

describe("made-to-order-aware stock rules", () => {
  it("made-to-order product is purchasable with unlimited quantity despite zero on-hand stock", () => {
    const product: StockInput = { ...base, availability: "Made to order", stock: 0, stock_by_size: {} };
    expect(isMadeToOrder(product)).toBe(true);
    expect(isProductUnavailable(product)).toBe(false);
    expect(availableQuantity(product, "M")).toBe(Number.POSITIVE_INFINITY);
    // Cart increment logic (ShopProvider) caps at availableQuantity -- infinity means no cap.
    expect(availableQuantity(product, "M") > 999).toBe(true);
  });

  it("currently unavailable product is blocked for every size regardless of stock numbers", () => {
    const product: StockInput = { availability: "Currently unavailable", sizes: ["S", "M"], stock: 50, stock_by_size: { M: 20 } };
    expect(isProductUnavailable(product)).toBe(true);
    expect(availableQuantity(product, "M")).toBe(0);
    expect(availableQuantity(product, "S")).toBe(0);
  });

  it("a product with no approved sizes is treated as unavailable even if marked in stock", () => {
    const product: StockInput = { availability: "In stock", sizes: [], stock: 10, stock_by_size: {} };
    expect(isProductUnavailable(product)).toBe(true);
    expect(availableQuantity(product, "M")).toBe(0);
  });

  it("stock-controlled product uses selected-size stock when present for that size", () => {
    const product: StockInput = { availability: "In stock", sizes: ["S", "M", "L"], stock: 25, stock_by_size: { S: 3, M: 0 } };
    expect(isMadeToOrder(product)).toBe(false);
    // size present in stock_by_size -> that exact number caps the cart, never the global stock
    expect(availableQuantity(product, "S")).toBe(3);
    // a size explicitly recorded as 0 must be blocked, not fall back to global stock
    expect(availableQuantity(product, "M")).toBe(0);
  });

  it("stock-controlled product falls back to global stock when the size has no per-size entry", () => {
    const product: StockInput = { availability: "In stock", sizes: ["S", "M", "L"], stock: 7, stock_by_size: { S: 3 } };
    // "L" has no stock_by_size entry -> falls back to the global stock figure
    expect(availableQuantity(product, "L")).toBe(7);
  });

  it("negative stored stock never produces a negative cart limit", () => {
    const negativeGlobal: StockInput = { availability: "In stock", sizes: ["M"], stock: -4, stock_by_size: {} };
    expect(availableQuantity(negativeGlobal, "M")).toBe(0);
    const negativeSize: StockInput = { availability: "In stock", sizes: ["M"], stock: 10, stock_by_size: { M: -2 } };
    expect(availableQuantity(negativeSize, "M")).toBe(0);
  });

  it("a stock-controlled product with zero quantity available on all sizes is considered unavailable overall", () => {
    const product: StockInput = { availability: "In stock", sizes: ["S", "M"], stock: 0, stock_by_size: { S: 0, M: 0 } };
    expect(isProductUnavailable(product)).toBe(true);
  });

  it("a stock-controlled product remains available overall while at least one size has stock", () => {
    const product: StockInput = { availability: "In stock", sizes: ["S", "M"], stock: 0, stock_by_size: { S: 0, M: 5 } };
    expect(isProductUnavailable(product)).toBe(false);
    expect(availableQuantity(product, "S")).toBe(0);
    expect(availableQuantity(product, "M")).toBe(5);
  });
});
