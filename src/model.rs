use crate::{Result, config::Config, json::Json};

#[derive(Clone, Copy, Debug)]
pub struct Cell {
    pub mating_type: i64,
    pub fitness: f64,
}
#[derive(Clone, Debug)]
pub struct Population {
    pub cells: Vec<Cell>,
    pub genes: Vec<u8>,
    pub loci: usize,
}
impl Population {
    pub fn new(loci: usize) -> Self {
        Self {
            cells: Vec::new(),
            genes: Vec::new(),
            loci,
        }
    }
    pub fn len(&self) -> usize {
        self.cells.len()
    }
    pub fn is_empty(&self) -> bool {
        self.cells.is_empty()
    }
    pub fn reserve(&mut self, n: usize) -> Result<()> {
        let n_genes = n.checked_mul(self.loci).ok_or("Population size overflow")?;
        self.cells
            .try_reserve(n)
            .map_err(|e| format!("Population allocation failed: {e}"))?;
        self.genes
            .try_reserve(n_genes)
            .map_err(|e| format!("Genotype allocation failed: {e}"))?;
        Ok(())
    }
    pub fn genome(&self, index: usize) -> &[u8] {
        &self.genes[index * self.loci..(index + 1) * self.loci]
    }
    pub fn push(&mut self, cell: Cell, genome: &[u8]) {
        self.cells.push(cell);
        self.genes.extend_from_slice(genome);
    }
    pub fn copy_cell(&mut self, source: &Self, index: usize) {
        self.push(source.cells[index], source.genome(index));
    }
    pub fn retain_mask(&mut self, keep: &[bool]) {
        let mut dst = 0;
        for (src, yes) in keep.iter().enumerate() {
            if *yes {
                self.cells[dst] = self.cells[src];
                self.genes
                    .copy_within(src * self.loci..(src + 1) * self.loci, dst * self.loci);
                dst += 1;
            }
        }
        self.cells.truncate(dst);
        self.genes.truncate(dst * self.loci);
    }
    // Descending deletions MUST NOT be deduplicated: source repeatedly deletes
    // positions in a shrinking list, not original identities (DEV-006).
    pub fn delete_positions(&mut self, positions: &mut [usize]) -> Result<()> {
        positions.sort_unstable_by(|a, b| b.cmp(a));
        for &index in positions.iter() {
            if index >= self.len() {
                return Err("Stalk deletion index outside shrinking slug".into());
            }
            self.cells.remove(index);
            self.genes.drain(index * self.loci..(index + 1) * self.loci);
        }
        Ok(())
    }
    pub fn append(&mut self, other: &Self) {
        self.cells.extend_from_slice(&other.cells);
        self.genes.extend_from_slice(&other.genes);
    }
    pub fn to_json(&self) -> Json {
        Json::Array(
            (0..self.len())
                .map(|i| {
                    let mut cell = Json::object();
                    cell.insert(
                        "loci",
                        Json::Array(
                            self.genome(i)
                                .iter()
                                .map(|v| {
                                    Json::Array(vec![
                                        Json::integer((v & 1) as i64),
                                        Json::integer(((v >> 1) & 1) as i64),
                                    ])
                                })
                                .collect(),
                        ),
                    );
                    cell.insert("mating_type", Json::integer(self.cells[i].mating_type));
                    cell.insert("fitness", Json::number(self.cells[i].fitness));
                    cell
                })
                .collect(),
        )
    }
    pub fn from_json(value: &Json, loci: usize) -> Result<Self> {
        let mut pop = Self::new(loci);
        for cell in value.as_array()? {
            let mut genes = Vec::new();
            for pair in cell.get("loci")?.as_array()? {
                let pair = pair.as_array()?;
                if pair.len() != 2 {
                    return Err("Fixture locus must contain two alleles".into());
                }
                let c = pair[0].as_integer()?;
                let r = pair[1].as_integer()?;
                if !(0..=1).contains(&c) || !(0..=1).contains(&r) {
                    return Err("Fixture interface supports reachable binary genotypes only".into());
                }
                genes.push((c | r << 1) as u8);
            }
            if genes.len() != loci {
                return Err("Fixture locus count differs from configuration".into());
            }
            pop.push(
                Cell {
                    mating_type: cell.get("mating_type")?.as_integer()?,
                    fitness: cell.get("fitness").map_or(Ok(1.0), Json::as_number)?,
                },
                &genes,
            );
        }
        Ok(pop)
    }
}

