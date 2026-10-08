use crate::{CANCELLED, Result};
use rand::{Rng, SeedableRng};
use rand_chacha::ChaCha12Rng;
use serde::Deserialize;
use std::sync::{
    Arc,
    atomic::{AtomicBool, Ordering},
};

pub trait Choices {
    fn uniform(&mut self) -> Result<f64>;
    fn integer(&mut self, high: usize) -> Result<usize>;
    fn sample(&mut self, n: usize, k: i64) -> Result<Vec<usize>>;
    fn weighted(&mut self, weights: &[f64], k: i64) -> Result<Vec<usize>>;
}

pub struct NativeChoices {
    py: ChaCha12Rng,
    np: ChaCha12Rng,
    cancel: Arc<AtomicBool>,
}
/// Exact state needed to run the existing Python-family ChaCha12 stream on a
/// device. Positions are in u32 words, including a possible odd offset.
#[derive(Clone, Copy, Debug)]
pub(crate) struct PyStream {
    pub key: [u32; 8],
    pub stream: u64,
    pub word_pos: u64,
}
impl NativeChoices {
    pub fn new(seed: u64, repeat: usize, cancel: Arc<AtomicBool>) -> Self {
        let mut py = ChaCha12Rng::seed_from_u64(seed);
        let mut np = py.clone();
        py.set_stream((repeat as u64).wrapping_mul(2));
        np.set_stream((repeat as u64).wrapping_mul(2).wrapping_add(1));
        Self { py, np, cancel }
    }
    pub(crate) fn py_stream(&self) -> Result<PyStream> {
        let seed = self.py.get_seed();
        let mut key = [0; 8];
        for (word, bytes) in key.iter_mut().zip(seed.chunks_exact(4)) {
            *word = u32::from_le_bytes(bytes.try_into().unwrap());
        }
        Ok(PyStream {
            key,
            stream: self.py.get_stream(),
            word_pos: self.py.get_word_pos().try_into().map_err(|_| {
                "GPU random stream position exceeds supported 64-bit word offset".to_string()
            })?,
        })
    }
    pub(crate) fn advance_py_words(&mut self, words: u64) -> Result<()> {
        let end = self
            .py_stream()?
            .word_pos
            .checked_add(words)
            .ok_or("GPU random stream position overflow")?;
        self.py.set_word_pos(end as u128);
        Ok(())
    }
    fn check(&self) -> Result<()> {
        if self.cancel.load(Ordering::Relaxed) {
            Err(CANCELLED.into())
        } else {
            Ok(())
        }
    }
}

pub fn cumulative(weights: &[f64]) -> Result<Vec<f64>> {
    if weights.is_empty() {
        return Err("Cannot select parents from an empty population".into());
    }
    let mut sum = 0.0;
    let values: Vec<_> = weights
        .iter()
        .map(|x| {
            sum += x;
            sum
        })
        .collect();
    if sum <= 0.0 || !sum.is_finite() {
        return Err("Total selection weight must be finite and greater than zero".into());
    }
    Ok(values)
}

// Python random.choices uses bisect_right(cumulative, draw * total, 0, n-1).
// Its behavior for negative individual weights intentionally survives here.
pub fn weighted_index(cum: &[f64], draw: f64) -> usize {
    let value = draw * cum[cum.len() - 1];
    let mut low = 0;
    let mut high = cum.len() - 1;
    while low < high {
        let mid = (low + high) / 2;
        if value < cum[mid] {
            high = mid;
        } else {
            low = mid + 1;
        }
    }
    low
}
fn sample_size(n: usize, k: i64) -> Result<usize> {
    if k < 0 || k as u64 > n as u64 {
        Err(format!("Sample size {k} is outside population size {n}"))
    } else {
        Ok(k as usize)
    }
}
impl Choices for NativeChoices {
    #[inline]
    fn uniform(&mut self) -> Result<f64> {
        Ok(self.py.random())
    }
    #[inline]
    fn integer(&mut self, high: usize) -> Result<usize> {
        if high == 0 {
            Err("Cannot choose from an empty candidate set".into())
        } else {
            Ok(self.np.random_range(0..high))
        }
    }
    fn sample(&mut self, n: usize, k: i64) -> Result<Vec<usize>> {
        let k = sample_size(n, k)?;
        let mut pool: Vec<_> = (0..n).collect();
        for i in 0..k {
            if i % 1024 == 0 {
                self.check()?;
            }
            let j = self.py.random_range(i..n);
            pool.swap(i, j);
        }
        pool.truncate(k);
        Ok(pool)
    }
    fn weighted(&mut self, weights: &[f64], k: i64) -> Result<Vec<usize>> {
        let cum = cumulative(weights)?;
        let mut result = Vec::new();
        result
            .try_reserve(k.max(0) as usize)
            .map_err(|e| format!("Parent selection allocation failed: {e}"))?;
        for i in 0..k {
            if i % 1024 == 0 {
                self.check()?;
            }
            result.push(weighted_index(&cum, self.py.random()));
        }
        Ok(result)
    }
}

