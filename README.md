# Claude Code Plugin Marketplace

A curated collection of Claude Code plugins for Home Assistant, ESPHome, and smart home automation.

## Available Plugins

| Plugin | Description | Version |
|--------|-------------|---------|
| [homeassistant-config](./homeassistant-config) | Create, modify, and troubleshoot Home Assistant configuration files | 1.0.0 |

## Installation

### Add the Marketplace

```bash
claude mcp add-json claude-plugins '{"type":"url","url":"https://raw.githubusercontent.com/YOUR_USERNAME/claude-homeassistant-plugins/main/.claude-plugin/plugin.json"}'
```

### Install Individual Plugins

After adding the marketplace, install plugins:

```bash
# Install Home Assistant Config plugin
cd /path/to/your/project
claude install homeassistant-config
```

Restart Claude Code to activate newly installed plugins.

## Plugin Structure

Each plugin follows a standardized format:

```
plugin-name/
├── .claude-plugin/
│   └── plugin.json          # Plugin metadata
├── skills/
│   └── plugin-name/
│       ├── SKILL.md         # Core instructions
│       ├── references/      # Detailed guides
│       └── examples/        # Working examples
└── README.md                # Plugin documentation
```

## Contributing

We welcome contributions! To add a new plugin:

1. Fork this repository
2. Create a plugin directory following the structure above
3. Include thorough documentation and examples
4. Submit a pull request

### Guidelines

- Follow the established directory structure
- Include a comprehensive SKILL.md
- Provide working examples
- Test your plugin thoroughly

## License

MIT License - See [LICENSE](LICENSE) for details.

## Resources

- [Claude Code Documentation](https://docs.anthropic.com/claude-code)
- [Home Assistant](https://www.home-assistant.io/)
- [ESPHome](https://esphome.io/)
