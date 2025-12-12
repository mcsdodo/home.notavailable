# Komodo Variables and Secrets Guide

## Sources

- [Variables and Secrets | Komodo](https://komo.do/docs/resources/variables)
- [Advanced Configuration | Komodo](https://komo.do/docs/setup/advanced)
- [Docker Compose | Komodo](https://komo.do/docs/resources/docker-compose)
- [Komodo FAQ, Tips, and Tricks | FoxxMD Blog](https://blog.foxxmd.dev/posts/komodo-tips-tricks/)
- [Stack and Compose Operations | DeepWiki](https://deepwiki.com/moghtech/komodo/5.3-stack-and-compose-operations)
- [GitHub Issue #364 - Variables not found at Deploy](https://github.com/moghtech/komodo/issues/364)
- [Sync Resources Documentation](https://github.com/moghtech/komodo/blob/main/docsite/docs/resources/sync-resources.md)

## How Variable Interpolation Works

### The Flow

1. **Secrets in `core.config.toml`** - Define secrets in the `[secrets]` section:
   ```toml
   [secrets]
   MY_SECRET = "secret_value"
   API_KEY = "abc123"
   ```

2. **Stack config in `komodo.toml`** - Use `[[VAR]]` syntax in the `environment` field:
   ```toml
   [[stack]]
   name = "my-stack"
   [stack.config]
   environment = """
   MY_ENV_VAR=[[MY_SECRET]]
   ANOTHER_VAR=[[API_KEY]]
   """
   ```

3. **Komodo Core interpolates** - Core replaces `[[MY_SECRET]]` with `secret_value`

4. **Periphery writes `.env` file** - The interpolated values are written to `.env` in the `run_directory`

5. **Docker Compose reads `.env`** - Compose files use standard `${VAR}` syntax:
   ```yaml
   services:
     app:
       environment:
         - MY_ENV_VAR=${MY_ENV_VAR}
   ```

### Key Points

From the [Komodo Variables Documentation](https://komo.do/docs/resources/variables):

> "You can interpolate the value into any resource Environment (and most other user configurable inputs) using double brackets around the key."

The syntax is:
```
SOME_ENV_VAR = [[KEY_1]]
```

From [DeepWiki - Stack Operations](https://deepwiki.com/moghtech/komodo/5.3-stack-and-compose-operations):

> "Variable Interpolation: Core interpolates `[[VARIABLE]]` and `[[SECRET]]` placeholders in the environment string."
>
> "Env File Generation: Periphery writes interpolated variables to `<run_directory>/<env_file_path>` (default: .env)."

### Where to Define Secrets

From the [Variables Documentation](https://komo.do/docs/resources/variables):

1. **UI Variables Tab** - Define through Settings page (can mark as secret)

2. **Core Config File** (`core.config.toml`):
   ```toml
   [secrets]
   KEY_1 = "value_1"
   KEY_2 = "value_2"
   ```
   > "Values are NOT exposed by API for ANY user."

3. **Periphery Agent Config** - Only available to resources on that specific server

4. **Dedicated Secret Management** - For enterprise needs (Hashicorp Vault, etc.)

### Common Mistake

From [FoxxMD Blog](https://blog.foxxmd.dev/posts/komodo-tips-tricks/):

> "Environmental Variables/Secrets don't work! This is likely a misunderstanding of how Compose file interpolation and environmental variables in Compose work."

**The `[[VAR]]` syntax does NOT work inside docker-compose.yml files!**

- **Wrong**: Using `[[VAR]]` in docker-compose.yml
- **Correct**: Using `${VAR}` in docker-compose.yml, and `[[VAR]]` in komodo.toml's `environment` field

### Example Configuration

**core.config.toml:**
```toml
[secrets]
TUNNEL_TOKEN = "eyJhIjoiYmI2..."
CF_API_TOKEN = "OwkbvGQ..."
```

**komodo.toml:**
```toml
[[stack]]
name = "cloudflare"
[stack.config]
server_id = "infra"
repo = "user/repo"
run_directory = "stacks/cloudflare"
file_paths = ["docker-compose.yml"]
environment = """
TUNNEL_TOKEN=[[TUNNEL_TOKEN]]
CF_API_TOKEN=[[CF_API_TOKEN]]
"""
```

**docker-compose.yml:**
```yaml
services:
  cloudflare-tunnel:
    image: cloudflare/cloudflared:latest
    environment:
      - TUNNEL_TOKEN=${TUNNEL_TOKEN}
```

### Global Variables

You can also define non-secret variables directly in komodo.toml:

```toml
[[variable]]
name = "CADDY_SERVER_IP"
value = "192.168.0.21"
```

These can be interpolated the same way: `[[CADDY_SERVER_IP]]`

### Known Issues

From [GitHub Issue #364](https://github.com/moghtech/komodo/issues/364):

> There was a bug where variables were interpolated in stages 1 and 2 (global variables and core secrets), but periphery secrets interpolation in stage 5 could fail.

Make sure you're using a recent version of Komodo if experiencing interpolation issues.

## Quick Reference

| Location | Syntax | Example |
|----------|--------|---------|
| `core.config.toml` secrets | `KEY = "value"` | `MY_SECRET = "abc123"` |
| `komodo.toml` variables | `[[variable]]` | `name = "IP"`, `value = "1.2.3.4"` |
| `komodo.toml` environment | `[[KEY]]` | `MY_VAR=[[MY_SECRET]]` |
| `docker-compose.yml` | `${VAR}` | `- MY_VAR=${MY_VAR}` |
