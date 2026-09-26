use std::env;
use std::path::PathBuf;
use std::time::Instant;

use koru_scan_todo::{count_todo_markers_in_project, ScanOptions, DEFAULT_SCAN_EXCLUDES};

fn print_usage() {
    eprintln!("Usage: koru-scan-todo [DIRECTORY] [OPTIONS]");
    eprintln!();
    eprintln!("Options:");
    eprintln!("  --min N          Minimum markers per file (default: 3)");
    eprintln!("  --max-files N    Maximum files to walk (default: 2000)");
    eprintln!("  --json           Output result as JSON");
    eprintln!("  --benchmark      Measure and report execution time");
    eprintln!("  -h, --help       Show this help message");
}

fn main() {
    let mut args = env::args().skip(1);
    let mut dir = PathBuf::from(".");
    let mut min_per_file = 3;
    let mut max_files = 2000;
    let mut output_json = false;
    let mut benchmark = false;

    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--min" => {
                if let Some(val) = args.next() {
                    min_per_file = val.parse().unwrap_or(3);
                }
            }
            "--max-files" => {
                if let Some(val) = args.next() {
                    max_files = val.parse().unwrap_or(2000);
                }
            }
            "--json" => {
                output_json = true;
            }
            "--benchmark" => {
                benchmark = true;
            }
            "-h" | "--help" => {
                print_usage();
                return;
            }
            other if !other.starts_with('-') => {
                dir = PathBuf::from(other);
            }
            unknown => {
                eprintln!("Unknown argument: {unknown}");
                print_usage();
                std::process::exit(1);
            }
        }
    }

    let options = ScanOptions {
        min_per_file,
        max_files_walked: max_files,
        excludes: DEFAULT_SCAN_EXCLUDES,
    };

    let start = Instant::now();
    let results = count_todo_markers_in_project(&dir, &options);
    let elapsed = start.elapsed();

    let total_markers: usize = results.values().sum();
    let elapsed_ms = elapsed.as_secs_f64() * 1000.0;

    if output_json || benchmark {
        println!("{{");
        println!("  \"totalMarkers\": {total_markers},");
        println!("  \"matchingFiles\": {},", results.len());
        println!("  \"elapsedMs\": {elapsed_ms:.3},");
        println!("  \"files\": {{");
        let mut first = true;
        for (file, count) in &results {
            if !first {
                println!(",");
            }
            first = false;
            print!("    {:?}: {}", file, count);
        }
        if !results.is_empty() {
            println!();
        }
        println!("  }}");
        println!("}}");
    } else {
        println!("koru-scan-todo scanned directory: {}", dir.display());
        println!("Found {total_markers} markers across {} files (min: {min_per_file}):", results.len());
        for (file, count) in &results {
            println!("  {file}: {count}");
        }
        println!("Completed in {elapsed_ms:.2} ms");
    }
}
