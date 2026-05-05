import importlib.util
import sys
from pathlib import Path


def default_plugin_dirs():
    return [
        Path.cwd() / "plugins",
        Path.home() / ".yunji" / "plugins",
    ]


class PluginManager:
    """Minimal plugin loader.

    A plugin is a .py file with an optional activate(editor) function.
    """

    def __init__(self, editor, plugin_dirs=None):
        self.editor = editor
        self.plugin_dirs = [Path(p) for p in (plugin_dirs or default_plugin_dirs())]
        self.plugins = []
        self.errors = []

    def discover(self):
        plugin_files = []
        for directory in self.plugin_dirs:
            if directory.is_dir():
                plugin_files.extend(sorted(directory.glob("*.py")))
        return plugin_files

    def load_all(self):
        self.plugins.clear()
        self.errors.clear()
        for plugin_file in self.discover():
            self.load_plugin(plugin_file)
        return self.plugins

    def load_plugin(self, plugin_file):
        plugin_file = Path(plugin_file)
        module_name = f"yunji_plugin_{plugin_file.stem}_{abs(hash(plugin_file))}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            if spec is None or spec.loader is None:
                raise ImportError(f"无法创建插件 spec: {plugin_file}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            activate = getattr(module, "activate", None)
            if callable(activate):
                activate(self.editor)
            self.plugins.append(module)
            return module
        except Exception as exc:
            self.errors.append((str(plugin_file), exc))
            return None

    def summary(self):
        return len(self.plugins), len(self.errors)
