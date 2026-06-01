use codex_protocol::config_types::ModeKind;
use codex_protocol::request_user_input::RequestUserInputArgs;
use codex_tools::JsonSchema;
use codex_tools::ResponsesApiTool;
use codex_tools::ToolSpec;
use std::collections::BTreeMap;

pub const REQUEST_USER_INPUT_TOOL_NAME: &str = "request_user_input";

pub fn create_request_user_input_tool(
    description: String,
    default_options_count: usize,
    max_questions: usize,
) -> ToolSpec {
    let option_props = BTreeMap::from([
        (
            "label".to_string(),
            JsonSchema::string(Some("User-facing label (1-5 words).".to_string())),
        ),
        (
            "description".to_string(),
            JsonSchema::string(Some(
                "One short sentence explaining impact/tradeoff if selected.".to_string(),
            )),
        ),
    ]);

    let options_schema = JsonSchema::array_with_bounds(
        JsonSchema::object(
            option_props,
            Some(vec!["label".to_string(), "description".to_string()]),
            Some(false.into()),
        ),
        Some(format!(
            "Provide exactly {default_options_count} mutually exclusive choices. Put the recommended option first and suffix its label with \"(Recommended)\". For each description, explain in one short sentence what this choice prioritizes and what it trades off. Do not include a free-form answer option; the client will add \"Custom answer\" automatically."
        )),
        Some(default_options_count),
        Some(default_options_count),
    );

    let question_props = BTreeMap::from([
        (
            "id".to_string(),
            JsonSchema::string(Some(
                "Stable identifier for mapping answers (snake_case).".to_string(),
            )),
        ),
        (
            "header".to_string(),
            JsonSchema::string(Some(
                "Short header label shown in the UI (12 or fewer chars).".to_string(),
            )),
        ),
        (
            "question".to_string(),
            JsonSchema::string(Some(
                "Single-sentence prompt shown to the user.".to_string(),
            )),
        ),
        ("options".to_string(), options_schema),
    ]);

    let questions_schema = JsonSchema::array_with_bounds(
        JsonSchema::object(
            question_props,
            Some(vec![
                "id".to_string(),
                "header".to_string(),
                "question".to_string(),
                "options".to_string(),
            ]),
            Some(false.into()),
        ),
        Some(format!(
            "Questions to show the user. Prefer 1 and do not exceed {max_questions}"
        )),
        Some(1),
        Some(max_questions),
    );

    let properties = BTreeMap::from([("questions".to_string(), questions_schema)]);

    ToolSpec::Function(ResponsesApiTool {
        name: REQUEST_USER_INPUT_TOOL_NAME.to_string(),
        description,
        strict: false,
        defer_loading: None,
        parameters: JsonSchema::object(
            properties,
            Some(vec!["questions".to_string()]),
            Some(false.into()),
        ),
        output_schema: None,
    })
}

pub fn request_user_input_unavailable_message(
    mode: ModeKind,
    available_modes: &[ModeKind],
) -> Option<String> {
    if available_modes.contains(&mode) {
        None
    } else {
        let mode_name = mode.display_name();
        Some(format!(
            "request_user_input is unavailable in {mode_name} mode"
        ))
    }
}

pub fn normalize_request_user_input_args(
    mut args: RequestUserInputArgs,
    default_options_count: usize,
    max_questions: usize,
) -> Result<RequestUserInputArgs, String> {
    if default_options_count == 0 {
        return Err(
            "request_user_input default options count must be greater than zero".to_string(),
        );
    }
    if max_questions == 0 {
        return Err("request_user_input max questions must be greater than zero".to_string());
    }

    let questions_count = args.questions.len();
    if questions_count == 0 || questions_count > max_questions {
        return Err(format!(
            "request_user_input requires between 1 and {max_questions} questions; received {questions_count}"
        ));
    }

    for question in &mut args.questions {
        let options_count = question.options.as_ref().map_or(0, Vec::len);
        if options_count != default_options_count {
            return Err(format!(
                "request_user_input requires exactly {default_options_count} options for every question; received {options_count}"
            ));
        }
        question.is_other = true;
    }

    Ok(args)
}

pub fn request_user_input_tool_description(
    available_modes: &[ModeKind],
    max_questions: usize,
) -> String {
    let allowed_modes = format_allowed_modes(available_modes);
    format!(
        "Request user input for up to {max_questions} short questions and wait for the response. This tool is only available in {allowed_modes}."
    )
}

fn format_allowed_modes(available_modes: &[ModeKind]) -> String {
    let mode_names: Vec<&str> = available_modes
        .iter()
        .map(|mode| mode.display_name())
        .collect();

    match mode_names.as_slice() {
        [] => "no modes".to_string(),
        [mode] => format!("{mode} mode"),
        [first, second] => format!("{first} or {second} mode"),
        [..] => format!("modes: {}", mode_names.join(",")),
    }
}

#[cfg(test)]
#[path = "request_user_input_spec_tests.rs"]
mod tests;
