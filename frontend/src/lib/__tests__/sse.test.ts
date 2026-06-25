import { describe, expect, it } from "vitest";

import { findEventSeparator, parseSseEvent } from "../sse";

describe("findEventSeparator", () => {
  it("returns -1 when no separator is present", () => {
    expect(findEventSeparator("data: hi")).toBe(-1);
  });
  it("finds an LF-LF separator", () => {
    expect(findEventSeparator("data: a\n\ndata: b")).toBe(7);
  });
  it("finds a CRLF separator", () => {
    expect(findEventSeparator("data: a\r\n\r\ndata: b")).toBe(7);
  });
  it("returns the earliest separator when both styles are present", () => {
    const buf = "data: x\r\n\r\ndata: y\n\n";
    // The CRLF one starts at index 7.
    expect(findEventSeparator(buf)).toBe(7);
  });
});

describe("parseSseEvent", () => {
  it("parses a simple event", () => {
    expect(parseSseEvent("event: token\ndata: hello")).toEqual({
      event: "token",
      data: "hello",
      id: undefined,
    });
  });
  it("defaults the event name to 'message'", () => {
    expect(parseSseEvent("data: hello")).toMatchObject({ event: "message", data: "hello" });
  });
  it("joins multi-line data with newlines", () => {
    expect(parseSseEvent("data: line1\ndata: line2")).toMatchObject({
      data: "line1\nline2",
    });
  });
  it("ignores comment lines (starting with ':')", () => {
    expect(parseSseEvent(":heartbeat\ndata: ok")).toMatchObject({ data: "ok" });
  });
  it("strips a single leading space from values per spec", () => {
    expect(parseSseEvent("data:no-space")).toMatchObject({ data: "no-space" });
    expect(parseSseEvent("data: with-space")).toMatchObject({ data: "with-space" });
  });
  it("returns null when the event has no data field", () => {
    expect(parseSseEvent("event: ping")).toBeNull();
  });
  it("captures the id field", () => {
    expect(parseSseEvent("id: 42\ndata: x")).toMatchObject({ id: "42", data: "x" });
  });
});
