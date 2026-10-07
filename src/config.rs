use crate::{Result, json::Json};

/// Cached conversions are checked only where a Python operation reads them.
/// Unused phase parameters may legitimately contain nulls or fractions.
#[derive(Clone, Debug)]
pub struct Parameter {
    name: &'static str,
    value: Option<Json>,
    number: Result<f64>,
    integer: Result<i64>,
}
impl Parameter {
    fn new(raw: &Json, name: &'static str) -> Self {
        let value = raw.get(name).ok().cloned();
        let number = raw
            .get(name)
            .and_then(Json::as_number)
            .map_err(|e| format!("{name}: {e}"));
        let integer = raw
            .get(name)
            .and_then(Json::as_integer)
            .map_err(|e| format!("{name}: {e}"));
        Self {
            name,
            value,
            number,
            integer,
        }
    }
    #[inline]
    pub fn number(&self) -> Result<f64> {
        self.number.clone()
    }
    pub fn integer(&self) -> Result<i64> {
        self.integer.clone()
    }
    pub fn value(&self) -> Result<&Json> {
        self.value
            .as_ref()
            .ok_or_else(|| format!("Missing parameter: {}", self.name))
    }
    pub fn equals(&self, n: f64) -> Result<bool> {
        self.value()?;
        Ok(self.number.as_ref().ok().copied() == Some(n))
    }
    pub fn string(&self) -> Result<&str> {
        self.value()?
            .as_str()
            .map_err(|e| format!("{}: {e}", self.name))
    }
}

#[derive(Clone, Debug)]
pub struct Config {
    pub raw: Json,
    pub n_runs: i64,
    pub n_dev: i64,
    pub gene_pairs: i64,
    pub vg: Parameter,
    pub n: Parameter,
    pub sl: Parameter,
    pub sp: Parameter,
    pub m_ch: Parameter,
    pub m_re: Parameter,
    pub c_ch: Parameter,
    pub c_res: Parameter,
    pub ch_germ: Parameter,
    pub ch_start: Parameter,
    pub res_start: Parameter,
    pub ch_res_dist: Parameter,
    pub ch_eff_rc: Parameter,
    pub res_eff_rc: Parameter,
    pub mc_count: Parameter,
    pub mc_germ_count: Parameter,
    pub recomb_chance: Parameter,
    pub mt: [Parameter; 3],
    pub resistance_type: Parameter,
    pub discrete_res: Parameter,
    pub interval: Parameter,
    pub schedule: Parameter,
    pub output: Parameter,
}
impl Config {
    pub fn parse(text: &str) -> Result<Self> {
        Self::from_json(Json::parse(text)?)
    }
    pub fn from_json(raw: Json) -> Result<Self> {
        let int = |k: &str| raw.get(k)?.as_integer().map_err(|e| format!("{k}: {e}"));
        let p = |k| Parameter::new(&raw, k);
        Ok(Self {
            n_runs: int("n_runs")?,
            n_dev: int("n_dev")?,
            gene_pairs: int("gene_pairs")?,
            vg: p("vg"),
            n: p("n"),
            sl: p("sl"),
            sp: p("sp"),
            m_ch: p("m_ch"),
            m_re: p("m_re"),
            c_ch: p("c_ch"),
            c_res: p("c_res"),
            ch_germ: p("ch_germ"),
            ch_start: p("ch_start"),
            res_start: p("res_start"),
            ch_res_dist: p("ch_res_dist"),
            ch_eff_rc: p("ch_eff_rc"),
            res_eff_rc: p("res_eff_rc"),
            mc_count: p("mc_count"),
            mc_germ_count: p("mc_germ_count"),
            recomb_chance: p("recomb_chance"),
            mt: [p("mt1_start"), p("mt2_start"), p("mt3_start")],
            resistance_type: p("resistance_type"),
            discrete_res: p("discrete_res"),
            interval: p("sex_cycle_interval"),
            schedule: p("i_macrocyst"),
            output: p("output_filepath"),
            raw,
        })
    }
    pub fn loci(&self) -> usize {
        self.gene_pairs.max(0) as usize
    }
    pub fn scheduled(&self, cycle: i64) -> Result<(bool, bool)> {
        let schedule =
            self.schedule.value()?.as_array().map_err(|_| {
                "i_macrocyst must be an array for development scheduling".to_string()
            })?;
        if !self.interval.equals(0.0)? {
            let first = schedule
                .first()
                .ok_or("Nonzero sex_cycle_interval with empty i_macrocyst")?;
            if first.as_number().ok() == Some(0.0) {
                return Ok(((cycle as f64) % self.interval.number()? == 0.0, true));
            }
        }
        Ok((
            schedule
                .iter()
                .any(|x| x.as_number().ok() == Some(cycle as f64)),
            false,
        ))
    }
}

pub fn trunc_count(value: f64, name: &str) -> Result<i64> {
    if !value.is_finite() || value < i64::MIN as f64 || value >= i64::MAX as f64 {
        return Err(format!("{name}: cannot convert to a finite integer"));
    }
    Ok(value as i64)
}
