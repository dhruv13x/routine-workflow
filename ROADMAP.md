# Strategic ROADMAP.md

A living document balancing **Innovation**, **Stability**, and **Debt**.

---

## 🏁 Phase 0: The Core (Stability & Debt)
**Goal**: Solid foundation. Ensure the house is clean before building the skyscraper.

- [x] **Testing**: Coverage > 95% `[S] [Feat]`
    - *Status*: Achieved (Current: >95%).
- [ ] **Refactoring**: Rename step modules `[L] [Debt]`
    - *Context*: `step1.py`, `step6_5.py` etc. need semantic names (e.g., `clean.py`, `git_ops.py`).
- [ ] **CI/CD**: Strict Type Checking (mypy) `[M] [Debt]`
    - *Context*: Enforce strict typing in `pyproject.toml` or `mypy.ini`.
- [x] **Documentation**: Comprehensive README `[M] [Feat]`
    - *Status*: Gold Standard structure in place.

## 🚀 Phase 1: The Standard (Feature Parity)
**Goal**: Competitiveness. Make it the best-in-class tool.
*Dependencies*: Requires Phase 0 stability.

- [ ] **UX**: Enhanced CLI with `rich` progress for all steps `[M] [Feat]`
    - *Risk*: Low.
- [ ] **Config**: Robust settings management `[M] [Feat]`
    - *Context*: Centralized configuration validation and defaults.
- [ ] **Performance**: Async execution for suitable steps `[L] [Feat]`
    - *Context*: Parallelize independent steps (e.g., linting vs. cache cleaning).

## 🔌 Phase 2: The Ecosystem (Integration)
**Goal**: Interoperability. Play nice with others.
*Dependencies*: Requires Phase 1 API/Config stability.

- [ ] **API**: Expose internal API for programmatic use `[XL] [Feat]`
    - *Risk*: Medium (Requires API design freeze).
- [ ] **Plugins**: Extension system for custom steps `[L] [Feat]`
    - *Context*: Allow users to define custom steps in `pyproject.toml`.
- [ ] **Webhooks**: Notification integration (Slack/Discord) `[M] [Feat]`

## 🔮 Phase 3: The Vision (Innovation)
**Goal**: Market Leader. "God Level" features.
*Dependencies*: Requires Phase 2 extensibility.

- [ ] **AI**: LLM Integration for commit messages `[L] [Feat]`
    - *Risk*: High (R&D).
- [ ] **Cloud**: Official Docker Image & K8s support `[M] [Feat]`
    - *Context*: Containerized workflow for CI/CD consistency.
- [ ] **Analytics**: Predictive Repo Health `[XL] [Feat]`
