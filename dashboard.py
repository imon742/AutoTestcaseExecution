"""Primary launcher for the local Ollama QA agent; legacy diagnostics are preserved."""
from local_qa.app import main

# Compatibility only for previously generated, user-reviewed legacy tests.
def replay_exported(*args, **kwargs):
    from legacy_dashboard import replay_exported as replay
    return replay(*args, **kwargs)

if __name__ == '__main__':
    main()
