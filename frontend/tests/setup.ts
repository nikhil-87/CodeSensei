/// <reference types="@testing-library/jest-dom" />
import "@testing-library/jest-dom/vitest";

// Stub matchMedia (mermaid + some Tailwind utilities probe it on load).
if (typeof window !== "undefined" && !window.matchMedia) {
  window.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as unknown as MediaQueryList;
}
