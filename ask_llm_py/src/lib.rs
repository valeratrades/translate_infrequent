use std::sync::LazyLock;

use pyo3::{exceptions::PyValueError, prelude::*};

static RT: LazyLock<tokio::runtime::Runtime> =
    LazyLock::new(|| tokio::runtime::Runtime::new().expect("tokio runtime is creatable at import"));

#[pymodule]
mod ask_llm_py {
    use super::*;

    #[pyfunction]
    fn ask(py: Python<'_>, prompt: String, model: &str) -> PyResult<String> {
        let model: ask_llm::Model = model
            .parse()
            .map_err(|e| PyValueError::new_err(format!("unknown ask_llm model '{model}': {e}")))?;
        py.detach(|| RT.block_on(ask_llm::Client::default().model(model).ask(prompt)))
            .map(|r| r.text)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("{e:?}")))
    }
}
