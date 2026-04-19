#!/usr/bin/env node

import { Ed25519Keypair } from "@mysten/sui/keypairs/ed25519";

const encoder = new TextEncoder();

const MINT_DOMAIN = encoder.encode("sui-human:claim-mint:v1");
const RENEW_DOMAIN = encoder.encode("sui-human:claim-renew:v1");

function readStdin() {
  return new Promise((resolve, reject) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => {
      data += chunk;
    });
    process.stdin.on("end", () => resolve(data));
    process.stdin.on("error", reject);
  });
}

function encodeU16(value) {
  const bytes = new Uint8Array(2);
  new DataView(bytes.buffer).setUint16(0, Number(value), true);
  return bytes;
}

function encodeU64(value) {
  const bytes = new Uint8Array(8);
  new DataView(bytes.buffer).setBigUint64(0, BigInt(value), true);
  return bytes;
}

function encodeUleb128(value) {
  let remaining = Number(value);
  const out = [];
  do {
    let byte = remaining & 0x7f;
    remaining >>>= 7;
    if (remaining > 0) {
      byte |= 0x80;
    }
    out.push(byte);
  } while (remaining > 0);
  return Uint8Array.from(out);
}

function encodeVector(bytes) {
  const data = bytes instanceof Uint8Array ? bytes : Uint8Array.from(bytes);
  const prefix = encodeUleb128(data.length);
  const out = new Uint8Array(prefix.length + data.length);
  out.set(prefix, 0);
  out.set(data, prefix.length);
  return out;
}

function normalizeHex(value) {
  const stripped = String(value ?? "").trim().replace(/^0x/i, "");
  if (!stripped) {
    throw new Error("Expected a hex value");
  }
  return stripped.length % 2 === 0 ? stripped : `0${stripped}`;
}

function hexToBytes(value) {
  const normalized = normalizeHex(value);
  const out = new Uint8Array(normalized.length / 2);
  for (let i = 0; i < normalized.length; i += 2) {
    out[i / 2] = Number.parseInt(normalized.slice(i, i + 2), 16);
  }
  return out;
}

function addressToBytes(value) {
  const raw = hexToBytes(value);
  if (raw.length > 32) {
    throw new Error(`Address too long: ${value}`);
  }
  const out = new Uint8Array(32);
  out.set(raw, 32 - raw.length);
  return out;
}

function appendParts(parts) {
  const total = parts.reduce((sum, part) => sum + part.length, 0);
  const out = new Uint8Array(total);
  let offset = 0;
  for (const part of parts) {
    out.set(part, offset);
    offset += part.length;
  }
  return out;
}

function buildClaimMessage(payload) {
  const domain = payload.operation === "renew" ? RENEW_DOMAIN : MINT_DOMAIN;
  const parts = [
    domain,
    encodeVector(encoder.encode(payload.claim_id)),
    encodeU64(payload.claim_expires_at_ms),
    addressToBytes(payload.wallet_address),
  ];

  if (payload.operation === "renew") {
    parts.push(addressToBytes(payload.proof_object_id));
  }

  parts.push(
    encodeVector(encoder.encode(payload.walrus_blob_id)),
    addressToBytes(payload.walrus_blob_object_id),
    encodeVector(encoder.encode(payload.seal_identity)),
    encodeU16(payload.evidence_schema_version),
    encodeVector(encoder.encode(payload.model_hash ?? "")),
    encodeU64(payload.confidence_bps),
    encodeU64(payload.issued_at_ms),
    encodeU64(payload.expires_at_ms),
    encodeVector(encoder.encode(payload.challenge_type)),
  );

  return appendParts(parts);
}

async function main() {
  const input = await readStdin();
  const payload = JSON.parse(input || "{}");

  if (!payload.private_key) {
    throw new Error("Missing private_key");
  }

  if (payload.operation !== "mint" && payload.operation !== "renew") {
    throw new Error(`Unsupported operation: ${payload.operation}`);
  }

  if (payload.operation === "renew" && !payload.proof_object_id) {
    throw new Error("Missing proof_object_id for renew claim");
  }

  const keypair = Ed25519Keypair.fromSecretKey(payload.private_key);
  const message = buildClaimMessage(payload);
  const signature = await keypair.sign(message);

  process.stdout.write(
    JSON.stringify({
      signature_b64: Buffer.from(signature).toString("base64"),
      public_key_hex: Buffer.from(keypair.getPublicKey().toRawBytes()).toString("hex"),
      message_b64: Buffer.from(message).toString("base64"),
    }),
  );
}

main().catch((error) => {
  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
  process.exitCode = 1;
});
