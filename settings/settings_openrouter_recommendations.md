# Settings Tab Improvements for OpenRouter

## Current State
- All models use OpenRouter API (`openrouter.ai/api/v1`)
- Single API key provides access to 200+ models
- Current UI still shows options for multiple providers (confusing)

## Recommended Changes

### 1. **Simplified API Key Section**

**BEFORE:**
```
API Keys Management
├── OPENAI_API_KEY
├── DEEPSEEK_API_KEY
├── GEMINI_API_KEY
├── OPENROUTER_API_KEY ← Only one you need!
├── GROQ_API_KEY
└── Add New API Key
```

**AFTER:**
```
🔑 OpenRouter API Key (Required)
└── Get your key at: openrouter.ai/keys

💡 One key gives you access to 200+ models including:
    • OpenAI (GPT-4, GPT-4o, GPT-3.5)
    • Anthropic (Claude 3.5 Sonnet, Claude 3)
    • Google (Gemini Pro, Gemini Flash)
    • Meta (Llama 3, Llama 2)
    • Mistral, DeepSeek, and many more!

[Advanced: Add other provider keys]  ← Collapsible section for edge cases
```

### 2. **Enhanced Custom Models Section**

Add quick-add buttons for popular OpenRouter models:

```python
st.subheader("🚀 Quick Add Popular Models")

col1, col2, col3 = st.columns(3)

with col1:
    st.write("**💰 Budget Models**")
    if st.button("+ GPT-4o-Mini"):
        add_openrouter_model("GPT-4o-Mini", "openai/gpt-4o-mini")
    if st.button("+ DeepSeek-Chat"):
        add_openrouter_model("DeepSeek-Chat", "deepseek/deepseek-chat")
    if st.button("+ Gemini Flash"):
        add_openrouter_model("Gemini-Flash", "google/gemini-2.0-flash-exp")

with col2:
    st.write("**⚡ Balanced Models**")
    if st.button("+ Claude 3.5 Sonnet"):
        add_openrouter_model("Claude-3.5-Sonnet", "anthropic/claude-3.5-sonnet")
    if st.button("+ GPT-4o"):
        add_openrouter_model("GPT-4o", "openai/gpt-4o")
    if st.button("+ Llama 3.1"):
        add_openrouter_model("Llama-3.1-70B", "meta-llama/llama-3.1-70b-instruct")

with col3:
    st.write("**🎯 Premium Models**")
    if st.button("+ Claude Opus"):
        add_openrouter_model("Claude-Opus", "anthropic/claude-3-opus")
    if st.button("+ GPT-4 Turbo"):
        add_openrouter_model("GPT-4-Turbo", "openai/gpt-4-turbo")
    if st.button("+ Gemini Pro"):
        add_openrouter_model("Gemini-Pro", "google/gemini-pro-1.5")
```

### 3. **Add OpenRouter Model Browser**

```python
st.subheader("📚 Browse OpenRouter Models")

st.info("💡 Visit [OpenRouter Model Catalog](https://openrouter.ai/models) to see all 200+ models with pricing and specs")

# Search/filter models
search = st.text_input("🔍 Search models", placeholder="e.g., claude, gpt, llama")

# Show popular categories
categories = st.multiselect(
    "Filter by category",
    ["Chat", "Code", "Vision", "Free", "Budget (<$1/M tokens)", "Premium"]
)
```

### 4. **Cost Tracker (Nice to Have)**

Since OpenRouter tracks usage per model:

```python
st.subheader("💰 Model Cost Estimates")

cost_table = {
    "Model": ["DeepSeek-Chat", "GPT-4o-Mini", "Claude 3.5 Sonnet", "GPT-4o"],
    "Input ($/1M tokens)": ["$0.14", "$0.15", "$3.00", "$2.50"],
    "Output ($/1M tokens)": ["$0.28", "$0.60", "$15.00", "$10.00"],
    "Best For": ["Budget tasks", "General use", "Complex reasoning", "Multimodal"]
}

st.dataframe(cost_table)
st.caption("💡 Prices from OpenRouter - may vary")
```

### 5. **Streamlined Provider Selection**

Instead of showing all these options:
```python
provider_options = [
    "OpenAIChatCompletionClient",  # Used for OpenRouter
    "AnthropicChatCompletionClient",  # Not needed anymore
    "GroqChatCompletionClient",  # Not needed
    "CohereClient",  # Not needed
    ...
]
```

Simplify to:
```python
# For OpenRouter models (99% of use cases)
provider = "OpenAIChatCompletionClient"
base_url = "https://openrouter.ai/api/v1"
api_provider = "OPENROUTER"

# Show advanced options only if user wants direct API access
with st.expander("🔧 Advanced: Use Direct API (Not Recommended)"):
    st.warning("⚠️ Most users should use OpenRouter for all models")
    provider = st.selectbox("Direct API Client", ["AnthropicChatCompletionClient", "GroqChatCompletionClient", ...])
```

## Implementation Priority

1. **HIGH**: Simplify API key section to highlight OpenRouter
2. **HIGH**: Add quick-add buttons for popular models
3. **MEDIUM**: Add model browser/search
4. **MEDIUM**: Add cost estimates table
5. **LOW**: Keep advanced options collapsed

## Benefits

✅ **Simpler**: One API key instead of managing multiple
✅ **Clearer**: Users understand they get access to all models
✅ **Faster**: Quick-add buttons for common models
✅ **Cheaper**: Easy to compare costs and choose budget models
✅ **Flexible**: Still allows advanced users to use direct APIs if needed

## Code Changes Needed

1. **settings.py** lines 72-157: Simplify API keys section
2. **settings.py** lines 158-283: Add quick-add model buttons
3. **settings.py** line 218-236: Simplify provider selection (default to OpenRouter)
4. Add helper function: `add_openrouter_model(name, model_id, temperature=0.2)`
