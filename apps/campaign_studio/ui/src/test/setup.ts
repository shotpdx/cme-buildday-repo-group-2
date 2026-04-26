import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// jsdom does not implement EventSource. Provide a minimal stub that
// component tests can spy on / drive manually via `getLastInstance()`.
class MockEventSource {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSED = 2;
  static instances: MockEventSource[] = [];

  CONNECTING = 0;
  OPEN = 1;
  CLOSED = 2;

  url: string;
  readyState = MockEventSource.OPEN;
  listeners: Record<string, Array<(e: MessageEvent | Event) => void>> = {};
  onopen: ((e: Event) => void) | null = null;
  onmessage: ((e: MessageEvent) => void) | null = null;
  onerror: ((e: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  addEventListener(type: string, fn: (e: MessageEvent | Event) => void) {
    (this.listeners[type] ||= []).push(fn);
  }
  removeEventListener(type: string, fn: (e: MessageEvent | Event) => void) {
    this.listeners[type] = (this.listeners[type] || []).filter((f) => f !== fn);
  }
  close() {
    this.readyState = MockEventSource.CLOSED;
  }

  emit(type: string, data: unknown) {
    const evt = new MessageEvent(type, { data: JSON.stringify(data) });
    (this.listeners[type] || []).forEach((fn) => fn(evt));
  }
}

(globalThis as unknown as { EventSource: typeof MockEventSource }).EventSource =
  MockEventSource;

afterEach(() => {
  cleanup();
  MockEventSource.instances.length = 0;
});

export { MockEventSource };
