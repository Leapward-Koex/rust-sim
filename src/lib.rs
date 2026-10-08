pub mod accelerated;
pub mod aggregate;
pub mod config;
pub mod engine;
pub mod gpu;
pub mod json;
pub mod model;
pub mod random;

pub type Result<T> = std::result::Result<T, String>;
pub const CANCELLED: &str = "Simulation cancelled";
pub const BEHAVIOR_VERSION: &str = "python-test-env-62d707e-v1";
