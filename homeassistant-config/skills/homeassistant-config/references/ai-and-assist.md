# AI Tasks, Assist and LLM Tools (Home Assistant 2026)

Actions and triggers for AI tasks, voice satellites and LLM integrations.

## Outdated → current

| Outdated | Current | Since |
|---|---|---|
| `conversation.process` + parsing free text to get data | `ai_task.generate_data` with a `structure` | 2025.8 |
| Reading the answer from `response.speech` for AI tasks | `result.data` (or `result.data.<field>` with a structure) | 2025.8 |
| TTS-only announcements | `assist_satellite.announce`, `start_conversation`, `ask_question` | 2025.2 / 2025.7 |
| Tool names `GetLiveContext`, `HassTurnOn` in custom prompts | `homeassistant__GetLiveContext`, `intent__HassTurnOn` | 2026.9 |
| MCP server set up by adding the integration by hand | Settings → System → AI → Model Context Protocol card | 2026.10 |

## `ai_task.generate_data`

Needs an AI Task entity (added as a sub-entry of an AI integration such as
OpenAI, Anthropic, Google Gemini or Ollama). With a default AI Task entity set
in Settings → System → General, `entity_id` can be left out, which helps when
sharing blueprints.

```yaml
- action: ai_task.generate_data
  data:
    task_name: "Front door visitor"
    instructions: >-
      Look at the image from the front door camera. Say whether a person
      is there and describe them in one short sentence.
    entity_id: ai_task.openai_ai_task      # optional with a default set
    structure:
      person_present:
        description: "True if a person is visible"
        required: true
        selector:
          boolean:
      description:
        description: "One sentence about the visitor"
        selector:
          text:
    attachments:
      - media_content_id: media-source://camera/camera.front_door
        media_content_type: image/jpeg
  response_variable: result
- if:
    - condition: template
      value_template: "{{ result.data.person_present }}"
  then:
    - action: notify.mobile_app_anna_phone
      data:
        title: "Someone at the door"
        message: "{{ result.data.description }}"
```

- `task_name` labels the task; `instructions` is the prompt. Without
  `structure`, `result.data` is a string. With it, each field has
  `description`, `required` and a `selector` (its type), and
  `result.data.<field>` holds the value.
- `attachments`: `media_content_id` + `media_content_type`. Cameras use
  `media-source://camera/<entity_id>`; images from the media browser use their
  media-source URI.
- Check `result.data` before acting on it: models can return empty values.

### AI task in a template sensor

Put the call in the `actions:` of a trigger-based template entity and set the
state from `result.data` (example in `templates.md` and in the 2025.8 release
notes). Each call costs tokens or local GPU time: trigger on a real event
(motion, doorbell) rather than a short `time_pattern`.

## `ai_task.generate_image` (2025.10)

```yaml
- action: ai_task.generate_image
  data:
    task_name: "Weather picture"
    instructions: "A small watercolour of {{ states('weather.home') }} weather over a city."
    entity_id: ai_task.openai_ai_task
  response_variable: image
- action: notify.mobile_app_anna_phone
  data:
    message: "Today's picture"
    data:
      image: "{{ image.url }}"
```

The URL of the image is in `<response_variable>.url`. Not every AI integration
can generate images; check the integration's docs.

## Voice satellites

### `assist_satellite.announce`

```yaml
- action: assist_satellite.announce
  target:
    entity_id: assist_satellite.kitchen
  data:
    message: "The washing machine is done."
    preannounce: true
```

### `assist_satellite.start_conversation`

Says the first message and then listens; the reply goes to the satellite's
conversation agent (an LLM agent works best).

```yaml
- action: assist_satellite.start_conversation
  target:
    entity_id: assist_satellite.living_room
  data:
    start_message: "The garage has been open for 30 minutes. Should I close it?"
    extra_system_prompt: "If the user agrees, close cover.garage."
```

### `assist_satellite.ask_question` (2025.7)

Asks a question and matches the reply against sentence templates, locally.

```yaml
- action: assist_satellite.ask_question
  data:
    entity_id: assist_satellite.living_room
    question: "What kind of music do you want?"
    preannounce: true
    answers:
      - id: genre
        sentences:
          - "genre {genre}"
      - id: stop
        sentences:
          - "nothing"
          - "never mind"
  response_variable: answer
- choose:
    - conditions: "{{ answer.id == 'genre' }}"
      sequence:
        - action: music_assistant.play_media
          target:
            entity_id: media_player.living_room
          data:
            media_id: "{{ answer.slots.genre }}"
            media_type: playlist
  default:
    - action: assist_satellite.announce
      target:
        entity_id: assist_satellite.living_room
      data:
        message: "Okay, no music."
```

Branch on `answer.id`; read wildcards from `answer.slots.<name>`. If nothing
matched, `answer.id` is none, so add a `default:` branch.

## Conversation trigger

Custom sentences without an LLM. `{name}` is a wildcard slot.

```yaml
- id: "voice_find_phone"
  alias: "Voice - find my phone"
  triggers:
    - trigger: conversation
      command:
        - "find my phone"
        - "where is [my] {device} phone"
  actions:
    - action: notify.mobile_app_anna_phone
      data:
        message: "request_location_update"   # Android companion app command
    - set_conversation_response: "Okay, ringing the phone."
```

- `trigger.sentence` has the text; `trigger.slots.<name>` the wildcard values.
- `[word]` is optional, `(a|b)` an alternative.
- The response must come from `set_conversation_response`; it may be a
  template.

## LLM tools and prompts (2026.9)

LLM tool names are prefixed with the domain of the integration that provides
them. Update custom prompts that name tools:

| Before 2026.9 | Since 2026.9 |
|---|---|
| `GetLiveContext` | `homeassistant__GetLiveContext` |
| `HassTurnOn` | `intent__HassTurnOn` |

Other intents follow the same `intent__` pattern; tools from other LLM APIs
use their own domain prefix.

Since 2026.11 an LLM API is only available after an admin attaches it to a
conversation agent or to the MCP server, and an AI conversation can only be
continued by the user who started it. The Assist API can search actions, call
them, list and reload integrations, and read logs (admin only), so give agents
only the access you need.

## MCP

- **MCP server** (`mcp_server`, 2025.2): lets external AI apps (Claude,
  ChatGPT, Cursor…) control Home Assistant through the exposed entities and
  LLM APIs. Since 2026.10 set it up in Settings → System → AI → Model Context
  Protocol; the card lists the URLs to paste into the app. New setups expose
  everything, including future additions, and only allow admin accounts.
  Since 2026.11 it can be limited to read-only tools.
- **MCP client** (`mcp`, 2025.2): connects Home Assistant's conversation
  agents to external MCP servers as extra tools. Since 2026.10, apps that run
  their own MCP server are discovered automatically.
- Which entities an agent can see is still set in Settings → Voice assistants
  → Expose.

## Checklist

- `response_variable` on every `ai_task.*` and `ask_question` call; read
  `result.data`, `answer.id`, `image.url`.
- Guard AI output with a condition before acting on it.
- Prompts use the 2026.9 tool prefixes; MCP stays read-only unless needed.
