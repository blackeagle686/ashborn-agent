# Entrypoint for microservice
from flash_attn import flash_attn_qkvpacked_func
import torch
import torch.nn as nn
import torch.nn.functional as F

class FlashAttention(nn.Module):
    def __init__(self, embed_dim, num_heads, dropout=0.1):
        super().__init__()
        assert embed_dim % num_heads == 0, "embed_dim must be divisible by num_heads"
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.head_dim = embed_dim // num_heads
        self.dropout = dropout

        self.qkv_proj = nn.Linear(embed_dim, 3 * embed_dim)
        self.out_proj = nn.Linear(embed_dim, embed_dim)

    def forward(self, x, mask=None):
        # x: (batch_size, seqlen, embed_dim)
        B, T, C = x.shape
        qkv = self.qkv_proj(x)  # (B, T, 3*C)
        qkv = qkv.reshape(B, T, 3, self.num_heads, self.head_dim).transpose(1, 2)  # (B, 3, T, H, D)
        q, k, v = qkv.unbind(dim=1)  # each: (B, T, H, D)
        
        # Pack QKV for flash attention
        out = flash_attn_qkvpacked_func(qkv.permute(0, 2, 3, 1, 4), dropout_p=self.dropout, softmax_scale=None, causal=False)
        out = out.transpose(1, 2).reshape(B, T, C)
        return self.out_proj(out)

class TransformerLayer(nn.Module):
    def __init__(self, embed_dim, num_heads, ff_hidden_mult=4, dropout=0.1):
        super().__init__()
        self.attn = FlashAttention(embed_dim, num_heads, dropout)
        self.norm1 = nn.LayerNorm(embed_dim)
        self.norm2 = nn.LayerNorm(embed_dim)
        self.ff = nn.Sequential(
            nn.Linear(embed_dim, ff_hidden_mult * embed_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(ff_hidden_mult * embed_dim, embed_dim),
            nn.Dropout(dropout)
        )

    def forward(self, x, mask=None):
        attn_out = self.attn(self.norm1(x), mask=mask)
        x = x + attn_out
        ff_out = self.ff(self.norm2(x))
        x = x + ff_out
        return x

class SimpleTransformer(nn.Module):
    def __init__(self, vocab_size, embed_dim, num_heads, num_layers, max_seq_len=512, dropout=0.1):
        super().__init__()
        self.token_emb = nn.Embedding(vocab_size, embed_dim)
        self.pos_emb = nn.Parameter(torch.zeros(1, max_seq_len, embed_dim))
        self.layers = nn.ModuleList([TransformerLayer(embed_dim, num_heads, dropout=dropout) for _ in range(num_layers)])
        self.norm = nn.LayerNorm(embed_dim)
        self.head = nn.Linear(embed_dim, vocab_size)
        self.max_seq_len = max_seq_len

    def forward(self, x, mask=None):
        B, T = x.shape
        x = self.token_emb(x) + self.pos_emb[:, :T, :]  # (B, T, embed_dim)
        for layer in self.layers:
            x = layer(x, mask=mask)
        x = self.norm(x)
        logits = self.head(x)  # (B, T, vocab_size)
        return logits

# Example usage and test
def main():
    model = SimpleTransformer(vocab_size=10000, embed_dim=512, num_heads=8, num_layers=6)
    x = torch.randint(0, 10000, (2, 128))  # batch of 2 sequences of length 128
    logits = model(x)
    print(logits.shape)  # Should print: torch.Size([2, 128, 10000])

if __name__ == '__main__':
    main()