# Flatpak Maven (Java) Generator

Generate a Flatpak manifest and other required files from a Maven POM to create a distributable application. For the most part, the plugin follows Mavens "Convention Over Configuration" approach, meaning you can go from source to a distributable application with the minimum amount of effort. However it is also highly configurable, allowing any generated meta-data or resources to be overridden.

The plugin will generate a manfest with all required dependencies for the simple build system, AppStream metadata, desktop entries and a launcher script using as much information as it can derive from your POM. The more complete your POM, the less additional information you may need to add to meet Flatpaks requirements.

See [flatpak-maven-plugin](https://github.com/bithatch/maven-flatpak-plugin) for more information.

## Requirements

 * Apache Maven (recommended 3.9+).
 * Java 8 or above.
 * A Java Maven project with a `pom.xml`.
 * `flatpak-builder` is optional for `build` goal.

That's it. The plugin is available on Maven Central and will be automatically downloaded when included in your POM. 

*The directory containing this README.md isn't required in your project like it might be with our languages and build systems.*

## Usage

Add the plugin to your POM. It is recommended you [check Maven Central](https://central.sonatype.com/artifact/uk.co.bithatch/flatpak-maven-plugin) for the latest version number.

```xml
<plugin>
	<groupId>uk.co.bithatch</groupId>
	<artifactId>flatpak-maven-plugin</artifactId>
	<version>0.0.4</version>
	<configuration>
		<mainClass>com.acme.Abc</mainClass>
	</configuration>
</plugin>
```

Then run ...

```
mvn clean package uk.co.bithatch:maven-flatpak-plugin:generate
```

This will by default generate the Flatpak manifest and others in `target/app`. So from here you can build the package.

```
cd target/app
flatpak-builder build-dir com.acme.Abc.yml
```

And then test and run.

```
flatpak-builder --user --install --force-clean build-dir com.acme.Abc.yml
flatpak run com.acme.Abc
```

See plugin [project page](https://github.com/bithatch/maven-flatpak-plugin) for more complete examples.
