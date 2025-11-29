# Claude Code Plugin Marketplace

A curated collection of Claude Code plugins for Home Assistant, ESPHome, and smart home automation.

## Available Plugins

| Plugin | Description | Version |
|--------|-------------|---------|
| [homeassistant-config](./homeassistant-config) | Create, modify, and troubleshoot Home Assistant configuration files | 1.0.1 |

## Installation

Plugins are installed using Claude Code's `/plugin` command (now in public beta).

### Option 1: Interactive Installation (Recommended)

1. **Add the marketplace** - In Claude Code, run:
   ```
   /plugin marketplace add ESJavadex/claude-homeassistant-plugins
   ```

2. **Browse and install** - Run `/plugin` and select "Browse Plugins" to view available plugins with descriptions and install options.

### Option 2: Direct Installation

After adding the marketplace, install plugins directly:

```
/plugin install homeassistant-config@claude-homeassistant-plugins
```

### Option 3: Using npx CLI

Install without manually adding the marketplace first:

```bash
npx claude-plugins install @ESJavadex/claude-homeassistant-plugins/homeassistant-config
```

### Managing Plugins

| Command | Description |
|---------|-------------|
| `/plugin` | Open plugin menu to browse/manage |
| `/plugin enable plugin-name@marketplace` | Enable a disabled plugin |
| `/plugin disable plugin-name@marketplace` | Disable without removing |
| `/plugin uninstall plugin-name@marketplace` | Remove completely |

### Verify Installation

After installation, run `/help` to confirm new commands appear, or use `/plugin` → "Manage Plugins" to review installed features.

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

- [Claude Code Plugins Documentation](https://code.claude.com/docs/en/plugins)
- [Plugin Marketplaces Guide](https://code.claude.com/docs/en/plugin-marketplaces)
- [Anthropic Blog: Claude Code Plugins](https://claude.com/blog/claude-code-plugins)
- [Home Assistant](https://www.home-assistant.io/)
- [ESPHome](https://esphome.io/)
