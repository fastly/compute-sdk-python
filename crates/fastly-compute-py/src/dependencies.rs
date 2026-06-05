use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;
use std::process::Command;

/// A single package dependency with name and version
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Dependency {
    pub name: String,
    pub version: String,
}

/// Fastly CLI DataCollection format for fastly_data metadata.
/// Matches the Go structs in pkg/commands/compute/build.go.
#[derive(Debug, Serialize)]
pub struct FastlyData {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub package_info: Option<PackageInfo>,
}

#[derive(Debug, Serialize)]
pub struct PackageInfo {
    pub packages: HashMap<String, String>,
}

/// PEP 751 pylock.toml format structures
#[derive(Debug, Deserialize)]
struct PylockToml {
    #[serde(rename = "lock-version")]
    _lock_version: String,
    packages: Vec<PylockPackage>,
}

#[derive(Debug, Deserialize)]
struct PylockPackage {
    name: String,
    /// Present for registry/VCS packages; absent for local source trees
    /// (PEP 751: version MUST NOT be included when using a source tree)
    version: Option<String>,
}

/// Get dependencies using UV's PEP 751 export.
///
/// Dependency collection only runs when both conditions are met:
///
/// 1. A `pyproject.toml` exists in the current directory — confirming this is
///    a Python project that could have a lockfile.  Without this, `uv export`
///    would fail with "no pyproject.toml found" (e.g. the Viceroy test
///    framework builds in a temp dir with no project files).
///
/// 2. The `UV` environment variable is set — confirming the tool was invoked
///    via `uv run` or similar.  We don't guess that `uv` should be used just
///    because a `uv` binary happens to be on PATH; the user may be using pip,
///    poetry, or another tool entirely.
///
/// When both conditions are met, errors from `uv export` are bubbled up since
/// something genuinely went wrong in a context where UV is expected to work.
pub fn get_dependencies(_virtualenv: &Option<PathBuf>) -> Result<Vec<Dependency>> {
    if !std::fs::exists("pyproject.toml").unwrap_or_default() {
        log::debug!("No pyproject.toml found, skipping dependency collection");
        return Ok(Vec::new());
    }

    let uv_bin = match std::env::var("UV") {
        Ok(bin) => bin,
        Err(_) => {
            log::debug!("UV env var not set, skipping dependency collection");
            return Ok(Vec::new());
        }
    };

    log::info!("Collecting dependencies from project environment...");

    let deps = get_dependencies_from_uv(&uv_bin)?;
    log::info!("Found {} dependencies via UV", deps.len());
    Ok(deps)
}

/// Serialize dependencies as fastly_data JSON, matching the CLI's DataCollection format.
///
/// The build tool injects this directly so the CLI does not need to know anything
/// about the Python environment to collect package metadata.
pub fn get_fastly_data_json(virtualenv: &Option<PathBuf>) -> Result<String> {
    let deps = get_dependencies(virtualenv)?;

    if deps.is_empty() {
        return Ok(String::new());
    }

    let packages: HashMap<String, String> = deps.into_iter().map(|d| (d.name, d.version)).collect();

    let fastly_data = FastlyData {
        package_info: Some(PackageInfo { packages }),
    };

    serde_json::to_string(&fastly_data).context("Failed to serialize fastly_data to JSON")
}

/// Use UV export to get dependencies in PEP 751 pylock.toml format
fn get_dependencies_from_uv(uv_bin: &str) -> Result<Vec<Dependency>> {
    log::debug!(
        "Attempting to export dependencies using UV binary: {}",
        uv_bin
    );

    let output = Command::new(uv_bin)
        .args([
            "export",
            "--format",
            "pylock.toml",
            "--no-emit-project",
            "--frozen",
            "--no-header",
        ])
        .output()
        .context("Failed to run 'uv export'")?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        anyhow::bail!("uv export failed: {}", stderr);
    }

    let pylock_content =
        String::from_utf8(output.stdout).context("UV output was not valid UTF-8")?;

    parse_pylock_toml(&pylock_content)
}

/// Parse PEP 751 pylock.toml format
fn parse_pylock_toml(content: &str) -> Result<Vec<Dependency>> {
    let pylock: PylockToml =
        toml::from_str(content).context("Failed to parse pylock.toml format")?;

    let dependencies = pylock
        .packages
        .into_iter()
        .map(|pkg| Dependency {
            version: pkg.version.unwrap_or_else(|| "unknown".to_string()),
            name: pkg.name,
        })
        .collect();

    Ok(dependencies)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_versioned_packages() {
        let sample = r#"
lock-version = "1.0"
created-by = "uv"
requires-python = ">=3.12"

[[packages]]
name = "bottle"
version = "0.13.4"

[[packages]]
name = "requests"
version = "2.31.0"
"#;

        let deps = parse_pylock_toml(sample).unwrap();
        assert_eq!(deps.len(), 2);
        assert_eq!(deps[0].name, "bottle");
        assert_eq!(deps[0].version, "0.13.4");
        assert_eq!(deps[1].name, "requests");
        assert_eq!(deps[1].version, "2.31.0");
    }

    #[test]
    fn test_parse_directory_dependency_uses_unknown() {
        // PEP 751: version MUST NOT be included for source trees.
        // We record "unknown" so the dependency is still visible.
        let sample = r#"
lock-version = "1.0"
created-by = "uv"
requires-python = ">=3.12"

[[packages]]
name = "bottle"
version = "0.13.4"

[[packages]]
name = "fastly-compute"
directory = { path = "../../", editable = true }
"#;

        let deps = parse_pylock_toml(sample).unwrap();
        assert_eq!(deps.len(), 2);
        assert_eq!(deps[1].name, "fastly-compute");
        assert_eq!(deps[1].version, "unknown");
    }
}