#[derive(Default, Deserialize)]
#[serde(default)]
pub struct Script {
    pub uniforms: Vec<f64>,
    pub integers: Vec<usize>,
    pub samples: Vec<Vec<usize>>,
    pub weighted: Vec<Vec<usize>>,
}
#[derive(Default, serde::Serialize)]
pub struct Consumed {
    pub uniforms: usize,
    pub integers: usize,
    pub samples: usize,
    pub weighted: usize,
}
pub struct ScriptedChoices {
    pub script: Script,
    pub consumed: Consumed,
}
impl ScriptedChoices {
    pub fn new(script: Script) -> Self {
        Self {
            script,
            consumed: Consumed::default(),
        }
    }
}
impl Choices for ScriptedChoices {
    fn uniform(&mut self) -> Result<f64> {
        let i = self.consumed.uniforms;
        let x = *self
            .script
            .uniforms
            .get(i)
            .ok_or_else(|| format!("Script uniform {i} exhausted"))?;
        self.consumed.uniforms += 1;
        Ok(x)
    }
    fn integer(&mut self, high: usize) -> Result<usize> {
        if high == 0 {
            return Err("Cannot choose from an empty candidate set".into());
        }
        let i = self.consumed.integers;
        let x = *self
            .script
            .integers
            .get(i)
            .ok_or_else(|| format!("Script integer {i} exhausted"))?;
        self.consumed.integers += 1;
        if x >= high {
            return Err(format!("Script integer {x} outside 0..{high}"));
        }
        Ok(x)
    }
    fn sample(&mut self, n: usize, k: i64) -> Result<Vec<usize>> {
        let k = sample_size(n, k)?;
        let i = self.consumed.samples;
        let x = self
            .script
            .samples
            .get(i)
            .ok_or_else(|| format!("Script sample {i} exhausted"))?
            .clone();
        self.consumed.samples += 1;
        let mut sorted = x.clone();
        sorted.sort_unstable();
        sorted.dedup();
        if x.len() != k || sorted.len() != k || x.iter().any(|j| *j >= n) {
            return Err("Invalid scripted sample".into());
        }
        Ok(x)
    }
    fn weighted(&mut self, weights: &[f64], k: i64) -> Result<Vec<usize>> {
        cumulative(weights)?;
        let i = self.consumed.weighted;
        let x = self
            .script
            .weighted
            .get(i)
            .ok_or_else(|| format!("Script weighted choice {i} exhausted"))?
            .clone();
        self.consumed.weighted += 1;
        if x.len() != k.max(0) as usize || x.iter().any(|j| *j >= weights.len()) {
            return Err("Invalid scripted weighted choice".into());
        }
        Ok(x)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn negative_weights_use_python_bisect() {
        let c = cumulative(&[2.0, -1.0, 2.0]).unwrap();
        assert_eq!(weighted_index(&c, 0.2), 0);
        assert_eq!(weighted_index(&c, 0.5), 2);
        assert!(cumulative(&[-1.0, 1.0]).is_err());
    }
    #[test]
    fn streams_repeat_independently() {
        let mut a = NativeChoices::new(42, 2, Arc::default());
        let mut b = NativeChoices::new(42, 2, Arc::default());
        for _ in 0..100 {
            assert_eq!(a.uniform().unwrap(), b.uniform().unwrap());
            a.integer(50).unwrap();
        }
    }
}
