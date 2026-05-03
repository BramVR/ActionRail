# ActionRail Examples

Built-in examples load from JSON presets in `../presets/`.

- `transform_stack.json` is the reference `M/T/R/S + K` vertical viewport rail. Local visual references can live in ignored `../research/` when present.
- `horizontal_tools.json` is a horizontal rail example used to prove layout metadata without widget-code changes.

Use `actionrail.show_example("transform_stack")` or `actionrail.show_example("horizontal_tools")` inside Maya to render them.

Python callers can also build a rail without adding a bundled preset:

```python
import actionrail

spec = actionrail.StackSpec(
    id="custom_tools",
    layout=actionrail.RailLayout(anchor="viewport.bottom.center", orientation="horizontal"),
    items=(
        actionrail.StackItem(type="button", id="custom_tools.key", label="K", action="maya.anim.set_key"),
    ),
)
actionrail.show_spec(spec)
```
