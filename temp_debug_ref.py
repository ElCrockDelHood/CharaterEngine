import json
import tempfile
from pathlib import Path

d = Path(tempfile.mkdtemp())
ref_dir = d / 'references'
ref_dir.mkdir()

registry_data = {
    'source_registry': {
        'version': '1.0.0',
        'status': 'PLACEHOLDER'
    },
    'sources': {},
    'placeholder_data': {
        'anthropometric_averages': {
            'status': 'PLACEHOLDER',
            'values': {
                'height': {
                    'value': 1.75,
                    'unit': 'meters',
                    'confidence': 'LOW',
                    'provenance': 'ASSUMPTION'
                }
            }
        }
    }
}

with open(ref_dir / 'source_registry.json', 'w') as f:
    json.dump(registry_data, f)

anthropometry_data = {
    'anthropometric_data': {
        'version': '1.0.0',
        'status': 'PLACEHOLDER',
        'global_parameters': {
            'height': {
                'value': 1.75,
                'unit': 'meters',
                'confidence': 'LOW',
                'provenance': 'ASSUMPTION'
            }
        },
        'body_proportions': {
            'head_height_ratio': {
                'value': 0.125,
                'confidence': 'LOW',
                'provenance': 'ASSUMPTION'
            }
        }
    }
}

with open(ref_dir / 'anthropometry.json', 'w') as f:
    json.dump(anthropometry_data, f)

biomechanics_data = {
    'biomechanical_data': {
        'version': '1.0.0',
        'status': 'PLACEHOLDER',
        'joint_centers': {}
    }
}

with open(ref_dir / 'biomechanics.json', 'w') as f:
    json.dump(biomechanics_data, f)

print(f'Created test data in {ref_dir}')

from character_engine.domain.anatomy.reference import ReferenceDataManager
manager = ReferenceDataManager(ref_dir)
print('Manager created')
print(f'Anthropometry data keys: {manager.anthropometry_data.keys()}')
print(f'Global parameters: {manager.anthropometry_data.get("global_parameters", {})}')