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

        /// Virtual environment in which to look for modules (default:
        /// VIRTUAL_ENV env var or .venv)
        #[arg(short, long)]
        virtualenv: Option<PathBuf>,
    },
    /// Generate WIT binding stubs for use with type checkers and IDEs
    Bindings {
        /// WIT directory to generate bindings from (default: wit)
        #[arg(short = 'd', long)]
        wit_dir: Option<PathBuf>,

        /// WIT world to target (e.g. fastly:compute/service@0.1.0)
        #[arg(short = 'w', long)]
        world: Option<String>,

        /// Python module name for the generated bindings (default: wit_world)
        #[arg(long)]
        world_module: Option<String>,

        /// Output directory for the generated stubs
        output_dir: PathBuf,
    },
    /// List project dependencies in the specified format
    Dependencies {
        /// Output format for dependencies
        #[arg(short, long, default_value = "json")]
        format: DependencyFormat,

        /// Virtual environment in which to look for modules (default:
        /// VIRTUAL_ENV env var or .venv)
        #[arg(short, long)]
        virtualenv: Option<PathBuf>,
    },
}

#[derive(Clone, Debug, clap::ValueEnum)]
pub enum DependencyFormat {
    /// JSON object format: {"package-name": "1.0.0", ...}
    /// Matches the format used in fastly_data metadata
    Json,
}
