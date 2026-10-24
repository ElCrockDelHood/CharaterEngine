"""Performance benchmark for manifold transform operations.

Measures actual performance (not estimates) for:
- Transform composition
- Chain update
- Skeleton update
- Global/local conversion
"""

import statistics
import time

from character_engine.domain.anatomy.osteology.transform import (
    GlobalTransform,
    LocalJointTransform,
)
from character_engine.math.algebra.quaternion import UnitQuaternion
from character_engine.math.algebra.vector3 import Vector3


def benchmark_composition(iterations=10000):
    """Benchmark transform composition (parent global + local joint)."""
    parent = GlobalTransform(
        Vector3(1.0, 2.0, 3.0),
        UnitQuaternion.from_axis_angle(Vector3(0.0, 0.0, 1.0), 0.5)
    )
    local = LocalJointTransform(
        Vector3(0.1, 0.2, 0.3),
        UnitQuaternion.from_axis_angle(Vector3(0.0, 1.0, 0.0), 0.3)
    )

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        result = parent.compose(local)
        end = time.perf_counter()
        times.append((end - start) * 1e6)  # Convert to microseconds

    return {
        'mean_us': statistics.mean(times),
        'median_us': statistics.median(times),
        'min_us': min(times),
        'max_us': max(times),
        'std_us': statistics.stdev(times) if len(times) > 1 else 0
    }


def benchmark_chain_update(levels=10, iterations=1000):
    """Benchmark chain update (root → joint1 → ... → jointN)."""
    times = []

    for _ in range(iterations):
        transforms = []
        current = GlobalTransform.identity()

        start = time.perf_counter()

        for i in range(levels):
            local = LocalJointTransform(
                Vector3(0.1 * i, 0.0, 0.0),
                UnitQuaternion.from_axis_angle(Vector3(0.0, 0.0, 1.0), 0.1 * i)
            )
            current = current.compose(local)
            transforms.append(current)

        end = time.perf_counter()
        times.append((end - start) * 1e6)  # Convert to microseconds

    return {
        'mean_us': statistics.mean(times),
        'median_us': statistics.median(times),
        'min_us': min(times),
        'max_us': max(times),
        'std_us': statistics.stdev(times) if len(times) > 1 else 0
    }


def benchmark_skeleton_update(joints=206, iterations=100):
    """Benchmark full skeleton update (206 joints)."""
    times = []

    for _ in range(iterations):
        current = GlobalTransform.identity()

        start = time.perf_counter()

        for _ in range(joints):
            local = LocalJointTransform(
                Vector3(0.01, 0.0, 0.0),
                UnitQuaternion.from_axis_angle(Vector3(0.0, 0.0, 1.0), 0.01)
            )
            current = current.compose(local)

        end = time.perf_counter()
        times.append((end - start) * 1e6)  # Convert to microseconds

    return {
        'mean_us': statistics.mean(times),
        'median_us': statistics.median(times),
        'min_us': min(times),
        'max_us': max(times),
        'std_us': statistics.stdev(times) if len(times) > 1 else 0
    }


def benchmark_global_local_conversion(iterations=10000):
    """Benchmark global → local → global conversion."""
    parent = GlobalTransform(
        Vector3(10, 20, 30),
        UnitQuaternion.from_axis_angle(Vector3(0, 1, 0), 0.5)
    )
    global_t = GlobalTransform(
        Vector3(1, 2, 3),
        UnitQuaternion.from_axis_angle(Vector3(0, 0, 1), 0.3)
    )

    times = []
    for _ in range(iterations):
        start = time.perf_counter()

        # Global → local
        pos_diff = global_t.position - parent.position
        local_pos = parent.orientation.inverse().rotate(pos_diff)
        local_orient = parent.orientation.inverse() * global_t.orientation
        local = LocalJointTransform(local_pos, local_orient)

        # Local → global
        global_prime = parent.compose(local)

        end = time.perf_counter()
        times.append((end - start) * 1e6)  # Convert to microseconds

    return {
        'mean_us': statistics.mean(times),
        'median_us': statistics.median(times),
        'min_us': min(times),
        'max_us': max(times),
        'std_us': statistics.stdev(times) if len(times) > 1 else 0
    }


if __name__ == '__main__':
    print("=== MANIFOLD TRANSFORM PERFORMANCE BENCHMARK ===")
    print()

    print("Composition (parent global + local joint):")
    comp_results = benchmark_composition()
    print(f"  Mean: {comp_results['mean_us']:.2f} us")
    print(f"  Median: {comp_results['median_us']:.2f} us")
    print(f"  Min: {comp_results['min_us']:.2f} us")
    print(f"  Max: {comp_results['max_us']:.2f} us")
    print(f"  Std: {comp_results['std_us']:.2f} us")
    print()

    print("Chain update (10 levels):")
    chain_results = benchmark_chain_update()
    print(f"  Mean: {chain_results['mean_us']:.2f} us")
    print(f"  Median: {chain_results['median_us']:.2f} us")
    print(f"  Min: {chain_results['min_us']:.2f} us")
    print(f"  Max: {chain_results['max_us']:.2f} us")
    print(f"  Std: {chain_results['std_us']:.2f} us")
    print()

    print("Skeleton update (206 joints):")
    skeleton_results = benchmark_skeleton_update()
    print(f"  Mean: {skeleton_results['mean_us']:.2f} us")
    print(f"  Median: {skeleton_results['median_us']:.2f} us")
    print(f"  Min: {skeleton_results['min_us']:.2f} us")
    print(f"  Max: {skeleton_results['max_us']:.2f} us")
    print(f"  Std: {skeleton_results['std_us']:.2f} us")
    print()

    print("Global <-> Local conversion:")
    conv_results = benchmark_global_local_conversion()
    print(f"  Mean: {conv_results['mean_us']:.2f} us")
    print(f"  Median: {conv_results['median_us']:.2f} us")
    print(f"  Min: {conv_results['min_us']:.2f} us")
    print(f"  Max: {conv_results['max_us']:.2f} us")
    print(f"  Std: {conv_results['std_us']:.2f} us")
