use super::*;
use codex_features::Feature;
use codex_features::Features;
use codex_protocol::config_types::ModeKind;
use codex_protocol::request_user_input::RequestUserInputQuestion;
use codex_protocol::request_user_input::RequestUserInputQuestionOption;
use codex_tools::JsonSchema;
use codex_tools::request_user_input_available_modes;
use pretty_assertions::assert_eq;
use std::collections::BTreeMap;

fn default_mode_enabled_available_modes() -> Vec<ModeKind> {
    let mut features = Features::with_defaults();
    features.enable(Feature::DefaultModeRequestUserInput);
    request_user_input_available_modes(&features)
}

fn default_available_modes() -> Vec<ModeKind> {
    request_user_input_available_modes(&Features::with_defaults())
}

#[test]
fn request_user_input_tool_includes_questions_schema() {
    assert_eq!(
        create_request_user_input_tool("Ask the user to choose.".to_string()),
        ToolSpec::Function(ResponsesApiTool {
            name: "request_user_input".to_string(),
            description: "Ask the user to choose.".to_string(),
            strict: false,
            defer_loading: None,
            parameters: JsonSchema::object(BTreeMap::from([(
                    "questions".to_string(),
                    JsonSchema::array(
                        JsonSchema::object(
                            BTreeMap::from([
                                (
                                    "header".to_string(),
                                    JsonSchema::string(Some(
                                        "Short header label shown in the UI (12 or fewer chars)."
                                            .to_string(),
                                    )),
                                ),
                                (
                                    "id".to_string(),
                                    JsonSchema::string(Some(
                                        "Stable identifier for mapping answers (snake_case)."
                                            .to_string(),
                                    )),
                                ),
                                (
                                    "isOther".to_string(),
                                    JsonSchema::boolean(Some(
                                        "When true, add a custom answer option. Omit unless the user needs free-form input."
                                            .to_string(),
                                    )),
                                ),
                                (
                                    "options".to_string(),
                                    JsonSchema::array(
                                        JsonSchema::object(
                                            BTreeMap::from([
                                                (
                                                    "description".to_string(),
                                                    JsonSchema::string(Some(
                                                        "One short sentence explaining impact/tradeoff if selected."
                                                            .to_string(),
                                                    )),
                                                ),
                                                (
                                                    "label".to_string(),
                                                    JsonSchema::string(Some(
                                                        "User-facing label (1-5 words)."
                                                            .to_string(),
                                                    )),
                                                ),
                                            ]),
                                            Some(vec![
                                                "label".to_string(),
                                                "description".to_string(),
                                            ]),
                                            Some(false.into()),
                                        ),
                                        Some(
                                            "Provide 2-6 mutually exclusive choices. Put the recommended option first and suffix its label with \"(Recommended)\". For each description, explain in one short sentence what this choice prioritizes and what it trades off. Do not include an \"Other\" option; set isOther only when free-form input is needed."
                                                .to_string(),
                                        ),
                                    ),
                                ),
                                (
                                    "question".to_string(),
                                    JsonSchema::string(Some(
                                        "Single-sentence prompt shown to the user.".to_string(),
                                    )),
                                ),
                            ]),
                            Some(vec![
                                "id".to_string(),
                                "header".to_string(),
                                "question".to_string(),
                                "options".to_string(),
                            ]),
                            Some(false.into()),
                        ),
                        Some(
                            "Questions to show the user. Prefer 1 and do not exceed 3".to_string(),
                        ),
                    ),
                )]), Some(vec!["questions".to_string()]), Some(false.into())),
            output_schema: None,
        })
    );
}

fn request_user_input_question(is_other: bool) -> RequestUserInputQuestion {
    RequestUserInputQuestion {
        id: "choice".to_string(),
        header: "Choice".to_string(),
        question: "Choose an option.".to_string(),
        is_other,
        is_secret: false,
        options: Some(vec![RequestUserInputQuestionOption {
            label: "Option 1".to_string(),
            description: "Prioritizes the first path and trades off the second.".to_string(),
        }]),
    }
}

#[test]
fn normalize_request_user_input_args_preserves_default_is_other_false() {
    let args = RequestUserInputArgs {
        questions: vec![request_user_input_question(false)],
    };

    let normalized = normalize_request_user_input_args(args.clone()).expect("valid input");

    assert_eq!(normalized, args);
}

#[test]
fn normalize_request_user_input_args_preserves_explicit_is_other_true() {
    let args = RequestUserInputArgs {
        questions: vec![request_user_input_question(true)],
    };

    let normalized = normalize_request_user_input_args(args.clone()).expect("valid input");

    assert_eq!(normalized, args);
}

#[test]
fn request_user_input_unavailable_messages_respect_default_mode_feature_flag() {
    assert_eq!(
        request_user_input_unavailable_message(ModeKind::Plan, &default_available_modes()),
        None
    );
    assert_eq!(
        request_user_input_unavailable_message(ModeKind::Default, &default_available_modes()),
        Some("request_user_input is unavailable in Default mode".to_string())
    );
    assert_eq!(
        request_user_input_unavailable_message(
            ModeKind::Default,
            &default_mode_enabled_available_modes()
        ),
        None
    );
    assert_eq!(
        request_user_input_unavailable_message(ModeKind::Execute, &default_available_modes()),
        Some("request_user_input is unavailable in Execute mode".to_string())
    );
    assert_eq!(
        request_user_input_unavailable_message(
            ModeKind::PairProgramming,
            &default_available_modes()
        ),
        Some("request_user_input is unavailable in Pair Programming mode".to_string())
    );
}

#[test]
fn request_user_input_tool_description_mentions_available_modes() {
    assert_eq!(
        request_user_input_tool_description(&default_available_modes()),
        "Request user input for one to three short questions and wait for the response. This tool is only available in Plan mode.".to_string()
    );
    assert_eq!(
        request_user_input_tool_description(&default_mode_enabled_available_modes()),
        "Request user input for one to three short questions and wait for the response. This tool is only available in Default or Plan mode.".to_string()
    );
}
