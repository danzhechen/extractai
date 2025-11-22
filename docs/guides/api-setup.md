# API Key Setup Guide

This guide shows you how to set up your API key for LLM-based table extraction.

## Quick Start

### Google Gemini API (Recommended - FREE Tier Available)

1. **Get your API key**:
   ```
   Your API Key: YOUR_API_KEY_HERE
   ```

2. **Set as environment variable** (recommended for security):
   ```bash
   export PDF_READER_LLM_API_KEY="YOUR_API_KEY_HERE"
   ```

3. **Make it permanent** (add to your shell profile):
   ```bash
   # For bash users
   echo 'export PDF_READER_LLM_API_KEY="YOUR_API_KEY_HERE"' >> ~/.bashrc
   source ~/.bashrc

   # For zsh users (macOS default)
   echo 'export PDF_READER_LLM_API_KEY="YOUR_API_KEY_HERE"' >> ~/.zshrc
   source ~/.zshrc
   ```

4. **Test it works**:
   ```bash
   python -m pdf_reader extract --input sample/sample.pdf --preset smart
   ```

---

## Alternative: OpenAI API (GPT-4o)

If you prefer using OpenAI's GPT-4o instead of Gemini:

1. **Get your OpenAI API key** from https://platform.openai.com/api-keys

2. **Set environment variable**:
   ```bash
   export PDF_READER_LLM_API_KEY="sk-your-openai-key-here"
   ```

3. **Use with OpenAI provider**:
   ```bash
   python -m pdf_reader extract \
     --input document.pdf \
     --llm-provider openai \
     --llm-model gpt-4o
   ```

---

## Configuration File Method

You can also set the API key in a config file (less secure, not recommended for production):

**Create `config.yaml`**:
```yaml
# API Configuration
llm_api_key: "YOUR_API_KEY_HERE"
llm_provider: google
llm_model: gemini-2.5-pro

# Other settings
extraction_preset: smart
dpi: 200
enable_debug_artifacts: false
```

**Use with CLI**:
```bash
python -m pdf_reader extract --input document.pdf --config config.yaml
```

⚠️ **Security Warning**: Never commit config files with API keys to version control! Add `config.yaml` to your `.gitignore`.

---

## Verification

### Check if API key is set:
```bash
echo $PDF_READER_LLM_API_KEY
# Should output: YOUR_API_KEY_HERE
```

### Test extraction:
```bash
# Smart preset (FREE Gemini 2.5 Pro)
python -m pdf_reader extract \
  --input sample/sample.pdf \
  --preset smart \
  --debug

# Check the output for:
# - "Starting LLM extraction" log message
# - Cost tracking in RunStats
# - Model used: gemini-2.5-pro
```

### Troubleshooting:

**Error: "LLM API key required for end-to-end extraction"**
- Check environment variable is set: `echo $PDF_READER_LLM_API_KEY`
- Try setting it again in current shell
- Make sure you sourced your shell profile

**Error: "API key invalid"**
- Verify API key is correct
- Check Gemini API is enabled in Google Cloud Console
- Try generating a new API key

**Error: "Rate limit exceeded"**
- Gemini 2.5 Pro has generous free tier limits
- Wait a few minutes and try again
- Consider using `--preset offline` for temporary workaround

---

## Cost Management

### Monitor your usage:
```bash
# After extraction, check RunStats for cost info
python -m pdf_reader extract --input document.pdf --preset smart

# Output will show:
# - llm_tokens_input: 1234
# - llm_tokens_output: 567
# - estimated_cost_usd: 0.00  (FREE with Gemini 2.5 Pro!)
# - models_used: ['gemini-2.5-pro']
```

### Cost presets:
- **`smart`**: FREE Gemini 2.5 Pro (~$0 per 1000 pages)
- **`premium`**: PAID Gemini 3.0 Pro (~$1.25 per 1000 pages)
- **`offline`**: No API, heuristics only ($0)

### Prevent unexpected costs:
```yaml
# In config file, set conservative escalation
enable_auto_escalation: false  # Don't auto-upgrade to paid models
```

---

## Next Steps

- See [Getting Started Guide](getting-started.md) for usage examples
- See [Configuration Guide](configuration.md) for advanced settings
- See [Cost Analysis](../prd.md#122-extraction-strategies-new-architecture) for pricing details


