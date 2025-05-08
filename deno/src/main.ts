import {
  base64ToHex,
  sha256,
  shortHash,
  shouldHash,
  splitOnce,
  urlSegments,
} from "./utils.ts";

interface Pkg {
  module: string;
  version: string;
  name: string;
  cpu?: "x86_64" | "aarch64";
}

async function jsrPkgToFlatpakData(pkg: Pkg) {
  const flatpkData = [];
  const metaUrl = `https://jsr.io/${pkg.module}/meta.json`;
  const metaText = await fetch(
    metaUrl,
  ).then((r) => r.text());

  flatpkData.push({
    type: "file",
    url: metaUrl,
    sha256: await sha256(metaText),
    dest: `vendor/jsr.io/${pkg.module}`,
    "dest-filename": "meta.json",
  });

  const metaVerUrl = `https://jsr.io/${pkg.module}/${pkg.version}_meta.json`;
  const metaVerText = await fetch(
    metaVerUrl,
  ).then((r) => r.text());

  flatpkData.push({
    type: "file",
    url: metaVerUrl,
    sha256: await sha256(metaVerText),
    dest: `vendor/jsr.io/${pkg.module}`,
    "dest-filename": `${pkg.version}_meta.json`,
  });

  const metaVer = JSON.parse(metaVerText);

  for (
    const fileUrl of Object.keys(metaVer.moduleGraph2 || metaVer.moduleGraph1)
  ) {
    const fileMeta = metaVer.manifest[fileUrl];
    // this mean the url exists in the module graph but not in the manifest -> this url is not needed
    if (!fileMeta) continue;
    const [checksumType, checksumValue] = splitOnce(fileMeta.checksum, "-");

    const url = `https://jsr.io/${pkg.module}/${pkg.version}${fileUrl}`;
    let [fileDir, fileName] = splitOnce(fileUrl, "/", "right");
    const dest = `vendor/jsr.io/${pkg.module}/${pkg.version}${fileDir}`;

    if (shouldHash(fileName)) {
      fileName = await shortHash(fileName);
    }

    flatpkData.push({
      type: "file",
      url,
      [checksumType]: checksumValue,
      dest,
      "dest-filename": fileName,
    });
  }

  // If a moule imports deno.json (import ... from "deno.json" with {type:"json"}), it won't appear in the module graph
  // Worarkound: if there is a deno.json file in the manifest just add it
  // Note this can be made better, by looking in the moduleGraph if deno.json is specified in the dependencies
  for (const [fileUrl, fileMeta] of Object.entries(metaVer.manifest)) {
    if (fileUrl.includes("deno.json")) {
      const [checksumType, checksumValue] = splitOnce(
        // deno-lint-ignore no-explicit-any
        (fileMeta as any).checksum,
        "-",
      );
      const url = `https://jsr.io/${pkg.module}/${pkg.version}${fileUrl}`;
      const [fileDir, fileName] = splitOnce(fileUrl, "/", "right");
      const dest = `vendor/jsr.io/${pkg.module}/${pkg.version}${fileDir}`;
      flatpkData.push({
        type: "file",
        url,
        [checksumType]: checksumValue,
        dest,
        "dest-filename": fileName,
      });
    }
  }

  return flatpkData;
}

async function npmPkgToFlatpakData(pkg: Pkg) {
  //url: https://registry.npmjs.org/@napi-rs/cli/-/cli-2.18.4.tgz
  //npmPkgs;
  const metaUrl = `https://registry.npmjs.org/${pkg.module}`;
  const metaText = await fetch(metaUrl).then(
    (r) => r.text(),
  );
  const meta = JSON.parse(metaText);

  const metaData = {
    type: "file",
    url: metaUrl,
    sha256: await sha256(metaText),
    dest: `deno_dir/npm/registry.npmjs.org/${pkg.module}`,
    "dest-filename": "registry.json",
  };

  const [checksumType, checksumValue] = splitOnce(
    meta.versions[pkg.version].dist.integrity,
    "-",
  );
  const pkgData: Record<string, unknown> = {
    type: "archive",
    "archive-type": "tar-gzip",
    url:
      `https://registry.npmjs.org/${pkg.module}/-/${pkg.name}-${pkg.version}.tgz`,
    [checksumType]: base64ToHex(checksumValue),
    dest: `deno_dir/npm/registry.npmjs.org/${pkg.module}/${pkg.version}`,
  };

  if (pkg.cpu) {
    pkgData["only-arches"] = [pkg.cpu];
  }

  return [metaData, pkgData];
}

if (import.meta.main) {
  const arg = Deno.args[0];
  if (!arg) {
    console.error("No argument provided");
    Deno.exit(1);
  }

  const lock = JSON.parse(Deno.readTextFileSync(arg));
  if (lock.version !== "5") {
    throw new Error(`Unsupported deno lock version: ${lock.version}`);
  }

  const jsrPkgs: Pkg[] = !lock.jsr ? [] : Object.keys(lock.jsr).map((pkg) => {
    const r = splitOnce(pkg, "@", "right");
    const name = r[0].split("/")[1];
    return { module: r[0], version: r[1], name };
  });
  jsrPkgs;
  const npmPkgs: Pkg[] = !lock.npm ? [] : Object.entries(lock.npm)
    .filter((
      // deno-lint-ignore no-explicit-any
      [_key, val]: any,
    ) => (val.os === undefined || val.os?.at(0) === "linux"))
    // deno-lint-ignore no-explicit-any
    .map(([key, val]: any) => {
      const r = splitOnce(key, "@", "right");
      const name = r[0].includes("/") ? r[0].split("/")[1] : r[0];
      const cpu = val.cpu?.at(0);
      return {
        module: r[0],
        version: r[1],
        name,
        cpu: cpu === "x64" ? "x86_64" : cpu === "arm64" ? "aarch64" : cpu,
      };
    });
  //url: https://registry.npmjs.org/@napi-rs/cli/-/cli-2.18.4.tgz
  npmPkgs;
  const httpPkgsData = !lock.remote
    ? []
    : Object.entries(lock.remote).map(async ([urlStr, checksum]) => {
      const url = new URL(urlStr);
      const segments = await Promise.all(
        urlSegments(url)
          .map(async (part) => shouldHash(part) ? await shortHash(part) : part),
      );
      const filename = segments.pop();
      return {
        type: "file",
        url: urlStr,
        sha256: checksum,
        dest: `vendor/${url.hostname}/${segments.join("/")}`,
        "dest-filename": filename,
      };
    });

  const flatpakData = [
    await Promise.all(
      jsrPkgs.map((pkg) => jsrPkgToFlatpakData(pkg)),
    ).then((r) => r.flat()),
    await Promise.all(npmPkgs.map((pkg) => npmPkgToFlatpakData(pkg))).then(
      (r) => r.flat(),
    ),
    await Promise.all(httpPkgsData),
  ].flat();
  // console.log(flatpakData);
  Deno.writeTextFileSync(
    "deno-sources.json",
    JSON.stringify(flatpakData, null, 2),
  );
}
