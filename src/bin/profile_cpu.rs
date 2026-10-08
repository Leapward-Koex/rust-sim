//! Read-only performance probe for phase boundaries; executes the existing CPU API.
//! Run with `cargo run --release --bin profile_cpu` and retain stdout as JSON.
use dicty_sim::{
    Result,
    aggregate::aggregate,
    config::Config,
    engine::{Context, RepeatResult, development, growth, initialize, sex},
    json::Json,
    model::{Population, ch_effectiveness, counts, measure},
    random::{Choices, NativeChoices},
};
use serde_json::json;
use std::{hint::black_box, time::Instant};

#[derive(Default, serde::Serialize)]
struct Timings {
    initialize: f64,
    growth: f64,
    development: f64,
    sex: f64,
    measurement: f64,
    aggregation: f64,
}

#[derive(Default, serde::Serialize)]
struct GrowthTimings {
    germination: f64,
    weights: f64,
    weighted_selection: f64,
    cloning: f64,
    mutation: f64,
}

// Diagnostic copy of the CPU growth loop, with timestamps only at stage
// boundaries. The production implementation is never called through this copy.
fn split_growth(
    mut pop: Population,
    cfg: &Config,
    rng: &mut NativeChoices,
    ctx: &Context,
    timings: &mut GrowthTimings,
) -> Result<Population> {
    let start = Instant::now();
    let mut keep = vec![true; pop.len()];
    for (i, yes) in keep.iter_mut().enumerate() {
        if i % 256 == 0 {
            ctx.check()?;
        }
        if counts(pop.genome(i)).0 > 0
            && (1.0 - cfg.ch_germ.number()? * ch_effectiveness(pop.genome(i), cfg)?)
                < rng.uniform()?
        {
            *yes = false;
        }
    }
    pop.retain_mask(&keep);
    timings.germination += start.elapsed().as_secs_f64();
    let mut next = Population::new(pop.loci);
    let mut weights = Vec::new();
    for _ in 0..cfg.vg.integer()? {
        ctx.check()?;
        let start = Instant::now();
        weights.clear();
        for i in 0..pop.len() {
            if i % 256 == 0 {
                ctx.check()?;
            }
            let (c, r, _) = counts(pop.genome(i));
            let fit = (1.0 - cfg.c_ch.number()? * c as f64)
                + (1.0 - cfg.c_res.number()? * r as f64) / 2.0;
            pop.cells[i].fitness = fit;
            weights.push(fit);
        }
        timings.weights += start.elapsed().as_secs_f64();
        let start = Instant::now();
        let selected = rng.weighted(&weights, cfg.n.integer()?)?;
        timings.weighted_selection += start.elapsed().as_secs_f64();
        let start = Instant::now();
        next.cells.clear();
        next.genes.clear();
        next.reserve(selected.len())?;
        for (i, &parent) in selected.iter().enumerate() {
            if i % 256 == 0 {
                ctx.check()?;
            }
            next.copy_cell(&pop, parent);
        }
        timings.cloning += start.elapsed().as_secs_f64();
        let start = Instant::now();
        for (i, gene) in next.genes.iter_mut().enumerate() {
            if i % 1024 == 0 {
                ctx.check()?;
            }
            if rng.uniform()? <= cfg.m_ch.number()? {
                *gene ^= 1;
            }
            if rng.uniform()? <= cfg.m_re.number()? {
                *gene ^= 2;
            }
        }
        timings.mutation += start.elapsed().as_secs_f64();
        std::mem::swap(&mut pop, &mut next);
    }
    Ok(pop)
}

fn profile_growth() -> Result<serde_json::Value> {
    let cfg = config(1, 50, true, 0)?;
    let ctx = Context::default();
    let mut rng = NativeChoices::new(20261007, 0, ctx.cancelled.clone());
    let mut oracle_rng = NativeChoices::new(20261007, 0, ctx.cancelled.clone());
    let mut pop = initialize(&cfg, &mut rng, &ctx)?;
    let mut oracle = initialize(&cfg, &mut oracle_rng, &ctx)?;
    let mut timings = GrowthTimings::default();
    for _ in 0..cfg.n_dev {
        pop = split_growth(pop, &cfg, &mut rng, &ctx, &mut timings)?;
        oracle = growth(oracle, &cfg, &mut oracle_rng, &ctx)?;
        assert_eq!(pop.genes, oracle.genes, "diagnostic growth genotype parity");
        assert!(
            pop.cells
                .iter()
                .zip(&oracle.cells)
                .all(|(a, b)| a.mating_type == b.mating_type && a.fitness == b.fitness)
        );
        pop = development(pop, &cfg, &mut rng, &ctx)?;
        oracle = development(oracle, &cfg, &mut oracle_rng, &ctx)?;
    }
    Ok(
        json!({"n_runs": 1, "n_dev": cfg.n_dev, "n": cfg.n.integer()?, "seconds": timings,
        "method": "Diagnostic stage-timed growth copy; checked against production growth after every generation group with same RNG stream"}),
    )
}

