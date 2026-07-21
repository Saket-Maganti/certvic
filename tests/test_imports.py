def test_imports():
    import certvic
    from certvic.schema import TaskItem

    assert certvic.__version__
    assert TaskItem
