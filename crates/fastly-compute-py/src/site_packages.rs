use anyhow::Result;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

/// Build a python_path list suitable for componentize-py.
/// This includes the current directory and all site-packages paths.
pub fn build_python_path() -> Result<Vec<String>> {
    let cwd = env::current_dir()?;
    log::debug!("Current directory: {}", cwd.display());

    let mut python_path = vec![cwd.to_string_lossy().to_string()];

    if let Some(site_packages) = find_site_packages()? {
        log::debug!(
            "Adding site-packages to python_path: {}",
            site_packages.display()
        );
        python_path.push(site_packages.to_string_lossy().to_string());

        // Add paths from .pth files (editable installs)
        let pth_paths = scan_pth_files(&site_packages)?;
        if !pth_paths.is_empty() {
            log::debug!("Found {} paths from .pth files", pth_paths.len());
            for pth_path in &pth_paths {
                log::debug!("  - {}", pth_path);
            }
        } else {
            log::debug!("No .pth files found in site-packages");
        }
        python_path.extend(pth_paths);
    } else {
        log::debug!("No site-packages found, using only current directory");
    }

    log::debug!("Final python_path has {} entries", python_path.len());
    Ok(python_path)
}

/// Find the site-packages directory within a virtualenv.
pub fn find_site_packages() -> Result<Option<PathBuf>> {
    let venv_path = find_venv()?;

    if let Some(venv) = venv_path {
        log::debug!("Found virtualenv: {}", venv.display());
        let lib_dir = venv.join("lib");
        if lib_dir.exists() {
            log::debug!("Scanning lib directory for site-packages...");
            let result = find_dir("site-packages", &lib_dir, 3)?;
            if let Some(ref sp) = result {
                log::debug!("✓ Located site-packages: {}", sp.display());
            } else {
                log::debug!("⚠ site-packages not found in virtualenv");
            }
            return Ok(result);
        } else {
            log::debug!(
                "⚠ lib directory does not exist in virtualenv: {}",
                lib_dir.display()
            );
        }
    } else {
        log::debug!("No virtualenv detected");
    }

    Ok(None)
}

/// Find the virtualenv path from environment or local .venv.
fn find_venv() -> Result<Option<PathBuf>> {
    if let Ok(venv) = env::var("VIRTUAL_ENV") {
        log::debug!("Detected VIRTUAL_ENV environment variable: {}", venv);
        return Ok(Some(PathBuf::from(venv)));
    }

    let local_venv = env::current_dir()?.join(".venv");
    if local_venv.exists() {
        log::debug!("Detected local .venv directory: {}", local_venv.display());
        return Ok(Some(local_venv));
    }

    log::debug!("No virtualenv detected (no VIRTUAL_ENV var or .venv directory)");
    Ok(None)
}

/// Recursively find a directory with the given name, up to max_depth levels deep.
fn find_dir(name: &str, path: &Path, max_depth: usize) -> Result<Option<PathBuf>> {
    log::trace!(
        "find_dir: searching for '{}' in {} (depth={})",
        name,
        path.display(),
        max_depth
    );

    if !path.is_dir() {
        return Ok(None);
    }

    // Check if current directory matches (before checking depth)
    if path.file_name().and_then(|n| n.to_str()) == Some(name) {
        log::trace!("find_dir: found match at {}", path.display());
        return Ok(Some(path.canonicalize()?));
    }

    // Only recurse if we have depth remaining
    if max_depth == 0 {
        return Ok(None);
    }

    // Search subdirectories
    fs::read_dir(path)?
        .flatten()
        .map(|entry| entry.path())
        .filter(|p| p.is_dir())
        .find_map(|subdir| find_dir(name, &subdir, max_depth - 1).transpose())
        .transpose()
}

/// Scan .pth files in site-packages to find additional paths (editable installs).
/// Returns a list of valid paths found in .pth files.
fn scan_pth_files(site_packages: &Path) -> Result<Vec<String>> {
    let pth_files: Vec<PathBuf> = fs::read_dir(site_packages)?
        .flatten()
        .map(|entry| entry.path())
        .filter(|path| path.extension().is_some_and(|ext| ext == "pth"))
        .collect();

    if pth_files.is_empty() {
        log::debug!("No .pth files found in site-packages");
        return Ok(Vec::new());
    }

    log::debug!(
        "Scanning {} .pth file(s) for editable installs",
        pth_files.len()
    );

    let mut resolved_pth_paths = Vec::new();
    for pth_path in pth_files {
        log::debug!("  Reading: {}", pth_path.display());
        if let Ok(pth_file_contents) = fs::read_to_string(&pth_path) {
            let mut found_in_file = 0;
            for line in pth_file_contents.lines() {
                let line = line.trim();
                if !line.is_empty() && !line.starts_with('#') {
                    if let Some(resolved) = resolve_pth_path(line, site_packages) {
                        log::debug!("    → {}", resolved.display());
                        resolved_pth_paths.push(resolved.to_string_lossy().into());
                        found_in_file += 1;
                    } else {
                        log::debug!("    ✗ Path not found: {}", line);
                    }
                }
            }
            if found_in_file == 0 {
                log::debug!("    (no valid paths in this file)");
            }
        }
    }

    Ok(resolved_pth_paths)
}

/// Resolve a path entry from a .pth file to either an absolute path
/// or path relative to site_packages.
///
/// Paths in .pth files that cannot be resolved are ignored.
fn resolve_pth_path(line: &str, site_packages: &Path) -> Option<PathBuf> {
    let pth_path = Path::new(line);

    if pth_path.is_absolute() && pth_path.exists() {
        return Some(pth_path.to_path_buf());
    }

    let relative = site_packages.join(line);
    if relative.exists() {
        return Some(relative);
    }

    None
}
