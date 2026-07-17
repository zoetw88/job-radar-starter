import worker from "../../optional-sync/cloudflare/src/index";
import { describe, expect, it } from "vitest";

const request = new Request("https://sync.example.test/v1/statuses", {
  headers: { authorization: "Bearer any-token" },
});

describe("missing deployment bindings fail closed", () => {
  it.each([
    ["missing secret", { STATUS_COORDINATOR: fakeCoordinator() }],
    ["missing coordinator binding", { SYNC_TOKEN: "secret" }],
    ["missing both", {}],
  ])("%s", async (_case, bindings) => {
    const response = await worker.fetch(
      request,
      bindings as never,
      {} as ExecutionContext,
    );

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({
      contract_version: 1,
      error: "sync_unavailable",
    });
    expect(response.headers.get("cache-control")).toBe("private, no-store");
  });

  it("does not disclose secrets or internal exceptions", async () => {
    const response = await worker.fetch(
      request,
      {
        SYNC_TOKEN: "any-token",
        STATUS_COORDINATOR: throwingCoordinator(),
      } as never,
      {} as ExecutionContext,
    );
    const serialized = JSON.stringify(await response.json());

    expect(response.status).toBe(500);
    expect(serialized).toContain("sync_failed");
    expect(serialized).not.toContain("any-token");
    expect(serialized).not.toContain("internal stack");
    expect(response.headers.get("cache-control")).toBe("private, no-store");
  });
});

function fakeCoordinator(): DurableObjectNamespace {
  return {
    getByName: () => ({
      getDocument: async () => ({ contract_version: 1, statuses: {} }),
    }),
  } as unknown as DurableObjectNamespace;
}

function throwingCoordinator(): DurableObjectNamespace {
  return {
    getByName: () => {
      throw new Error("SYNC_TOKEN=any-token internal stack");
    },
  } as unknown as DurableObjectNamespace;
}
