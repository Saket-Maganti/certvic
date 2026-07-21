def test_open_vlm_modules_import_without_torch_load():
    import certvic.providers.internvl
    import certvic.providers.llava_onevision
    import certvic.providers.qwen_vl

    assert certvic.providers.qwen_vl.QwenVLProvider
