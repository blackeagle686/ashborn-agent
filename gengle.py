def scaled_dot_product_attention(query, key, value):
    """
    Compute the scaled dot-product attention.

    Args:
        query (torch.Tensor): Query tensor of shape (batch_size, num_heads, seq_len_q, d_k)
        key (torch.Tensor): Key tensor of shape (batch_size, num_heads, seq_len_k, d_k)
        value (torch.Tensor): Value tensor of shape (batch_size, num_heads, seq_len_v, d_v)

    Returns:
        torch.Tensor: Output tensor of shape (batch_size, num_heads, seq_len_q, d_v)
    """
    # Compute the dot product between query and key
    matmul_qk = torch.matmul(query, key.transpose(-2, -1))  # (..., seq_len_q, seq_len_k)

    # Scale matmul_qk by sqrt(d_k)
    dk = query.size(-1)  # d_k is the last dimension of the query tensor
    scaled_attention_logits = matmul_qk / math.sqrt(dk)

    # Apply softmax to get attention weights
    attention_weights = F.softmax(scaled_attention_logits, dim=-1)  # (..., seq_len_q, seq_len_k)

    # Multiply attention weights with values
    output = torch.matmul(attention_weights, value)  # (..., seq_len_q, d_v)

    return output, attention_weights


# Example usage and demonstration
def demonstrate_attention():
    """Demonstrate the scaled dot-product attention mechanism with a simple example."""
    import torch
    import torch.nn.functional as F
    import math

    # Set random seed for reproducibility
    torch.manual_seed(42)

    # Define dimensions
    batch_size = 2
    num_heads = 8
    seq_length = 60  # Sequence length
    d_model = 512   # Model dimension
    d_k = d_model // num_heads  # Dimension per head
    d_v = d_model // num_heads  # Dimension per head

    # Generate random tensors for query, key, and value
    query = torch.randn(batch_size, num_heads, seq_length, d_k)
    key = torch.randn(batch_size, num_heads, seq_length, d_k)
    value = torch.randn(batch_size, num_heads, seq_length, d_v)

    # Compute attention
    output, attention_weights = scaled_dot_product_attention(query, key, value)

    print("Query shape:", query.shape)
    print("Key shape:", key.shape)
    print("Value shape:", value.shape)
    print("Output shape:", output.shape)
    print("Attention weights shape:", attention_weights.shape)
    print("\nExample output (first element, first head, first token):")
    print(output[0, 0, 0])

if __name__ == "__main__":
    demonstrate_attention()
