use clap::Parser;
use dicty_sim::{
    BEHAVIOR_VERSION, CANCELLED, Result,
    accelerated::{self, Backend},
    aggregate::aggregate,
    config::Config,
    engine::{self, Context},
};
use serde_json::{Value, json};
use std::{
    fs,
    io::{self, BufRead, Write},
    path::{Path, PathBuf},
    sync::{Arc, Mutex, atomic::Ordering},
    time::{Instant, SystemTime, UNIX_EPOCH},
};

#[derive(Parser)]
#[command(version, about = "Rust engine for the captured Dicty simulation")]
struct Args {
    #[arg(long)]
    param: PathBuf,
    #[arg(long)]
    seed: Option<u64>,
    #[arg(long)]
    threads: Option<usize>,
    #[arg(long)]
    result: Option<PathBuf>,
    #[arg(long)]
    events: bool,
    #[arg(long, default_value = "auto", value_parser = ["auto", "cpu", "gpu"])]
    backend: String,
    #[arg(long, default_value_t = 128)]
    gpu_batch_size: usize,
}
struct Events {
    enabled: bool,
    run_id: String,
    output: Mutex<io::Stdout>,
}
impl Events {
    fn emit(&self, kind: &str, mut body: Value) {
        if !self.enabled {
            return;
        }
        body["protocol_version"] = json!(1);
        body["run_id"] = json!(self.run_id);
        body["type"] = json!(kind);
        if let Ok(mut out) = self.output.lock() {
            let _ = writeln!(out, "{body}");
            let _ = out.flush();
        }
    }
}
fn absolute(path: &Path) -> Result<PathBuf> {
    if path.is_absolute() {
        Ok(path.to_path_buf())
    } else {
        Ok(std::env::current_dir()
            .map_err(|e| e.to_string())?
            .join(path))
    }
}
/// Commit the result and its provenance together, restoring the original pair
/// if either replacement fails. This handles ordinary I/O failures; no pair of
/// independent filesystem renames can provide power-loss atomicity.
fn write_result_pair(
    result: &Path,
    result_data: &[u8],
    metadata: &Path,
    metadata_data: &[u8],
) -> Result<()> {
    struct Staged {
        destination: PathBuf,
        temporary: PathBuf,
        backup: Option<PathBuf>,
    }
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos();
    let mut staged: Vec<Staged> = Vec::new();
    let mut preserve_backups = false;
    let operation = (|| {
        for (path, data) in [(result, result_data), (metadata, metadata_data)] {
            let name = path
                .file_name()
                .ok_or("Result destination must name a file")?
                .to_string_lossy();
            let temporary =
                path.with_file_name(format!("{name}.tmp-{}-{nonce}", std::process::id()));
            let mut file = fs::OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(&temporary)
                .map_err(|e| format!("Cannot stage {}: {e}", path.display()))?;
            staged.push(Staged {
                destination: path.into(),
                temporary,
                backup: None,
            });
            file.write_all(data)
                .map_err(|e| format!("Cannot stage {}: {e}", path.display()))?;
            file.sync_all()
                .map_err(|e| format!("Cannot flush {}: {e}", path.display()))?;
        }
        // Keep writable backup copies; fs::copy would copy a Windows read-only
        // attribute and prevent cleaning a backup after a refused replacement.
        for item in &mut staged {
            match fs::metadata(&item.destination) {
                Ok(info) => {
                    if !info.is_file() {
                        return Err(format!(
                            "Result destination is not a file: {}",
                            item.destination.display()
                        ));
                    }
                    let backup = PathBuf::from(format!("{}.backup", item.temporary.display()));
                    let mut source = fs::File::open(&item.destination).map_err(|e| {
                        format!("Cannot back up {}: {e}", item.destination.display())
                    })?;
                    let mut copy = fs::OpenOptions::new()
                        .write(true)
                        .create_new(true)
                        .open(&backup)
                        .map_err(|e| format!("Cannot create result backup: {e}"))?;
                    item.backup = Some(backup);
                    io::copy(&mut source, &mut copy)
                        .map_err(|e| format!("Cannot back up result: {e}"))?;
                    copy.sync_all().map_err(|e| e.to_string())?;
                }
                Err(e) if e.kind() == io::ErrorKind::NotFound => {}
                Err(e) => {
                    return Err(format!(
                        "Cannot inspect {}: {e}",
                        item.destination.display()
                    ));
                }
            }
        }
        for i in 0..staged.len() {
            if let Err(error) = fs::rename(&staged[i].temporary, &staged[i].destination) {
                let mut message = format!(
                    "Cannot replace {}: {error}",
                    staged[i].destination.display()
                );
                for item in staged[..i].iter().rev() {
                    let restored = if let Some(backup) = &item.backup {
                        fs::rename(backup, &item.destination)
                    } else {
                        fs::remove_file(&item.destination)
                    };
                    if let Err(restore_error) = restored {
                        preserve_backups = true;
                        message.push_str(&format!(
                            "; restore failed for {}: {restore_error}; original retained at {:?}",
                            item.destination.display(),
                            item.backup
                        ));
                    }
                }
                return Err(message);
            }
        }
        Ok(())
    })();
    for item in staged {
        let _ = fs::remove_file(item.temporary);
        if !preserve_backups {
            if let Some(backup) = item.backup {
                let _ = fs::remove_file(backup);
            }
        }
    }
    operation
}
fn execute(args: &Args, events: &Events, ctx: &Context) -> Result<()> {
    let text = fs::read_to_string(&args.param)
        .map_err(|e| format!("Cannot read parameter file {}: {e}", args.param.display()))?;
    let cfg = Config::parse(&text)?;
    let seed = args.seed.unwrap_or_else(rand::random);
    let logical = std::thread::available_parallelism()
        .map(usize::from)
        .unwrap_or(1);
    if args.threads == Some(0) {
        return Err("--threads must be at least one".into());
    }
    if args.gpu_batch_size == 0 {
        return Err("--gpu-batch-size must be at least one".into());
    }
    let start = Instant::now();
    let mut backend = Backend::select(&args.backend, &cfg, args.gpu_batch_size)?;
    ctx.check()?;
    let default_workers = logical
        .saturating_sub(1)
        .max(1)
        .min(if backend.gpu.is_some() { 8 } else { usize::MAX });
    let threads = args
        .threads
        .unwrap_or(default_workers.min(cfg.n_runs.max(1) as usize));
    let backend_name = backend.name();
    let gpu_batch_size = backend.batch_size;
    let device = backend.device().map(str::to_owned);
    events.emit("started",json!({"seed":seed,"threads":threads,"total_repeats":cfg.n_runs,"total_cycles":cfg.n_dev.max(0),"engine_version":env!("CARGO_PKG_VERSION"),"backend":backend_name,"requested_backend":args.backend,"device":device,"backend_reason":backend.reason,"gpu_batch_size":gpu_batch_size}));
    eprintln!(
        "Seed: {seed}; backend: {backend_name}; CPU workers: {threads}; {}",
        backend.reason
    );
    // Large repeat jobs otherwise emit millions of JSON records. Count every
    // completed cycle, but send at most ten progress records per second.
    let progress_state = Mutex::new((None::<Instant>, 0u64));
    let progress = |p: engine::Progress| {
        if !events.enabled {
            return;
        }
        let mut state = progress_state.lock().unwrap();
        if p.phase == "cycle_complete" {
            state.1 += 1;
        }
        let total = (cfg.n_runs.max(0) as u64).saturating_mul(cfg.n_dev.max(0) as u64);
        if cfg.n_runs < 64
            || state.0.is_none_or(|last| last.elapsed().as_millis() >= 100)
            || (p.phase == "cycle_complete" && state.1 == total)
        {
            state.0 = Some(Instant::now());
            let mut body = serde_json::to_value(p).unwrap();
            body["completed_cycles"] = json!(state.1);
            events.emit("progress", body);
        }
    };
    let repeats = if let Some(gpu) = backend.gpu.as_mut() {
        accelerated::simulate(gpu, &cfg, seed, threads, gpu_batch_size, ctx, progress)?
    } else {
        engine::simulate(&cfg, seed, threads, ctx, progress)?
    };
    ctx.check()?;
    let result = aggregate(&cfg, &repeats)?;
    ctx.check()?;
    let output = cfg.output.string()?;
    let destination = if let Some(p) = &args.result {
        Some(absolute(p)?)
    } else if output.is_empty() {
        None
    } else {
        Some(absolute(Path::new(&format!("{output}.json")))?)
    };
    let mut metadata_path = None;
    if let Some(path) = &destination {
        let metadata = PathBuf::from(format!("{}.run.json", path.display()));
        let record = json!({"seed":seed,"engine_version":env!("CARGO_PKG_VERSION"),"behavior_version":BEHAVIOR_VERSION,"rng":"ChaCha12, seed_from_u64, stream=2*repeat+family; family 0 Python, 1 NumPy","threads":threads,"elapsed_seconds":start.elapsed().as_secs_f64(),"run_id":events.run_id,"source_commit":"62d707eee5f348320d6e50ab034b18a3a1a45b23","backend":backend_name,"requested_backend":args.backend,"device":device,"backend_reason":backend.reason,"gpu_batch_size":gpu_batch_size});
        // Compute/encode completely before changing an existing result file.
        let encoded = result.encode();
        ctx.check()?;
        write_result_pair(
            path,
            encoded.as_bytes(),
            &metadata,
            serde_json::to_string_pretty(&record).unwrap().as_bytes(),
        )?;
        metadata_path = Some(metadata);
    }
    events.emit("completed",json!({"result_path":destination,"metadata_path":metadata_path,"seed":seed,"elapsed_seconds":start.elapsed().as_secs_f64(),"backend":backend_name,"device":device}));
    eprintln!(
        "Simulation completed in {:.3} seconds",
        start.elapsed().as_secs_f64()
    );
    Ok(())
}
fn main() {
    let args = Args::parse();
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos();
    let events = Events {
        enabled: args.events,
        run_id: format!("{}-{nanos}", std::process::id()),
        output: Mutex::new(io::stdout()),
    };
    let ctx = Context::default();
    if args.events {
        let cancelled = Arc::clone(&ctx.cancelled);
        std::thread::spawn(move || {
            for line in io::stdin()
                .lock()
                .lines()
                .map_while(std::result::Result::ok)
            {
                if let Ok(value) = serde_json::from_str::<Value>(&line) {
                    if value.get("command").and_then(Value::as_str) == Some("cancel") {
                        cancelled.store(true, Ordering::Relaxed);
                        break;
                    }
                }
            }
        });
    }
    if let Err(error) = execute(&args, &events, &ctx) {
        if error == CANCELLED {
            events.emit("cancelled", json!({"message":error}));
            eprintln!("{error}");
            std::process::exit(130);
        }
        events.emit("error", json!({"message":error}));
        eprintln!("{error}");
        std::process::exit(1);
    }
}
