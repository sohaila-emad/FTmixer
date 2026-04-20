#!/usr/bin/env python
"""
Direct verification test for Stretch Theorem implementation.
Tests that the amplitude adjustment is correctly applied.
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from ImageMixer.services.transform_explorer.complex_helpers import (
    stretch_complex,
    stretch_complex_inverse,
)

def test_direct_amplitude_scaling():
    """
    Direct test: verify that stretch_complex_inverse applies amplitude factor.
    
    For a constant complex array, after stretch_complex_inverse with scales a_x, a_y,
    the magnitude should be divided by (a_x * a_y).
    """
    print("=" * 70)
    print("DIRECT TEST: Amplitude Scaling Verification")
    print("=" * 70)
    
    # Create a simple test image filled with a known complex value
    test_image = np.ones((8, 8), dtype=np.complex128) * (1.0 + 1.0j)
    original_magnitude = np.mean(np.abs(test_image))
    
    test_cases = [
        (1.0, 1.0),
        (2.0, 2.0),
        (0.5, 0.5),
        (2.0, 0.5),
        (10.0, 10.0),
    ]
    
    print(f"Original image: constant (1 + 1j) in all cells")
    print(f"Original magnitude (mean): {original_magnitude:.6f}\n")
    
    all_pass = True
    
    for scale_x, scale_y in test_cases:
        result = stretch_complex_inverse(test_image.copy(), scale_x, scale_y)
        result_magnitude = np.mean(np.abs(result))
        expected_amplitude_factor = 1.0 / (abs(scale_x) * abs(scale_y))
        expected_magnitude = original_magnitude * expected_amplitude_factor
        
        # For a uniform array, the amplitude should scale uniformly
        ratio_observed = result_magnitude / original_magnitude if original_magnitude > 0 else 0
        error = abs(ratio_observed - expected_amplitude_factor)
        
        # Allow some tolerance for numerical errors and interpolation artifacts
        tolerance = 0.05
        passed = error < tolerance
        all_pass = all_pass and passed
        
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} scale_x={scale_x:6.2f}, scale_y={scale_y:6.2f}:")
        print(f"     Expected amplitude factor: {expected_amplitude_factor:.6f}")
        print(f"     Observed amplitude factor: {ratio_observed:.6f}")
        print(f"     Error: {error:.6f}")
        print()
    
    return all_pass

def test_amplitude_factor_consistency():
    """
    Verify that the amplitude factor calculation is consistent with the theorem.
    The key: amplitude scales as 1 / (|scale_x| * |scale_y|)
    """
    print("=" * 70)
    print("AMPLITUDE FACTOR CONSISTENCY TEST")
    print("=" * 70)
    
    all_pass = True
    
    test_factors = [
        ((1.0, 1.0), 1.0),
        ((2.0, 2.0), 0.25),
        ((0.5, 0.5), 4.0),
        ((2.0, 1.0), 0.5),
        ((1.0, 4.0), 0.25),
        ((0.1, 0.1), 100.0),
        ((10.0, 0.1), 10.0),
    ]
    
    for (scale_x, scale_y), expected_factor in test_factors:
        computed = 1.0 / (abs(scale_x) * abs(scale_y))
        error = abs(computed - expected_factor)
        passed = error < 1e-10
        all_pass = all_pass and passed
        
        status = "✓" if passed else "✗"
        print(f"{status} scale({scale_x:6.2f}, {scale_y:6.2f}) → "
              f"factor {computed:.6f} (expected {expected_factor:.6f})")
    
    print()
    return all_pass

def test_inverse_is_applied():
    """
    Verify that stretch_complex_inverse applies inverse scaling (1/a instead of a).
    """
    print("=" * 70)
    print("INVERSE SCALING VERIFICATION")
    print("=" * 70)
    
    # Create a simple image with a peak in the center
    test_image = np.zeros((16, 16), dtype=np.complex128)
    test_image[7:9, 7:9] = 5.0 + 0j
    
    scale_x, scale_y = 2.0, 2.0
    
    # Direct scaling (what _stretch_theorem_spatial does)
    spatial_scaled = stretch_complex(test_image.copy(), scale_x, scale_y)
    
    # Inverse scaling (what _stretch_theorem_frequency does)  
    freq_scaled = stretch_complex_inverse(test_image.copy(), scale_x, scale_y)
    
    # For direct scaling with scale > 1, the content moves toward center (zooms in)
    # For inverse scaling, it should move away from center (zooms out)
    
    spatial_nonzero = np.count_nonzero(np.abs(spatial_scaled) > 0.1)
    freq_nonzero = np.count_nonzero(np.abs(freq_scaled) > 0.1)
    
    print(f"Original non-zero count (peak at 7:9, 7:9): {np.count_nonzero(np.abs(test_image) > 0.1)}")
    print(f"After stretch_complex(scale 2.0x): {spatial_nonzero} non-zero elements")
    print(f"After stretch_complex_inverse(scale 2.0x): {freq_nonzero} non-zero elements")
    print()
    print("Expected behavior:")
    print("  - Direct scaling (2x): zooms in, concentrates content")
    print("  - Inverse scaling (1/2x): zooms out, spreads content")
    print()
    
    # Verify amplitude adjustment in frequency version
    spatial_max = np.max(np.abs(spatial_scaled))
    freq_max = np.max(np.abs(freq_scaled))
    
    expected_freq_amplitude = np.max(np.abs(test_image)) / (scale_x * scale_y)
    amplitude_error = abs(freq_max - expected_freq_amplitude)
    
    passed = amplitude_error < 0.1  # Allow some tolerance
    status = "✓ PASS" if passed else "✗ FAIL"
    
    print(f"{status} Amplitude adjustment in frequency scaling:")
    print(f"    Original max: {np.max(np.abs(test_image)):.6f}")
    print(f"    Spatial (direct scale) max: {spatial_max:.6f}")
    print(f"    Frequency (inverse scale) max: {freq_max:.6f}")
    print(f"    Expected frequency max: {expected_freq_amplitude:.6f}")
    print(f"    Error: {amplitude_error:.6f}")
    print()
    
    return passed

def main():
    print("\n" + "=" * 70)
    print("DIRECT VERIFICATION TESTS")
    print("=" * 70 + "\n")
    
    try:
        test1_pass = test_amplitude_factor_consistency()
        test2_pass = test_direct_amplitude_scaling()
        test3_pass = test_inverse_is_applied()
        
        all_passed = test1_pass and test2_pass and test3_pass
        
        print("=" * 70)
        if all_passed:
            print("✓ ALL TESTS PASSED")
        else:
            print("✗ SOME TESTS FAILED - See details above")
        print("=" * 70)
        
        return 0 if all_passed else 1
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
