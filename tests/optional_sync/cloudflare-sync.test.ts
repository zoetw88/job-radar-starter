import {
  env,
  listDurableObjectIds,
  runInDurableObject,
  SELF,
} from "cloudflare:test";
import { beforeEach, describe, expect, it } from "vitest";
import type { StatusCoordinator } from "../../optional-sync/cloudflare/src/index";

const endpoint = "https://sync.example.test/v1/statuses";
const token = "test-only-sync-token";

function request(
  method: string,
  body?: unknown,
  headers: Record<string, string> = {},
): Request {
  return new Request(endpoint, {
    method,
    headers: {
      authorization: `Bearer ${token}`,
      ...(body === undefined ? {} : { "content-type": "application/json" }),
      ...headers,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

async function json(response: Response): Promise<Record<string, unknown>> {
  return response.json() as Promise<Record<string, unknown>>;
}

function assertPrivate(response: Response): void {
  expect(response.headers.get("cache-control")).toBe("private, no-store");
  expect(response.headers.get("access-control-allow-origin")).toBeNull();
}

function coordinator() {
  return env.STATUS_COORDINATOR.getByName("owner:statuses");
}

async function storedDocument() {
  return coordinator().getDocument();
}

async function seedStatuses(statuses: Record<string, string>): Promise<void> {
  const stub = coordinator();
  await runInDurableObject(
    stub,
    async (_instance: StatusCoordinator, state) => {
      state.storage.sql.exec("DELETE FROM statuses");
      for (const [key, status] of Object.entries(statuses)) {
        state.storage.sql.exec(
          "INSERT INTO statuses (stable_key, status) VALUES (?, ?)",
          key,
          status,
        );
      }
    },
  );
}

describe("optional single-owner Cloudflare status sync", () => {
  beforeEach(async () => {
    await SELF.fetch(request("DELETE"));
  });

  it.each([
    ["missing header", {}],
    ["wrong scheme", { authorization: token }],
    ["wrong token", { authorization: "Bearer wrong-secret" }],
  ])("fails closed for %s", async (_case, headers) => {
    const response = await SELF.fetch(new Request(endpoint, { headers }));

    expect(response.status).toBe(401);
    expect(await json(response)).toEqual({
      contract_version: 1,
      error: "unauthorized",
    });
    assertPrivate(response);
  });

  it("uses one server-owned key and ignores client identity fields", async () => {
    const response = await SELF.fetch(
      request("POST", {
        contract_version: 1,
        user_id: "attacker-selected-owner",
        statuses: { job_0123456789abcdef: "interested" },
      }),
    );

    expect(response.status).toBe(400);
    expect(await listDurableObjectIds(env.STATUS_COORDINATOR)).toHaveLength(1);
    expect(await storedDocument()).toEqual({
      contract_version: 1,
      statuses: {},
    });
  });

  it("persists across independent clients using GET and POST", async () => {
    const deviceA = await SELF.fetch(
      request("POST", {
        contract_version: 1,
        statuses: {
          job_0123456789abcdef: "interested",
          job_fedcba9876543210: "applied",
        },
        legacy_keys: [],
      }),
    );
    expect(deviceA.status).toBe(200);
    assertPrivate(deviceA);

    const deviceB = await SELF.fetch(request("GET"));
    expect(deviceB.status).toBe(200);
    expect(await json(deviceB)).toEqual({
      contract_version: 1,
      statuses: {
        job_0123456789abcdef: "interested",
        job_fedcba9876543210: "applied",
      },
    });
    assertPrivate(deviceB);
    expect(await storedDocument()).toEqual({
      contract_version: 1,
      statuses: {
        job_0123456789abcdef: "interested",
        job_fedcba9876543210: "applied",
      },
    });
  });

  it("supports explicit deletion of the fixed owner state", async () => {
    await seedStatuses({ job_0123456789abcdef: "applied" });

    const response = await SELF.fetch(request("DELETE"));

    expect(response.status).toBe(204);
    expect(await storedDocument()).toEqual({
      contract_version: 1,
      statuses: {},
    });
    assertPrivate(response);
  });

  it.each(["interested", "applied", "skip", "dead"])(
    "allows status %s",
    async (status) => {
      const response = await SELF.fetch(
        request("POST", {
          contract_version: 1,
          statuses: { job_0123456789abcdef: status },
          legacy_keys: [],
        }),
      );
      expect(response.status).toBe(200);
    },
  );

  it.each([
    ["unknown contract", { contract_version: 2, statuses: {}, legacy_keys: [] }],
    ["unknown field", { contract_version: 1, statuses: {}, legacy_keys: [], extra: true }],
    [
      "unknown status",
      {
        contract_version: 1,
        statuses: { job_0123456789abcdef: "offer" },
        legacy_keys: [],
      },
    ],
    [
      "invalid key",
      {
        contract_version: 1,
        statuses: { "https://legacy.example/job": "applied" },
        legacy_keys: [],
      },
    ],
    [
      "too-long key",
      {
        contract_version: 1,
        statuses: { [`job_${"a".repeat(129)}`]: "applied" },
        legacy_keys: [],
      },
    ],
    [
      "too many statuses",
      {
        contract_version: 1,
        statuses: Object.fromEntries(
          Array.from({ length: 501 }, (_, index) => [
            `job_${index.toString(16).padStart(16, "0")}`,
            "interested",
          ]),
        ),
        legacy_keys: [],
      },
    ],
    [
      "too many legacy keys",
      {
        contract_version: 1,
        statuses: {},
        legacy_keys: Array.from({ length: 501 }, (_, index) => `legacy-${index}`),
      },
    ],
  ])("rejects %s without mutating prior data", async (_case, body) => {
    const previous = {
      contract_version: 1,
      statuses: { job_aaaaaaaaaaaaaaaa: "interested" },
    };
    await seedStatuses(previous.statuses);

    const response = await SELF.fetch(request("POST", body));

    expect(response.status).toBe(400);
    expect(await storedDocument()).toEqual(previous);
    assertPrivate(response);
  });

  it("rejects oversized requests before JSON parsing", async () => {
    const response = await SELF.fetch(
      new Request(endpoint, {
        method: "POST",
        headers: {
          authorization: `Bearer ${token}`,
          "content-type": "application/json",
          "content-length": "65537",
        },
        body: "{",
      }),
    );

    expect(response.status).toBe(413);
    expect(await json(response)).toEqual({
      contract_version: 1,
      error: "payload_too_large",
    });
    expect(await storedDocument()).toEqual({
      contract_version: 1,
      statuses: {},
    });
  });

  it("removes declared legacy keys while preserving other stable statuses", async () => {
    await seedStatuses({
      "greenhouse:42": "interested",
      "https://example.test/jobs/42": "applied",
      job_aaaaaaaaaaaaaaaa: "skip",
    });

    const response = await SELF.fetch(
      request("POST", {
        contract_version: 1,
        statuses: { job_0123456789abcdef: "applied" },
        legacy_keys: [
          "greenhouse:42",
          "https://example.test/jobs/42",
        ],
      }),
    );

    expect(response.status).toBe(200);
    expect(await json(response)).toEqual({
      contract_version: 1,
      statuses: {
        job_0123456789abcdef: "applied",
        job_aaaaaaaaaaaaaaaa: "skip",
      },
    });
  });

  it("is retry-safe and produces the same stored document", async () => {
    const body = {
      contract_version: 1,
      statuses: { job_0123456789abcdef: "interested" },
      legacy_keys: [],
    };

    const first = await SELF.fetch(request("POST", body));
    const firstStored = await storedDocument();
    const second = await SELF.fetch(request("POST", body));
    const secondStored = await storedDocument();

    expect(first.status).toBe(200);
    expect(second.status).toBe(200);
    expect(await first.text()).toBe(await second.text());
    expect(secondStored).toEqual(firstStored);
  });

  it("rejects an update when the merged stored state would exceed 500 statuses", async () => {
    const existing = Object.fromEntries(
      Array.from({ length: 500 }, (_, index) => [
        `job_${index.toString(16).padStart(16, "0")}`,
        "interested",
      ]),
    );
    await seedStatuses(existing);

    const response = await SELF.fetch(
      request("POST", {
        contract_version: 1,
        statuses: { job_ffffffffffffffff: "applied" },
        legacy_keys: [],
      }),
    );

    expect(response.status).toBe(409);
    expect(await json(response)).toEqual({
      contract_version: 1,
      error: "stored_state_limit_exceeded",
    });
    expect(await storedDocument()).toEqual({
      contract_version: 1,
      statuses: existing,
    });
    assertPrivate(response);
  });

  it("serializes concurrent writes from two devices without losing either key", async () => {
    const [deviceA, deviceB] = await Promise.all([
      SELF.fetch(
        request("POST", {
          contract_version: 1,
          statuses: { job_aaaaaaaaaaaaaaaa: "interested" },
          legacy_keys: [],
        }),
      ),
      SELF.fetch(
        request("POST", {
          contract_version: 1,
          statuses: { job_bbbbbbbbbbbbbbbb: "applied" },
          legacy_keys: [],
        }),
      ),
    ]);

    expect(deviceA.status).toBe(200);
    expect(deviceB.status).toBe(200);
    expect(await storedDocument()).toEqual({
      contract_version: 1,
      statuses: {
        job_aaaaaaaaaaaaaaaa: "interested",
        job_bbbbbbbbbbbbbbbb: "applied",
      },
    });
  });

  it("serializes concurrent near-limit writes so only one can reach 500", async () => {
    const existing = Object.fromEntries(
      Array.from({ length: 499 }, (_, index) => [
        `job_${index.toString(16).padStart(16, "0")}`,
        "interested",
      ]),
    );
    await seedStatuses(existing);

    const responses = await Promise.all([
      SELF.fetch(
        request("POST", {
          contract_version: 1,
          statuses: { job_aaaaaaaaaaaaaaaa: "applied" },
          legacy_keys: [],
        }),
      ),
      SELF.fetch(
        request("POST", {
          contract_version: 1,
          statuses: { job_bbbbbbbbbbbbbbbb: "skip" },
          legacy_keys: [],
        }),
      ),
    ]);

    expect(responses.map(({ status }) => status).sort()).toEqual([200, 409]);
    const stored = await storedDocument();
    expect(Object.keys(stored.statuses)).toHaveLength(500);
    expect(
      [
        stored.statuses.job_aaaaaaaaaaaaaaaa,
        stored.statuses.job_bbbbbbbbbbbbbbbb,
      ].filter(Boolean),
    ).toHaveLength(1);
  });

  it.each([
    ["PUT", undefined, {}, 405],
    ["PATCH", undefined, {}, 405],
    ["OPTIONS", undefined, {}, 405],
    [
      "POST",
      { contract_version: 1, statuses: {}, legacy_keys: [] },
      { "content-type": "text/plain" },
      415,
    ],
  ])(
    "handles method/content-type contract for %s",
    async (method, body, headers, status) => {
      const response = await SELF.fetch(request(method, body, headers));
      expect(response.status).toBe(status);
      assertPrivate(response);
    },
  );

});