pub fn counts(genes: &[u8]) -> (usize, usize, usize) {
    let (mut c, mut r, mut b) = (0, 0, 0);
    for &v in genes {
        c += (v & 1) as usize;
        r += ((v >> 1) & 1) as usize;
        b += usize::from(v == 3);
    }
    (c, r, b)
}
pub fn effectiveness(genes: &[u8], config: &Config) -> Result<(f64, f64)> {
    Ok((
        ch_effectiveness(genes, config)?,
        res_effectiveness(genes, config)?,
    ))
}
pub fn ch_effectiveness(genes: &[u8], config: &Config) -> Result<f64> {
    if genes.is_empty() {
        return Err("Effectiveness divides by zero gene pairs".into());
    }
    let (c, _, b) = counts(genes);
    let q = 1.0 / genes.len() as f64;
    Ok(((c - b) as f64 * q) + ((b as f64 * config.ch_eff_rc.number()?) * q))
}
pub fn res_effectiveness(genes: &[u8], config: &Config) -> Result<f64> {
    if genes.is_empty() {
        return Err("Effectiveness divides by zero gene pairs".into());
    }
    let (_, r, b) = counts(genes);
    let q = 1.0 / genes.len() as f64;
    Ok(((r - b) as f64 * q) + ((b as f64 * config.res_eff_rc.number()?) * q))
}
pub fn exploitable(actor: &[u8], target: &[u8], config: &Config) -> Result<bool> {
    for (&a, &b) in actor.iter().zip(target) {
        let c = a & 1;
        let cb = a == 3;
        let tc = b & 1;
        let tr = (b >> 1) & 1;
        let tb = b == 3;
        if config.ch_eff_rc.equals(0.0)? {
            if cb || c == 0 {
                continue;
            }
            if config.res_eff_rc.equals(0.0)? {
                if tc == 1 && !tb {
                    continue;
                }
                if tb || tr == 0 {
                    return Ok(true);
                }
            } else if config.res_eff_rc.equals(1.0)? {
                if tc == 1 && !tb {
                    continue;
                }
                if tr == 0 {
                    return Ok(true);
                }
            }
        } else if config.ch_eff_rc.equals(1.0)? {
            if c == 0 {
                continue;
            }
            if config.res_eff_rc.equals(0.0)? {
                if tc == 1 {
                    continue;
                }
                if tb || tr == 0 {
                    return Ok(true);
                }
            } else if config.res_eff_rc.equals(1.0)? {
                if tc == 1 {
                    continue;
                }
                if tr == 0 {
                    return Ok(true);
                }
            }
        }
    }
    Ok(false)
}

#[derive(Clone, Debug)]
pub struct Measurement {
    pub values: [f64; 8],
    pub loci: Vec<[f64; 3]>,
}
impl Measurement {
    pub fn to_json(&self) -> Json {
        let mut v = Json::object();
        v.insert("values", Json::numbers(self.values));
        v.insert(
            "loci",
            Json::Array(self.loci.iter().map(|x| Json::numbers(*x)).collect()),
        );
        v
    }
}
pub fn measure(pop: &Population, cfg: &Config) -> Result<Measurement> {
    let (mut c, mut r, mut wild) = (0usize, 0usize, 0usize);
    let mut eff = [0.0; 2];
    let mut carriers = [0usize; 2];
    let mut mt = [0usize; 3];
    let mut loci = vec![[0.0; 3]; pop.loci];
    for (i, cell) in pop.cells.iter().enumerate() {
        let genome = pop.genome(i);
        let (ci, ri, _) = counts(genome);
        c += ci;
        r += ri;
        wild += 2 * genome.len() - ci - ri;
        for (tracker, &v) in loci.iter_mut().zip(genome) {
            if v == 3 {
                tracker[2] += 1.0;
            } else {
                tracker[0] += (v & 1) as f64;
                tracker[1] += ((v >> 1) & 1) as f64;
            }
        }
        if ci > 0 {
            eff[0] += ch_effectiveness(genome, cfg)?;
            carriers[0] += 1;
        }
        if ri > 0 {
            eff[1] += res_effectiveness(genome, cfg)?;
            carriers[1] += 1;
        }
        if (1..=3).contains(&cell.mating_type) {
            mt[(cell.mating_type - 1) as usize] += 1;
        }
    }
    let denominator = cfg.gene_pairs as f64 * pop.len() as f64;
    if denominator == 0.0 || pop.is_empty() {
        return Err("Measurement divides by zero: empty population or zero gene_pairs".into());
    }
    Ok(Measurement {
        values: [
            c as f64 / denominator,
            r as f64 / denominator,
            wild as f64 / (2.0 * denominator),
            mt[0] as f64 / pop.len() as f64,
            mt[1] as f64 / pop.len() as f64,
            mt[2] as f64 / pop.len() as f64,
            if carriers[0] == 0 {
                0.0
            } else {
                eff[0] / carriers[0] as f64
            },
            if carriers[1] == 0 {
                0.0
            } else {
                eff[1] / carriers[1] as f64
            },
        ],
        loci,
    })
}
