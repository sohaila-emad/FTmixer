#!/usr/bin/env python
"""
Verification test for Mirror operation conjugation.
Confirms that conjugation is applied in frequency domain but not in spatial domain.
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from ImageMixer.services.transform_explorer.actions import _mirror, _mirror_frequency

def test_mirror_no_conjugation_spatial():
    """Verify spatial mirror does NOT conjugate"""
    print("=" * 70)
    print("TEST 1: Spatial Mirror (NO Conjugation)")
    print("=" * 70)
    
    # Create test array with complex values
    test_image = np.array([
        [1 + 2j, 3 + 4j],
        [5 + 6j, 7 + 8j]
    ], dtype=np.complex128)
    
    params = {"axis": "vertical", "direction": "positive"}
    result = _mirror(test_image, params)
    
    # After flip+concatenate (no conjugation), the right half should be flipped left-right
    # Original:     [[1+2j, 3+4j],
    #                [5+6j, 7+8j]]
    # Flipped LR:   [[3+4j, 1+2j],
    #                [7+8j, 5+6j]]
    # Concatenated: [[1+2j, 3+4j, 3+4j, 1+2j],
    #                [5+6j, 7+8j, 7+8j, 5+6j]]
    
    print(f"Original shape: {test_image.shape}")
    print(f"Result shape: {result.shape}")
    print(f"\nOriginal (first element): {test_image[0, 0]}")
    print(f"Result (first element): {result[0, 0]}")
    print(f"Result (flipped copy in same row): {result[0, 2]}")
    
    # Verify no conjugation
    assert result[0, 0] == test_image[0, 0], "Original element should not change"
    assert result[0, 3] == test_image[0, 0], "Flipped should be same (no conjugate)"
    
    print("✓ PASS: Spatial mirror does NOT conjugate")
    print()

def test_mirror_with_conjugation_frequency():
    """Verify frequency mirror DOES conjugate"""
    print("=" * 70)
    print("TEST 2: Frequency Mirror (WITH Conjugation)")
    print("=" * 70)
    
    # Create test array with complex values
    test_image = np.array([
        [1 + 2j, 3 + 4j],
        [5 + 6j, 7 + 8j]
    ], dtype=np.complex128)
    
    params = {"axis": "vertical", "direction": "positive"}
    result = _mirror_frequency(test_image, params)
    
    # After flip+concatenate (WITH conjugation), the right half should be conjugated
    # Original:     [[1+2j, 3+4j],
    #                [5+6j, 7+8j]]
    # Flipped LR:   [[3+4j, 1+2j],
    #                [7+8j, 5+6j]]
    # Conjugated:   [[3-4j, 1-2j],
    #                [7-8j, 5-6j]]
    # Concatenated: [[1+2j, 3+4j, 3-4j, 1-2j],
    #                [5+6j, 7+8j, 7-8j, 5-6j]]
    
    print(f"Original shape: {test_image.shape}")
    print(f"Result shape: {result.shape}")
    print(f"\nOriginal (first element): {test_image[0, 0]}")
    print(f"Result (first element): {result[0, 0]}")
    print(f"Result (conjugated flipped): {result[0, 2]}")
    print(f"Expected conjugated: {np.conj(test_image[0, 1])}")
    
    # Verify conjugation was applied
    assert result[0, 0] == test_image[0, 0], "Original element should not change"
    assert result[0, 2] == np.conj(test_image[0, 1]), "Flipped should be conjugated"
    
    print("✓ PASS: Frequency mirror DOES conjugate")
    print()

def test_comparison_spatial_vs_frequency():
    """Compare spatial and frequency versions side-by-side"""
    print("=" * 70)
    print("TEST 3: Spatial vs Frequency - Side by Side Comparison")
    print("=" * 70)
    
    test_image = np.array([
        [1 + 1j, 2 + 2j],
        [3 + 3j, 4 + 4j]
    ], dtype=np.complex128)
    
    params = {"axis": "vertical", "direction": "positive"}
    
    spatial_result = _mirror(test_image, params)
    freq_result = _mirror_frequency(test_image, params)
    
    print(f"Test image:\n{test_image}\n")
    
    print(f"Spatial mirror result:\n{spatial_result}\n")
    print(f"Frequency mirror result:\n{freq_result}\n")
    
    # Check that they differ
    differs = not np.allclose(spatial_result, freq_result)
    print(f"Results differ: {differs} ✓" if differs else f"Results differ: {differs} ✗")
    
    # Specifically check the duplicated part
    flipped_spatial = spatial_result[0, 2:4]
    flipped_freq = freq_result[0, 2:4]
    
    print(f"\nDuplicated part (spatial): {flipped_spatial}")
    print(f"Duplicated part (frequency): {flipped_freq}")
    print(f"Frequency duplicated is conjugated: {np.allclose(flipped_freq, np.conj(test_image[0, ::-1]))}")
    
    print()

def main():
    print("\n" + "=" * 70)
    print("MIRROR CONJUGATION VERIFICATION TESTS")
    print("=" * 70 + "\n")
    
    try:
        test_mirror_no_conjugation_spatial()
        test_mirror_with_conjugation_frequency()
        test_comparison_spatial_vs_frequency()
        
        print("=" * 70)
        print("✓ ALL MIRROR TESTS PASSED")
        print("\nConjugation is correctly applied:")
        print("  - Spatial: Flip without conjugation")
        print("  - Frequency: Flip WITH conjugation (Fourier property)")
        print("=" * 70)
        
        return 0
        
    except AssertionError as e:
        print(f"\n✗ ASSERTION FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
