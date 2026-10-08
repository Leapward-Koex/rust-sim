use crate::{
    CANCELLED, Result,
    config::{Config, trunc_count},
    model::{
        Cell, Measurement, Population, ch_effectiveness, counts, effectiveness, exploitable,
        measure,
    },
    random::{Choices, NativeChoices},
};
use rayon::prelude::*;
use std::sync::{
    Arc,
    atomic::{AtomicBool, Ordering},
};

pub struct Context {
    pub cancelled: Arc<AtomicBool>,
}
impl Default for Context {
    fn default() -> Self {
        Self {
            cancelled: Arc::default(),
        }
    }
}
impl Context {
    #[inline]
    pub fn check(&self) -> Result<()> {
        if self.cancelled.load(Ordering::Relaxed) {
            Err(CANCELLED.into())
        } else {
            Ok(())
        }
    }
}
pub fn initialize<R: Choices>(cfg: &Config, rng: &mut R, ctx: &Context) -> Result<Population> {
    let configured_n = cfg.n.number()?;
    let n = trunc_count(configured_n, "n")?.max(0) as usize;
    let mut pop = Population::new(cfg.loci());
    pop.reserve(n)?;
    let blank = vec![0; cfg.loci()];
    for i in 0..n {
        if i % 256 == 0 {
            ctx.check()?;
        }
        let mt = rng.weighted(
            &[
                cfg.mt[0].number()?,
                cfg.mt[1].number()?,
                cfg.mt[2].number()?,
            ],
            1,
        )?[0]
            + 1;
        pop.push(
            Cell {
                mating_type: mt as i64,
                fitness: 1.0,
            },
            &blank,
        );
    }
    let (cheater, resistor) = if cfg.ch_res_dist.equals(1.0)? {
        let ni = cfg.n.integer()?.max(0) as usize;
        let c = trunc_count(
            (cfg.ch_start.number()? * configured_n).round_ties_even(),
            "initial cheater sample",
        )?;
        let r = trunc_count(
            (cfg.res_start.number()? * configured_n).round_ties_even(),
            "initial resistor sample",
        )?;
        (rng.sample(ni, c)?, rng.sample(ni, r)?)
    } else {
        let end = trunc_count(
            cfg.ch_start.number()? * configured_n,
            "initial cheater count",
        )?;
        let cheater: Vec<_> = (0..end).map(|i| i as usize).collect();
        let last = if end > 0 { end - 1 } else { 0 };
        let rend = trunc_count(
            last as f64 + cfg.res_start.number()? * configured_n,
            "initial resistor count",
        )?;
        (cheater, (last..rend).map(|i| i as usize).collect())
    };
    for (indexes, bit) in [(&cheater, 1), (&resistor, 2)] {
        for &i in indexes {
            if i >= pop.len() {
                return Err("Initial allele assignment index outside population".into());
            }
            for gene in &mut pop.genes[i * pop.loci..(i + 1) * pop.loci] {
                *gene |= bit;
            }
        }
    }
    // Initial measurement's unused local reads still require these keys, but
    // their values need not be numeric until an allele carrier uses them.
    if !pop.is_empty() {
        cfg.ch_eff_rc.value()?;
        cfg.res_eff_rc.value()?;
    }
    Ok(pop)
}

pub fn germinate<R: Choices>(
    mut pop: Population,
    cfg: &Config,
    rng: &mut R,
    ctx: &Context,
) -> Result<Population> {
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
    Ok(pop)
}

pub fn growth<R: Choices>(
    pop: Population,
    cfg: &Config,
    rng: &mut R,
    ctx: &Context,
) -> Result<Population> {
    let mut pop = germinate(pop, cfg, rng, ctx)?;
    let mut next = Population::new(pop.loci);
    let mut weights = Vec::new();
    for _ in 0..cfg.vg.integer()? {
        ctx.check()?;
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
        let k = cfg.n.integer()?;
        let selected = rng.weighted(&weights, k)?;
        next.cells.clear();
        next.genes.clear();
        next.reserve(selected.len())?;
        for (i, &parent) in selected.iter().enumerate() {
            if i % 256 == 0 {
                ctx.check()?;
            }
            next.copy_cell(&pop, parent);
        }
        // Every clone exists before the first mutation. Fitness remains the
        // pre-mutation parental value until the next generation's assignment.
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
        std::mem::swap(&mut pop, &mut next);
    }
    Ok(pop)
}

