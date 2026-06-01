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
/// Errors are bubbled up when UV is known to be available (i.e. the `UV`
/// environment variable is set, which `uv run` always provides).  If UV is
/// not discoverable at all we warn and return an empty list, since the project
/// may not be using UV as its package manager.
pub fn get_dependencies(_virtualenv: &Option<PathBuf>) -> Result<Vec<Dependency>> {
    log::info!("Collecting dependencies from project environment...");

    let uv_bin = std::env::var("UV").unwrap_or_else(|_| "uv".to_string());
    let uv_from_env = std::env::var("UV").is_ok();

    match get_dependencies_from_uv(&uv_bin) {
        Ok(deps) => {
            log::info!("Found {} dependencies via UV", deps.len());
            Ok(deps)
        }
        Err(e) if !uv_from_env && is_not_found(&e) => {
            // UV not on PATH and not provided by the environment — not a UV project.
            log::warn!("UV not found, skipping dependency collection: {}", e);
            Ok(Vec::new())
        }
        Err(e) => Err(e),
    }
}

/// Returns true if the error chain contains an OS "not found" error.
fn is_not_found(e: &anyhow::Error) -> bool {
    e.chain().any(|cause| {
        cause
            .downcast_ref::<std::io::Error>()
            .map(|io| io.kind() == std::io::ErrorKind::NotFound)
            .unwrap_or(false)
    })
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
