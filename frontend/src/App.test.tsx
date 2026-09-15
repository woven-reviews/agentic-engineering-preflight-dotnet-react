import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { App } from "./App";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("App", () => {
  it("shows the success state when the preflight check resolves ok", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ database: "ok" }),
      }),
    );

    render(<App />);

    expect(await screen.findByText("✅ Stack is up")).toBeInTheDocument();
    expect(screen.getByText("database: ok")).toBeInTheDocument();
  });

  it("shows the error state when the preflight check rejects", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network down")));

    render(<App />);

    expect(await screen.findByText("❌ Stack check failed")).toBeInTheDocument();
    expect(screen.getByText("Error: network down")).toBeInTheDocument();
  });
});
