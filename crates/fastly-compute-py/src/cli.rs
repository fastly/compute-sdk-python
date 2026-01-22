use clap::{Parser, Subcommand};
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "fastly-compute-py")]
#[command(version)]
#[command(about = "Build Python applications for Fastly Compute", long_about = None)]
#[command(after_help = "LOGGING:\n  \
    By default, only fastly-compute-py logs are shown.\n  \
    Use RUST_LOG environment variable to show logs from dependencies:\n    \
    RUST_LOG=debug fastly-compute-py build\n    \
    RUST_LOG=componentize_py=debug fastly-compute-py build")]
pub struct Cli {
    /// Increase logging verbosity (-v for info, -vv for debug, -vvv for trace)
    #[arg(short, long, action = clap::ArgAction::Count)]
    pub verbose: u8,

    #[command(subcommand)]
    pub command: Command,
}

#[derive(Subcommand)]
pub enum Command {
    /// Build a Python application into a WebAssembly component
    Build {
        /// Output path for the WASM file (default: bin/main.wasm)
        #[arg(short, long)]
        output: Option<PathBuf>,

        /// Entry point module (default: main or auto-detect)
        #[arg(short, long)]
        entry: Option<String>,
    },
}
