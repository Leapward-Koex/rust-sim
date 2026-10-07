//! Native sampling regressions supplement (not replace) scripted source parity.
//! Fixed seeds and an a-priori six-standard-deviation bound avoid significance
//! fishing. These tests detect gross distribution mistakes, not prove equivalence.
use dicty_sim::{
    config::Config,
    engine::{Context, simulate},
    json::Json,
    model::exploitable,
    random::{Choices, NativeChoices},
};
use std::sync::{Arc, atomic::Ordering};

fn six_sigma(observed: usize, n: usize, p: f64) {
    let expected = n as f64 * p;
    let margin = 6.0 * (n as f64 * p * (1.0 - p)).sqrt();
    assert!(
        (observed as f64 - expected).abs() <= margin,
        "{observed} outside {expected} +/- {margin}"
    );
}

#[test]
fn weighted_native_frequencies() {
    let mut rng = NativeChoices::new(971011, 0, Arc::default());
    let draws = rng.weighted(&[1.0, 2.0, 3.0], 60_000).unwrap();
    let mut counts = [0; 3];
    for x in draws {
        counts[x] += 1;
    }
    for (i, count) in counts.iter().enumerate() {
        six_sigma(*count, 60_000, (i + 1) as f64 / 6.0);
    }
}

#[test]
fn ordered_samples_are_uniform_without_replacement() {
    let mut rng = NativeChoices::new(20261007, 0, Arc::default());
    let mut pairs = [[0; 4]; 4];
    for _ in 0..60_000 {
        let draw = rng.sample(4, 2).unwrap();
        assert_ne!(draw[0], draw[1]);
        pairs[draw[0]][draw[1]] += 1;
    }
    for (i, row) in pairs.iter().enumerate() {
        for (j, count) in row.iter().enumerate() {
            if i == j {
                assert_eq!(*count, 0);
            } else {
                six_sigma(*count, 60_000, 1.0 / 12.0);
            }
        }
    }
    assert!(rng.sample(4, 5).is_err());
    assert!(rng.sample(4, -1).is_err());
    assert_eq!(rng.sample(4, 0).unwrap(), Vec::<usize>::new());
}

#[test]
fn numpy_family_integer_frequencies() {
    let mut rng = NativeChoices::new(7123, 4, Arc::default());
    let mut counts = [0; 3];
    for _ in 0..60_000 {
        counts[rng.integer(3).unwrap()] += 1;
    }
    for count in counts {
        six_sigma(count, 60_000, 1.0 / 3.0);
    }
    assert!(rng.integer(0).is_err());
}

#[test]
fn documented_exploitation_table() {
    let base = Config::parse(include_str!("../reference-source/import_template.json")).unwrap();
    for (ch, re, pairs) in [
        (0.0, 0.0, vec![(1, 0), (1, 3)]),
        (0.0, 1.0, vec![(1, 0)]),
        (1.0, 0.0, vec![(1, 0), (3, 0)]),
        (1.0, 1.0, vec![(1, 0), (3, 0)]),
        (0.5, 1.0, vec![]),
        (1.0, 0.5, vec![]),
    ] {
        let mut raw = base.raw.clone();
        raw.insert("ch_eff_rc", Json::number(ch));
        raw.insert("res_eff_rc", Json::number(re));
        let cfg = Config::from_json(raw).unwrap();
        for a in 0..4 {
            for b in 0..4 {
                assert_eq!(
                    exploitable(&[a], &[b], &cfg).unwrap(),
                    pairs.contains(&(a, b)),
                    "ch={ch} re={re} actor={a} target={b}"
                );
            }
        }
    }
}

#[test]
fn cancellation_checked_before_initialization() {
    let mut raw = Json::parse(include_str!("../reference-source/import_template.json")).unwrap();
    raw.insert("n_runs", Json::integer(2));
    let cfg = Config::from_json(raw).unwrap();
    let ctx = Context::default();
    ctx.cancelled.store(true, Ordering::Relaxed);
    for threads in [1, 2] {
        assert_eq!(
            simulate(&cfg, 1, threads, &ctx, |_| {}).unwrap_err(),
            dicty_sim::CANCELLED
        );
    }
}
