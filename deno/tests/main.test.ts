// LICENSE = MIT
// deno-lint-ignore-file require-await
import { assert, assertEquals, assertMatch } from "jsr:@std/assert@0.221.0";
import { jsrPkgToFlatpakData, npmPkgToFlatpakData } from "../src/main.ts";

Deno.test("jsrPkgToFlatpakData returns correct flatpak data", async () => {
  // Mock fetch for meta.json and versioned meta
  const metaJson = JSON.stringify({
    dummy: true,
  });
  const metaVerJson = JSON.stringify({
    moduleGraph2: {
      "/mod.ts": {},
      "/deno.json": {},
    },
    moduleGraph1: {},
    manifest: {
      "/mod.ts": {
        checksum: "sha256-abcdef1234567890",
      },
      "/deno.json": {
        checksum: "sha256-ffeeddccbbaa9988",
      },
    },
  });

  let fetchCallCount = 0;
  const origFetch = globalThis.fetch;
  Object.defineProperty(globalThis, "fetch", {
    configurable: true,
    writable: true,
    value: async (input: URL | RequestInfo, _init?: RequestInit) => {
      const url = typeof input === "string"
        ? input
        : input instanceof URL
        ? input.toString()
        : (input as Request).url;
      fetchCallCount++;
      if (url.endsWith("_meta.json")) {
        return {
          text: async () => metaVerJson,
        } as Response;
      }
      if (url.endsWith("meta.json")) {
        return {
          text: async () => metaJson,
        } as Response;
      }
      throw new Error("Unexpected fetch url: " + url);
    },
  });

  const pkg = {
    module: "@std/encoding",
    version: "1.0.10",
    name: "encoding",
  };

  const data = await jsrPkgToFlatpakData(pkg);
  // Restore fetch after test
  Object.defineProperty(globalThis, "fetch", {
    configurable: true,
    writable: true,
    value: origFetch,
  });

  // Should have meta.json, versioned meta, /mod.ts, deno.json, and duplicate deno.json
  assertEquals(data.length, 5);

  // meta.json
  assertEquals(data[0].url, "https://jsr.io/@std/encoding/meta.json");
  assertEquals(data[0]["dest-filename"], "meta.json");
  assertEquals(data[1].url, "https://jsr.io/@std/encoding/1.0.10_meta.json");
  assertEquals(data[1]["dest-filename"], "1.0.10_meta.json");

  // /mod.ts
  assertEquals(data[2].url, "https://jsr.io/@std/encoding/1.0.10/mod.ts");
  assertEquals(data[2].sha256, "abcdef1234567890");
  // Accept either "mod.ts" or a hashed filename
  assertMatch(
    data[2]["dest-filename"] as string,
    /^mod\.ts$|^#mod_[a-f0-9]{5}\.ts$/,
  );

  // /deno.json
  assertEquals(data[3].url, "https://jsr.io/@std/encoding/1.0.10/deno.json");
  assertEquals(data[3].sha256, "ffeeddccbbaa9988");
  assertEquals(data[3]["dest-filename"], "deno.json");
});

Deno.test("npmPkgToFlatpakData returns correct flatpak data", async () => {
  // Mock fetch for npm meta
  const metaJson = {
    versions: {
      "2.18.4": {
        dist: {
          // "abcdefg" in base64 is "YWJjZGVmZw=="
          integrity: "sha512-YWJjZGVmZw==",
        },
      },
    },
  };

  const origFetch = globalThis.fetch;
  Object.defineProperty(globalThis, "fetch", {
    configurable: true,
    writable: true,
    value: async (input: URL | RequestInfo, _init?: RequestInit) => {
      const url = typeof input === "string"
        ? input
        : input instanceof URL
        ? input.toString()
        : (input as Request).url;
      if (url === "https://registry.npmjs.org/@napi-rs/cli") {
        return {
          json: async () => metaJson,
        } as Response;
      }
      throw new Error("Unexpected fetch url: " + url);
    },
  });

  const pkg = {
    module: "@napi-rs/cli",
    version: "2.18.4",
    name: "cli",
    cpu: "x86_64" as const,
  };

  const data = await npmPkgToFlatpakData(pkg);
  // Restore fetch after test
  Object.defineProperty(globalThis, "fetch", {
    configurable: true,
    writable: true,
    value: origFetch,
  });

  // Should have registry.json and archive
  assertEquals(data.length, 2);

  // registry.json
  const registryContents = data.at(0)?.contents;
  assert(registryContents !== undefined);
  assert("2.18.4" in JSON.parse(registryContents).versions);
  assertEquals(data[0]["dest-filename"], "registry.json");

  // archive
  assertEquals(
    data[1].url,
    "https://registry.npmjs.org/@napi-rs/cli/-/cli-2.18.4.tgz",
  );
  assertEquals(
    data[1]["archive-type"],
    "tar-gzip",
  );
  assertEquals(
    data[1].dest,
    "deno_dir/npm/registry.npmjs.org/@napi-rs/cli/2.18.4",
  );
  assertEquals(
    (data[1]["only-arches"] as string[])[0],
    "x86_64",
  );
  // sha512 should be present and hex
  assertMatch(
    String(data[1].sha512),
    /^[a-f0-9]+$/,
  );
});
