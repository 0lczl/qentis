"""Shared interface and scientific-chart themes."""
THEMES = {
    "Dark": {"background": "#0a0a0a", "surface": "#121218", "surface-raised": "#1b1a24",
             "border": "#34313f", "control-border": "#777180", "text": "#f4f1fa", "muted": "#b9b2c8",
             "accent": "#b89aff", "reference": "#68d9d1", "random": "#f0bd69", "brand-bright": "#6e2eda"},
    "Light": {"background": "#f7f6fa", "surface": "#ffffff", "surface-raised": "#eeebf3",
              "border": "#d5cedf", "control-border": "#80758f", "text": "#20182d", "muted": "#60566e",
              "accent": "#6735af", "reference": "#087870", "random": "#946009", "brand-bright": "#6e2eda"},
}


def palette(theme="Dark"):
    return THEMES[theme]
