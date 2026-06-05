use anyhow::{Context, Result};
use std::env;
use std::fs;
use std::path::Path;
use std::path::PathBuf;
use wit_component::WitPrinter;
use wit_parser::Resolve;

fn main() -> Result<()> {
    println!("cargo:rerun-if-changed=../../wit");
    println!("cargo:rerun-if-changed=../../crates/wasiless");
    println!("cargo:rerun-if-changed=../../wrap_app_in_wasiless.wac");
    println!("cargo:rerun-if-changed=../../Cargo.lock");

    let manifest_dir = env::var("CARGO_MANIFEST_DIR").expect("Failed to get CARGO_MANIFEST_DIR");
    let root_dir: PathBuf = [&manifest_dir, "..", ".."].iter().collect();
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
    let mut resolve = Resolve {
        all_features: true,
        ..Default::default()
    };
    let (main_pkg, _) = resolve.push_path(source_wit_dir).with_context(|| {
        format!(
            "failed to parse WIT directory: {}",
            source_wit_dir.display()
        )
    })?;

    // Collect all package IDs and remove the main pkg
    let nested_pkgs: Vec<_> = resolve
        .packages
        .iter()
        .map(|(id, _)| id)
        .filter(|&id| id != main_pkg)
        .collect();

    let merged = WitPrinter::default()
        .print(&resolve, main_pkg, &nested_pkgs)
        .context("failed to print merged WIT")?;

    let merged_wit_path = out_dir.as_ref().join("merged.wit");
    fs::write(&merged_wit_path, merged)?;

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

    // Wrap the core wasm module into a wasm component using wit-component's
    // ComponentEncoder, replacing the previous `wasm-tools component new` call.
    let input_wasm = target_dir.join("wasm32-unknown-unknown/release/wasiless.wasm");
    let output_wasm = out_dir.as_ref().join("wasiless.wasm");

    let module_bytes = fs::read(&input_wasm)
        .with_context(|| format!("failed to read {}", input_wasm.display()))?;

    let component_bytes = wit_component::ComponentEncoder::default()
        .module(&module_bytes)
        .context("failed to set module on ComponentEncoder")?
        .encode()
        .context("failed to encode wasm component")?;

    fs::write(&output_wasm, component_bytes)
        .with_context(|| format!("failed to write {}", output_wasm.display()))?;

    Ok(())
}
