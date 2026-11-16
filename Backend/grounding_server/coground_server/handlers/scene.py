from __future__ import annotations

from typing import Any

from ..rpc import RequestContext, Router
from ..state import SceneSnapshot

router = Router()


@router.method(
    "scene.update",
    params=SceneSnapshot,
    description="シーン全体（物体と領域）を置き換える。Plan を作り直し、全クライアントに state.updated が届く",
)
async def update_scene(ctx: RequestContext, scene: SceneSnapshot) -> dict[str, Any]:
    version = ctx.services.state.set_scene(scene)
    # Plan は set_scene の中で作り直される（state.py / planner.py）
    await ctx.services.publish_state()
    return {"version": version, "objects": len(scene.objects), "regions": len(scene.regions)}
