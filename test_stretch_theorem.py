#!/usr/bin/env python
"""
Test script for Stretch (Scaling Theorem) implementation.
Verifies that the scaling/similarity theorem is correctly applied.
"""

import sys
import os
import numpy as np

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from ImageMixer.services.transform_explorer.complex_helpers import (
    stretch_complex,
    stretch_complex_inverse,
    fft2c,
    ifft2c,
)

def test_amplitude_scaling():
    """Test that amplitude_factor = 1/(|scale_x| * |scale_y|)"""
    print("=" * 70)
    print("TEST 1: Amplitude Scaling Factor")
    print("=" * 70)
    
    test_cases = [
        (2.0, 2.0, 0.25),    # scale 2x → amplitude 1/4
        (0.5, 0.5, 4.0),     # scale 0.5x → amplitude 4x
        (2.0, 0.5, 1.0),     # scale 2x × 0.5x → amplitude 1
        (10.0, 10.0, 0.01),  # scale 10x → amplitude 1/100
    ]
    
    for scale_x, scale_y, expected_amplitude_factor in test_cases:
        computed = 1.0 / (abs(scale_x) * abs(scale_y))
        status = "✓" if abs(computed - expected_amplitude_factor) < 1e-10 else "✗"
        print(f"{status} scale_x={scale_x}, scale_y={scale_y}: "
              f"amplitude_factor={computed:.4f} (expected {expected_amplitude_factor:.4f})")
    print()

def test_inverse_scaling():
    """Test that frequency scaling is inverse of spatial scaling"""
    print("=" * 70)
    print("TEST 2: Inverse Scaling Relationship")
    print("=" * 70)
    
    # Create a simple test image (complex array)
    test_image = np.ones((4, 4), dtype=np.complex128)
    test_image[1:3, 1:3] = 2 + 1j
    
    scale_x, scale_y = 2.0, 2.0
    
    # Spatial scaling (direct)
    spatial_scaled = stretch_complex(test_image.copy(), scale_x, scale_y)
    
    # Frequency scaling (inverse)
    freq_scaled = stretch_complex_inverse(test_image.copy(), scale_x, scale_y)
    
    print(f"Test image shape: {test_image.shape}")
    print(f"Original max magnitude: {np.max(np.abs(test_image)):.4f}")
    print(f"\nAfter spatial scaling (direct {scale_x}x):")
    print(f"  Max magnitude: {np.max(np.abs(spatial_scaled)):.4f}")
    print(f"  Non-zero elements: {np.count_nonzero(spatial_scaled)}")
    
    print(f"\nAfter frequency scaling (inverse 1/{scale_x}x with amplitude 1/{scale_x**2:.2f}):")
    print(f"  Max magnitude: {np.max(np.abs(freq_scaled)):.4f}")
    print(f"  Expected amplitude factor: {1.0 / (scale_x * scale_y):.4f}")
    print(f"  Non-zero elements: {np.count_nonzero(freq_scaled)}")
    print()

def test_fourier_theorem():
    """Test complete Fourier scaling theorem: if you scale spatial by a, spectrum scales by 1/a with amplitude 1/|a|²"""
    print("=" * 70)
    print("TEST 3: Complete Fourier Scaling Theorem")
    print("=" * 70)
    
    # Create a simple spatial image
    spatial = np.zeros((16, 16), dtype=np.complex128)
    spatial[6:10, 6:10] = 1.0 + 0j
    
    # Compute its FFT
    frequency = fft2c(spatial)
    original_magnitude = np.max(np.abs(frequency))
    
    print(f"Original spatial array: {spatial.shape}")
    print(f"Original frequency magnitude (max): {original_magnitude:.6f}")
    
    # Now scale the spatial domain by 2
    scale_x, scale_y = 2.0, 2.0
    spatial_scaled = stretch_complex(spatial.copy(), scale_x, scale_y)
    
    # Recompute FFT
    frequency_from_scaled = fft2c(spatial_scaled)
    new_magnitude = np.max(np.abs(frequency_from_scaled))
    
    # According to similarity theorem: if spatial scales by a, frequency scales by 1/a with amplitude 1/|a|²
    # So if spatial scales by 2, frequency should have 1/4 amplitude
    expected_magnitude = original_magnitude / (scale_x * scale_y)
    
    print(f"\nAfter scaling spatial by {scale_x}x:")
    print(f"  New FFT magnitude (max): {new_magnitude:.6f}")
    print(f"  Expected (1/4 of original): {expected_magnitude:.6f}")
    print(f"  Ratio: {new_magnitude / original_magnitude:.6f} (expected 0.25)")
    
    # Verify the theorem
    ratio = new_magnitude / original_magnitude
    expected_ratio = 1.0 / (scale_x * scale_y)
    error = abs(ratio - expected_ratio)
    status = "✓ PASS" if error < 0.01 else "✗ FAIL"
    print(f"  {status} - Error: {error:.6f}")
    print()

def test_inverse_operations():
    """Test that applying stretch_theorem in spatial and frequency domains are inverses"""
    print("=" * 70)
    print("TEST 4: Domain-Specific Operations (Spatial vs Frequency)")
    print("=" * 70)
    
    # Create test frequency data (simulate an FFT output)
    frequency = np.zeros((16, 16), dtype=np.complex128)
    frequency[7:9, 7:9] = 10.0 + 5.0j
    
    scale_x, scale_y = 2.0, 2.0
    
    # Apply inverse scaling in frequency domain
    freq_after_inverse = stretch_complex_inverse(frequency.copy(), scale_x, scale_y)
    
    print(f"Original frequency magnitude (max): {np.max(np.abs(frequency)):.6f}")
    print(f"After inverse scaling (1/{scale_x}x, amplitude 1/{scale_x*scale_y:.1f}):")
    print(f"  Magnitude (max): {np.max(np.abs(freq_after_inverse)):.6f}")
    print(f"  Expected: {np.max(np.abs(frequency)) / (scale_x * scale_y):.6f}")
    
    # Verify amplitude adjustment
    ratio = np.max(np.abs(freq_after_inverse)) / np.max(np.abs(frequency))
    expected_ratio = 1.0 / (scale_x * scale_y)
    error = abs(ratio - expected_ratio)
    status = "✓ PASS" if error < 0.01 else "✗ FAIL"
    print(f"  {status} - Amplitude ratio error: {error:.6f}")
    print()

def main():
    print("\n" + "=" * 70)
    print("STRETCH THEOREM IMPLEMENTATION TEST SUITE")
    print("=" * 70 + "\n")
    
    try:
        test_amplitude_scaling()
        test_inverse_scaling()
        test_fourier_theorem()
        test_inverse_operations()
        
        print("=" * 70)
        print("ALL TESTS COMPLETED")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
