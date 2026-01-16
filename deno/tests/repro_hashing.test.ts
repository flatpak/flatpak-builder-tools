import { jsrPkgToFlatpakData } from "../src/main.ts";
import { assert } from "jsr:@std/assert@0.221.0";

Deno.test("jsrPkgToFlatpakData hashes all segments", async () => {
  const pkg = { module: "@sigmasd/gtk", version: "0.13.1", name: "gtk" };
  const data = await jsrPkgToFlatpakData(pkg);

  const modFile = data.find((d) =>
    d.url === "https://jsr.io/@sigmasd/gtk/0.13.1/src/libPaths/mod.ts"
  );
  assert(modFile, "Should find mod.ts");

  // Current code probably produces: vendor/jsr.io/@sigmasd/gtk/0.13.1/src/libPaths
  // But it should be: vendor/jsr.io/@sigmasd/gtk/0.13.1/src/#libpaths_8b87f

  console.log("Dest for mod.ts:", modFile.dest);
  assert(
    modFile.dest.includes("#libpaths_8b87f"),
    `Path should be hashed, got: ${modFile.dest}`,
  );
});
