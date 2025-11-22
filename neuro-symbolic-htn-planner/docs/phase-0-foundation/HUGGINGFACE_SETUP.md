# Hugging Face Integration Setup Guide

## 🚀 Quick Setup (3 minutes)

### Step 1: Get Your Free API Token

1. Go to **https://huggingface.co/settings/tokens**
2. If you don't have an account, click "Sign Up" (free!)
3. Once logged in, click **"New token"**
4. Give it a name like "HTN-Planner"
5. Set permissions to **"Read"** (we only need to run models, not upload)
6. Click **"Generate"**
7. **Copy the token** (starts with `hf_...`)

### Step 2: Set Your Environment Variable

Add to your `~/.zshrc`:

```bash
export HF_TOKEN="hf_your_token_here"
```

Then reload:
```bash
source ~/.zshrc
```

### Step 3: Test It

```bash
cd neuro-symbolic-htn-planner
python test_huggingface.py
```

---

## 📊 Available Models

### Small Models (Fast, 1-3 seconds)
- **meta-llama/Llama-3.2-3B-Instruct** ← Recommended default
- **microsoft/Phi-3-mini-4k-instruct**

### Medium Models (Balanced, 3-8 seconds)
- **mistralai/Mistral-7B-Instruct-v0.3** ← Best reasoning
- **Qwen/Qwen2.5-7B-Instruct** ← Strong reasoning
- **meta-llama/Llama-3.1-8B-Instruct**

### Large Models (High Quality, 10-30 seconds)
- **meta-llama/Llama-3.1-70B-Instruct** ← Best quality
- **mistralai/Mixtral-8x7B-Instruct-v0.1** ← MoE efficient

---

## ✅ Advantages vs Mistral/Eden

| Feature | Hugging Face | Mistral | Eden |
|---------|--------------|---------|------|
| **Cost** | ✅ Free tier | ⚠️ Rate limited | ⚠️ Limited |
| **Models** | ✅ 1000+ options | ❌ 1 model | ❌ 1 provider |
| **Quality** | ✅ High (Llama, Mistral, Qwen) | ✅ Good | ❌ Unreliable |
| **Speed** | ✅ 2-8s (medium models) | ✅ 5-9s | ✅ Fast but gibberish |
| **Reliability** | ✅ Stable | ⚠️ Rate limits | ❌ Random responses |
| **Open Source** | ✅ Yes | ✅ Yes | ❌ Proprietary wrapper |

---

## 🎯 Usage Example

```python
from llm.huggingface_client import HuggingFaceClient
from llm.local_llm_interface import LLMConfig

# Initialize client
client = HuggingFaceClient(
    config=LLMConfig(
        model_name="meta-llama/Llama-3.2-3B-Instruct",
        temperature=0.7,
        max_tokens=500
    )
)

# Check availability
if client.is_available():
    # Generate HTN decomposition
    response = client.generate(
        prompt="Decompose: make_coffee into subtasks",
        system_prompt="You are an HTN planning expert."
    )
    print(response.content)
```

---

## 🔧 Integration with Strategic Decomposition Engine

The Hugging Face client integrates seamlessly:

```python
from algorithms.strategic_decomposition import StrategicDecompositionEngine
from llm.huggingface_client import HuggingFaceClient

engine = StrategicDecompositionEngine()

# Add Llama 3.2 (fast, good quality)
llama_client = HuggingFaceClient(
    config=LLMConfig(model_name="meta-llama/Llama-3.2-3B-Instruct")
)
engine.add_llm_provider("llama_3.2_3b", llama_client)

# Add Mistral 7B (best reasoning)
mistral_client = HuggingFaceClient(
    config=LLMConfig(model_name="mistralai/Mistral-7B-Instruct-v0.3")
)
engine.add_llm_provider("mistral_7b_hf", mistral_client)

# Add Qwen 2.5 (strong reasoning)
qwen_client = HuggingFaceClient(
    config=LLMConfig(model_name="Qwen/Qwen2.5-7B-Instruct")
)
engine.add_llm_provider("qwen_2.5_7b", qwen_client)
```

---

## ⚡ Rate Limits

Hugging Face Free Tier (Serverless Inference):
- **Rate Limit**: ~1000 requests/day per model
- **Concurrent**: 1-3 requests at a time
- **Timeout**: Models may take 10-20s to "wake up" first time

**Pro Tip**: Spread requests across multiple models to avoid rate limits!

---

## 🎉 Why This is Better

1. **Multiple Models**: Not locked into one provider
2. **Open Source**: All models are fully open (Llama, Mistral, Qwen, Phi)
3. **Free**: No credit card required, generous free tier
4. **Quality**: Better than Eden, more reliable than Mistral API
5. **Flexibility**: Can switch models based on task complexity

---

## 🚨 Troubleshooting

### "Model is loading" error
- First request may take 10-20 seconds as model loads
- Just retry after a few seconds

### Rate limit exceeded
- Switch to a different model
- OR wait a few minutes
- OR use multiple models in rotation

### Authentication error
- Check your token is set: `echo $HF_TOKEN`
- Verify token starts with `hf_`
- Make sure token has "Read" permissions

---

## 📚 Next Steps

After setup:
1. ✅ Run `python test_huggingface.py`
2. ✅ Integrate with Strategic Decomposition Engine
3. ✅ Test on household tasks benchmark
4. ✅ Compare with existing 5 providers
5. ✅ Proceed with multi-agent architecture

---

## 🔗 Resources

- Token Creation: https://huggingface.co/settings/tokens
- Model Hub: https://huggingface.co/models
- Inference API Docs: https://huggingface.co/docs/api-inference
- Best Models for Planning: https://huggingface.co/spaces/lmsys/chatbot-arena-leaderboard

---

**Status**: Ready to replace Mistral and Eden with high-quality open-source models! 🎯
