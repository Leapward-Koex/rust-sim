//! Python json compatibility, including non-standard NaN/Infinity tokens.
//! The scanner changes only complete tokens outside strings. Its marker is chosen
//! absent from the input, so user strings (including JSON-looking strings) survive.
use crate::Result;
use serde_json::Value;

#[derive(Clone, Debug)]
pub enum Json {
    Null,
    Bool(bool),
    Number(serde_json::Number),
    Nonfinite(f64),
    String(String),
    Array(Vec<Json>),
    Object(Vec<(String, Json)>),
}

impl Json {
    pub fn parse(text: &str) -> Result<Self> {
        let mut strings = Vec::new();
        let (mut start, mut quoted, mut escaped) = (0, false, false);
        for (i, ch) in text.char_indices() {
            if quoted {
                if escaped {
                    escaped = false;
                } else if ch == '\\' {
                    escaped = true;
                } else if ch == '"' {
                    quoted = false;
                    if let Ok(s) = serde_json::from_str::<String>(&text[start..=i]) {
                        strings.push(s);
                    }
                }
            } else if ch == '"' {
                quoted = true;
                start = i;
            }
        }
        let mut marker = "__dicty_nonfinite__".to_string();
        while text.contains(&marker) || strings.iter().any(|s| s.contains(&marker)) {
            marker.push('_');
        }
        let mut rewritten = String::with_capacity(text.len());
        let bytes = text.as_bytes();
        let mut i = 0;
        let mut quoted = false;
        let mut escaped = false;
        while i < bytes.len() {
            if !quoted && bytes[i] == b'"' {
                // Escape every user object key before serde's arbitrary-precision
                // visitor can mistake its reserved Number key for a number.
                let mut end = i + 1;
                let mut key_escape = false;
                while end < bytes.len() {
                    if key_escape {
                        key_escape = false;
                    } else if bytes[end] == b'\\' {
                        key_escape = true;
                    } else if bytes[end] == b'"' {
                        break;
                    }
                    end += 1;
                }
                if end < bytes.len() {
                    let mut next = end + 1;
                    while next < bytes.len() && bytes[next].is_ascii_whitespace() {
                        next += 1;
                    }
                    if next < bytes.len() && bytes[next] == b':' {
                        let key: String = serde_json::from_str(&text[i..=end])
                            .map_err(|e| format!("Invalid JSON key: {e}"))?;
                        rewritten.push_str(
                            &serde_json::to_string(&format!("{marker}key:{key}")).unwrap(),
                        );
                        i = end + 1;
                        continue;
                    }
                }
            }
            if !quoted {
                let token = ["-Infinity", "Infinity", "NaN"]
                    .into_iter()
                    .find(|s| text[i..].starts_with(s));
                if let Some(token) = token {
                    let before = i == 0 || b" \r\n\t[:,".contains(&bytes[i - 1]);
                    let end = i + token.len();
                    let after = end == bytes.len() || b" \r\n\t,]}".contains(&bytes[end]);
                    if before && after {
                        rewritten
                            .push_str(&serde_json::to_string(&format!("{marker}{token}")).unwrap());
                        i = end;
                        continue;
                    }
                }
            }
            let ch = text[i..].chars().next().unwrap();
            rewritten.push(ch);
            if quoted {
                if escaped {
                    escaped = false;
                } else if ch == '\\' {
                    escaped = true;
                } else if ch == '"' {
                    quoted = false;
                }
            } else if ch == '"' {
                quoted = true;
            }
            i += ch.len_utf8();
        }
        let value: Value =
            serde_json::from_str(&rewritten).map_err(|e| format!("Invalid parameter JSON: {e}"))?;
        fn convert(v: Value, marker: &str) -> Json {
            match v {
                Value::Null => Json::Null,
                Value::Bool(x) => Json::Bool(x),
                Value::Number(x) => {
                    let lexical = x.to_string();
                    if lexical.contains(['.', 'e', 'E']) {
                        // Python json.loads uses binary64 for float literals,
                        // including overflow to Infinity, and arbitrary-size ints.
                        Json::number(lexical.parse::<f64>().unwrap())
                    } else if lexical == "-0" {
                        Json::integer(0)
                    } else {
                        Json::Number(x)
                    }
                }
                Value::String(x) => match x.strip_prefix(marker) {
                    Some("NaN") => Json::Nonfinite(f64::NAN),
                    Some("Infinity") => Json::Nonfinite(f64::INFINITY),
                    Some("-Infinity") => Json::Nonfinite(f64::NEG_INFINITY),
                    _ => Json::String(x),
                },
                Value::Array(x) => Json::Array(x.into_iter().map(|x| convert(x, marker)).collect()),
                Value::Object(x) => Json::Object(
                    x.into_iter()
                        .map(|(k, v)| {
                            (
                                k.strip_prefix(&format!("{marker}key:"))
                                    .unwrap_or(&k)
                                    .to_string(),
                                convert(v, marker),
                            )
                        })
                        .collect(),
                ),
            }
        }
        Ok(convert(value, &marker))
    }
    pub fn object() -> Self {
        Self::Object(Vec::new())
    }
    pub fn insert(&mut self, key: &str, value: Self) {
        let Self::Object(items) = self else {
            panic!("object required")
        };
        if let Some((_, old)) = items.iter_mut().find(|(k, _)| k == key) {
            *old = value;
        } else {
            items.push((key.into(), value));
        }
    }
    pub fn get(&self, key: &str) -> Result<&Self> {
        let Self::Object(items) = self else {
            return Err("Configuration must be a JSON object".into());
        };
        items
            .iter()
            .find(|(k, _)| k == key)
            .map(|(_, v)| v)
            .ok_or_else(|| format!("Missing parameter: {key}"))
    }
    pub fn number(value: f64) -> Self {
        serde_json::Number::from_f64(value)
            .map(Self::Number)
            .unwrap_or(Self::Nonfinite(value))
    }
    pub fn integer(value: i64) -> Self {
        Self::Number(value.into())
    }
    pub fn string(value: impl Into<String>) -> Self {
        Self::String(value.into())
    }
    pub fn numbers(values: impl IntoIterator<Item = f64>) -> Self {
        Self::Array(values.into_iter().map(Self::number).collect())
    }
    pub fn as_number(&self) -> Result<f64> {
        match self {
            Self::Number(n) => n
                .to_string()
                .parse()
                .map_err(|_| "Number out of range".into()),
            Self::Nonfinite(n) => Ok(*n),
            Self::Bool(n) => Ok(if *n { 1.0 } else { 0.0 }),
            _ => Err("Expected a number".into()),
        }
    }
    pub fn as_integer(&self) -> Result<i64> {
        match self {
            Self::Number(n) => n
                .as_i64()
                .ok_or("Expected an integer (a JSON float is not accepted by Python range)".into()),
            Self::Bool(n) => Ok(i64::from(*n)),
            _ => Err("Expected an integer".into()),
        }
    }
    pub fn as_array(&self) -> Result<&[Self]> {
        if let Self::Array(v) = self {
            Ok(v)
        } else {
            Err("Expected an array".into())
        }
    }
    pub fn as_str(&self) -> Result<&str> {
        if let Self::String(v) = self {
            Ok(v)
        } else {
            Err("Expected a string".into())
        }
    }
    pub fn encode(&self) -> String {
        match self {
            Self::Null => "null".into(),
            Self::Bool(b) => b.to_string(),
            Self::Number(n) => n.to_string(),
            Self::Nonfinite(x) => if x.is_nan() {
                "NaN"
            } else if *x > 0.0 {
                "Infinity"
            } else {
                "-Infinity"
            }
            .into(),
            Self::String(s) => serde_json::to_string(s).unwrap(),
            Self::Array(a) => format!(
                "[{}]",
                a.iter().map(Self::encode).collect::<Vec<_>>().join(",")
            ),
            Self::Object(o) => format!(
                "{{{}}}",
                o.iter()
                    .map(|(k, v)| format!("{}:{}", serde_json::to_string(k).unwrap(), v.encode()))
                    .collect::<Vec<_>>()
                    .join(",")
            ),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn nonfinite_tokens_do_not_change_strings() {
        let x=Json::parse(r#"{"a":NaN,"b":[Infinity,-Infinity],"s":"NaN \"Infinity\" 🐌","__dicty_nonfinite__NaN":"keep","i":1,"f":1.0}"#).unwrap();
        assert!(x.get("a").unwrap().as_number().unwrap().is_nan());
        assert!(x.encode().contains("\"i\":1,\"f\":1.0"));
        assert_eq!(
            x.get("__dicty_nonfinite__NaN").unwrap().as_str().unwrap(),
            "keep"
        );
        assert!(Json::parse("[NaNx]").is_err());
        Json::parse(&x.encode()).unwrap();
    }
    #[test]
    fn escaped_marker_and_large_integer_survive() {
        let x=Json::parse(r#"{"s":"\u005f_dicty_nonfinite__NaN","big":123456789012345678901234567890,"overflow":1e309,"nan":NaN}"#).unwrap();
        assert_eq!(
            x.get("s").unwrap().as_str().unwrap(),
            "__dicty_nonfinite__NaN"
        );
        assert!(x.encode().contains("123456789012345678901234567890"));
        assert_eq!(
            x.get("overflow").unwrap().as_number().unwrap(),
            f64::INFINITY
        );
        assert!(x.encode().contains("\"overflow\":Infinity"));
    }
    #[test]
    fn serde_private_number_key_remains_an_object() {
        for text in [
            r#"{"extra":{"$serde_json::private::Number":"7"}}"#,
            r#"{"extra":{"$serde_json::private::Number":"hello","x":[NaN,1.0,123456789012345678901234567890]}}"#,
            r#"{"extra":{"\u0024serde_json::private::Number":{"nested":"1"}}}"#,
        ] {
            let value = Json::parse(text).unwrap();
            let extra = value.get("extra").unwrap();
            assert!(matches!(extra, Json::Object(_)));
            extra.get("$serde_json::private::Number").unwrap();
            assert_eq!(
                Json::parse(&value.encode()).unwrap().encode(),
                value.encode()
            );
        }
    }
}
