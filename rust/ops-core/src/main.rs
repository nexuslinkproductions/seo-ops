//! seo-ops integrity and validation CLI.
//!
//! Stateless, std-only subprocess component:
//!   ops-core verify-evidence --dir <dir> [--manifest <file>]
//!   ops-core validate-csv <file> [--required col1,col2]
//!
//! Output is JSON on stdout. Python orchestrates; this crate owns no
//! business rules.

mod csvparse;
mod sha256;

use std::collections::HashMap;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::ExitCode;
use std::thread;

fn usage() -> ! {
    eprintln!("usage: ops-core <verify-evidence|validate-csv> ...");
    std::process::exit(2);
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        usage();
    }
    match args[1].as_str() {
        "verify-evidence" => verify_evidence_cmd(&args[2..]),
        "validate-csv" => validate_csv_cmd(&args[2..]),
        other => {
            eprintln!("unknown subcommand: {other}");
            usage();
        }
    }
}

fn esc_json(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('"');
    for ch in s.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

// ---------- verify-evidence ----------

fn collect_files(dir: &Path) -> std::io::Result<Vec<PathBuf>> {
    let mut out = Vec::new();
    for entry in fs::read_dir(dir)? {
        let entry = entry?;
        let path = entry.path();
        if path.is_dir() {
            out.extend(collect_files(&path)?);
        } else if path.is_file() {
            out.push(path);
        }
    }
    Ok(out)
}

fn parse_manifest(path: &Path) -> std::io::Result<HashMap<String, String>> {
    let text = fs::read_to_string(path)?;
    let mut map = HashMap::new();
    for line in text.lines() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        if let Some((digest, rel)) = line.split_once("  ") {
            map.insert(rel.trim().to_string(), digest.trim().to_string());
        }
    }
    Ok(map)
}

fn verify_evidence_cmd(args: &[String]) -> ExitCode {
    let mut dir: Option<PathBuf> = None;
    let mut manifest: Option<PathBuf> = None;
    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--dir" => {
                i += 1;
                dir = Some(PathBuf::from(&args[i]));
            }
            "--manifest" => {
                i += 1;
                manifest = Some(PathBuf::from(&args[i]));
            }
            other => {
                eprintln!("unknown flag: {other}");
                usage();
            }
        }
        i += 1;
    }
    let dir = match dir {
        Some(d) => d,
        None => usage(),
    };
    let expected: HashMap<String, String> = match &manifest {
        Some(m) => match parse_manifest(m) {
            Ok(map) => map,
            Err(err) => {
                eprintln!("manifest error: {err}");
                return ExitCode::from(2);
            }
        },
        None => HashMap::new(),
    };
    let files = match collect_files(&dir) {
        Ok(files) => files,
        Err(err) => {
            eprintln!("dir error: {err}");
            return ExitCode::from(2);
        }
    };

    let hashed = hash_files_parallel(&dir, &files);
    let mut mismatches: Vec<String> = Vec::new();
    let mut missing: Vec<String> = Vec::new();
    let mut extra: Vec<String> = Vec::new();

    let mut seen: Vec<String> = Vec::new();
    for (rel, digest) in hashed {
        seen.push(rel.clone());
        match expected.get(&rel) {
            Some(want) if *want != digest => {
                mismatches.push(format!(
                    "{{\"path\":{},\"expected\":{},\"actual\":{}}}",
                    esc_json(&rel),
                    esc_json(want),
                    esc_json(&digest)
                ));
            }
            None => {
                extra.push(format!("{{\"path\":{}}}", esc_json(&rel)));
            }
            _ => {}
        }
    }
    for (rel, want) in &expected {
        if !seen.contains(rel) {
            missing.push(format!(
                "{{\"path\":{},\"expected\":{}}}",
                esc_json(rel),
                esc_json(want)
            ));
        }
    }
    let clean = mismatches.is_empty() && missing.is_empty() && extra.is_empty();
    println!(
        "{{\"tool\":\"ops-core\",\"subcommand\":\"verify-evidence\",\"checked\":{},\"clean\":{},\"mismatches\":[{}],\"missing\":[{}],\"extra\":[{}],\"errors\":[]}}",
        files.len(),
        clean,
        mismatches.join(","),
        missing.join(","),
        extra.join(",")
    );
    ExitCode::SUCCESS
}

fn hash_files_parallel(base: &Path, files: &[PathBuf]) -> Vec<(String, String)> {
    let workers = thread::available_parallelism()
        .map(|n| n.get())
        .unwrap_or(4)
        .min(files.len().max(1));
    let chunk = (files.len() + workers - 1) / workers;
    let mut results: Vec<(String, String)> = Vec::new();
    thread::scope(|scope| {
        let mut handles = Vec::new();
        for part in files.chunks(chunk.max(1)) {
            let part: Vec<PathBuf> = part.to_vec();
            let base = base.to_path_buf();
            handles.push(scope.spawn(move || {
                let mut out = Vec::new();
                for path in part {
                    let rel = path
                        .strip_prefix(&base)
                        .unwrap_or(&path)
                        .to_string_lossy()
                        .replace('\\', "/");
                    if let Ok(bytes) = fs::read(&path) {
                        out.push((rel, sha256::hash_bytes(&bytes)));
                    }
                }
                out
            }));
        }
        for handle in handles {
            results.extend(handle.join().unwrap_or_default());
        }
    });
    results.sort();
    results
}

// ---------- validate-csv ----------

fn validate_csv_cmd(args: &[String]) -> ExitCode {
    let mut file: Option<PathBuf> = None;
    let mut required: Vec<String> = Vec::new();
    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--required" => {
                i += 1;
                required = args[i]
                    .split(',')
                    .map(|s| s.trim().to_string())
                    .filter(|s| !s.is_empty())
                    .collect();
            }
            other if !other.starts_with("--") => {
                file = Some(PathBuf::from(other));
            }
            other => {
                eprintln!("unknown flag: {other}");
                usage();
            }
        }
        i += 1;
    }
    let file = match file {
        Some(f) => f,
        None => usage(),
    };
    let text = match fs::read_to_string(&file) {
        Ok(t) => t,
        Err(err) => {
            eprintln!("read error: {err}");
            return ExitCode::from(2);
        }
    };
    let mut rows: Vec<Vec<String>> = Vec::new();
    for line in text.lines() {
        rows.push(csvparse::parse_line(line));
    }
    let columns: Vec<String> = rows.first().cloned().unwrap_or_default();
    let mut required_json: Vec<String> = Vec::new();
    let mut ok = true;
    for col in &required {
        let present = columns.contains(col);
        if !present {
            ok = false;
        }
        required_json.push(format!(
            "{}:{}",
            esc_json(col),
            if present { "true" } else { "false" }
        ));
    }
    let columns_json: Vec<String> = columns.iter().map(|c| esc_json(c)).collect();
    println!(
        "{{\"tool\":\"ops-core\",\"subcommand\":\"validate-csv\",\"rows\":{},\"columns\":[{}],\"required\":{{{}}},\"ok\":{}}}",
        rows.len().saturating_sub(1),
        columns_json.join(","),
        required_json.join(","),
        ok
    );
    ExitCode::SUCCESS
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sha256_known_vectors() {
        assert_eq!(
            sha256::hash_bytes(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
        assert_eq!(
            sha256::hash_bytes(b""),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        );
    }

    #[test]
    fn csv_quoted_fields() {
        let row = csvparse::parse_line("a,\"b,c\",\"say \"\"hi\"\"\"");
        assert_eq!(row, vec!["a", "b,c", "say \"hi\""]);
    }
}