pub fn development<R: Choices>(
    mut pop: Population,
    cfg: &Config,
    rng: &mut R,
    ctx: &Context,
) -> Result<Population> {
    let sl = cfg.sl.number()?;
    if sl == 0.0 {
        return Err("Development divides by zero slug size".into());
    }
    let slugs = trunc_count((cfg.n.number()? / sl).floor(), "slug count")?;
    let mut fruit = Population::new(pop.loci);
    fruit.reserve(pop.len())?;
    let mut slug = Population::new(pop.loci);
    for _ in 0..slugs {
        ctx.check()?;
        let selected = rng.sample(pop.len(), cfg.sl.integer()?)?;
        slug.cells.clear();
        slug.genes.clear();
        slug.reserve(selected.len())?;
        let mut keep = vec![true; pop.len()];
        for &i in &selected {
            slug.copy_cell(&pop, i);
            keep[i] = false;
        }
        pop.retain_mask(&keep);
        if !cfg.resistance_type.equals(1.0)? {
            continue;
        }
        let mut stalk = Vec::new();
        if cfg.discrete_res.equals(1.0)? {
            let mut pre = Vec::new();
            let mut pre_mask = vec![false; slug.len()];
            for (i, yes) in pre_mask.iter_mut().enumerate() {
                if i % 256 == 0 {
                    ctx.check()?;
                }
                if rng.uniform()? < 1.0 - cfg.sp.number()? {
                    pre.push(i);
                    *yes = true;
                }
            }
            let mut stalk_mask = vec![false; slug.len()];
            let mut candidates = Vec::new();
            for i in pre {
                ctx.check()?;
                let target = if counts(slug.genome(i)).0 > 0 {
                    candidates.clear();
                    // U XOR set(stalk) XOR set(pre), in deliberately stable
                    // ascending index order. Duplicate stalk entries stay in
                    // the deletion list, but have set membership here.
                    for j in 0..slug.len() {
                        if (true ^ stalk_mask[j]) ^ pre_mask[j] {
                            candidates.push(j);
                        }
                    }
                    let j = candidates[rng.integer(candidates.len())?];
                    if exploitable(slug.genome(i), slug.genome(j), cfg)? {
                        j
                    } else {
                        i
                    }
                } else {
                    i
                };
                stalk.push(target);
                stalk_mask[target] = true;
            }
        }
        slug.delete_positions(&mut stalk)?;
        fruit.append(&slug);
    }
    Ok(fruit)
}

pub fn sex<R: Choices>(
    pop: Population,
    cfg: &Config,
    rng: &mut R,
    ctx: &Context,
) -> Result<Population> {
    let founders = rng.sample(pop.len(), cfg.mc_count.integer()?)?;
    let mut available = vec![true; pop.len()];
    for &i in &founders {
        available[i] = false;
    }
    let mut offspring = Population::new(pop.loci);
    let mut partners = Vec::new();
    for founder in founders {
        ctx.check()?;
        partners.clear();
        for (i, yes) in available.iter().enumerate() {
            if i % 1024 == 0 {
                ctx.check()?;
            }
            if *yes && pop.cells[i].mating_type != pop.cells[founder].mating_type {
                partners.push(i);
            }
        }
        let partner = partners[rng.sample(partners.len(), 1)?[0]];
        available[partner] = false;
        let a = pop.genome(founder);
        let b = pop.genome(partner);
        let (genome, mt) = if pop.loci == 0 {
            // All reachable nonempty genomes own distinct locus objects;
            // only the empty-list equality branch remains reachable here.
            (
                Vec::new(),
                if rng.integer(2)? == 1 {
                    pop.cells[founder].mating_type
                } else {
                    pop.cells[partner].mating_type
                },
            )
        } else if rng.uniform()? < 1.0 - cfg.recomb_chance.number()? {
            let parent = if rng.integer(2)? == 1 {
                founder
            } else {
                partner
            };
            (pop.genome(parent).to_vec(), pop.cells[parent].mating_type)
        } else {
            let mut genes = Vec::with_capacity(pop.loci);
            for (j, (&av, &bv)) in a.iter().zip(b).enumerate() {
                if j % 1024 == 0 {
                    ctx.check()?;
                }
                let c = if rng.integer(2)? == 1 { av & 1 } else { bv & 1 };
                let r = if rng.integer(2)? == 1 { av & 2 } else { bv & 2 };
                genes.push(c | r);
            }
            (
                genes,
                if rng.integer(2)? == 1 {
                    pop.cells[founder].mating_type
                } else {
                    pop.cells[partner].mating_type
                },
            )
        };
        let (ce, re) = effectiveness(&genome, cfg)?;
        let cell = Cell {
            mating_type: mt,
            fitness: ((1.0 - cfg.c_ch.number()? * ce) + (1.0 - cfg.c_res.number()? * re)) / 2.0,
        };
        let germ_count = cfg.mc_germ_count.integer()?;
        offspring.reserve(germ_count.max(0) as usize)?;
        for i in 0..germ_count {
            if i % 256 == 0 {
                ctx.check()?;
            }
            offspring.push(cell, &genome);
        }
    }
    Ok(offspring)
}

