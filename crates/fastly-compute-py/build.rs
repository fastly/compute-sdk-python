use anyhow::{Context, Result};
use std::env;
use std::fs;
use std::path::Path;
use std::path::PathBuf;

fn main() -> Result<()> {
    println!("cargo:rerun-if-changed=../../wit");
    println!("cargo:rerun-if-changed=../../crates/wasiless");
    println!("cargo:rerun-if-changed=../../wrap_app_in_wasiless.wac");
    println!("cargo:rerun-if-changed=../../Cargo.lock");

    let root_dir = PathBuf::from("../../");
    let wit_dir = root_dir.join("wit");
    let out_dir = PathBuf::from(env::var("OUT_DIR")?);

    // Generate merged WIT file from WIT directory
    generate_merged_wit(&wit_dir, &out_dir)?;

    // Build and embed wasiless.wasm
    build_wasiless_wasm(&root_dir, &out_dir)?;

    // Prepare WAC file for embedding
    fs::copy(
        root_dir.join("wrap_app_in_wasiless.wac"),
        out_dir.join("wrap_app_in_wasiless.wac"),
    )?;

    // Expose the componentize-py version for embedding in Wasm producers metadata.
    let metadata = cargo_metadata::MetadataCommand::new()
        .manifest_path(root_dir.join("Cargo.toml"))
        .exec()
        .context("Failed to run `cargo metadata`")?;
    let componentize_py_version = metadata
        .packages
        .iter()
        .find(|p| p.name == "componentize-py")
        .with_context(|| "componentize-py not found in cargo metadata")?
        .version
        .to_string();
    println!("cargo:rustc-env=COMPONENTIZE_PY_VERSION={componentize_py_version}");

    Ok(())
}

fn generate_merged_wit(source_wit_dir: &PathBuf, out_dir: impl AsRef<Path>) -> Result<()> {
    // Generate merged WIT file using wasm-tools
    let merged_wit_path = out_dir.as_ref().join("merged.wit");
    let output = std::process::Command::new("wasm-tools")
        .arg("component")
        .arg("wit")
        .arg(source_wit_dir)
        .output()
        .context("Failed to run wasm-tools")?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        anyhow::bail!("wasm-tools component wit failed: {}", stderr);
    }

    fs::write(&merged_wit_path, &output.stdout)?;

    Ok(())
}

fn build_wasiless_wasm(root_dir: impl AsRef<Path>, out_dir: impl AsRef<Path>) -> Result<()> {
    let wasiless_dir = root_dir.as_ref().join("crates/wasiless");
    let manifest_path = wasiless_dir.join("Cargo.toml");
    let target_dir = out_dir.as_ref().join("wasiless-target");

    // Build wasiless.wasm using cargo; a separate target directory to avoid
    // locking issues with the main build.
    let cargo = env::var("CARGO").unwrap_or_else(|_| "cargo".to_string());
    let status = std::process::Command::new(cargo)
        .arg("build")
        .arg("--target")
        .arg("wasm32-unknown-unknown")
        .arg("--release")
        .arg("--manifest-path")
        .arg(&manifest_path)
        .env("CARGO_TARGET_DIR", &target_dir)
        // Clear host-specific rustflags injected by maturin or other build
        // wrappers (e.g. -Csplit-debuginfo=packed).  These are valid for the
        // host target but are not supported by wasm32-unknown-unknown and
        // will cause the cross-compilation to fail.
        .env_remove("CARGO_ENCODED_RUSTFLAGS")
        .env_remove("RUSTFLAGS")
        .status()
        .context("Failed to run cargo build for wasiless")?;

    if !status.success() {
        anyhow::bail!("Failed to build wasiless");
    }

    // Transform wasiless into a component using wasm-tools component new
    let input_wasm = target_dir.join("wasm32-unknown-unknown/release/wasiless.wasm");
    let output_wasm = out_dir.as_ref().join("wasiless.wasm");

    let status = std::process::Command::new("wasm-tools")
        .arg("component")
        .arg("new")
        .arg(&input_wasm)
        .arg("-o")
        .arg(&output_wasm)
        .status()
        .context("Failed to run wasm-tools component new")?;

    if !status.success() {
        anyhow::bail!("Failed to componentize wasiless");
    }

    Ok(())
}
