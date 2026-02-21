//! 💠 JadeGate CLI (Rust)

use std::env;
use std::path::Path;

fn main() {
    let args: Vec<String> = env::args().collect();

    if args.len() < 2 {
        print_help();
        return;
    }

    match args[1].as_str() {
        "help" | "--help" | "-h" => print_help(),
        "verify" => {
            if args.len() < 3 {
                eprintln!("Usage: jade verify <file.json>");
                std::process::exit(1);
            }
            let validator = jadegate::JadeValidator::new();
            match validator.validate_file(Path::new(&args[2])) {
                Ok(result) => {
                    if result.valid {
                        println!("💠 VALID — {} layers passed", result.layers_passed);
                    } else {
                        println!("❌ INVALID — stopped at layer {}", result.layers_passed);
                        for issue in &result.issues {
                            let icon = match issue.severity {
                                jadegate::validator::Severity::Error => "❌",
                                jadegate::validator::Severity::Warning => "⚠️",
                                jadegate::validator::Severity::Info => "ℹ️",
                            };
                            println!("  {} [L{}] {}: {}", icon, issue.layer, issue.code, issue.message);
                        }
                        std::process::exit(1);
                    }
                }
                Err(e) => {
                    eprintln!("Error: {}", e);
                    std::process::exit(1);
                }
            }
        }
        "status" => {
            println!("\n💠 JadeGate (Rust Engine)");
            println!("========================");
            println!("Version:  1.0.0");
            println!("Engine:   5-layer deterministic verification");
            println!("Crypto:   Ed25519 (ed25519-dalek)");
            println!("Runtime:  Native binary\n");
        }
        _ => {
            eprintln!("Unknown command: {}", args[1]);
            print_help();
            std::process::exit(1);
        }
    }
}

fn print_help() {
    println!("
💠 JadeGate CLI (Rust)
======================
Usage:
  jade help              Show this help
  jade status            Show engine status
  jade verify <file>     Verify a skill file (5-layer)
");
}
