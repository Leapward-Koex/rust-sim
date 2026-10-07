use crate::{Result, config::Config, engine::RepeatResult, json::Json};
use statrs::distribution::{ContinuousCDF, StudentsT};

pub fn confidence(data: &[f64]) -> f64 {
    if data.len() < 2 {
        return f64::NAN;
    }
    let mean = data.iter().sum::<f64>() / data.len() as f64;
    let sum = data.iter().map(|x| (x - mean) * (x - mean)).sum::<f64>();
    let se = (sum / (data.len() - 1) as f64).sqrt() / (data.len() as f64).sqrt();
    // The Python function captured 0.95 when defined, before configuration import.
    se * StudentsT::new(0.0, 1.0, (data.len() - 1) as f64)
        .unwrap()
        .inverse_cdf(0.975)
}
pub fn aggregate(cfg: &Config, repeats: &[RepeatResult]) -> Result<Json> {
    let times = (cfg.n_dev + 1).max(0) as usize;
    if times > 0 && repeats.is_empty() {
        return Err("Cannot aggregate zero repeats".into());
    }
    if repeats.iter().any(|r| r.measurements.len() < times) {
        return Err("Incomplete repeat history".into());
    }
    let mut result = Json::object();
    result.insert("parameters", cfg.raw.clone());
    result.insert(
        "sex_cycle_list",
        Json::Array(
            repeats
                .iter()
                .flat_map(|r| r.sex_cycles.iter())
                .map(|x| Json::integer(*x))
                .collect(),
        ),
    );
    result.insert(
        "x_axis_values",
        Json::Array((0..times).map(|x| Json::integer(x as i64)).collect()),
    );
    let names = [
        ("mean_ch", "ch_ci"),
        ("mean_res", "res_ci"),
        ("mean_wild", "wild_ci"),
        ("mean_mt1", "mt1_ci"),
        ("mean_mt2", "mt2_ci"),
        ("mean_mt3", "mt3_ci"),
        ("graph_mean_ch_eff", "ch_eff_ci"),
        ("graph_mean_res_eff", "res_eff_ci"),
    ];
    for (series, (mean_name, ci_name)) in names.iter().enumerate() {
        let mut means = Vec::with_capacity(times);
        let mut cis = Vec::with_capacity(times);
        for t in 0..times {
            let values: Vec<_> = repeats
                .iter()
                .map(|r| r.measurements[t].values[series])
                .collect();
            means.push(values.iter().sum::<f64>() / values.len() as f64);
            cis.push(confidence(&values));
        }
        result.insert(mean_name, Json::numbers(means));
        result.insert(ci_name, Json::numbers(cis));
    }
    let mut mean_dict = Json::object();
    let mut ci_dict = Json::object();
    for locus in 0..cfg.loci() {
        let mut means = Vec::new();
        let mut cis = Vec::new();
        for series in 0..3 {
            let mut m = Vec::new();
            let mut c = Vec::new();
            for t in 0..times {
                let values: Vec<_> = repeats
                    .iter()
                    .map(|r| r.measurements[t].loci[locus][series])
                    .collect();
                m.push(values.iter().sum::<f64>() / values.len() as f64);
                c.push(confidence(&values));
            }
            means.push(Json::numbers(m));
            cis.push(Json::numbers(c));
        }
        let key = format!("gene_pair{locus}");
        mean_dict.insert(&key, Json::Array(means));
        ci_dict.insert(&key, Json::Array(cis));
    }
    result.insert("average_tracker_dict", mean_dict);
    result.insert("ci_tracker_dict", ci_dict);
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn scipy_confidence_examples() {
        assert!(confidence(&[1.0]).is_nan());
        assert_eq!(confidence(&[4.0, 4.0]), 0.0);
        assert!((confidence(&[1.0, 2.0, 3.0]) - 2.484137711719546).abs() < 1e-8);
    }
}
