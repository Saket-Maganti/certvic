"""Compatibility wrapper for the evaluation runner."""

from certvic.eval.run_eval import main, run_eval

__all__ = ["main", "run_eval"]

if __name__ == "__main__":
    main()
