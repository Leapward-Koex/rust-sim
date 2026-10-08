//! Batches independent repeats for GPU growth, retaining the existing CPU
//! implementation of initialization, germination, sex, development and metrics.
use crate::{
    Result,
    config::Config,
    engine::{self, Context, Progress, RepeatResult},
    gpu::GpuGrowth,
    model::{Population, measure},
    random::NativeChoices,
};
use rayon::prelude::*;

pub struct Backend {
    pub gpu: Option<GpuGrowth>,
    pub reason: String,
    pub batch_size: usize,
}
impl Backend {
    pub fn select(requested: &str, cfg: &Config, batch_size: usize) -> Result<Self> {
        if requested == "cpu" {
            return Ok(Self {
                gpu: None,
                reason: "CPU requested".into(),
                batch_size,
            });
        }
        if requested == "auto"
            && !(cfg.n_runs >= 64
                && cfg.n.integer().is_ok_and(|n| n >= 2048)
                && cfg.vg.integer().is_ok_and(|n| n >= 2)
                && cfg.n_dev > 0)
        {
            return Ok(Self { gpu: None, reason: "CPU selected for a small workload (GPU batching requires at least 64 repeats, 2048 cells and 2 growth generations)".into(), batch_size });
        }
        let candidate = GpuGrowth::supported(cfg).and_then(|()| {
            let gpu = GpuGrowth::new()?;
            let mut capacity = cfg.n.integer()? as usize;
            // Conservative sex-output bound, without rejecting unused fields.
            // Germination and development can only reduce these populations.
            let sex_possible = cfg.n_dev > 0
                && (cfg.interval.number().is_ok_and(|x| x != 0.0)
                    || cfg
                        .schedule
                        .value()
                        .and_then(|v| v.as_array())
                        .is_ok_and(|xs| {
                            xs.iter().any(|x| {
                                x.as_number()
                                    .is_ok_and(|v| v >= 1.0 && v <= cfg.n_dev as f64)
                            })
                        }));
            if sex_possible {
                if let (Ok(pairs), Ok(children)) =
                    (cfg.mc_count.integer(), cfg.mc_germ_count.integer())
                {
                    let offspring = (pairs.max(0) as usize)
                        .checked_mul(children.max(0) as usize)
                        .ok_or("GPU sexual population capacity overflow")?;
                    capacity = capacity.max(offspring);
                }
            }
            let actual = gpu.maximum_batch(capacity, cfg.loci(), batch_size)?;
            Ok((gpu, actual))
        });
        match candidate {
            Ok((gpu, actual)) => Ok(Self {
                gpu: Some(gpu),
                reason: format!(
                    "Vegetative growth runs on the GPU; other phases use CPU helpers{}",
                    if actual < batch_size {
                        format!("; GPU batch reduced to {actual} for device memory")
                    } else {
                        String::new()
                    }
                ),
                batch_size: actual,
            }),
            Err(error) if requested == "auto" => Ok(Self {
                gpu: None,
                reason: format!("CPU fallback: {error}"),
                batch_size,
            }),
            Err(error) => Err(error),
        }
    }
    pub fn name(&self) -> &'static str {
        if self.gpu.is_some() { "gpu" } else { "cpu" }
    }
    pub fn device(&self) -> Option<&str> {
        self.gpu.as_ref().map(GpuGrowth::device_name)
    }
}

pub fn simulate(
    gpu: &mut GpuGrowth,
    cfg: &Config,
    seed: u64,
    threads: usize,
    batch_size: usize,
    ctx: &Context,
    progress: impl Fn(Progress) + Sync,
) -> Result<Vec<RepeatResult>> {
    if threads == 0 || batch_size == 0 {
        return Err("Worker count and GPU batch size must be at least one".into());
    }
    let repeats = cfg.n_runs.max(0) as usize;
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(threads.min(repeats.max(1)))
        .build()
        .map_err(|e| format!("CPU helper pool: {e}"))?;
    let mut results = Vec::new();
    let emit = |repeat, cycle, phase| {
        progress(Progress {
            repeat: repeat + 1,
            cycle,
            total_repeats: cfg.n_runs,
            total_cycles: cfg.n_dev.max(0),
            phase,
        })
    };
    for start in (0..repeats).step_by(batch_size) {
        ctx.check()?;
        let count = batch_size.min(repeats - start);
        let mut rngs: Vec<_> = (start..start + count)
            .map(|r| NativeChoices::new(seed, r, ctx.cancelled.clone()))
            .collect();
        let mut batch: Vec<RepeatResult> = pool
            .install(|| {
                rngs.par_iter_mut()
                    .enumerate()
                    .map(|(i, rng)| {
                        ctx.check()?;
                        emit(start + i, 0, "initialize");
                        let population = engine::initialize(cfg, rng, ctx)?;
                        Ok(RepeatResult {
                            measurements: vec![measure(&population, cfg)?],
                            sex_cycles: Vec::new(),
                            population,
                        })
                    })
                    .collect::<Vec<Result<_>>>()
            })
            .into_iter()
            .collect::<Result<_>>()?;
        for cycle in 1..=cfg.n_dev {
            ctx.check()?;
            let (scheduled, interval) = cfg.scheduled(cycle)?;
            pool.install(|| {
                batch
                    .par_iter_mut()
                    .zip(rngs.par_iter_mut())
                    .enumerate()
                    .map(|(i, (state, rng))| {
                        ctx.check()?;
                        let mut pop =
                            std::mem::replace(&mut state.population, Population::new(cfg.loci()));
                        if scheduled {
                            emit(start + i, cycle, "sex");
                            pop = engine::sex(pop, cfg, rng, ctx)?;
                        }
                        emit(start + i, cycle, "growth");
                        state.population = engine::germinate(pop, cfg, rng, ctx)?;
                        Ok(())
                    })
                    .collect::<Vec<Result<()>>>()
            })
            .into_iter()
            .collect::<Result<Vec<_>>>()?;
            let populations: Vec<_> = batch
                .iter_mut()
                .map(|state| std::mem::replace(&mut state.population, Population::new(cfg.loci())))
                .collect();
            let grown = gpu.grow_batch(&populations, &mut rngs, cfg, ctx)?;
            pool.install(|| {
                batch
                    .par_iter_mut()
                    .zip(rngs.par_iter_mut())
                    .zip(grown.into_par_iter())
                    .enumerate()
                    .map(|(i, ((state, rng), pop))| {
                        ctx.check()?;
                        emit(start + i, cycle, "development");
                        state.population = engine::development(pop, cfg, rng, ctx)?;
                        state.measurements.push(measure(&state.population, cfg)?);
                        if scheduled && interval {
                            state.sex_cycles.push(cycle);
                        }
                        emit(start + i, cycle, "cycle_complete");
                        Ok(())
                    })
                    .collect::<Vec<Result<()>>>()
            })
            .into_iter()
            .collect::<Result<Vec<_>>>()?;
        }
        for mut state in batch {
            state.population = Population::new(cfg.loci());
            results.push(state);
        }
    }
    Ok(results)
}
