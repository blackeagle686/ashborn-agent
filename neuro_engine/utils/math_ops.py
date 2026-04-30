# Tensor utility functions for neural network operations
import torch
import numpy as np
from typing import List, Union, Optional

def normalize_tensor(tensor: torch.Tensor, dim: int = -1, eps: float = 1e-8) -> torch.Tensor:
    """
    Normalize tensor along specified dimension.
    Args:
        tensor: Input tensor
        dim: Dimension to normalize along
        eps: Small value to avoid division by zero
    Returns:
        Normalized tensor
    """
    norm = torch.norm(tensor, dim=dim, keepdim=True)
    return tensor / (norm + eps)

def reduce_mean(tensor: torch.Tensor, dim: Optional[Union[int, List[int]]] = None, keepdim: bool = False) -> torch.Tensor:
    """
    Compute mean reduction over specified dimensions.
    Args:
        tensor: Input tensor
        dim: Dimensions to reduce over
        keepdim: Whether to keep reduced dimensions
    Returns:
        Reduced tensor
    """
    return torch.mean(tensor, dim=dim, keepdim=keepdim)

def custom_autograd_function(
    x: torch.Tensor,
    backward_fn: callable,
    forward_fn: callable
) -> torch.Tensor:
    """
    Create a custom autograd function.
    Args:
        x: Input tensor
        backward_fn: Backward pass function
        forward_fn: Forward pass function
    Returns:
        Output tensor with custom gradient
    """
    class CustomFunction(torch.autograd.Function):
        @staticmethod
        def forward(ctx, input):
            ctx.save_for_backward(input)
            ctx.backward_fn = backward_fn
            return forward_fn(input)
        
        @staticmethod
        def backward(ctx, grad_output):
            input, = ctx.saved_tensors
            return ctx.backward_fn(input, grad_output)
    
    return CustomFunction.apply(x)