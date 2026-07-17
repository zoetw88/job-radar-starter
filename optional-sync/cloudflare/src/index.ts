import { DurableObject } from "cloudflare:workers";

const OWNER_NAME = "owner:statuses";
const API_PATH = "/v1/statuses";
const MAX_BYTES = 65536;
const MAX_ITEMS = 500;
const MAX_KEY_LENGTH = 128;
const STATUS_VALUES = new Set(["interested", "applied", "skip", "dead"]);
const STABLE_KEY = /^job_[a-z0-9_-]{8,128}$/;
const RESPONSE_HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "private, no-store",
};

type StatusDocument = {
  contract_version: 1;
  statuses: Record<string, string>;
};

type UpdateRequest = StatusDocument & {
  legacy_keys: string[];
};

type MergeResult =
  | { ok: true; document: StatusDocument }
  | { ok: false; error: "stored_state_limit_exceeded" };

function response(
  status: number,
  payload?: object,
): Response {
  if (status === 204) {
    return new Response(null, {
      status,
      headers: { "cache-control": "private, no-store" },
    });
  }
  return Response.json(payload, { status, headers: RESPONSE_HEADERS });
}

function error(status: number, code: string): Response {
  return response(status, { contract_version: 1, error: code });
}

function isCoordinator(
  value: unknown,
): value is DurableObjectNamespace<StatusCoordinator> {
  return Boolean(
    value &&
      typeof value === "object" &&
      typeof (value as DurableObjectNamespace).getByName === "function",
  );
}

function timingSafeEqual(left: string, right: string): boolean {
  const encoder = new TextEncoder();
  const leftBytes = encoder.encode(left);
  const rightBytes = encoder.encode(right);
  const length = Math.max(leftBytes.length, rightBytes.length);
  let difference = leftBytes.length ^ rightBytes.length;
  for (let index = 0; index < length; index += 1) {
    difference |= (leftBytes[index] ?? 0) ^ (rightBytes[index] ?? 0);
  }
  return difference === 0;
}

function authorized(request: Request, secret: string): boolean {
  const header = request.headers.get("authorization");
  if (!header?.startsWith("Bearer ")) return false;
  return timingSafeEqual(header.slice("Bearer ".length), secret);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

function parseUpdate(value: unknown): UpdateRequest | null {
  if (!isRecord(value)) return null;
  if (
    Object.keys(value).sort().join(",") !==
    "contract_version,legacy_keys,statuses"
  ) {
    return null;
  }
  if (value.contract_version !== 1 || !isRecord(value.statuses)) return null;
  if (
    !Array.isArray(value.legacy_keys) ||
    value.legacy_keys.length > MAX_ITEMS ||
    !value.legacy_keys.every(
      (key) => typeof key === "string" && key.length <= MAX_KEY_LENGTH * 4,
    )
  ) {
    return null;
  }
  const entries = Object.entries(value.statuses);
  if (
    entries.length > MAX_ITEMS ||
    !entries.every(
      ([key, status]) =>
        key.length <= MAX_KEY_LENGTH &&
        STABLE_KEY.test(key) &&
        typeof status === "string" &&
        STATUS_VALUES.has(status),
    )
  ) {
    return null;
  }
  return value as UpdateRequest;
}

export class StatusCoordinator extends DurableObject<Env> {
  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);
    this.ctx.storage.sql.exec(`
      CREATE TABLE IF NOT EXISTS statuses (
        stable_key TEXT PRIMARY KEY,
        status TEXT NOT NULL
      )
    `);
  }

  getDocument(): StatusDocument {
    const rows = this.ctx.storage.sql
      .exec<{ stable_key: string; status: string }>(
        "SELECT stable_key, status FROM statuses ORDER BY stable_key",
      )
      .toArray();
    return {
      contract_version: 1,
      statuses: Object.fromEntries(
        rows
          .filter(({ status }) => STATUS_VALUES.has(status))
          .map(({ stable_key, status }) => [stable_key, status]),
      ),
    };
  }

  merge(payload: UpdateRequest): MergeResult {
    const statuses = { ...this.getDocument().statuses };
    for (const legacyKey of payload.legacy_keys) delete statuses[legacyKey];
    Object.assign(statuses, payload.statuses);
    const entries = Object.entries(statuses).sort(([left], [right]) =>
      left.localeCompare(right),
    );
    if (entries.length > MAX_ITEMS) {
      return { ok: false, error: "stored_state_limit_exceeded" };
    }

    this.ctx.storage.transactionSync(() => {
      for (const legacyKey of payload.legacy_keys) {
        this.ctx.storage.sql.exec(
          "DELETE FROM statuses WHERE stable_key = ?",
          legacyKey,
        );
      }
      for (const [stableKey, status] of Object.entries(payload.statuses)) {
        this.ctx.storage.sql.exec(
          `INSERT INTO statuses (stable_key, status) VALUES (?, ?)
           ON CONFLICT(stable_key) DO UPDATE SET status = excluded.status`,
          stableKey,
          status,
        );
      }
    });
    return {
      ok: true,
      document: {
        contract_version: 1,
        statuses: Object.fromEntries(entries),
      },
    };
  }

  clear(): void {
    this.ctx.storage.sql.exec("DELETE FROM statuses");
  }
}

async function parseRequest(request: Request): Promise<UpdateRequest | Response> {
  const contentType = request.headers.get("content-type")?.split(";")[0].trim();
  if (contentType !== "application/json") {
    return error(415, "unsupported_media_type");
  }
  const declaredLength = Number(request.headers.get("content-length") ?? 0);
  if (declaredLength > MAX_BYTES) return error(413, "payload_too_large");
  const bytes = new Uint8Array(await request.arrayBuffer());
  if (bytes.byteLength > MAX_BYTES) return error(413, "payload_too_large");
  let raw: unknown;
  try {
    raw = JSON.parse(new TextDecoder().decode(bytes));
  } catch {
    return error(400, "invalid_request");
  }
  return parseUpdate(raw) ?? error(400, "invalid_request");
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (
      typeof env?.SYNC_TOKEN !== "string" ||
      !env.SYNC_TOKEN ||
      !isCoordinator(env.STATUS_COORDINATOR)
    ) {
      return error(503, "sync_unavailable");
    }
    if (!authorized(request, env.SYNC_TOKEN)) {
      return error(401, "unauthorized");
    }
    const url = new URL(request.url);
    if (url.pathname !== API_PATH) return error(404, "not_found");
    try {
      const coordinator = env.STATUS_COORDINATOR.getByName(OWNER_NAME);
      if (request.method === "GET") {
        return response(200, await coordinator.getDocument());
      }
      if (request.method === "POST") {
        const parsed = await parseRequest(request);
        if (parsed instanceof Response) return parsed;
        const result = await coordinator.merge(parsed);
        if (!result.ok) return error(409, result.error);
        return response(200, result.document);
      }
      if (request.method === "DELETE") {
        await coordinator.clear();
        return response(204);
      }
      return error(405, "method_not_allowed");
    } catch {
      return error(500, "sync_failed");
    }
  },
} satisfies ExportedHandler<Env>;
