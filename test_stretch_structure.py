#!/usr/bin/env python
"""
Structural verification test for Stretch Theorem implementation.
Verifies that the code structure correctly implements the theorem intent.
"""

import sys
import os
import ast
import inspect

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from ImageMixer.services.transform_explorer import actions, complex_helpers

def test_function_exists():
    """Verify all required functions exist"""
    print("=" * 70)
    print("STRUCTURAL TEST 1: Required Functions Exist")
    print("=" * 70)
    
    required_functions = {
        'complex_helpers': ['stretch_complex', 'stretch_complex_inverse'],
        'actions': ['_stretch', '_stretch_theorem_spatial', '_stretch_theorem_frequency'],
    }
    
    all_pass = True
    
    for module_name, func_names in required_functions.items():
        if module_name == 'complex_helpers':
            module = complex_helpers
        else:
            module = actions
            
        for func_name in func_names:
            exists = hasattr(module, func_name)
            status = "✓" if exists else "✗"
            all_pass = all_pass and exists
            print(f"{status} {module_name}.{func_name}: {'EXISTS' if exists else 'MISSING'}")
    
    print()
    return all_pass

def test_stretch_inverse_implementation():
    """Verify stretch_complex_inverse uses correct math"""
    print("=" * 70)
    print("STRUCTURAL TEST 2: stretch_complex_inverse Implementation")
    print("=" * 70)
    
    # Get source code
    source = inspect.getsource(complex_helpers.stretch_complex_inverse)
    
    checks = {
        "Uses inv_scale_x = 1.0 / scale_x": "inv_scale_x = 1.0 / scale_x" in source,
        "Uses inv_scale_y = 1.0 / scale_y": "inv_scale_y = 1.0 / scale_y" in source,
        "Applies amplitude_factor": "amplitude_factor" in source,
        "Multiplies by amplitude_factor": "result * amplitude_factor" in source,
        "Uses abs(scale_x) and abs(scale_y)": "abs(scale_x)" in source and "abs(scale_y)" in source,
    }
    
    all_pass = True
    for check_name, passed in checks.items():
        status = "✓" if passed else "✗"
        all_pass = all_pass and passed
        print(f"{status} {check_name}")
    
    print()
    return all_pass

def test_wrapper_functions():
    """Verify wrapper functions call correct underlying functions"""
    print("=" * 70)
    print("STRUCTURAL TEST 3: Wrapper Function Implementations")
    print("=" * 70)
    
    # Test _stretch_theorem_spatial
    spatial_source = inspect.getsource(actions._stretch_theorem_spatial)
    spatial_correct = "stretch_complex(" in spatial_source
    status_spatial = "✓" if spatial_correct else "✗"
    print(f"{status_spatial} _stretch_theorem_spatial calls stretch_complex (direct scaling)")
    
    # Test _stretch_theorem_frequency
    freq_source = inspect.getsource(actions._stretch_theorem_frequency)
    freq_correct = "stretch_complex_inverse(" in freq_source
    status_freq = "✓" if freq_correct else "✗"
    print(f"{status_freq} _stretch_theorem_frequency calls stretch_complex_inverse (inverse scaling)")
    
    print()
    return spatial_correct and freq_correct

def test_operation_registration():
    """Verify OperationSpec is registered"""
    print("=" * 70)
    print("STRUCTURAL TEST 4: Operation Registration")
    print("=" * 70)
    
    # Get the registry through a local controller
    from ImageMixer.services.transform_explorer.controller import TransformExplorerController
    
    controller = TransformExplorerController()
    registry = controller.registry
    
    # Check for both operations
    stretch_exists = "stretch" in registry
    stretch_theorem_exists = "stretch_theorem" in registry
    
    print(f"{'✓' if stretch_exists else '✗'} Original 'stretch' operation registered")
    print(f"{'✓' if stretch_theorem_exists else '✗'} New 'stretch_theorem' operation registered")
    
    if stretch_theorem_exists:
        spec = registry["stretch_theorem"]
        print(f"\nOperation Details:")
        print(f"  Name: {spec.name}")
        print(f"  Description: {spec.description}")
        print(f"  Has apply_spatial: {hasattr(spec, 'apply_spatial') and spec.apply_spatial is not None}")
        print(f"  Has apply_frequency: {hasattr(spec, 'apply_frequency') and spec.apply_frequency is not None}")
        
        # Verify apply_spatial and apply_frequency are different functions
        same_functions = spec.apply_spatial == spec.apply_frequency
        print(f"  Domain-specific functions: {'✗ SAME' if same_functions else '✓ DIFFERENT'}")
        
        if not same_functions:
            print(f"    apply_spatial = _stretch_theorem_spatial: {spec.apply_spatial.__name__ == '_stretch_theorem_spatial'}")
            print(f"    apply_frequency = _stretch_theorem_frequency: {spec.apply_frequency.__name__ == '_stretch_theorem_frequency'}")
    
    print()
    return stretch_exists and stretch_theorem_exists

def test_controller_dispatch():
    """Verify controller correctly dispatches to domain-specific functions"""
    print("=" * 70)
    print("STRUCTURAL TEST 5: Controller Dispatch Logic")
    print("=" * 70)
    
    from ImageMixer.services.transform_explorer.controller import TransformExplorerController
    
    controller = TransformExplorerController()
    
    # Check that the controller's _apply_worker method exists and has the right structure
    source = inspect.getsource(controller._apply_worker)
    
    checks = {
        "Checks domain == 'spatial'": "domain == \"spatial\"" in source,
        "Calls apply_spatial for spatial domain": "operation.apply_spatial" in source,
        "Calls apply_frequency for frequency domain": "operation.apply_frequency" in source,
        "Computes FFT after spatial": "fft2c(result_spatial)" in source,
        "Computes IFFT after frequency": "ifft2c(result_frequency)" in source,
    }
    
    all_pass = True
    for check_name, passed in checks.items():
        status = "✓" if passed else "✗"
        all_pass = all_pass and passed
        print(f"{status} {check_name}")
    
    print()
    return all_pass

def main():
    print("\n" + "=" * 70)
    print("STRUCTURAL VERIFICATION TESTS")
    print("=" * 70 + "\n")
    
    try:
        test1 = test_function_exists()
        test2 = test_stretch_inverse_implementation()
        test3 = test_wrapper_functions()
        test4 = test_operation_registration()
        test5 = test_controller_dispatch()
        
        all_passed = test1 and test2 and test3 and test4 and test5
        
        print("=" * 70)
        if all_passed:
            print("✓ ALL STRUCTURAL TESTS PASSED")
            print("\nImplementation is correctly structured.")
            print("Ready for integration testing and manual verification in UI.")
        else:
            print("✗ SOME STRUCTURAL TESTS FAILED")
        print("=" * 70)
        
        return 0 if all_passed else 1
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