#[derive(Clone, Debug)]
pub struct RepeatResult {
    pub measurements: Vec<Measurement>,
    pub sex_cycles: Vec<i64>,
    pub population: Population,
}
#[derive(Clone, serde::Serialize)]
pub struct Progress {
    pub repeat: usize,
    pub cycle: i64,
    pub total_repeats: i64,
    pub total_cycles: i64,
    pub phase: &'static str,
}
pub fn simulate_repeat<R: Choices>(
    cfg: &Config,
    rng: &mut R,
    ctx: &Context,
    repeat: usize,
    progress: &impl Fn(Progress),
) -> Result<RepeatResult> {
    let emit = |cycle, phase| {
        progress(Progress {
            repeat: repeat + 1,
            cycle,
            total_repeats: cfg.n_runs,
            total_cycles: cfg.n_dev.max(0),
            phase,
        })
    };
    ctx.check()?;
    emit(0, "initialize");
    let mut pop = initialize(cfg, rng, ctx)?;
    let mut measurements = vec![measure(&pop, cfg)?];
    let mut sex_cycles = Vec::new();
    for cycle in 1..=cfg.n_dev {
        ctx.check()?;
        let (scheduled, interval) = cfg.scheduled(cycle)?;
        if scheduled {
            emit(cycle, "sex");
            pop = sex(pop, cfg, rng, ctx)?;
        }
        emit(cycle, "growth");
        pop = growth(pop, cfg, rng, ctx)?;
        emit(cycle, "development");
        pop = development(pop, cfg, rng, ctx)?;
        measurements.push(measure(&pop, cfg)?);
        if scheduled && interval {
            sex_cycles.push(cycle);
        }
        emit(cycle, "cycle_complete");
    }
    Ok(RepeatResult {
        measurements,
        sex_cycles,
        population: pop,
    })
}

pub fn simulate(
    cfg: &Config,
    seed: u64,
    threads: usize,
    ctx: &Context,
    progress: impl Fn(Progress) + Sync,
) -> Result<Vec<RepeatResult>> {
    let repeats = cfg.n_runs.max(0) as usize;
    if threads == 0 {
        return Err("Worker count must be at least one".into());
    }
    let run = |repeat| {
        let mut rng = NativeChoices::new(seed, repeat, ctx.cancelled.clone());
        let mut result = simulate_repeat(cfg, &mut rng, ctx, repeat, &progress)?;
        // CLI aggregation needs histories only. Fixture operations retain cells.
        result.population = Population::new(cfg.loci());
        Ok(result)
    };
    // Explicit serial branch is the reference implementation and avoids any
    // scheduling dependency in seeded repeat construction or result reduction.
    if threads == 1 {
        return (0..repeats).map(run).collect();
    }
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(threads.min(repeats.max(1)))
        .build()
        .map_err(|e| format!("Worker pool: {e}"))?;
    pool.install(|| {
        (0..repeats)
            .into_par_iter()
            .map(run)
            .collect::<Vec<Result<RepeatResult>>>()
    })
    .into_iter()
    .collect()
}
