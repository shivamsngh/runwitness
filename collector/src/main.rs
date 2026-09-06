use serde::Serialize;
use std::collections::{HashMap, HashSet};
use std::env;
use std::fs::File;
use std::path::PathBuf;
use std::process::{Child, Command, ExitCode};
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};
use sysinfo::{Pid, ProcessRefreshKind, ProcessesToUpdate, System};

#[derive(Serialize)]
struct ObservedProcess {
    pid: u32,
    parent_pid: Option<u32>,
    executable: Option<String>,
    name: String,
}

#[derive(Serialize)]
struct Evidence {
    schema_version: &'static str,
    collector: CollectorIdentity,
    scope: Scope,
    started_at_unix_ms: u128,
    root_pid: u32,
    sample_interval_ms: u64,
    samples: u64,
    wall_seconds: f64,
    exit_code: Option<i32>,
    peak_tree_rss_bytes: u64,
    peak_process_count: usize,
    observed_processes: Vec<ObservedProcess>,
}

#[derive(Serialize)]
struct CollectorIdentity {
    name: &'static str,
    version: &'static str,
}

#[derive(Serialize)]
struct Scope {
    includes: &'static str,
    excludes: &'static str,
    command_arguments_recorded: bool,
}

struct Options {
    output: PathBuf,
    interval_ms: u64,
    command: Vec<String>,
}

fn usage(message: &str) -> ! {
    eprintln!(
        "{message}\nusage: fieldkit-collector run --output FILE [--sample-interval-ms N] -- COMMAND [ARG ...]"
    );
    std::process::exit(2);
}

fn parse_args() -> Options {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.first().map(String::as_str) != Some("run") {
        usage("expected 'run'");
    }
    let separator = args
        .iter()
        .position(|arg| arg == "--")
        .unwrap_or_else(|| usage("missing '--' before command"));
    let mut output = None;
    let mut interval_ms = 100_u64;
    let mut index = 1;
    while index < separator {
        match args[index].as_str() {
            "--output" => {
                index += 1;
                output = args.get(index).map(PathBuf::from);
            }
            "--sample-interval-ms" => {
                index += 1;
                interval_ms = args
                    .get(index)
                    .and_then(|value| value.parse().ok())
                    .filter(|value| *value >= 10)
                    .unwrap_or_else(|| {
                        usage("sample interval must be an integer of at least 10 ms")
                    });
            }
            other => usage(&format!("unknown option: {other}")),
        }
        index += 1;
    }
    let command = args[(separator + 1)..].to_vec();
    if command.is_empty() {
        usage("missing command");
    }
    Options {
        output: output.unwrap_or_else(|| usage("missing --output")),
        interval_ms,
        command,
    }
}

fn descendants(system: &System, root: Pid) -> HashSet<Pid> {
    let mut selected = HashSet::from([root]);
    loop {
        let before = selected.len();
        for (pid, process) in system.processes() {
            if process
                .parent()
                .is_some_and(|parent| selected.contains(&parent))
            {
                selected.insert(*pid);
            }
        }
        if selected.len() == before {
            return selected;
        }
    }
}

fn sample(
    system: &mut System,
    root: Pid,
    known: &mut HashMap<u32, ObservedProcess>,
) -> (u64, usize) {
    system.refresh_processes_specifics(
        ProcessesToUpdate::All,
        true,
        ProcessRefreshKind::everything(),
    );
    let selected = descendants(system, root);
    let rss = selected
        .iter()
        .filter_map(|pid| system.process(*pid))
        .map(|process| process.memory())
        .sum();
    for pid in &selected {
        if let Some(process) = system.process(*pid) {
            known
                .entry(pid.as_u32())
                .or_insert_with(|| ObservedProcess {
                    pid: pid.as_u32(),
                    parent_pid: process.parent().map(Pid::as_u32),
                    executable: process
                        .exe()
                        .map(|path| path.to_string_lossy().into_owned()),
                    name: process.name().to_string_lossy().into_owned(),
                });
        }
    }
    (rss, selected.len())
}

fn run(mut child: Child, options: &Options) -> Result<(Evidence, i32), String> {
    let root = Pid::from_u32(child.id());
    let started_at = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|e| e.to_string())?
        .as_millis();
    let started = Instant::now();
    let mut system = System::new();
    let mut known = HashMap::new();
    let mut peak_rss = 0;
    let mut peak_count = 0;
    let mut samples = 0;
    loop {
        let (rss, count) = sample(&mut system, root, &mut known);
        peak_rss = peak_rss.max(rss);
        peak_count = peak_count.max(count);
        samples += 1;
        if let Some(status) = child.try_wait().map_err(|e| e.to_string())? {
            let code = status.code().unwrap_or(1);
            let mut observed: Vec<_> = known.into_values().collect();
            observed.sort_by_key(|item| item.pid);
            return Ok((
                Evidence {
                    schema_version: "0.1",
                    collector: CollectorIdentity {
                        name: "fieldkit-collector",
                        version: env!("CARGO_PKG_VERSION"),
                    },
                    scope: Scope {
                        includes: "benchmark root process and descendants observed during sampling",
                        excludes: "pre-existing services, unobserved short-lived processes, GPU memory, and network activity",
                        command_arguments_recorded: false,
                    },
                    started_at_unix_ms: started_at,
                    root_pid: root.as_u32(),
                    sample_interval_ms: options.interval_ms,
                    samples,
                    wall_seconds: started.elapsed().as_secs_f64(),
                    exit_code: status.code(),
                    peak_tree_rss_bytes: peak_rss,
                    peak_process_count: peak_count,
                    observed_processes: observed,
                },
                code,
            ));
        }
        thread::sleep(Duration::from_millis(options.interval_ms));
    }
}

fn main() -> ExitCode {
    let options = parse_args();
    let child = match Command::new(&options.command[0])
        .args(&options.command[1..])
        .spawn()
    {
        Ok(child) => child,
        Err(error) => {
            eprintln!("could not start benchmark: {error}");
            return ExitCode::from(126);
        }
    };
    let (evidence, code) = match run(child, &options) {
        Ok(value) => value,
        Err(error) => {
            eprintln!("collector failed: {error}");
            return ExitCode::from(125);
        }
    };
    let file = match File::create(&options.output) {
        Ok(file) => file,
        Err(error) => {
            eprintln!("could not create evidence file: {error}");
            return ExitCode::from(125);
        }
    };
    if let Err(error) = serde_json::to_writer_pretty(file, &evidence) {
        eprintln!("could not write evidence: {error}");
        return ExitCode::from(125);
    }
    ExitCode::from(u8::try_from(code.clamp(0, 255)).unwrap_or(1))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn records_a_launched_process_without_arguments() {
        let child = Command::new("sh")
            .args(["-c", "sleep 0.05"])
            .spawn()
            .expect("test process should launch");
        let options = Options {
            output: PathBuf::from("unused.json"),
            interval_ms: 10,
            command: vec![],
        };
        let (evidence, code) = run(child, &options).expect("collection should succeed");
        assert_eq!(code, 0);
        assert!(evidence.samples >= 1);
        assert!(evidence.peak_process_count >= 1);
        assert!(evidence.peak_tree_rss_bytes > 0);
        assert!(!evidence.scope.command_arguments_recorded);
    }
}
