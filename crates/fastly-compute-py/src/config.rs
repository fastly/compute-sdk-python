use anyhow::{Context, Result};
use serde::Deserialize;
use std::fs;
use std::path::PathBuf;

use crate::cli::Command;

#[derive(Debug, Deserialize, Default, Clone)]
pub struct ConfigSource {
    pub entry: Option<String>,
    pub output: Option<PathBuf>,
    pub virtualenv: Option<PathBuf>,
}

#[derive(Deserialize, Debug)]
struct PyProjectToml {
    tool: Option<Tool>,
}

#[derive(Deserialize, Debug)]
#[serde(rename_all = "kebab-case")]
struct Tool {
    fastly_compute: Option<ConfigSource>,
}

#[derive(Debug, Default)]
pub struct ConfigBuilder {
    pyproject: ConfigSource,
    cli: ConfigSource,
}

impl ConfigBuilder {
    /// Load configuration from pyproject.toml if it exists
    pub fn from_pyproject() -> Result<Self> {
        let path = PathBuf::from("pyproject.toml");
        if !path.exists() {
            log::debug!("No pyproject.toml found");
            return Ok(Self::default());
        }

        let content = fs::read_to_string(&path)
            .with_context(|| format!("Failed to read {}", path.display()))?;

        let pyproject_toml: PyProjectToml = toml::from_str(&content)
            .with_context(|| format!("Failed to parse {}", path.display()))?;

        let pyproject = pyproject_toml
            .tool
            .and_then(|t| t.fastly_compute)
            .unwrap_or_default();

        if pyproject.entry.is_some() || pyproject.output.is_some() {
            log::debug!("Config from pyproject.toml: {pyproject:?}");
        }

        Ok(Self {
            pyproject,
            cli: ConfigSource::default(),
        })
    }

    /// Add CLI command arguments as a configuration source
    pub fn with_command(mut self, command: &Command) -> Self {
        match command {
            Command::Build {
                entry,
                output,
                virtualenv,
            } => {
                if entry.is_some() || output.is_some() || virtualenv.is_some() {
                    log::debug!("Config from CLI: entry={entry:?}, output={output:?}, virtualenv={virtualenv:?}");
                }
                self.cli.entry = entry.clone();
                self.cli.output = output.clone();
                self.cli.virtualenv = virtualenv.clone();
            }
        }
        self
    }

    /// Resolve into a final Config based on the following resolution order:
    /// CLI > pyproject.toml > defaults.
    pub fn resolve(self) -> Config {
        let entry = self.cli.entry.or(self.pyproject.entry).unwrap_or_else(|| {
            log::debug!("Using default: entry=\"main\"");
            "main".to_string()
        });

        let output = self
            .cli
            .output
            .or(self.pyproject.output)
            .unwrap_or_else(|| {
                log::debug!("Using default: output=\"bin/main.wasm\"");
                PathBuf::from("bin/main.wasm")
            });

        Config {
            entry,
            output,
            virtualenv: self.cli.virtualenv,
        }
    }
}

#[derive(Debug)]
pub struct Config {
    pub entry: String,
    pub output: PathBuf,
    pub virtualenv: Option<PathBuf>,
}
