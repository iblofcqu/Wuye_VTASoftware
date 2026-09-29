"""生成 golden 对比用的合成小样例（确定性种子）。

用法：cd backend && uv run python tests/golden/generate_fixtures.py
产物：backend/tests/fixtures/{sample_mesh.ply, sample_scene.xyz, sample_bim.xyz}
"""

from pathlib import Path

import numpy as np
import open3d as o3d

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def main() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(11)

    def sphere_cloud(
        n: int, radius: float = 1.0, shift: tuple[float, float, float] = (0.0, 0.0, 0.0), noise: float = 0.002
    ) -> np.ndarray:
        pts = rng.normal(size=(n, 3))
        pts /= np.linalg.norm(pts, axis=1, keepdims=True)
        return pts * radius + np.asarray(shift) + rng.normal(scale=noise, size=(n, 3))

    scene = sphere_cloud(600, shift=(0.05, -0.03, 0.02))
    bim = sphere_cloud(700)
    np.savetxt(FIXTURES / "sample_scene.xyz", scene)
    np.savetxt(FIXTURES / "sample_bim.xyz", bim)

    mesh = o3d.geometry.TriangleMesh.create_sphere(radius=1.0, resolution=10)
    mesh.compute_vertex_normals()
    o3d.io.write_triangle_mesh(str(FIXTURES / "sample_mesh.ply"), mesh)


if __name__ == "__main__":
    main()
