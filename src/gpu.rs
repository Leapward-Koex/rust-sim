//! Optional OpenCL vegetative-growth accelerator. The dynamically loaded
//! runtime is discovered only when requested; the CPU engine needs no driver.
//! Germination remains on the CPU and must precede `grow_batch`.
use crate::{
    Result,
    config::Config,
    engine::Context,
    model::{Cell, Population},
    random::NativeChoices,
};
use opencl3::{
    command_queue::CommandQueue,
    context::Context as ClContext,
    device::{CL_DEVICE_TYPE_GPU, Device, get_all_devices},
    kernel::{ExecuteKernel, Kernel},
    memory::{Buffer, CL_MEM_READ_WRITE},
    program::Program,
    types::CL_BLOCKING,
};
use std::ptr;

const SOURCE: &str = include_str!("kernels/growth.cl");
fn cl_error(e: impl std::fmt::Display) -> String {
    format!("OpenCL GPU: {e}")
}

// Match the allocations in Buffers::new, including the 32-byte per-repeat
// ChaCha key (the largest buffer when both stride and loci are tiny).
fn batch_budget(
    stride: usize,
    loci: usize,
    requested: usize,
    memory: u64,
    max_allocation: u64,
) -> Result<usize> {
    if stride == 0 || loci == 0 || requested == 0 {
        return Err("GPU capacity requires positive cells, loci and batch size".into());
    }
    let genes = stride
        .checked_mul(loci)
        .ok_or("GPU gene capacity overflow")?;
    let bytes = genes
        .checked_mul(2)
        .and_then(|x| stride.checked_mul(48).and_then(|y| x.checked_add(y)))
        .and_then(|x| x.checked_add(128))
        .ok_or("GPU memory budget overflow")?;
    let largest = genes
        .max(stride.checked_mul(8).ok_or("GPU buffer size overflow")?)
        .max(32);
    let allowed = (memory / 2 / bytes as u64)
        .min(max_allocation / largest as u64)
        .min(requested as u64) as usize;
    if allowed == 0 {
        return Err(format!(
            "One GPU repeat needs {bytes} bytes with a largest buffer of {largest} bytes, exceeding the safe device memory budget; select the CPU backend or reduce cells/gene_pairs"
        ));
    }
    Ok(allowed)
}

struct Buffers {
    stride: usize,
    batch: usize,
    loci: usize,
    genes: [Buffer<u8>; 2],
    mating: [Buffer<i64>; 2],
    fitness: [Buffer<f64>; 2],
    weights: Buffer<f64>,
    cumulative: Buffer<f64>,
    counts: Buffer<u64>,
    failed: Buffer<u32>,
    keys: Buffer<u32>,
    streams: Buffer<u64>,
    positions: Buffer<u64>,
}
fn buffer<T>(context: &ClContext, count: usize) -> Result<Buffer<T>> {
    // Every allocation has a checked positive length and a device-memory
    // budget check before this function is called.
    unsafe { Buffer::create(context, CL_MEM_READ_WRITE, count, ptr::null_mut()) }.map_err(cl_error)
}
impl Buffers {
    fn new(
        context: &ClContext,
        stride: usize,
        batch: usize,
        loci: usize,
        memory: u64,
        max_allocation: u64,
    ) -> Result<Self> {
        let cells = stride
            .checked_mul(batch)
            .ok_or("GPU cell capacity overflow")?;
        let genes = cells
            .checked_mul(loci)
            .ok_or("GPU gene capacity overflow")?;
        // Two populations, two fitness arrays, weights and prefixes, plus
        // small per-repeat state. Leave at least half the device memory free.
        let allowed = batch_budget(stride, loci, batch, memory, max_allocation)?;
        if allowed < batch {
            return Err(format!(
                "GPU batch of {batch} exceeds the safe device memory budget; reduce the GPU batch size to {allowed}"
            ));
        }
        Ok(Self {
            stride,
            batch,
            loci,
            genes: [buffer(context, genes)?, buffer(context, genes)?],
            mating: [buffer(context, cells)?, buffer(context, cells)?],
            fitness: [buffer(context, cells)?, buffer(context, cells)?],
            weights: buffer(context, cells)?,
            cumulative: buffer(context, cells)?,
            counts: buffer(context, batch)?,
            failed: buffer(context, batch)?,
            keys: buffer(context, batch * 8)?,
            streams: buffer(context, batch)?,
            positions: buffer(context, batch)?,
        })
    }
}

