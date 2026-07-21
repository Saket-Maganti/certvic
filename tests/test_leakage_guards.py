from certvic.validation.leakage import check_path_no_leakage, check_prompt_no_leakage, validate_task_no_leakage


def test_leakage_detection_in_prompt_and_filename(smoke_tasks):
    assert check_prompt_no_leakage("The object was removed. Respond yes or no.")
    assert check_path_no_leakage("scene_removed_answer.png")
    assert validate_task_no_leakage(smoke_tasks[0]) == []
