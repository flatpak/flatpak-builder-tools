# Flatpak Maven Generator

Tool to automatically generate `flatpak-builder` manifest json from maven artifact names.

## Usage

`flatpak-maven-generator.py groupId:artifactId:version` which generates `maven-sources.json` and can be included in a manifest like:

```json
"sources": [
  "maven-sources.json"
]
```

You can also list multiple space separated artifacts in single command, for example:
```
flatpak-maven-generator.py org.foo.bar:artifact1:1.0.0 org.foo.baz:artifact2:1.5.21
```

By default, artifacts are looked up on [Maven Central](https://search.maven.org/), but different or additional repositories can be specified with the `-r`/`--repo` flag. For example:
```
flatpak-maven-generator.py --repo https://plugins.gradle.org/m2/ --repo https://repo.maven.apache.org/maven2/ org.foo.bar:artifact1:1.0.0
```

Repositories will be searched in the order they are specified on the command line.

When included in a manifest, the JSON file will instruct `flatpak-builder` to download the necessary files to mirror the requested artifacts (and their recursive dependencies) into a local maven repository. This is created in a folder called `maven-local`, so the build configuration of the software being built will have to be modified to search for its dependencies there. For example, in a `build.gradle.kts` file, you would add the following:
```
allprojects {
	repositories {
		maven(url = "./maven-local")
	}
}
```

If you are intending to mirror Gradle plugins inside your Flatpak build sandbox, you may additionally have to specify the following in `settings.gradle.kts` (or equivalent):
```
pluginManagement {
    repositories {
        maven(url = "./maven-local")
    }
}
```

If you are building multiple modules that all depend on the local maven mirror, you may wish to move the mirrored `maven-local` folder to `$FLATPAK_DEST`, where it can be shared between modules and then cleaned up afterwards.