pub struct GpuGrowth {
    context: ClContext,
    queue: CommandQueue,
    _program: Program,
    fitness: Kernel,
    prefix: Kernel,
    offspring: Kernel,
    name: String,
    memory: u64,
    max_allocation: u64,
    buffers: Option<Buffers>,
}

/// Configurations outside this fast path continue to use the existing CPU
/// implementation. No probabilities or costs are clamped or normalized.
pub fn supported(cfg: &Config) -> Result<()> {
    if cfg.n.integer()? <= 0 || cfg.gene_pairs <= 0 || cfg.vg.integer()? <= 0 {
        return Err("GPU growth requires positive integer n, gene_pairs and vg".into());
    }
    if cfg.gene_pairs > u32::MAX as i64 {
        return Err("GPU growth gene_pairs exceeds the supported counting range".into());
    }
    for (name, value) in [
        ("c_ch", cfg.c_ch.number()?),
        ("c_res", cfg.c_res.number()?),
        ("m_ch", cfg.m_ch.number()?),
        ("m_re", cfg.m_re.number()?),
    ] {
        if !value.is_finite() {
            return Err(format!("GPU growth requires finite {name}"));
        }
    }
    Ok(())
}

impl GpuGrowth {
    pub fn supported(cfg: &Config) -> Result<()> {
        supported(cfg)
    }

    pub fn new() -> Result<Self> {
        let mut candidates: Vec<_> = get_all_devices(CL_DEVICE_TYPE_GPU)
            .map_err(cl_error)?
            .into_iter()
            .map(Device::new)
            .filter(|d| d.double_fp_config().unwrap_or(0) != 0 && d.available().unwrap_or(false))
            .collect();
        candidates.sort_by_key(|d| {
            std::cmp::Reverse((
                d.global_mem_size().unwrap_or(0),
                d.max_compute_units().unwrap_or(0),
            ))
        });
        let mut failures = Vec::new();
        for device in candidates {
            match Self::on_device(&device) {
                Ok(gpu) => return Ok(gpu),
                Err(e) => failures.push(e),
            }
        }
        if failures.is_empty() {
            Err("No available OpenCL GPU with binary64 (FP64) arithmetic was found".into())
        } else {
            Err(failures.join("; "))
        }
    }
    fn on_device(device: &Device) -> Result<Self> {
        let context = ClContext::from_device(device).map_err(cl_error)?;
        #[allow(deprecated)]
        let queue = CommandQueue::create_default(&context, 0).map_err(cl_error)?;
        let program = Program::create_and_build_from_source(&context, SOURCE, "-cl-std=CL1.2")
            .map_err(cl_error)?;
        Ok(Self {
            fitness: Kernel::create(&program, "fitness").map_err(cl_error)?,
            prefix: Kernel::create(&program, "prefix").map_err(cl_error)?,
            offspring: Kernel::create(&program, "offspring").map_err(cl_error)?,
            context,
            queue,
            _program: program,
            name: device.name().map_err(cl_error)?,
            memory: device.global_mem_size().map_err(cl_error)?,
            max_allocation: device.max_mem_alloc_size().map_err(cl_error)?,
            buffers: None,
        })
    }
    pub fn device_name(&self) -> &str {
        &self.name
    }

