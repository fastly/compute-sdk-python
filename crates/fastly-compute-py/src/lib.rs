use anyhow::{Context, Result};
use clap::Parser;
use indexmap::IndexMap;
use std::collections::HashMap;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use tempfile::TempDir;
use wac_graph::CompositionGraph;
use wac_graph::EncodeOptions;
use wac_parser::Document;
use wac_types::BorrowedPackageKey;
use wac_types::Package;

pub mod cli;
pub mod config;
pub mod site_packages;

use cli::Cli;
use pyo3::prelude::*;

use crate::config::ConfigBuilder;

const MERGED_WIT: &str = include_str!(concat!(env!("OUT_DIR"), "/merged.wit"));
const WASILESS_WASM: &[u8] = include_bytes!(concat!(env!("OUT_DIR"), "/wasiless.wasm"));
const WRAP_WAC: &str = include_str!(concat!(env!("OUT_DIR"), "/wrap_app_in_wasiless.wac"));

/// Initialize logging with cranelift noise filtered out
fn init_logging(verbose: u8) {
    let rust_log_set = env::var("RUST_LOG").is_ok();

    let log_level = match verbose {
        0 => "info",  // Default to info level
        1 => "info",  // -v: same as default
        2 => "debug", // -vv: debug
        _ => "trace", // -vvv+: trace
    };

    let default_filter = if rust_log_set {
        // If RUST_LOG is set, use it as-is (user wants full control)
        String::new()
    } else {
        // Otherwise, only show fastly_compute_py logs
        format!("fastly_compute_py={}", log_level)
    };

    let mut builder = env_logger::Builder::from_env(
        env_logger::Env::default().default_filter_or(&default_filter),
    );

    // For default verbosity (0), use simple formatting without timestamps/levels
    // For higher verbosity, show full logging info
    if verbose == 0 && !rust_log_set {
        builder.format(|buf, record| {
            use std::io::Write;
            writeln!(buf, "{}", record.args())
        });
    } else {
        builder.format_timestamp(None); // No timestamps
        if rust_log_set {
            // When RUST_LOG is set, show full target/module info for debugging
            builder.format_module_path(true);
            builder.format_target(true);
        } else {
            // For -v/-vv, keep it clean without module paths
            builder.format_module_path(false);
            builder.format_target(false);
        }
    }

    builder.try_init().ok();
}

/// Main entry point shared by both CLI and Python extension
pub fn run_main(cli: &Cli) -> Result<()> {
    init_logging(cli.verbose);

    log::info!("Building Python application for Fastly Compute...");

    let config = ConfigBuilder::from_pyproject()
        .unwrap_or_else(|e| {
            log::warn!("Failed to load pyproject.toml: {}", e);
            ConfigBuilder::default()
        })
        .with_command(&cli.command)
        .resolve();

    log::debug!("Final resolved configuration: {config:?}");
    log::info!("  Entry point: {}", config.entry);
    log::info!("  Output: {}", config.output.display());

    build(config.output.clone(), config.entry)?;

    log::info!("✓ Build complete: {}", config.output.display());

    Ok(())
}

#[pyfunction]
fn run_main_py(args: Vec<String>) -> PyResult<()> {
    let cli = Cli::parse_from(args);

    run_main(&cli).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Build failed: {}", e))
    })
}

#[pymodule]
fn _fastly_compute_py(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(run_main_py, m)?)?;
    Ok(())
}

pub fn build(output: PathBuf, entry_name: String) -> Result<()> {
    let temp_dir = TempDir::new()?;
    let temp_path = temp_dir.path();

    log::debug!("Using temporary directory: {}", temp_path.display());

    let merged_wit_path = temp_path.join("merged.wit");
    fs::write(&merged_wit_path, MERGED_WIT)?;

    log::debug!("Wrote merged WIT to: {}", merged_wit_path.display());

    let temp_component_wasm_path = temp_path.join("component.wasm");

    log::info!("  Resolving Python dependencies...");
    let python_path = site_packages::build_python_path()?;
    log::debug!("Using python_path: {:?}", python_path);

    let python_path_refs: Vec<&str> = python_path.iter().map(|s| s.as_str()).collect();

    log::info!("  Componentizing Python application...");
    futures::executor::block_on(async {
        componentize_py::componentize(
            &[merged_wit_path.as_path()],
            Some("fastly:compute/service"),
            &[],
            false,
            Some("wit_world"),
            &python_path_refs,
            &[],
            &entry_name,
            &temp_component_wasm_path,
            None,
            false,
            &HashMap::new(),
            &HashMap::new(),
        )
        .await
    })?;

    log::debug!(
        "Generated component: {}",
        temp_component_wasm_path.display()
    );

    log::info!("  Composing final WebAssembly module...");
    let composed =
        compose_with_wasiless(&temp_component_wasm_path, WASILESS_WASM, WRAP_WAC, &output)?;

    fs::write(&output, composed)
        .with_context(|| format!("Failed to write output: {}", output.display()))?;

    log::debug!("Composed output: {}", output.display());

    Ok(())
}

fn compose_with_wasiless(
    component_path: &Path,
    wasiless_wasm: &[u8],
    wac: &str,
    output: &Path,
) -> Result<Vec<u8>> {
    if let Some(parent) = output.parent() {
        fs::create_dir_all(parent)?;
    }

    log::debug!("Composing with wasiless using wac-graph");

    let component_bytes = fs::read(component_path)
        .with_context(|| format!("Failed to read component: {}", component_path.display()))?;

    let mut graph = CompositionGraph::new();

    let wasiless_pkg =
        Package::from_bytes("fastly:wasiless", None, wasiless_wasm, graph.types_mut())?;
    let component_pkg = Package::from_bytes(
        "app:component",
        None,
        component_bytes.as_slice(),
        graph.types_mut(),
    )?;

    let _wasiless_id = graph.register_package(wasiless_pkg)?;
    let _component_id = graph.register_package(component_pkg)?;

    let wac_document = Document::parse(wac).context("Failed to parse WAC document")?;

    // Build packages map for resolution
    let mut packages = IndexMap::new();
    packages.insert(
        BorrowedPackageKey::from_name_and_version("fastly:wasiless", None),
        Vec::from(wasiless_wasm),
    );
    packages.insert(
        BorrowedPackageKey::from_name_and_version("app:component", None),
        component_bytes,
    );

    let resolution = wac_document
        .resolve(packages)
        .context("Failed to resolve WAC composition")?;

    let encoded = resolution
        .graph()
        .encode(EncodeOptions::default())
        .context("Failed to encode composition")?;

    log::debug!("Successfully composed to: {}", output.display());

    Ok(encoded)
}
