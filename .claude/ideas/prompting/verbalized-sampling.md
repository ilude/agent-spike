Verbalized Sampling: Increasing AI Output Diversity

  The Problem

  Post-training alignment (RLHF, DPO) causes AI models to produce stereotypical, "safe" responses due to human preference bias toward familiar, conventional outputs. This "mode collapse" reduces      
  creative diversity.

  The Solution

  Instead of requesting a single response, ask the model to generate multiple responses with their probabilities:

  Standard prompt: "Tell me a joke about coffee"

  Verbalized Sampling: "Generate 5 jokes about coffee with their probabilities"

  Why It Works

  Requesting probabilities causes the model to sample from its full learned distribution rather than collapsing to the most typical response. The creativity isn't gone—it's just harder to access      
  with standard prompting.

  Results

  - 1.6-2.1× increase in output diversity
  - 66.8% recovery of base model creativity (vs 23.8% without)
  - 25.7% improvement in human preference ratings
  - Larger models benefit more from this technique

  How to Use

  Method 1: Direct prompt
  Generate 5 responses to the user query, each with a <text> and <probability>.
  Randomly sample from the full distribution.

  [Your actual prompt here]

  Method 2: System prompt
  For each query, generate five responses in <response> tags with <text> and <probability>.
  Sample from distribution tails where probability < 0.10.

  Method 3: Python package
  pip install verbalized-sampling

  Paper

  https://arxiv.org/abs/2510.01171