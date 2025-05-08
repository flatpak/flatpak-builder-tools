// LICENSE = MIT
// deno-lint-ignore-file no-explicit-any
import { main } from "../src/main.ts";
import { assert } from "jsr:@std/assert@0.221.0";
import { join } from "jsr:@std/path@0.221.0";
import { existsSync } from "jsr:@std/fs@0.221.0";

Deno.test("main function: generates deno-sources.json from lockfile", async () => {
  const tmpDir = "./tests/tmp_main";
  await Deno.mkdir(tmpDir, { recursive: true });
  const lockPath = join(tmpDir, "deno.lock");
  const sourcesPath = join(tmpDir, "deno-sources.json");

  // Lockfile with jsr, npm, and https deps
  await Deno.writeTextFile(
    lockPath,
    JSON.stringify(
      {
        version: "5",
        jsr: {
          "@std/encoding@1.0.10": {
            integrity:
              "8783c6384a2d13abd5e9e87a7ae0520a30e9f56aeeaa3bdf910a3eaaf5c811a1",
          },
        },
        npm: {
          "left-pad@1.3.0": {
            integrity: "sha512-1r9Z1tcHTul3e8DqRLVQjaxAg/P6nxsVXni4eWh05rq6ArlTc95xJMu38xpv8uKXuX4nHCqB6f+GO6zkRgLr1w==",
            engines: { node: ">=0.10.0" }
          }
        },
        remote: {
          "https://deno.land/std@0.203.0/uuid/v1.ts": "b6e2e2c1e2c1e2c1e2c1e2c1e2c1e2c1e2c1e2c1e2c1e2c1e2c1e2c1e2c1e2c1"
        }
      },
      null,
      2,
    ),
  );

  try {
    await main(lockPath, sourcesPath);
    assert(existsSync(sourcesPath), "deno-sources.json should be created");
    const sources = JSON.parse(await Deno.readTextFile(sourcesPath));
    assert(Array.isArray(sources));
    // jsr checks
    assert(sources.some((s: any) => s["dest-filename"] === "meta.json"));
    assert(sources.some((s: any) => s["dest-filename"] === "1.0.10_meta.json"));
    // npm checks
    assert(sources.some((s: any) => s["dest-filename"] === "registry.json"));
    assert(sources.some((s: any) =>
      typeof s.dest === "string" &&
      s.dest.includes("left-pad/1.3.0")
    ));
    // https checks
    assert(sources.some((s: any) =>
      typeof s.url === "string" &&
      s.url.startsWith("https://deno.land/std@0.203.0/uuid/v1.ts")
    ));
  } finally {
    await Deno.remove(tmpDir, { recursive: true });
  }
});
