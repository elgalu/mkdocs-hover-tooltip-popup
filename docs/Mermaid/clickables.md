# Clickables

```mermaid
flowchart LR
    A-->B
    B-->C
    C-->D
    click A callback "Tooltip for a callback"
    click B "https://www.github.com" "This is a tooltip for a link"
    click C call callback() "Tooltip for a callback"
    click D href "https://www.github.com" "This is a tooltip for a link"
```

This page shows Mermaid's native `click` directive. For the plugin's own per-node
Markdown popups, see [Hover Tooltip Popups](tooltips.md).