fn config(repeats: i64, cycles: i64, mixed: bool, interval: i64) -> Result<Config> {
    let mut raw = Json::parse(include_str!("../../reference-source/import_template.json"))?;
    raw.insert("n_runs", Json::integer(repeats));
    raw.insert("n_dev", Json::integer(cycles));
    raw.insert("sex_cycle_interval", Json::integer(interval));
    raw.insert("output_filepath", Json::String(String::new()));
    if mixed {
        raw.insert("ch_start", Json::number(0.3));
        raw.insert("res_start", Json::number(0.2));
    }
    Config::from_json(raw)
}

fn run_case(name: &str, cfg: Config) -> Result<(serde_json::Value, Vec<RepeatResult>)> {
    let ctx = Context::default();
    let mut timings = Timings::default();
    let mut repeats = Vec::new();
    let wall = Instant::now();
    for repeat in 0..cfg.n_runs as usize {
        let mut rng = NativeChoices::new(20261007, repeat, ctx.cancelled.clone());
        let start = Instant::now();
        let mut pop = initialize(&cfg, &mut rng, &ctx)?;
        timings.initialize += start.elapsed().as_secs_f64();
        let start = Instant::now();
        let mut measurements = vec![measure(&pop, &cfg)?];
        timings.measurement += start.elapsed().as_secs_f64();
        let mut sex_cycles = Vec::new();
        for cycle in 1..=cfg.n_dev {
            let (scheduled, interval) = cfg.scheduled(cycle)?;
            if scheduled {
                let start = Instant::now();
                pop = sex(pop, &cfg, &mut rng, &ctx)?;
                timings.sex += start.elapsed().as_secs_f64();
            }
            let start = Instant::now();
            pop = growth(pop, &cfg, &mut rng, &ctx)?;
            timings.growth += start.elapsed().as_secs_f64();
            let start = Instant::now();
            pop = development(pop, &cfg, &mut rng, &ctx)?;
            timings.development += start.elapsed().as_secs_f64();
            let start = Instant::now();
            measurements.push(measure(&pop, &cfg)?);
            timings.measurement += start.elapsed().as_secs_f64();
            if scheduled && interval {
                sex_cycles.push(cycle);
            }
        }
        repeats.push(RepeatResult {
            measurements,
            sex_cycles,
            population: Population::new(cfg.loci()),
        });
    }
    let start = Instant::now();
    black_box(aggregate(&cfg, &repeats)?);
    timings.aggregation = start.elapsed().as_secs_f64();
    Ok((
        json!({"name": name, "n": cfg.n.integer()?, "n_runs": cfg.n_runs,
        "n_dev": cfg.n_dev, "gene_pairs": cfg.gene_pairs, "vg": cfg.vg.integer()?,
        "workers": 1, "seed": 20261007, "seconds": timings,
        "wall_seconds": wall.elapsed().as_secs_f64()}),
        repeats,
    ))
}

fn main() -> Result<()> {
    let mut cases = Vec::new();
    let (ordinary, reference) = run_case("ordinary_10_repeats", config(10, 50, false, 0)?)?;
    cases.push(ordinary);
    cases.push(run_case("mixed_10_repeats", config(10, 50, true, 0)?)?.0);
    cases.push(run_case("sex_heavy_10_repeats", config(10, 50, true, 2)?)?.0);
    cases.push(run_case("ordinary_1000_short_repeats", config(1000, 2, false, 0)?)?.0);
    // Isolate aggregation cost at the requested repeat count. Histories are
    // synthetic repetitions of real measurements; no biological run is claimed.
    let cfg = config(1000, 500, false, 0)?;
    let repeats: Vec<_> = (0..1000)
        .map(|r| RepeatResult {
            measurements: (0..501)
                .map(|t| reference[r % reference.len()].measurements[t % 51].clone())
                .collect(),
            sex_cycles: Vec::new(),
            population: Population::new(cfg.loci()),
        })
        .collect();
    let start = Instant::now();
    black_box(aggregate(&cfg, &repeats)?);
    let aggregation = json!({"n_runs": 1000, "n_dev": 500,
        "synthetic_histories": true, "seconds": start.elapsed().as_secs_f64()});
    println!("{}", serde_json::to_string_pretty(&json!({
        "method": "One worker; unchanged public CPU phase functions; wall-clock phase timings; no progress or output serialization",
        "cases": cases, "aggregation_only": aggregation, "growth_detail": profile_growth()?
    })).unwrap());
    Ok(())
}
