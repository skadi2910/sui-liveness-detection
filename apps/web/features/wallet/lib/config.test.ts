import { describe, expect, it } from "vitest";
import {
  formatSuiNetworkLabel,
  hasConnectedWallet,
  resolveSuiNetwork,
  resolveSuiRpcUrl,
  shortenWalletAddress,
} from "./config";

describe("resolveSuiNetwork", () => {
  it("keeps supported network values", () => {
    expect(resolveSuiNetwork("mainnet")).toBe("mainnet");
    expect(resolveSuiNetwork("localnet")).toBe("localnet");
  });

  it("falls back to testnet for missing or unsupported values", () => {
    expect(resolveSuiNetwork(undefined)).toBe("testnet");
    expect(resolveSuiNetwork("previewnet")).toBe("testnet");
  });
});

describe("resolveSuiRpcUrl", () => {
  it("prefers explicit env values", () => {
    expect(
      resolveSuiRpcUrl({
        envValue: "https://rpc.example.com",
        network: "testnet",
      }),
    ).toBe("https://rpc.example.com");
  });

  it("falls back to the known network url", () => {
    expect(resolveSuiRpcUrl({ network: "localnet" })).toBe("http://127.0.0.1:9000");
  });
});

describe("wallet display helpers", () => {
  it("shortens long addresses for compact UI", () => {
    expect(shortenWalletAddress("0x1234567890abcdef1234567890abcdef")).toBe("0x1234...cdef");
  });

  it("formats network labels for display", () => {
    expect(formatSuiNetworkLabel("testnet")).toBe("Testnet");
  });

  it("detects whether a wallet is connected", () => {
    expect(hasConnectedWallet("0xabc")).toBe(true);
    expect(hasConnectedWallet("")).toBe(false);
  });
});