    /// Cap a requested batch using a conservative upper bound on cells per
    /// repeat. Callers account for any population expansion during sex.
    pub fn maximum_batch(&self, cells: usize, loci: usize, requested: usize) -> Result<usize> {
        if cells == 0 {
            return Err("GPU capacity requires positive cells".into());
        }
        let stride = cells
            .checked_next_power_of_two()
            .ok_or("GPU capacity overflow")?;
        batch_budget(stride, loci, requested, self.memory, self.max_allocation)
    }

    pub fn grow_batch(
        &mut self,
        pops: &[Population],
        rngs: &mut [NativeChoices],
        cfg: &Config,
        ctx: &Context,
    ) -> Result<Vec<Population>> {
        ctx.check()?;
        supported(cfg)?;
        if pops.len() != rngs.len() {
            return Err("GPU population/random-stream batch lengths differ".into());
        }
        if pops.is_empty() {
            return Ok(Vec::new());
        }
        if pops.iter().any(Population::is_empty) {
            return Err("Cannot select parents from an empty population".into());
        }
        let n = cfg.n.integer()? as usize;
        let generations = cfg.vg.integer()? as u64;
        let loci = cfg.loci();
        let mut stride = n;
        for pop in pops {
            if pop.loci != loci
                || pop.genes.len()
                    != pop
                        .len()
                        .checked_mul(loci)
                        .ok_or("GPU input size overflow")?
            {
                return Err("GPU population genotype shape differs from configuration".into());
            }
            stride = stride.max(pop.len());
        }
        let words = (n as u64)
            .checked_mul(2)
            .and_then(|x| {
                (n as u64)
                    .checked_mul(loci as u64)
                    .and_then(|g| g.checked_mul(4))
                    .and_then(|g| x.checked_add(g))
            })
            .ok_or("GPU random-stream generation size overflow")?;
        let consumed = words
            .checked_mul(generations)
            .ok_or("GPU random-stream advance overflow")?;
        let states: Vec<_> = rngs
            .iter()
            .map(NativeChoices::py_stream)
            .collect::<Result<_>>()?;
        for state in &states {
            state
                .word_pos
                .checked_add(consumed)
                .ok_or("GPU random-stream position overflow")?;
        }
        if self
            .buffers
            .as_ref()
            .is_none_or(|b| b.stride < stride || b.batch < pops.len() || b.loci != loci)
        {
            stride = stride
                .checked_next_power_of_two()
                .ok_or("GPU capacity overflow")?;
            // Release an obsolete allocation before reserving the new one.
            self.buffers = None;
            self.buffers = Some(Buffers::new(
                &self.context,
                stride,
                pops.len(),
                loci,
                self.memory,
                self.max_allocation,
            )?);
        }
        let b = self.buffers.as_mut().unwrap();
        stride = b.stride;
        let cells = stride
            .checked_mul(pops.len())
            .ok_or("GPU batch size overflow")?;
        let mut genes = vec![0u8; cells * loci];
        let mut mating = vec![0i64; cells];
        let mut fitness = vec![0f64; cells];
        let mut counts = Vec::with_capacity(pops.len());
        for (repeat, pop) in pops.iter().enumerate() {
            let start = repeat * stride;
            genes[start * loci..start * loci + pop.genes.len()].copy_from_slice(&pop.genes);
            for (i, cell) in pop.cells.iter().enumerate() {
                mating[start + i] = cell.mating_type;
            }
            counts.push(pop.len() as u64);
        }
        let keys: Vec<_> = states.iter().flat_map(|s| s.key).collect();
        let streams: Vec<_> = states.iter().map(|s| s.stream).collect();
        let positions: Vec<_> = states.iter().map(|s| s.word_pos).collect();
        let mut failed = vec![0u32; pops.len()];
        // All transfer slices stay alive until their blocking copy completes.
        unsafe {
            self.queue
                .enqueue_write_buffer(&mut b.genes[0], CL_BLOCKING, 0, &genes, &[])
                .map_err(cl_error)?;
            self.queue
                .enqueue_write_buffer(&mut b.mating[0], CL_BLOCKING, 0, &mating, &[])
                .map_err(cl_error)?;
            self.queue
                .enqueue_write_buffer(&mut b.counts, CL_BLOCKING, 0, &counts, &[])
                .map_err(cl_error)?;
            self.queue
                .enqueue_write_buffer(&mut b.failed, CL_BLOCKING, 0, &failed, &[])
                .map_err(cl_error)?;
            self.queue
                .enqueue_write_buffer(&mut b.keys, CL_BLOCKING, 0, &keys, &[])
                .map_err(cl_error)?;
            self.queue
                .enqueue_write_buffer(&mut b.streams, CL_BLOCKING, 0, &streams, &[])
                .map_err(cl_error)?;
            self.queue
                .enqueue_write_buffer(&mut b.positions, CL_BLOCKING, 0, &positions, &[])
                .map_err(cl_error)?;
        }
        let (stride_arg, loci_arg, n_arg) = (stride as u64, loci as u64, n as u64);
        let (c_ch, c_res, m_ch, m_re) = (
            cfg.c_ch.number()?,
            cfg.c_res.number()?,
            cfg.m_ch.number()?,
            cfg.m_re.number()?,
        );
        let mut current = 0;
        for generation in 0..generations {
            ctx.check()?;
            let next = 1 - current;
            let first = u32::from(generation == 0);
            let offset = generation * words;
            // Queue is in order: the next population is not consumed until
            // all writes from the previous generation have completed.
            unsafe {
                ExecuteKernel::new(&self.fitness)
                    .set_arg(&b.genes[current])
                    .set_arg(&b.weights)
                    .set_arg(&b.counts)
                    .set_arg(&b.failed)
                    .set_arg(&stride_arg)
                    .set_arg(&loci_arg)
                    .set_arg(&n_arg)
                    .set_arg(&first)
                    .set_arg(&c_ch)
                    .set_arg(&c_res)
                    .set_global_work_size(cells)
                    .enqueue_nd_range(&self.queue)
                    .map_err(cl_error)?;
                ExecuteKernel::new(&self.prefix)
                    .set_arg(&b.weights)
                    .set_arg(&b.cumulative)
                    .set_arg(&b.counts)
                    .set_arg(&b.failed)
                    .set_arg(&stride_arg)
                    .set_arg(&n_arg)
                    .set_arg(&first)
                    .set_global_work_size(pops.len())
                    .enqueue_nd_range(&self.queue)
                    .map_err(cl_error)?;
                ExecuteKernel::new(&self.offspring)
                    .set_arg(&b.genes[current])
                    .set_arg(&b.mating[current])
                    .set_arg(&b.weights)
                    .set_arg(&b.cumulative)
                    .set_arg(&b.genes[next])
                    .set_arg(&b.mating[next])
                    .set_arg(&b.fitness[next])
                    .set_arg(&b.counts)
                    .set_arg(&b.failed)
                    .set_arg(&b.keys)
                    .set_arg(&b.streams)
                    .set_arg(&b.positions)
                    .set_arg(&stride_arg)
                    .set_arg(&loci_arg)
                    .set_arg(&n_arg)
                    .set_arg(&first)
                    .set_arg(&offset)
                    .set_arg(&m_ch)
                    .set_arg(&m_re)
                    .set_global_work_size(n * pops.len())
                    .enqueue_nd_range(&self.queue)
                    .map_err(cl_error)?;
            }
            // Bound the in-flight work so cancellation never sits behind the
            // entire vegetative phase. Kernels themselves are per generation.
            self.queue.finish().map_err(cl_error)?;
            // Catch invalid initial weights immediately and errors arising
            // later within at most eight generations, independent of vg.
            if generation == 0 || (generation + 1) % 8 == 0 || generation + 1 == generations {
                unsafe {
                    self.queue
                        .enqueue_read_buffer(&b.failed, CL_BLOCKING, 0, &mut failed, &[])
                        .map_err(cl_error)?;
                }
                if failed.iter().any(|&x| x != 0) {
                    return Err(
                        "Total selection weight must be finite and greater than zero".into(),
                    );
                }
            }
            current = next;
        }
        ctx.check()?;
        unsafe {
            self.queue
                .enqueue_read_buffer(&b.genes[current], CL_BLOCKING, 0, &mut genes, &[])
                .map_err(cl_error)?;
            self.queue
                .enqueue_read_buffer(&b.mating[current], CL_BLOCKING, 0, &mut mating, &[])
                .map_err(cl_error)?;
            self.queue
                .enqueue_read_buffer(&b.fitness[current], CL_BLOCKING, 0, &mut fitness, &[])
                .map_err(cl_error)?;
        }
        let mut result = Vec::with_capacity(pops.len());
        for (repeat, rng) in rngs.iter_mut().enumerate() {
            ctx.check()?;
            let start = repeat * stride;
            let mut pop = Population::new(loci);
            pop.reserve(n)?;
            pop.genes
                .extend_from_slice(&genes[start * loci..(start + n) * loci]);
            pop.cells.extend((start..start + n).map(|i| Cell {
                mating_type: mating[i],
                fitness: fitness[i],
            }));
            result.push(pop);
            rng.advance_py_words(consumed)?;
        }
        Ok(result)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{engine, json::Json, random::Choices};

    #[test]
    fn gpu_budget_caps_total_memory_and_each_allocation() {
        // One stride=16/loci=3 repeat uses 992 bytes; largest allocation=128.
        assert_eq!(batch_budget(16, 3, 100, 992 * 2 * 7, 128 * 10).unwrap(), 7);
        assert_eq!(batch_budget(16, 3, 100, 992 * 2 * 10, 128 * 3).unwrap(), 3);
        assert_eq!(batch_budget(16, 3, 2, 992 * 2 * 10, 128 * 10).unwrap(), 2);
        assert!(batch_budget(16, 3, 1, 992 * 2 - 1, 128).is_err());
        assert!(batch_budget(16, 3, 1, 992 * 2, 127).is_err());
        // Tiny populations must still respect the 32-byte ChaCha-key buffer.
        assert_eq!(batch_budget(1, 1, 9, 10_000, 64).unwrap(), 2);
        assert!(batch_budget(1, 1, 1, 10_000, 31).is_err());
        assert!(batch_budget(usize::MAX, 2, 1, u64::MAX, u64::MAX).is_err());
        assert!(batch_budget(0, 1, 1, 10_000, 10_000).is_err());
        assert!(batch_budget(1, 0, 1, 10_000, 10_000).is_err());
        assert!(batch_budget(1, 1, 0, 10_000, 10_000).is_err());
    }

    fn config(n: usize, loci: usize, generations: usize, c: f64, r: f64) -> Config {
        Config::parse(&format!(r#"{{"n_runs":1,"n_dev":1,"gene_pairs":{loci},"n":{n},"vg":{generations},"c_ch":{c},"c_res":{r},"m_ch":0.17,"m_re":0.09,"ch_germ":0,"ch_eff_rc":1}}"#)).unwrap()
    }
    fn population(count: usize, loci: usize) -> Population {
        let mut pop = Population::new(loci);
        for i in 0..count {
            let genes: Vec<_> = (0..loci).map(|j| ((i * 7 + j * 3) % 4) as u8).collect();
            pop.push(
                Cell {
                    mating_type: (i % 3 + 1) as i64,
                    fitness: -0.25,
                },
                &genes,
            );
        }
        pop
    }

    #[test]
    #[ignore = "requires an OpenCL GPU with FP64"]
    fn gpu_rng_matches_chacha_at_odd_offsets() {
        let gpu = GpuGrowth::new().unwrap();
        let kernel = Kernel::create(&gpu._program, "rng_probe").unwrap();
        for offset in [0, 1, 15, 16, 31, 63, 64, 129, 16_777_215] {
            let mut rng = NativeChoices::new(42, 31, Default::default());
            rng.advance_py_words(offset).unwrap();
            let state = rng.py_stream().unwrap();
            let mut keys = buffer(&gpu.context, 8).unwrap();
            let mut streams = buffer(&gpu.context, 1).unwrap();
            let mut positions = buffer(&gpu.context, 1).unwrap();
            let output: Buffer<f64> = buffer(&gpu.context, 257).unwrap();
            let mut actual = vec![0.0; 257];
            unsafe {
                gpu.queue
                    .enqueue_write_buffer(&mut keys, CL_BLOCKING, 0, &state.key, &[])
                    .unwrap();
                gpu.queue
                    .enqueue_write_buffer(&mut streams, CL_BLOCKING, 0, &[state.stream], &[])
                    .unwrap();
                gpu.queue
                    .enqueue_write_buffer(&mut positions, CL_BLOCKING, 0, &[state.word_pos], &[])
                    .unwrap();
                ExecuteKernel::new(&kernel)
                    .set_arg(&keys)
                    .set_arg(&streams)
                    .set_arg(&positions)
                    .set_arg(&output)
                    .set_global_work_size(actual.len())
                    .enqueue_nd_range(&gpu.queue)
                    .unwrap();
                gpu.queue
                    .enqueue_read_buffer(&output, CL_BLOCKING, 0, &mut actual, &[])
                    .unwrap();
            }
            for (i, value) in actual.iter().enumerate() {
                assert_eq!(
                    *value,
                    rng.uniform().unwrap(),
                    "offset {offset}, uniform {i}"
                );
            }
        }
    }

    #[test]
    #[ignore = "requires an OpenCL GPU with FP64"]
    fn gpu_growth_matches_cpu_and_following_random_stream() {
        let mut gpu = GpuGrowth::new().unwrap();
        eprintln!("Testing exact growth parity on {}", gpu.device_name());
        let ctx = Context::default();
        for (n, loci, generations, batch, cost_c, cost_r) in [
            (1, 1, 1, 1, 0.01, 0.02),
            (37, 3, 4, 5, 0.01, 0.02),
            (257, 7, 3, 9, 0.11, 0.001),
            (71, 2, 3, 2, 0.7, 0.1),
            // C carriers have fitness -0.5 but the population total is
            // positive: preserve Python's non-monotone prefix/bisect behavior.
            (257, 1, 3, 3, 2.0, 0.0),
            (13, 67, 2, 3, 0.0001, 0.0002),
            (10_000, 3, 10, 16, 0.001, 0.001),
        ] {
            let cfg = config(n, loci, generations, cost_c, cost_r);
            let mut pops = Vec::new();
            let mut actual_rng = Vec::new();
            let mut expected_rng = Vec::new();
            let mut expected = Vec::new();
            for repeat in 0..batch {
                let pop = population(
                    if repeat % 2 == 0 {
                        n + 17
                    } else {
                        n.max(2) - 1
                    },
                    loci,
                );
                let mut cpu = NativeChoices::new(564, repeat, Default::default());
                let mut device = NativeChoices::new(564, repeat, Default::default());
                // Exercise non-block-aligned RNG state on every call.
                cpu.advance_py_words(repeat as u64 + 1).unwrap();
                device.advance_py_words(repeat as u64 + 1).unwrap();
                expected.push(engine::growth(pop.clone(), &cfg, &mut cpu, &ctx).unwrap());
                // ch_germ=0 still consumes one uniform for each C carrier.
                for i in 0..pop.len() {
                    if crate::model::counts(pop.genome(i)).0 > 0 {
                        device.uniform().unwrap();
                    }
                }
                pops.push(pop);
                actual_rng.push(device);
                expected_rng.push(cpu);
            }
            let actual = gpu.grow_batch(&pops, &mut actual_rng, &cfg, &ctx).unwrap();
            for repeat in 0..batch {
                assert_eq!(
                    actual[repeat].genes, expected[repeat].genes,
                    "n={n}, loci={loci}, repeat={repeat}"
                );
                for (a, b) in actual[repeat].cells.iter().zip(&expected[repeat].cells) {
                    assert_eq!(a.mating_type, b.mating_type);
                    assert_eq!(
                        a.fitness.to_bits(),
                        b.fitness.to_bits(),
                        "fitness n={n}, loci={loci}"
                    );
                }
                for _ in 0..20 {
                    assert_eq!(
                        actual_rng[repeat].uniform().unwrap(),
                        expected_rng[repeat].uniform().unwrap()
                    );
                    assert_eq!(
                        actual_rng[repeat].integer(177).unwrap(),
                        expected_rng[repeat].integer(177).unwrap()
                    );
                }
            }
        }
    }

    #[test]
    #[ignore = "requires an OpenCL GPU with FP64"]
    fn gpu_rejects_invalid_weights_without_advancing_rng() {
        let mut gpu = GpuGrowth::new().unwrap();
        let ctx = Context::default();
        let cfg = config(32, 3, 2, 5.0, 5.0);
        let pop = population(32, 3);
        let mut rng = vec![NativeChoices::new(99, 0, Default::default())];
        let before = rng[0].py_stream().unwrap().word_pos;
        assert!(
            gpu.grow_batch(&[pop], &mut rng, &cfg, &ctx)
                .unwrap_err()
                .contains("Total selection weight")
        );
        assert_eq!(rng[0].py_stream().unwrap().word_pos, before);
        let mut raw = cfg.raw.clone();
        raw.insert("m_ch", Json::number(f64::NAN));
        assert!(supported(&Config::from_json(raw).unwrap()).is_err());
    }

    #[test]
    #[ignore = "manual GPU growth benchmark; requires an OpenCL GPU with FP64"]
    fn gpu_growth_benchmark() {
        use rayon::prelude::*;
        use std::time::Instant;
        let mut gpu = GpuGrowth::new().unwrap();
        let ctx = Context::default();
        let cfg = config(10_000, 3, 10, 0.001, 0.001);
        let pool = rayon::ThreadPoolBuilder::new()
            .num_threads(8)
            .build()
            .unwrap();
        for batch in [32, 128, 256] {
            let mut pops = Vec::new();
            let mut rngs = Vec::new();
            for repeat in 0..batch {
                pops.push(population(10_000, 3));
                rngs.push(NativeChoices::new(42, repeat, Default::default()));
            }
            let started = Instant::now();
            let cpu: Vec<_> = pool.install(|| {
                pops.par_iter()
                    .enumerate()
                    .map(|(repeat, pop)| {
                        let mut rng = NativeChoices::new(42, repeat, Default::default());
                        engine::growth(pop.clone(), &cfg, &mut rng, &ctx).unwrap()
                    })
                    .collect()
            });
            let cpu_secs = started.elapsed().as_secs_f64();
            for (pop, rng) in pops.iter().zip(&mut rngs) {
                for i in 0..pop.len() {
                    if crate::model::counts(pop.genome(i)).0 > 0 {
                        rng.uniform().unwrap();
                    }
                }
            }
            let started = Instant::now();
            let actual = gpu.grow_batch(&pops, &mut rngs, &cfg, &ctx).unwrap();
            let first_secs = started.elapsed().as_secs_f64();
            for (a, b) in actual.iter().zip(&cpu) {
                assert_eq!(a.genes, b.genes);
            }
            let started = Instant::now();
            gpu.grow_batch(&pops, &mut rngs, &cfg, &ctx).unwrap();
            let warm_secs = started.elapsed().as_secs_f64();
            eprintln!(
                "batch={batch} CPU8={cpu_secs:.6}s GPUfirst={first_secs:.6}s GPUwarm={warm_secs:.6}s speedup={:.2}x",
                cpu_secs / warm_secs
            );
        }
    }
}
