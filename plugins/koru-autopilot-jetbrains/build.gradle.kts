plugins {
    kotlin("jvm") version "2.1.20"
    id("org.jetbrains.intellij.platform") version "2.7.2"
}

group = "com.semcod.koru"
version = providers.gradleProperty("pluginVersion").get()

kotlin {
    jvmToolchain(17)
}

repositories {
    mavenCentral()
    intellijPlatform {
        defaultRepositories()
    }
}

dependencies {
    intellijPlatform {
        intellijIdeaCommunity(providers.gradleProperty("platformVersion").get())
        bundledPlugin("com.intellij.java")
    }
}

intellijPlatform {
    pluginConfiguration {
        id = "com.semcod.koru.autopilot"
        name = "koru Autopilot"
        version = project.version.toString()

        ideaVersion {
            sinceBuild = providers.gradleProperty("pluginSinceBuild").get()
            untilBuild = providers.gradleProperty("pluginUntilBuild").orNull
        }

        vendor {
            name = "Semcod"
            email = "tom@sapletta.com"
            url = "https://github.com/semcod/koru"
        }

        description = """
            Terminal-to-IDE bridge for koru autopilot. Connects JetBrains IDEs
            to the local koru autopilot daemon over a same-user unix socket.
        """.trimIndent()
    }
}
