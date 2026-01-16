use anyhow::Result;
use clap::Parser;
use fastly_compute_py::cli::Cli;

fn main() -> Result<()> {
    let cli = Cli::parse();
    fastly_compute_py::run_main(&cli)
}
