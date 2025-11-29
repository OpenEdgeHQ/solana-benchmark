"""
Parameter Generator - Generate random values for question parameters

This module provides functionality to generate random values for different
parameter types within reasonable and realistic ranges.
"""

import random
from typing import Dict, Any, List
from decimal import Decimal
from solders.keypair import Keypair

class ParameterGenerator:
    """Generate random parameter values based on configuration"""
    
    def __init__(self, seed: int = None):
        """
        Initialize parameter generator
        
        Args:
            seed: Random seed for reproducibility (optional)
        """
        if seed is not None:
            random.seed(seed)
    
    def generate_parameters(self, param_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate random values for all parameters based on configuration
        
        Args:
            param_config: Parameter configuration dictionary
            
        Returns:
            Dictionary of parameter names to generated values
        """
        result = {}
        
        for param_name, config in param_config.items():
            param_type = config.get('type')
            generation_config = config.get('generation', {})
            
            if param_type == 'address':
                result[param_name] = self._generate_address(generation_config)
            elif param_type == 'number':
                result[param_name] = self._generate_number(generation_config)
            elif param_type == 'string':
                result[param_name] = self._generate_string(generation_config)
            elif param_type == 'integer':
                result[param_name] = self._generate_integer(generation_config)
            elif param_type == 'boolean':
                result[param_name] = self._generate_boolean(generation_config)
            else:
                raise ValueError(f"Unsupported parameter type: {param_type}")
        
        return result
    
    def _generate_address(self, config: Dict[str, Any]) -> str:
        """
        Generate a random Solana address
        
        Args:
            config: Generation configuration
                - method: 'random' or 'from_list'
                - addresses: List of addresses (if method is 'from_list')

        Returns:
            Solana address
        """
        method = config.get('method', 'random')

        if method == 'fixed':
            # Return fixed address value
            return config.get('value', '')
        if method == 'random':
            # Generate a new random account
            return str(Keypair().pubkey())
        elif method == 'from_list':
            # Choose from predefined list
            addresses = config.get('addresses', [])
            if not addresses:
                raise ValueError("No addresses provided in configuration")
            return random.choice(addresses)
        else:
            raise ValueError(f"Unsupported address generation method: {method}")
    
    def _generate_number(self, config: Dict[str, Any]) -> float:
        """
        Generate a number (float or int)
        
        Args:
            config: Generation configuration
                - method: 'fixed' or 'random' (default: 'random')
                - value: Fixed value if method is 'fixed'
                - min: Minimum value (default: 0.001)
                - max: Maximum value (default: 1.0)
                - decimals: Number of decimal places (default: 3)
                - unit: Unit of measurement (e.g., 'BNB', 'ETH')
                
        Returns:
            Number value (float or int)
        """
        from decimal import Decimal, ROUND_HALF_UP
        
        method = config.get('method', 'random')
        
        if method == 'fixed':
            return config.get('value', 0)
        
        # Random generation
        min_val = config.get('min', 0.001)
        max_val = config.get('max', 1.0)
        decimals = config.get('decimals', 3)
        
        # Generate random value using Decimal for precision
        # This avoids floating point precision issues when converting to wei
        min_decimal = Decimal(str(min_val))
        max_decimal = Decimal(str(max_val))
        
        # Generate random decimal
        random_decimal = min_decimal + (max_decimal - min_decimal) * Decimal(str(random.random()))
        
        # Round to specified decimals
        quantize_value = Decimal(10) ** -decimals
        rounded = random_decimal.quantize(quantize_value, rounding=ROUND_HALF_UP)
        
        # Convert back to float
        return float(rounded)
    
    def _generate_integer(self, config: Dict[str, Any]) -> int:
        """
        Generate a random integer
        
        Args:
            config: Generation configuration
                - method: 'random', 'fixed', or 'from_list'
                - value: Fixed value (if method is 'fixed')
                - values: List of values to choose from (if method is 'from_list')
                - min: Minimum value (default: 1)
                - max: Maximum value (default: 100)
                
        Returns:
            Random integer value, fixed value, or value from list
        """
        method = config.get('method', 'random')
        
        if method == 'fixed':
            return config.get('value', 0)
        
        if method == 'from_list':
            values = config.get('values', [])
            if not values:
                raise ValueError("from_list method requires 'values' list")
            return random.choice(values)
        
        # Random method
        min_val = config.get('min', 1)
        max_val = config.get('max', 100)
        
        return random.randint(min_val, max_val)
    
    def _generate_string(self, config: Dict[str, Any]) -> str:
        """
        Generate a random string
        
        Args:
            config: Generation configuration
                - method: 'from_list' or 'random'
                - values: List of possible values (if method is 'from_list')
                - length: String length (if method is 'random')
                - charset: Character set (if method is 'random')
                
        Returns:
            Random string value
        """
        method = config.get('method', 'from_list')
        
        if method == 'fixed':
            # Return fixed string value
            return config.get('value', '')
        elif method == 'from_list':
            values = config.get('values', [])
            if not values:
                raise ValueError("No values provided in configuration")
            return random.choice(values)
        elif method == 'random':
            length = config.get('length', 10)
            charset = config.get('charset', 'alphanumeric')
            
            if charset == 'alphanumeric':
                import string
                chars = string.ascii_letters + string.digits
            elif charset == 'alphanumeric_space':
                import string
                chars = string.ascii_letters + string.digits + ' '
            elif charset == 'alpha':
                import string
                chars = string.ascii_letters
            elif charset == 'numeric':
                import string
                chars = string.digits
            else:
                chars = charset
            
            return ''.join(random.choice(chars) for _ in range(length))
        else:
            raise ValueError(f"Unsupported string generation method: {method}")
    
    def _generate_boolean(self, config: Dict[str, Any]) -> bool:
        """
        Generate a boolean value
        
        Args:
            config: Generation configuration
                - method: 'fixed' or 'random' (default: 'random')
                - value: Fixed value if method is 'fixed'
                - probability: Probability of True (default: 0.5) if method is 'random'
                
        Returns:
            Boolean value
        """
        method = config.get('method', 'random')
        
        if method == 'fixed':
            return config.get('value', False)
        else:
            # Random generation
            probability = config.get('probability', 0.5)
            return random.random() < probability

def format_parameter_value(value: Any, param_config: Dict[str, Any]) -> str:
    """
    Format a parameter value for display in natural language prompts
    
    Args:
        value: The parameter value
        param_config: Parameter configuration
        
    Returns:
        Formatted string representation
    """
    param_type = param_config.get('type')
    unit = param_config.get('unit', '')
    
    if param_type == 'number':
        # Format number with unit
        if unit:
            return f"{value} {unit}"
        return str(value)
    elif param_type == 'address':
        # Address as-is
        return str(value)
    elif param_type == 'integer':
        # Integer with optional unit
        if unit:
            return f"{value} {unit}"
        return str(value)
    else:
        return str(value)

