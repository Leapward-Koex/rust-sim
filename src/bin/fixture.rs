//! Private differential-test adapter. Not included in the desktop distribution.
use dicty_sim::{
    Result,
    aggregate::{self, confidence},
    config::Config,
    engine::{self, Context},
    json::Json,
    model::{Population, measure},
    random::{Script, ScriptedChoices},
};
use std::io::{self, Read};

fn run(request: &Json, rng: &mut ScriptedChoices) -> Result<Json> {
    let operation = request.get("operation")?.as_str()?;
    if operation == "confidence" {
        let data = request.get("data")?.as_array()?;
        let mut out = Json::object();
        out.insert(
            "confidence",
            Json::numbers(
                data.iter()
                    .map(|a| {
                        a.as_array()?
                            .iter()
                            .map(Json::as_number)
                            .collect::<Result<Vec<_>>>()
                    })
                    .collect::<Result<Vec<_>>>()?
                    .iter()
                    .map(|a| confidence(a)),
            ),
        );
        return Ok(out);
    }
    let cfg = Config::from_json(request.get("config")?.clone())?;
    let ctx = Context::default();
    let mut out = Json::object();
    if operation == "run" {
        let mut repeats = Vec::new();
        for r in 0..cfg.n_runs.max(0) as usize {
            repeats.push(engine::simulate_repeat(&cfg, rng, &ctx, r, &|_| {})?);
        }
        out.insert("result", aggregate::aggregate(&cfg, &repeats)?);
        if let Some(last) = repeats.last() {
            out.insert("population", last.population.to_json());
        }
        return Ok(out);
    }
    let pop = if operation == "initialize" {
        engine::initialize(&cfg, rng, &ctx)?
    } else {
        let pop = Population::from_json(request.get("cells")?, cfg.loci())?;
        match operation {
            "growth" => engine::growth(pop, &cfg, rng, &ctx)?,
            "development" => engine::development(pop, &cfg, rng, &ctx)?,
            "sex" => engine::sex(pop, &cfg, rng, &ctx)?,
            "measure" => pop,
            _ => return Err(format!("Unknown fixture operation: {operation}")),
        }
    };
    out.insert("population", pop.to_json());
    if matches!(operation, "initialize" | "development" | "measure") {
        out.insert("measurement", measure(&pop, &cfg)?.to_json());
    }
    Ok(out)
}
fn main() {
    let mut text = String::new();
    io::stdin().read_to_string(&mut text).unwrap();
    let mut rng = ScriptedChoices::new(Script::default());
    let result = (|| {
        let request = Json::parse(&text)?;
        if let Ok(script) = request.get("script") {
            rng.script = serde_json::from_str(&script.encode()).map_err(|e| e.to_string())?;
        }
        run(&request, &mut rng)
    })();
    let failed = result.is_err();
    let mut out = result.unwrap_or_else(|e| {
        let mut out = Json::object();
        out.insert("error", Json::string(e));
        out
    });
    out.insert(
        "consumed",
        Json::parse(&serde_json::to_string(&rng.consumed).unwrap()).unwrap(),
    );
    println!("{}", out.encode());
    if failed {
        std::process::exit(1);
    }
}
